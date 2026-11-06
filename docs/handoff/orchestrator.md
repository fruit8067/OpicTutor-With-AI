# orchestrator — 감사 사항 해결

## 상태

진행 중, 2026-11-07 KST. CR orchestrator-01, M0, corpus M1이 main에 반영됐다. 현재 ownership CI 보강과 역할별 재검증 중이다. 과거 위반은 감사 이력으로 보존한다.

## 완료한 것

감사 보고서/재현 코드는 PR #9에 있다. 정식 CR #10, ownership 기반 #11, bootstrap #1, corpus M1 #5가 병합됐다. Pickle 혼합 PR #8은 닫았고 나머지 기능 PR은 미완료 조건 때문에 Draft다. 최신 현황은 docs/REMEDIATION_STATUS.md에 기록한다.

## 실행 방법

PowerShell/bash 공통: `python agents/tools/check_ownership.py orchestrator`, `git diff --check origin/main...HEAD`. ownership workflow는 PR마다 실제 CI 결과를 확인한다.

## 공개 함수·화면

CR은 tier nullable 선언·TTS hash 정규화·provider 요청 기록/예산을 명확히 한다. API와 고정 평가 원문은 유지한다.

## 알려진 문제

기능 수정은 data-layer/grader 브랜치에 준비됐다. main에 임의로 합치지 않고 각 역할 검증과 의존 조건을 확인한다. 신뢰한 main 코드만 실행하는 필수 ownership check, 역할별 기본 origin/main 비교와 handoff 갱신을 마무리해야 한다. 실제 서비스/마이크 검증은 별도 조건을 기다린다.

## 다른 에이전트에게 요청

순차적으로 원래 소유 역할에서 수정하고 default origin/main ownership을 사용한다. M0 이후 역할 브랜치를 재구성하고 미충족 local_checks를 기록한다.

## 측정값

ownership 경계 unittest 5개 통과(2.304초), 두 workflow YAML 파싱 성공. trusted contract/head 객체 비교·M0 예외 재사용 거부·합성 음성 허용/로컬 자료 금지를 검증했다. 정확도·외부 요청 요금은 측정하지 않았다. 기존 테스트 82 passed는 결함 해결 증거로 재사용하지 않는다.
