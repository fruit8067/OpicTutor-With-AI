먼저 프로젝트 폴더 구조를 확인해서 RAG 파이프라인에 맞는 수집 전략을 세워볼게요.

프로젝트 폴더를 봤는데, 지금은 `PROJECT_REQUIREMENTS.md`만 있는 초기 단계예요. 요구사항의 "STT로 받은 답변을 등급으로 분류한다"는 기능을 기준으로 수집 전략을 짰습니다.

## 0. 먼저 짚을 문제: 정답 등급이 붙은 실제 답변이 거의 없음

등급이 확인된 실제 오픽 답변은 공개된 게 거의 없어요. 학원이나 유튜브에서 "IH 답변", "AL 모범답안"이라고 붙인 건 강사가 감으로 붙인 라벨이고, 저작권도 걸려 있습니다. 그래서 이 프로젝트는 많이 모으는 것보다 **등급 라벨을 믿을 수 있게 만드는 것**이 더 중요합니다. 출처마다 신뢰도를 매겨서 따로 관리하는 걸 추천해요.

| 신뢰도 | 출처 | 사용법 |
|---|---|---|
| **A** | ACTFL 2024 Guidelines 원문, OPIc 공식 등급 설명, 성적표로 인증된 실제 녹음(본인·지인·커뮤니티에서 동의받은 것) | 루브릭과 기준 예시로 원문 그대로 사용 |
| **B** | 학원·강사·블로그의 "등급별 답변" | **원문은 저장하지 않음.** "IM2와 IH의 차이"처럼 특징만 뽑아서 직접 다시 씀 |
| **C** | LLM으로 합성한 답변 | 루브릭을 기준으로 생성하고 교차 검증을 통과한 것만 채택. 양으로는 대부분이 여기서 나옴 |

참고로 IM1·IM2·IM3는 ACTFL 기준에는 없는 OPIc만의 세분화예요. ACTFL에는 Intermediate Mid 하나뿐이라서, IM1~3의 경계는 OPIc 공식 설명과 B 출처를 보고 직접 정의해야 합니다.

## 1. 코퍼스는 4개 층으로 구성

1. **루브릭 문서**: 등급(NL, NM, NH, IL, IM1, IM2, IM3, IH, AL)마다 1개 청크. 담을 내용은 과제 수행 능력, 문장 단위(단어 → 문장 → 문단), 시제 통제, 연결어, 오류가 의사소통에 미치는 영향, 그리고 "이 등급에서 무너지는 지점(breakdown)"입니다.
2. **등급 대조 세트 (핵심)**: **같은 질문 하나에 9개 등급 답변**을 한 세트로 묶습니다. 사용자 답변을 평가할 때 같은 질문 유형의 대조 세트를 통째로 검색해 오면, LLM이 "IM3보다는 낫고 IH보다는 부족하다"는 식으로 비교 판정을 할 수 있어요. 점수만 맞히게 하는 것보다 훨씬 안정적입니다.
3. **승급 패턴 문서**: IM2→IM3, IM3→IH처럼 한 단계 올리려면 무엇이 바뀌는지 정리합니다(시제 전환, 묘사 디테일, 문단 구조 등). 채팅 피드백 기능에 그대로 쓰입니다.
4. **문항 메타**: 질문 유형(묘사, 루틴, 과거 경험, 비교, 롤플레이, 사회 이슈), 서베이 주제, 콤보 구조(같은 주제로 2~3문항이 이어지는 방식).

## 2. 합성 답변 파이프라인 (C 출처)

