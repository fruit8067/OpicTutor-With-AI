# CR orchestrator-06 — 비동기 STT와 분석 중 화면 이동 (develop/v3)

AI-assisted: 이 문서와 관련 구현은 Claude(Anthropic)의 도움으로 작성되었습니다.

## 배경

사용자 요청 두 가지를 반영한다.

1. 답변을 녹음한 뒤 STT 완료를 기다리지 않고 바로 다음 문항으로 넘어간다.
2. 제출 후 STT 대기·평가 중에도 다른 화면(내 시험 기록, 새 시험, 다른 리포트)으로 이동하고, 끝나면 알림을 받는다.

기존 계약 v8에서는 순서 전진이 `complete_stt`에만 있었고, `submit_session`이 모든 답변의 `stt_status='done'`을 요구했다. 상단 메뉴의 리포트 항목에는 이동 경로가 없었다.

## 결정

- **새 상태를 만들지 않는다.** 원래 계획의 평가 상태 `waiting_stt` 대신, 이미 enum·전이표·프론트에 있는 세션 상태 `submitted`를 "제출됨, 남은 STT 대기 중"으로 넓힌다. 평가 행은 평가를 등록하는 순간에만 만들어, 채택 답변이 등록 시점에 고정되게 한다. **DB 마이그레이션은 없다.**
- 순서 전진은 `create_answer` 접수 트랜잭션으로 옮긴다.
- STT 결과는 세션이 `in_progress` 또는 `submitted`이면 문항 위치와 관계없이 반영한다. 그 밖의 상태에서 늦게 도착한 결과는 무시한다.
- `rejected`와 재시도를 소진한 `failed`는 종결 상태다. 평가에서는 인식 불가 문항(`unusable_items_required`)으로 처리한다. 기존 평가 검증(`precheck_snapshot`·`validate_output`)을 그대로 쓴다.
- 평가 등록은 `maybe_enqueue_evaluation(cur, session)` 하나로만 한다. 세션 행 잠금 아래에서 `submitted`이고 대기 중인 STT가 없을 때만 등록한다. 그래서 제출과 마지막 STT 종결 중 나중 트랜잭션에서 정확히 한 번 등록된다(동시 실행 테스트 포함).
- 워커 안전장치: `stt` 작업이 `dead`가 되면 `fail_stt`로 답변을 종결한다. 제출된 세션이 영원히 대기하지 않게 하기 위함이다.
- 응답에 `SttProgress {total, done, pending, unusable}`를 추가하고(SessionOut, CurrentQuestionOut, ResultOut), `ResultItemOut.stt_status`를 추가한다.
- `GET /sessions/active`(H2)를 추가한다. 로그인 사용자 본인 세션만 반환하며, 헤더 배지와 완료 알림 폴링에 쓴다.

## 변경 범위

- 계약: `agents/contracts.yaml` v9, `docs/API_SPEC.md`
- 백엔드: `app/db/answers.py`, `app/db/evaluations.py`, `app/db/sessions.py`, `app/db/__init__.py`, `app/api/*`, `app/schemas/api.py`, `app/worker/runner.py`
- 프론트: `Exam.tsx`, `Result.tsx`, `History.tsx`, `Shell.tsx`, `lib/*`, `api/*`
- 테스트: 기존 "STT 완료 후에야 전진" 전제 테스트를 새 계약으로 수정하고, 제출 대기·자동 등록·동시성·dead 작업 종결·활성 세션 격리 테스트를 추가

## 소유권

여러 소유 경로(data-layer, session-api, worker-stt, bootstrap, frontend, orchestrator)를 함께 바꾸는 교차 작업이므로 오케스트레이터 권한으로 `develop/v3`에서 진행한다.

`python agents/tools/check_ownership.py orchestrator --base d3aa844 --head develop/v3` 결과, 의도한 대로 다음 소유자 경로가 교차 변경으로 보고된다(검사 스크립트는 수정하지 않음).

| 소유자 | 경로 |
| --- | --- |
| data-layer | `backend/app/db/{__init__,answers,evaluations,sessions}.py`, `backend/tests/test_db_invariants.py` |
| session-api | `backend/app/api/{deps,routes_answers,routes_results,routes_sessions}.py`, `backend/tests/{test_api_db,test_api_session_replay,test_api_upload}.py` |
| worker-stt | `backend/app/worker/runner.py`, `backend/tests/test_stt_job.py` |
| bootstrap | `backend/app/schemas/api.py`, `frontend/src/api/types.ts`, `docs/API_SPEC.md` |
| frontend | `frontend/src/{api/client.ts,components/Shell.tsx,index.css,lib/session.ts,lib/useActiveSessions.ts,pages/*.tsx}` |

`main` 병합 시에는 이 CR을 근거로 오케스트레이터가 확인한다.

## 검증 결과 (2026-11-08)

- `pytest`: 165 통과. 5개 실패(`test_db_ingest` 2, `test_grading_eval` 3)는 검증 환경에서 tiktoken 인코딩 파일 다운로드가 차단되어 생긴 것으로, 이 변경 전에도 같은 이유로 실패했다.
- `npm run lint`(0 warnings), `npm run build` 통과.
- 브라우저 흐름 점검(Playwright, 가짜 마이크, 6초 지연 가짜 STT, 실패하는 가짜 평가): 녹음을 멈춘 뒤 다음 문항이 뜨기까지 약 3.3초(진행자 "next" 음성 길이)로, STT를 기다리지 않았다. 8문항 제출 후 결과 화면에 "답변 분석 중 7/8", 기록 화면으로 이동하면 헤더 "분석 중 1" 배지가 보였다. 평가가 끝나자 기록 화면에 실패 토스트가 떴고, 토스트에서 리포트로 이동했다. 마지막 답변(가짜 거부)은 `rejected`로 스냅샷에 들어갔다.

## 남은 위험

- STT 백로그가 길어지면 제출 후 평가 시작까지 대기 시간이 늘어난다. 워커 1개 기준 답변 1개의 전사 시간이 녹음 시간보다 짧아 따라잡을 수 있다고 본다. 밀리면 `WORKER_JOB_TYPES=stt`로 STT 전용 워커를 하나 더 띄운다.
- 사용자는 시험 중에 인식 실패를 바로 알 수 없다. 진행 표시에 "인식되지 않은 답변 N개"를 띄우고, 리포트에서 해당 문항을 인식 불가로 보여 준다.
