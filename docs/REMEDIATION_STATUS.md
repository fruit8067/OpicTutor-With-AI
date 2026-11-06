# 감사 사항 해결 상태

2026-11-07 KST. [감사 보고서](COMPLIANCE_AUDIT.md)는 2026-11-06의 발견 이력이다. 현재 상태는 이 문서와 각 역할 handoff로 관리한다. 과거 위반을 소급해 준수로 바꾸지 않는다.

사용자가 목표를 명확히 했다: C는 새로 구현하지 않고 A/B의 핵심 기능과 전체 요구사항·API·flowchart 연결을 심화 검증한다. C가 필요한 경계는 명시적인 테스트 대역으로 확인하며 제품 완주 완료로 표시하지 않는다.

## 적용된 기반

- CR orchestrator-01: PR #10에서 승인·병합. contracts v4, orchestration v3, 실제 도구 attribution, nullable tier·strip UTF-8 TTS hash·provider 실제 요청 예산을 명확히 했다. 고정 평가 원문과 API/도메인 DB 스키마는 유지했다.
- 저장소는 rebase merge만 허용한다. main-contract-gates ruleset이 활성화되어 있으며 상세 게이트 적용 여부를 API와 실제 CI로 재확인한다.
- M0: bootstrap PR #1을 독립 브랜치로 재구성·검증하여 main에 병합했다.
- corpus M1: PR #5, M2 확대 자료: PR #12를 main에 병합했다.
- 기존 혼합 Pickle PR #8은 닫고 실제 소유 역할의 변경으로 재구성했다.
- 감사·trusted ownership 보강 PR #9는 필수 ownership 성공 확인 후 rebase 방식으로 main에 병합됐다(da004c5). 보호 규칙을 면제하거나 완화하지 않았다.
- CR session-api-01은 PR #14/main 90e7835에 반영됐다. contracts v5는 생성 재전송이 코퍼스 변경에 영향을 받지 않도록 저장 세션 조회 함수를 추가한다.
- CR data-layer-01은 PR #16/main a136406에 반영됐다. contracts v6는 기존 API/DB의 nullable 평가 메타데이터를 공개 함수 타입과 일치시킨다. 런타임·컬럼·평가 기준 변경은 없다.
- A/B 코어 대조표·재현·110개 검증 기록은 PR #13/main 482e273에 병합됐다. 실제 서비스가 필요한 기능 PR의 Draft 상태는 유지한다.

## 이번에 진행하는 작업

- ownership 검사는 PR 코드/계약을 실행하지 않는 `pull_request_target` workflow에서 main의 신뢰한 검사기/계약과 PR Git 객체를 대조한다. API로 수동 등록한 성공 체크의 병합 오류를 해소하기 위해 native workflow job 이름을 `ownership`으로 맞추고 PR #13으로 main에 설치했다. 일반 PR 체크는 `ownership-local`로 분리해 native trusted job만 필수 ownership을 제공하는 실제 CI/병합을 확인한다. 보호 규칙과 필수 source app은 유지한다.
- checker는 명시적 head를 검사하며 M0 이후 Phase 0 예외 재사용과 로컬 키/데이터/원음 경로를 거부한다. 합성 TTS/시험 음성은 계약이 허용한 소유 경로만 허용한다.
- 기존 역할 브랜치를 최신 main에 다시 맞추고 default origin/main ownership, 역할별 local_checks, 미완료 의존 조건을 handoff에 기록한다.
- I-01/02/04/05/06은 grader, I-03은 data-layer의 수정과 경계 검증을 확인한다. 실제 서비스 검증 전까지 이를 전체 시험 완료로 표시하지 않는다.

## 외부 입력·선행 구현이 필요한 조건

업데이트: .env 저장 후 실제 Pickle 연결, M1/M2 ingest(4,539문서/4,522벡터/중복 0요청), IL v4 실제 평가 done 저장을 확인했다. 연결·적재 증거는 docs/compliance/live-*-2026-11-07.json에 있다. 상대 경로를 강제하고 다른 checkout/cwd 및 native STT도 통과했다. v5 전체 40시험은 5건 정상 후 6번째에 HTTP429/quota_exhausted로 중단됐다.

Pickle 주소 `https://llm.pcl.kr/v1`와 모델 `pickle-general`, large3072·상대 경로 설정이 main에 반영됐다. 사용자가 학교 크레딧 약 $10 사용을 허용했지만 현재 키의 공급자 할당량 거절이 확인되어 추가 호출은 중단했다. 실제 달러 잔액은 관측하지 않았다. 정확도/함정/반복·C·실제 마이크 완주는 미완료이며 M2/M3/M4 검증을 면제하지 않는다.

이 파일의 진행 항목은 실행 결과 확인 후 갱신한다. 보고서의 원래 결함 재현 코드는 수정 후 회귀 검증을 대신하는 것이 아니다.

## A/B 심화 검증 결과

최신 로컬 회귀는 **128 passed/skip 0/13.65초**다. 독립 API/STT CLI도 실제 HTTP/로컬 Whisper/DB로 검증했다. 데이터 M1/M2와 corpus M2는 병합됐다. F5 전체 40시험은 정상 5건 뒤 학교 API 429/quota_exhausted로 중단됐고 작은 요청도 거절됐다. 완료 5건과 중단 이력을 유지하는 재개 검증은 통과했다. 남은 35시험·반복/함정 및 마이크 검증은 미완료다.

초기 v7 검증은 [large/3072 기록](compliance/large-embedding-2026-11-07.json)의 114 passed / skip 0 / 12.20초였다. 이때 공개 함수64/API 모델29/경로17 차이0, 실제 유료 호출0이었다. 이후 실제 M2 적재가 완료됐으며 최신 결과는 위 128개 및 별도 실사용 기록이다. data-layer는 원문 보존 전진 마이그레이션·exact cosine·모델/제공자 프로필별 재임베딩/검색을, grader는 os.getenv Pickle 키 별칭을 자기 PR에 push했다. 이전 기록을 이력으로 보존한다.

[요구사항/flowchart 대조표](CORE_REQUIREMENTS_VERIFICATION.md)와 [고정 검증 기록](compliance/verification-2026-11-07.json)을 추가했다. 독립 역할 모듈의 메모리 조합에서 실제 임시 PostgreSQL·HTTP·작업·결과 저장/복구 **110 passed, skip 0**. 실제 provider/마이크/C 완주와 구분한다. 기존 6개 감사 항목 외 세션/오디오 재전송·임베딩 응답·M1 평가 계획/개발 seed·JSON-only 제공자의 예산 내 수정 요청을 보강했다.

후속 현재 상태 검증에서 실제 Whisper/worker CLI로 합성 30초 음성 8개를 HTTP 업로드부터 제출 대기까지 처리했다. 모두 done/attempt 1, 순서 1→9, 모델 네트워크/외부 평가·임베딩 호출 없음. 단일 5.500초, 8개 각각 5.438~5.594초(시작 포함). ASR 추론 대역을 제거한 별도 증거이며 실제 마이크/LLM 평가 품질이나 C 완주를 대신하지 않는다.
