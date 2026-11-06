# PC-C · 음성·화면 (tts-host → frontend → reviewer)

> 진행자 음성(OmniVoice·Colab)과 캐릭터, 사용자 화면 전체, 마지막 독립 검토를 맡습니다.
> **마이크와 브라우저가 있는 컴퓨터, Google 계정(Colab)**이 필요합니다. API 키는 reviewer 단계 외에는 필요 없습니다.
> 공통 규칙은 [`../HANDOFF.md`](../HANDOFF.md), 계약은 [`../contracts.yaml`](../contracts.yaml)에 있습니다.
>
> AI-assisted: this guide was written with help from Claude (Anthropic).

| 순서 | 에이전트 | 파일 | 시작 조건 | 예상 |
|---|---|---|---|---|
| 0 | (사람) Colab 준비 | — | T0 | 30분 |
| 1 | tts-host | `1_tts-host.yaml` | M0 병합 직후 | 2~3시간 |
| 2 | frontend | `2_frontend.yaml` | tts-host 코드 PR 올린 뒤 | 3~4시간 |
| 3 | reviewer | `3_reviewer.yaml` | M3(통합 완료) 공지 후 | 1시간 |

필요한 것: Python 3.11+, Node 20+, 마이크, Google 계정, Docker Desktop(tts-host 준비 핸들러 확인·reviewer)

---

## 0. 준비 (한 번)

```bash
git clone https://github.com/fruit8067/OpicTutor-With-AI
cd OpicTutor-With-AI
git config user.name  "곽윤직 (PC-C)"
git config pull.rebase true
git config rebase.autoStash true
```

### Colab 준비 (T0, 사람이 직접 — 저장소는 수정하지 않음)

bootstrap(M0)을 기다리는 동안 진행자 목소리를 미리 정해 둡니다.

