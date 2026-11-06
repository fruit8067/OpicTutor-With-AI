# integrator M3 준비

## 사용자 요청에 따른 Pickle 설정 변경
정식 CR orchestrator-01/v4가 PR #10으로 main에 반영되어 명시적인 Pickle 설정을 요구한다. 기존 혼합 PR #8은 역할별 PR로 이관하고 닫았다.
LLM 키는 os.getenv('LLM_API_KEY')로 읽으며 임베딩은 기존 OpenAI 설정을 유지한다.
과거 조합의 전체 테스트는 82 passed였다. 2026-11-07 A/B 코어 검증은 별도 orchestrator 도구로 101 passed이며 M3 완주가 아니다. 실제 Pickle endpoint/model ID는 사용자 답변 대기 중이며 실제 요청은 보내지 않았다.
이번 브랜치에는 integrator의 자기 소유 파일만 있다. 과거 역할별 커밋/HEAD~1 검사는 기본 ownership을 충족하지 못했으며 그 위반을 감사 기록에 보존했다. HTTP·DB·평가 출력 스키마는 변경하지 않았다.

## 상태
통합 스크립트와 실행 안내를 보존. **M3 완주 미완료** (2026-11-07 KST).
M2 전원 병합 조건이 충족되지 않아 실제 AI·음성·화면 통합은 보류한다.
기존 통합 코드를 보존해 M0 main 기준의 독립 증분으로 재구성했다. 이는 과거 산출물 보존이며 Phase 2 착수/M3 완료가 아니다. M2 충족 전 실제 통합 실행은 진행하지 않는다.
사용자 최신 목표에 따라 C는 새로 만들지 않는다. A/B 요구사항·API·flowchart 검증은 docs/compliance/verify_core.py와 명시적인 경계 대역으로 수행하며 제품/브라우저 완주와 구분한다.

## 완료한 것
- HTTP 전용 e2e_smoke: 실제 8문항 업로드→STT 폴링→submit→결과 폴링, v3 결과/자기소개 배제 검사.
- --fail-cases: 무음 거부·재녹음, 처리 중 업로드, 다른 순서, 중복 업로드·제출, 조기 제출, 반복 결과 조회.
- 합성 MP3를 로컬 WAV로 변환하여 계약의 accepted_mime를 준수.
- RUNBOOK: Windows/bash 설치·초기화·적재·TTS 반입·API·worker·frontend 실행과 수동 검증 절차.

## 실행 방법
[RUNBOOK](../RUNBOOK.md)을 따른다.
PowerShell: `cd backend; .venv/Scripts/python -m scripts.e2e_smoke --level IM2`.
bash: `cd backend && .venv/bin/python -m scripts.e2e_smoke --level IL --fail-cases`.

## 검증 결과
| 항목 | 상태 |
| --- | --- |
| Python 전체 모듈 import / compile | 통과 |
| frontend npm run build | 통과 |
| backend 전체 테스트 | **76 passed, skip 0** (A+B 통합, PostgreSQL 포함) |
| corpus 회귀 테스트 | **3 passed** |
| 실제 HTTP health/docs/openapi | 200 / 200 / 200 |
| 실제 코퍼스 scenarios 조회 | B 반영 후 default/leisure/health 3개 공개. 초기 미준비 상태는 해소 |
| 실제 DB 동시성/마이그레이션 | WSL Docker의 PostgreSQL 16/pgvector에서 통과. DDL 직접 적용 2회 성공 |
| DB/API 8답변 연결 | 세션→준비→8업로드→STT 완료 콜백→중복 제출→결과 조회 10회 통과. TTS URL·STT 계산만 fixture |
| IM2/IL 실제 AI·음성 완주 | 미실행: 다른 PC 구현·합성 음성·키 필요 |
| 실제 마이크·화면·LLM 비용 측정 | 미실행 |

## 연결 버그 수정
현재 없음. 다른 PC의 기능 로직을 대신 구현하지 않았다.

