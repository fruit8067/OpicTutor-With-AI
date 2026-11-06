# orchestrator — 감사 사항 해결

## 상태

진행 중, 2026-11-07 KST. CR orchestrator-01/session-api-01, M0, corpus M1, trusted ownership이 main에 반영됐다. C는 추가하지 않고 A/B 요구사항·API·flowchart 연결을 심화 검증한다. 과거 위반은 감사 이력으로 보존한다.

## 완료한 것

감사 보고서/재현 코드는 PR #9에 있다. 정식 CR #10, ownership 기반 #11, bootstrap #1, corpus M1 #5가 병합됐다. Pickle 혼합 PR #8은 닫았고 나머지 기능 PR은 미완료 조건 때문에 Draft다. 최신 현황은 docs/REMEDIATION_STATUS.md에 기록한다.

## 실행 방법

PowerShell/bash 공통: `python agents/tools/check_ownership.py orchestrator`, `git diff --check origin/main...HEAD`. ownership workflow는 PR마다 실제 CI 결과를 확인한다.

## 공개 함수·화면

CR은 tier nullable 선언·TTS hash 정규화·provider 요청 기록/예산을 명확히 한다. API와 고정 평가 원문은 유지한다.

## 알려진 문제

기능 수정은 각 역할 PR에 push했다. 실제 서비스 키/모델/주소 부재로 ingest·평가 정확도 local_checks가 남아 있다. C를 새로 구현하지 않으며 M2/M3 전체 완료를 주장하지 않는다. 현재 A/B 코어 구현 검증은 docs/CORE_REQUIREMENTS_VERIFICATION.md에 기록한다.

## 다른 에이전트에게 요청

순차적으로 원래 소유 역할에서 수정하고 default origin/main ownership을 사용한다. M0 이후 역할 브랜치를 재구성하고 미충족 local_checks를 기록한다.

## 측정값

ownership 경계 unittest 5개 통과(2.304초), 두 workflow YAML 파싱 성공. trusted contract/head 객체 비교·M0 예외 재사용 거부·합성 음성 허용/로컬 자료 금지를 검증했다. 정확도·외부 요청 요금은 측정하지 않았다. 기존 테스트 82 passed는 결함 해결 증거로 재사용하지 않는다.
이번 A/B 코어 조합은 깨끗한 역할 커밋을 대상으로 전용 임시 DB에서 104 passed, skip 0, 5.56초다. HTTP/queue/STT 저장/평가 검증/결과 재조회/401 후 재평가를 연결했으며 추론과 C 경계는 fixture다. 실제 외부 LLM/임베딩 호출은 0회다.
