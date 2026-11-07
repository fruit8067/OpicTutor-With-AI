-- AI-assisted: 이 마이그레이션은 Claude(Anthropic)의 도움으로 작성되었습니다.
-- 사용자가 문항을 건너뛴 시각. NULL이면 건너뛰지 않은 문항이다.
-- 건너뛴 문항은 선택된(done) 답변 없이 다음 문항으로 진행되며, 채점에서는 답변 없음(unusable)으로 처리한다.
ALTER TABLE session_questions ADD COLUMN IF NOT EXISTS skipped_at TIMESTAMPTZ NULL;
