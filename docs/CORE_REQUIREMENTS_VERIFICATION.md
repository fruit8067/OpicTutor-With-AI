# A/B 코어 요구사항·흐름 검증

2026-11-07 KST. 사용자의 최신 목표에 따라 C를 새로 만들지 않고 A/B를 프로젝트 전체 흐름에 대조했다. 기준은 REQUIREMENTS_v2, PROJECT_REQUIREMENTS, FLOWCHART, API_SPEC 및 contracts v6다. 요구사항을 현재 구현에 맞춰 낮추지 않았다.

## 판정

**A/B 핵심 흐름은 명시적인 외부 경계 대역을 사용한 실제 HTTP 계층·PostgreSQL·작업·검증·결과 저장 조합에서 통과했다. 실제 Pickle·임베딩 서비스 연결, 실제 마이크 품질, 제품/브라우저 완주까지 완료한 상태는 아니다.**

- 기존 모듈 검증과 신규 회귀/흐름 검증 합계 **110 passed, skip 0, 5.83초**.
- 별도 선언 대조: **공개 함수 64개, API 모델 29개 필드 집합, 경로/기본 성공 status 17개 차이 0**. 이 대조만으로 모든 데이터 제약·모델 품질을 검증했다고 주장하지 않으며 동작 제약은 위 테스트로 확인한다.
- 별도 `opic_ab_check_<무작위 ID>` DB를 생성해 검증하고 연결을 닫은 후 삭제했다. 기존 개발 DB를 reset하지 않았다.
- 각 역할 worktree 모듈을 메모리에 명시적으로 조합했다. 다른 역할 코드를 자기 브랜치에 상속하거나 운영 소스의 stub을 가짜 구현으로 바꾸지 않았다.
- TTS URL/사전 자산, ASR 추론, LLM HTTP 응답은 테스트 대역이다. DB claim/리스·파일 업로드·STT 처리/저장·평가 검증/저장은 실제 A/B 코드다. 합성 tone은 마이크/실제 영어 발화가 아니다.
- pytest 초기 import 순서의 anyio assertion-rewrite 경고 1건이 있었으며 실패나 skip은 없었다.

원본 커밋/조건은 [검증 기록](compliance/verification-2026-11-07.json)에 고정했다. [기존 감사](COMPLIANCE_AUDIT.md)의 과거 위반을 삭제하지 않는다.

## 실제 ASR·워커 CLI 추가 검증

추론 대역을 사용한 110개 회귀 검증과 별도로, 캐시된 small.en/CPU/int8 및 실제 worker CLI를 사용했다. [단일 기록](compliance/native-stt-2026-11-07.json)과 [8문항 기록](compliance/native-eight-stt-2026-11-07.json)을 남겼다.

- 단일 30초 SAPI 합성 영어 음성: 프로세스 시작 포함 5.500초, answer/job done, attempts 1, order 1→2. 실제 Whisper 텍스트·단어 timestamp·VAD/m1 지표를 DB에 저장했다.
- 8문항: 실제 HTTP 파일 업로드·중복 전송 → 실제 worker CLI 8회/Whisper 전사 → STT 저장 후 order 1→9 → 전체 답변 고정·submit 중복 방지까지 통과했다. 문항별 프로세스 시작 포함 5.438~5.594초였다.
- 워밍업은 채점 제외, 채택 답변 8개, 시험 중 evaluate/embed 외부 요청 0. 마지막 상태는 grading/evaluation queued이며 **LLM 평가 성공이 아니다**.
- TTS URL/자산은 경계 fixture다. 원래 SAPI 샘플 한 개를 반복해 전송·ASR·진행을 검증했으므로 실제 수험생의 발화 품질이나 질문별 과제 수행 정확도를 검증한 것은 아니다. 사용자 마이크와 C 구현은 사용/추가하지 않았다.
- 모델 다운로드를 비활성화하고 기존 캐시만 읽었다. 검증용 DB 및 임시 업로드 파일은 실행 후 제거했으며 원본 합성 음성·모델 캐시는 보존했다.

재현: 기존 명령의 Python으로 `docs/compliance/verify_native_stt.py --workspace <worktree parent> --audio <기존 합성 wav> --answers 8 --report <결과.json>`을 실행한다. 기본 `--answers 1`은 단일 실제 STT/DB 경로를 검사한다. 실제 서비스 검증 시 사용할 설정은 primary `OpicTutor-With-AI/backend/.env`에 두고 서비스 검증 프로세스에서 명시적으로 로드한다. 이 ASR 검증은 외부 LLM/임베딩을 호출하지 않는다.

## 요구사항과 검증 근거