## 남은 문제와 담당
- corpus: Q000·시나리오·VERSION·v3 태그와 확장 코퍼스 빌드.
- worker-stt / grader / tts-host / frontend: 각각의 Phase 1 구현.
- 로컬 환경: Docker Desktop 시작 오류. Windows 프로세스 종료/소켓 정리 시도는 자동 승인 검토에서 정책 차단.
- 대체 검증 DB: WSL 독립 Docker 엔진, `opic-core-a-check-db` 컨테이너와 같은 이름의 전용 볼륨.
  Windows의 127.0.0.1:5432에서 접속. Docker Desktop 소켓이나 기존 볼륨은 정리하지 않았다.
- GitHub 연결 도구의 PR 생성은 403이었으나, 기존 로컬 Git 인증으로 PR 생성까지 완료했다.
- 병합 순서: agent/bootstrap → agent/data-layer → agent/session-api → agent/integrator.
  쌓인 브랜치이므로 비교 기준은 직전 단계. 각 단계의 검증 제한은 개별 handoff에 기록.

## 측정값
실제 완주 등급·STT 지연·평가 지연·토큰·비용은 미측정. 합성/가짜 테스트를 실제 측정으로 표시하지 않는다.

## 최종 실행 확인
- IM2 및 IL --fail-cases를 실제 HTTP 서버에 실행: 두 명령 모두 ready=false를 감지하여 exit 1.
  코퍼스·TTS·다른 PC의 기능 구현이 없으므로 이것은 예상되는 준비 실패이며 완주 통과가 아니다.
- API 모델 필드 30개 모델, 오류 코드 전체, 17개 method/path가 계약 v3와 일치함을 대조했다.
- npm run build 통과. npm run lint는 exit 0, frontend 소유 client stub의 미사용 매개변수 경고만 있음.
- 코드 비교의 공백 오류 없음. .env·data·원음 파일은 커밋하지 않았다.

