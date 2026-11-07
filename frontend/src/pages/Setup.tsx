// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// 후속 수정: 상태 복구 처리는 OpenAI Codex의 도움으로 작성되었습니다.
// 후속 수정: 마이크 장치 선택·음량 막대는 Claude(Anthropic)의 도움으로 작성되었습니다.
// OWNER: frontend (contracts.yaml ownership)
// 설정: 마이크 권한 → 실시간 음량 → 3초 테스트 녹음·재생(업로드 안 함) → 시나리오 선택 → S1.
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiError, createSession, getScenarios, getSession } from '../api/client';
import type { ScenarioOut } from '../api/types';
import { ErrorNote, Live, Shell } from '../components/Shell';
import { MicLevel } from '../components/MicLevel';
import {
  listMics, meter, micErrorKind, openMic, Recorder, SILENCE_PEAK, streamDeviceId, toLevel, type MicDevice, type MicErrorKind,
} from '../lib/recorder';
import { loadMicId, loadSessionId, saveMicId, saveSessionId } from '../lib/session';

const MIC_HELP: Record<MicErrorKind, string> = {
  denied: '마이크 권한이 막혀 있어요. 주소창 왼쪽 자물쇠(또는 사이트 설정) 아이콘 → 마이크 → 허용으로 바꾼 뒤 이 페이지를 새로고침해 주세요. Safari는 설정 → 웹사이트 → 마이크에서 바꿀 수 있어요.',
  not_found: '연결된 마이크를 찾지 못했어요. 마이크(또는 이어폰)를 연결하고 다시 시도해 주세요.',
  unsupported: '이 브라우저는 녹음을 지원하지 않아요. 최신 Chrome·Edge·Firefox·Safari를 사용해 주세요.',
  other: '마이크를 켜지 못했어요. 다른 프로그램이 마이크를 쓰고 있지 않은지 확인해 주세요.',
};

type TestState = 'idle' | 'recording' | 'recorded' | 'passed' | 'quiet';

