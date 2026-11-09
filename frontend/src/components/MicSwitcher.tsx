// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// OWNER: frontend (contracts.yaml ownership)
// 시험 중 상시 대기하는 "마이크 변경·테스트" 비상 버튼.
// 패널을 열면 연결된 마이크 목록과 실시간 음량을 보여 주고, [이 마이크로 사용]을 누르면 시험 화면이 쓰는 스트림을 바꾼다.
// 패널이 연 테스트 스트림은 [사용]을 누르면 시험 화면으로 넘기고(소유권 이전), 그냥 닫으면 정리한다.
import { useCallback, useEffect, useRef, useState } from 'react';
import { MicLevel } from './MicLevel';
import { listMics, meter, micErrorKind, openMic, streamDeviceId, toLevel, watchMicDevices, type MicDevice } from '../lib/recorder';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** 시험 화면이 지금 쓰는 장치 ID(아직 마이크를 열지 않았으면 저장된 ID) */
  activeDeviceId: string | null;
  /** 시험 화면이 지금 쓰는 장치 이름 */
  activeLabel: string;
  /** 녹음 중이면 [사용] 시 지금 녹음을 버린다는 안내를 보여 준다 */
  recording: boolean;
  /** 버튼 위에 띄울 경고(마이크 분리·새 마이크 연결 등). null이면 없음 */
  alert: string | null;
  /** 테스트를 마친 새 스트림을 넘긴다. 받은 쪽이 이전 스트림을 정리한다. */
  onUse: (stream: MediaStream) => void;
}

const ERR_TEXT: Record<string, string> = {
  denied: '마이크 권한이 꺼져 있어요. 주소창의 사이트 설정에서 마이크를 허용해 주세요.',
  not_found: '이 마이크를 찾지 못했어요. 연결을 확인하거나 다른 마이크를 골라 주세요.',
  unsupported: '이 브라우저는 녹음을 지원하지 않아요.',
  other: '마이크를 켜지 못했어요. 다시 시도해 주세요.',
};

