# develop/v3 에이전트 프롬프트 — 1단계(답변 처리 비동기화) · 2단계(분석 중 화면 이동)

> 이 문서 전체를 에이전트에게 그대로 붙여 넣으세요.
> AI-assisted: this prompt was drafted with help from Claude (Anthropic).

---

## 0. 역할과 작업 환경

너는 OpicTutor-With-AI 저장소에서 **세션 흐름 업그레이드(v3)** 를 맡은 단일 에이전트다. 백엔드·프론트·계약 파일을 모두 건드리는 교차 작업이므로 오케스트레이터 권한으로 진행한다.

- 작업 브랜치: **`develop/v3`** (이미 `develop/v2`의 `d3aa844`에서 로컬로 만들어 둠, 아직 push 안 됨)
- 시작 전에 반드시 읽을 것: `agents/HANDOFF.md`, `agents/orchestration.yaml`, `agents/contracts.yaml`, `docs/API_SPEC.md`, `docs/FLOWCHART.md`
- **작업 트리 주의:** `develop/v2`에 커밋되지 않은 변경이 있다(`README.md`, `backend/app/llm/embeddings.py`, `backend/static/tts/ac3049e033/manifest.json`, `backend/static/tts/ac3049e033/e2e_answer/*` 미추적 폴더). 이 작업과 무관하므로 **절대 stage/commit 하지 말고, 되돌리거나 지우지도 마라.** `git add -A`/`git add .` 금지, 항상 경로를 지정해서 add 한다.
- `git checkout develop/v3` 후 작업. 원격 push와 PR 생성은 사용자가 요청할 때만 한다.
- 커밋 메시지는 저장소 관례대로 한국어 `[feat] …` / `[fix] …` / `[docs] …` 형식. AI 도움을 받은 로직에는 기존 파일들처럼 출처 주석을 남긴다.

## 1. 목표

1. **답변 후 바로 다음 문항:** 녹음 업로드가 접수(202)되면 STT 완료를 기다리지 않고 바로 다음 문항으로 넘어간다. STT는 뒤에서 계속 처리된다.
2. **분석 중 다른 화면 이동:** 제출 후 STT 대기·평가 중에도 사용자가 "내 시험 기록", "환경 점검(새 시험)", 다른 세션의 리포트로 자유롭게 이동할 수 있고, 분석이 끝나면 어느 화면에 있든 알림을 받는다.

이번 범위가 아닌 것: RAG/평가 방식 교체(3단계), STT 모델 변경, 디자인 리뉴얼.

## 2. 현재 코드에서 막혀 있는 지점 (확인 완료)

| 위치 | 현재 동작 |
| --- | --- |
| `backend/app/db/answers.py` `create_answer` | `current_order_no`와 같은 문항만 접수, 같은 문항에 queued/processing 답변이 있으면 `ANSWER_PENDING` |
| `answers.py` `complete_stt` | `in_progress` + `current_order_no == order_no`일 때만 저장하고, **여기서** `current_order_no+1` |
| `answers.py` `reject_stt`, `fail_stt`, `retry_stt` | 모두 `in_progress`이고 현재 문항일 때만 반영 |
| `backend/app/db/evaluations.py` `submit_session` | 건너뛰지 않은 모든 문항에 `stt_status='done'` 채택 답변이 있어야 제출 가능(`NOT_ALL_ANSWERED`). 제출 트랜잭션에서 `new_evaluation` 호출 → `submitted`→`grading` |
| `backend/app/stt/job.py` | 재시도 가능한 오류는 jobs 테이블의 `max_attempts=3`으로 자동 재시도, 소진되면 `fail_stt`. 무음 등은 `reject_stt` |
| `backend/app/grading/prompt.py` / `validate.py` | `stt_status!='done'`이거나 텍스트가 빈 채점 문항은 이미 `unusable_items_required`로 처리됨 |
| `frontend/src/pages/Exam.tsx` | 업로드 후 `poll()`로 STT 완료(`current_order_no > orderNo`)를 기다린 뒤 다음 문항. rejected면 재녹음, failed면 "다시 처리" 버튼 |
| `frontend/src/components/Shell.tsx` | 상단 메뉴 `exam`, `result` 항목이 `to: null`(이동 불가) |
| `frontend/src/pages/Result.tsx` | 이미 `?session_id=` 쿼리를 읽음. 없으면 localStorage 세션 하나 |

## 3. 설계 결정 (이대로 구현)

### 3.1 상태 모델 — 새 상태를 만들지 않고 `submitted`의 의미를 넓힌다

원래 계획서에는 평가 상태에 `waiting_stt`를 추가하는 안이 있었지만, 다음 이유로 **세션 상태 `submitted`를 "제출됨, STT 완료 대기 중"으로 확장**하는 방식을 쓴다.

