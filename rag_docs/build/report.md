# 코퍼스 v3 빌드 리포트

- corpus_version: 2026-11-06.86127713111320
- 문항 31 / pilot 13 / todo 18
- 문서 수: {'rubrics': 9, 'upgrade_patterns': 8, 'questions': 31, 'answers': 216}
- 예상 임베딩 대상: 247
- 자동 형식 검증은 실제 수험생 채점 정확도나 태그의 독립적인 사람 검증을 의미하지 않음.
- 고정 평가 기준: performance-feedback-actfl-speaking-v3. rubrics.jsonl은 참고용이며 기본 채점 기준이 아님.

## pilot 유형별 수
{'self_intro': 1, 'description': 3, 'routine': 2, 'past_experience': 2, 'comparison': 1, 'issue': 1, 'roleplay_ask': 1, 'roleplay_solve': 1, 'roleplay_experience': 1}

## 시나리오
### default
[(1, 1), (2, 3), (3, 2), (4, 2), (5, 1), (6, 1), (7, 1), (8, 2)]
{"functions": ["ask_information", "compare", "describe", "narrate_past", "report_routine", "solve_problem"], "time_frames": ["past", "present"], "contexts": ["everyday_transaction", "personal_familiar", "unexpected_situation"], "warnings": ["future 시간대 요구가 모든 추첨에서 보장되지 않음"]}

## 시나리오 제외 사유
없음

## todo 문항과 사유
- Q013: 기존 질문과 대조 세트 질문 불일치, 답변 빌드 제외
- Q014: 기존 질문과 대조 세트 질문 불일치, 답변 빌드 제외
- Q015: 기존 질문과 대조 세트 질문 불일치, 답변 빌드 제외
- Q016: 기존 질문과 대조 세트 질문 불일치, 답변 빌드 제외
- Q017: 기존 질문과 대조 세트 질문 불일치, 답변 빌드 제외
- Q018: 기존 질문과 대조 세트 질문 불일치, 답변 빌드 제외
- Q019: 기존 질문과 대조 세트 질문 불일치, 답변 빌드 제외
- Q020: 기존 질문과 대조 세트 질문 불일치, 답변 빌드 제외
- Q021: 기존 질문과 대조 세트 질문 불일치, 답변 빌드 제외
- Q022: 기존 질문과 대조 세트 질문 불일치, 답변 빌드 제외
- Q023: 기존 질문과 대조 세트 질문 불일치, 답변 빌드 제외
- Q024: 기존 질문과 대조 세트 질문 불일치, 답변 빌드 제외
- Q025: 기존 질문과 대조 세트 질문 불일치, 답변 빌드 제외
- Q026: 기존 질문과 대조 세트 질문 불일치, 답변 빌드 제외
- Q027: 기존 질문과 대조 세트 질문 불일치, 답변 빌드 제외
- Q028: 기존 질문과 대조 세트 질문 불일치, 답변 빌드 제외
- Q029: 기존 질문과 대조 세트 질문 불일치, 답변 빌드 제외
- Q030: 기존 질문과 대조 세트 질문 불일치, 답변 빌드 제외

## 단조성 점검
경고 없음

## IM 프로필 검토 목록
길이만으로 설명한 명시적 근거 없음. 내용 확장·시간 관계를 별도로 검토해야 함.

## 길이 참고 통계 (공식 등급 경계·pilot 탈락 기준 아님)
- 참고 범위 밖 0건

## 미래 시간대
M1 기본 세트는 future 시간대 요구를 보장하지 않으므로 경고를 유지.

## 출처/질문 변경
원본 대조 세트의 실제 기출 원문 아님 문구와 답변을 보존함. Q013~Q030 기존 뱅크/대조 질문 불일치는 question_text_changes.yaml 참조.
