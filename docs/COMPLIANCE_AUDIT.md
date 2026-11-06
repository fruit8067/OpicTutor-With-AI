# 계약·인수인계·오케스트레이션 감사

> 아래는 2026-11-06 감사 당시의 판정과 이력이다. 이후 해결 진행과 현재 상태는 [해결 상태](REMEDIATION_STATUS.md)를 참고한다.

감사일: 2026-11-06 KST. 작성: OpenAI Codex. 사용자가 기존 구현 목표보다 이 감사를 우선하도록 요청했다.

**판정: 준수 완료가 아니다. A/B 구현과 일부 로컬 검증은 있지만, 정해진 단계·브랜치·계약 변경 절차를 위반했고 구현 결함도 재현했다. M0~M4 및 어느 역할의 `done_when`도 완료로 선언할 수 없다. 기존 기능 PR을 현재 상태로 병합하면 안 된다.**

## 범위와 기준

- 정본: `origin/main` = `a1c456cbf0ea0f95eff90fa1b52b522e99f33199`, contracts v3, orchestration v2, HANDOFF.md. 감사 중 fetch로 확인했다.
- 구현: `orchestrator/pickle-llm` = `ee90ba4a65bf24e8842839aff72333f367ac4041` 및 그 선행 A/B 브랜치·PR #1~8.
- 구현 브랜치의 contracts v4는 **미병합 제안**이다. 변경한 계약만 기준으로 삼아 기존 일탈을 적합으로 처리하지 않았다.
- 사용자 지시 범위는 처음 A, 이후 B 추가, 이후 Pickle LLM/`os.getenv` 설정 변경이다. C 기능 구현은 수행하지 않았다. 초기 bootstrap의 C 골격 생성은 Phase 0 예외에 해당한다.
- 코드·Git 이력·handoff·PR 메타데이터·GitHub 설정을 대조했다. 현재 감사는 기존 작업에 대한 자체 감사이며, 독립 reviewer/M4 검토를 대신하지 않는다.