- `submitted`는 이미 enum·전이표·프론트(`Result.tsx`의 대기 판정, `History.tsx`)에 있다. 지금은 "평가 등록 직전의 짧은 상태"일 뿐이다.
- 평가 행(`evaluations`)을 **평가를 등록하는 순간에만** 만들면, "채택 답변(`selected_answer_ids`)은 등록 시점에 정한다"는 요구가 자연스럽게 지켜지고 `evaluations.status` CHECK를 바꿀 필요가 없다.
- 따라서 **마이그레이션은 원칙적으로 필요 없다.** 세션별 미완료 STT 조회용 인덱스가 실제로 필요하다고 판단될 때만 `backend/migrations/007_async_stt.sql`을 만들고, `test_db_migration.py`가 통과하는지 확인한다.

`contracts.yaml` 수정 내용:
- `session_status.submitted`: "전체 문항 답변 접수(또는 건너뜀) 완료. STT가 모두 끝나면 같은 트랜잭션에서 평가 작업을 등록하고 grading으로 넘어간다"
- `session_transitions`의 `[submitted, grading]` 주석: "마지막 STT 종결 트랜잭션 또는 제출 트랜잭션에서"
- `answer_stt_status.done`: "텍스트·지표 저장 + 채택" (순서 전진 문구 제거)
- `answer_stt_status.rejected` / `failed`: "자동 재시도 소진 후 최종 상태. 평가에서는 인식 불가 문항으로 처리"
- `create_answer`, `complete_stt`, `submit_session`의 함수 설명 주석, `CurrentQuestionOut`/새 응답 모델
- 변경 사유를 `docs/change-requests/orchestrator-06.md`에 기존 change request 형식을 따라 기록

### 3.2 STT 실패·거부 처리 — 자동 재시도 후 "인식 불가"로 평가

사용자는 이미 다음 문항에 가 있으므로 그 자리에서 재녹음하게 하지 않는다.
- 재시도 가능한 오류: 기존 jobs 재시도(최대 3회)를 그대로 쓴다. 소진되면 `failed`.
- `rejected`(무음, 너무 짧음 등)와 최종 `failed`는 **종결 상태**로 보고, 평가에서는 `unusable_items_required`로 들어가게 한다.
- `POST /retry-stt` 엔드포인트는 남겨 두되, 세션이 `in_progress` 또는 `submitted`(평가 등록 전)일 때 **이전 문항이어도** 허용한다. 프론트에서 노출은 4.2 참고.

### 3.3 동시성 규칙

- 세션 행 잠금(`session_for_update`)을 **항상 먼저** 잡는다. `locked_answer`가 이미 이 순서를 지킨다. 새 코드도 같은 순서를 지켜 교착을 피한다.
- 평가 등록은 공용 헬퍼 하나로만 한다. 예: `evaluations.py`에 `maybe_enqueue_evaluation(cur, s)`
  - 조건: `s['status']=='submitted'` 이고 그 세션에 `stt_status IN ('queued','processing')`인 답변이 0개
  - 동작: 문항별 채택 답변을 **지금** 계산 → `new_evaluation(cur, s, 1, selected)` (run_no=1, 멱등 키 `evaluate:{sid}:1`로 중복 등록 방지)
  - 호출 위치: `submit_session`, `complete_stt`, `reject_stt`, `fail_stt` 의 각 트랜잭션 끝. 제출과 마지막 STT 종결 중 **나중에 끝나는 쪽**에서 정확히 한 번 등록된다.
- 문항별 채택 규칙: 건너뛴 문항은 제외. 그 외 문항은 가장 최근 시도(`attempt_no` 최대)를 쓴다. `done`이면 `is_selected=true`인 그 답변, `rejected`/`failed`이면 그 답변 id를 그대로 넣어 스냅샷에 상태가 실리게 한다(`load_exam_snapshot`·`validate.py`가 이 상태를 받아들이는지 테스트로 확인).

## 4. 1단계 구현 — 답변 처리 비동기화

### 4.1 백엔드

1. `create_answer`
   - 검증은 그대로(`in_progress`, `order_no == current_order_no`, 문항 범위).
   - 답변 INSERT + stt 작업 등록과 **같은 트랜잭션에서** `current_order_no+1`.
   - `client_request_id` 멱등성 유지: 같은 요청이 다시 오면 이미 전진한 상태여도 기존 답변을 돌려준다(현재 멱등 처리 경로를 확인하고 order 검증보다 먼저 타는지 점검).
   - 응답에 `current_order_no`, `all_answered`를 포함해 프론트가 바로 다음 문항으로 갈 수 있게 한다.
