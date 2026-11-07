// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// 후속 수정: 취소 실패 시 세션 보존은 OpenAI Codex의 도움으로 작성되었습니다.
// OWNER: frontend (contracts.yaml ownership)
import { ApiError, cancelSession } from '../api/client';
import { clearSessionId } from './session';

/** 준비 중·준비 완료 세션을 취소(S4)하고 브라우저의 session_id를 지운다(설정 바꾸기). */
export async function cancelAndReset(id: string) {
  try { await cancelSession(id); } catch (error) {
    if (!(error instanceof ApiError) || error.code !== 'SESSION_NOT_FOUND') throw error;
  }
  clearSessionId();
}
