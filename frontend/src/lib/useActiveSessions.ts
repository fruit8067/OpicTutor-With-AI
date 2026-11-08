// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// OWNER: frontend (contracts.yaml ownership)
//
// v3 전역 분석 상태(H2 GET /sessions/active). 페이지마다 Shell이 새로 마운트되므로 상태는 모듈 단위 저장소 하나에 둔다.
// - 화면이 붙을 때 한 번 읽고, 분석·채점 중인 세션이 있을 때만 5초마다 다시 읽는다. 없으면 멈춘다.
// - 대기 중으로 본 세션이 recent_finished에 나타나면 완료/실패 알림(토스트, 허용 시 브라우저 알림)을 한 번 띄운다.
// - 로그인하지 않았거나 요청이 실패하면 조용히 빈 상태로 둔다(헤더 기능만 빠지고 화면은 그대로 동작).
import { useEffect, useSyncExternalStore } from 'react';
import { getActiveSessions } from '../api/client';
import type { ActiveSessionItemOut, ActiveSessionsOut } from '../api/types';
import { loadAuthToken } from './session';

export type ReportToast = { session_id: string; ok: boolean };
type State = { data: ActiveSessionsOut | null; toasts: ReportToast[] };

const POLL_MS = 5000;
const SEEN_KEY = 'opictutor.waiting_sessions';     // 새로고침 뒤에도 완료 알림을 이어 가기 위한 탭 단위 기록
const DONE_KEY = 'opictutor.notified_sessions';

let state: State = { data: null, toasts: [] };
const listeners = new Set<() => void>();
let subscribers = 0;
let timer = 0;
let inflight = false;
let lastFetch = 0;

const emit = (next: Partial<State>) => { state = { ...state, ...next }; listeners.forEach((l) => l()); };

function readSet(key: string): Set<string> {
  try { return new Set(JSON.parse(sessionStorage.getItem(key) ?? '[]') as string[]); } catch { return new Set(); }
}
function writeSet(key: string, value: Set<string>) {
  try { sessionStorage.setItem(key, JSON.stringify([...value].slice(-50))); } catch { /* 저장 불가 환경은 무시 */ }
}

export const isWaiting = (s: { status: string }) => s.status === 'submitted' || s.status === 'grading';

function notifyBrowser(ok: boolean) {
  try {
    if (typeof Notification === 'undefined' || Notification.permission !== 'granted' || document.visibilityState === 'visible') return;
    new Notification(ok ? 'OpicTutor 리포트가 준비됐어요' : 'OpicTutor 평가를 마치지 못했어요',
      { body: ok ? '모의 인터뷰 AI 피드백 리포트를 확인해 보세요.' : '리포트 화면에서 다시 평가할 수 있어요.' });
  } catch { /* 알림 미지원 */ }
}

function schedule() {
  window.clearTimeout(timer);
  if (subscribers === 0) return;
  const waiting = state.data?.items.some(isWaiting) ?? false;
  if (waiting) timer = window.setTimeout(() => void refreshActiveSessions(), POLL_MS);
}

export async function refreshActiveSessions(): Promise<void> {
  if (inflight) return;
  if (!loadAuthToken()) { emit({ data: null }); return; }
  inflight = true; lastFetch = Date.now();
  try {
    const data = await getActiveSessions();
    const seen = readSet(SEEN_KEY); const notified = readSet(DONE_KEY);
    const fresh: ReportToast[] = [];
    for (const r of data.recent_finished) {
      if (seen.has(r.session_id) && !notified.has(r.session_id)) {
        const ok = r.status === 'done';
        fresh.push({ session_id: r.session_id, ok }); notified.add(r.session_id); seen.delete(r.session_id);
        notifyBrowser(ok);
      }
    }
    data.items.filter(isWaiting).forEach((i) => seen.add(i.session_id));
    writeSet(SEEN_KEY, seen); writeSet(DONE_KEY, notified);
    emit({ data, toasts: fresh.length ? [...state.toasts, ...fresh] : state.toasts });
  } catch { /* 401·네트워크 오류: 헤더 기능만 비활성 */ }
  finally { inflight = false; schedule(); }
}

export const dismissToast = (id: string) => emit({ toasts: state.toasts.filter((t) => t.session_id !== id) });

function subscribe(l: () => void) { listeners.add(l); return () => { listeners.delete(l); }; }
const snapshot = () => state;

/** Shell·기록 화면에서 쓰는 훅. 붙을 때 오래된 값이면 다시 읽고, 창으로 돌아오면 바로 갱신한다. */
export function useActiveSessions() {
  const s = useSyncExternalStore(subscribe, snapshot, snapshot);
  useEffect(() => {
    subscribers += 1;
    if (Date.now() - lastFetch > 2000) void refreshActiveSessions(); else schedule();
    const onFocus = () => { if (document.visibilityState === 'visible') void refreshActiveSessions(); };
    document.addEventListener('visibilitychange', onFocus);
    return () => {
      subscribers -= 1;
      document.removeEventListener('visibilitychange', onFocus);
      if (subscribers === 0) window.clearTimeout(timer);
    };
  }, []);
  return s;
}

export const waitingItems = (data: ActiveSessionsOut | null): ActiveSessionItemOut[] => data?.items.filter(isWaiting) ?? [];
