// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// 후속 수정: Stitch 디자인(로고·고정 헤더·푸터) 및 단계별 상단 네비게이션·로그아웃 통합을 적용했습니다.
// 후속 수정: v3 분석 중 화면 이동(메뉴 경로), 헤더 "분석 중" 배지, 리포트 준비 토스트는 Claude(Anthropic)의 도움으로 작성되었습니다.
// OWNER: frontend (contracts.yaml ownership)
import type { ReactNode } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { logoutUser } from '../api/client';
import { clearAuth, clearSessionId, loadAuthUser, loadNickname, resultPath, saveSessionId } from '../lib/session';
import { dismissToast, useActiveSessions, waitingItems } from '../lib/useActiveSessions';

export function Logo() {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10, fontWeight: 700, fontSize: '1.0625rem', letterSpacing: '-0.02em', color: 'var(--ink)' }}>
      <span aria-hidden="true" style={{ width: 32, height: 32, borderRadius: 9, background: 'var(--primary)', display: 'grid', placeItems: 'center' }}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round"><rect x="9" y="3" width="6" height="11" rx="3" fill="#fff" stroke="none" /><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21" /></svg>
      </span>
      OpicTutor
    </span>
  );
}

// to: 고정 경로. exam·result는 서버의 활성 세션 정보로 경로를 정한다(없으면 이동 불가).
const NAV_STEPS: { key: string; label: string; paths: string[]; to: string | null }[] = [
  { key: 'setup', label: '환경 점검', paths: ['/setup', '/prepare', '/ready'], to: '/setup' },
  { key: 'exam', label: '실전 인터뷰', paths: ['/exam'], to: null },
  { key: 'result', label: 'AI 피드백 리포트', paths: ['/result'], to: null },
  { key: 'history', label: '내 시험 기록', paths: ['/history'], to: '/history' },
];

