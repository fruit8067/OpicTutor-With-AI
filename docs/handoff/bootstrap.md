# bootstrap M0

## 상태
골격 구현 완료, 검증 진행 중 (2026-11-06 KST).

## 완료한 것
계약 v3의 API/내부 스키마, 모든 모듈 시그니처, DDL, Compose, 환경변수,
React/TypeScript/Tailwind v3, API 명세 v2, 소유권 검사기.

## 실행 방법
PowerShell: `python -m venv backend/.venv; backend/.venv/Scripts/python -m pip install -r backend/requirements/bootstrap.txt`
후 `cd backend; .venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1`.
bash: `python -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements/bootstrap.txt`
후 `cd backend && .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1`.
공통: `docker compose up -d`, `cd frontend` 후 `npm ci`와 `npm run build`.

## 알려진 문제
- 문서의 숫자 점수(1~5) 지시는 v3의 영역별 서술 진단과 충돌하여 계약 v3 우선.
- EvidenceBundle 상세 필드는 계약에 명시되지 않아 docs/corpus_version/retrieved_doc_ids로 정의.
- SessionRow/AnswerRow/JobRow는 psycopg dict_row와 호환되는 매핑 별칭.
- 출처 주석은 실제 작성 도구인 OpenAI Codex로 표시.
- 다른 PC 소유 모듈은 NotImplementedError stub. 실행 구현은 각 소유자가 담당.

## 생성한 모듈과 OWNER
- `backend/app/__init__.py` — # OWNER: bootstrap (contracts.yaml ownership)
- `backend/app/api/__init__.py` — # OWNER: session-api (contracts.yaml ownership)
- `backend/app/api/deps.py` — # OWNER: session-api (contracts.yaml ownership)
- `backend/app/api/routes_answers.py` — # OWNER: session-api (contracts.yaml ownership)
- `backend/app/api/routes_meta.py` — # OWNER: session-api (contracts.yaml ownership)
- `backend/app/api/routes_results.py` — # OWNER: session-api (contracts.yaml ownership)
- `backend/app/api/routes_sessions.py` — # OWNER: session-api (contracts.yaml ownership)
- `backend/app/config.py` — # OWNER: bootstrap (contracts.yaml ownership)
- `backend/app/db/__init__.py` — # OWNER: data-layer (contracts.yaml ownership)
- `backend/app/db/ai_requests.py` — # OWNER: data-layer (contracts.yaml ownership)
- `backend/app/db/answers.py` — # OWNER: data-layer (contracts.yaml ownership)
- `backend/app/db/dev.py` — # OWNER: data-layer (contracts.yaml ownership)
- `backend/app/db/evaluations.py` — # OWNER: data-layer (contracts.yaml ownership)
- `backend/app/db/jobs.py` — # OWNER: data-layer (contracts.yaml ownership)
- `backend/app/db/pool.py` — # OWNER: data-layer (contracts.yaml ownership)
- `backend/app/db/rag.py` — # OWNER: data-layer (contracts.yaml ownership)
- `backend/app/db/sessions.py` — # OWNER: data-layer (contracts.yaml ownership)
- `backend/app/db/tts.py` — # OWNER: data-layer (contracts.yaml ownership)
- `backend/app/errors.py` — # OWNER: bootstrap (contracts.yaml ownership)
- `backend/app/exam/__init__.py` — # OWNER: session-api (contracts.yaml ownership)
- `backend/app/exam/builder.py` — # OWNER: session-api (contracts.yaml ownership)
- `backend/app/exam/scenarios.py` — # OWNER: session-api (contracts.yaml ownership)
- `backend/app/grading/__init__.py` — # OWNER: grader (contracts.yaml ownership)
- `backend/app/grading/evidence.py` — # OWNER: grader (contracts.yaml ownership)
- `backend/app/grading/job.py` — # OWNER: grader (contracts.yaml ownership)
- `backend/app/grading/prompt.py` — # OWNER: grader (contracts.yaml ownership)
- `backend/app/grading/service.py` — # OWNER: grader (contracts.yaml ownership)
- `backend/app/grading/tiers.py` — # OWNER: grader (contracts.yaml ownership)
- `backend/app/grading/validate.py` — # OWNER: grader (contracts.yaml ownership)
- `backend/app/llm/__init__.py` — # OWNER: grader (contracts.yaml ownership)
- `backend/app/llm/chat.py` — # OWNER: grader (contracts.yaml ownership)
- `backend/app/llm/embeddings.py` — # OWNER: data-layer (contracts.yaml ownership)
- `backend/app/main.py` — # OWNER: session-api (contracts.yaml ownership)
- `backend/app/schemas/__init__.py` — # OWNER: bootstrap (contracts.yaml ownership)
- `backend/app/schemas/api.py` — # OWNER: bootstrap (contracts.yaml ownership)
- `backend/app/schemas/internal.py` — # OWNER: bootstrap (contracts.yaml ownership)
- `backend/app/stt/__init__.py` — # OWNER: worker-stt (contracts.yaml ownership)
- `backend/app/stt/audio.py` — # OWNER: worker-stt (contracts.yaml ownership)
- `backend/app/stt/engine.py` — # OWNER: worker-stt (contracts.yaml ownership)
- `backend/app/stt/job.py` — # OWNER: worker-stt (contracts.yaml ownership)
- `backend/app/stt/metrics.py` — # OWNER: worker-stt (contracts.yaml ownership)
- `backend/app/tts/__init__.py` — # OWNER: tts-host (contracts.yaml ownership)
- `backend/app/tts/assets.py` — # OWNER: tts-host (contracts.yaml ownership)
- `backend/app/tts/host_lines.py` — # OWNER: tts-host (contracts.yaml ownership)
- `backend/app/tts/prepare.py` — # OWNER: tts-host (contracts.yaml ownership)
- `backend/app/worker/__init__.py` — # OWNER: worker-stt (contracts.yaml ownership)
- `backend/app/worker/__main__.py` — # OWNER: worker-stt (contracts.yaml ownership)
- `backend/app/worker/errors.py` — # OWNER: worker-stt (contracts.yaml ownership)
- `backend/app/worker/registry.py` — # OWNER: worker-stt (contracts.yaml ownership)
- `backend/app/worker/runner.py` — # OWNER: worker-stt (contracts.yaml ownership)

## 실행 확인
- Python 전체 모듈 import 성공, TestClient health=200(ready=false), docs=200.
- npm run build 통과, git check-ignore: 지정한 두 경로 출력 없음.
- Docker 엔진 연결 미확인. SQL 실제 적용 검증은 data-layer 단계에서 재시도.


## 최종 검증 추가
- WSL의 독립 Docker 엔진에 전용 PostgreSQL 16/pgvector 컨테이너를 띄워 검증.
- init_db 반복 실행 및 001_init.sql 직접 적용 2회 모두 오류 없이 통과.
- API 예시는 실제 스키마 enum·상태와 일치하도록 검토. 완료 스키마 필드 표 포함.
- worker stub은 미구현 상태를 exit 오류로 알림. 정상 실행처럼 종료하지 않음.
- GitHub 연결의 PR 생성은 403. 브랜치 push는 성공했으며 PR 병합은 대기.