export function MicSwitcher({ open, onOpenChange, activeDeviceId, activeLabel, recording, alert, onUse }: Props) {
  const [mics, setMics] = useState<MicDevice[]>([]);
  const [picked, setPicked] = useState<string | null>(null);
  const [test, setTest] = useState<MediaStream | null>(null);
  const [level, setLevel] = useState(0);
  const [err, setErr] = useState<string | null>(null);
  const [opening, setOpening] = useState(false);
  const testRef = useRef<MediaStream | null>(null);
  const handedOver = useRef<MediaStream | null>(null);
  const seq = useRef(0);

  const refresh = useCallback(() => { listMics().then(setMics).catch(() => {}); }, []);

  // 테스트 스트림 교체: 이전 테스트 스트림은 넘겨준 것이 아니면 닫는다.
  const replaceTest = useCallback((next: MediaStream | null) => {
    const prev = testRef.current;
    if (prev && prev !== handedOver.current && prev !== next) prev.getTracks().forEach((t) => t.stop());
    testRef.current = next;
    setTest(next);
  }, []);

  const openTest = useCallback(async (deviceId: string | null) => {
    const my = ++seq.current;
    setOpening(true); setErr(null);
    try {
      const s = await openMic(deviceId);
      if (my !== seq.current) { s.getTracks().forEach((t) => t.stop()); return; }
      replaceTest(s);
      setPicked(streamDeviceId(s) ?? deviceId);
      refresh();                                   // 권한을 받은 뒤라 장치 이름이 채워진다
    } catch (e) {
      if (my === seq.current) { replaceTest(null); setErr(ERR_TEXT[micErrorKind(e)]); }
    } finally { if (my === seq.current) setOpening(false); }
  }, [refresh, replaceTest]);

  // 패널을 열면 목록을 읽고 현재 마이크로 테스트를 시작한다. 닫으면 테스트 스트림을 정리한다.
  useEffect(() => {
    if (!open) { seq.current++; replaceTest(null); setErr(null); setLevel(0); return; }
    handedOver.current = null;
    refresh();
    void openTest(activeDeviceId);
    return watchMicDevices(refresh);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  useEffect(() => () => { seq.current++; const s = testRef.current; if (s && s !== handedOver.current) s.getTracks().forEach((t) => t.stop()); }, []);

  useEffect(() => {
    if (!test) { setLevel(0); return; }
    return meter(test, (rms) => setLevel(toLevel(rms)));
  }, [test]);

  // 테스트 중 장치가 뽑히면 바로 알려 준다.
  useEffect(() => {
    if (!test) return;
    const tracks = test.getAudioTracks();
    const ended = () => { setErr('테스트 중인 마이크 연결이 끊어졌어요. 다른 마이크를 골라 주세요.'); replaceTest(null); };
    tracks.forEach((t) => t.addEventListener('ended', ended, { once: true }));
    return () => tracks.forEach((t) => t.removeEventListener('ended', ended));
  }, [test, replaceTest]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onOpenChange(false); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onOpenChange]);

  const use = () => {
    if (!test) return;
    handedOver.current = test;
    onUse(test);
    onOpenChange(false);
  };

  const pickedIsActive = !!picked && picked === activeDeviceId;
  const voice = level >= 0.09;

  return (
    <div className="mic-switch no-print">
      {open && (
        <div className="mic-panel sheet" role="dialog" aria-modal="false" aria-labelledby="mic-panel-h">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
            <h2 id="mic-panel-h" style={{ fontSize: '1rem' }}>마이크 변경 · 테스트</h2>
            <button type="button" className="btn btn-quiet" style={{ minHeight: 30, padding: '0 0.5rem' }} onClick={() => onOpenChange(false)} aria-label="마이크 패널 닫기">닫기</button>
          </div>
          {alert && <p className="notice notice-warn" role="alert" style={{ fontSize: '0.8125rem', padding: '0.55rem 0.75rem' }}>{alert}</p>}
          <p className="faint" style={{ fontSize: '0.78rem' }}>지금 사용 중: <strong style={{ color: 'var(--ink)' }}>{activeLabel || '기본 마이크'}</strong></p>

          <fieldset style={{ border: 0, margin: 0, padding: 0, display: 'grid', gap: 6 }}>
            <legend className="faint" style={{ fontSize: '0.75rem', fontWeight: 600, marginBottom: 4 }}>연결된 마이크 {mics.length}개</legend>
            {mics.length === 0 && <span className="faint" style={{ fontSize: '0.8125rem' }}>마이크를 찾는 중이에요…</span>}
            {mics.map((m) => (
              <label key={m.deviceId} className="mic-option" data-checked={picked === m.deviceId}>
                <input type="radio" name="mic-pick" value={m.deviceId} checked={picked === m.deviceId} disabled={opening}
                       onChange={() => { setPicked(m.deviceId); void openTest(m.deviceId); }} />
                <span style={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{m.label}</span>
                {m.deviceId === activeDeviceId && <span className="chip chip-soft" style={{ minHeight: 18, padding: '0 0.4rem', fontSize: '0.65rem' }}>사용 중</span>}
              </label>
            ))}
          </fieldset>
          <button type="button" className="btn btn-quiet" style={{ justifySelf: 'start', minHeight: 30, padding: '0 0.5rem', fontSize: '0.8125rem' }} onClick={refresh}>목록 새로고침</button>

          <div className="panel" style={{ padding: '8px 12px', display: 'grid', gap: 4 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontWeight: 600 }}>
              <span style={{ color: voice ? 'var(--primary)' : 'var(--ink-faint)' }}>{opening ? '마이크 여는 중…' : test ? (voice ? '소리가 들어와요' : '말해 보세요 — 막대가 움직이면 정상이에요') : '테스트 대기'}</span>
              <span className="faint">{Math.round(level * 100)}%</span>
            </div>
            <MicLevel level={level} active={!!test} label="테스트 중인 마이크 음량" variant="test" />
          </div>
          {err && <p className="notice notice-warn" role="alert" style={{ fontSize: '0.8125rem', padding: '0.55rem 0.75rem' }}>{err}</p>}
          {recording && <p className="faint" style={{ fontSize: '0.75rem', color: '#92400e' }}>녹음 중이에요. 마이크를 바꾸면 지금 녹음은 버리고, 같은 문항을 새 마이크로 다시 답해요.</p>}
          <button type="button" className="btn" onClick={use} disabled={!test || opening}>
            {pickedIsActive ? '이 마이크로 계속 사용' : recording ? '녹음 버리고 이 마이크로 바꾸기' : '이 마이크로 사용'}
          </button>
        </div>
      )}
      <button type="button" className="mic-fab" data-alert={!!alert} onClick={() => onOpenChange(!open)} aria-expanded={open}
              aria-label={alert ? `마이크 변경·테스트 (${alert})` : '마이크 변경·테스트'}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21" /></svg>
        <span>마이크 변경·테스트</span>
        {alert && <span className="mic-fab-dot" aria-hidden="true" />}
      </button>
    </div>
  );
}
