// AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
// OWNER: frontend (contracts.yaml ownership)
import type * as T from './types';
export const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000/api/v1';
export async function getHealth(): Promise<T.HealthOut> {
  throw new Error("TODO: frontend A1");
}
export async function listScenarios(): Promise<T.ScenarioOut[]> {
  throw new Error("TODO: frontend A2");
}
export async function getHostLines(): Promise<Record<string, T.HostLineOut>> {
  throw new Error("TODO: frontend A3");
}
export async function createSession(data: T.CreateSessionIn): Promise<T.SessionOut> {
  throw new Error("TODO: frontend S1");
}
export async function getSession(session_id: string): Promise<T.SessionOut> {
  throw new Error("TODO: frontend S2");
}
export async function retryPrepare(session_id: string): Promise<T.SessionOut> {
  throw new Error("TODO: frontend S3");
}
export async function cancelSession(session_id: string): Promise<T.SessionOut> {
  throw new Error("TODO: frontend S4");
}
export async function startSession(session_id: string): Promise<T.SessionOut> {
  throw new Error("TODO: frontend S5");
}
export async function getCurrentQuestion(session_id: string): Promise<T.CurrentQuestionOut> {
  throw new Error("TODO: frontend Q1");
}
export async function replayQuestion(session_id: string, order_no: number): Promise<T.ReplayOut> {
  throw new Error("TODO: frontend Q2");
}
export async function createAnswer(session_id: string, data: FormData): Promise<T.AnswerOut> {
  throw new Error("TODO: frontend U1");
}
export async function getAnswer(session_id: string, answer_id: string): Promise<T.AnswerOut> {
  throw new Error("TODO: frontend U2");
}
export async function retryStt(session_id: string, answer_id: string): Promise<T.AnswerOut> {
  throw new Error("TODO: frontend U3");
}
export async function submitSession(session_id: string): Promise<T.SessionOut> {
  throw new Error("TODO: frontend E1");
}
export async function getResult(session_id: string): Promise<T.ResultOut> {
  throw new Error("TODO: frontend E2");
}
export async function regradeSession(session_id: string): Promise<T.SessionOut> {
  throw new Error("TODO: frontend E3");
}
export async function chat(session_id: string): Promise<never> {
  throw new Error("TODO: frontend X1");
}
