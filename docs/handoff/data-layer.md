# data-layer M1/M2

## 상태
코드·로컬 DB 검증 통과, 실제 코퍼스 적재/local_checks 및 M1·M2 병합 대기 (2026-11-07 KST).
CR session-api-01 및 data-layer-01/contracts v6 main a136406 기준 독립 브랜치다. 검사는 기본 origin/main 기준이며 타 역할 코드는 상속하지 않는다.

## 완료한 것
app.db 계약의 세션/음성/답변/평가/RAG/작업/AI 메타데이터 함수 전부와 dev 함수 3개.
스키마 이력·트리거·워밍업 최대 1개 제약, 작업 리스·재시도, 배치 임베딩·재개 가능한 적재.

## 실행 방법
PowerShell: `docker compose up -d` 후 `cd backend; .venv/Scripts/python -m scripts.db_reset --yes`.
bash: `docker compose up -d && cd backend && .venv/bin/python -m scripts.db_reset --yes`.
공통(가상환경 활성화 후):
`python -m scripts.ingest_rag --dry-run`, `python -m scripts.ingest_rag`.
`python -m app.db.dev seed-session --status ready` 또는 `--link-tts`.
`python -m app.db.dev seed-grading --level IM2`.
`python -m app.db.dev seed-answer <session_id> <audio.webm>`.

## 공개 함수
agents/contracts.yaml의 app.db 및 app.db.dev 전부. get_session은 host_lines와 latest_evaluation_status,
get_session_question은 latest_answer를 함께 반환한다. SQL은 API에서 직접 쓰지 않는다.
작업 payload는 tts_prepare.prepare_attempt, stt.stt_attempt, evaluate.run_no를 포함한다.
get_session_question의 내부 dict에는 해당 문항의 모든 client_request_ids도 포함한다.
업로드의 빠른 사전 검사에서 이전 시도의 유효한 재전송을 새 요청과 구분할 수 있으며 API 응답 필드는 바뀌지 않는다.

## 알려진 문제 및 다른 에이전트에게 요청
- corpus M1은 PR #5로 main에 반영됐다. 현재 M1 dry-run은 264문서/예상 임베딩 247건이다. M2 확대 자료는 corpus PR #12이며 아직 main 적재 완료로 세지 않는다. 과거 VERSION 누락 기록은 당시의 이력이다.
- 실제 임베딩 적재는 EMBED_API_KEY가 필요하다. --dry-run은 외부 호출 없이 적재 예정 건수를 계산한다.
- STT 완료 콜백 시그니처에는 attempt/lease가 없어 이전 STT 시도를 엄격하게 구분할 수 없다.
  worker-stt는 작업 payload의 stt_attempt와 현재 answer.stt_attempt 및 작업 리스를 확인한 뒤 콜백해야 한다.
- 외부 AI 호출은 실제 키로 실행하지 않음. 답변/프롬프트 원문을 AI 요청 로그에 저장하지 않음.

## 측정값
WSL Docker의 전용 PostgreSQL 16/pgvector 컨테이너에서 검증. 검증용 합성 자료만 사용.
실제 코퍼스 적재 수·임베딩 시간·비용은 키 미준비로 미측정이다. dry-run 예상 건수와 실제 완료 건수를 구분한다.

## 감사 후 수정·검증

- CR data-layer-01/PR #16 승인 후 finish_evaluation의 nullable 메타데이터 타입을 API/DB와 일치시켰다. 실제 IL 재평가를 im_rubric_version=None/corpus_version=None으로 저장·조회하는 검증을 추가했다. 런타임·컬럼·평가 기준 변경은 없다.

- 2026-11-07 추가 검증: 14 passed, skip 0(1.61초). HTTP 408/503 임베딩 재시도, 401 단일 실패, 중복 응답 index 거부를 실제 SDK+MockTransport로 검증했다.
- CR session-api-01의 get_session_id_by_request_id를 구현하고 빈 문자열 키도 None과 구분해 동시 생성 시 1행/1작업을 보장한다. HTTP/SQL 공개 시그니처는 승인된 v5에 맞춘다.
- A/B 메모리 조합 검증 101 passed(5.37초). 별도 생성/삭제한 테스트 DB를 사용했으며 기존 data-layer 단독 검증과 구분한다. TTS URL·ASR·LLM은 명시적 대역이고 실제 provider 정확도는 아니다.

