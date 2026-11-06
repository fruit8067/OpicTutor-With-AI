// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// OWNER: frontend (contracts.yaml ownership)
//
// 시험 화면 — 문항 하나의 상태 머신. 서버 상태가 진실이다.
// loading → playing → awaiting_record → recording → uploading → processing
//   → done(서버 current_order_no 증가 확인) → next 대사 → 다음 문항 loading
//   → rejected → awaiting_record(재녹음) / failed → [다시 처리](U3)
// 업로드 202는 접수일 뿐이므로 절대 그것만 보고 다음 문항으로 가지 않는다. 문항·순서는 클라이언트가 계산하지 않는다.
import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ApiError, getAnswer, getCurrent, mediaUrl, NETWORK_ERROR, postReplay, retryStt, submitSession, uploadAnswer,
} from '../api/client';
import type { AnswerOut, CurrentQuestionOut } from '../api/types';
import { Live, Rail, Shell } from '../components/Shell';
import { Host, type HostState } from '../features/host/Host';
import { labelOf, REJECT_TEXT, STT_ERROR_TEXT, TYPE_LABEL } from '../lib/messages';
import { usePlayer, type PlayResult } from '../lib/player';
import { extFor, micErrorKind, openMic, Recorder, RECORD_MAX_MS, RECORD_MIN_MS, SILENCE_PEAK, type Recording } from '../lib/recorder';
import { clearSessionId, loadSessionId, routeFor } from '../lib/session';

type Phase =
  | 'loading' | 'playing' | 'blocked' | 'play_error' | 'awaiting_record' | 'recording'
  | 'uploading' | 'upload_failed' | 'processing' | 'failed' | 'finishing' | 'fatal';

const RETRY_DELAYS = [1000, 2000, 4000];
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function hostStateOf(phase: Phase): HostState {
  if (phase === 'playing') return 'speaking';
  if (phase === 'recording') return 'listening';
  if (phase === 'uploading' || phase === 'processing' || phase === 'finishing') return 'processing';
  return 'idle';
}
const fmt = (ms: number) => { const s = Math.floor(ms / 1000); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; };

