// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// OWNER: frontend (contracts.yaml ownership)
// HTTP 오류 문구는 서버가 준 message(contracts error_codes)를 그대로 쓴다. 아래는 응답 안의 작업 오류 코드·사유 설명.
export const PREPARE_ERROR_TEXT: Record<string, string> = {
  TTS_ASSET_MISSING: '이 문항의 음성이 아직 만들어지지 않았어요.',
  TTS_HASH_MISMATCH: '문항 문장이 바뀌어 음성을 다시 만들어야 해요.',
  TTS_FILE_MISSING: '음성 파일을 찾을 수 없어요.',
  NO_ACTIVE_VOICE: '사용할 진행자 음성이 설정되지 않았어요.',
};
export const REJECT_TEXT: Record<string, string> = {
  too_short: '녹음이 너무 짧았어요.',
  too_long: '녹음이 너무 길었어요.',
  silence: '목소리가 거의 들리지 않았어요.',
  no_speech: '말한 내용을 알아듣지 못했어요.',
  corrupt: '녹음 파일이 손상됐어요.',
  unsupported_format: '지원하지 않는 녹음 형식이에요.',
};
export const STT_ERROR_TEXT: Record<string, string> = {
  STT_ENGINE_ERROR: '음성 인식 중 오류가 났어요. 녹음은 저장되어 있어요.',
  STT_DECODE_ERROR: '녹음 파일을 읽지 못했어요. 녹음은 저장되어 있어요.',
};
export const GRADING_ERROR_TEXT: Record<string, string> = {
  LLM_TRANSIENT: '평가 서버가 잠시 응답하지 않았어요.',
  LLM_REFUSED: '평가 요청이 처리되지 않았어요.',
  LLM_INVALID_OUTPUT: '평가 결과가 검증을 통과하지 못했어요.',
  EVAL_INPUT_TOO_LARGE: '답변이 길어 한 번에 평가할 수 없었어요.',
  EVAL_INPUT_INVALID: '평가에 필요한 시험 정보가 맞지 않아요.',
  EVAL_INTERNAL: '평가 중 서버 오류가 났어요.',
};
export const TYPE_LABEL: Record<string, string> = {
  self_intro: '자기소개', description: '묘사', routine: '일상', past_experience: '과거 경험', comparison: '비교',
  issue: '이슈', roleplay_ask: '롤플레이 · 질문하기', roleplay_solve: '롤플레이 · 문제 해결', roleplay_experience: '롤플레이 · 관련 경험',
};
export const FUNCTION_LABEL: Record<string, string> = {
  self_introduce: '자기소개', describe: '묘사하기', report_routine: '일상 말하기', narrate_past: '과거 서술', compare: '비교하기',
  ask_information: '정보 묻기', solve_problem: '문제 해결', explain_issue: '이슈 설명', state_future_plan: '미래 계획·예상',
  express_opinion: '의견 말하기',
};
export const TIME_LABEL: Record<string, string> = { present: '현재', past: '과거', future: '미래' };
export const CONTEXT_LABEL: Record<string, string> = {
  personal_familiar: '개인·익숙한 일상', everyday_transaction: '일상 거래·문의', community_public: '사회·공공',
  unexpected_situation: '예상 밖 상황',
};
export const FACT_LABEL: Record<string, string> = {
  functions_tasks: '과제 수행', accuracy: '의미 전달의 정확성', context_content: '상황·내용 범위', text_type: '발화 구성',
};
export const FACT_STATUS_LABEL: Record<string, string> = {
  demonstrated: '보여 줌', not_demonstrated: '보여 주지 못함', not_observed: '관찰 기회 없음',
};
export const FULFILL_LABEL: Record<string, string> = {
  fulfilled: '과제 수행', partial: '일부 수행', not_fulfilled: '미수행', not_assessable: '확인 불가',
};
export function labelOf(map: Record<string, string>, key: string): string { return map[key] ?? key; }
