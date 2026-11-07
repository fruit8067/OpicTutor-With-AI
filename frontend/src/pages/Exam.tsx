// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// 후속 수정: 필수 대사 재시도·이탈 후 요청 방지는 OpenAI Codex의 도움으로 작성되었습니다.
// 후속 수정: 문항 건너뛰기(Q3), 마이크 UX(실시간 음량·무음 경고·장치 선택), Stitch 레이아웃(진행 카드·7:5 작업 영역)은 Claude(Anthropic)의 도움으로 작성되었습니다.
// OWNER: frontend (contracts.yaml ownership)
//
// 시험 화면 — 문항 하나의 상태 머신. 서버 상태가 진실이다.
// loading → playing → awaiting_record → recording → uploading → processing
//   → done(서버 current_order_no 증가 확인) → next 대사 → 다음 문항 loading
//   → rejected → awaiting_record(재녹음) / failed → [다시 처리](U3)
//   → [건너뛰기](Q3) → skipping → 서버 current_order_no 증가 확인 → next 대사 → 다음 문항
// 업로드 202는 접수일 뿐이므로 절대 그것만 보고 다음 문항으로 가지 않는다. 문항·순서는 클라이언트가 계산하지 않는다.
import { useCallback, useEffect, useRef, useState, type CSSProperties } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ApiError, getAnswer, getCurrent, mediaUrl, NETWORK_ERROR, postReplay, retryStt, skipQuestion, submitSession, uploadAnswer,
} from '../api/client';
import type { AnswerOut, CurrentQuestionOut } from '../api/types';
import { Live, Shell } from '../components/Shell';
import { Host, type HostState } from '../features/host/Host';
import { MicLevel } from '../components/MicLevel';
import { labelOf, REJECT_TEXT, STT_ERROR_TEXT, TYPE_LABEL } from '../lib/messages';
import { usePlayer, type PlayResult } from '../lib/player';
import {
  extFor, micErrorKind, openMic, Recorder, RECORD_MAX_MS, RECORD_MIN_MS, SILENCE_PEAK, SILENCE_WARN_MS, toLevel, VOICE_RMS, type Recording,
} from '../lib/recorder';
import { clearSessionId, loadMicId, loadSessionId, routeFor } from '../lib/session';

type Phase =
  | 'loading' | 'playing' | 'blocked' | 'play_error' | 'awaiting_record' | 'recording'
  | 'line_error' | 'uploading' | 'upload_failed' | 'processing' | 'failed' | 'skipping' | 'finishing' | 'fatal';

// 오디오가 재생 중이지 않고 서버에 처리 중인 답변이 없는 단계에서만 건너뛸 수 있다.
const SKIPPABLE: Phase[] = ['awaiting_record', 'blocked', 'play_error', 'failed'];

