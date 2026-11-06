# corpus M1

## 상태
M1 재구성·빌드 검증 통과, 병합 대기. M2는 보존한 후속 증분으로 분리 (2026-11-06 KST).
M0 main afa076e 기준의 독립 agent/corpus 브랜치다. 과거 stacked/늦은 공개 기록은 감사 보고서에 보존하며 이번 공개를 소급해 적합으로 주장하지 않는다.

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
감사 후 M1 재빌드: VERSION 2026-11-06.6048386932744, 31문항/13 pilot/18 todo, 답변 216건·질문 31건으로 임베딩 대상 247건. 빌드 exit 0, default 시나리오 검사 통과. M1에는 별도 unittest 파일이 없어 0개였으며 통과 테스트로 세지 않는다.

전체 원본 check_monotonic 경고 16건(Q019,Q040,Q042,Q088~Q097,Q140,Q144,Q192)은 M1 pilot Q000~Q012 밖이다. 공식 점수 기준으로 해석하지 않고 M2에서 해당 문항을 todo/사유 기록 대상으로 유지한다. 원문 답변은 바꾸지 않는다.
실제 외부 임베딩·비용은 미측정. 최종 문서/임베딩 대상 수와 시나리오 목록은 M2 빌드 후 기록한다.
