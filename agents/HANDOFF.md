# OpicTutor 에이전트 인수인계서

> 각 컴퓨터에서 에이전트를 시작하기 전에 이 문서를 처음부터 끝까지 읽어 주세요.
> 규칙의 원본은 [`orchestration.yaml`](orchestration.yaml)(협업 규칙)과 [`contracts.yaml`](contracts.yaml)(구현 계약)입니다. 이 문서는 그 두 파일을 사람이 따라 하기 쉽게 풀어 쓴 실행 안내서입니다. 서로 다르면 YAML이 우선합니다.
>
> AI-assisted: this handoff guide was written with help from Claude (Anthropic).

---

## 0. 한눈에 보기

```
           Phase 0              Phase 1 (동시에, 컴퓨터별)                 Phase 2        Phase 3
main ──●───────────●──────────────●─────────────────────────●─────────────●──────────────●──▶
       │  bootstrap │ M0           │ M1                       │ M2          │ M3           │ M4
       └─ agent/bootstrap          │  (corpus·data-layer 먼저) │ (전원 병합)  │ integrator   │ reviewer
                    ├─ agent/corpus ────────●(M1 PR)──────────●(M2 PR)
                    ├─ agent/data-layer ────●(M1 PR)──────────●(M2 PR)
                    ├─ agent/session-api ─────────────────────●
                    ├─ agent/worker-stt ──────────────────────●
                    ├─ agent/grader ──────────────────────────●
                    ├─ agent/tts-host ────────────────────────●
                    └─ agent/frontend ────────────────────────●
```

- **에이전트 1개 = 브랜치 1개 = 소유 경로 묶음 1개**입니다. 남의 경로는 고치지 않으므로 병합 충돌이 원칙적으로 생기지 않습니다.
- `main`에는 **오케스트레이터만** 병합합니다. 병합 방식은 **Rebase and merge** 하나만 씁니다.
- 계약(`contracts.yaml`)은 오케스트레이터만 바꿉니다. 바꿔야 하면 change request를 올립니다.

---

## 1. GitHub 병합 전략

### 1.1 저장소 설정 (오케스트레이터가 Phase 0 전에 한 번)

**Settings → General → Pull Requests**

| 항목 | 설정 | 이유 |
|---|---|---|
| Allow merge commits | ❌ 끔 | 히스토리를 한 줄로 유지 |
| Allow squash merging | ❌ 끔 | M1 이후에도 같은 브랜치를 계속 쓰기 때문(아래 1.3) |
| Allow rebase merging | ✅ 켬 | **유일한 병합 방식** |
| Always suggest updating pull request branches | ✅ 켬 | 뒤처진 PR에 "Update branch" 버튼 표시 |
| Automatically delete head branches | ❌ 끔 | M1 병합 후에도 M2 작업을 같은 브랜치에서 이어 감 |

**Settings → Rules → Rulesets → New branch ruleset** (대상: `main`)

| 규칙 | 설정 |
|---|---|
| Restrict deletions | ✅ |
| Block force pushes | ✅ |
| Require linear history | ✅ |
| Require a pull request before merging | ✅, **Required approvals: 0** |
| Require status checks to pass | ✅ `ownership` (1.5의 워크플로를 먼저 추가한 뒤) |
| Require branches to be up to date before merging | ✅ |
| Bypass list | 비움 (오케스트레이터도 PR로만 병합) |

> **승인 수를 0으로 두는 이유:** 모든 컴퓨터가 같은 GitHub 계정을 쓰면, 자기 PR은 자기가 승인할 수 없습니다. 그래서 "승인" 대신 **소유권 검사(status check)와 오케스트레이터의 확인**을 품질 관문으로 씁니다. 컴퓨터마다 다른 계정을 쓴다면 승인 1로 올려도 됩니다.

### 1.2 줄바꿈·바이너리 통일 (Phase 0 전에 한 번)

Windows와 다른 OS가 섞이면 줄바꿈(CRLF/LF) 차이 때문에 내용이 같은 파일이 수천 줄 변경으로 잡힙니다. 실제로 이 저장소에서 이미 이 현상이 생겼습니다. 오케스트레이터가 루트에 `.gitattributes`를 추가합니다.

```gitattributes
* text=auto eol=lf
*.ps1 text eol=crlf
*.bat text eol=crlf
*.mp3 binary
*.wav binary
*.webm binary
*.png binary
*.ipynb text eol=lf
```

