# orchestrator — 감사 사항 해결

## 상태

사용자 후속 C 병합 요청으로 frontend PR#24를 최신 main/필수 native ownership 확인 후 main 731c1e3에 rebase merge했다. TTS PR#19는 이미 main 832f898에 있다. A/B/C Phase1 구현 PR은 main에 반영됐고, 단일 main에서 frontend npm ci/build/lint 및 녹음 Node4개를 통과했다. .env와 backend 트리는 변경되지 않았다. 기록: docs/compliance/c-merge-2026-11-07.json.

integrator #4/M3는 아직 미병합이며 실제 사람 마이크/공급자 품질·Pickle 남은35시험/반복/함정·독립 M4 검토는 후속이다. 구현 병합을 제품 전체 완료로 표시하지 않는다.

### 이전 상태 이력

사용자의 후속 A/B main 병합 요청을 반영했다. worker-stt #7→session-api #3→grader #6 순서로 필수 native ownership/최신 main을 확인하고 rebase merge했다. main 4dc68a3의 단일 checkout 전체 backend/tests는 **157 passed/skip0/14.37초**이며 격리 DB를 생성/삭제했다. 로컬 .env는 보존했다. 자세한 기록은 docs/compliance/ab-merge-2026-11-07.json.

구현 병합은 품질/M3 완료 선언이 아니다. Pickle quota_exhausted로 남은35시험·반복/함정·실제 사람 마이크 조건을 보존한다. frontend #24와 integrator #4는 아직 미병합이며 전체 M2/M3/M4를 완료로 표시하지 않는다.

### 이전 상태 이력

최신 C 요구사항 감사: docs/C_REQUIREMENTS_VERIFICATION.md와 compliance/c-audit-2026-11-07.json을 정본으로 본다. 다른 작업자의 실제 음성 dd440e3을 보존해242개/해시 일치/누락0을 확인했다. 취소/문항 누락/녹음 오류/늦은 마이크와 음성 덮어쓰기 등 재현·정적 발견을 수정했다. 음성 덮어쓰기 CR tts-host-01은 PR#30/main으로 승인해 계약 v8이 됐다. 공개 HTTP/DB/평가 원문 변경 없음.

TTS29개, 녹음 Node4개, 기존 Chromium15·추가 경계11개 통과. 실제 C+AB HTTP/DB/워커/OmniVoice8문항 done/평가1회/미디어206 17개, 결과 refresh 추가평가0. STT 전사·채점 추론만 대역이며 유료요청0. A/B128/14.34초·공개 선언 차이0. 실제 사람 마이크/공급자 품질·M2/M3·독립 reviewer는 별도 조건이다.

TTS 코드/실제 자산/감사 수정 PR#19는 main 832f898에 병합했다. frontend PR#24는 최신 main rebase/build/lint/ownership 후 Draft를 유지한다.

### 이전 상태 이력

최신 사용자 지시로 C 작업을 시작했다. 기존 tts-host/frontend 원격 구현을 보존해 최신 main으로 rebase하고 역할별 수정·push를 완료했다. 사용자는 코드 우선/Colab 나중을 선택했다. TTS 단위19개·실제 임시 DB 준비/누락/복구, Chromium15개(키보드8문항 포함)가 통과했다. CR frontend-01 타입 수정은 PR#28/main 0c4ee09에 병합했다. 코드 PR#19/#24는 실제 음성 및 M2 의존 조건을 명시한 Draft로 유지한다. 상세 기록: docs/compliance/c-current-2026-11-07.json.

기존 A/B 완료5건·Pickle quota_exhausted·남은35시험 조건은 유지된다. 실제 음성/마이크·M2/M3·독립 reviewer를 완료로 표시하지 않는다.

### 이전 A/B 전용 작업 이력

현재: 데이터 M1/#2·corpus M2/#12·data-layer M2/#27은 main에 병합됐다. F5 전체 40시험은 정상 5건 뒤 6번째에 학교 API HTTP429/quota_exhausted로 중단됐다. 작은 요청도 거절됐으며 키/모델은 바꾸지 않았다. 완료 5건을 보존하고 나머지 35건을 재개하는 검증은 통과했다. 실제 마이크 파일은 아직 없다. C/M2/M3 전체 완료를 주장하지 않는다.

실제 M2 large3072 적재 4,522벡터·재실행 0요청·검색 62ms와 IL 평가 v4의 done 저장을 확인했다. F5의 초기 v4/v5 실패 보고서와 NM1 재실행 성공도 보존했다. 사용자는 학교 크레딧 약 $10 사용을 허용했지만 실제 잔액은 관측하지 않았으며 공급자 할당량 회복을 기다린다. C를 새로 구현하지 않는다.

CR orchestrator-04는 PR#21/main, 기본 설정은#22/main, 상대 경로 강제 설정은#25/main이다. 기존 DB는 reset 없이 vector(3072)로 전환했고 실제M2 적재가 완료됐다. 키는 저장됐고 연결 성공했다. native ASR 증거는#20/main 및 상대 경로 후속 기록에 보존했다. data-layer M2 측정값은PR#27이며 API/grader/worker의 M2 완료·C·마이크 조건은 아직 남아 있다.

