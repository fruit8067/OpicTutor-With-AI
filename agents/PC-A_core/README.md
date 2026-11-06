# PC-A · 백엔드 핵심 (bootstrap → data-layer → session-api → integrator)

> 이 컴퓨터가 팀의 **임계 경로**입니다. 여기가 늦어지면 다른 두 대가 기다립니다.
> 오케스트레이터(PR 병합·공지 담당)도 이 컴퓨터 앞에 있는 것을 권장합니다.
> 공통 규칙은 [`../HANDOFF.md`](../HANDOFF.md), 계약은 [`../contracts.yaml`](../contracts.yaml)에 있습니다.
>
> AI-assisted: this guide was written with help from Claude (Anthropic).

| 순서 | 에이전트 | 파일 | 시작 조건 | 예상 |
|---|---|---|---|---|
| 1 | bootstrap | `1_bootstrap.yaml` | T0 (가장 먼저) | 45~60분 |
| 2 | data-layer | `2_data-layer.yaml` | M0 병합 직후 | 2~3시간 (M1은 1~1.5시간 안에) |
| 3 | session-api | `3_session-api.yaml` | data-layer M2 PR 올린 뒤 | 2~3시간 |
| 4 | integrator | `4_integrator.yaml` | M2(전원 병합) 공지 후 | 1.5~2시간 |

필요한 것: Docker Desktop, Python 3.11+, Node 20+, 마이크(통합 단계), `EMBED_API_KEY`(data-layer), 모든 키(integrator)

---

## 0. 준비 (한 번)

```bash
git clone https://github.com/fruit8067/OpicTutor-With-AI
cd OpicTutor-With-AI
git config user.name  "곽윤직 (PC-A)"
git config pull.rebase true
git config rebase.autoStash true
```

**오케스트레이터 사전 작업** (bootstrap 시작 전, [`HANDOFF.md`](../HANDOFF.md) 1.1·1.2절)
1. GitHub 저장소 설정: Rebase merge만 켜기, 브랜치 자동 삭제 끄기
2. `.gitattributes` 추가 PR → 병합
3. `main` 보호 규칙(ruleset)은 **bootstrap 병합 직후** 켭니다. 소유권 검사 워크플로가 bootstrap 이후에 생기기 때문입니다.
4. PC-B에 "corpus 바로 시작", PC-C에 "Colab 준비 시작"을 알립니다.

---

## 1단계 · bootstrap (T0)

```bash
git fetch origin
git switch -c agent/bootstrap origin/main
```

**에이전트 첫 메시지** (새 대화로 시작)

```text
너는 OpicTutor 프로젝트의 bootstrap 에이전트다. 지금 브랜치는 agent/bootstrap이고 이 컴퓨터는 PC-A다.
다른 컴퓨터 2대가 너의 결과물(M0)을 기다리고 있다. PC-B의 corpus 에이전트는 rag_docs/만 다루며 동시에 일하고 있다.

1. agents/HANDOFF.md, agents/orchestration.yaml, agents/contracts.yaml을 읽어라.
2. orchestration.yaml의 shared_preamble을 모든 작업의 규칙으로 삼아라.
3. agents/PC-A_core/1_bootstrap.yaml의 prompt를 작업 지시로 삼아 그대로 수행하라.
   local_checks를 실제로 실행하고, handoff_must_include 항목을 docs/handoff/bootstrap.md에 채워라.
4. rag_docs/ 는 건드리지 마라(PC-B corpus 소유).
5. 30분 안에 docs/handoff/bootstrap.md 초안을 커밋·푸시하고 Draft PR "[bootstrap] M0 WIP"를 만들어라.
6. 다 끝나면 PR 본문에 local_checks 결과를 붙이고 Ready for review로 바꿔라.
```

**끝나면 (오케스트레이터)**
1. PR 확인 → **Rebase and merge** → `[M0]` 공지 ([`HANDOFF.md`](../HANDOFF.md) 4절 문구)
2. `.github/workflows/ownership.yml` 추가(1.5절) → `main` ruleset 켜기
3. PC-B corpus에게 "M0 병합됨, rebase 후 M1 PR 올려 주세요"

---

## 2단계 · data-layer (M0 직후)

```bash
git fetch origin
git switch -c agent/data-layer origin/main
cp backend/.env.example backend/.env      # PowerShell: Copy-Item backend\.env.example backend\.env
# backend/.env 에 EMBED_API_KEY 입력
docker compose up -d
cd backend && python -m venv .venv && .venv\Scripts\activate   # bash: source .venv/bin/activate
pip install -r requirements.txt && cd ..
```

**에이전트 첫 메시지** (새 대화)