2. `complete_stt`: 세션이 `in_progress` 또는 `submitted`이면 문항 위치와 관계없이 저장. 순서 전진 코드 제거. 이미 `done`이면 멱등. 세션이 `grading`/`done`/`cancelled` 등이면 늦게 도착한 결과로 보고 무시(False 반환 또는 기존 계약대로).
3. `reject_stt`, `fail_stt`: 같은 조건 완화. 끝에 `maybe_enqueue_evaluation`.
4. `mark_stt_processing`: `in_progress`뿐 아니라 `submitted`에서도 처리 시작 허용. **이걸 빠뜨리면 마지막 답변 STT가 영원히 안 돌아간다.**
5. `skip_question`: 현재 문항 기준 동작 유지. 현재 문항에 대기 중 답변이 있을 수 없는 구조가 되었으므로 해당 검사는 남겨도 무방.
6. `submit_session`: `current_order_no > question_count`(모든 문항 접수 또는 건너뜀)이면 제출 가능. STT 완료 여부는 묻지 않는다. 상태를 `submitted`로 바꾸고 `maybe_enqueue_evaluation` 호출. 반환값: 평가가 등록됐으면 evaluation id, 아직이면 `None` — `routes_results.py`와 `SessionOut` 응답이 이 경우를 처리하게 한다.
7. STT 진행 현황을 응답에 추가: `stt_progress: {total, done, pending, unusable}` (total=건너뛰지 않고 답변이 접수된 문항 수). `CurrentQuestionOut`, `SessionOut`(또는 결과 대기 응답), 2단계의 `/sessions/active`에서 공용으로 쓴다. `schemas`와 `frontend/src/api/types.ts` 동기화.
8. 처리량: 워커 1개로 충분하다고 가정한다. `docker-compose.yml`은 바꾸지 말고, 필요하면 README에 "STT 전용 워커 추가 방법"만 메모한다(README는 작업 트리 변경이 있으니 이번에는 건드리지 않는 것을 권장 — 대신 change request 문서에 기록).

### 4.2 프론트 (`Exam.tsx`)

- 업로드 성공 → STT `poll()`을 기다리지 않고 응답의 `current_order_no`로 바로 다음 문항 로드·재생.
- 화면 한쪽(헤더 근처)에 작은 진행 표시: "답변 분석 중 3/8". 백그라운드로 `stt_progress`를 가볍게 폴링(`lib/usePoll.ts` 재사용, 5초 간격 정도, 탭이 숨겨지면 늦추거나 중지).
- 마지막 문항 업로드(또는 건너뛰기) 직후 바로 `submitSession` 호출 → `/result?session_id=<id>`로 이동.
- 현재 문항 rejected 시 재녹음 안내, failed 시 "다시 처리" 버튼 UI는 제거하거나 진행 표시 안의 작은 안내("인식되지 않은 답변 1개는 평가에서 제외돼요")로 바꾼다. 상단 주석의 상태 다이어그램(9행 근처)도 새 흐름으로 고친다.
- 새로고침·재진입 시(181행 근처 재개 경로): 이전 문항의 STT 대기 때문에 멈추지 말고 `getCurrent` 기준 현재 문항으로 진행.
- `lib/messages.ts`에 새 문구 추가, 기존 `REJECT_TEXT`/`STT_ERROR_TEXT`는 진행 표시 상세에 재사용.

### 4.3 1단계 테스트

`backend/tests`에 추가·수정 (`test_stt_job.py`, `test_api_upload.py`, `test_question_skip.py`, `test_api_db.py` 등 기존 패턴을 따른다):
- 업로드 직후 `current_order_no`가 전진한다 / 같은 `client_request_id` 재요청은 멱등
- 이전 문항 STT 완료·거부·실패가 정상 반영된다
- STT가 남아 있어도 제출 가능 → 상태 `submitted`, 평가 행 없음
- 마지막 STT 완료 시 평가가 정확히 1번 등록 → `grading`
- 제출보다 STT가 먼저 다 끝난 경우 제출 트랜잭션에서 등록
- rejected/failed 문항이 섞여도 평가 스냅샷이 `validate.py`를 통과하고 해당 문항이 unusable로 들어간다
- `submitted` 상태에서도 `mark_stt_processing`이 동작
- 늦게 도착한 STT 결과(세션 `done` 이후)는 무시
- 기존 테스트 중 "STT 완료 후에야 전진" 전제를 검증하던 것은 새 계약에 맞게 수정하고, 커밋 메시지에 어떤 테스트를 왜 바꿨는지 적는다.

커밋 예: `[feat] 답변 업로드 즉시 다음 문항으로 진행하고 STT 완료 시 평가 자동 등록`

## 5. 2단계 구현 — 분석 중 화면 이동

