# data-layer M1/M2

## 상태
트랜잭션 구현 완료, 실제 DB 검증 진행 중 (2026-11-06 KST).
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

## 알려진 문제 및 다른 에이전트에게 요청
- corpus M1의 scenarios.json, VERSION, Q000과 v3 문항 태그가 아직 없음. dev seed는 태그를 추측하지 않고 실패한다.
- 실제 임베딩 적재는 EMBED_API_KEY가 필요하다. --dry-run은 외부 호출 없이 적재 예정 건수를 계산한다.
- STT 완료 콜백 시그니처에는 attempt/lease가 없어 이전 STT 시도를 엄격하게 구분할 수 없다.
  worker-stt는 작업 payload의 stt_attempt와 현재 answer.stt_attempt 및 작업 리스를 확인한 뒤 콜백해야 한다.
- 외부 AI 호출은 실제 키로 실행하지 않음. 답변/프롬프트 원문을 AI 요청 로그에 저장하지 않음.

## 측정값
실제 DB 테스트와 소유권 검사 결과를 검증 후 추가한다.

## 실행 확인 (2026-11-06 KST)
- 전체 모듈 compile/import 통과.
- 임베딩 배치·응답 순서·차원 거부·본문 미기록 테스트 통과.
- 실제 PostgreSQL 불변 조건 테스트 5개는 DB 미기동으로 skip. 통과로 간주하지 않음.
- Docker 로그: dockerInference 소켓 접근 실패로 엔진 시작 중단. 프로세스 종료/소켓 정리는 자동 승인 검토에서 정책 차단되어 실행하지 않음.
- ingest --dry-run: VERSION 파일 누락으로 명시적 실패. 실제 적재·임베딩 수·시간 미측정.
- DB 동시성/마이그레이션 실제 검증 및 M1/M2 병합은 보류.