- I-03: complete_prepare의 질문 해시는 Python text.strip().encode('utf-8')의 SHA1을 사용한다. SQL의 원문 해시 비교를 제거했다.
- 실제 PostgreSQL에서 9개 DB/임베딩 경계 테스트 통과(1.46초). 준비 링크 테스트는 탭·개행·Unicode 공백을 포함한 원문도 명세대로 만든 asset에 연결되는지 검증한다.
- LLM/임베딩 네트워크 호출 없이 fixture 검증했다. 실제 ingest local_check는 미충족이므로 PR은 Draft다.

## 실행 확인 (2026-11-06 KST)
- 전체 모듈 compile/import 통과.
- 임베딩 배치·응답 순서·차원 거부·본문 미기록 테스트 통과.
- 초기 PostgreSQL 테스트 5개 skip 후 WSL의 독립 Docker 엔진으로 DB를 시작하여 재검증.
- Docker 로그: dockerInference 소켓 접근 실패로 엔진 시작 중단. 프로세스 종료/소켓 정리는 자동 승인 검토에서 정책 차단되어 실행하지 않음.
- ingest --dry-run: VERSION 파일 누락으로 명시적 실패. 실제 적재·임베딩 수·시간 미측정.
- PostgreSQL 16: db_reset --yes, init_db 2회, 001_init.sql 직접 적용 2회 모두 성공.
- 실제 DB+임베딩 경계 테스트: 8 passed (2026-11-06 KST).
- 세션/답변 같은 키 동시 5회 → 각각 1행·created 1회. complete_stt 동시 10회 → 순서 +1만.
- 워커 2개 claim → 서로 다른 작업, 잘못된/만료된 리스 거부 및 복구 확인.
- 준비 링크 원자성, 워밍업 최대 1개 DB 제약, 조기 제출 차단, submit 멱등성,
  2단 등급 CHECK, 재평가 이전 run 완료·실패 무시, ingest 재개·메타데이터·벡터 검색 확인.
- ingest는 임베딩만 가짜 벡터로 대체한 로컬 fixture 4건으로 적재·재적재 확인.
  실제 외부 임베딩 호출과 실제 코퍼스 적재는 아직 실행하지 않음. M1/M2 PR 병합은 대기.
- 로컬 검증 컨테이너: WSL `opic-core-a-check-db`, 볼륨도 같은 이름, 127.0.0.1:5432.
- 완료 조건 재점검에서 마지막 시도의 워커 종료 후 작업이 dead로 고립되는 문제를 재현했다.
  recover_expired_jobs는 계약대로 running→failed로 복구하고 claim_job은 다시 확보한다.
  max_attempts 판정은 fail_job에서 유지해 워커가 최종 실패를 답변/세션에 반영할 수 있다.
- PostgreSQL 재검증: data-layer 테스트 9 passed, 리스 마지막 시도 복구 및 모든 시도의 멱등 키 조회 포함.


## M1 공개 기록과 함수 목록

PR #2 생성: **2026-11-06 17:28:34 KST**. M1/M2 코드는 같은 PR에 누적했으며 아직 병합 전이다.

| 모듈 | 공개 함수 |
| --- | --- |
| pool | `init_db`, `ping` |
| sessions | `create_session`, `get_session`, `list_session_questions`, `get_session_question`, `retry_prepare`, `cancel_session`, `start_session`, `increment_replay` |
| tts | `upsert_tts_asset`, `find_tts_asset`, `complete_prepare`, `fail_prepare` |
| answers | `create_answer`, `get_answer`, `mark_stt_processing`, `complete_stt`, `reject_stt`, `fail_stt`, `retry_stt` |
| evaluations | `submit_session`, `create_regrade`, `get_evaluation`, `get_latest_evaluation`, `load_exam_snapshot`, `mark_evaluation_running`, `finish_evaluation`, `fail_evaluation` |
| rag | `get_rag_docs`, `get_contrast_set`, `search_similar_answers`, `current_corpus_version` |
| jobs | `claim_job`, `heartbeat_job`, `complete_job`, `fail_job`, `recover_expired_jobs`, `last_job_activity` |
| ai_requests | `log_ai_request`, `count_ai_requests` |
| dev | `seed_session`, `seed_queued_answer`, `seed_grading_session` |
| llm.embeddings | `embed_texts` |