### 5.1 백엔드
- `GET /sessions/active` (인증 필요, `GET /sessions/history`와 같은 사용자 범위 규칙): 현재 사용자의 `in_progress`/`submitted`/`grading` 세션 목록과 각 `stt_progress`, 그리고 `latest_session_id`(가장 최근 결과가 있는 세션)를 반환. 매 5초 호출돼도 가벼운 쿼리로 작성한다. 라우트 순서상 `/sessions/{session_id}`보다 **먼저** 등록해야 `active`가 UUID로 파싱되는 문제를 피한다(`/sessions/history`가 이미 같은 방식).
- `docs/API_SPEC.md`, `contracts.yaml` 엔드포인트 목록 갱신. 테스트 추가(다른 사용자의 세션이 보이지 않는지 포함).

### 5.2 프론트
- **결과 주소에 세션 지정:** 결과 화면으로 가는 모든 이동은 `/result?session_id=<id>` 형식으로 통일(`Exam.tsx`, `History.tsx`, `lib/session.ts`의 `routeFor` 사용처). `Result.tsx`는 쿼리가 있으면 그 세션, 없으면 localStorage(마지막으로 본 세션). localStorage는 "마지막으로 본 세션" 기억 용도로만 쓴다.
- **상단 메뉴(`Shell.tsx`):**
  - "AI 피드백 리포트" → `latest_session_id`가 있으면 `/result?session_id=…`, 없으면 비활성
  - "실전 인터뷰" → `in_progress` 세션이 있으면 `/exam`으로 재개, 없으면 비활성
  - "내 시험 기록", "환경 점검(새 시험)"은 분석 중에도 항상 이동 가능. 새 시험을 시작해도 분석 중인 이전 세션은 백엔드에서 계속 진행되어야 한다(세션 생성 경로가 이전 세션을 취소하지 않는지 확인. `replaces_session_id`는 "설정 변경" 용도이니 분석 중 세션에 쓰이지 않게 한다).
- **전역 분석 상태:** Shell에 `/sessions/active` 폴링 훅(예: `lib/useActiveSessions.ts`). 대기 중 세션이 있을 때만 5초 간격, 없으면 중지. 헤더에 "분석 중 N" 배지. 세션이 `grading`→`done`으로 바뀌면 "리포트가 준비됐어요" 토스트 + 클릭 시 해당 리포트로 이동. `grading_failed`면 실패 토스트. 브라우저 알림(Notification API)은 사용자가 허용했을 때만 보내는 선택 기능으로 넣는다.
- **`History.tsx`:** `submitted`는 "답변 분석 중 3/8", `grading`은 "채점 중" 배지. 대기 중 항목이 있으면 자동 새로고침(같은 훅 재사용 가능).
- 로그인 화면 등 Shell 밖 화면에서는 폴링하지 않는다.

### 5.3 2단계 테스트
- 백엔드: `/sessions/active` 사용자 격리, 상태별 포함 여부
- 프론트: `npm run lint`(0 warnings/errors), `npm run build`(tsc 포함) 통과

커밋 예: `[feat] 분석 중 화면 이동 허용 및 전역 분석 상태 알림 추가`

## 6. 검증 (마지막 단계, 생략 금지)

1. `docker compose -f docker-compose.yml -f data/compose.local.yml up -d db` 후 `cd backend && pytest` 전체 통과
2. `python agents/tools/check_ownership.py` 실행 결과 확인. 교차 작업이라 소유권 경고가 나오면 내용을 change request 문서에 기록(검사 스크립트 자체는 수정하지 않는다)
3. `cd frontend && npm run lint && npm run build`
4. 로컬에서 앱을 띄워 실제 흐름 점검(가능하면 Playwright로):
   - 문항 답변 직후 바로 다음 문항 음성이 재생되는가
   - 진행 표시가 늘어나다가 마지막에 평가로 넘어가는가
   - 제출 직후 "내 시험 기록"으로 이동 → 배지 표시 → 완료 토스트 → 리포트 열림
   - 무음 답변을 하나 섞었을 때 시험이 막히지 않고 리포트에서 해당 문항이 인식 불가로 나오는가
5. 마지막에 사용자에게 보고: 바꾼 계약 항목, 추가/수정한 테스트, 수동 점검 결과, 남은 위험(예: STT 백로그가 길어질 때 대기 시간)

## 7. 하지 말 것

- `develop/v2`의 미커밋 변경 파일을 stage/commit/되돌리기
- `main`이나 `develop/v2`에 직접 커밋·병합, force push
- 평가 프롬프트(`docs/prompts/opic_evaluation_system.md`)·RAG·임베딩 코드 수정 (3단계 범위)
- 테스트를 통과시키려고 검증 로직(`validate.py`)을 느슨하게 만들기 — 스냅샷 쪽을 맞춘다