```bash
git switch -c orchestrator/gitattributes origin/main
# .gitattributes 작성 후
git add --renormalize .
git commit -m "[orchestrator] Normalize line endings"
git push -u origin orchestrator/gitattributes   # → PR → Rebase and merge
```

### 1.3 왜 Rebase and merge만 쓰나

- **Squash merge의 문제:** corpus와 data-layer는 M1에서 한 번 병합하고 **같은 브랜치에서 M2 작업을 이어 갑니다.** squash로 병합하면 브랜치의 원래 커밋과 `main`의 squash 커밋이 서로 다른 것으로 취급됩니다. 그러면 다음 rebase 때 이미 병합된 변경이 다시 적용되거나 충돌이 납니다.
- **Rebase and merge의 장점:** 커밋 내용이 그대로 `main`에 올라가므로, 다음 `git rebase origin/main` 때 git이 이미 반영된 커밋을 알아서 건너뜁니다.
- **Merge commit을 쓰지 않는 이유:** 8개 브랜치의 merge commit이 쌓이면 히스토리를 읽기 어렵고 문제가 생겼을 때 되돌리기도 어렵습니다.

### 1.4 병합 순서

| 시점 | 병합 대상 (이 순서대로) | 병합 후 공지 |
|---|---|---|
| M0 | `orchestrator/gitattributes` → `agent/bootstrap` | "M0 완료, Phase 1 시작" |
| M1 | `agent/corpus`(M1 PR) → `agent/data-layer`(M1 PR) | "M1 병합됨, 전원 rebase" |
| M2 | corpus → data-layer → tts-host → worker-stt → session-api → grader → frontend | 하나 병합할 때마다 "다음 PR rebase 후 알려 주세요" |
| M3 | `agent/integrator` | "M3 완료, reviewer 시작" |
| M4 | `agent/reviewer` | "MVP 완료" 또는 수정 지시 |
| 수시 | `orchestrator/cr-<id>-<NN>` (계약 변경) | "contract v{N}, 전원 rebase" |

**M2 순서의 이유:** 데이터(corpus) → 저장 계층(data-layer) → 그 함수를 호출하는 쪽(tts-host, worker-stt, session-api, grader) → 화면(frontend) 순입니다. 뒤 PR이 앞 PR의 실제 코드 위에서 다시 확인되도록 매번 rebase를 거칩니다.

**병합 전 오케스트레이터 체크리스트** (PR 하나마다)

- [ ] `ownership` 검사 통과 (남의 경로 변경 0)
- [ ] 브랜치가 최신 `main` 기준 (뒤처졌으면 에이전트에게 rebase 요청)
- [ ] PR 본문에 `local_checks` 실행 결과가 붙어 있음
- [ ] `docs/handoff/<id>.md`가 갱신됨 (상태·실행 방법·알려진 문제)
- [ ] `.env`, `data/`, 녹음 파일, API 키가 diff에 없음
- [ ] 해당 YAML의 구현 조건·local_checks 충족. 아직 못 한 검증은 대기/실패로 적고 병합하지 않음
- [ ] `done_when` 중 PR 병합 조건은 위 검증 후 병합 시 충족 여부를 확인 (병합 전 체크에 순환 조건으로 요구하지 않음)

### 1.5 소유권 검사 자동화 (선택이지만 권장)

bootstrap이 `agents/tools/check_ownership.py`를 만든 뒤, 오케스트레이터가 `.github/workflows/ownership.yml`을 추가합니다. 브랜치 이름 `agent/<id>`에서 에이전트 ID를 읽어 검사합니다.

```yaml
# AI-assisted: this workflow was written with help from Claude (Anthropic).
name: ownership
on:
  pull_request:
    branches: [main]
jobs:
  ownership:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install pyyaml
      - name: check
        run: |
          BRANCH="${{ github.head_ref }}"
          case "$BRANCH" in
            agent/bootstrap) python agents/tools/check_ownership.py bootstrap --phase0 --base origin/main ;;
            agent/*)         python agents/tools/check_ownership.py "${BRANCH#agent/}" --base origin/main ;;
            orchestrator/*)  echo "orchestrator branch — skip" ;;
            *)               echo "branch must be agent/<id> or orchestrator/<topic>"; exit 1 ;;
          esac
```

### 1.6 충돌이 났을 때

소유권을 지켰다면 충돌은 거의 생기지 않습니다. 충돌이 생겼다면 **누군가 남의 경로를 건드렸다는 신호**입니다.

