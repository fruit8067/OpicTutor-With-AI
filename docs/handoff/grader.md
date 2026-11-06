# grader M2

## 사용자 요청: Pickle LLM 설정
LLM의 OpenAI 기본 URL·모델을 제거하고 실제 Pickle의 LLM_BASE_URL·LLM_MODEL을 명시적으로 설정하도록 변경했다.
키는 chat.llm_options에서 호출마다 os.getenv('LLM_API_KEY')로 읽는다. URL·모델·키 중 하나라도 없으면
검색 임베딩이나 LLM 요청 전에 실패한다. OPENAI_API_KEY 또는 settings에 남은 키를 인증 fallback으로 사용하지 않는다.
임베딩의 OpenAI base URL·text-embedding-3-small·EMBED_API_KEY는 그대로 유지한다.
현재 Pickle의 정확한 endpoint/model ID를 사용자에게 요청한 상태이며 호환 SDK 인자 전달만 fixture로 검증했다.
실제 Pickle 서비스의 구조화 출력/JSON 모드 지원이나 응답 품질은 아직 확인하지 않았다.
임베딩 키와 Pickle 키는 각각 해당 서비스의 키를 별도 환경변수에 설정한다.

## 상태
구현·로컬 규칙 검증 완료, 실제 외부 평가 대기 (2026-11-06 KST). agent/corpus 위에 쌓인 브랜치.

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
