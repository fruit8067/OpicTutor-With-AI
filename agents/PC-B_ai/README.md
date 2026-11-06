# PC-B · 데이터·AI (corpus → grader → worker-stt)

> 문제 은행·평가 근거 데이터, 종료 후 종합 평가, 로컬 STT를 맡습니다.
> **CPU가 가장 좋은 컴퓨터**에 배정하세요(Whisper 처리 속도). `LLM_API_KEY`, `EMBED_API_KEY`가 필요합니다.
> 공통 규칙은 [`../HANDOFF.md`](../HANDOFF.md), 계약은 [`../contracts.yaml`](../contracts.yaml)에 있습니다.
>
> AI-assisted: this guide was written with help from Claude (Anthropic).

| 순서 | 에이전트 | 파일 | 시작 조건 | 예상 |
|---|---|---|---|---|
| 1 | corpus | `1_corpus.yaml` | **T0 (bootstrap과 동시에)** | 2.5~3.5시간 (M1은 1시간 안에) |
| 2 | grader | `2_grader.yaml` | corpus M2 PR 올린 뒤 | 2.5~3.5시간 |
| 3 | worker-stt | `3_worker-stt.yaml` | grader PR 올린 뒤 | 2~3시간 |

필요한 것: Python 3.11+, Docker Desktop(grader부터), 마이크(worker-stt 테스트 녹음), `LLM_API_KEY`, `EMBED_API_KEY`

---

## 0. 준비 (한 번)

```bash
git clone https://github.com/fruit8067/OpicTutor-With-AI
cd OpicTutor-With-AI
git config user.name  "곽윤직 (PC-B)"
git config pull.rebase true
git config rebase.autoStash true
```

---

## 1단계 · corpus (T0, bootstrap과 동시에)

corpus는 `rag_docs/`만 다루므로 bootstrap을 기다리지 않습니다.

```bash
git fetch origin
git switch -c agent/corpus origin/main
```

> **주의 (M0 전까지만):** 지금 `.gitignore`의 `build/` 규칙 때문에 `rag_docs/build/`에 **새로** 만든 파일(`scenarios.json`, `VERSION`)이 무시됩니다. bootstrap이 고치기 전까지는 강제로 추가하세요.
> ```bash
> git add -f rag_docs/build/scenarios.json rag_docs/build/VERSION
> ```
> `agents/tools/check_ownership.py`도 M0 이후에 생깁니다. M0 병합 공지를 받으면 `git rebase origin/main` 후 실행합니다.

**에이전트 첫 메시지** (새 대화)

```text
너는 OpicTutor 프로젝트의 corpus 에이전트다. 지금 브랜치는 agent/corpus이고 이 컴퓨터는 PC-B다.
PC-A의 bootstrap이 동시에 뼈대를 만들고 있다. 너는 rag_docs/** 만 수정한다.
M1(Q000 추가, scenarios.json의 default 시나리오, VERSION)을 1시간 안에 먼저 끝내라. PC-A·PC-C가 기다린다.

1. agents/HANDOFF.md, agents/orchestration.yaml, agents/contracts.yaml을 읽어라.
2. orchestration.yaml의 shared_preamble을 모든 작업의 규칙으로 삼아라.
3. agents/PC-B_ai/1_corpus.yaml의 prompt를 작업 지시로 삼아 M1 → M2 순서로 수행하라.
4. rag_docs/build/에 새로 만든 파일은 .gitignore 때문에 무시될 수 있으니 git add -f로 추가하라(M0 전까지).
5. M1이 끝나면 커밋·푸시하고 Draft PR "[corpus] M1 …"을 만들어라. 오케스트레이터가 M0 병합을 알리면
   git rebase origin/main → python agents/tools/check_ownership.py corpus → PR을 Ready로 바꿔라.
6. M1이 병합되면 같은 브랜치에서 rebase 후 M2를 이어서 하고 새 PR을 올려라.
7. docs/handoff/corpus.md에 M1 이후 바뀐 문항 문장 목록(TTS 재생성 대상)을 반드시 적어라.
```

**M2에서 시간이 걸리는 부분:** 대조 세트가 Q013~Q187(`contrast_sets_04`~`08`)이라 문제 은행에 150개 넘게 분류해 넣어야 합니다. 규칙 기반 스크립트로 1차 분류하게 했습니다.

---

## 2단계 · grader (corpus M2 PR 올린 뒤)

