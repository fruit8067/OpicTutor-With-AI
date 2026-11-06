# integrator M3 준비

## 상태
통합 스크립트와 실행 안내 작성. **M3 완주 미완료** (2026-11-06 KST).
M2 전원 병합 조건이 충족되지 않아 실제 AI·음성·화면 통합은 보류한다.
브랜치는 agent/session-api 위에 쌓았다. main에 직접 push하지 않았다.

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
| backend 전체 테스트 | **21 passed, skip 0** (실제 PostgreSQL 포함) |
| 실제 HTTP health/docs/openapi | 200 / 200 / 200 |
| 실제 코퍼스 scenarios 조회 | 422 SCENARIO_UNAVAILABLE: corpus M1 자료 미준비 |
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
- GitHub 연결: PR 생성 권한 403. 각 단계 브랜치 push는 성공.
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
