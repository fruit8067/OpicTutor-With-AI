-- AI-assisted: OpenAI Codex. 계약의 불변 조건 및 조회 인덱스.
CREATE UNIQUE INDEX IF NOT EXISTS session_one_warmup ON session_questions(session_id) WHERE NOT is_scored;
CREATE INDEX IF NOT EXISTS answers_question_attempt ON answers(session_question_id,attempt_no DESC);
CREATE INDEX IF NOT EXISTS evaluations_session_run ON evaluations(session_id,run_no DESC);
CREATE INDEX IF NOT EXISTS jobs_lease ON jobs(locked_until) WHERE status='running';
CREATE INDEX IF NOT EXISTS jobs_activity ON jobs(updated_at DESC) WHERE status IN ('running','done');
CREATE INDEX IF NOT EXISTS ai_requests_purpose ON ai_requests(purpose,created_at);
