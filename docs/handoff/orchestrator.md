# orchestrator — 감사 사항 해결

## 상태

진행 중, 2026-11-06 KST. CR orchestrator-01 승인 범위의 계약·절차 복구부터 수행한다. 과거 위반은 감사 이력으로 보존한다.

## 완료한 것

감사 보고서/재현 코드는 PR #9에 있다. 기존 기능 PR #1~8을 Draft로 전환했다. 정식 CR을 접수했다.

## 실행 방법

PowerShell/bash 공통: `python agents/tools/check_ownership.py orchestrator`, `git diff --check origin/main...HEAD`. ownership workflow는 PR마다 실제 CI 결과를 확인한다.

## 공개 함수·화면

CR은 tier nullable 선언·TTS hash 정규화·provider 요청 기록/예산을 명확히 한다. API와 고정 평가 원문은 유지한다.

## 알려진 문제

기존 기능 코드 결함 I-01~06 수정·검증, main 보호 설정 적용, 역할별 브랜치 재구성과 handoff 갱신이 남았다. 실제 서비스/마이크 검증은 별도 조건을 기다린다.

## 다른 에이전트에게 요청

순차적으로 원래 소유 역할에서 수정하고 default origin/main ownership을 사용한다. M0 이후 역할 브랜치를 재구성하고 미충족 local_checks를 기록한다.

## 측정값

이 단계는 운영/계약 준비다. 정확도·외부 요청 요금은 측정하지 않았다. 기존 테스트 82 passed는 결함 해결 증거로 재사용하지 않는다.