```text
너는 OpicTutor 프로젝트의 data-layer 에이전트다. 지금 브랜치는 agent/data-layer이고 이 컴퓨터는 PC-A다.
M1(DB 함수 전부 + 작업 큐 + app.db.dev 테스트 데이터 함수 + ingest)이 팀 전체의 임계 경로다.
PC-B(grader, worker-stt)와 PC-C(tts-host)가 M1을 기다린다. 1~1.5시간 안에 M1 PR을 먼저 올려라.

1. agents/HANDOFF.md, agents/orchestration.yaml, agents/contracts.yaml(contract_version 확인)을 읽어라.
2. orchestration.yaml의 shared_preamble을 모든 작업의 규칙으로 삼아라.
3. agents/PC-A_core/2_data-layer.yaml의 prompt를 작업 지시로 삼아 M1 → M2 순서로 수행하라.
4. M1이 끝나면 PR "[data-layer] M1 …"을 Ready로 올리고, 병합되면 같은 브랜치에서 git rebase origin/main 후 M2를 이어서 하라.
5. 푸시 전에는 항상 python agents/tools/check_ownership.py data-layer 를 실행하라.
6. docs/handoff/data-layer.md를 30분 안에 초안, M1·M2마다 갱신하라. 특히 app.db.dev 사용 예시를 반드시 적어라.
```

**M1 PR이 올라오면 (오케스트레이터)**
- corpus M1 PR이 먼저 병합되어 있어야 합니다. 순서: **corpus M1 → data-layer M1**
- 병합 후 `[M1]` 공지 → 전원 rebase

---

## 3단계 · session-api (data-layer M2 PR 올린 뒤)

data-layer M2 PR이 아직 병합 대기 중이어도 시작합니다. 같은 DB를 쓰므로 data-layer 에이전트 대화는 끝낸 상태여야 합니다.

```bash
git fetch origin
git switch -c agent/session-api origin/main
python -m scripts.db_reset --yes   # backend/ 에서, M1 이후
python -m scripts.ingest_rag
```

**에이전트 첫 메시지** (새 대화)

```text
너는 OpicTutor 프로젝트의 session-api 에이전트다. 지금 브랜치는 agent/session-api이고 이 컴퓨터는 PC-A다.
data-layer M1은 main에 병합되어 있다. 너는 SQL을 쓰지 않고 app.db 함수만 호출하는 얇은 HTTP 계층이다.

1. agents/HANDOFF.md, agents/orchestration.yaml, agents/contracts.yaml, docs/handoff/data-layer.md, docs/handoff/corpus.md를 읽어라.
2. orchestration.yaml의 shared_preamble을 모든 작업의 규칙으로 삼아라.
3. agents/PC-A_core/3_session-api.yaml의 prompt를 작업 지시로 삼아 그대로 수행하라.
   TTS 준비가 아직 없으면 app.db.dev.seed_session(status="ready")로 앞 단계를 건너뛰어 테스트하라.
4. 푸시 전에는 항상 python agents/tools/check_ownership.py session-api 를 실행하라.
5. docs/handoff/session-api.md를 30분 안에 초안, 완료 시 갱신하고 Draft PR → Ready로 올려라.
```

**M2 병합 (오케스트레이터)** — 순서: corpus → data-layer → tts-host → worker-stt → session-api → grader → frontend
하나 병합할 때마다 다음 차례에게 "rebase 후 알려 주세요".

---

## 4단계 · integrator (M2 공지 후)

```bash
git fetch origin
git switch -c agent/integrator origin/main
# backend/.env 에 LLM_API_KEY, EMBED_API_KEY 모두 입력
```

**에이전트 첫 메시지** (새 대화)

```text
너는 OpicTutor 프로젝트의 integrator 에이전트다. 지금 브랜치는 agent/integrator이고 이 컴퓨터는 PC-A다.
Phase 1의 모든 PR이 main에 병합되었다(M2). 각자 만든 부품을 실제로 연결해 처음부터 끝까지 완주시키는 것이 너의 일이다.

1. agents/HANDOFF.md, agents/orchestration.yaml, agents/contracts.yaml, docs/handoff/*.md 전부를 읽어라.
2. orchestration.yaml의 shared_preamble을 모든 작업의 규칙으로 삼아라.
3. agents/PC-A_core/4_integrator.yaml의 prompt를 작업 지시로 삼아 그대로 수행하라.
   연결 버그만 고치고, 고친 파일마다 원인과 원래 소유자를 handoff에 기록하라. 재설계가 필요하면 change request.
4. 완료되면 PR "[integrator] M3 …"을 올려라.
```

**끝나면** `[M3]` 공지 → PC-C에 reviewer 시작 요청

---

## 기다리는 동안

| 기다리는 것 | 그동안 할 일 |
|---|---|
| bootstrap 병합 | 다른 컴퓨터 진행 확인, 공지 |
| data-layer M1 병합 | (오케스트레이터) corpus M1 PR 확인·병합 |
| M2 병합 순서 | 각 PR 체크리스트 확인 ([`HANDOFF.md`](../HANDOFF.md) 1.4절) |

같은 컴퓨터에서 다음 에이전트를 미리 시작하려면 폴더를 분리합니다. DB를 쓰는 에이전트 둘을 동시에 돌리지는 마세요.

```bash
git worktree add ../opic-session-api -b agent/session-api origin/main
```