1. **문항 뱅크 만들기**: 질문 유형 6종 × 주요 서베이 주제 10~15개 → 60~90문항.
2. **등급별 제약을 걸고 생성**: 예를 들어 NL은 단어 나열과 암기 표현 위주, 아주 짧게. IM2는 단문을 이어 붙인 수준에 현재시제 위주, 문단 구성은 약함. AL은 문단 단위로 말하고, 과거·현재·미래 시제를 통제하고, 서술의 흐름이 있음. 길이·문장 수·오류 빈도를 등급마다 숫자로 정해 두면 등급별 답변이 서로 겹치지 않습니다.
3. **STT 스타일로 변환**: 실제 사용자 입력은 STT 결과물이라 구두점이 없고, "um, uh", 반복, 자기 수정이 섞여 있어요. 문서도 **깔끔한 버전과 STT 버전 두 가지로 저장**해야 임베딩 검색이 잘 맞습니다. 이걸 빼먹으면 검색 품질이 크게 떨어져요.
4. **블라인드 교차 평가**: 생성에 쓰지 않은 다른 모델이 등급을 모른 채 판정하게 하고, 의도한 등급과 일치하거나 ±1 등급 이내인 것만 채택합니다. 특히 IM1/IM2/IM3, IH/AL처럼 이웃한 등급끼리 헷갈리는지 집중 점검합니다.
5. **사람이 샘플 검수**: 등급마다 10% 정도는 직접, 또는 실제 등급을 받은 지인이 확인합니다.

## 3. 문서 스키마 (예시)

```json
{
  "id": "Q031-IM2-stt",
  "doc_type": "answer",
  "level": "IM2",
  "level_rank": 6,
  "question_type": "past_experience",
  "topic": "travel_domestic",
  "question": "Tell me about a memorable trip you took...",
  "answer_text": "um so last year i go to busan with my friend and ...",
  "text_style": "stt",
  "word_count": 95,
  "features": {
    "sentence_level": "connected_sentences",
    "tense_control": "inconsistent_past",
    "connectors": ["so", "and then", "because"],
    "error_impact": "noticeable_not_blocking"
  },
  "rationale": "과거 경험을 순서대로 말하지만 과거시제가 자주 무너지고 문단 구성이 없음",
  "upgrade_tip": "IM3로 가려면 과거시제를 유지하고 감정이나 결과를 덧붙이기",
  "contrast_set_id": "Q031",
  "source_tier": "C",
  "verified_by": ["model_b", "human"],
  "license": "self_generated"
}
```

- **청킹**: 답변 1개 = 청크 1개로 하고, `rationale`을 같은 청크에 넣습니다. 그래야 왜 그 등급인지가 함께 검색돼요.
- **메타데이터 필터**: `question_type`, `level`, `contrast_set_id`로 걸러서 대조 세트를 한 번에 가져옵니다.

## 4. 목표 규모와 단계

- **1단계**: 루브릭 9개 + 승급 패턴 8개. A 출처로 정리합니다.
- **2단계 (MVP)**: 60문항 × 9등급 × 2스타일 ≈ 약 1,080개 답변 문서.
- **3단계 (평가셋)**: 실제 등급이 확인된 답변 30~50개를 모읍니다. **이건 RAG에 넣지 않고** 평가 정확도를 재는 테스트셋으로만 씁니다. 같이 넣으면 정확도가 부풀려집니다.
- **4단계**: 서비스 운영 중에 사용자가 실제 성적을 인증하면 동의를 받아 A 출처로 추가합니다.

한 가지 확인할 점이 있어요. `PROJECT_REQUIREMENTS.md`에는 평가 범위가 "AH부터 IM까지"로 적혀 있어서, 이번 범위(AL~NL)에 맞게 고쳐 두면 좋겠습니다. 원하시면 다음 단계로 문항 뱅크(60문항)와 등급별 생성 제약표, 생성·검증 스크립트를 이 프로젝트 폴더에 바로 만들어 드릴게요.

Sources:
- [ACTFL Proficiency Guidelines 2024 (PDF)](https://www.isbe.net/Documents/ACTFL-Proficiency-Guidelines-2024.pdf)
- [ACTFL's New 2024 Proficiency Guidelines – What's New?](https://icosahedron-saxophone-bwlc.squarespace.com/blog/actfls-new-2024-guidelines-whats-new)
- [ACTFL Level Descriptions – UMN](https://cla.umn.edu/language-center/students/language-testing/actfl-testing/actfl-level-descriptions)
- [Oral Proficiency Module – Intermediate Low/Mid (UT Austin COERLL)](https://oralproficiency.coerll.utexas.edu/?p=77)
- [OPIc Levels Explained: NL to AL (TalkDrill)](https://www.talkdrill.com/blog/exams/opic-toeic-speaking/opic-levels-im1-im2-im3-ih-al/)
- [오픽 등급 체계와 레벨별 수준](https://baby.tali.kr/opic-level)