# data-layer M1/M2

## 상태
M1/M2 코드와 실제 로컬 DB 검증 완료, 병합 대기 (2026-11-06 KST).
브랜치는 agent/bootstrap 위에 쌓음. main 병합 대기 중이므로 비교 기준은 agent/bootstrap.

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
- corpus M1의 scenarios.json, VERSION, Q000과 v3 문항 태그가 아직 없음. dev seed는 태그를 추측하지 않고 실패한다.
- 실제 임베딩 적재는 EMBED_API_KEY가 필요하다. --dry-run은 외부 호출 없이 적재 예정 건수를 계산한다.
- STT 완료 콜백 시그니처에는 attempt/lease가 없어 이전 STT 시도를 엄격하게 구분할 수 없다.
  worker-stt는 작업 payload의 stt_attempt와 현재 answer.stt_attempt 및 작업 리스를 확인한 뒤 콜백해야 한다.
- 외부 AI 호출은 실제 키로 실행하지 않음. 답변/프롬프트 원문을 AI 요청 로그에 저장하지 않음.

## 측정값
WSL Docker의 전용 PostgreSQL 16/pgvector 컨테이너에서 검증. 검증용 합성 자료만 사용.
실제 코퍼스의 임베딩 수·소요 시간·비용은 VERSION과 키 미준비로 미측정.

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