| 요구사항·flowchart 단계 | A/B 구현과 검증 | 판정/한계 |
| --- | --- | --- |
| F0: 마이크 확인·지원 시나리오·전체 8문항 확정 | mic_check false 거부, pilot/유형/태그/중복 검사, 결정적 seed, DB 스냅샷 | 서버 경계 통과. 브라우저 마이크 UI는 C 범위라 추가하지 않음 |
| F0: 재전송·새로고침·준비 재시도 세트 불변 | 같은 request ID는 저장 세션 우선 조회, 코퍼스 오류 후 재전송 200, 실제 DB 동시 생성 5회→1행/1작업, stale prepare 무시 | 통과. CR session-api-01/v5 추가 함수 사용 |
| F0: 전체 음성 준비 후 시작 | preparing start 409, prepare_failed→같은 세트 retry, 이전 attempt 완료 무시, 정상 asset 링크 후 ready | DB/API 경계 통과. 실제 TTS 파일 검증·재생은 대역 |
| F1: 고정된 현재 문항 조회·다시 듣기 | 확정 snapshot 조회, 현재 order 외 업로드 거부, replay 한도 | API/DB 경계 통과 |
| F1/F2: 202 접수와 STT 저장 구분 | 8회 업로드 모두 202 직후 order 유지, 실제 stt job claim/처리/complete 이후에만 +1 | 통과. 전사 문자열 생성만 fixture |
| F2: 업로드 크기·형식·기간·중복·로컬 파일 | 1.5초/125초 초과/11MB/text/plain/빈 파일 거부, SHA256·임시 파일 정리, 같은 키 중복 ID, 잘못된 세션 접근 거부 | 통과 |
| F2/§9: 파일 이동 실패·같은 요청 재전송 | DB 접수 후 rename 실패를 주입, 같은 Blob으로 원래 answer 복구·STT 재시도, 다른 Blob 불변, 복구 후 DB retry 실패도 다음 전송으로 복구. 이미 문항이 전진/제출된 과거 실패 답변의 재전송은 읽기 멱등성을 유지 | 신규 보강·통과 |
| F2: 무음·손상·기술적 실패·작업 복구 | 로컬 PyAV probe, silence/corrupt/no_speech 구분, lease/attempt/cancel 가드와 만료 복구 | 모듈/DB 검증 통과. 과거 합성 Whisper·실제 프로세스 종료 결과와 현재 fixture 조합 결과를 구분 |
| F3: 마지막 STT 전 제출 금지·시험 중 평가 없음 | 매 업로드 직후 조기 submit 409, 마지막 done 뒤에만 submit 202, 그 전 evaluate 요청 0, 중복 submit 평가 ID 동일 | 통과 |
| F3: 서버가 전체 문항·답변·태그·고정 기준 조회 | 고정된 selected_answer_ids, 실제 grading job→snapshot/evidence/messages→출력 검증→DB done | 통과. LLM 응답은 MockTransport 대역 |
| F3: 워밍업 제외·결측·인용·잠정 IM·서술형 FACT | 7문항 scored, 1번 feedback_only, 가짜 인용·자기소개 혼입·잘못된 등급/버전·기술적 결측 fact 거부 | 통과. 실제 모델의 판단 품질은 미검증 |
| F3/F5: 근거 버전·검색 누출·요청 예산 | 직접/유사 검색 대조 세트 제외, fallback 버전 재검사, 실제 provider 요청별 로그/3회 상한, 408/429/5xx·401·refusal 구분 | 통과. 실제 서비스 latency/cost는 미측정 |
| F3: JSON-only 제공자의 재요청 | schema 미지원 400 이후 JSON object 모드를 해당 평가 안에서 기억, 잘못된 JSON 뒤 수정 요청까지 총 3회 안에서 성공 | 신규 보강·통과. 실제 Pickle 호환성은 주소/모델 확인 후 검증 |
| F4: 저장 결과 재조회·평가 실패 후 재평가 | 최초 결과 DB 저장, 결과 10회 조회→AI 증가 0, 401 fixture 실패 후 이전 성공 결과·선택 답변 보존, regrade run 3 성공 | 통과. 새 시험 없이 원래 답변 재사용 |
| F5: 평가 계획과 정확도 구분 | 40시험/5종 함정 계획, 선택적 Q000 예시 없을 때 출처 명시 fixed warmup만 사용, 채점 문항 예시 부재는 실패 유지 | 계획·규칙 통과. 실제 ±1/경계/반복 정확도 미측정 |
| 개발용 M1→grader 검증 경로 | seed-grading의 선택적 Q000 fallback 출처 기록, 채점 답변 누락/빈 본문/비정상 시간은 세션 생성 전 실패, unsupported scenario 유지, 합성 STT 완료 후 대기 작업 제거 | 신규 보강·통과. 운영 API에서 dev 모듈을 import하지 않음 |
| F6/F7: TTS·캐릭터·브라우저 | A/B가 제공할 자산 링크·오류·진행 상태만 확인 | C를 새로 구현하지 않음. 제품 완주로 주장하지 않음 |
| F8 등 후속 범위 | chat은 계약대로 501, 시험 중 추가 출제·회원·페르소나 확장 없음 | 현재 주 흐름에 불필요한 기능을 추가하지 않음 |