1. [colab.research.google.com](https://colab.research.google.com) → **파일 → 노트 업로드** → `colab/omnivoice_tts.ipynb`
2. **런타임 → 런타임 유형 변경 → T4 GPU**
3. 셀 1·2·3·5·6만 실행합니다. `jobs.jsonl` 업로드(4번 셀)는 건너뜁니다.
4. 6번 셀의 기준 음성을 들어 보고, 마음에 들 때까지 3번 셀의 `SEED`·`INSTRUCT`를 바꿔 다시 실행합니다.
5. 7번 셀로 `host_voice.pt`를 만들고 내려받아 **로컬에 보관**합니다(아직 커밋하지 않음).
6. 정한 `INSTRUCT`, `SEED`, `SPEED` 값을 메모해 둡니다. tts-host 에이전트에게 알려 줄 값입니다.

---

## 1단계 · tts-host (M0 직후)

```bash
git fetch origin
git switch -c agent/tts-host origin/main
cd frontend && npm install && cd ..
```

**음성 생성은 두 번 합니다.**
- **1차 (corpus M1 이후):** pilot 문항 + Q000 + 진행자 대사로 파이프라인을 검증합니다.
- **2차 (corpus M2 이후):** 늘어난 pilot 문항(최대 Q187)을 `--stale`로 추가 생성합니다.

그래서 **코드 PR과 음성 PR을 나눠도 됩니다.** 코드 PR을 먼저 올리고 frontend로 넘어간 뒤, corpus M2가 병합되면 tts-host 브랜치로 돌아와 음성만 추가합니다.

**에이전트 첫 메시지** (새 대화)

```text
너는 OpicTutor 프로젝트의 tts-host 에이전트다. 지금 브랜치는 agent/tts-host이고 이 컴퓨터는 PC-C다.
진행자 음성은 운영자가 Google Colab에서 OmniVoice로 미리 만들어 반입하고, 서버는 세션의 8문항+대사 음성이 정확히 준비됐는지
검사·연결한다(tts_prepare). TTS와 캐릭터는 필수이며 Web Speech·텍스트 대체 경로를 만들지 않는다.
사람이 Colab에서 정한 기준 음성 설정: INSTRUCT="<메모한 값>", SEED=<값>, SPEED=<값>. host_voice.pt는 로컬에 있다.

1. agents/HANDOFF.md, agents/orchestration.yaml, agents/contracts.yaml, docs/handoff/corpus.md를 읽어라.
2. orchestration.yaml의 shared_preamble을 모든 작업의 규칙으로 삼아라.
3. agents/PC-C_media-ui/1_tts-host.yaml의 prompt를 작업 지시로 삼아 수행하라.
   노트북 실행·zip 내려받기는 사람이 한다. 너는 jobs.jsonl을 만들고, 노트북을 고치고, 사람에게 실행 순서를 안내하고,
   받은 zip을 import_tts로 반입·검증하라.
4. 코드(export·import·prepare 핸들러·Host·useTtsPlayer·노트북)가 끝나면 PR "[tts-host] M2 code"를 먼저 올려라.
   corpus M2 병합 후 --stale로 추가 음성을 반입하는 PR "[tts-host] M2 audio"를 따로 올린다.
5. 푸시 전에는 항상 python agents/tools/check_ownership.py tts-host 를 실행하라.
6. docs/handoff/tts-host.md에 voice_id, 생성 개수·용량, 운영자용 재생성 절차, Host 사용 예시를 적어라.
```

---

## 2단계 · frontend (tts-host 코드 PR 올린 뒤)

서버가 없어도 mock으로 개발합니다. tts-host의 `Host`·`useTtsPlayer`가 아직 병합 전이면 bootstrap stub을 씁니다.

```bash
git fetch origin
git switch -c agent/frontend origin/main
cd frontend && npm install
```

**에이전트 첫 메시지** (새 대화)

```text
너는 OpicTutor 프로젝트의 frontend 에이전트다. 지금 브랜치는 agent/frontend이고 이 컴퓨터는 PC-C다.
더미 로그인 → 설정 → 준비 → 시험 → 채점 중 → 결과 화면 전부를 만든다. 서버 상태가 진실이며,
업로드가 202로 접수돼도 답변이 done이고 current_order_no가 바뀐 것을 확인하기 전에는 다음 문항으로 가지 않는다.
결과 화면은 contracts v3 기준(base_level·estimated_level, IM 잠정 진단 라벨, 전사 기반 추정 안내, 자기소개 채점 제외 표시,
숫자 점수 없는 FACT 서술 진단, 관찰 범위·추가 확인 과제, 세분화 보류 화면)이다.

1. agents/HANDOFF.md, agents/orchestration.yaml, agents/contracts.yaml(contract_version 3 이상), docs/handoff/tts-host.md를 읽어라.
2. orchestration.yaml의 shared_preamble을 모든 작업의 규칙으로 삼아라.
3. agents/PC-C_media-ui/2_frontend.yaml의 prompt를 작업 지시로 삼아 그대로 수행하라.
   frontend/src/features/host/ 와 frontend/src/api/types.ts 는 수정하지 마라(다른 에이전트 소유).
4. mock 서버(frontend/src/__dev__/)는 커밋하지 마라.
5. 푸시 전에는 항상 python agents/tools/check_ownership.py frontend 를 실행하라.
6. docs/handoff/frontend.md에 화면별 호출 API, mock 사용법, 디자인 방향 두 줄을 적어라.
```

**frontend 진행 중에 corpus M2가 병합되면:** 대화를 잠시 멈추고 tts-host 음성 2차 작업을 별도 폴더에서 합니다.

```bash
git worktree add ../opic-tts-host agent/tts-host
cd ../opic-tts-host && git rebase origin/main
# 새 대화에서 tts-host 에이전트에게: "corpus M2가 병합됐다. --stale로 추가 음성을 만들고 반입해 'M2 audio' PR을 올려라"
```

---

## 3단계 · reviewer (M3 공지 후)

**reviewer는 반드시 새 대화로 시작합니다.** 같은 컴퓨터에서 frontend를 만들었더라도, 코드를 작성한 대화의 맥락이 섞이면 독립 검토가 되지 않습니다.

```bash
git fetch origin
git switch -c agent/reviewer origin/main
cp backend/.env.example backend/.env       # RUNBOOK대로 서비스를 띄우기 위해 키 입력
```

**에이전트 첫 메시지** (새 대화)

```text
너는 OpicTutor 프로젝트의 reviewer 에이전트다. 지금 브랜치는 agent/reviewer이고 이 컴퓨터는 PC-C다.
너는 이 코드를 작성하지 않은 독립 검토자다. 코드를 고치지 말고 docs/REVIEW.md에 발견 사항만 적는다.

1. agents/HANDOFF.md, agents/orchestration.yaml, agents/contracts.yaml, docs/RUNBOOK.md, docs/handoff/*.md를 읽어라.
2. orchestration.yaml의 shared_preamble을 모든 작업의 규칙으로 삼아라.
3. agents/PC-C_media-ui/3_reviewer.yaml의 prompt를 작업 지시로 삼아 그대로 수행하라.
   RUNBOOK대로 직접 서비스를 띄우고 불변 조건을 하나씩 재현해 확인하라.
4. 완료되면 PR "[reviewer] M4 REVIEW"를 올려라.
```

**끝나면** 🔴가 0건이면 MVP 완료입니다. 🔴가 있으면 오케스트레이터가 담당 컴퓨터에 수정 브랜치를 배정합니다.
