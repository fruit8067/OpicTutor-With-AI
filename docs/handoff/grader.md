# grader M2

## 사용자 요청: Pickle LLM 설정
contracts v7 기본값은 Pickle `https://llm.pcl.kr/v1` / `pickle-general`이다. 호출 시 os.getenv('LLM_API_KEY') 우선, 비어 있으면 PICKLE_API_KEY를 읽는다. OpenAI 키로 LLM 인증을 대체하지 않는다. 검색 임베딩은 별도 EMBED_API_KEY / large3072다. 실제 구조화 ping1요청과 실제 M1 ingest는 성공했다.

실제 합성 IL 전체 시험은 초기 v1에서 범위/coverage/인용 검증 실패, v2/v3에서 인용 검증 실패를 관측했다. 실패를 성공 결과로 저장하지 않는다. 고정 system 원문·엄격한 인용 검증은 유지하고 user v2에 서버 계산 범위/태그 제약, v3에 실제 전사 인용 후보, v4에 JSON/전사 본문 따옴표 보존(속성만 quote escape)을 적용했다. v4 실제 점검 중이며 전체 정확도 검증은 미완료다. 검증 실패 상세에는 코드로 정의된 오류 이름만 저장하고 임의 예외/답변 본문은 저장하지 않는다.

## 상태

후속 실제 v4 IL 시험: 최초 응답의 잘못된 인용은 거부하고 수정 응답으로 queue/evaluation/session 모두done, IL/IL·8items 저장. 2요청, 입력31,392+31,424/출력6,094+6,751토큰, 전체85.844초. 실제 전체 회귀·반복 정확도 검증을 대신하지 않는다. 사용자는 학교 크레딧 약$10 사용을 명시했다. 단가 미공개 시 --school-credit-usd 10으로 실제 비용을 미산정(None)으로 기록하며 예산/인증 거절은 일괄 중단한다. 각 시험 후 같은 리포트에 체크포인트를 기록한다. 실패 시 실제 요청/토큰도 별도 누적한다.
감사 결함 수정·로컬 규칙 검증 통과, 실제 외부 평가의 출력 안정성 보강 중 (2026-11-07 KST). main 기반 독립 agent/grader 브랜치다. 아래 키 미구성/계획만 존재 기록은 당시 이력이다.

## 공개 함수·화면
contracts v4의 app.grading/app.llm.chat. evaluate_exam의 job_id와 반환 타입 주석을 계약대로 복원했다. nullable tier 선언은 정식 CR orchestrator-01에 반영됐다. provider 추적은 내부 ContextVar이며 공개 함수 시그니처를 변경하지 않는다.

## 다른 에이전트에게 요청
data-layer: 실제 corpus ingest/DB 함수 main 반영. session-api: build_question_set main 반영. 해당 기능이 없는 M0 기준 브랜치에서는 평가 계획 연결 검사가 미완료다. 실제 Pickle URL·모델·키, 임베딩 키도 필요하다.

## 측정값
감사 후 grader 단위/provider 경계 44개 통과(2.76초). 전체 grader tests 최초 실행은 40 passed/1 failed였으며 실패 원인은 M0의 session-api stub이었다. 이 연결 검사는 면제하지 않고 main 의존 기능 준비 후 재실행한다. 실제 정확도·요금은 미측정이다.

## 감사 후 수정
- JSON schema 미지원 제공자는 같은 평가의 재시도에서 JSON object 모드를 기억한다. 첫 400/잘못된 JSON/수정된 JSON이 총 3요청 안에 성공하는 경계를 검증하며, 다른 시험으로 상태를 넘기거나 4번째 요청을 보내지 않는다.
- 2026-11-07 교차 검증에서 M1의 선택적 Q000 대조 답변 부재로 평가 계획 생성 실패를 재현했다. 워밍업만 고정 샘플(v1)로 대체하고 리포트에 샘플·적용 case ID를 기록한다. 채점 문항 대조 답변이 없으면 계속 실패한다. 채점 기준이나 사용자 답변을 대체하지 않는다.
- A/B 메모리 조합 검증 101 passed(5.37초): 실제 DB·HTTP·STT/평가 작업 경계·결과 저장·10회 재조회·실패 후 재평가를 연결했다. ASR/LLM 추론은 명시적인 fixture이며 실제 정확도·서비스 성공 결과가 아니다.
- 기술적 결측 fact는 not_observed만 허용한다. demonstrated/not_demonstrated를 모두 거부하는 회귀 검증을 추가했다.
- 유사 검색 후보와 대조 세트 확장 모두 현재 corpus_version을 다시 검사한다.
- HTTP 408/429/502를 실제 설치 SDK+MockTransport로 재현해 LLMTransientError 및 재시도를 검증했다.
- JSON 대체 협상 요청도 1회씩 기록하고 총 provider 요청 3회 예산에 포함한다. 4번째 요청은 전송하지 않으며 요청 본문/답변은 로그에 넣지 않는다.