export function Shell({ children, wide = false, compact = false, aside }: { children: ReactNode; wide?: boolean; compact?: boolean; aside?: ReactNode }) {
  const nav = useNavigate();
  const loc = useLocation();
  const user = loadAuthUser();
  const nick = user?.nickname || loadNickname();
  const max = wide ? 1280 : 960;
  const inExam = loc.pathname === '/exam';
  const { data: active, toasts } = useActiveSessions();
  const waiting = waitingItems(active);
  const examId = active?.in_progress_session_id ?? null;
  const reportId = active?.latest_report_session_id ?? null;
  const go = (key: string, to: string | null) => {
    if (key === 'exam' && examId) { saveSessionId(examId); nav('/exam'); return; }
    if (key === 'result' && reportId) { nav(resultPath(reportId)); return; }
    if (to) nav(to);
  };
  const targetOf = (key: string, to: string | null) => (key === 'exam' ? (examId ? '/exam' : null) : key === 'result' ? (reportId ? 'r' : null) : to);

  const onLogout = async () => {
    try { await logoutUser(); } catch { /* 네트워크/만료 무시 */ }
    clearAuth();
    clearSessionId();
    nav('/login', { replace: true });
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header className="no-print" style={{ borderBottom: '1px solid var(--line)', background: 'rgba(255,255,255,0.92)', backdropFilter: 'blur(8px)', position: 'sticky', top: 0, zIndex: 20 }}>
        <div style={{ maxWidth: max, margin: '0 auto', padding: compact ? '0.55rem 1.5rem' : '0.8rem 1.5rem', display: 'flex',
                      alignItems: 'center', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap' }}>
            <Logo />
            <nav aria-label="진행 단계" className="shell-nav">
              {NAV_STEPS.map((st, idx) => {
                const active = st.paths.includes(loc.pathname);
                // 시험 화면에서는 녹음 흐름을 지키려고 메뉴 이동을 막는다. 분석·채점 중에는 자유롭게 이동할 수 있다.
                const clickable = !!targetOf(st.key, st.to) && !inExam && !active;
                if (clickable) {
                  return (
                    <button
                      key={st.key}
                      type="button"
                      onClick={() => go(st.key, st.to)}
                      className={`shell-nav-item ${active ? 'active' : ''}`}
                      style={{ border: 0, background: 'transparent', cursor: 'pointer', fontFamily: 'inherit' }}
                    >
                      <span className="shell-nav-num" aria-hidden="true">{idx + 1}</span>
                      {st.label}
                    </button>
                  );
                }
                return (
                  <span
                    key={st.key}
                    aria-current={active ? 'page' : undefined}
                    className={`shell-nav-item ${active ? 'active' : ''}`}
                  >
                    <span className="shell-nav-num" aria-hidden="true">{idx + 1}</span>
                    {st.label}
                  </span>
                );
              })}
            </nav>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {waiting.length > 0 && (
              <button type="button" className="chip chip-soft shell-analyzing" disabled={inExam}
                      onClick={() => nav(waiting.length === 1 ? resultPath(waiting[0].session_id) : '/history')}
                      title="답변 분석·AI 채점이 서버에서 진행 중이에요. 다른 화면으로 이동해도 계속돼요.">
                <span className="spinner spinner-xs" aria-hidden="true" />분석 중 {waiting.length}
              </button>
            )}
            {aside}
            {nick && (
              <span className="shell-user-badge" title={user?.email ?? undefined}>
                <span className="shell-user-avatar" aria-hidden="true">{nick.slice(0, 1).toUpperCase()}</span>
                <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{nick} 님</span>
              </span>
            )}
            {(nick || user) && (
              <button
                type="button"
                className="btn-quiet"
                style={{ minHeight: 32, padding: '0 0.65rem', fontSize: '0.8125rem', color: 'var(--ink-soft)', borderRadius: 8 }}
                onClick={() => void onLogout()}
              >
                로그아웃
              </button>
            )}
          </div>
        </div>
      </header>
      <main style={{ flex: 1, width: '100%', maxWidth: max, margin: '0 auto', padding: compact ? '0.75rem 1.5rem 0.75rem' : '2rem 1.5rem 4rem', boxSizing: 'border-box' }}>
        {children}
      </main>
      {toasts.length > 0 && (
        <div className="toast-stack no-print" role="region" aria-label="알림">
          {toasts.map((t) => (
            <div key={t.session_id} className={`toast ${t.ok ? '' : 'toast-warn'}`} role="status">
              <span style={{ fontWeight: 700 }}>{t.ok ? '리포트가 준비됐어요' : '평가를 마치지 못했어요'}</span>
              <span className="faint" style={{ fontSize: '0.8125rem' }}>{t.ok ? 'AI 피드백 리포트를 확인해 보세요.' : '리포트 화면에서 다시 평가할 수 있어요.'}</span>
              <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                <button type="button" className="btn" style={{ minHeight: 32, padding: '0 0.85rem', fontSize: '0.8125rem' }} disabled={inExam}
                        onClick={() => { dismissToast(t.session_id); nav(resultPath(t.session_id)); }}>
                  {t.ok ? '리포트 보기' : '확인하기'}
                </button>
                <button type="button" className="btn btn-ghost" style={{ minHeight: 32, padding: '0 0.85rem', fontSize: '0.8125rem' }}
                        onClick={() => dismissToast(t.session_id)} aria-label="알림 닫기">닫기</button>
              </div>
            </div>
          ))}
        </div>
      )}
      <footer className="no-print" style={{ borderTop: '1px solid var(--line)', background: 'var(--panel)' }}>
        <div className="faint" style={{ maxWidth: max, margin: '0 auto', padding: compact ? '0.6rem 1.5rem' : '1.25rem 1.5rem', fontSize: compact ? '0.75rem' : undefined }}>
          OpicTutor · AI 기반 오픽 모의 인터뷰. 예상 등급은 참고용이며 공식 성적이 아니에요.
        </div>
      </footer>
    </div>
  );
}

export function Rail({ total, current, doneUpTo }: { total: number; current: number; doneUpTo: number }) {
  return (
    <ol className="rail" aria-label={`${total}문항 중 ${Math.min(current, total)}번째`} style={{ listStyle: 'none', margin: 0, padding: 0 }}>
      {Array.from({ length: total }, (_, i) => i + 1).map((n) => (
        <li key={n} style={{ display: 'flex', alignItems: 'center' }}>
          {n > 1 && <span className="rail-gap" aria-hidden="true" />}
          <span className="rail-step" data-state={n <= doneUpTo ? 'done' : n === current ? 'current' : 'todo'}
                aria-current={n === current ? 'step' : undefined}>{n}</span>
        </li>
      ))}
    </ol>
  );
}

export function Live({ children }: { children: ReactNode }) {
  return <p className="sr-only" aria-live="polite" role="status">{children}</p>;
}

export function ErrorNote({ error, children }: { error: unknown; children?: ReactNode }) {
  if (!error) return null;
  const msg = (error as { message?: string })?.message ?? '잠시 후 다시 시도해 주세요.';
  return (
    <div className="notice notice-warn" role="alert" style={{ marginTop: 12 }}>
      <p>{msg}</p>
      {children}
    </div>
  );
}
