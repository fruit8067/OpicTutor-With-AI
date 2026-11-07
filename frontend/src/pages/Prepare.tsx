// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// 후속 수정: 상태 복구 처리는 OpenAI Codex의 도움으로 작성되었습니다.
// OWNER: frontend (contracts.yaml ownership)
// 준비: S2 2초 폴링. linked/total, prepare_failed면 실패 목록 + 같은 세트로 다시 준비(S3) / 설정 바꾸기(S4).
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiError, getSession, retryPrepare } from '../api/client';
import type { SessionOut } from '../api/types';
import { ErrorNote, Live, Shell } from '../components/Shell';
import { labelOf, PREPARE_ERROR_TEXT } from '../lib/messages';
import { clearSessionId, loadSessionId, routeFor } from '../lib/session';
import { usePoll } from '../lib/usePoll';
import { cancelAndReset } from '../lib/actions';

const HOST_KEY_LABEL: Record<string, string> = { greeting: '인사', say_again: '다시 말해 달라는 안내', next: '다음 문항 안내', finish: '종료 인사' };

export default function Prepare() {
  const nav = useNavigate();
  const id = loadSessionId();
  const [s, setS] = useState<SessionOut | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  usePoll(async () => {
    if (!id) { nav('/setup', { replace: true }); return false; }
    try {
      const cur = await getSession(id);
      setS(cur); setError(null);
      const to = routeFor(cur.status);
      if (!to) { clearSessionId(); nav('/setup', { replace: true }); return false; }
      if (to !== '/prepare') { nav(to, { replace: true }); return false; }
      return cur.status === 'preparing';
    } catch (e) {
      if (e instanceof ApiError && e.code === 'SESSION_NOT_FOUND') { clearSessionId(); nav('/setup', { replace: true }); return false; }
      setError(e); return true;
    }
  }, 2000, !!id && (!s || s.status === 'preparing'));

  const retry = async () => {
    if (!id) return;
    setBusy(true);
    try {
      const updated = await retryPrepare(id);
      setS(updated); setError(null);
      const to = routeFor(updated.status);
      if (to && to !== '/prepare') nav(to, { replace: true });
    } catch (e) { setError(e); } finally { setBusy(false); }
  };
  const change = async () => { if (id) await cancelAndReset(id); nav('/setup'); };

  const p = s?.prepare;
  const pct = p && p.total ? Math.round((p.linked / p.total) * 100) : 0;
  const failed = s?.status === 'prepare_failed';
  return (
    <Shell>
      <div style={{ display: 'grid', gap: 24, maxWidth: 680 }}>
        <h1>{failed ? '시험 음성을 준비하지 못했어요' : '진행자 음성을 준비하고 있어요'}</h1>
        {!failed && (
          <div style={{ display: 'grid', gap: 8 }}>
            <div className="progress" role="progressbar" aria-valuemin={0} aria-valuemax={p?.total ?? 0} aria-valuenow={p?.linked ?? 0}
                 aria-label="음성 연결 진행"><span style={{ width: `${pct}%` }} /></div>
            <p className="muted">{p ? `${p.linked} / ${p.total}개 연결됨` : '문항과 진행자 대사를 확인하는 중…'}</p>
            <p className="faint">문항 8개와 진행자 대사가 모두 준비되면 자동으로 다음 화면으로 넘어가요.</p>
          </div>
        )}
        {failed && (
          <div style={{ display: 'grid', gap: 16 }}>
            <p className="muted prose-w">아래 음성이 없거나 오래된 버전이에요. 운영자가 음성을 다시 만들어 반입한 뒤 <strong>같은 문항 세트로</strong> 다시 준비할 수 있어요. 문항이 다른 것으로 바뀌지는 않아요.</p>
            <ul className="sheet" style={{ margin: 0, padding: '8px 0', listStyle: 'none' }}>
              {(p?.failures ?? []).map((f, i) => (
                <li key={i} style={{ padding: '10px 16px', borderTop: i ? '1px solid var(--line)' : 'none', display: 'grid', gap: 2 }}>
                  <strong>{f.order_no != null ? `${f.order_no}번 문항` : f.host_key ? `진행자 대사 · ${HOST_KEY_LABEL[f.host_key] ?? f.host_key}` : '음성 설정'}</strong>
                  <span className="muted">{labelOf(PREPARE_ERROR_TEXT, f.error_code)} <span className="faint">({f.error_code})</span></span>
                </li>
              ))}
            </ul>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <button className="btn" onClick={retry} disabled={busy}>같은 세트로 다시 준비</button>
              <button className="btn btn-ghost" onClick={change} disabled={busy}>설정 바꾸기</button>
            </div>
          </div>
        )}
        <ErrorNote error={error} />
        <Live>{failed ? '준비 실패. 다시 준비하거나 설정을 바꿀 수 있어요' : p ? `${p.linked}/${p.total} 연결` : ''}</Live>
      </div>
    </Shell>
  );
}
