// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// OWNER: frontend (contracts.yaml ownership)
// 준비 완료: [시험 시작] 클릭에서 오디오 잠금 해제(unlock) 후 S5 → /exam.
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getSession, startSession } from '../api/client';
import type { SessionOut } from '../api/types';
import { ErrorNote, Shell } from '../components/Shell';
import { Host } from '../features/host/Host';
import { usePlayer } from '../lib/player';
import { clearSessionId, loadSessionId, routeFor } from '../lib/session';
import { cancelAndReset } from '../lib/actions';

export default function Ready() {
  const nav = useNavigate();
  const id = loadSessionId();
  const player = usePlayer();
  const [s, setS] = useState<SessionOut | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!id) { nav('/setup', { replace: true }); return; }
    getSession(id).then((cur) => {
      const to = routeFor(cur.status);
      if (!to) { clearSessionId(); nav('/setup', { replace: true }); }
      else if (to !== '/ready') nav(to, { replace: true });
      else setS(cur);
    }).catch(setError);
  }, [id, nav]);

  const start = async () => {
    if (!id) return;
    setBusy(true);
    try {
      await player.unlock();
      await startSession(id);
      nav('/exam');
    } catch (e) { setError(e); } finally { setBusy(false); }
  };

  return (
    <Shell>
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(180px, 260px) 1fr', gap: 40, alignItems: 'center', maxWidth: 880 }}>
        <div style={{ color: 'var(--ink)' }}><Host state="idle" /></div>
        <div style={{ display: 'grid', gap: 18 }}>
          <h1>준비됐어요</h1>
          <ul className="muted" style={{ margin: 0, paddingLeft: '1.2rem', display: 'grid', gap: 6 }}>
            <li>진행자가 질문 {s?.question_count ?? 8}개를 하나씩 영어로 읽어요. 1번 자기소개는 연습용이라 채점하지 않아요.</li>
            <li>질문이 끝나면 마이크 버튼을 눌러 답하고, 다시 눌러 마쳐요. 한 답변은 최대 2분이에요.</li>
            <li>질문 다시 듣기는 문항마다 한 번 할 수 있어요.</li>
            <li>답변이 저장된 뒤에 다음 문항으로 넘어가요. 마지막 문항이 끝나면 전체 답변으로 평가해요.</li>
          </ul>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <button className="btn" onClick={start} disabled={busy || !s} autoFocus>시험 시작</button>
            <button className="btn btn-ghost" onClick={async () => { if (id) await cancelAndReset(id); nav('/setup'); }} disabled={busy}>설정 바꾸기</button>
          </div>
          <p className="faint">시작하면 진행자 음성이 바로 나와요. 스피커나 이어폰 소리를 켜 주세요.</p>
          <ErrorNote error={error} />
        </div>
      </div>
    </Shell>
  );
}
