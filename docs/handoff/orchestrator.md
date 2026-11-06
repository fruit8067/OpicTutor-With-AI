# orchestrator — 감사 사항 해결

## 상태

최신: 사용자가 .env를 저장하여 Pickle 구조화 ping1요청/large3072 실제 연결과 M1 실제 적재247벡터/중복 재실행0요청을 확인했다. session-api의 늦은 파일 크기 검사를 수신 단계로 옮기고 실제HTTP413을 검증했다. 사용자 경로 이식성 요청에 따라 문서 고정 경로를 제거하고 bootstrap이 상대 경로 강제/별도 checkout·cwd 검증을 수행했다. 아래 0바이트 기록은 저장 전 이력이다.

CR orchestrator-04는 PR #21/main, 기본 설정은 PR #22/main에 반영됐다. 사용자 제공 Pickle URL/model·키 별칭, large/3072와 모델별 재임베딩 구현은 역할 PR #2/#6에 push했다. 기존 DB를 reset 없이 vector(3072)로 전환했고 기존 코퍼스는 0행이다. 키 파일은 디스크 기준 아직 0바이트라 실제 요청/유료 ingest는 대기다. native ASR 증거는 PR #20/main에 보존했다.

진행 중, 2026-11-07 KST. CR orchestrator-01/session-api-01, M0, corpus M1, trusted ownership이 main에 반영됐다. C는 추가하지 않고 A/B 요구사항·API·flowchart 연결을 심화 검증한다. 과거 위반은 감사 이력으로 보존한다.

## 완료한 것

감사 보고서/재현 코드는 PR #9에 있다. 정식 CR #10, ownership 기반 #11, bootstrap #1, corpus M1 #5가 병합됐다. Pickle 혼합 PR #8은 닫았고 나머지 기능 PR은 미완료 조건 때문에 Draft다. 최신 현황은 docs/REMEDIATION_STATUS.md에 기록한다.

## 실행 방법

PowerShell/bash 공통: `python agents/tools/check_ownership.py orchestrator`, `git diff --check origin/main...HEAD`. ownership workflow는 PR마다 실제 CI 결과를 확인한다.

## 공개 함수·화면

CR은 tier nullable 선언·TTS hash 정규화·provider 요청 기록/예산을 명확히 한다. API와 고정 평가 원문은 유지한다.

## 알려진 문제

기능 수정은 각 역할 PR에 push했다. 주소·모델은 확정됐으며 디스크에 저장된 키 부재로 ingest·평가 정확도 local_checks가 남아 있다. C를 새로 구현하지 않으며 M2/M3 전체 완료를 주장하지 않는다. 현재 A/B 코어 구현 검증은 docs/CORE_REQUIREMENTS_VERIFICATION.md에 기록한다.

## 다른 에이전트에게 요청

순차적으로 원래 소유 역할에서 수정하고 default origin/main ownership을 사용한다. M0 이후 역할 브랜치를 재구성하고 미충족 local_checks를 기록한다.

## 측정값

후속 A/B117 passed/skip0/13.01초. 실제HTTP는 약20MiB Content-Length 중10MiB+64KiB만 보내고 종료 boundary 없이413. 이식성 unittest1개 통과(0.298초). M1 실제 적재13.921초, 질의 포함4요청/46,376토큰, 검색47.0ms/top5. LLM ping48/12토큰·3.532초. 채점 품질은 미측정.

v7 최신 실행: clean 역할 커밋 조합 114 passed / skip 0 / 12.20초. 공개 함수 64/API 모델 29/경로 17 차이 0. 이전 v6 기록은 별도 보존. M2 임베딩 dry-run 945,183토큰, 약 $0.122874/3회 상한 $0.368621(large $0.13/1M 표준 단가). 실제 provider 점검은 키 파일 0바이트로 exit 2, 외부 요청 0. docs/compliance/large-embedding-2026-11-07.json 참조.

추가 실제 ASR/CLI 검증: 30초 합성 SAPI 파일 단일 5.500초, HTTP 업로드 8문항 각각 5.438~5.594초(프로세스 시작 포함), answer/job 모두 done/attempt 1, order 1→9, submit 후 selected 8/evaluation queued. 실제 모델 캐시를 오프라인 사용하고 테스트 DB·업로드를 정리했다. 외부 평가/임베딩 호출 0, 실제 마이크·C 없음. 원본 기록은 docs/compliance/native-*-2026-11-07.json이며 LLM 완료를 주장하지 않는다.

ownership 경계 unittest 5개 통과(2.304초), 두 workflow YAML 파싱 성공. trusted contract/head 객체 비교·M0 예외 재사용 거부·합성 음성 허용/로컬 자료 금지를 검증했다. 정확도·외부 요청 요금은 측정하지 않았다. 기존 테스트 82 passed는 결함 해결 증거로 재사용하지 않는다.
이번 A/B 코어 조합은 깨끗한 역할 커밋을 대상으로 전용 임시 DB에서 110 passed, skip 0, 5.83초다. HTTP/queue/STT 저장/평가 검증/결과 재조회/401 후 재평가와 M1 개발 seed를 연결했으며 추론과 C 경계는 fixture다. 실제 외부 LLM/임베딩 호출은 0회다. contracts v6 선언 기준 공개 함수 64개/API 모델 필드 집합 29개/경로·기본 status 17개 차이 0도 확인했다.
