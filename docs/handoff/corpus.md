# corpus M1

## 상태
M1 구현·빌드 검증 완료, M2 진행 중 (2026-11-06 KST).
Core A 구현을 사용하는 쌓인 브랜치: agent/session-api → agent/corpus.

## 완료한 것
Q000과 pilot 13개 v3 태그, 문장 전체를 담은 태그 근거, default 8슬롯, coverage/warnings,
내용 기반 VERSION과 모든 JSONL의 corpus_version, 구조·어휘·중복·이분 매칭 검사.
Q013~Q030은 기존 뱅크 질문과 대조 세트 질문이 달라 M1 답변 빌드에서 제외했다. M2에서 정렬한다.

## 실행 방법
PowerShell: `Set-Location rag_docs; python scripts/build_corpus.py; python scripts/check_monotonic.py`.
bash: `cd rag_docs && python scripts/build_corpus.py && python scripts/check_monotonic.py`.
새 원본 정리: `python scripts/prepare_question_bank.py --phase m2` 후 빌드.
준비 스크립트는 질문 주석과 검토한 대표 유형표로 태그를 준비하며 대조 답변 본문은 수정하지 않는다.

## 공개 자료
rag_docs/build/{questions,answers,rubrics,upgrade_patterns}.jsonl, scenarios.json, VERSION, report.md.
M1 pilot 13개, 자기소개 채점 제외 1개. default slots: 1/3/2/2/1/1/1/2.
rubrics.jsonl은 참고 자료이며 채점 기본 기준은 performance-feedback-actfl-speaking-v3다.

## 알려진 문제
원격 contrast_sets_09에 Q188~Q237이 추가되어 YAML 지시의 Q187보다 범위가 늘었다. M2에 함께 반영한다.
길이·연결어·문장 길이 휴리스틱은 공식 등급 경계가 아니다. 경고가 있는 새 문항은 todo로 보류하며 원문을 억지로 늘리지 않는다.
실제 수험생 등급과의 정확도·독립 사람 검토는 아직 수행하지 않았다.

## 문장 변경 목록
M1 pilot Q000~Q012의 기존 질문 문장은 변경하지 않았다. Q000만 새로 추가하여 TTS 생성이 필요하다.
M2의 기존 Q013~Q030 변경은 source/question_text_changes.yaml에 기록한다.

## 다른 에이전트에게 요청
tts-host: Q000과 M2 신규 pilot의 음성 생성. grader: rubrics.jsonl을 기본 기준에 넣지 말 것.

## 측정값
실제 외부 임베딩·비용은 미측정. 최종 문서/임베딩 대상 수와 시나리오 목록은 M2 빌드 후 기록한다.
