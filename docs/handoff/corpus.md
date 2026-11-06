# corpus M1/M2

## 상태
M1은 PR #5로 main 3f2d3c9에 병합됐다. 2026-11-07 재빌드·unit 3개 통과. M2는 PR #12 Draft이며 data-layer M1/지정 병합 순서 대기다.
같은 agent/corpus 브랜치를 main에 rebase하고 M2 자기 증분만 이어갔다. 과거 stacked/늦은 공개 위반은 감사 이력으로 보존한다.

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
원격 contrast_sets_09의 Q188~Q237도 M2에 반영했다. YAML 지시의 Q187보다 늘어난 범위를 보고서에 기록했다.
길이·연결어·문장 길이 휴리스틱은 공식 등급 경계가 아니다. 경고가 있는 새 문항은 todo로 보류하며 원문을 억지로 늘리지 않는다.
실제 수험생 등급과의 정확도·독립 사람 검토는 아직 수행하지 않았다.

## 문장 변경 목록
M1 pilot Q000~Q012의 기존 질문 문장은 변경하지 않았다. Q000만 새로 추가하여 TTS 생성이 필요하다.
M2의 기존 Q013~Q030 변경은 source/question_text_changes.yaml에 기록한다.

## 다른 에이전트에게 요청
tts-host: Q000과 M2 신규 pilot의 음성 생성. grader: rubrics.jsonl을 기본 기준에 넣지 말 것.

## 측정값
실제 외부 임베딩·비용은 미측정. 감사 후 M2 재빌드 VERSION은 2026-11-06.112940456345857이다. 헤더 출처 추가로 내용 기반 버전이 바뀌었으며 질문 문장·대조 답변 내용은 이 변경으로 바뀌지 않았다. 빌드 exit 0, unittest 3개 통과(1.87초). 단조성 경고 16건은 todo로 보류하고 report에 기록했다.

## M2 최종 결과

2026-11-07: data-layer M1은 main532951f에 병합됐다. 이후 main 기준 rebase, build exit0 / 동일 VERSION 보존, monotonic16경고의 todo 보류 사유 재확인, unittest3개 통과(1.886초), 정규화 후 build diff0을 확인했다. M2 확대 실제 임베딩은 data-layer 후속 검증에서 진행한다.
- corpus_version: 2026-11-06.112940456345857 (감사 후 재빌드)
- Q000~Q237 238문항, pilot 222, todo 16; 자기소개 채점 제외 1개.
- pilot 유형별 수와 모든 슬롯 pool 크기: rag_docs/build/report.md.
- default/leisure/health를 공개. travel은 routine 슬롯 부족으로 제외했고 임의 대체하지 않음.
- 4,284개 답변 + 238개 질문 = 임베딩 대상 4,522개. 외부 임베딩 미실행.
- 단조성 경고 16건은 기존 답변을 보존하고 해당 16문항을 todo로 보류. 사유·ID는 report.md.
- Q013~Q030 질문 18개는 대조 세트의 실제 질문으로 정렬. Q001~Q012는 문장 변경 없음.
- Q000 대조 예시 9개(clean/STT 18개)를 추가해 dev seed-grading의 워밍업 답변을 지원. 등급 근거에는 사용 금지.
- Q033/Q041/Q043/Q047/Q075/Q130 등 혼합·과거 묘사 과제를 직접 검토해 추가 기능·시간대를 구분.
- Q071의 실제 예상 결과 요구를 default issue pool에 반영. future는 매 추첨 보장이 아니므로 경고 유지.
- IM 프로필 검토: 길이를 공식 경계처럼 사용하는 것은 금지. 명시적인 길이 근거는 없었으나 연결어 역전 Q019/Q040/Q042 및 문장 길이 경고 문항은 사람 검토 대기.
- M1 자료는 724dc11에서 먼저 push했고 M2를 같은 corpus 브랜치에 누적했다.
- 빌드 exit 0, 코퍼스 회귀 테스트 3개 통과, API에서 공개 시나리오별 100 seed 선택 성공.

- 추가 문장 검토: Q069 산업 발전 과정의 past/narrate_past, Q138 갑작스러운 정전의 unexpected_situation을 실제 요구에 맞춰 보완.