## 공개 브랜치 및 PR
- [bootstrap #1](https://github.com/fruit8067/OpicTutor-With-AI/pull/1): base main, 검토 가능.
- [data-layer #2](https://github.com/fruit8067/OpicTutor-With-AI/pull/2): base agent/bootstrap, 검토 가능.
- [session-api #3](https://github.com/fruit8067/OpicTutor-With-AI/pull/3): base agent/data-layer, 검토 가능.
- [integrator #4](https://github.com/fruit8067/OpicTutor-With-AI/pull/4): base agent/session-api, Draft.
실제 AI·음성 M3 완주는 미완료이므로 #4를 완료 또는 Ready로 표시하지 않았다.

## Core A 작성 시점의 YAML 완료 조건 재점검 (B 반영 후 변경은 아래 참조)

| 단계·요구 항목 | 현재 근거 | 판정 |
| --- | --- | --- |
| bootstrap 1: ignore·Compose 구성 | 두 출제/프런트 경로 ignore 제외, localhost DB·볼륨·healthcheck 선언 | 코드 완료. Windows Compose 엔진 기동은 로컬 환경 문제로 미검증 |
| bootstrap 2: 설정·오류·스키마·DDL·모듈 골격 | 전체 import, 30개 모델 필드/오류 코드 대조, PostgreSQL 16 DDL 반복 적용 | 검증 완료 |
| bootstrap 3: React/TS·Tailwind v3·타입·호스트 골격 | npm run build 통과, 다른 PC 함수는 명시적인 stub | 골격 완료 |
| bootstrap 4~6: ownership 검사·API_SPEC·이전 안내·handoff | 스크립트와 문서 존재, 단계별 변경 소유권 검사 통과 | 완료 |
| bootstrap done_when | PR #1 open, merged=false | **미완료: orchestrator 병합 필요** |
| data-layer M1 1~3: 풀·이력·트랜잭션·큐 | 실제 DB 동시성·상태·멱등성·오래된 결과 거부 검증 | 코드/로컬 DB 검증 완료 |
| data-layer M1 4~5: 임베딩·재개 가능한 ingest | 배치·차원·메타데이터·재적재 검증. 실제 VERSION·키 없음 | 코드 검증 완료, **실제 코퍼스 적재/비용 미검증** |
| data-layer M1 6~7: reset·개발 seed | reset 실제 실행, seed 함수/CLI 구현. 검토된 Q000/태그 필요 | 코드 완료, **실제 코퍼스 seed 실행 미검증** |
| data-layer M2 8~9: 동시성·인덱스·테스트 | 동시 5요청 단일 행, 10회 완료 단일 전진, 큐 확보/리스 복구, 9개 테스트 통과 | 로컬 검증 완료 |
| data-layer done_when | PR #2 open, 실제 ingest 대기 | **미완료** |
| session-api 1: 시나리오·태그·세트 고정 | 결정적 선택·중복 방지·누락 태그 거부·커버리지 fixture 검증 | 코드 검증 완료. **실제 corpus M1 미반영** |
| session-api 2~3: 전체 API·업로드·앱 실행 | 17개 method/path 대조, 실제 DB 8답변 연결, HTTP 서버·문서 응답 확인 | 코드 검증 완료. **실제 TTS·STT 음성 연결 미검증** |
| session-api done_when | PR #3 open, merged=false | **미완료: 병합 필요** |
| integrator 1: 실행 안내 | RUNBOOK에 PowerShell/bash·TTS 반입·복구 절차 | 작성 완료 |
| integrator 2: HTTP smoke·실제 IM2/IL 결과 | smoke 구현. 두 실행은 ready=false로 exit 1 | **실제 완주 미완료** |
| integrator 3: 실제 실패/복구 및 마이크 증거 | DB/API 범위의 실패 검증만 통과. 실제 TTS 누락/음성/STT/LLM 키/워커/마이크 검증 대기 | **미완료** |
| integrator 4: 지연·토큰·비용 | 실제 평가 실행 없음 | **미측정** |
| integrator 진입/완료 게이트 | 원격 main에 Phase 1 구현 없음, PR #4 Draft | **M2 진입 조건·M3 완료 조건 미충족** |

외부 의존성 재확인: 원격에는 main과 Core A 네 브랜치만 있고 corpus/tts-host/worker-stt/grader/frontend 구현 브랜치가 없다.
현재 설정의 LLM_API_KEY·EMBED_API_KEY 구성 여부는 둘 다 false이며 키 값은 출력하지 않았다.
scenarios.json·VERSION·active_voice.json·IM2/IL 합성 음성 디렉터리가 모두 없다.
이 항목들은 다른 PC 소유 경로 또는 사용자 로컬 설정이므로 Core A에서 임의 구현하거나 준비 완료로 표시하지 않는다.

## 사용자 요청에 따른 B 구현 후 상태

사용자가 B 작업도 요청하여 corpus→grader→worker-stt를 순서대로 구현·push했다.
현재 integrator는 이 세 브랜치의 변경을 모두 포함한다. PR #4의 비교 기준도 agent/worker-stt로 갱신한다.

- corpus [PR #5](https://github.com/fruit8067/OpicTutor-With-AI/pull/5): Q000~Q237, pilot 222/todo 16, 답변 4,284개,
  default/leisure/health 시나리오, corpus 회귀 3개와 API 300 seed 선택 검증.
- grader [PR #6](https://github.com/fruit8067/OpicTutor-With-AI/pull/6): 고정 프롬프트 로드, 엄격한 출력 검증·누출 방지·재시도·평가 작업,
  32개 회귀 테스트와 40시험/5종 함정 계획. 키가 없어 실제 AI·임베딩 정확도/비용 실험은 미실행, Draft.
- worker-stt [PR #7](https://github.com/fruit8067/OpicTutor-With-AI/pull/7): 실제 small.en CPU로 30초 합성 음성 처리→DB done/순서 1→2,
  자신의 워커 자식 프로세스 종료→실제 60초 리스 만료→재시작→attempt 2에서 done/순서 2 확인.
  실제 사용자 마이크 녹음은 미검증, Draft.
- 새 병합/검토 순서: bootstrap #1 → data-layer #2 → session-api #3 → corpus #5 → grader #6 → worker-stt #7 → integrator #4.
- 남은 의존성: C의 TTS·화면 구현과 음성 파일, 로컬 API 키, 실제 외부 평가의 비용 확인·실행,
  실제 마이크 완주와 단계별 PR 병합. B 코드를 작성했다고 전체 M3 완주를 완료로 표시하지 않는다.
- 최종 A+B 테스트: backend 76 passed/skip 0, corpus 3 passed, npm run build 통과.
- 실제 API /scenarios: 200과 default/leisure/health 확인. /health ready=false: DB 코퍼스 외부 임베딩 적재 및 활성 TTS가 아직 필요.