1. 충돌 파일의 소유자를 `contracts.yaml` → `ownership`에서 확인합니다.
2. **소유자의 버전(= `main` 쪽)이 이깁니다.** 내 브랜치의 변경은 버립니다: `git checkout --ours <file>`. rebase 중에는 `--ours`가 `main` 쪽입니다.
3. 그 변경이 꼭 필요했다면 change request로 소유자나 오케스트레이터에게 요청합니다.
4. 예외는 `frontend/package-lock.json`입니다. 이 파일은 frontend만 고칩니다. 다른 에이전트는 npm 패키지를 추가하지 말고 handoff에 요청합니다.

---

## 2. 각 컴퓨터 시작 절차

### 2.1 준비 (컴퓨터마다 한 번)

```bash
git clone https://github.com/fruit8067/OpicTutor-With-AI
cd OpicTutor-With-AI

# 이 컴퓨터가 맡을 에이전트를 커밋 작성자 이름에 표시 (누가 무엇을 했는지 추적)
git config user.name  "곽윤직 (agent:<agent_id>)"
git config user.email "rhkrdbswlr@gmail.com"
git config pull.rebase true
git config rebase.autoStash true
```

필요한 도구는 `orchestration.yaml` → `agents.<id>.needs`에 있습니다. 대부분 Python 3.11+, Node 20+, Docker Desktop입니다.

### 2.2 브랜치 만들기 (Phase 1 시작 공지 = M0 이후)

```bash
git fetch origin
git switch -c agent/<agent_id> origin/main
```

### 2.3 환경 설정

```bash
# PowerShell
Copy-Item backend\.env.example backend\.env
# bash
cp backend/.env.example backend/.env
```

필요한 키만 채웁니다. `.env`는 **절대 커밋하지 않습니다.** 키는 메신저 공지 채널에 올리지 말고 각자 직접 입력하세요.

| 에이전트 | 필요한 키 |
|---|---|
| data-layer | `EMBED_API_KEY` |
| grader | `LLM_API_KEY`, `EMBED_API_KEY` |
| integrator | 위 전부 |
| 나머지 | 없음 |

DB가 필요한 에이전트(corpus, frontend 외 전원)는 다음을 실행합니다.

```bash
docker compose up -d
cd backend
python -m venv .venv
.venv\Scripts\activate        # PowerShell
source .venv/bin/activate     # bash
pip install -r requirements.txt
python -m scripts.db_reset --yes      # M1 병합 이후에 동작
python -m scripts.ingest_rag          # M1 병합 이후, EMBED_API_KEY 필요
```

각 컴퓨터는 **자기 로컬 DB**를 씁니다. 공용 DB 서버는 두지 않습니다.

### 2.4 에이전트에게 보낼 첫 메시지 (복사해서 `<>`만 바꾸기)

```text
너는 OpicTutor 프로젝트의 <agent_id> 에이전트다. 지금 브랜치는 agent/<agent_id>다.

1. agents/HANDOFF.md, agents/orchestration.yaml, agents/contracts.yaml을 읽어라.
2. orchestration.yaml의 shared_preamble을 모든 작업의 규칙으로 삼아라.
3. agents/<PC 폴더>/<파일명>.yaml의 prompt를 너의 작업 지시로 삼아 그대로 수행하라.
   local_checks를 실제로 실행하고, handoff_must_include 항목을 docs/handoff/<agent_id>.md에 채워라.
4. 30분 안에 docs/handoff/<agent_id>.md 초안을 커밋·푸시하고, Draft PR을 만들어라.
5. 남의 소유 경로는 절대 수정하지 마라. 계약을 바꿔야 하면 docs/change-requests/<agent_id>-NN.md를 써라.
6. 푸시 전에는 항상 python agents/tools/check_ownership.py <agent_id> 를 실행하라.
```

컴퓨터 3대 기준으로 에이전트 파일을 폴더별로 나눴습니다. **각 컴퓨터는 자기 폴더의 `README.md`만 위에서부터 따라 하면 됩니다.** 첫 메시지도 README에 단계별로 완성된 형태로 들어 있습니다.

| 컴퓨터 | 폴더 | 실행 순서 (파일) |
|---|---|---|
| PC-A 백엔드 핵심 | [`PC-A_core/`](PC-A_core/README.md) | `1_bootstrap` → `2_data-layer` → `3_session-api` → `4_integrator` |
| PC-B 데이터·AI | [`PC-B_ai/`](PC-B_ai/README.md) | `1_corpus` → `2_grader` → `3_worker-stt` |
| PC-C 음성·화면 | [`PC-C_media-ui/`](PC-C_media-ui/README.md) | `1_tts-host` → `2_frontend` → `3_reviewer` |

