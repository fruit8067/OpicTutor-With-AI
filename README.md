<div align="center">

# OpicTutor

**OPIc 영어 말하기 시험을 실제 시험처럼 치르고 AI 예상 등급과 개선 피드백을 받는 웹 모의고사**

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-4169E1?logo=postgresql&logoColor=white)
![Status](https://img.shields.io/badge/status-MVP%20in%20progress-orange)

[개요](#개요) · [주요 기능](#주요-기능) · [아키텍처](#아키텍처) · [시작하기](#시작하기) · [API](#api) · [개발 참여](#개발-참여) · [로드맵](#로드맵)

</div>

---

> [!IMPORTANT]
> OpicTutor가 제시하는 등급은 **참고용 예상 등급**이며 공식 OPIc 성적이 아닙니다.
> 평가는 STT 전사문과 관측 지표를 기반으로 하므로 발음·억양은 평가하지 않습니다.

## 목차

- [개요](#개요)
- [주요 기능](#주요-기능)
- [아키텍처](#아키텍처)
- [기술 스택](#기술-스택)
- [시작하기](#시작하기)
  - [사전 요구사항](#사전-요구사항)
  - [설치](#설치)
  - [환경 변수](#환경-변수)
  - [실행](#실행)
- [사용 흐름](#사용-흐름)
- [API](#api)
- [프로젝트 구조](#프로젝트-구조)
- [테스트](#테스트)
- [개발 참여](#개발-참여)
- [로드맵](#로드맵)
- [문서](#문서)
- [라이선스](#라이선스)

## 개요

OPIc은 말하기 시험이라 수험생이 자신의 답변 수준을 객관적으로 확인하기 어렵습니다.
OpicTutor는 **설정 → 문제 세트 준비 → 진행자 음성 → 녹음 답변 → 시험 종료 후 종합 평가 → 결과** 흐름으로
실제 시험에 가까운 8문항 모의고사를 제공합니다.

- **시험 중에는** 로컬 STT(faster-whisper)만 실행합니다. 지연이 적고 외부로 음성을 보내지 않습니다.
- **시험이 끝난 뒤에** 전체 문항·답변·지표를 한 번에 LLM에 전달해 예상 등급과 피드백을 생성합니다.
- 진행자 음성은 OmniVoice로 **미리 생성한 파일**을 사용합니다. 시험 중 TTS API를 호출하지 않습니다.

대상 환경은 한국어 UI의 데스크톱 웹이며, localhost에서 실행하는 MVP입니다.

## 주요 기능

| 기능 | 설명 |
| --- | --- |
| 모의고사 구성 | 시나리오(기본·여가·운동/건강)를 고르면 서버가 8문항 세트와 순서를 한 번에 확정합니다. 자기소개 1문항은 채점에서 제외합니다. |
| 진행자 캐릭터 | 사전 생성한 문항 음성을 재생하고, Web Audio 음량에 맞춰 캐릭터가 말하기·듣기 상태로 움직입니다. |
| 녹음·STT | 버튼으로 녹음을 시작·종료합니다. 원음을 저장한 뒤 워커가 전사하고 문항에 연결합니다. 다시 듣기는 1회입니다. |
| 종합 평가 | 사용자 제공 Performance Feedback 표, ACTFL 2024 Speaking 보강, 내부 IM 세분화 기준(`project-im-v1`)으로 평가합니다. |
| 결과 리포트 | 예상 등급(NL–AL, IM은 IM1–IM3 잠정 진단), 실제 답변 인용 근거, FACT 진단, 개선 카드, 문항별 수정안을 보여 줍니다. |
| 복구 | 준비·STT·평가 실패 시 같은 세트와 저장된 답변으로 재시도합니다. 새로고침해도 진행 상태를 이어 갑니다. |

## 아키텍처

```mermaid
flowchart LR
    subgraph Browser["브라우저 (React)"]
        UI[설정 · 시험 · 결과]
        Host[진행자 캐릭터<br/>Web Audio]
        Rec[MediaRecorder]
    end

    subgraph Backend["백엔드 (FastAPI)"]
        API["/api/v1"]
        Static["/media/tts"]
    end

    subgraph Worker["워커 (python -m app.worker)"]
        Prep[tts_prepare]
        STT[stt<br/>faster-whisper]
        Eval[evaluate<br/>LLM 채점]
    end

    DB[(PostgreSQL<br/>+ pgvector)]
    Files[(data/audio<br/>static/tts)]
    LLM[[OpenAI 호환 LLM]]
    Colab[[Colab · OmniVoice<br/>음성 사전 생성]]

    UI -->|REST · 2초 폴링| API
    Rec -->|multipart 업로드| API
    Host -->|mp3| Static
    API --> DB
    API --> Files
    Worker -->|작업 큐 · 상태| DB
    STT --> Files
    Eval --> LLM
    Colab -.->|import_tts| Files
```

- **긴 작업은 비동기**입니다. API는 TTS 준비·STT·평가를 `202 Accepted`로 접수하고, 워커가 DB 작업 상태를 갱신하며, 클라이언트는 상태를 폴링합니다.
- **모든 쓰기 요청은 멱등**입니다(`client_request_id` 또는 상태 기반). 재시도·중복 클릭으로 세션·답변·평가가 중복 생성되지 않습니다.
- **평가 기준은 시스템 프롬프트에 고정**됩니다([`docs/prompts/opic_evaluation_system.md`](docs/prompts/opic_evaluation_system.md)). RAG는 문항별 대조 답변 검색만 보조합니다.

## 기술 스택

| 영역 | 기술 |
| --- | --- |
| Frontend | React 19, Vite, TypeScript, React Router 7, Tailwind CSS, oxlint |
| 브라우저 오디오 | MediaRecorder, HTMLAudioElement, Web Audio API (AnalyserNode) |
| Backend | Python 3.11+, FastAPI, Pydantic v2 |
| Worker | DB 기반 작업 큐 (`tts_prepare`, `stt`, `evaluate`) |
| Database | PostgreSQL 16 + pgvector (Docker) |
| STT | faster-whisper `small.en` (CPU int8 / CUDA float16) |
| TTS | OmniVoice, Google Colab에서 사전 생성 후 로컬 반입 |
| LLM | OpenAI SDK 호환 API (구조화 출력) |
| Embedding | `text-embedding-3-large` (3072차원) |

## 시작하기

### 사전 요구사항

- Python **3.11+**
- Node.js **20+**
- Docker Desktop (실행 중)
- 마이크가 있는 데스크톱 환경
- OpenAI 호환 LLM API 키, 임베딩용 API 키

### 설치

```bash
git clone https://github.com/fruit8067/OpicTutor-With-AI.git
cd OpicTutor-With-AI

# 1) DB
docker compose up -d

# 2) Backend
python -m venv backend/.venv
source backend/.venv/bin/activate          # Windows: backend\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt

# 3) Frontend
cd frontend && npm ci && cd ..
```

### 환경 변수

```bash
cp backend/.env.example backend/.env       # 처음 한 번만. 기존 파일을 덮어쓰지 마세요.
```

`backend/.env`에서 아래 값을 채웁니다. 전체 목록과 기본값은 [`backend/.env.example`](backend/.env.example)에 있습니다.

| 변수 | 설명 | 기본값 |
| --- | --- | --- |
| `DATABASE_URL` | PostgreSQL 연결 문자열 | `postgresql://opic:opic@127.0.0.1:5432/opic` |
| `LLM_BASE_URL` / `LLM_MODEL` | 평가용 OpenAI 호환 API | `https://llm.pcl.kr/v1` / `pickle-general` |
| `LLM_API_KEY` | 평가 LLM 키 (비어 있으면 `PICKLE_API_KEY` 사용) | — |
| `EMBED_BASE_URL` / `EMBED_MODEL` / `EMBED_API_KEY` | RAG 임베딩 설정 | OpenAI / `text-embedding-3-large` |
| `WHISPER_MODEL` / `WHISPER_DEVICE` | STT 모델과 장치 | `small.en` / `cpu` |
| `DATA_DIR`, `TTS_DIR`, `RAG_BUILD_DIR` | 파일 경로. **`backend/` 기준 상대 경로만** 허용 | `../data`, `static/tts`, `../rag_docs/build` |

> [!WARNING]
> API 키, `backend/.env`, `data/`(녹음 원음)는 절대 커밋하지 마세요. DB와 API는 `127.0.0.1`에만 바인딩됩니다.

### 실행

**1. 데이터 준비** (`backend/`에서, 처음 한 번)

```bash
cd backend
python -m scripts.db_reset --yes                              # 새 개발 DB에서만. 기존 데이터가 삭제됩니다.
python -m scripts.ingest_rag --dry-run && python -m scripts.ingest_rag
python -m scripts.import_tts static/tts/ac3049e033 --activate # 저장소에 포함된 진행자 음성을 DB에 등록
```

**2. 서비스 실행** (터미널 3개)

```bash
# Terminal 1 — API
cd backend && uvicorn app.main:app --host 127.0.0.1 --port 8000

# Terminal 2 — Worker
cd backend && python -m app.worker

# Terminal 3 — Frontend
cd frontend && npm run dev -- --host 127.0.0.1
```

브라우저에서 <http://127.0.0.1:5173>을 엽니다. 마이크 권한을 허용해야 시험을 시작할 수 있습니다.

> [!NOTE]
> 현재 M2 기능 브랜치가 순서대로 병합되는 중입니다. `import_tts`와 워커 명령은 tts-host·worker-stt PR이 `main`에 병합된 뒤 사용할 수 있습니다.
> 단계별 상세 절차와 Windows PowerShell 명령은 [`docs/RUNBOOK.md`](docs/RUNBOOK.md)를 참고하세요.

## 사용 흐름

1. **설정** — 마이크를 테스트하고 시나리오를 선택합니다.
2. **준비** — 서버가 8문항 세트를 확정하고 모든 문항 음성이 있는지 확인합니다.
3. **시험** — 진행자가 문항을 읽으면 녹음 버튼으로 답합니다. STT 저장이 끝나야 다음 문항으로 넘어갑니다.
4. **채점** — 마지막 답변이 저장되면 시험이 종료되고 전체 답변을 한 번에 평가합니다.
5. **결과** — 예상 등급, 근거 인용, 개선 카드, 문항별 피드백을 확인합니다.

자세한 상태 전이는 [`docs/FLOWCHART.md`](docs/FLOWCHART.md)를 참고하세요.

## API

Base URL: `http://127.0.0.1:8000/api/v1` · 단일 기준: [`agents/contracts.yaml`](agents/contracts.yaml) §8

| Method | Path | 설명 |
| --- | --- | --- |
| `GET` | `/health` | 서비스 상태 |
| `GET` | `/scenarios` | 선택 가능한 시나리오 |
| `GET` | `/host-lines` | 진행자 대사 음성 URL |
| `POST` | `/sessions` | 세션 생성 및 문제 세트 준비 (`202`) |
| `GET` | `/sessions/{id}` | 세션 상태 조회 |
| `POST` | `/sessions/{id}/prepare/retry` | 준비 재시도 (`202`) |
| `POST` | `/sessions/{id}/start` | 시험 시작 |
| `POST` | `/sessions/{id}/cancel` | 세션 취소 |
| `GET` | `/sessions/{id}/current` | 현재 문항 |
| `POST` | `/sessions/{id}/questions/{order_no}/replay` | 다시 듣기 (1회) |
| `POST` | `/sessions/{id}/answers` | 녹음 업로드 (`202`, multipart) |
| `GET` | `/sessions/{id}/answers/{answer_id}` | 답변·STT 상태 |
| `POST` | `/sessions/{id}/answers/{answer_id}/retry-stt` | STT 재처리 (`202`) |
| `POST` | `/sessions/{id}/submit` | 시험 종료 및 평가 요청 (`202`) |
| `GET` | `/sessions/{id}/result` | 저장된 결과 (LLM을 호출하지 않음) |
| `POST` | `/sessions/{id}/regrade` | 재평가 (`202`) |

오류 응답 형식:

```json
{ "error": { "code": "ORDER_MISMATCH", "message": "현재 문항이 아니에요. 화면을 새로고침해 주세요.", "detail": {} } }
```

정적 음성 파일은 `/media/tts/**`로 제공됩니다.

## 프로젝트 구조

```text
OpicTutor-With-AI/
├── agents/              # 멀티 에이전트 계약(contracts.yaml)·오케스트레이션·PC별 프롬프트
├── backend/
│   ├── app/
│   │   ├── api/         # FastAPI 라우트
│   │   ├── exam/        # 세션·출제 로직
│   │   ├── db/          # DB 접근 계층
│   │   ├── worker/      # 작업 큐 러너
│   │   ├── stt/         # faster-whisper 전사·지표
│   │   ├── tts/         # 음성 자산 조회·준비 검증
│   │   ├── grading/     # 평가 입력 구성·출력 검증
│   │   ├── llm/         # LLM·임베딩 클라이언트
│   │   └── schemas/     # API·DB 스키마
│   ├── migrations/      # SQL 마이그레이션
│   ├── scripts/         # db_reset, ingest_rag, import_tts, export_tts_jobs …
│   ├── static/tts/      # 사전 생성된 진행자 음성
│   └── tests/           # pytest
├── colab/               # OmniVoice TTS 생성 노트북
├── docs/                # 요구사항·플로차트·API·평가 프롬프트·인수인계·변경 요청
├── frontend/            # React 앱
├── rag_docs/            # 문항·대조 답변 코퍼스 원본과 빌드 결과
└── docker-compose.yml   # PostgreSQL + pgvector
```

## 테스트

```bash
# Backend (DB가 실행 중이어야 하는 테스트 포함)
cd backend && python -m pytest -q

# Corpus 빌드·회귀 검사
cd rag_docs && python scripts/build_corpus.py && python scripts/check_monotonic.py

# Frontend
cd frontend && npm run lint && npm run build
```

## 개발 참여

이 저장소는 **계약 기반 멀티 에이전트 워크플로**로 개발합니다.

- **단일 기준**: 모듈 경계·API·DB·파일 형식은 [`agents/contracts.yaml`](agents/contracts.yaml)이 정합니다. 계약 변경은 `docs/change-requests/`에 변경 요청(CR)을 올리고 오케스트레이터 승인을 받습니다.
- **소유권**: 각 경로에는 담당 에이전트가 있으며 소유자만 수정합니다. PR 전에 검사하세요.
  ```bash
  python agents/tools/check_ownership.py <agent_id>
  ```
- **브랜치**: `agent/<agent_id>` 브랜치에서 작업하고 `main`에 대한 PR을 엽니다. 병합은 오케스트레이터만 **Rebase and merge**로 수행합니다.
- **병합 순서**: `corpus → data-layer → tts-host → worker-stt → session-api → grader → frontend`
- **인수인계**: 작업 결과와 검증 내역은 `docs/handoff/<agent_id>.md`에 남깁니다.
- **금지 사항**: `git push --force`(필요하면 `--force-with-lease`), 키·`.env`·`data/`·녹음 파일 커밋.
- **AI 사용 표기**: AI 도움을 받은 파일과 커밋에는 그 사실을 표기합니다.

## 로드맵

- [x] **M0** 골격·계약·스키마
- [x] **M1** DB·코퍼스 파일럿·세션 API·STT·채점 기초
- [ ] **M2** 코퍼스 확장(238문항), 진행자 음성, 프론트엔드, 실제 평가 검증 — *진행 중*
- [ ] **M3** 전체 흐름 통합 실행(E2E)과 독립 리뷰
- [ ] **이후** AI 후속 채팅, 진행자 페르소나, 한 문항 연습 모드, 실제 회원·기록 관리

## 문서

| 문서 | 내용 |
| --- | --- |
| [PROJECT_REQUIREMENTS.md](PROJECT_REQUIREMENTS.md) | 요구사항 요약 |
| [docs/REQUIREMENTS_v2.md](docs/REQUIREMENTS_v2.md) | 상세 요구사항 (우선 기준) |
| [docs/FLOWCHART.md](docs/FLOWCHART.md) | 사용자 흐름·상태 전이 |
| [docs/API_SPEC.md](docs/API_SPEC.md) | API 명세 |
| [docs/OPIC_SCORING_RESEARCH.md](docs/OPIC_SCORING_RESEARCH.md) | 평가 기준 조사 |
| [docs/prompts/opic_evaluation_system.md](docs/prompts/opic_evaluation_system.md) | 평가 시스템 프롬프트 |
| [rag_docs/README.md](rag_docs/README.md) | 코퍼스 구성과 빌드 |

## 라이선스

[GNU General Public License v3.0](LICENSE)

연습 문항과 대조 답변은 교육용으로 작성한 자료이며 실제 기출 원문이나 공식 채점 답안이 아닙니다.
OPIc은 해당 권리자의 상표이며, 이 프로젝트는 시험 주관사와 관련이 없습니다.