const RETRY_DELAYS = [1000, 2000, 4000];
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function hostStateOf(phase: Phase): HostState {
  if (phase === 'playing') return 'speaking';
  if (phase === 'recording') return 'listening';
  if (phase === 'uploading' || phase === 'processing' || phase === 'skipping' || phase === 'finishing') return 'processing';
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
  const [confirmSkip, setConfirmSkip] = useState(false);
  const [level, setLevel] = useState(0);              // 녹음 중 실시간 음량(0~1)
  const [silent, setSilent] = useState(false);        // 녹음 중 SILENCE_WARN_MS 이상 목소리 없음
  const rms = useRef(0);
  const lastVoiceAt = useRef(0);
  const retryLine = useRef<(() => Promise<void>) | null>(null);
  const recordingStarted = useRef(false);
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

  // 대사도 필수 음성이다. 실패하면 같은 음성을 재시도한 뒤에만 진행한다.
  const playLine = useCallback(async (c: CurrentQuestionOut | null, key: string, next: () => Promise<void>) => {
    const attempt = async (): Promise<void> => {
      setSpeakingLine(true);
      const url = lineUrl(c, key);
      const result = url ? await player.play(url) : 'error';
      if (!alive.current) return;
      setSpeakingLine(false);
      if (result !== 'ended') {
        retryLine.current = attempt;
        setPhase('line_error');
        return;
      }
      retryLine.current = null;
      await next();
    };
    await attempt();
  }, [lineUrl, player]);

  const handleFatal = useCallback((e: unknown) => {
    if (e instanceof ApiError && e.code === 'SESSION_NOT_FOUND') { clearSessionId(); nav('/setup', { replace: true }); return; }
    setNote({ kind: 'warn', text: (e as Error)?.message ?? '잠시 후 다시 시도해 주세요.' });
    setPhase('fatal');
  }, [nav]);

  const finish = useCallback(async (c: CurrentQuestionOut | null) => {
    if (!id) return;
    setPhase('finishing');
    await playLine(c, 'finish', async () => {
    try { await submitSession(id); if (alive.current) nav('/result', { replace: true }); }
    catch (e) {
      if (e instanceof ApiError && e.code === 'INVALID_STATE') { nav('/', { replace: true }); return; } // 이미 제출됨 → 상태 라우팅
      handleFatal(e);
    }
    });
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
      if (!alive.current) return;
      if (a.stt_status === 'done' && (a.current_order_no > orderNo || a.all_answered)) {
        pendingUpload.current = null;
        if (a.all_answered) { await finish(c); return; }
        await playLine(c, 'next', () => loadRef.current());
        return;
      }
      if (a.stt_status === 'rejected') {
        setNote({ kind: 'warn', text: `${labelOf(REJECT_TEXT, a.reject_reason ?? '')} 같은 문항에 다시 답해 주세요.` });
        await playLine(c, 'say_again', async () => { setPhase('awaiting_record'); });
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
    setPhase('loading'); setNote(null); setShowText(false); setFailedAnswer(null); setConfirmSkip(false);
    let c: CurrentQuestionOut;
    try { c = await getCurrent(id); }
    catch (e) {
      if (e instanceof ApiError && e.code === 'INVALID_STATE') { nav('/', { replace: true }); return; }
      handleFatal(e); return;
    }
    if (!alive.current) return;
    setCur(c);
    if (c.session_status !== 'in_progress') { const to = routeFor(c.session_status); nav(to ?? '/setup', { replace: true }); return; }
    if (c.all_answered) { await finish(c); return; }
    if (!c.question) { handleFatal(new Error('현재 문항을 불러오지 못했어요. 다시 불러와 주세요.')); return; }
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
    if (c.question.order_no === 1) await playLine(c, 'greeting', () => playQuestion(c));
    else await playQuestion(c);
  }, [id, nav, finish, poll, playQuestion, playLine, handleFatal]);

  useEffect(() => { loadRef.current = load; }, [load]);
  const started = useRef(false);
  useEffect(() => { if (started.current) return; started.current = true; void loadRef.current(); }, []); // 첫 진입 1회(StrictMode 이중 실행 방지)

  // 녹음 경과 시간·실시간 음량·무음 감지
  useEffect(() => {
    if (phase !== 'recording') return;
    lastVoiceAt.current = performance.now();
    const t = window.setInterval(() => {
      setElapsed(recorder.current?.elapsedMs() ?? 0);
      const now = performance.now();
      if (rms.current >= VOICE_RMS) lastVoiceAt.current = now;
      setLevel(toLevel(rms.current));
      setSilent(now - lastVoiceAt.current >= SILENCE_WARN_MS);
    }, 80);
    return () => window.clearInterval(t);
  }, [phase]);

  const upload = async (job: { rec: Recording; reqId: string; orderNo: number }) => {
    if (!id || !cur) return;
    setPhase('uploading');
    for (let i = 0; ; i++) {
      if (!alive.current) return;
      try {
        const a = await uploadAnswer(id, { order_no: job.orderNo, client_request_id: job.reqId, duration_ms: job.rec.durationMs,
                                           audio: job.rec.blob, filename: `answer.${extFor(job.rec.mime)}` });
        if (!alive.current) return;
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
    if (phase !== 'awaiting_record' || recordingStarted.current) return;
    recordingStarted.current = true;
    setNote(null); setMicError(null);
    try { if (!stream.current || !stream.current.getAudioTracks().some((t) => t.readyState === 'live')) stream.current = await openMic(loadMicId()); }
    catch (e) {
      const k = micErrorKind(e);
      recordingStarted.current = false;
      setMicError(k === 'denied' ? '마이크 권한이 꺼졌어요. 주소창의 사이트 설정에서 마이크를 허용한 뒤 다시 눌러 주세요.' : '마이크를 켜지 못했어요. 연결을 확인하고 다시 눌러 주세요.');
      return;
    }
    if (!alive.current || phaseRef.current !== 'awaiting_record') { recordingStarted.current = false; stream.current?.getTracks().forEach((t) => t.stop()); return; }
    rms.current = 0;
    const r = new Recorder(stream.current, (v) => { rms.current = v; });
    recorder.current = r;
    setElapsed(0);
    setPhase('recording');
    let rec: Recording;
    try { rec = await r.start(RECORD_MAX_MS); }
    catch {
      stream.current?.getTracks().forEach((t) => t.stop()); stream.current = null;
      if (alive.current) { setMicError('녹음하지 못했어요. 마이크 연결을 확인하고 다시 녹음해 주세요.'); setPhase('awaiting_record'); }
      return;
    } finally { recordingStarted.current = false; }
    if (!alive.current) return;
    if (rec.durationMs < RECORD_MIN_MS || rec.peak < SILENCE_PEAK) {
      setNote({ kind: 'warn', text: rec.durationMs < RECORD_MIN_MS ? '답변이 너무 짧았어요. 다시 답해 주세요.' : '목소리가 거의 들리지 않았어요. 마이크 가까이에서 다시 답해 주세요.' });
      setPhase('awaiting_record');
      await playLine(cur, 'say_again', async () => { setPhase('awaiting_record'); });
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

  const skip = async () => {
    if (!id || !cur?.question || !SKIPPABLE.includes(phase) || speakingLine) return;
    const before = phase;
    const orderNo = cur.question.order_no;
    setConfirmSkip(false); setNote(null); setMicError(null);
    setPhase('skipping');                                                  // 중복 클릭 방지
    try {
      const r = await skipQuestion(id, orderNo);
      if (!alive.current) return;
      pendingUpload.current = null; setFailedAnswer(null);
      if (r.all_answered) { await finish(cur); return; }
      await playLine(cur, 'next', () => loadRef.current());
    } catch (e) {
      if (!alive.current) return;
      const code = e instanceof ApiError ? e.code : '';
      if (code === 'ORDER_MISMATCH' || code === 'INVALID_STATE' || code === 'ANSWER_PENDING') { await load(); return; }
      setNote({ kind: 'warn', text: (e as Error)?.message ?? '건너뛰지 못했어요. 다시 시도해 주세요.' });
      setPhase(before);
    }
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
  const canSkip = !!q && SKIPPABLE.includes(phase) && !speakingLine;
  const hostState = speakingLine ? 'speaking' : hostStateOf(phase);
  const status = {
    loading: '문항을 불러오는 중', playing: '질문을 듣고 있어요', blocked: '브라우저가 자동 재생을 막았어요',
    play_error: '질문 음성을 재생하지 못했어요', awaiting_record: '마이크 버튼을 눌러 답해 주세요', recording: '녹음 중 — 다 말했으면 버튼을 다시 눌러 주세요',
    line_error: '진행자 음성을 다시 재생해 주세요', uploading: '답변을 보내는 중', upload_failed: '답변을 보내지 못했어요', processing: '답변 처리 중', failed: '답변을 처리하지 못했어요', skipping: '다음 문항으로 넘어가는 중',
    finishing: '시험을 마치는 중', fatal: '문제가 생겼어요',
  }[phase];

  const recording = phase === 'recording';
  const saving = phase === 'uploading' || phase === 'processing' || phase === 'skipping' || phase === 'finishing';
  const ready = phase === 'awaiting_record' && canRecord && !busyAudio;
  const pill = recording
    ? (silent ? <span className="chip chip-warn"><span className="rec-dot" aria-hidden="true" />REC · 음성 입력 감지 대기 중</span>
              : <span className="chip chip-rec"><span className="rec-dot" aria-hidden="true" />REC · 녹음 진행 중</span>)
    : saving ? <span className="chip chip-soft">● 답변 저장 중</span>
    : ready ? <span className="chip chip-soft">● 답변 대기 (준비 완료)</span>
    : busyAudio ? <span className="chip">● 질문 듣는 중</span>
    : <span className="chip">● 대기</span>;
  const headline = recording ? (silent ? '마이크 입력이 감지되지 않고 있어요' : '녹음 중이에요 — 편하게 말해 보세요')
    : saving ? (phase === 'skipping' ? '다음 문항으로 넘어가는 중이에요' : '답변을 저장하고 있어요…')
    : ready ? '버튼을 눌러 답변을 시작하세요'
    : busyAudio ? '진행자 음성이 끝나면 녹음할 수 있어요'
    : status;
  const sub = recording ? (silent ? '마이크 가까이에서 다시 말하거나, 마이크 연결을 확인해 주세요. 녹음은 계속되고 있어요.' : '말이 막히면 "Well…"처럼 자연스럽게 이어 가도 괜찮아요. 다 말했으면 버튼을 다시 눌러요.')
    : saving ? '음성을 텍스트로 바꿔 저장하는 중이에요. 이 문항에서 잠시 기다려 주세요.'
    : ready ? '녹음이 시작되면 버튼이 빨간색으로 바뀌고, 말하는 동안 막대가 움직여요.'
    : null;
  const stepState = (n: number) => (n < orderNo ? 'done' : n === orderNo ? 'current' : 'todo');
  const stepKicker = (n: number) => (n < orderNo ? '완료' : n > orderNo ? '대기 중' : recording ? '진행 중 (REC)' : saving ? '저장 중' : '진행 중');
  const steps = [orderNo - 1, orderNo, orderNo + 1].map((n, i) => ({ n, pos: ['prev', 'cur', 'next'][i] })).filter((s) => s.n >= 1 && s.n <= total);

  return (
    <Shell wide compact>
      <div style={{ display: 'grid', gap: 10 }}>
        <section className="sheet exam-top-bar" aria-label="진행 상황">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span className="chip chip-soft" style={{ minHeight: 22, padding: '0 0.55rem', fontSize: '0.7rem' }}>● 실전 모의 인터뷰</span>
            <span className="faint" style={{ fontSize: '0.8125rem' }}>전체 {total}문항 중 <strong>{orderNo}번째</strong></span>
            {q && !q.is_scored && <span className="faint" style={{ fontSize: '0.75rem' }}>· 연습 문항(채점 제외)</span>}
          </div>
          <ol className="steps" style={{ listStyle: 'none', margin: 0, padding: 0 }}>
            {steps.map(({ n, pos }) => (
              <li key={n} className="step" data-state={stepState(n)} data-pos={pos} aria-current={n === orderNo ? 'step' : undefined}>
                <span className="step-no">{n < orderNo
                  ? <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>
                  : n}</span>
                <span style={{ display: 'inline-flex', alignItems: 'baseline', gap: 5, minWidth: 0 }}>
                  <span className="step-kicker">{stepKicker(n)}</span>
                  <span className="step-title">문항 {n}{n === orderNo && q ? ` (${labelOf(TYPE_LABEL, q.question_type)})` : ''}</span>
                </span>
                {n === orderNo && recording && <span className="chip chip-rec" style={{ minHeight: 20, padding: '0 0.45rem', fontSize: '0.6875rem' }}>LIVE</span>}
              </li>
            ))}
          </ol>
        </section>

        <div className="exam-grid">
          <section className="exam-host-col" aria-labelledby="q-h">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <span className="chip chip-primary">Question {String(orderNo).padStart(2, '0')}</span>
                {q && <span className="chip">{labelOf(TYPE_LABEL, q.question_type)}</span>}
                {q && !q.is_scored && <span className="chip chip-soft">연습 문항</span>}
              </div>
              {q && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                  <span className="faint" style={{ fontSize: '0.75rem', color: 'var(--primary)', fontWeight: 600 }}>다시 듣기 {q.replay_limit - q.replay_count}회 남음</span>
                  <button className="btn btn-ghost" style={{ minHeight: 34, padding: '0 0.85rem', fontSize: '0.8125rem' }} onClick={replay} disabled={!canReplay}
                          aria-label={`질문 다시 듣기, ${q.replay_limit - q.replay_count}회 남음`}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><path d="M3 12a9 9 0 1 0 3-6.7L3 8" /><path d="M3 3v5h5" /></svg>
                    다시 듣기
                  </button>
                  <button className="btn btn-ghost" style={{ minHeight: 34, padding: '0 0.85rem', fontSize: '0.8125rem' }}
                          onClick={() => setShowText((v) => !v)} aria-expanded={showText} aria-controls="q-text">
                    <span>{showText ? '질문 글 숨기기' : '질문 글 보기'}</span>
                  </button>
                </div>
              )}
            </div>
            <h1 id="q-h" className="sr-only">{orderNo}번 문항 — {status}</h1>

            <div className="host-open-stage">
              <div className="host-avatar">
                <Host state={hostState} />
              </div>
              <div className="host-caption">
                <strong style={{ fontSize: '0.9375rem' }}>진행자 린</strong>
                <span className="faint" style={{ fontSize: '0.8125rem' }}>· {busyAudio ? '질문을 읽고 있어요' : recording ? '답변을 듣고 있어요' : saving ? '답변을 확인하고 있어요' : '질문 음성 대기'}</span>
              </div>
            </div>

            {showText && q && (
              <div className="sheet" style={{ padding: '12px 16px' }}>
                <p id="q-text" lang="en" className="question-quote prose-w">“{q.text}”</p>
              </div>
            )}

            {phase === 'blocked' && cur && (
              <div className="notice"><p style={{ marginBottom: 8 }}>브라우저가 소리 자동 재생을 막았어요. 버튼을 눌러 질문을 들어 주세요.</p>
                <button className="btn" onClick={async () => { await player.unlock(); await playQuestion(cur); }} autoFocus>눌러서 듣기</button></div>
            )}
            {phase === 'play_error' && cur && (
              <div className="notice notice-warn" role="alert"><p style={{ marginBottom: 8 }}>질문 음성을 불러오지 못했어요. 같은 문항을 다시 재생해 주세요.</p>
                <button className="btn" onClick={() => playQuestion(cur)} autoFocus>다시 재생</button></div>
            )}
            {phase === 'line_error' && (
              <div className="notice notice-warn" role="alert">
                <p style={{ marginBottom: 8 }}>진행자 음성을 재생하지 못했어요. 음성을 들은 뒤 계속할 수 있어요.</p>
                <button className="btn" disabled={speakingLine} onClick={() => retryLine.current?.()} autoFocus>진행자 음성 다시 듣기</button>
              </div>
            )}
          </section>

          <section className="sheet" style={{ padding: '18px 22px', display: 'grid', gap: 12, justifyItems: 'center', alignContent: 'center', textAlign: 'center',
                   background: recording && !silent ? 'linear-gradient(180deg, #fff7f7 0%, #fff 40%)' : undefined }} aria-label="답변 녹음">
            {pill}
            {recording && silent && (
              <div className="notice notice-warn" role="status" style={{ textAlign: 'left', width: '100%', boxSizing: 'border-box', padding: '0.6rem 0.85rem' }}>
                <strong style={{ display: 'block', fontSize: '0.875rem' }}>목소리가 들리지 않아요. 마이크를 확인해 주세요</strong>
                <span style={{ fontSize: '0.8125rem' }}>마이크 권한이나 연결 상태, 음소거 버튼을 확인해 주세요.</span>
              </div>
            )}
            <div style={{ display: 'grid', gap: 6, width: '100%', maxWidth: 280 }}>
              <span className="timer" style={{ fontSize: '2.35rem' }} aria-hidden="true">{fmt(recording ? elapsed : 0).padStart(5, '0')} <small style={{ fontSize: '1.05rem' }}>/ {fmt(RECORD_MAX_MS).padStart(5, '0')}</small></span>
              <div className="rec-progress" aria-hidden="true"><span style={{ width: `${recording ? Math.min(100, (elapsed / RECORD_MAX_MS) * 100) : 0}%` }} /></div>
              <div className="faint" style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem' }}>
                <span>최소 {RECORD_MIN_MS / 1000}초</span><span>최대 {RECORD_MAX_MS / 1000}초 · 시간이 되면 자동 종료</span>
              </div>
            </div>

            {saving
              ? <div style={{ width: 104, height: 104, margin: '8px 0', borderRadius: '50%', display: 'grid', placeItems: 'center', alignContent: 'center', gap: 6, background: 'var(--canvas)', boxShadow: '0 0 0 8px var(--panel)' }}>
                  <span className="spinner" aria-hidden="true" /><span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--primary)' }}>저장 중</span>
                </div>
              : <button className="mic" onClick={toggleRecord} disabled={!canRecord || busyAudio} data-recording={recording} data-silent={silent}
                        data-state={ready ? 'ready' : undefined}
                        style={{ '--lvl': level, width: 104, height: 104, margin: '8px 0' } as CSSProperties}
                        aria-label={recording ? '녹음 마치기' : '녹음 시작'} aria-pressed={recording}>
                  {recording
                    ? <svg width="28" height="28" viewBox="0 0 24 24" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" /></svg>
                    : <svg width="30" height="30" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><rect x="9" y="3" width="6" height="11" rx="3" fill="currentColor" stroke="none" /><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21" /></svg>}
                  <span aria-hidden="true">{recording ? 'STOP' : 'START'}</span>
                </button>}

            <div style={{ display: 'grid', gap: 4 }}>
              <h2 style={{ fontSize: '1.125rem' }}>{headline}</h2>
              {sub && <p className="muted" style={{ fontSize: '0.8125rem' }}>{sub}</p>}
            </div>

            {recording && (
              <div className="panel" style={{ width: '100%', padding: '10px 14px', boxSizing: 'border-box', display: 'grid', gap: 6 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontWeight: 600 }}>
                  <span style={{ color: silent ? '#92400e' : 'var(--rec)' }}>{silent ? '음성 감지 신호 없음' : '실시간 음성 감지 중'}</span>
                  <span className="faint" style={{ fontSize: '0.75rem' }}>입력 {Math.round(level * 100)}%</span>
                </div>
                <MicLevel level={level} active label="실시간 입력 음량" />
              </div>
            )}

            {micError && <p className="notice notice-warn" role="alert" style={{ textAlign: 'left', width: '100%', boxSizing: 'border-box' }}>{micError}</p>}
            {note && <p className={`notice ${note.kind === 'warn' ? 'notice-warn' : ''}`} role={note.kind === 'warn' ? 'alert' : undefined}
                        style={{ textAlign: 'left', width: '100%', boxSizing: 'border-box' }}>{note.text}</p>}
            {phase === 'uploading' && <p className="faint">새로고침하거나 창을 닫으면 아직 보내지 못한 녹음이 사라질 수 있어요.</p>}
            {phase === 'upload_failed' && (
              <div className="notice notice-warn" role="alert" style={{ textAlign: 'left', width: '100%', boxSizing: 'border-box' }}>
                <p style={{ marginBottom: 8 }}>네트워크 문제로 답변을 보내지 못했어요. 녹음은 이 화면에 보관되어 있어요. 새로고침하면 사라질 수 있어요.</p>
                <button className="btn" onClick={() => pendingUpload.current && upload(pendingUpload.current)} autoFocus>다시 보내기</button>
              </div>
            )}
            {phase === 'failed' && <button className="btn" onClick={retryProcessing} autoFocus>다시 처리</button>}
            {phase === 'fatal' && <button className="btn btn-ghost" onClick={() => load()}>다시 불러오기</button>}
          </section>
        </div>

        <section className="sheet" style={{ padding: '10px 16px', display: 'grid', gap: 8 }} aria-label="문항 동작">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <span className="faint" style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontSize: '0.8125rem' }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><path d="M3 14v-2a9 9 0 0 1 18 0v2" /><rect x="3" y="14" width="4" height="6" rx="1.5" /><rect x="17" y="14" width="4" height="6" rx="1.5" /></svg>
              답변을 저장하면 자동으로 다음 문항으로 넘어가요.
            </span>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {q && (
                <button className="btn btn-ghost" style={{ minHeight: 38, padding: '0 1rem', fontSize: '0.875rem' }} onClick={() => setConfirmSkip(true)} disabled={!canSkip || confirmSkip}
                        aria-expanded={confirmSkip} aria-controls="skip-confirm">
                  이 문항 건너뛰기
                </button>
              )}
              <button className="btn btn-rec" style={{ minHeight: 38, padding: '0 1rem', fontSize: '0.875rem' }} onClick={toggleRecord} disabled={!recording}>
                <span className="rec-dot" aria-hidden="true" style={{ animation: recording ? undefined : 'none' }} />답변 완료 및 저장
              </button>
            </div>
          </div>
          {confirmSkip && canSkip && q && (
            <div id="skip-confirm" className="notice" role="alertdialog" aria-labelledby="skip-h">
              <p id="skip-h" style={{ marginBottom: 8 }}>
                {q.is_scored
                  ? '이 문항을 건너뛸까요? 답변 없이 다음 문항으로 넘어가고, 이 문항은 채점에 쓰이지 않아요. 건너뛴 문항이 많으면 예상 등급을 내지 못할 수 있어요.'
                  : '이 문항을 건너뛸까요? 연습 문항이라 채점에는 영향이 없어요.'}
              </p>
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="btn" onClick={skip} autoFocus>건너뛰기</button>
                <button className="btn btn-ghost" onClick={() => setConfirmSkip(false)}>계속 답하기</button>
              </div>
            </div>
          )}
        </section>
      </div>
      <Live>{status}</Live>
    </Shell>
  );
}