export default function Setup() {
  const nav = useNavigate();
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [micErr, setMicErr] = useState<MicErrorKind | null>(null);
  const [level, setLevel] = useState(0);
  const [mics, setMics] = useState<MicDevice[]>([]);
  const [test, setTest] = useState<TestState>('idle');
  const [testUrl, setTestUrl] = useState<string | null>(null);
  const [scenarios, setScenarios] = useState<ScenarioOut[] | null>(null);
  const [scenario, setScenario] = useState('default');
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const alive = useRef(true);
  const openingMic = useRef(false);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  const reqId = useRef<string>(crypto.randomUUID());

  useEffect(() => { getScenarios().then(setScenarios).catch(setError); }, []);
  // 권한을 받은 뒤에야 장치 이름이 보인다. 장치를 꽂거나 빼면 목록을 다시 읽는다.
  useEffect(() => {
    if (!stream) return;
    const refresh = () => { listMics().then((m) => { if (alive.current) setMics(m); }).catch(() => {}); };
    refresh();
    navigator.mediaDevices?.addEventListener?.('devicechange', refresh);
    return () => navigator.mediaDevices?.removeEventListener?.('devicechange', refresh);
  }, [stream]);
  useEffect(() => {
    if (!stream) return;
    const stop = meter(stream, setLevel);
    return () => { stop(); };
  }, [stream]);
  useEffect(() => () => { stream?.getTracks().forEach((t) => t.stop()); }, [stream]);
  useEffect(() => () => { if (testUrl) URL.revokeObjectURL(testUrl); }, [testUrl]);

  const enableMic = async () => {
    if (openingMic.current) return;
    openingMic.current = true;
    setMicErr(null);
    try {
      const opened = await openMic(loadMicId());
      if (!alive.current) opened.getTracks().forEach((track) => track.stop());
      else setStream(opened);
    } catch (e) { if (alive.current) setMicErr(micErrorKind(e)); }
    finally { openingMic.current = false; }
  };

  // 다른 마이크로 바꾸면 테스트를 다시 해야 한다.
  const changeMic = async (deviceId: string) => {
    if (openingMic.current || deviceId === micId) return;
    openingMic.current = true;
    setMicErr(null);
    try {
      const opened = await openMic(deviceId);
      if (!alive.current) { opened.getTracks().forEach((t) => t.stop()); return; }
      stream?.getTracks().forEach((t) => t.stop());
      saveMicId(streamDeviceId(opened) ?? deviceId);
      setStream(opened);
      setTest('idle');
      if (testUrl) { URL.revokeObjectURL(testUrl); setTestUrl(null); }
    } catch (e) { if (alive.current) setMicErr(micErrorKind(e)); }
    finally { openingMic.current = false; }
  };

  const runTest = async () => {
    if (!stream) return;
    setTest('recording');
    const rec = new Recorder(stream);
    try {
      const r = await rec.start(3000);
      if (!alive.current) return;
      if (testUrl) URL.revokeObjectURL(testUrl);
      setTestUrl(URL.createObjectURL(r.blob));
      setTest(r.peak < SILENCE_PEAK ? 'quiet' : 'recorded');
    } catch {
      stream.getTracks().forEach((t) => t.stop());
      if (alive.current) { setStream(null); setMicErr('other'); setTest('idle'); }
    }
  };

  const submit = async () => {
    setBusy(true); setError(null);
    try {
      const prev = loadSessionId();
      let replaces: string | null = null;
      if (prev) {
        try {
          const s = await getSession(prev);
          if (['preparing', 'ready', 'prepare_failed'].includes(s.status)) replaces = prev;
          else if (s.status !== 'cancelled') { nav('/', { replace: true }); return; }  // 진행 중 시험이 있으면 그 화면으로
        } catch (e) {
          // 조회가 실패한 상태에서 진행 중 세션을 덮어 만들지 않는다.
          if (!(e instanceof ApiError) || e.code !== 'SESSION_NOT_FOUND') throw e;
        }
      }
      const s = await createSession({ client_request_id: reqId.current, scenario_id: scenario, mic_check_passed: true,
                                      replaces_session_id: replaces });
      saveMicId(streamDeviceId(stream));
      stream?.getTracks().forEach((t) => t.stop());
      saveSessionId(s.session_id);
      nav('/prepare');
    } catch (e) {
      setError(e);
      if (e instanceof ApiError && e.code === 'SCENARIO_UNAVAILABLE') reqId.current = crypto.randomUUID();
    } finally { setBusy(false); }
  };

  const micOk = test === 'passed';
  const micId = streamDeviceId(stream);
  return (
    <Shell>
      <div style={{ display: 'grid', gap: 32, maxWidth: 720 }}>
        <div style={{ display: 'grid', gap: 8 }}>
          <h1>시험 전에 확인할게요</h1>
          <p className="muted prose-w">마이크로 답변을 녹음해요. 테스트 녹음은 이 브라우저에서만 재생하고 서버로 보내지 않아요.</p>
        </div>

        <section className="sheet" style={{ padding: 24, display: 'grid', gap: 16 }} aria-labelledby="mic-h">
          <h2 id="mic-h">1. 마이크</h2>
          {!stream ? (
            <div style={{ display: 'grid', gap: 12, justifyItems: 'start' }}>
              <button className="btn" onClick={enableMic}>마이크 켜기</button>
              {micErr && <p className="notice notice-warn" role="alert">{MIC_HELP[micErr]}</p>}
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 14 }}>
              {mics.length > 0 && (
                <label className="field" style={{ maxWidth: 420 }}>
                  <span>사용할 마이크</span>
                  <select className="input" value={micId ?? ''} onChange={(e) => void changeMic(e.target.value)}>
                    {!mics.some((m) => m.deviceId === micId) && <option value={micId ?? ''}>기본 마이크</option>}
                    {mics.map((m) => <option key={m.deviceId} value={m.deviceId}>{m.label}</option>)}
                  </select>
                </label>
              )}
              <div style={{ display: 'grid', gap: 6 }}>
                <span className="faint">입력 음량 — 아무 말이나 해 보세요. 말할 때 막대가 움직이면 정상이에요.</span>
                <MicLevel level={toLevel(level)} active variant="test" label="입력 음량" />
              </div>
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
                <button className="btn btn-ghost" onClick={runTest} disabled={test === 'recording'}>
                  {test === 'recording' ? '3초 녹음 중…' : test === 'idle' ? '3초 테스트 녹음' : '다시 테스트'}
                </button>
                {testUrl && test !== 'recording' && <audio src={testUrl} controls aria-label="테스트 녹음 재생" />}
              </div>
              {test === 'quiet' && <p className="notice notice-warn" role="alert">소리가 거의 녹음되지 않았어요. 마이크 가까이에서 다시 테스트해 주세요.</p>}
              {(test === 'recorded' || test === 'passed') && (
                <label style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <input type="checkbox" checked={micOk} onChange={(e) => setTest(e.target.checked ? 'passed' : 'recorded')} />
                  <span>녹음한 내 목소리가 또렷하게 들려요</span>
                </label>
              )}
            </div>
          )}
        </section>

        <section className="sheet" style={{ padding: 24, display: 'grid', gap: 12 }} aria-labelledby="sc-h">
          <h2 id="sc-h">2. 시험 구성</h2>
          {!scenarios ? <p className="muted">구성 목록을 불러오는 중…</p> : (
            <fieldset disabled={busy} style={{ border: 0, padding: 0, margin: 0, display: 'grid', gap: 8 }}>
              <legend className="sr-only">시험 구성 선택</legend>
              {scenarios.map((sc) => (
                <label key={sc.scenario_id} style={{ display: 'flex', gap: 12, alignItems: 'flex-start', padding: '10px 12px',
                  border: `1.5px solid ${scenario === sc.scenario_id ? 'var(--teal)' : 'var(--line)'}`, borderRadius: 'var(--radius-s)', cursor: 'pointer',
                  background: scenario === sc.scenario_id ? 'var(--teal-wash)' : 'var(--sheet)' }}>
                  <input type="radio" name="scenario" value={sc.scenario_id} checked={scenario === sc.scenario_id}
                         onChange={() => { if (scenario !== sc.scenario_id) reqId.current = crypto.randomUUID(); setScenario(sc.scenario_id); }} style={{ marginTop: 6 }} />
                  <span><strong>{sc.label}</strong> <span className="faint">{sc.question_count}문항</span><br /><span className="muted">{sc.description}</span></span>
                </label>
              ))}
            </fieldset>
          )}
        </section>

        <div style={{ display: 'grid', gap: 8, justifyItems: 'start' }}>
          <button className="btn" onClick={submit} disabled={!micOk || busy || !scenarios}>
            {busy ? '시험 준비를 요청하는 중…' : '이 설정으로 시험 준비하기'}
          </button>
          {!micOk && <p className="faint">마이크 테스트를 마치고 소리가 잘 들리는지 확인해야 시작할 수 있어요.</p>}
          <ErrorNote error={error} />
        </div>
        <Live>{test === 'recording' ? '테스트 녹음 중' : test === 'recorded' ? '테스트 녹음 완료. 재생해서 확인해 주세요' : ''}</Live>
      </div>
    </Shell>
  );
}
