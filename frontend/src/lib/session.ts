// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// OWNER: frontend (contracts.yaml ownership)
// 브라우저에는 session_id와 표시용 닉네임만 둔다. 나머지는 항상 서버에서 다시 읽는다.
import type { session_status } from '../api/types';

const KEY = 'opictutor.session_id';
const NICK = 'opictutor.nickname';

function safe<T>(fn: () => T, fallback: T): T {
  try { return fn(); } catch { return fallback; }
}
export const loadSessionId = () => safe(() => localStorage.getItem(KEY), null);
export const saveSessionId = (id: string) => safe(() => localStorage.setItem(KEY, id), undefined);
export const clearSessionId = () => safe(() => localStorage.removeItem(KEY), undefined);
export const loadNickname = () => safe(() => localStorage.getItem(NICK), null) ?? '';
export const saveNickname = (n: string) => safe(() => (n ? localStorage.setItem(NICK, n) : localStorage.removeItem(NICK)), undefined);

/** 세션 상태 → 화면 경로 (frontend.yaml 2번 라우팅 표). null이면 세션 삭제 후 /setup */
export function routeFor(status: session_status): string | null {
  switch (status) {
    case 'preparing':
    case 'prepare_failed': return '/prepare';
    case 'ready': return '/ready';
    case 'in_progress': return '/exam';
    case 'submitted':
    case 'grading':
    case 'grading_failed':
    case 'done': return '/result';
    case 'cancelled': return null;
  }
}
