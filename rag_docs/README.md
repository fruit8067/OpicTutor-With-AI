# OpicTutor RAG 코퍼스 v3

AI-assisted: 기존 대조 답변은 원본의 출처 표시를 유지하며, v3 빌드·문항 태그·자기소개 예시는 OpenAI Codex의 도움으로 작성했습니다.

- corpus_version: `2026-11-06.77496797373666`
- 문항 Q000~Q237 총 238개: pilot 222, todo 16. 자기소개 Q000만 is_scored=false.
- 답변 4,284개(clean/STT), 질문 238개, 참고 루브릭 9개, 승급 패턴 8개.
- 임베딩 대상: 질문+답변 4,522개. 외부 호출 전 ingest --dry-run으로 다시 확인한다.
- 시나리오: default(기본), leisure(여가), health(운동·건강). travel은 routine 슬롯이 비어 제외했다.

**rubrics.jsonl은 참고용이며 평가의 기본 기준이 아니다. performance-feedback-actfl-speaking-v3를 우선한다.**
평가 system 역할에는 docs/prompts/opic_evaluation_system.md 원문을 넣는다. 대조 답변/승급 패턴은 보조 예시다.
Q000은 연습 피드백용이며 등급 근거 RAG에 넣지 않는다. IM1~IM3는 내부 잠정 기준 project-im-v1이다.

## 빌드 및 검증

```text
cd rag_docs
python scripts/prepare_question_bank.py --phase m2
python scripts/build_corpus.py
python scripts/test_corpus_v3.py
python scripts/check_monotonic.py
```

PyYAML만 필요하다. PowerShell/bash 모두 위 Python 명령을 사용한다.
원본 source/*.yaml을 편집하고 생성된 build/*.jsonl을 직접 수정하지 않는다.
질문 원문은 contrast_sets_04~09의 `# Qxxx 질문:` 주석에서 가져온다.
Q013~Q030의 기존 뱅크 문장과 대조 질문 불일치는 source/question_text_changes.yaml에 기록했다.
기존 pilot Q001~Q012 문장은 바뀌지 않았다. Q000과 Q013 이후 신규 pilot은 새 TTS가 필요하다.

## 태그와 보류

source/question_tags_rationale.yaml에 각 질문 전체와 근거 태그를 기록했다.
대표 유형은 전체 질문 검토표, 추가 기능·시간대·맥락은 실제 요청 구절로 결정했다.
역할극의 배경이 미래라는 이유만으로 future를 붙이지 않는다. Q071의 예상 영향 질문은 future로 분류한다.
슬롯별 pool의 교집합을 합쳐 보장 커버리지를 계산한다. 각 추첨의 실제 합집합은 API가 별도로 저장한다.
모든 시나리오는 future를 항상 보장하지 못한다는 경고를 표시한다.

check_monotonic의 기존 16건 경고는 report.md에 설명하고 해당 문항을 todo로 보류했다.
단어 수·문장 길이·연결어 개수는 공식 등급 경계가 아니므로 경고를 없애려고 답변을 기계적으로 늘리거나 줄이지 않았다.
기존 길이 참고 범위 밖 사례도 report에 남기되 구조 오류와 구분한다.
전체 질문 태그와 합성 답변의 교육적 적합성에 대한 독립적인 사람 검토는 아직 필요하다.

## 출처와 라이선스 메모


- ACTFL Proficiency Guidelines 2024는 ACTFL 저작물로, 비영리 교육 목적에 한해 **원문 전체를 수정 없이** 재배포하는 것만 허용합니다. 그래서 원문은 넣지 않았고, 기준을 우리 말로 다시 썼습니다. 일반 공개 서비스(특히 유료화) 전에는 ACTFL 사용 정책을 다시 확인하세요.
- IM1·IM2·IM3는 ACTFL에 없는 OPIc 고유 세분화이고, 공식 세부 기준이 공개되어 있지 않습니다. 공개 해설(TalkDrill, SpeakShark)을 참고해 **프로젝트 내부 기준**으로 정의했습니다.
- 합성 답변(C)은 모두 직접 작성했고, 학원·유튜브 모범답안은 옮기지 않았습니다.
- 자세한 출처: `SOURCES.md`


## 남은 검증

실제 수험생 채점 정확도, LLM 블라인드 교차 평가, 실제 STT 필러 비율 보정은 미실행이다.
합성 코퍼스의 형식 검증 통과를 실제 등급 정확도 검증으로 표시하지 않는다.