코드 위치는 아래에 `경로:행`으로 표시한다. 구현 파일은 [감사 대상 커밋](https://github.com/fruit8067/OpicTutor-With-AI/tree/ee90ba4a65bf24e8842839aff72333f367ac4041)에서 확인할 수 있다.

## 1. 확인된 절차 위반 및 설정 미충족

| ID / 우선순위 | 기준 | 실제 행위·상태 | 영향 / 필요한 처리 |
| --- | --- | --- | --- |
| P-01 / 높음 | orchestration:87,91,95 — M0 병합 후 Phase 1, M0 main에서 분기, M2 후 integrator | main에는 bootstrap조차 병합되지 않았는데 data-layer·session-api·grader·worker 및 integrator까지 진행했다. | 코드 작성·로컬 검증을 마일스톤 완료와 구분해야 한다. 정해진 병합 게이트를 건너뛰었다. |
| P-02 / 높음 | orchestration:114~116,157; HANDOFF:93~100 — 역할별 main 기반 PR·지정 병합 순서 | PR을 `main → bootstrap → data-layer → session-api → corpus → grader → worker-stt → integrator → Pickle` 순으로 쌓았다. | 기존 PR 의존 구조로는 지정된 M1/M2 순서로 독립 검토·병합할 수 없다. 아직 실제 병합은 없으므로 **잘못된 순서로 main에 병합한 사실은 없다**. |
| P-03 / 높음 | orchestration:160~162 — 기본 origin/main 기준 ownership + local_checks | 이전 역할 브랜치를 `--base`로 사용해 역할별 증분만 검사했다. Pickle 변경은 같은 브랜치에서 역할별 커밋을 HEAD~1과 비교했다. | 증분 검사 통과는 규정의 기본 검사 통과가 아니다. 아래 소유권 표 참조. |
| P-04 / 높음 | orchestration:193~200; HANDOFF CR 절차 — CR 파일, 승인 기록, 버전 증가, main 반영·공지 | 사용자 요청에 따라 v4와 설정을 만들었지만 `docs/change-requests/`에는 .gitkeep만 있다. 브랜치도 `orchestrator/cr-<id>-<NN>` 형식이 아니다. 한 PR에 bootstrap/grader/integrator 변경이 함께 있다. | 요청 내용은 사용자 승인 범위이나 **정식 CR·역할별 브랜치·배포 절차는 미준수**다. v4를 팀에 반영된 정본으로 부르면 안 된다. |
| P-05 / 높음 | orchestration:155~156; HANDOFF:36~80 — rebase only, main ruleset, LF 통일 | GitHub: allow_merge_commit=true, allow_squash_merge=true, allow_rebase_merge=true. main protected=false, rulesets=[], required status checks 없음. `.gitattributes` 없음. | 병합 방식·PR 강제·linear history·ownership 등 필수 정책이 강제되지 않는다. 저장소 설정은 이번 감사에서 변경하지 않았다. |
| P-06 / 중간 | HANDOFF:112 — ownership workflow는 선택 권장; orchestration:155 — ownership status 필수 | `.github/workflows/ownership.yml` 없음. bootstrap/Pickle head의 check-runs도 빈 목록. | workflow 파일 자체를 필수라고 오독하지 않는다. 다만 필수 ownership status를 제공하는 다른 체크도 확인되지 않았다. |
| P-07 / 중간 | HANDOFF:263,379 — `git add .`/`-A` 금지 | 초기 bootstrap 준비 중 `git add .`를 사용했다. | 대화의 실행 이력에 근거한 실제 절차 위반이다. Git 객체에는 staging 명령이 기록되지 않는다. 이번 경로/키 패턴 검사에서 금지 자료 커밋은 발견하지 않았다. |
| P-08 / 중간 | orchestration:181, HANDOFF:218,275 — 30분 내 handoff·Draft PR | corpus 첫 커밋 17:55:51 KST, PR #5 생성 18:31:18 KST: 첫 커밋보다도 35분27초 뒤다. #1~3,#5가 감사 시작 시 Ready였다. | corpus의 PR 공개 30분 조건은 미준수다. 나머지 역할은 정확한 작업 시작 시각과 최초 Draft 여부를 모두 입증할 수 없어 일괄 적합 판정하지 않는다. |
| P-09 / 낮음 | orchestration:158,239~240 — 명시된 attribution 형식 | 커밋 본문은 `AI-assisted (OpenAI Codex)`로 실제 도구를 표기했다. `001_init.sql`, `rag_docs/scripts/build_corpus.py`는 첫 줄 AI-assisted 표기가 없다. | Claude라는 문구를 그대로 쓰라는 형식과 불일치한다. 실제 사용하지 않은 Claude로 허위 표기해 해결할 사안은 아니다. 정책 문구 조정은 별도 검토해야 한다. |

### 소유권 검사의 구분

기존 검사기의 `matches`와 계약의 첫 일치 규칙을 그대로 사용해 각 브랜치의 파일 집합을 대조했다.

| 역할 | origin/main 기준 타 소유 파일 수 | 기존 stacked PR의 자기 증분 |
| --- | ---: | --- |
| bootstrap | 일반 검사 79, `--phase0` 예외 적용 대상 | 골격 생성 예외. 타 역할 파일을 만들었다는 이유만으로 위반 처리하지 않음 |
| data-layer | 79 | 17개 파일, 소유권 위반 0 |
| session-api | 88 | 12개 파일, 소유권 위반 0 |
| corpus | 102 | 18개 파일, 소유권 위반 0 |
| grader | 112 | 20개 파일, 소유권 위반 0 |
| worker-stt | 123 | 15개 파일, 소유권 위반 0 |
| integrator | 139 | 3개 파일, 소유권 위반 0 |

상속된 다른 역할의 변경 때문에 생긴 실패를, 그 역할이 남의 구현을 직접 수정했다는 증거로 해석하지 않는다. 그러나 기본 ownership 게이트가 통과하지 않는 브랜치 구조인 것은 사실이다. 현재 Pickle 브랜치에서 기본 `grader` 검사를 직접 실행해도 121개 파일을 거부했다. 역할별 커밋 접두어만으로 혼합 PR의 소유권 문제가 해결되지는 않는다.

## 2. 재현한 구현 결함과 인터페이스 불일치

### I-01 / 높음 — 기술적 결측을 수행 실패로 수용

- 위치: `backend/app/grading/validate.py:117`~122.
- 기준: 시스템 프롬프트 42행은 기술적 결측을 `not_observed`로 두도록 명시한다. grader YAML도 기술적 결측은 실패가 아니라고 한다.
- 재현: 8번만 `stt_status='failed', stt_text=''`로 만들고 scope와 item을 정상적인 결측 표현으로 맞췄다. 그 문항의 fact를 `status='not_demonstrated', order_no=8, quote=None`로 넣어도 `validate_output`이 수용했다. `demonstrated`도 수용했다.
- 영향: 인용이 null이면 유효 답변 여부를 검사하지 않아, 확인 불가를 수행 실패·성공으로 제시할 수 있다. §10의 명시적 null 규칙만 검사한 것으로는 고정 평가 원칙을 지키지 못한다.
- 담당: grader. 결측 문항의 fact 상태 검증과 이 경우의 회귀 검증이 필요하다.

### I-02 / 중간 — RAG 실제 자료와 기록한 corpus_version 불일치

- 위치: `backend/app/grading/evidence.py:19,25`~27.
- 재현: 현재 버전을 `current-v2`, 직접 조회와 유사 검색의 자료를 `old-v1`로 설정했다. 직접 조회는 배제했지만 fallback에서 같은 구버전 자료를 다시 채택했다. 반환은 `corpus_version='current-v2'`, retrieved ID는 구버전 `OLD-IM2-stt`였다.
- 영향: 평가 기록의 버전으로 사용한 증거를 재현할 수 없다. 이는 명시되지 않은 검색 시그니처를 임의로 바꾸라는 요구가 아니라, 현재 구현의 버전 선택·기록 일관성 문제다.
- 담당: grader/data-layer. fallback과 대조 세트 확장에도 동일한 버전 정책을 적용해야 한다.

### I-03 / 중간 — TTS 해시 정규화 불일치

- 위치: `backend/app/db/tts.py:33`; 기준: `agents/PC-C_media-ui/1_tts-host.yaml:23`.
- tts-host 지시는 UTF-8 텍스트의 **앞뒤 공백을 제거한** SHA1이다. DB의 준비 완료 조건은 원문 `q.question_text`의 SHA1을 비교한다.
- 재현: `' Question with whitespace?\n'`의 `.strip()` 해시와 실제 DB predicate를 비교한 결과 `accepts_host_hash=false`.
- 영향: 명세대로 생성한 TTS가 있어도 경계 공백이 있는 질문의 prepare가 실패할 수 있다. 현재 코퍼스에서 실제 실패가 발생했다거나 C 구현을 실행했다는 뜻은 아니다.
- 담당: data-layer/tts-host. 계약의 간략한 `sha1(utf-8 text)` 표현과 상세 역할 지시의 정규화 규칙을 일치시켜야 한다.

### I-04 / 중간 — HTTP 408 재시도 오류 분류 누락

- 위치: `backend/app/llm/chat.py:70`; 기준: grader YAML:35의 타임아웃 → LLMTransientError.
- 실제 설치 SDK와 `httpx.MockTransport`로 408 응답을 재현했더니 `APIStatusError`가 그대로 나왔다. 클라이언트의 `max_retries=0`이고 service는 `LLMTransientError`만 재시도한다.
- 영향: HTTP timeout 응답은 정해진 2초/4초 재시도 없이 EVAL_INTERNAL로 끝날 수 있다. 연결/클라이언트 타임아웃은 별도로 처리되므로 타임아웃 처리가 전부 없다고 표현하지 않는다.
- 담당: grader.

### I-05 / 중간 — JSON 대체 경로에서 실제 요청 수 과소 기록

- 위치: `backend/app/llm/chat.py:39`~54, `backend/app/grading/service.py:29,36`.
- 기준: grader YAML:66의 모든 호출 `db.log_ai_request` 기록.
- 재현: 첫 parse 요청에 JSON schema 미지원 400, 다음 JSON object 요청에 유효 결과를 반환했다. HTTP 요청은 **2회**, ai_requests 기록은 **1행**, meta.llm_calls는 **1**이었다.
- 영향: 실패한 협상 요청이 누락되어 실제 요청 수·재시도 예산 관찰이 부정확하다. 그 400 응답에 요금이 청구된다고 가정한 것은 아니다.
- 담당: grader. 논리적 평가 시도와 실제 provider 요청을 구분해 기록·예산 기준을 명확히 해야 한다.

### I-06 / 낮음 — 선언된 공개 시그니처 불일치

- app.db/dev, errors, embeddings, chat, exam, stt, grading의 계약 공개 함수 63개를 AST/실제 함수와 비교했다. 인자 이름·기본값·타입 주석·반환 주석 기준 차이는 2개였다.
- `app.grading.evaluate_exam`: `job_id: UUID | None`와 `-> tuple[EvaluationResult, dict]` 주석 누락. 현재 호출 방식은 호환되지만 “이름·인자·반환형을 바꾸지 않는다”는 선언과 다르다.
- `tier_of`: 계약은 `str -> dict`, 구현은 `str | None -> dict | None`. **이 항목은 문서 모순도 있다.** grader YAML:62는 null 입력 시 null 반환을 요구한다. nullable 동작을 제거해 맞추면 오히려 기능 요구를 어긴다. 정식 CR로 선언을 정리해야 한다.

## 3. HANDOFF 적용 상태

7개 역할의 handoff 파일은 존재하고 실행 명령·테스트 결과·막힌 이유를 상당 부분 기록했다. 그러나 완전하게 적용됐다고 할 수 없다.

- data-layer의 알려진 문제에는 “corpus M1의 Q000·VERSION·태그가 아직 없음”이 남아 있다. 최종 합성 브랜치에는 이 자료가 있으므로 현재 통합 상태로 읽으면 낡은 내용이다. 역할 브랜치 당시 상태와 이후 통합 상태를 구분해 갱신해야 한다.
- bootstrap은 공개 함수·요청·측정값이 지정된 구조로 충분히 정리되지 않았다. session-api는 측정값 섹션이 없고, grader·worker-stt는 공개 인터페이스·다른 역할에 대한 요청이 지정된 형태로 모두 정리되지 않았다. 일부 내용은 다른 절에 있으므로 단순히 제목이 다르다는 이유만으로 전체 내용 누락이라고 판단하지 않는다.
- grader와 worker-stt는 실제 LLM 평가/마이크 측정을 하지 않았음을 기록했다. integrator도 초기 A 당시 결과와 B 반영 이후를 구분했다. 이 한계 표시는 유지해야 한다.
- `M1/M2 코드·로컬 DB 검증 완료`라는 data-layer 표현은 ingest 실제 적재·local_checks·병합까지 완료했다는 뜻으로 읽히면 과장이다. 코드·fixture 검증 완료로 한정해야 한다.
- HANDOFF:109는 병합 전에 done_when을 요구하지만 역할 YAML의 done_when에는 이미 PR이 병합되어야 한다는 조건이 있다. 순환 조건이다. “병합 전 실행 기준”과 “병합 후 완료”를 구분하는 문서 정리가 필요하다. 이 모순을 이용해 모든 Ready 상태를 자동 적합으로 처리하지 않았다.

## 4. 미완료 게이트

| 역할 / 마일스톤 | 확인된 것 | 남은 필수 조건 |
| --- | --- | --- |
| bootstrap / M0 | 골격·API 스키마·로컬 build/import | bootstrap main 병합, 선행 LF·GitHub 정책 준비 |
| data-layer / M1·M2 | 실제 DB 동시성·멱등·리스·fixture ingest 검증 | 실제 코퍼스 임베딩/적재·건수/시간, 기본 ownership, 지정 순서 M1·M2 병합 |
| session-api / M2 | 실제 DB+TestClient 8답변 흐름 | 실제 TTS/STT 연결, 기본 ownership, M2 병합 |
| corpus / M2 | 빌드·태그·시나리오; pilot 222, todo 16 | 정해진 M1 공개·병합 흐름, M2 병합 |
| grader / M2 | 형식·규칙·재시도 단위 검증, 40시험 계획 | I-01/02/04/05/06 해결; 실제 평가·함정/반복 리포트·토큰/비용, 필요 시 템플릿 반복, M2 병합 |
| worker-stt / M2 | 로컬 합성 음성 Whisper, 실제 프로세스 종료 후 60초 리스 복구 | 실제 마이크 발화 검증, 기본 ownership, M2 병합 |
| integrator / M3 | HTTP smoke 도구·runbook·부분 실패 조건 | M2 선행 병합, 실제 TTS/캐릭터/화면, IM2·IL 음성 완주, 실제 마이크 완주·증거, 실제 평가/비용, M3 병합 |
| reviewer / M4 | 미수행 | 독립 리뷰·docs/REVIEW.md·중대 문제 0 |

Pickle의 공개 base URL·정확한 모델 ID 및 실제 키가 아직 주어지지 않았다. `os.getenv('LLM_API_KEY')` 지원은 구현됐지만 Pickle의 실제 연결·구조화 출력 지원·응답 품질을 검증한 것은 아니다. 임베딩은 기존 OpenAI 설정을 유지하며 실제 적재/호출을 수행하지 않았다. TTS·프런트엔드는 골격 상태이므로 앱 완성이나 실제 음성 시험 완주로 표시할 수 없다.

## 5. 확인된 준수 사항과 검증 한계

- `docs/prompts/opic_evaluation_system.md`는 main 원본과 Git diff가 없다. 기존 prompt 동일성 검증도 통과한다. 숫자 dimension_scores를 도입하지 않았다.
- API 스키마 29개의 최상위 필드 집합에 차이가 없다. OpenAPI 기준 계약 엔드포인트 17개가 존재하고 명시된 기본 성공 status가 일치한다. 이것만으로 모든 응답의 의미·동시성·외부 서비스를 검증한 것은 아니다.
- 공개 함수 비교 63개 중 위의 2개 외 시그니처 차이는 없었다. C stub의 존재는 C 구현 완료를 의미하지 않는다.
- 001_init의 도메인 테이블 DDL은 계약과 일치한다. 문자열 비교의 추가 차이는 updated_at trigger 설치 DO 블록이다. 002에는 warmup 유일 제약과 인덱스가 있고 pool에는 내부 schema_migrations가 있다. 도메인 컬럼을 임의로 추가한 증거로 해석하지 않는다.
- 기존 역할 PR의 자기 증분에서는 bootstrap 예외를 제외한 소유권 위반을 찾지 않았다. integrator가 다른 역할 기능을 대신 구현한 증분도 없었다.
- main 직접 push·main 병합은 수행하지 않았다. rebase 후에는 `--force-with-lease`를 사용했고 plain `--force`를 쓰지 않았다. main SHA는 감사 전후 동일하다. 모든 과거 원격 동작을 Git 객체만으로 증명할 수는 없으며 대화 실행 이력도 대조했다.
- 현재 추적 파일과 이번 작업에서 추가된 이력의 경로에 `.env` 실파일·data/·음성/모델 파일 커밋은 없었다. `.env.example`은 예시다. 추가/변경 파일에서 선택한 OpenAI/GitHub 키·private key 패턴도 탐지되지 않았다. 전면 보안 감사를 완료했다는 뜻은 아니다.
- 실제 사용자 마이크 녹음을 수집하지 않았다. STT 측정은 로컬 합성 음성이다. 외부 LLM/임베딩 유료 호출은 수행하지 않았다. 모델 다운로드와 GitHub·문서·패키지 네트워크 사용은 있었다.

이번 재검증: `backend/.venv/Scripts/python -m pytest tests -q` → **82 passed in 4.88s**, skip 없음. 테스트와 위의 결함 재현은 양립한다. 기존 테스트가 이 경계를 다루지 못했다.

## 6. 이번 감사에서 실제로 바꾼 것

1. Ready였던 PR #1, #2, #3, #5를 Draft로 전환했다. 기존 #4, #6, #7, #8도 Draft다. main이나 기능 코드는 변경하지 않았다.
2. main에서 새 `orchestrator/compliance-audit` worktree/브랜치를 만들었다. 감사 문서와 재현 스크립트만 담아 기존 stacked 변경을 섞지 않았다.
3. 과거 절차 위반은 사후 적합으로 바꾸거나 승인 날짜를 소급하지 않았다. contract/HANDOFF/orchestration을 완화하지 않았다. GitHub 보호 설정·기존 PR base·기능 코드는 수정하지 않았다.

## 7. 재현 방법과 후속 처리 순서

감사 대상 구현 worktree와 그 가상환경이 있는 상태에서 다음을 실행한다. 재현 스크립트는 실제 provider 네트워크 대신 MockTransport/메모리 대역을 사용하며, DB에서는 해시 비교 SELECT만 한다. 경로를 인자로 받는다.

```powershell
& 'C:/Users/fruit/Documents/OpicTutor/OpicTutor-With-AI/backend/.venv/Scripts/python.exe' `
  'C:/Users/fruit/Documents/OpicTutor/OpicTutor-audit/docs/compliance/probe.py' `
  'C:/Users/fruit/Documents/OpicTutor/OpicTutor-With-AI'
```

1. orchestrator가 LF·저장소 보호/ownership 정책을 정식 PR·설정 절차로 준비한다. main 자동 병합으로 이를 건너뛰지 않는다.
2. 승인된 bootstrap M0를 기준으로 역할별 증분을 지정된 main 기반 브랜치에 재구성한다. 기존 stacked PR을 그대로 순서대로 합쳐 해결했다고 주장하지 않는다.
3. Pickle 변경과 nullable tier 시그니처·문서 모순에 CR 기록을 만들고 사용자 지시와 형식적 승인 상태를 명시한다. v4는 그 전까지 제안으로 취급한다.
4. I-01~06을 원래 소유자 브랜치에서 수정·재검증하고 handoff를 최신화한다. 이번 감사는 결함 확인 단계이며 이 수정들이 끝났다고 표시하지 않는다.
5. 실제 키/모델 정보·C 구현·음성 자료가 준비되면 지정된 local_checks와 M1/M2/M3/M4를 순서대로 수행한다. 실제 평가 전 정확도나 비용을 측정값으로 기입하지 않는다.

기존 PR: [#1](https://github.com/fruit8067/OpicTutor-With-AI/pull/1), [#2](https://github.com/fruit8067/OpicTutor-With-AI/pull/2), [#3](https://github.com/fruit8067/OpicTutor-With-AI/pull/3), [#4](https://github.com/fruit8067/OpicTutor-With-AI/pull/4), [#5](https://github.com/fruit8067/OpicTutor-With-AI/pull/5), [#6](https://github.com/fruit8067/OpicTutor-With-AI/pull/6), [#7](https://github.com/fruit8067/OpicTutor-With-AI/pull/7), [#8](https://github.com/fruit8067/OpicTutor-With-AI/pull/8).
