// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// OWNER: frontend (contracts.yaml ownership)
// 앱 시작·새로고침: session_id가 있으면 서버 상태(S2)로 화면을 정한다. 없거나 취소·404면 /login → /setup.
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiError, getSession } from '../api/client';
import { Shell, ErrorNote } from '../components/Shell';
import { clearSessionId, loadNickname, loadSessionId, routeFor } from '../lib/session';

export default function Boot() {
  const nav = useNavigate();
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const id = loadSessionId();
    if (!id) { nav(loadNickname() ? '/setup' : '/login', { replace: true }); return; }
    getSession(id).then((s) => {
      const to = routeFor(s.status);
      if (!to) { clearSessionId(); nav('/setup', { replace: true }); } else nav(to, { replace: true });
    }).catch((e) => {
      if (e instanceof ApiError && e.code === 'SESSION_NOT_FOUND') { clearSessionId(); nav('/setup', { replace: true }); }
      else setError(e);
    });
  }, [nav, attempt]);
  return (
    <Shell>
      <p className="muted" aria-live="polite">시험 상태를 불러오는 중…</p>
      <ErrorNote error={error}><button className="btn btn-ghost" style={{ marginTop: 8 }} onClick={() => { setError(null); setAttempt((a) => a + 1); }}>다시 불러오기</button></ErrorNote>
    </Shell>
  );
}