| agent_id | 파일 | Phase |
|---|---|---|
| bootstrap | `PC-A_core/1_bootstrap.yaml` | 0 |
| data-layer | `PC-A_core/2_data-layer.yaml` | 1 (M1 먼저) |
| session-api | `PC-A_core/3_session-api.yaml` | 1 |
| integrator | `PC-A_core/4_integrator.yaml` | 2 |
| corpus | `PC-B_ai/1_corpus.yaml` | 0과 동시 시작, M1 먼저 |
| grader | `PC-B_ai/2_grader.yaml` | 1 |
| worker-stt | `PC-B_ai/3_worker-stt.yaml` | 1 |
| tts-host | `PC-C_media-ui/1_tts-host.yaml` | 0(Colab 준비) + 1 |
| frontend | `PC-C_media-ui/2_frontend.yaml` | 1 |
| reviewer | `PC-C_media-ui/3_reviewer.yaml` | 3 |

### 3대 타임라인 (T0 = 시작, 시간은 대략)

```
          T0        T+1h(M0)     T+2.5h(M1)            T+6~7h(M2)     T+8h(M3)   T+9h(M4)
PC-A  [bootstrap]──[data-layer M1]──[data-layer M2][session-api]────[integrator]
PC-B  [corpus M1 ]──[corpus M2   ]──[grader              ][worker-stt]  (대기·버그 수정 지원)
PC-C  (Colab 준비)──[tts-host                  ][frontend              ]·········[reviewer]
```

- **PC-A가 임계 경로**입니다. 오케스트레이터는 PC-A 앞에 있는 것이 가장 효율적입니다.
- M2 병합 순서(1.4절)는 컴퓨터와 상관없이 그대로 지킵니다.

---

## 3. 작업 중 Git 흐름

### 3.1 커밋과 푸시

```bash
git add <내 소유 파일들>                     # git add . 금지 (실수로 .env·data가 들어갈 수 있음)
git commit -m "[<agent_id>] <요약>" -m "AI-assisted (OpenAI Codex)" # 실제 사용 도구·제공자를 기록
python agents/tools/check_ownership.py <agent_id>
git push -u origin agent/<agent_id>         # 처음 한 번 -u, 이후 git push
```

- **작은 단위로 자주 푸시합니다.** 컴퓨터가 꺼져도 다른 컴퓨터가 이어받을 수 있게 하기 위해서입니다.
- 커밋 메시지는 `[agent_id]`로 시작합니다.

### 3.2 PR 수명 주기

```
작업 시작 30분 안   →  Draft PR 생성   "[<id>] WIP"
마일스톤 완료       →  Ready for review  "[<id>] M1 …" 또는 "[<id>] M2 …"
오케스트레이터 확인 →  Rebase and merge
(corpus·data-layer) →  M1 병합 후 같은 브랜치에서 계속 작업 → 새 Draft PR "[<id>] M2 WIP"
```

**PR 본문 템플릿**

```markdown
## [<agent_id>] <M1|M2> <요약>

- handoff: docs/handoff/<agent_id>.md
- contract_version: <작업 기준 버전>

### local_checks 결과
<명령과 출력 요약을 붙여넣기>

### 다른 에이전트에게 영향
- (없음 / CR-<id>-NN 참조)

### 체크
- [ ] check_ownership 통과
- [ ] .env·data·녹음 파일 없음
- [ ] 각 소스 첫 줄 AI-assisted 주석
```

라벨은 `agent:<id>`, `M1`/`M2`/`M3`/`M4`, `contract-change`를 씁니다. 오케스트레이터가 처음에 한 번 만들어 둡니다.

### 3.3 rebase (공지를 받으면 바로)

```bash
git fetch origin
git rebase origin/main
# 충돌이 나면 1.6절 규칙대로. 끝나면:
git push --force-with-lease          # 자기 브랜치에서만, --force는 금지
```

rebase 후에는 `contracts.yaml`의 `contract_version`과 `changelog`를 확인해 바뀐 계약이 있는지 봅니다. 바뀌었으면 내 코드를 새 계약에 맞춥니다.

### 3.4 다른 모듈이 아직 없을 때

`orchestration.yaml` → `communication.stub_policy`를 따릅니다.

- 아직 병합되지 않은 다른 모듈은 `backend/tests_local/<agent_id>_fakes.py` 또는 `frontend/src/__dev__/`에 가짜 구현을 두고 테스트합니다. 이 두 폴더는 `.gitignore`로 커밋되지 않습니다.
- M1 이후에는 data-layer의 테스트 데이터 함수(`app.db.dev`)로 앞 단계를 건너뜁니다.

