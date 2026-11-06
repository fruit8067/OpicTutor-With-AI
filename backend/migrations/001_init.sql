-- AI-assisted: 계약 DDL 골격은 OpenAI Codex의 도움으로 작성했습니다.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END; $$ LANGUAGE plpgsql;

CREATE TABLE IF NOT EXISTS sessions (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_request_id   TEXT UNIQUE,
  replaces_session_id UUID NULL REFERENCES sessions(id),
  scenario_id         TEXT NOT NULL,
  settings_json       JSONB NOT NULL DEFAULT '{}'::jsonb,
  status              TEXT NOT NULL CHECK (status IN ('preparing','prepare_failed','ready','cancelled',
                        'in_progress','submitted','grading','grading_failed','done')),
  question_count      INT  NOT NULL,
  current_order_no    INT  NOT NULL DEFAULT 1,       -- question_count + 1 이면 모든 답변 저장 완료
  prepare_attempt     INT  NOT NULL DEFAULT 1,
  prepare_error_json  JSONB NULL,                    -- [{order_no|host_key, ref_id, error_code}]
  selected_answer_ids UUID[] NULL,                   -- submit 때 고정
  result_id           UUID NULL,                     -- 현재 표시할 evaluations.id
  started_at TIMESTAMPTZ NULL, submitted_at TIMESTAMPTZ NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tts_assets (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cache_key        TEXT NOT NULL UNIQUE,             -- "{kind}:{ref_id}:{text_hash}:{voice_id}"
  kind             TEXT NOT NULL CHECK (kind IN ('question','host','e2e_answer')),
  ref_id           TEXT NOT NULL,                    -- question_id 또는 host line key
  text_hash        TEXT NOT NULL,                    -- sha1(utf-8 text)
  voice_id         TEXT NOT NULL,
  settings_version TEXT NOT NULL,
  status           TEXT NOT NULL CHECK (status IN ('available','missing','invalid')),
  file_path        TEXT NOT NULL,                    -- TTS_DIR 기준 상대 경로
  duration_sec     REAL NULL,
  error_code       TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS session_questions (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id       UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  order_no         INT  NOT NULL,
  question_id      TEXT NOT NULL,
  question_version TEXT NOT NULL,                    -- sha1(question_text)[:12]
  question_text    TEXT NOT NULL,
  question_type    TEXT NOT NULL,
  is_scored        BOOLEAN NOT NULL,                 -- 자기소개 워밍업 false
  target_functions   TEXT[] NOT NULL DEFAULT '{}',   -- question_tags.target_functions
  target_time_frames TEXT[] NOT NULL DEFAULT '{}',
  context_scope      TEXT[] NOT NULL DEFAULT '{}',
  tts_asset_id     UUID NULL REFERENCES tts_assets(id),
  replay_count     INT  NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (session_id, order_no),
  UNIQUE (session_id, question_id)
);

CREATE TABLE IF NOT EXISTS session_host_lines (
  session_id   UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  line_key     TEXT NOT NULL,
  tts_asset_id UUID NOT NULL REFERENCES tts_assets(id),
  PRIMARY KEY (session_id, line_key)
);

CREATE TABLE IF NOT EXISTS answers (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_question_id UUID NOT NULL REFERENCES session_questions(id) ON DELETE CASCADE,
  attempt_no          INT  NOT NULL,
  client_request_id   TEXT NOT NULL UNIQUE,          -- 업로드 재전송 멱등 키
  audio_path          TEXT NOT NULL,
  audio_mime          TEXT NOT NULL,
  audio_bytes         INT  NOT NULL,
  audio_hash          TEXT NOT NULL,                 -- sha256
  client_duration_ms  INT  NOT NULL,
  stt_status          TEXT NOT NULL CHECK (stt_status IN ('queued','processing','done','rejected','failed')),
  stt_attempt         INT  NOT NULL DEFAULT 1,
  reject_reason       TEXT NULL,
  is_selected         BOOLEAN NOT NULL DEFAULT false,
  stt_text            TEXT NULL,
  timestamps_json     JSONB NULL,                    -- [{word,start,end}]
  metrics_json        JSONB NULL,
  stt_version         TEXT NULL,
  error_code          TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (session_question_id, attempt_no)
);
CREATE UNIQUE INDEX IF NOT EXISTS answers_one_selected ON answers (session_question_id) WHERE is_selected;

CREATE TABLE IF NOT EXISTS evaluations (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id          UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  run_no              INT  NOT NULL,
  selected_answer_ids UUID[] NOT NULL,
  status              TEXT NOT NULL CHECK (status IN ('queued','running','done','failed')),
  assessment_status   TEXT NULL CHECK (assessment_status IN ('assessed','insufficient_evidence')),
  base_level          TEXT NULL CHECK (base_level IN ('NL','NM','NH','IL','IM','IH','AL')),
  estimated_level     TEXT NULL CHECK (estimated_level IN ('NL','NM','NH','IL','IM1','IM2','IM3','IH','AL')),
  im_estimation_status TEXT NULL CHECK (im_estimation_status IN ('provisional','insufficient_evidence','not_applicable')),
  result_json         JSONB NULL,                    -- schemas.EvaluationResult (검증 통과본)
  model TEXT NULL, prompt_version TEXT NULL, rubric_version TEXT NULL, im_rubric_version TEXT NULL,
  corpus_version TEXT NULL,
  retrieved_doc_ids   TEXT[] NULL,
  error_code          TEXT NULL,
  error_detail        JSONB NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (session_id, run_no),
  -- done이면: assessed ⇔ base_level 있음 / insufficient_evidence ⇔ 두 등급 모두 없음
  CHECK (status <> 'done' OR (
    (assessment_status = 'assessed' AND base_level IS NOT NULL) OR
    (assessment_status = 'insufficient_evidence' AND base_level IS NULL AND estimated_level IS NULL))),
  -- 2단 등급 일관성
  CHECK (estimated_level IS NULL OR base_level IS NOT NULL),
  CHECK (base_level IS NULL OR base_level = 'IM' OR estimated_level IS NULL OR estimated_level = base_level),
  CHECK (base_level IS DISTINCT FROM 'IM' OR estimated_level IS NULL OR estimated_level IN ('IM1','IM2','IM3'))
);
ALTER TABLE sessions DROP CONSTRAINT IF EXISTS sessions_result_fk;
ALTER TABLE sessions ADD CONSTRAINT sessions_result_fk FOREIGN KEY (result_id) REFERENCES evaluations(id);

CREATE TABLE IF NOT EXISTS rag_docs (
  id              TEXT PRIMARY KEY,
  doc_type        TEXT NOT NULL CHECK (doc_type IN ('rubric','upgrade_pattern','question','answer')),
  question_id     TEXT NULL,
  question_type   TEXT NULL,
  level           TEXT NULL,
  level_rank      INT  NULL,
  contrast_set_id TEXT NULL,
  text_style      TEXT NULL,
  text            TEXT NOT NULL,
  metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
  corpus_version  TEXT NOT NULL,
  embedding       VECTOR(1536) NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS rag_docs_lookup ON rag_docs (doc_type, contrast_set_id, text_style);
CREATE INDEX IF NOT EXISTS rag_docs_embedding ON rag_docs USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS jobs (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  type         TEXT NOT NULL CHECK (type IN ('tts_prepare','stt','evaluate')),
  target_id    UUID NOT NULL,
  dedupe_key   TEXT NOT NULL UNIQUE,
  status       TEXT NOT NULL CHECK (status IN ('queued','running','done','failed','dead')),
  attempts     INT  NOT NULL DEFAULT 0,
  max_attempts INT  NOT NULL DEFAULT 3,
  locked_by    TEXT NULL,
  locked_until TIMESTAMPTZ NULL,
  next_run_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  payload      JSONB NOT NULL DEFAULT '{}'::jsonb,
  error_code   TEXT NULL,
  error_detail JSONB NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS jobs_ready ON jobs (type, status, next_run_at);

CREATE TABLE IF NOT EXISTS ai_requests (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id        UUID NULL REFERENCES jobs(id),
  purpose       TEXT NOT NULL CHECK (purpose IN ('evaluate','embed','eval_script')),
  model         TEXT NOT NULL,
  input_tokens  INT NULL, output_tokens INT NULL, latency_ms INT NULL,
  status        TEXT NOT NULL CHECK (status IN ('ok','error','refused','invalid_output')),
  error_code    TEXT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);                                               -- 답변 원문·프롬프트 본문은 저장하지 않는다

-- updated_at 트리거: sessions, tts_assets, session_questions, answers, evaluations, jobs
-- (data-layer가 DO 블록으로 각 테이블에 set_updated_at 트리거를 붙인다)

DO $$ DECLARE tbl text; BEGIN
  FOREACH tbl IN ARRAY ARRAY['sessions','tts_assets','session_questions','answers','evaluations','jobs'] LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS touch_updated_at ON %I', tbl);
    EXECUTE format('CREATE TRIGGER touch_updated_at BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION set_updated_at()', tbl);
  END LOOP;
END $$;