export default function Exam() {
  const nav = useNavigate();
  const id = loadSessionId();
  const player = usePlayer();
  const [cur, setCur] = useState<CurrentQuestionOut | null>(null);
  const [phase, setPhase] = useState<Phase>('loading');
  const [speakingLine, setSpeakingLine] = useState(false);
  const [note, setNote] = useState<{ kind: 'info' | 'warn'; text: string } | null>(null);
  const [showText, setShowText] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [failedAnswer, setFailedAnswer] = useState<AnswerOut | null>(null);
  const [micError, setMicError] = useState<string | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const recorder = useRef<Recorder | null>(null);
  const pendingUpload = useRef<{ rec: Recording; reqId: string; orderNo: number } | null>(null);
  const alive = useRef(true);
  const phaseRef = useRef<Phase>('loading');
  const loadRef = useRef<() => Promise<void>>(async () => {});
  useEffect(() => { phaseRef.current = phase; }, [phase]);

  const stopRef = useRef(player.stop);
  useEffect(() => { stopRef.current = player.stop; });
  useEffect(() => { alive.current = true; return () => { alive.current = false; stopRef.current(); stream.current?.getTracks().forEach((t) => t.stop()); }; }, []);

  // 업로드가 끝나지 않은 녹음이 있으면 새로고침·닫기 경고
  useEffect(() => {
    const warn = (e: BeforeUnloadEvent) => { if (phaseRef.current === 'uploading' || phaseRef.current === 'upload_failed') { e.preventDefault(); e.returnValue = ''; } };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, []);

  const lineUrl = useCallback((c: CurrentQuestionOut | null, key: string) => mediaUrl(c?.host_lines?.[key]?.audio_url), []);

  const playLine = useCallback(async (c: CurrentQuestionOut | null, key: string) => {
    const url = lineUrl(c, key);
    if (!url) return;
    setSpeakingLine(true);
    await player.play(url);
    setSpeakingLine(false);
  }, [lineUrl, player]);

  const handleFatal = useCallback((e: unknown) => {
    if (e instanceof ApiError && e.code === 'SESSION_NOT_FOUND') { clearSessionId(); nav('/setup', { replace: true }); return; }
    setNote({ kind: 'warn', text: (e as Error)?.message ?? '잠시 후 다시 시도해 주세요.' });
    setPhase('fatal');
  }, [nav]);

  const finish = useCallback(async (c: CurrentQuestionOut | null) => {
    if (!id) return;
    setPhase('finishing');
    await playLine(c, 'finish');
    try { await submitSession(id); nav('/result', { replace: true }); }
    catch (e) {
      if (e instanceof ApiError && e.code === 'INVALID_STATE') { nav('/', { replace: true }); return; } // 이미 제출됨 → 상태 라우팅
      handleFatal(e);
    }
  }, [id, nav, playLine, handleFatal]);

  const playQuestion = useCallback(async (c: CurrentQuestionOut) => {
    const url = mediaUrl(c.question?.audio_url);
    if (!url) { setPhase('play_error'); return; }
    setPhase('playing');
    const r: PlayResult = await player.play(url);
    if (!alive.current) return;
    setPhase(r === 'ended' ? 'awaiting_record' : r === 'blocked' ? 'blocked' : 'play_error');
  }, [player]);

  const poll = useCallback(async (answerId: string, orderNo: number, c: CurrentQuestionOut) => {
    if (!id) return;
    setPhase('processing');
    for (;;) {
      if (!alive.current) return;
      let a: AnswerOut;
      try { a = await getAnswer(id, answerId); }
      catch (e) {
        if (e instanceof ApiError && e.code !== NETWORK_ERROR && e.status < 500) { handleFatal(e); return; }
        await sleep(2000); continue;                    // 일시 오류: 같은 문항에서 계속 확인
      }
      if (a.stt_status === 'done' && (a.current_order_no > orderNo || a.all_answered)) {
        pendingUpload.current = null;
        if (a.all_answered) { await finish(c); return; }
        await playLine(c, 'next');
        await loadRef.current();
        return;
      }
      if (a.stt_status === 'rejected') {
        setNote({ kind: 'warn', text: `${labelOf(REJECT_TEXT, a.reject_reason ?? '')} 같은 문항에 다시 답해 주세요.` });
        await playLine(c, 'say_again');
        setPhase('awaiting_record');
        return;
      }
      if (a.stt_status === 'failed') {
        setFailedAnswer(a);
        setNote({ kind: 'warn', text: labelOf(STT_ERROR_TEXT, a.error_code ?? 'STT_ENGINE_ERROR') });
        setPhase('failed');
        return;
      }
      await sleep(2000);
    }
  }, [id, finish, playLine, handleFatal]); // 다음 문항 로드는 loadRef(아래 load)로

  const load = useCallback(async (): Promise<void> => {
    if (!id) { nav('/setup', { replace: true }); return; }
    setPhase('loading'); setNote(null); setShowText(false); setFailedAnswer(null);
    let c: CurrentQuestionOut;
    try { c = await getCurrent(id); }
    catch (e) {
      if (e instanceof ApiError && e.code === 'INVALID_STATE') { nav('/', { replace: true }); return; }
      handleFatal(e); return;
    }
    if (!alive.current) return;
    setCur(c);
    if (c.session_status !== 'in_progress') { const to = routeFor(c.session_status); nav(to ?? '/setup', { replace: true }); return; }
    if (c.all_answered || !c.question) { await finish(c); return; }
    const p = c.pending_answer;
    if (p && p.order_no === c.question.order_no) {
      if (p.stt_status === 'queued' || p.stt_status === 'processing') { await poll(p.answer_id, p.order_no, c); return; }
      if (p.stt_status === 'failed') {
        setFailedAnswer(p); setNote({ kind: 'warn', text: labelOf(STT_ERROR_TEXT, p.error_code ?? 'STT_ENGINE_ERROR') });
        setPhase('failed'); return;
      }
      if (p.stt_status === 'rejected') {
        setNote({ kind: 'warn', text: `${labelOf(REJECT_TEXT, p.reject_reason ?? '')} 같은 문항에 다시 답해 주세요.` });
        setPhase('awaiting_record'); return;
      }
    }
    await playQuestion(c);
  }, [id, nav, finish, poll, playQuestion, handleFatal]);

  useEffect(() => { loadRef.current = load; }, [load]);
  const started = useRef(false);
  useEffect(() => { if (started.current) return; started.current = true; void loadRef.current(); }, []); // 첫 진입 1회(StrictMode 이중 실행 방지)

  // 녹음 경과 시간
  useEffect(() => {
    if (phase !== 'recording') return;
    const t = window.setInterval(() => setElapsed(recorder.current?.elapsedMs() ?? 0), 200);
    return () => window.clearInterval(t);
  }, [phase]);

  const upload = async (job: { rec: Recording; reqId: string; orderNo: number }) => {
    if (!id || !cur) return;
    setPhase('uploading');
    for (let i = 0; ; i++) {
      try {
        const a = await uploadAnswer(id, { order_no: job.orderNo, client_request_id: job.reqId, duration_ms: job.rec.durationMs,
                                           audio: job.rec.blob, filename: `answer.${extFor(job.rec.mime)}` });
        await poll(a.answer_id, job.orderNo, cur);
        return;
      } catch (e) {
        const transient = !(e instanceof ApiError) || e.code === NETWORK_ERROR || e.status >= 500;
        if (transient && i < RETRY_DELAYS.length) { await sleep(RETRY_DELAYS[i]); continue; }
        if (transient) { setPhase('upload_failed'); return; }
        const code = (e as ApiError).code;
        pendingUpload.current = null;
        if (code === 'ORDER_MISMATCH' || code === 'ANSWER_PENDING' || code === 'INVALID_STATE') { await load(); return; }
        setNote({ kind: 'warn', text: `${(e as ApiError).message} 같은 문항에 다시 답해 주세요.` });
        setPhase('awaiting_record');
        return;
      }
    }
  };

  const toggleRecord = async () => {
    if (!cur?.question) return;
    if (phase === 'recording') { recorder.current?.stop(); return; }
    if (phase !== 'awaiting_record') return;
    setNote(null); setMicError(null);
    try { if (!stream.current) stream.current = await openMic(); }
    catch (e) {
      const k = micErrorKind(e);
      setMicError(k === 'denied' ? '마이크 권한이 꺼졌어요. 주소창의 사이트 설정에서 마이크를 허용한 뒤 다시 눌러 주세요.' : '마이크를 켜지 못했어요. 연결을 확인하고 다시 눌러 주세요.');
      return;
    }
    const r = new Recorder(stream.current);
    recorder.current = r;
    setElapsed(0);
    setPhase('recording');
    const rec = await r.start(RECORD_MAX_MS);
    if (!alive.current) return;
    if (rec.durationMs < RECORD_MIN_MS || rec.peak < SILENCE_PEAK) {
      setNote({ kind: 'warn', text: rec.durationMs < RECORD_MIN_MS ? '답변이 너무 짧았어요. 다시 답해 주세요.' : '목소리가 거의 들리지 않았어요. 마이크 가까이에서 다시 답해 주세요.' });
      setPhase('awaiting_record');
      await playLine(cur, 'say_again');
      return;
    }
    const job = { rec, reqId: crypto.randomUUID(), orderNo: cur.question.order_no };   // 녹음 1회당 키 1개
    pendingUpload.current = job;
    await upload(job);
  };

  const replay = async () => {
    if (!id || !cur?.question) return;
    try {
      const r = await postReplay(id, cur.question.order_no);
      setCur({ ...cur, question: { ...cur.question, replay_count: r.replay_count } });
      await playQuestion(cur);
    } catch (e) { setNote({ kind: 'warn', text: (e as Error).message }); }
  };

  const retryProcessing = async () => {
    if (!id || !failedAnswer || !cur) return;
    setPhase('processing'); setNote(null);                                // 중복 클릭 방지: 즉시 처리 중으로
    try { const a = await retryStt(id, failedAnswer.answer_id); setFailedAnswer(null); await poll(a.answer_id, a.order_no, cur); }
    catch (e) { setNote({ kind: 'warn', text: (e as Error).message }); setPhase('failed'); }
  };

  const q = cur?.question;
  const total = cur?.total ?? 8;
  const orderNo = q?.order_no ?? 1;
  const busyAudio = phase === 'playing' || speakingLine;
  const canRecord = (phase === 'awaiting_record' || phase === 'recording') && !speakingLine;
  const canReplay = !!q && q.replay_count < q.replay_limit && (phase === 'awaiting_record') && !speakingLine;
  const hostState = speakingLine ? 'speaking' : hostStateOf(phase);
  const status = {
    loading: '문항을 불러오는 중', playing: '질문을 듣고 있어요', blocked: '브라우저가 자동 재생을 막았어요',
    play_error: '질문 음성을 재생하지 못했어요', awaiting_record: '마이크 버튼을 눌러 답해 주세요', recording: '녹음 중 — 다 말했으면 버튼을 다시 눌러 주세요',
    uploading: '답변을 보내는 중', upload_failed: '답변을 보내지 못했어요', processing: '답변 처리 중', failed: '답변을 처리하지 못했어요',
    finishing: '시험을 마치는 중', fatal: '문제가 생겼어요',
  }[phase];

  return (
    <Shell wide aside={<Rail total={total} current={orderNo} doneUpTo={orderNo - 1} />}>
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(220px, 320px) 1fr', gap: 48, alignItems: 'start', paddingTop: 16 }}>
        <div style={{ color: 'var(--ink)', position: 'sticky', top: 24 }}>
          <Host state={hostState} />
          <p className="faint" style={{ textAlign: 'center', marginTop: 8 }}>진행자 린</p>
        </div>

        <section style={{ display: 'grid', gap: 24 }} aria-labelledby="q-h">
          <div style={{ display: 'grid', gap: 6 }}>
            <span className="faint">{orderNo} / {total} · {q ? labelOf(TYPE_LABEL, q.question_type) : ''}{q && !q.is_scored ? ' · 채점하지 않는 연습 문항' : ''}</span>
            <h1 id="q-h" style={{ fontSize: '1.5rem' }}>{status}</h1>
          </div>

          {q && (
            <div style={{ display: 'grid', gap: 8 }}>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button className="btn btn-ghost" onClick={replay} disabled={!canReplay}
                        aria-label={`질문 다시 듣기, ${q.replay_limit - q.replay_count}회 남음`}>
                  다시 듣기 ({q.replay_limit - q.replay_count}회 남음)
                </button>
                <button className="btn btn-quiet" onClick={() => setShowText((v) => !v)} aria-expanded={showText} aria-controls="q-text">
                  {showText ? '질문 글 숨기기' : '질문 글 보기'}
                </button>
              </div>
              {showText && <p id="q-text" lang="en" className="sheet prose-w" style={{ padding: '14px 16px' }}>{q.text}</p>}
            </div>
          )}

          {phase === 'blocked' && cur && (
            <div className="notice"><p style={{ marginBottom: 10 }}>브라우저가 소리 자동 재생을 막았어요. 버튼을 눌러 질문을 들어 주세요.</p>
              <button className="btn" onClick={async () => { await player.unlock(); await playQuestion(cur); }} autoFocus>눌러서 듣기</button></div>
          )}
          {phase === 'play_error' && cur && (
            <div className="notice notice-warn" role="alert"><p style={{ marginBottom: 10 }}>질문 음성을 불러오지 못했어요. 같은 문항을 다시 재생해 주세요.</p>
              <button className="btn" onClick={() => playQuestion(cur)} autoFocus>다시 재생</button></div>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: 24, padding: '20px 0' }}>
            <button className="mic" onClick={toggleRecord} disabled={!canRecord || busyAudio} data-recording={phase === 'recording'}
                    aria-label={phase === 'recording' ? '녹음 마치기' : '녹음 시작'} aria-pressed={phase === 'recording'}>
              {phase === 'recording'
                ? <svg width="30" height="30" viewBox="0 0 24 24" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" /></svg>
                : <svg width="34" height="34" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><rect x="9" y="3" width="6" height="11" rx="3" fill="currentColor" stroke="none" /><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21" /></svg>}
            </button>
            <div style={{ display: 'grid', gap: 4 }}>
              {phase === 'recording' ? (
                <>
                  <span style={{ color: 'var(--rec)', fontWeight: 600 }} aria-hidden="true">● 녹음 중 {fmt(elapsed)}</span>
                  <span className="faint">최대 {fmt(RECORD_MAX_MS)}. 시간이 되면 자동으로 마쳐요.</span>
                </>
              ) : busyAudio ? <span className="muted">진행자 음성이 끝나면 녹음할 수 있어요.</span>
                : phase === 'awaiting_record' ? <span className="muted">버튼을 눌러 시작하고, 다 말하면 다시 눌러 마쳐요.</span>
                : phase === 'uploading' || phase === 'processing' ? <span className="muted">답변을 저장하는 중이에요. 이 문항에서 기다려 주세요.</span>
                : null}
            </div>
          </div>

          {micError && <p className="notice notice-warn" role="alert">{micError}</p>}
          {note && <p className={`notice ${note.kind === 'warn' ? 'notice-warn' : ''}`} role={note.kind === 'warn' ? 'alert' : undefined}>{note.text}</p>}

          {phase === 'uploading' && <p className="faint">새로고침하거나 창을 닫으면 아직 보내지 못한 녹음이 사라질 수 있어요.</p>}
          {phase === 'upload_failed' && (
            <div className="notice notice-warn" role="alert">
              <p style={{ marginBottom: 10 }}>네트워크 문제로 답변을 보내지 못했어요. 녹음은 이 화면에 보관되어 있어요. 새로고침하면 사라질 수 있어요.</p>
              <button className="btn" onClick={() => pendingUpload.current && upload(pendingUpload.current)} autoFocus>다시 보내기</button>
            </div>
          )}
          {phase === 'failed' && (
            <div style={{ display: 'flex', gap: 12 }}>
              <button className="btn" onClick={retryProcessing} autoFocus>다시 처리</button>
            </div>
          )}
          {phase === 'fatal' && <button className="btn btn-ghost" onClick={() => load()}>다시 불러오기</button>}
        </section>
      </div>
      <Live>{status}</Live>
    </Shell>
  );
}
