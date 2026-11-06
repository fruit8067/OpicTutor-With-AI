# grader M2

## 상태
구현·로컬 검증 진행 중 (2026-11-06 KST). agent/corpus 위에 쌓인 브랜치.

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
