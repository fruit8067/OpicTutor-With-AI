// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// OWNER: frontend (contracts.yaml ownership)
// 브라우저에는 session_id와 표시용 닉네임만 둔다. 나머지는 항상 서버에서 다시 읽는다.
import type { session_status, UserOut } from '../api/types';

const KEY = 'opictutor.session_id';
const NICK = 'opictutor.nickname';
const MIC = 'opictutor.mic_device_id';   // AI-assisted(Claude): 설정 화면에서 고른 마이크. 브라우저에만 저장
const TOKEN = 'opictutor.auth_token';
const USER = 'opictutor.auth_user';

function safe<T>(fn: () => T, fallback: T): T {
  try { return fn(); } catch { return fallback; }
}
export const loadSessionId = () => safe(() => localStorage.getItem(KEY), null);
export const saveSessionId = (id: string) => safe(() => localStorage.setItem(KEY, id), undefined);
export const clearSessionId = () => safe(() => localStorage.removeItem(KEY), undefined);
export const loadNickname = () => safe(() => localStorage.getItem(NICK), null) ?? '';
export const saveNickname = (n: string) => safe(() => (n ? localStorage.setItem(NICK, n) : localStorage.removeItem(NICK)), undefined);
export const loadMicId = () => safe(() => localStorage.getItem(MIC), null);
export const saveMicId = (id: string | null) => safe(() => (id ? localStorage.setItem(MIC, id) : localStorage.removeItem(MIC)), undefined);
export const loadAuthToken = () => safe(() => localStorage.getItem(TOKEN), null);
export const saveAuthToken = (t: string | null) => safe(() => (t ? localStorage.setItem(TOKEN, t) : localStorage.removeItem(TOKEN)), undefined);
export const loadAuthUser = (): UserOut | null => safe(() => {
  const raw = localStorage.getItem(USER);
  return raw ? (JSON.parse(raw) as UserOut) : null;
}, null);
export const saveAuth = (token: string, user: UserOut) => {
  const prev = loadAuthUser();
  if (!prev || prev.id !== user.id) {
    clearSessionId();
  }
  saveAuthToken(token);
  saveNickname(user.nickname);
  safe(() => localStorage.setItem(USER, JSON.stringify(user)), undefined);
};
export const clearAuth = () => {
  clearSessionId();
  saveAuthToken(null);
  saveNickname('');
  safe(() => localStorage.removeItem(USER), undefined);
};

/** v3: 리포트 주소에 세션을 담아 여러 시험 결과를 열 수 있게 한다. AI-assisted(Claude). */
export const resultPath = (id: string) => `/result?session_id=${encodeURIComponent(id)}`;

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
