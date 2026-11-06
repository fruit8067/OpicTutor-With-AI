// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// OWNER: frontend (contracts.yaml ownership)
import type { ReactNode } from 'react';
import { loadNickname } from '../lib/session';

export function Shell({ children, wide = false, aside }: { children: ReactNode; wide?: boolean; aside?: ReactNode }) {
  const nick = loadNickname();
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header style={{ borderBottom: '1px solid var(--line)', background: 'var(--sheet)' }}>
        <div style={{ maxWidth: wide ? 1200 : 960, margin: '0 auto', padding: '0.75rem 1.25rem', display: 'flex',
                      alignItems: 'center', justifyContent: 'space-between', gap: 16 }}>
          <span style={{ fontWeight: 700, color: 'var(--teal-deep)' }}>OpicTutor <span className="faint" style={{ fontWeight: 400 }}>모의 인터뷰</span></span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            {aside}
            {nick && <span className="faint">{nick} 님</span>}
          </div>
        </div>
      </header>
      <main style={{ flex: 1, width: '100%', maxWidth: wide ? 1200 : 960, margin: '0 auto', padding: '2rem 1.25rem 4rem', boxSizing: 'border-box' }}>
        {children}
      </main>
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