## 완료한 것
시스템 프롬프트 원문 로드, 구조화 출력/JSON 호환 경로, 누출 제외 RAG와 토큰 예산,
스냅샷 선검사·v3 출력 검증, 최대 3호출 예산 안의 재시도, 평가 작업 완료/실패 저장 구현.
DB에는 복합 prompt_version을, 사용자 결과에는 고정 opic-evaluation-system-v3를 저장한다.

## 실행 방법
PowerShell: `cd backend; .venv/Scripts/python -m pytest tests/test_grading_*.py -q`.
bash: `cd backend && .venv/bin/python -m pytest tests/test_grading_*.py -q`.
실제 평가에는 backend/.env의 LLM_API_KEY 및 검색 임베딩용 EMBED_API_KEY와 적재된 corpus가 필요하다.
키를 대화나 커밋에 넣지 않는다. 유료 eval_exam은 예상 호출 수·비용을 확인한 뒤 실행한다.

## 검증 규칙
자기소개는 items.feedback_only만 허용. FACT·영역·커버리지·수행·붕괴·카드는 채점 대상만 사용.
인용은 대소문자·공백·구두점 정규화 후 실제 전사의 부분 문자열인지 확인한다.
IM은 서로 다른 채점 문항 유형 2개에서 실제 인용 2개 이상일 때만 세분화 허용.
누락 전사는 not_assessable, 모두 누락이면 insufficient_evidence. 카드 3~5/0~5, before=null이면 practice.
금지 패턴: 발음\\s*점수, 합격\\s*보장, 숫자+%, AM 단독, Advanced Mid, 100\\s*점.

## 알려진 문제와 측정값

contracts v7 / CR orchestrator-04: 호출 시점 os.getenv('LLM_API_KEY') 우선, 비어 있으면 os.getenv('PICKLE_API_KEY')를 사용한다. 설정 기본값은 main의 Pickle URL/model·large3072를 따른다. 채점 temperature=0 유지. 동적 키 교체·별칭·우선순위·누락 키 시 OPENAI_API_KEY 미사용을 검증한다. PC-B의 원격 rebase를 먼저 보존하고 구현 파일 동일성을 확인했다.
현재 로컬 API 키가 구성되지 않아 실제 LLM 등급·토큰·지연·비용 및 반복 정확도는 미측정.
로컬 구조/규칙 테스트를 실제 채점 정확도 리포트로 표시하지 않는다.
평가 기준 원문이 다른 문서와 다르면 원문을 수정하지 않고 CR로 기록한다.

## 로컬 실행 결과
- 평가 테스트 32 passed. 정상·IM 잠정 진단·IM 보류·결측·자기소개 혼입·가짜 인용·버전·금지 패턴·재시도·누출·리스 상실 후 저장 차단 확인.
- 세 시스템 프롬프트 본문이 줄바꿈 경계 정규화 후 일치. sha1: c2a7e9fe97b3d76083006d2a76c97c56ad3ef7ad.
- prompt_version: opic-evaluation-system-v3+evaluate_exam.v1, rubric_version: performance-feedback-actfl-speaking-v3, IM: project-im-v1.
- `python -m scripts.eval_exam --traps --plan`: 40시험, 정상 40호출, 최대 120호출 계획 생성. 외부 호출 0.
- 계획 리포트는 eval_reports/*-plan.md/.json이며 **실제 평가 리포트가 아니다**. 정확·±1·base·경계·보류·함정·반복 수치는 모두 미측정.
- 실제 실행 예: `python -m scripts.eval_exam --limit 4 --input-usd-per-million <단가> --output-usd-per-million <단가> --embedding-usd-per-million <단가>`.
  호출 수와 보수적인 비용 상한을 확인하고 yes 입력. --yes는 비용 확인을 대신하지 않는다.
- `--traps`, `--repeat 3` 전체 실행 및 기준 미달 시 템플릿 2회 개선은 실제 키·비용 확인 전에는 실행하지 않았다.
- ingest --dry-run: 전체 4,539문서 중 임베딩 대상 4,522개. 실제 외부 임베딩은 미실행.
- 사전 비용 계획에는 대조 세트 제외로 필요한 검색 임베딩의 호출 수·토큰 추정·재시도 상한도 별도 포함한다.
  실측 리포트의 평균 비용은 LLM usage 기준이며 검색 임베딩 usage는 ai_requests의 embed 기록과 구분한다.
- 키 미구성 상태에서 실제 evaluate 워커 실행: evaluation.failed, session.grading_failed, EVAL_INTERNAL, 외부 평가 호출 0.
  실제 잘못된 키의 HTTP 401 실험이나 성공 등급 실험을 통과했다고 표시하지 않는다.