진행 중, 2026-11-07 KST. CR orchestrator-01/session-api-01, M0, corpus M1, trusted ownership이 main에 반영됐다. C는 추가하지 않고 A/B 요구사항·API·flowchart 연결을 심화 검증한다. 과거 위반은 감사 이력으로 보존한다.

## 완료한 것

감사 보고서/재현 코드는 PR #9에 있다. 정식 CR #10, ownership 기반 #11, bootstrap #1, corpus M1 #5가 병합됐다. Pickle 혼합 PR #8은 닫았고 나머지 기능 PR은 미완료 조건 때문에 Draft다. 최신 현황은 docs/REMEDIATION_STATUS.md에 기록한다.

## 실행 방법

PowerShell/bash 공통: `python agents/tools/check_ownership.py orchestrator`, `git diff --check origin/main...HEAD`. ownership workflow는 PR마다 실제 CI 결과를 확인한다.

## 공개 함수·화면

CR은 tier nullable 선언·TTS hash 정규화·provider 요청 기록/예산을 명확히 한다. API와 고정 평가 원문은 유지한다.

## 알려진 문제

기능 수정은 각 역할 PR에 push했다. 실제 ingest·인증 성공/실패·IL 평가 저장은 확인했고, 전체 정확도/함정/반복 및 실제 마이크 local_checks가 남아 있다. C를 새로 구현하지 않으며 M2/M3 전체 완료를 주장하지 않는다. 현재 A/B 코어 구현 검증은 docs/CORE_REQUIREMENTS_VERIFICATION.md에 기록한다.

## 다른 에이전트에게 요청

순차적으로 원래 소유 역할에서 수정하고 default origin/main ownership을 사용한다. M0 이후 역할 브랜치를 재구성하고 미충족 local_checks를 기록한다.

## 측정값

최신 로컬 회귀 128 passed/skip 0/13.65초, 소유권 unittest5/이식성1 통과, 공개64/29/17 차이0. 독립 STT CLI 5.046초, 독립 API 17 operation·생성202/중복200·preparing 시작 차단·취소·AI요청0. 전체40시험은 6attempt/5done/1quota이며 남은35와 repeat3은 할당량 회복 후 필요하다. 일부 결과를 전체 정확도 목표 달성으로 표시하지 않는다.

이전 A/B123 passed/skip0/13.65초, 별도 선언64/29/17 차이0. M2 실사용945,194입력토큰/47요청(질의 포함), 추정$0.12287522,236.594초, 검색62ms. native 상대 경로 STT5.110초, 실제 잘못된 키1요청/0.984초 후실패. IL v4실제2요청/85.844초 후done. 현재CLI의 일반실패까지요청/토큰을 누적하고 비용미공개는None으로 기록한다. 아래110/114개 및키부재 기록은 과거 이력이다.

후속 A/B117 passed/skip0/13.01초. 실제HTTP는 약20MiB Content-Length 중10MiB+64KiB만 보내고 종료 boundary 없이413. 이식성 unittest1개 통과(0.298초). M1 실제 적재13.921초, 질의 포함4요청/46,376토큰, 검색47.0ms/top5. LLM ping48/12토큰·3.532초. 채점 품질은 미측정.

v7 최신 실행: clean 역할 커밋 조합 114 passed / skip 0 / 12.20초. 공개 함수 64/API 모델 29/경로 17 차이 0. 이전 v6 기록은 별도 보존. M2 임베딩 dry-run 945,183토큰, 약 $0.122874/3회 상한 $0.368621(large $0.13/1M 표준 단가). 실제 provider 점검은 키 파일 0바이트로 exit 2, 외부 요청 0. docs/compliance/large-embedding-2026-11-07.json 참조.

추가 실제 ASR/CLI 검증: 30초 합성 SAPI 파일 단일 5.500초, HTTP 업로드 8문항 각각 5.438~5.594초(프로세스 시작 포함), answer/job 모두 done/attempt 1, order 1→9, submit 후 selected 8/evaluation queued. 실제 모델 캐시를 오프라인 사용하고 테스트 DB·업로드를 정리했다. 외부 평가/임베딩 호출 0, 실제 마이크·C 없음. 원본 기록은 docs/compliance/native-*-2026-11-07.json이며 LLM 완료를 주장하지 않는다.

ownership 경계 unittest 5개 통과(2.304초), 두 workflow YAML 파싱 성공. trusted contract/head 객체 비교·M0 예외 재사용 거부·합성 음성 허용/로컬 자료 금지를 검증했다. 정확도·외부 요청 요금은 측정하지 않았다. 기존 테스트 82 passed는 결함 해결 증거로 재사용하지 않는다.
이번 A/B 코어 조합은 깨끗한 역할 커밋을 대상으로 전용 임시 DB에서 110 passed, skip 0, 5.83초다. HTTP/queue/STT 저장/평가 검증/결과 재조회/401 후 재평가와 M1 개발 seed를 연결했으며 추론과 C 경계는 fixture다. 실제 외부 LLM/임베딩 호출은 0회다. contracts v6 선언 기준 공개 함수 64개/API 모델 필드 집합 29개/경로·기본 status 17개 차이 0도 확인했다.
