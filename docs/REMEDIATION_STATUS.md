# 감사 사항 해결 상태

2026-11-07 KST. [감사 보고서](COMPLIANCE_AUDIT.md)는 2026-11-06의 발견 이력이다. 현재 상태는 이 문서와 각 역할 handoff로 관리한다. 과거 위반을 소급해 준수로 바꾸지 않는다.

사용자가 목표를 명확히 했다: C는 새로 구현하지 않고 A/B의 핵심 기능과 전체 요구사항·API·flowchart 연결을 심화 검증한다. C가 필요한 경계는 명시적인 테스트 대역으로 확인하며 제품 완주 완료로 표시하지 않는다.

## 적용된 기반

- CR orchestrator-01: PR #10에서 승인·병합. contracts v4, orchestration v3, 실제 도구 attribution, nullable tier·strip UTF-8 TTS hash·provider 실제 요청 예산을 명확히 했다. 고정 평가 원문과 API/도메인 DB 스키마는 유지했다.
- 저장소는 rebase merge만 허용한다. main-contract-gates ruleset이 활성화되어 있으며 상세 게이트 적용 여부를 API와 실제 CI로 재확인한다.
- M0: bootstrap PR #1을 독립 브랜치로 재구성·검증하여 main에 병합했다.
- corpus M1: PR #5를 main에 병합했다. M2 확대 자료는 별도 Draft PR #12에서 검증한다.
- 기존 혼합 Pickle PR #8은 닫고 실제 소유 역할의 변경으로 재구성했다.
- 감사·trusted ownership 보강 PR #9는 필수 ownership 성공 확인 후 rebase 방식으로 main에 병합됐다(da004c5). 보호 규칙을 면제하거나 완화하지 않았다.
- CR session-api-01은 PR #14/main 90e7835에 반영됐다. contracts v5는 생성 재전송이 코퍼스 변경에 영향을 받지 않도록 저장 세션 조회 함수를 추가한다.
- CR data-layer-01은 PR #16/main a136406에 반영됐다. contracts v6는 기존 API/DB의 nullable 평가 메타데이터를 공개 함수 타입과 일치시킨다. 런타임·컬럼·평가 기준 변경은 없다.

## 이번에 진행하는 작업

- ownership 검사는 PR 코드/계약을 실행하지 않는 `pull_request_target` workflow에서 main의 신뢰한 검사기/계약과 PR Git 객체를 대조한다. API로 수동 등록한 성공 체크가 필수 게이트로 인정되지 않는 병합 오류를 확인해 native workflow job 이름을 `ownership`으로 맞췄다. main 설치·실제 병합 확인 전에는 기존 일반 PR의 필수 체크를 유지한다. 보호 규칙은 완화하지 않는다.
- checker는 명시적 head를 검사하며 M0 이후 Phase 0 예외 재사용과 로컬 키/데이터/원음 경로를 거부한다. 합성 TTS/시험 음성은 계약이 허용한 소유 경로만 허용한다.
- 기존 역할 브랜치를 최신 main에 다시 맞추고 default origin/main ownership, 역할별 local_checks, 미완료 의존 조건을 handoff에 기록한다.
- I-01/02/04/05/06은 grader, I-03은 data-layer의 수정과 경계 검증을 확인한다. 실제 서비스 검증 전까지 이를 전체 시험 완료로 표시하지 않는다.

## 외부 입력·선행 구현이 필요한 조건

Pickle의 실제 공개 base URL/모델 ID 및 로컬 LLM_API_KEY, 실제 임베딩 적재용 EMBED_API_KEY가 필요하다. C의 TTS·캐릭터·화면 구현과 실제 마이크 완주는 아직 완료되지 않았다. 이 조건들이 필요한 M1/M2/M3/M4 검증을 면제하거나 가짜 성공값으로 대신하지 않는다.

이 파일의 진행 항목은 실행 결과 확인 후 갱신한다. 보고서의 원래 결함 재현 코드는 수정 후 회귀 검증을 대신하는 것이 아니다.

## A/B 심화 검증 결과

[요구사항/flowchart 대조표](CORE_REQUIREMENTS_VERIFICATION.md)와 [고정 검증 기록](compliance/verification-2026-11-07.json)을 추가했다. 독립 역할 모듈의 메모리 조합에서 실제 임시 PostgreSQL·HTTP·작업·결과 저장/복구 **110 passed, skip 0**. 실제 provider/마이크/C 완주와 구분한다. 기존 6개 감사 항목 외 세션/오디오 재전송·임베딩 응답·M1 평가 계획/개발 seed·JSON-only 제공자의 예산 내 수정 요청을 보강했다.
