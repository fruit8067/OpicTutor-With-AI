// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// 후속 수정: Stitch 디자인(로고·고정 헤더·푸터) 적용도 Claude(Anthropic)의 도움으로 작성되었습니다.
// OWNER: frontend (contracts.yaml ownership)
import type { ReactNode } from 'react';
import { loadNickname } from '../lib/session';

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

export function Shell({ children, wide = false, aside }: { children: ReactNode; wide?: boolean; aside?: ReactNode }) {
  const nick = loadNickname();
  const max = wide ? 1280 : 960;
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header style={{ borderBottom: '1px solid var(--line)', background: 'rgba(255,255,255,0.92)', backdropFilter: 'blur(6px)', position: 'sticky', top: 0, zIndex: 10 }}>
        <div style={{ maxWidth: max, margin: '0 auto', padding: '0.85rem 1.5rem', display: 'flex',
                      alignItems: 'center', justifyContent: 'space-between', gap: 16 }}>
          <Logo />
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            {aside}
            {nick && <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>{nick} 님</span>}
          </div>
        </div>
      </header>
      <main style={{ flex: 1, width: '100%', maxWidth: max, margin: '0 auto', padding: '2rem 1.5rem 4rem', boxSizing: 'border-box' }}>
        {children}
      </main>
      <footer style={{ borderTop: '1px solid var(--line)', background: 'var(--panel)' }}>
        <div className="faint" style={{ maxWidth: max, margin: '0 auto', padding: '1.25rem 1.5rem' }}>
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
