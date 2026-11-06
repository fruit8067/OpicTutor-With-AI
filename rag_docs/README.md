# OpicTutor RAG 문서 코퍼스

OPIc 답변 평가·피드백용 RAG 문서입니다. 등급 범위는 NL~AL(9단계)입니다.
사람이 편집하는 원본은 `source/*.yaml`이고, 임베딩에 넣는 것은 `build/*.jsonl`입니다.

> AI-assisted: 루브릭 재서술, 문항, 합성 답변, 스크립트는 Claude(Anthropic)의 도움으로 작성했습니다.

## 구성

| 파일 | doc_type | 개수 | 출처 등급 | 용도 |
|---|---|---|---|---|
| `build/rubrics.jsonl` | rubric | 9 | A(ACTFL 재서술) / B(IM1~3 프로젝트 정의) | 등급별 판정 기준 |
| `build/upgrade_patterns.jsonl` | upgrade_pattern | 8 | B | 다음 등급으로 올리는 피드백 |
| `build/questions.jsonl` | question | 30 (파일럿 12 + 확장 대기 18) | 자체 작성 | 문항 메타·필터 |
| `build/answers.jsonl` | answer | 216 (12문항 × 9등급 × clean/stt) | C(합성) | 등급 대조 예시 |

## 폴더

```
rag_docs/
├─ source/                  # 편집 원본 (여기만 고치기)
│  ├─ rubrics.yaml          # 등급 루브릭 9 + 승급 패턴 8
│  ├─ level_constraints.yaml# 등급별 길이·시제·오류·STT 필러 비율
│  ├─ question_bank.yaml    # 문항 30개 (status: pilot / todo)
│  └─ contrast_sets_0X.yaml # 문항별 9등급 답변 (text / rationale / upgrade_tip)
├─ scripts/
│  ├─ build_corpus.py       # YAML → JSONL, STT 버전 생성, 길이·누락 검사 → build/report.md
│  ├─ check_monotonic.py    # 등급↑에 따라 단어 수·문장 길이·고급 연결어가 늘어나는지 점검
│  ├─ generate_answers.py   # todo 문항 9등급 생성 (LLM)
│  ├─ cross_validate.py     # 다른 모델로 블라인드 채점, 혼동 행렬
│  └─ llm.py                # GEN_MODEL / JUDGE_MODEL 분리
└─ build/                   # 생성물 (직접 수정 금지)
```

## 작업 순서

```bash
cd rag_docs
pip install pyyaml anthropic
python scripts/build_corpus.py          # 0 = 통과
python scripts/check_monotonic.py       # 경고 0건 목표

# 확장 (ANTHROPIC_API_KEY 필요, 생성·평가 모델을 다르게)
export GEN_MODEL=claude-sonnet-5-5 JUDGE_MODEL=claude-haiku-5-5
python scripts/generate_answers.py --limit 6
python scripts/build_corpus.py && python scripts/check_monotonic.py
python scripts/cross_validate.py --only Q013,Q014,...   # fail 항목은 수정 후 재빌드
```

## 검색(RAG) 사용 팁

- **평가할 때**: 사용자 STT 답변으로 `answers.jsonl` 중 `text_style=stt` + 같은 `question_type`을 검색하고, 가장 가까운 문항의 `contrast_set_id`로 **9등급 세트를 통째로** 가져와 LLM이 비교 판정하게 합니다. 해당 등급의 `rubric`도 같이 넣습니다.
- **피드백할 때**: 판정 등급 → `upgrade_pattern`(from_level)과 다음 등급 답변의 `upgrade_tip`을 가져옵니다.
- 임베딩 필드는 `text`이고, 나머지 필드는 메타데이터 필터로 씁니다.

## 출처와 라이선스 메모

- ACTFL Proficiency Guidelines 2024는 ACTFL 저작물로, 비영리 교육 목적에 한해 **원문 전체를 수정 없이** 재배포하는 것만 허용합니다. 그래서 원문은 넣지 않았고, 기준을 우리 말로 다시 썼습니다. 일반 공개 서비스(특히 유료화) 전에는 ACTFL 사용 정책을 다시 확인하세요.
- IM1·IM2·IM3는 ACTFL에 없는 OPIc 고유 세분화이고, 공식 세부 기준이 공개되어 있지 않습니다. 공개 해설(TalkDrill, SpeakShark)을 참고해 **프로젝트 내부 기준**으로 정의했습니다.
- 합성 답변(C)은 모두 직접 작성했고, 학원·유튜브 모범답안은 옮기지 않았습니다.
- 자세한 출처: `SOURCES.md`

## 아직 남은 일 (중요)

1. **블라인드 교차 평가 미실행**: 파일럿 108개는 작성자 검토와 자동 점검만 거쳤습니다. API 키를 넣고 `cross_validate.py`를 돌려야 합니다.
2. **실제 등급 평가셋(A)**: 성적이 확인된 실제 녹음 30~50개를 모아 **RAG에 넣지 말고** 평가 정확도 측정에만 쓰세요.
3. **STT 필러 비율 보정**: `level_constraints.yaml`의 stt 값은 추정치입니다. 실제 STT 출력(Whisper 등)과 비교해 보정이 필요합니다.
4. 확장 18문항 생성 → 목표 60문항이면 question_bank에 30문항 더 추가.