data-layer M1이 병합되기 전이면 코드·검증 테스트부터 작성하고, DB 연동 테스트는 M1 이후에 합니다.

```bash
git fetch origin
git switch -c agent/grader origin/main
cp backend/.env.example backend/.env       # LLM_API_KEY, EMBED_API_KEY 입력
docker compose up -d
cd backend && python -m venv .venv && .venv\Scripts\activate   # bash: source .venv/bin/activate
pip install -r requirements.txt
python -m scripts.db_reset --yes && python -m scripts.ingest_rag   # data-layer M1 이후
```

**에이전트 첫 메시지** (새 대화)

```text
너는 OpicTutor 프로젝트의 grader 에이전트다. 지금 브랜치는 agent/grader이고 이 컴퓨터는 PC-B다.
시험 종료 후 전체 답변을 한 번의 LLM 요청으로 평가하는 엔진이 너의 일이고, 이 서비스에서 가장 중요한 부분이다.
평가 기준은 docs/prompts/opic_evaluation_system.md(opic-evaluation-system-v3, project-im-v1 포함)이며
그 파일을 한 글자도 바꾸지 않고 그대로 읽어 싣는다. 1번 자기소개는 채점 제외, 영역별 숫자 점수는 없다(서술 진단).

1. agents/HANDOFF.md, agents/orchestration.yaml, agents/contracts.yaml(contract_version 3 이상), docs/prompts/opic_evaluation_system.md,
   docs/OPIC_SCORING_RESEARCH.md, docs/handoff/corpus.md, docs/handoff/data-layer.md를 읽어라.
2. orchestration.yaml의 shared_preamble을 모든 작업의 규칙으로 삼아라.
3. agents/PC-B_ai/2_grader.yaml의 prompt를 작업 지시로 삼아 그대로 수행하라.
   data-layer M1이 아직이면 시스템 프롬프트 추출·검증 로직·pytest부터 하고, M1 공지 후 rebase해서 DB 연동을 진행하라.
4. eval_exam은 실행 전에 비용을 출력하고 확인을 받아라. 리포트는 backend/eval_reports/에 커밋하라.
5. 푸시 전에는 항상 python agents/tools/check_ownership.py grader 를 실행하라.
6. docs/handoff/grader.md를 30분 안에 초안, 완료 시 시도별 평가 수치 표를 채워라.
```

---

## 3단계 · worker-stt (grader PR 올린 뒤)

```bash
git fetch origin
git switch -c agent/worker-stt origin/main
# 첫 실행 때 Whisper 모델(small.en, 약 500MB)을 내려받습니다
```

**에이전트 첫 메시지** (새 대화)

```text
너는 OpicTutor 프로젝트의 worker-stt 에이전트다. 지금 브랜치는 agent/worker-stt이고 이 컴퓨터는 PC-B다.
워커 러너(tts_prepare·stt·evaluate 작업 실행)와 로컬 faster-whisper STT·관측 지표가 너의 일이다.
STT 저장이 끝나야 사용자가 다음 문항으로 넘어간다. "끝나지 않는 처리 중" 상태가 생기지 않게 하는 것이 핵심이다.

1. agents/HANDOFF.md, agents/orchestration.yaml, agents/contracts.yaml, docs/handoff/data-layer.md를 읽어라.
2. orchestration.yaml의 shared_preamble을 모든 작업의 규칙으로 삼아라.
3. agents/PC-B_ai/3_worker-stt.yaml의 prompt를 작업 지시로 삼아 그대로 수행하라.
   app.db.dev.seed_queued_answer로 테스트 답변을 만들고, 이 컴퓨터 마이크로 직접 녹음한 파일로도 확인하라.
4. 녹음 파일은 커밋하지 마라(data/ 와 *.webm은 무시 대상).
5. 푸시 전에는 항상 python agents/tools/check_ownership.py worker-stt 를 실행하라.
6. docs/handoff/worker-stt.md에 처리 시간 측정표와 권장 Whisper 모델을 적어라.
```

---

## 끝난 뒤

M2 병합 순서에서 worker-stt는 tts-host 다음, session-api 앞입니다. worker-stt가 늦으면 뒤 PR들이 기다립니다. 오케스트레이터가 순서를 조정할 수 있으니 진행 상황을 handoff에 자주 갱신하세요.

integrator(PC-A)가 통합 중 이 컴퓨터 담당 모듈의 버그를 물어볼 수 있습니다. M3까지는 이 저장소를 그대로 두세요.
