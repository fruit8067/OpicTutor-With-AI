// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// OWNER: frontend (contracts.yaml ownership)
//
// contracts.yaml api.endpoints 전부. 실패 응답 {"error": {code, message, detail}} → ApiError로 throw.
// 함수 이름은 contracts frontend_interfaces.api_client 기준. bootstrap stub 이름은 아래 별칭으로 유지한다.
import type * as T from './types';

export const API_BASE: string = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000/api/v1';
export const API_ORIGIN: string = (() => {
  try { return new URL(API_BASE).origin; } catch { return window.location.origin; }
})();

export class ApiError extends Error {
  code: string;
  detail: Record<string, unknown>;
  status: number;
  constructor(code: string, message: string, detail: Record<string, unknown> = {}, status = 0) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.detail = detail;
    this.status = status;
  }
}

/** 네트워크 자체가 실패했을 때(서버 응답 없음) code = NETWORK_ERROR */
export const NETWORK_ERROR = 'NETWORK_ERROR';

async function request<R>(method: string, path: string, body?: unknown, init?: RequestInit): Promise<R> {
  let res: Response;
  try {
    res = await fetch(API_BASE + path, {
      method,
      headers: body !== undefined && !(body instanceof FormData) ? { 'Content-Type': 'application/json' } : undefined,
      body: body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body),
      ...init,
    });
  } catch {
    throw new ApiError(NETWORK_ERROR, '서버에 연결하지 못했어요. 네트워크를 확인해 주세요.');
  }
  const text = await res.text();
  let data: unknown = null;
  if (text) {
    try { data = JSON.parse(text); } catch { data = null; }
  }
  if (!res.ok) {
    const err = (data as { error?: { code?: string; message?: string; detail?: Record<string, unknown> } } | null)?.error;
    throw new ApiError(err?.code ?? 'INTERNAL_ERROR', err?.message ?? '잠시 후 다시 시도해 주세요.', err?.detail ?? {}, res.status);
  }
  return data as R;
}

const s = (id: string) => `/sessions/${encodeURIComponent(id)}`;

export const getHealth = () => request<T.HealthOut>('GET', '/health');                                    // A1
export const getScenarios = () => request<T.ScenarioOut[]>('GET', '/scenarios');                         // A2
export const getHostLines = () => request<Record<string, T.HostLineOut>>('GET', '/host-lines');          // A3
export const createSession = (data: T.CreateSessionIn) => request<T.SessionOut>('POST', '/sessions', data); // S1
export const getSession = (id: string) => request<T.SessionOut>('GET', s(id));                           // S2
export const retryPrepare = (id: string) => request<T.SessionOut>('POST', `${s(id)}/prepare/retry`);    // S3
export const cancelSession = (id: string) => request<T.SessionOut>('POST', `${s(id)}/cancel`);          // S4
export const startSession = (id: string) => request<T.SessionOut>('POST', `${s(id)}/start`);            // S5
export const getCurrent = (id: string) => request<T.CurrentQuestionOut>('GET', `${s(id)}/current`);      // Q1
export const postReplay = (id: string, orderNo: number) =>
  request<T.ReplayOut>('POST', `${s(id)}/questions/${orderNo}/replay`);                                 // Q2
export const skipQuestion = (id: string, orderNo: number) =>
  request<T.SkipOut>('POST', `${s(id)}/questions/${orderNo}/skip`);                                     // Q3

export interface UploadInput { order_no: number; client_request_id: string; duration_ms: number; audio: Blob; filename: string }
export const uploadAnswer = (id: string, u: UploadInput) => {                                           // U1
  const fd = new FormData();
  fd.append('order_no', String(u.order_no));
  fd.append('client_request_id', u.client_request_id);
  fd.append('duration_ms', String(Math.round(u.duration_ms)));
  fd.append('audio', u.audio, u.filename);
  return request<T.AnswerOut>('POST', `${s(id)}/answers`, fd);
};
export const getAnswer = (id: string, answerId: string) =>
  request<T.AnswerOut>('GET', `${s(id)}/answers/${encodeURIComponent(answerId)}`);                      // U2
export const retryStt = (id: string, answerId: string) =>
  request<T.AnswerOut>('POST', `${s(id)}/answers/${encodeURIComponent(answerId)}/retry-stt`);           // U3
export const submitSession = (id: string) => request<T.SessionOut>('POST', `${s(id)}/submit`);          // E1
export const getResult = (id: string) => request<T.ResultOut>('GET', `${s(id)}/result`);                 // E2
export const regrade = (id: string) => request<T.SessionOut>('POST', `${s(id)}/regrade`);               // E3
export const chat = (id: string) => request<never>('POST', `${s(id)}/chat`);                             // X1 (501)

// bootstrap stub 이름 호환
export const listScenarios = getScenarios;
export const getCurrentQuestion = getCurrent;
export const replayQuestion = postReplay;
export const regradeSession = regrade;

/** 서버가 준 /media/... 상대 경로를 API 서버 기준 절대 URL로. */
export function mediaUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  try { return new URL(path, API_ORIGIN + '/').toString(); } catch { return null; }
}