```bash
python -m app.db.dev seed-grading --level IM2   # 채점 대기 세션을 바로 만듦 (grader용)
```

---

## 4. 소통 규칙

| 무엇을 | 어디에 | 누가 |
|---|---|---|
| 진행 상황, 실행 방법, 측정값, 알려진 문제 | `docs/handoff/<agent_id>.md` | 각자 자기 파일만 |
| 계약 변경 요청 | `docs/change-requests/<agent_id>-NN.md` + PR 라벨 `contract-change` | 요청자 |
| 계약 변경 반영 | `agents/contracts.yaml` (version+1, changelog) | 오케스트레이터만 |
| 마일스톤·rebase 공지 | 팀 메신저 + 해당 PR 코멘트 | 오케스트레이터 |
| 30분 이상 막힘 | handoff의 "알려진 문제" + 메신저로 오케스트레이터 호출 | 막힌 사람 |

**오케스트레이터 공지 문구 (복사용)**

```text
[M0] bootstrap 병합 완료(main <sha>). 각 컴퓨터는 2.2절대로 agent/<id> 브랜치를 만들고 시작하세요.
[M1] corpus·data-layer M1 병합 완료(main <sha>). 전원 git fetch && git rebase origin/main 후 db_reset·ingest_rag 실행.
[CR] contract v<N> 반영(<CR 번호>: <한 줄 요약>). 영향: <에이전트들>. 전원 rebase.
[M2] <agent> 병합 완료. 다음 차례 <agent>: rebase 후 PR에 "ready" 코멘트 주세요.
```

### change request 처리 흐름

```
에이전트: docs/change-requests/grader-01.md 작성 → 자기 브랜치에 커밋·푸시, 메신저로 알림
          (승인 전까지는 현재 계약대로 구현, 우회한 곳에 "# CR-grader-01" 주석)
오케스트레이터: 승인 → git switch -c orchestrator/cr-grader-01 origin/main
          → contracts.yaml 수정, contract_version+1, changelog 추가 → PR → Rebase and merge → [CR] 공지
영향 받는 에이전트: rebase → 새 계약에 맞게 수정
```

---

## 5. 중간에 컴퓨터를 바꾸거나 다른 사람이 이어받을 때

```bash
git fetch origin
git switch agent/<agent_id>              # 원격 브랜치를 그대로 가져옴
git log --oneline -10                    # 어디까지 했는지 확인
```

1. `docs/handoff/<agent_id>.md`의 "상태"와 "알려진 문제"를 읽습니다.
2. 에이전트에게 2.4절 첫 메시지에 다음 한 줄을 추가해 보냅니다.
   > "이전 작업자의 handoff를 먼저 읽고, 완료된 항목은 다시 하지 말고 남은 항목부터 이어서 하라."
3. 이전 컴퓨터에 푸시하지 않은 커밋이 남아 있으면 먼저 그 컴퓨터에서 `git push`합니다. 그게 불가능하면 handoff에 "미푸시 작업 유실"을 기록합니다.

---

## 6. 하면 안 되는 것

- `main`에 직접 push, `git push --force`
- 다른 에이전트 브랜치에 push, 남의 소유 경로 수정
- Squash merge, Merge commit (rebase merge만)
- `.env`, `data/`, 녹음 파일, Whisper 모델 파일 커밋
- `git add .` / `git add -A`
- 계약에 없는 기능 추가 (채팅, 실제 로그인, 페르소나, 배포 등)
- 시험 중 평가 LLM 호출, STT 저장 전 다음 문항 이동, TTS 실패 시 Web Speech·텍스트 대체

---

## 7. 최종 완료 기준

`orchestration.yaml` → `definition_of_done` 전부 충족 + `docs/REVIEW.md`에 🔴 0건이면 MVP 완료입니다.

| 확인 | 담당 |
|---|---|
| RUNBOOK대로 새 컴퓨터에서 서비스가 뜸 | integrator |
| 실제 마이크로 8문항 완주 → 결과 확인 | integrator |
| 자동 완주 테스트 `e2e_smoke` 통과 (IM2·IL 세트) | integrator |
| 실패 시나리오 표 전부 통과 | integrator |
| 평가 리포트(±1등급 일치율, 반복 변동) 존재 | grader |
| 독립 검토 🔴 0건 | reviewer |
