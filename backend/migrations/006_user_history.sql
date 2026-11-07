-- AI-assisted: 유저별 테스트 히스토리 조회 인덱스 및 세션 삭제 시 외래키 정리 마이그레이션입니다.
CREATE INDEX IF NOT EXISTS sessions_user_created_idx
  ON sessions (user_id, created_at DESC)
  WHERE user_id IS NOT NULL;

ALTER TABLE sessions DROP CONSTRAINT IF EXISTS sessions_result_fk;
ALTER TABLE sessions ADD CONSTRAINT sessions_result_fk
  FOREIGN KEY (result_id) REFERENCES evaluations(id) ON DELETE SET NULL;

ALTER TABLE sessions DROP CONSTRAINT IF EXISTS sessions_replaces_session_id_fkey;
ALTER TABLE sessions ADD CONSTRAINT sessions_replaces_session_id_fkey
  FOREIGN KEY (replaces_session_id) REFERENCES sessions(id) ON DELETE SET NULL;