## 이번에 해결한 결함

기존 I-01~06: 기술적 결측 FACT 상태, fallback RAG 버전, TTS strip 해시, HTTP 408 분류, 실제 provider 요청 로그/예산, 공개 시그니처를 수정했다. nullable tier는 CR orchestrator-01로 선언 모순을 해소했다.
추가로 CR data-layer-01/계약 v6는 비 IM 결과와 선택적 corpus 메타데이터의 기존 nullable API/DB 동작을 함수 타입에 정확히 반영했다. 실제 IL 재평가의 두 null 메타데이터 저장/조회도 검증했다. 평가 기준·도메인 컬럼은 바꾸지 않았다.

추가로 다음 흐름 문제를 수정했다.

1. 생성 재전송이 변경된 문제 은행 때문에 실패함 → DB 조회 함수 승인 후 저장 세션 우선 반환.
2. DB 접수 후 원음 rename 실패가 같은 키 재전송으로 복구되지 않음 → 동일 Blob에 한해 원래 파일/답변과 STT 재시도 복구.
3. 임베딩 HTTP 408이 재시도되지 않음 → 일시 오류 분류·3회 상한/본문 없는 로그 검증.
4. 중복 embedding index가 문서와 벡터를 잘못 연결할 수 있음 → 완전한 index 집합 검증.
5. M1의 선택적 Q000 대조 답변 부재로 평가 계획 생성 불가 → 워밍업만 고정 샘플·출처 기록, 채점 증거는 대체하지 않음.
6. 개발용 grading seed도 같은 이유로 실패하고 부분 세션/작업을 남김 → 입력 전체 사전 검증·워밍업 출처·완료된 합성 작업 정리. 잘못된 시나리오를 기본 세트로 대신하지 않음.

## 절차 복구

CR #10/#14/#16, M0 #1, corpus M1 #5, ownership 기반 #11 및 감사/보강 #9가 main에 병합됐다. rebase-only·main ruleset·필수 ownership을 유지한다. 새 trusted workflow는 PR의 코드/계약을 실행하지 않고 main 기준과 PR 객체를 검사한다. 실제 CI에서 `ownership`/`trusted ownership runner` 성공을 확인했다.

A/B 기능 PR은 각자 최신 기준의 자기 증분으로 재구성하고 기본 origin/main ownership을 사용한다. main 외 역할 브랜치를 PR base로 두지 않도록 정리한다. 작업자별 실행 결과와 남은 의존 조건은 해당 handoff에 기록한다. C를 추가해 M2/M3를 억지로 완료하지 않는다.

## 실행

```powershell
& 'C:/Users/fruit/Documents/OpicTutor/OpicTutor-With-AI/backend/.venv/Scripts/python.exe' `
  'C:/Users/fruit/Documents/OpicTutor/OpicTutor-audit/docs/compliance/verify_core.py' `
  --workspace 'C:/Users/fruit/Documents/OpicTutor'
```

이 명령은 `OpicTutor-session`, `OpicTutor-data`, `OpicTutor-grader`, `OpicTutor-worker` worktree와 해당 의존 패키지를 사용한다. PostgreSQL 테스트 계정은 임시 DB 생성/삭제 권한이 필요하다. `core_flow_cases.py`가 실제 HTTP/DB/작업/결과 복구를 검증한다.
같은 명령 끝에 `--interfaces-only`를 붙이면 DB를 변경하지 않고 공개 함수 선언/API 필드·경로·기본 status를 대조한다.

## 아직 검증할 조건

Pickle 실제 base URL·모델 ID·로컬 LLM_API_KEY, EMBED_API_KEY가 제공되면 실제 ingest와 서비스 회귀/함정/반복·비용을 검증해야 한다. 현재 키·주소는 미설정이다. 이 조건 없이 실제 채점 정확도·서비스 호환성·모든 YAML done_when 완료를 선언할 수 없다. C의 화면/음성 제작을 새로 구현해서 이 조건을 대신하지 않는다.
