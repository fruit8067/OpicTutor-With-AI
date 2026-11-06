# OpicTutor — API 명세 v1

> **병합 상태: 이전 API 계약 초안.** 최신 기준은 `REQUIREMENTS_v2.md`와 `FLOWCHART.md`이며, 상세 요구사항 8장의 동기화가 필요합니다. 문항별 실시간 평가·코드 등급 산출·STT 대기 없는 이동 규칙은 더 이상 현재 요구사항이 아닙니다.
> 기준 문서: `docs/REQUIREMENTS_v2.md`
> FastAPI가 이 명세의 Pydantic 모델로 `/docs`(Swagger)와 `/openapi.json`을 자동 생성합니다. **최신 요구사항에 맞게 이 API 초안을 갱신한 뒤 구현 계약으로 사용합니다.**
>
> AI-assisted: 이 명세는 Claude(Anthropic)의 도움으로 작성했습니다.

---

## 1. 공통 규칙

| 항목 | 값 |
|---|---|
| Base URL | `http://127.0.0.1:8000/api/v1` |
| 정적 파일 | `http://127.0.0.1:8000/static/...` (`/api/v1` 밖) |
| 인증 | 없음. `session_id`(UUID v4)로 시험을 구분합니다 |
| 요청/응답 형식 | `application/json; charset=utf-8` (답변 업로드만 `multipart/form-data`) |
| 시간 형식 | ISO 8601 UTC (`2026-11-06T05:13:00Z`) |
| 필드 표기 | `snake_case` |
| CORS 허용 | `http://localhost:5173`, `http://127.0.0.1:5173` (Vite 개발 서버) |
| 서버 바인딩 | `127.0.0.1` 전용 |

### 1.1 비동기 처리 원칙

시간이 걸리는 작업(STT, 평가, 피드백 생성)은 **`202 Accepted`를 바로 돌려주고 백그라운드에서 처리**합니다.
클라이언트는 `GET /sessions/{id}/result`를 **2초 간격으로 폴링**해서 진행 상태를 확인합니다.

### 1.2 에러 응답 형식

모든 4xx/5xx 응답은 아래 형식을 따릅니다.

```json
{
  "error": {
    "code": "AUDIO_TOO_SHORT",
    "message": "녹음이 너무 짧습니다. 다시 답변해 주세요.",
    "detail": { "duration_ms": 1200, "min_ms": 2000 }
  }
}
```

- `code`: 프론트엔드가 분기할 때 쓰는 고정 문자열입니다(전체 목록은 §5).
- `message`: 사용자에게 그대로 보여 줄 수 있는 한국어 문장입니다.
- `detail`: 디버깅용 추가 정보이며 생략될 수 있습니다.

---

## 2. 상태 값 (Enum)

### 2.1 `SessionStatus` — 시험 상태

```
in_progress ──finish──▶ grading ──▶ done
                           │
                           └──▶ failed ──regrade──▶ grading
```

| 값 | 의미 |
|---|---|
| `in_progress` | 시험 진행 중. 답변 업로드 가능 |
| `grading` | 시험 종료. 남은 STT·평가·피드백 생성 중 |
| `done` | 결과 생성 완료 |
| `failed` | 평가 가능한 문항이 4개 미만이어서 결과를 만들지 못함. `regrade` 가능 |

### 2.2 `SttStatus` / `EvalStatus` — 문항 처리 상태

| `stt_status` | 의미 |
|---|---|
| `pending` | 업로드 완료, STT 대기·처리 중 |
| `done` | STT와 유창성 지표 계산 완료 |
| `empty` | STT 결과에 단어가 없음(무음). 해당 문항은 NL로 처리 |
| `failed` | STT 오류 |

| `eval_status` | 의미 |
|---|---|
| `pending` | 평가 대기·처리 중 (STT가 끝나면 자동 시작) |
| `done` | 문항 평가 완료 |
| `skipped` | 평가 생략 (`stt_status`가 `empty`이거나 답변을 업로드하지 않은 문항) |
| `failed` | LLM 재시도 2회 후에도 실패 |

### 2.3 `Level` / `Tier`

```
Level = "NL" | "NM" | "NH" | "IL" | "IM1" | "IM2" | "IM3" | "IH" | "AL"
rank  =   1     2      3     4      5       6       7      8     9
```

| `tier` | 등급 | `color` |
|---|---|---|
| `bronze` | NL, NM, NH | `#B0794A` |
| `silver` | IL, IM1 | `#A8B3BD` |
| `gold` | IM2, IM3 | `#E3B341` |
| `platinum` | IH | `#4FC3C7` |
| `diamond` | AL | `#7C8CFF` |

### 2.4 `QuestionType`

```
self_intro | description | routine | past_experience | comparison
| issue | roleplay_ask | roleplay_solve | roleplay_experience
```

---

## 3. 엔드포인트 요약

| # | Method | Path | 설명 | 성공 코드 |
|---|---|---|---|---|
| E1 | GET | `/health` | 서버·DB·Whisper 상태 | 200 |
| E2 | GET | `/meta/survey-options` | 배경 설문 선택지 (MVP는 UI 표시용) | 200 |
| E3 | POST | `/sessions` | 시험 생성 + 8문항 출제 | 201 |
| E4 | GET | `/sessions/{session_id}` | 시험 상태와 문항별 처리 상태 | 200 |
| E5 | POST | `/sessions/{session_id}/answers` | 답변 녹음 업로드 | 202 |
| E6 | GET | `/sessions/{session_id}/answers/{order_no}` | 문항 하나의 STT·지표·평가 상세 | 200 |
| E7 | POST | `/sessions/{session_id}/finish` | 시험 종료 → 채점 시작 | 202 |
| E8 | GET | `/sessions/{session_id}/result` | 채점 진행률 또는 최종 결과 (폴링) | 200 |
| E9 | POST | `/sessions/{session_id}/regrade` | 실패한 평가 다시 실행 | 202 |
| E10 | POST | `/sessions/{session_id}/chat` | AI 후속 채팅 (**나중에**) | 501 |
| S1 | GET | `/static/tts/questions/{question_id}.mp3` | 문항 음성 | 200 |
| S2 | GET | `/static/tts/host/{line_id}.mp3` | 진행자 대사 음성 | 200 |

---

## 4. 엔드포인트 상세

### E1. `GET /health`

서버를 시작한 뒤, 그리고 프론트엔드 랜딩 화면이 열릴 때 호출합니다. `ready`가 `false`면 [모의고사 시작] 버튼을 비활성화합니다.

**200**
```json
{
  "ready": true,
  "db": "ok",
  "whisper": { "loaded": true, "model": "small.en" },
  "rag_docs": 263,
  "tts_cached": true
}
```

- `ready = db == "ok" && whisper.loaded && rag_docs > 0`
- `tts_cached`가 `false`면 프론트엔드는 Web Speech API로 대신 읽습니다.

---

### E2. `GET /meta/survey-options`

**200**
```json
{
  "groups": [
    { "key": "residence", "label": "거주", "options": ["가족과 아파트", "혼자 아파트", "기숙사"] },
    { "key": "leisure",   "label": "여가", "options": ["공원 가기", "영화 보기", "카페 가기", "콘서트 보기"] },
    { "key": "exercise",  "label": "운동", "options": ["조깅/걷기", "헬스"] },
    { "key": "hobby",     "label": "취미", "options": ["음악 감상"] },
    { "key": "travel",    "label": "휴가", "options": ["국내 여행"] }
  ],
  "note": "MVP에서는 설문 결과가 출제에 반영되지 않습니다."
}
```

---

### E3. `POST /sessions`

시험을 만들고 문항 8개를 **한 번에** 뽑아 돌려줍니다.

**Request** (body 전체 생략 가능)
```json
{
  "survey": { "residence": ["가족과 아파트"], "leisure": ["영화 보기"] },
  "self_assessment": 4
}
```

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `survey` | `object<string, string[]>` | N | 배경 설문 선택 결과. MVP에서는 저장만 함 |
| `self_assessment` | `int (1~6)` | N | 자가 평가 단계. MVP에서는 저장만 함 |

**201**
```json
{
  "session_id": "8f0c2c1e-6c1a-4b5e-9f0a-2b7d1f3e4a10",
  "status": "in_progress",
  "created_at": "2026-11-06T05:13:00Z",
  "limits": {
    "min_record_ms": 2000,
    "max_record_ms": 120000,
    "replay_limit": 1,
    "idle_prompt_ms": 20000,
    "accepted_mime": ["audio/webm", "audio/ogg", "audio/wav"]
  },
  "questions": [
    {
      "order_no": 1,
      "question_id": "Q000",
      "question_type": "self_intro",
      "text": "Let's start the interview now. Tell me a little bit about yourself.",
      "difficulty": "1-6",
      "audio_url": "/static/tts/questions/Q000.mp3"
    },
    {
      "order_no": 2,
      "question_id": "Q001",
      "question_type": "description",
      "text": "Please describe the place where you live. ...",
      "difficulty": "3-6",
      "audio_url": "/static/tts/questions/Q001.mp3"
    }
  ]
}
```

- 출제 순서는 `self_intro → description → routine → past_experience → comparison → roleplay_ask → roleplay_solve → (issue | roleplay_experience)`로 고정입니다.
- `audio_url`은 mp3 캐시가 없으면 `null`입니다. 이때 프론트엔드는 Web Speech API로 `text`를 읽습니다.
- `replay_limit`(다시 듣기 1회)는 **프론트엔드에서만** 제한합니다. 서버는 다시 들었는지 기록하지 않습니다.

**에러:** `503 SERVICE_NOT_READY` (Whisper 모델이나 DB가 준비되지 않음)

---

### E4. `GET /sessions/{session_id}`

새로고침한 뒤 시험을 이어 가거나, 어느 문항까지 올렸는지 확인할 때 씁니다.

**200**
```json
{
  "session_id": "8f0c...4a10",
  "status": "in_progress",
  "created_at": "2026-11-06T05:13:00Z",
  "questions": [ /* E3와 같은 Question 배열 */ ],
  "answers": [
    { "order_no": 1, "uploaded": true,  "stt_status": "done",    "eval_status": "done" },
    { "order_no": 2, "uploaded": true,  "stt_status": "pending", "eval_status": "pending" },
    { "order_no": 3, "uploaded": false, "stt_status": null,      "eval_status": null }
  ],
  "next_order_no": 3
}
```

- `next_order_no`: 아직 업로드하지 않은 가장 앞 문항입니다. 다 올렸으면 `null`입니다.

**에러:** `404 SESSION_NOT_FOUND`

---

### E5. `POST /sessions/{session_id}/answers`

답변 녹음을 올립니다. **STT를 기다리지 않고 바로 `202`를 돌려줍니다.**

**Request** — `multipart/form-data`

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `order_no` | `int (1~8)` | Y | 문항 순서 |
| `audio` | file | Y | MediaRecorder 녹음 파일 (`audio/webm;codecs=opus` 권장), 최대 10MB |
| `duration_ms` | `int` | Y | 클라이언트가 잰 녹음 길이 |
| `client_rms_max` | `float (0~1)` | N | 녹음 중 최대 음량. 무음 판단 보조용 |

**202**
```json
{
  "answer_id": "c2b7...91fe",
  "order_no": 2,
  "stt_status": "pending",
  "replaced": false,
  "next_order_no": 3
}
```

- **같은 `order_no`로 다시 올리면 덮어씁니다** (`replaced: true`). 업로드 실패 후 다시 보내기와 재녹음 모두 이 방식으로 처리합니다. 이전 녹음 파일과 STT·평가 결과는 삭제됩니다.
- 서버 처리 순서: 파일 저장 → `202` 응답 → 백그라운드 STT + 지표 계산 → 문항 평가 자동 시작

**무음 처리 ("Could you say that again?") 책임 분담**

| 단계 | 판단 주체 | 기준 | 동작 |
|---|---|---|---|
| 업로드 전 | 프론트엔드 | `duration_ms < 2000` 또는 `client_rms_max < 0.02` | 업로드하지 않고 진행자 대사 `say_again` 재생 → 재녹음 |
| 업로드 시 | 서버 | `duration_ms < min_record_ms` | `422 AUDIO_TOO_SHORT` → 프론트엔드가 `say_again` 재생 |
| STT 후 | 서버 | 단어 0개 | `stt_status: "empty"`. 이미 다음 문항으로 넘어갔으므로 결과 화면에 "답변이 인식되지 않음"으로 표시 |

**에러**

| 코드 | HTTP | 조건 |
|---|---|---|
| `SESSION_NOT_FOUND` | 404 | |
| `SESSION_CLOSED` | 409 | `status`가 `in_progress`가 아님 |
| `INVALID_ORDER_NO` | 422 | 1~8 범위 밖 |
| `AUDIO_TOO_SHORT` | 422 | `duration_ms < 2000` |
| `AUDIO_TOO_LONG` | 422 | `duration_ms > 125000` (5초 여유) |
| `UNSUPPORTED_MEDIA` | 415 | `accepted_mime`에 없는 형식 |
| `PAYLOAD_TOO_LARGE` | 413 | 10MB 초과 |

---

### E6. `GET /sessions/{session_id}/answers/{order_no}`

결과 화면의 "문항별 펼쳐 보기"와 개발 중 디버깅에 씁니다.

**200**
```json
{
  "order_no": 2,
  "question": { /* Question */ },
  "stt_status": "done",
  "stt_text": "Um, I live in a, uh, apartment with my family. It is ...",
  "metrics": {
    "duration_sec": 48.2,
    "speech_sec": 41.0,
    "word_count": 86,
    "wpm": 125.9,
    "long_pause_count": 4,
    "filler_per100": 8.1,
    "repeat_per100": 2.3
  },
  "eval_status": "done",
  "eval": {
    "scores": { "task_completion": 3, "text_type": 3, "accuracy": 2, "fluency": 3 },
    "closest_level": "IM2",
    "item_rank": 5.8,
    "evidence": ["I live in a, uh, apartment with my family", "and then we usually ..."],
    "mistakes": [
      {
        "quote": "I live in a apartment",
        "problem": "모음으로 시작하는 단어 앞 관사 오류",
        "fix": "I live in an apartment"
      }
    ],
    "upgrade_tip": "방 하나를 골라 '왜 좋아하는지'를 because로 두 문장 이상 이어 말해 보세요.",
    "retrieved_contrast_set_id": "CS-Q001"
  }
}
```

- `stt_status`가 `pending`이면 `stt_text`, `metrics`, `eval`은 `null`입니다.
- `audio_path`(로컬 경로)는 **응답에 넣지 않습니다.** 녹음 다시 듣기는 MVP 범위 밖입니다.

**에러:** `404 SESSION_NOT_FOUND`, `404 ANSWER_NOT_FOUND`

---

### E7. `POST /sessions/{session_id}/finish`

시험을 끝내고 최종 채점을 시작합니다. 마지막 문항을 업로드한 직후 호출합니다.

**Request:** body 없음

**202**
```json
{ "session_id": "8f0c...4a10", "status": "grading", "uploaded_count": 8 }
```

- 서버 처리 순서: 남은 STT·문항 평가 완료 대기 → 등급 산출(코드) → 시험 단위 피드백 카드 생성(LLM 1회) → `done`
- 업로드하지 않은 문항은 `eval_status: "skipped"`로 처리합니다.
- **이미 `grading`이나 `done` 상태면 아무것도 하지 않고 현재 상태로 `202`를 돌려줍니다(멱등).** 버튼을 두 번 눌러도 안전합니다.

**에러**

| 코드 | HTTP | 조건 |
|---|---|---|
| `SESSION_NOT_FOUND` | 404 | |
| `NOT_ENOUGH_ANSWERS` | 422 | 업로드한 문항이 4개 미만. `detail.uploaded_count` 포함 |

---

### E8. `GET /sessions/{session_id}/result`

**2초 간격으로 폴링**합니다. `status`가 `done` 또는 `failed`가 되면 폴링을 멈춥니다.

**200 — 채점 중 (`grading`)**
```json
{
  "session_id": "8f0c...4a10",
  "status": "grading",
  "progress": {
    "stage": "item_eval",
    "stt_done": 8,
    "eval_done": 6,
    "total": 8,
    "percent": 70
  },
  "result": null
}
```

| `progress.stage` | 의미 | 화면 문구(안) |
|---|---|---|
| `stt` | 음성 인식 중 | "답변을 듣고 있어요" |
| `item_eval` | 문항 평가 중 | "문항별로 채점하고 있어요" |
| `scoring` | 등급 산출 중 | "등급을 계산하고 있어요" |
| `feedback` | 피드백 카드 생성 중 | "피드백을 정리하고 있어요" |

- `percent` = `(stt_done + eval_done) / (total × 2) × 80` + `scoring` 10 + `feedback` 10

**200 — 완료 (`done`)**
```json
{
  "session_id": "8f0c...4a10",
  "status": "done",
  "progress": null,
  "result": {
    "level": "IM2",
    "rank": 6,
    "rank_raw": 6.34,
    "tier": { "name": "gold", "color": "#E3B341" },
    "next": { "level": "IM3", "gap": 0.66, "message": "IM3까지 한 단계 남았어요" },
    "headline": "문장을 이어 말하는 힘은 충분해요. 과거 시제만 잡으면 IM3가 보여요.",
    "scores": {
      "task_completion": 3.4,
      "text_type": 3.1,
      "accuracy": 2.6,
      "fluency": 3.0
    },
    "cards": [
      {
        "priority": 1,
        "title": "과거 경험 질문에서 시제가 현재로 돌아와요",
        "why": "IM3부터는 과거 시제를 끝까지 유지하는 능력이 핵심 기준이에요.",
        "before": "Last year I go to Busan and I eat ...",
        "after": "Last year I went to Busan, and I ate ...",
        "related_order_nos": [4, 8]
      }
    ],
    "items": [
      {
        "order_no": 1,
        "question_type": "self_intro",
        "level": "IM2",
        "stt_status": "done",
        "eval_status": "done"
      },
      {
        "order_no": 3,
        "question_type": "routine",
        "level": "NL",
        "stt_status": "empty",
        "eval_status": "skipped"
      }
    ],
    "applied_rules": [
      { "rule": "length_cap", "message": "평균 답변 길이가 짧아 한 단계 낮게 조정했어요" }
    ],
    "evaluated_count": 7,
    "disclaimer": "합성 데이터로 보정한 참고용 예상 등급입니다. 실제 OPIc 결과와 다를 수 있습니다.",
    "graded_at": "2026-11-06T05:31:10Z"
  }
}
```

| 필드 | 설명 |
|---|---|
| `rank_raw` | 가중 평균 결과(반올림 전). `next.gap = ceil(rank_raw) - rank_raw`로 "다음 등급까지의 거리"를 보여 줄 때 씀 |
| `scores` | 평가 완료 문항의 영역별 평균 (1.0~5.0) |
| `cards` | 3~5장, `priority` 오름차순 = 고치면 효과가 큰 순서 |
| `items` | 문항별 요약. 상세는 E6 |
| `applied_rules` | 등급 조정 규칙이 적용되었으면 그 내역. 없으면 `[]` |
| `evaluated_count` | `eval_status: done`인 문항 수 |

**200 — 실패 (`failed`)**
```json
{
  "session_id": "8f0c...4a10",
  "status": "failed",
  "progress": null,
  "result": null,
  "failure": {
    "code": "INSUFFICIENT_EVALUATIONS",
    "message": "평가를 완료하지 못했습니다. 다시 평가를 눌러 주세요.",
    "evaluated_count": 3,
    "failed_order_nos": [2, 5, 6, 7, 8]
  }
}
```

- 결과 화면은 이때 [다시 평가] 버튼으로 E9를 호출합니다.
- **시험 단위 피드백 생성만 실패한 경우**에는 `failed`로 처리하지 않습니다. `status: "done"`, `cards: []`로 등급은 보여 주고 "피드백을 불러오지 못했어요" 문구를 띄웁니다.

**에러:** `404 SESSION_NOT_FOUND`, `409 SESSION_NOT_FINISHED` (`in_progress` 상태에서 호출)

---

### E9. `POST /sessions/{session_id}/regrade`

녹음과 STT 결과를 재사용해서 **실패한 단계만** 다시 실행합니다.

**Request** (body 생략 가능)
```json
{ "scope": "failed" }
```

| `scope` | 동작 |
|---|---|
| `failed` (기본) | `stt_status`나 `eval_status`가 `failed`인 문항만 재처리 후 등급·피드백 재생성 |
| `all` | 모든 문항 평가를 다시 실행 (프롬프트를 바꾼 뒤 개발 중에 사용) |

**202**
```json
{ "session_id": "8f0c...4a10", "status": "grading", "requeued_order_nos": [2, 5, 6, 7, 8] }
```

**에러:** `404 SESSION_NOT_FOUND`, `409 SESSION_NOT_FINISHED`, `409 ALREADY_GRADING`

---

### E10. `POST /sessions/{session_id}/chat` — 나중에

MVP에서는 항상 `501`을 돌려줍니다. 프론트엔드 버튼은 "개발 중"으로 표시합니다.

**501**
```json
{ "error": { "code": "NOT_IMPLEMENTED", "message": "AI 채팅은 준비 중입니다." } }
```

예정 형식(참고):
```json
// Request
{ "message": "과거 시제 연습은 어떻게 하면 좋을까요?" }
// Response (SSE 스트리밍 예정)
{ "reply": "...", "referenced_order_nos": [4] }
```

---

### S1·S2. 정적 TTS 파일

서버를 시작하기 전에 Google Colab에서 OmniVoice로 미리 만들어 `backend/static/tts/`에 넣어 둡니다(`colab/omnivoice_tts.ipynb`, 과정은 REQUIREMENTS_v2 §4 F6).

| 경로 | 내용 |
|---|---|
| `/static/tts/questions/{question_id}.mp3` | 문항 음성 |
| `/static/tts/host/greeting.mp3` | "Hi, I'm ___. Let's get started." |
| `/static/tts/host/say_again.mp3` | "Sorry, I didn't catch that. Could you say that again?" |
| `/static/tts/host/whenever_ready.mp3` | "Whenever you're ready." (20초 동안 녹음을 시작하지 않을 때) |
| `/static/tts/host/next.mp3` | "Okay. Let's move on to the next question." |
| `/static/tts/host/finish.mp3` | "That's the end of the test. Great job!" |

- 진행자 애니메이션이 음량을 분석해야 하므로 **같은 출처(same-origin)에서 서빙**합니다. 다른 출처면 CORS 헤더(`Access-Control-Allow-Origin`)가 필요하고, `<audio crossorigin="anonymous">`로 불러와야 합니다.
- 파일이 없으면 `404`가 납니다. 이때 프론트엔드는 Web Speech API로 대신 읽습니다.

---

## 5. 에러 코드 전체 목록

| 코드 | HTTP | 사용 엔드포인트 | 프론트엔드 동작 |
|---|---|---|---|
| `VALIDATION_ERROR` | 422 | 전체 | 개발 중 버그. 콘솔 출력 |
| `SERVICE_NOT_READY` | 503 | E3 | "서버를 준비하고 있어요" + 3초 후 E1 재확인 |
| `SESSION_NOT_FOUND` | 404 | E4~E10 | 랜딩으로 이동 |
| `ANSWER_NOT_FOUND` | 404 | E6 | 해당 문항 "답변 없음" 표시 |
| `SESSION_CLOSED` | 409 | E5 | 결과 화면으로 이동 |
| `SESSION_NOT_FINISHED` | 409 | E8, E9 | 시험 화면으로 이동 |
| `ALREADY_GRADING` | 409 | E9 | 폴링 계속 |
| `INVALID_ORDER_NO` | 422 | E5 | 개발 중 버그 |
| `AUDIO_TOO_SHORT` | 422 | E5 | `say_again` 재생 → 재녹음 |
| `AUDIO_TOO_LONG` | 422 | E5 | 녹음 2분 자동 종료가 동작하지 않은 버그 |
| `UNSUPPORTED_MEDIA` | 415 | E5 | "지원하지 않는 브라우저" 안내 |
| `PAYLOAD_TOO_LARGE` | 413 | E5 | 위와 같음 |
| `NOT_ENOUGH_ANSWERS` | 422 | E7 | "최소 4문항은 답해야 채점할 수 있어요" |
| `NOT_IMPLEMENTED` | 501 | E10 | "개발 중" |
| `INTERNAL_ERROR` | 500 | 전체 | "잠시 후 다시 시도해 주세요" |

> FastAPI 기본 422 응답(`{"detail": [...]}`)은 예외 핸들러에서 `VALIDATION_ERROR` 형식으로 바꿉니다.
> 500 응답에는 스택 트레이스를 넣지 않습니다(로그로만 남김).

---

## 6. 전체 시퀀스

```
Browser                         FastAPI                       Background
  │ GET /health ─────────────────▶│
  │◀──────────── 200 ready:true ──│
  │ POST /sessions ──────────────▶│ 문항 8개 추출
  │◀──────── 201 questions[8] ────│
  │
  │ ┌─ 문항 반복 (order_no = 1..8) ───────────────────────────────┐
  │ │ <audio> 문항 mp3 재생 (+ AnalyserNode → 진행자 애니메이션)    │
  │ │ MediaRecorder 녹음                                         │
  │ │ POST /answers (multipart) ─▶│ 파일 저장                    │
  │ │◀──────────────────── 202 ───│──────▶ STT + 지표            │
  │ │ 바로 다음 문항                │        └▶ 문항 평가(RAG+LLM)  │
  │ └────────────────────────────────────────────────────────────┘
  │
  │ POST /finish ────────────────▶│ status = grading
  │◀────────────────────── 202 ───│──────▶ 남은 평가 → 등급(코드) → 피드백(LLM)
  │ GET /result (2초 폴링) ───────▶│
  │◀──── 200 grading, percent ────│
  │ ...                           │
  │◀──── 200 done, result ────────│ 폴링 종료 → 결과 화면
```

---

## 7. Pydantic 스키마 초안 (`backend/app/schemas.py`)

```python
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field

Level = Literal["NL", "NM", "NH", "IL", "IM1", "IM2", "IM3", "IH", "AL"]
TierName = Literal["bronze", "silver", "gold", "platinum", "diamond"]
QuestionType = Literal[
    "self_intro", "description", "routine", "past_experience", "comparison",
    "issue", "roleplay_ask", "roleplay_solve", "roleplay_experience",
]
SessionStatus = Literal["in_progress", "grading", "done", "failed"]
SttStatus = Literal["pending", "done", "empty", "failed"]
EvalStatus = Literal["pending", "done", "skipped", "failed"]


# ---------- 공통 ----------
class ErrorBody(BaseModel):
    code: str
    message: str
    detail: dict | None = None

class ErrorResponse(BaseModel):
    error: ErrorBody


# ---------- E3 ----------
class CreateSessionRequest(BaseModel):
    survey: dict[str, list[str]] | None = None
    self_assessment: int | None = Field(None, ge=1, le=6)

class Limits(BaseModel):
    min_record_ms: int = 2000
    max_record_ms: int = 120000
    replay_limit: int = 1
    idle_prompt_ms: int = 20000
    accepted_mime: list[str] = ["audio/webm", "audio/ogg", "audio/wav"]

class Question(BaseModel):
    order_no: int = Field(ge=1, le=8)
    question_id: str
    question_type: QuestionType
    text: str
    difficulty: str
    audio_url: str | None

class CreateSessionResponse(BaseModel):
    session_id: UUID
    status: SessionStatus
    created_at: datetime
    limits: Limits
    questions: list[Question]


# ---------- E4 / E5 ----------
class AnswerState(BaseModel):
    order_no: int
    uploaded: bool
    stt_status: SttStatus | None
    eval_status: EvalStatus | None

class SessionResponse(BaseModel):
    session_id: UUID
    status: SessionStatus
    created_at: datetime
    questions: list[Question]
    answers: list[AnswerState]
    next_order_no: int | None

class UploadAnswerResponse(BaseModel):
    answer_id: UUID
    order_no: int
    stt_status: SttStatus
    replaced: bool
    next_order_no: int | None


# ---------- E6 (평가 결과: LLM 출력 스키마와 공유) ----------
class Metrics(BaseModel):
    duration_sec: float
    speech_sec: float
    word_count: int
    wpm: float
    long_pause_count: int
    filler_per100: float
    repeat_per100: float

class Scores(BaseModel):
    task_completion: int = Field(ge=1, le=5)
    text_type: int = Field(ge=1, le=5)
    accuracy: int = Field(ge=1, le=5)
    fluency: int = Field(ge=1, le=5)

class Mistake(BaseModel):
    quote: str          # 사용자 답변 원문 인용
    problem: str        # 한국어 설명
    fix: str            # 고친 영어 문장

class ItemScoreLLM(BaseModel):
    """LLM Structured Output으로 강제하는 스키마. item_rank는 코드가 계산하므로 여기 없음."""
    scores: Scores
    closest_level: Level
    evidence: list[str] = Field(max_length=3)
    mistakes: list[Mistake] = Field(max_length=5)
    upgrade_tip: str

class ItemEval(ItemScoreLLM):
    item_rank: float                 # scoring.py가 계산
    retrieved_contrast_set_id: str

class AnswerDetailResponse(BaseModel):
    order_no: int
    question: Question
    stt_status: SttStatus | None
    stt_text: str | None
    metrics: Metrics | None
    eval_status: EvalStatus | None
    eval: ItemEval | None


# ---------- E7 / E9 ----------
class FinishResponse(BaseModel):
    session_id: UUID
    status: SessionStatus
    uploaded_count: int

class RegradeRequest(BaseModel):
    scope: Literal["failed", "all"] = "failed"

class RegradeResponse(BaseModel):
    session_id: UUID
    status: SessionStatus
    requeued_order_nos: list[int]


# ---------- E8 ----------
class Progress(BaseModel):
    stage: Literal["stt", "item_eval", "scoring", "feedback"]
    stt_done: int
    eval_done: int
    total: int
    percent: int = Field(ge=0, le=100)

class Tier(BaseModel):
    name: TierName
    color: str

class NextLevel(BaseModel):
    level: Level | None          # AL이면 None
    gap: float
    message: str

class AvgScores(BaseModel):
    task_completion: float
    text_type: float
    accuracy: float
    fluency: float

class FeedbackCard(BaseModel):
    priority: int
    title: str
    why: str
    before: str
    after: str
    related_order_nos: list[int]

class ItemSummary(BaseModel):
    order_no: int
    question_type: QuestionType
    level: Level | None
    stt_status: SttStatus | None
    eval_status: EvalStatus | None

class AppliedRule(BaseModel):
    rule: Literal["length_cap", "fluency_cap"]
    message: str

class ExamResult(BaseModel):
    level: Level
    rank: int = Field(ge=1, le=9)
    rank_raw: float
    tier: Tier
    next: NextLevel
    headline: str
    scores: AvgScores
    cards: list[FeedbackCard]
    items: list[ItemSummary]
    applied_rules: list[AppliedRule]
    evaluated_count: int
    disclaimer: str
    graded_at: datetime

class Failure(BaseModel):
    code: Literal["INSUFFICIENT_EVALUATIONS"]
    message: str
    evaluated_count: int
    failed_order_nos: list[int]

class ResultResponse(BaseModel):
    session_id: UUID
    status: SessionStatus
    progress: Progress | None
    result: ExamResult | None
    failure: Failure | None = None
```

---

## 8. 프론트엔드 구현 메모

- **녹음 포맷:** `MediaRecorder.isTypeSupported("audio/webm;codecs=opus")`를 먼저 확인하고, 안 되면 `audio/ogg`를 씁니다. faster-whisper는 내부적으로 ffmpeg로 디코딩하므로 webm을 그대로 받을 수 있습니다.
- **업로드 실패 재시도:** 녹음 `Blob`을 메모리에 보관하고 최대 3회 다시 보냅니다(1초, 2초, 4초 간격). 같은 `order_no`라서 덮어쓰기로 안전하게 처리됩니다.
- **새로고침 복구:** `session_id`를 `localStorage`에 저장하고, 앱이 시작될 때 E4로 `next_order_no`부터 이어 갑니다(`localStorage` 접근은 `try/catch`로 감쌉니다).
- **폴링:** E8을 2초 간격으로 호출하고, `done`이나 `failed`가 되면 멈춥니다. 3분이 지나도 `grading`이면 "생각보다 오래 걸리고 있어요" 문구를 띄우되 폴링은 계속합니다.
- **API 클라이언트 타입:** 백엔드를 띄운 뒤 `npx openapi-typescript http://127.0.0.1:8000/openapi.json -o src/lib/api-types.ts`로 TypeScript 타입을 자동 생성하면 §7과 프론트엔드 타입이 어긋나지 않습니다.

---

## 9. 변경 이력

| 버전 | 날짜 | 내용 |
|---|---|---|
| v1 | 2026-11-06 | REQUIREMENTS_v2 §8을 바탕으로 최초 작성. `GET /sessions/{id}`, `GET /answers/{order_no}`, `GET /meta/survey-options`, `POST /chat`(501)을 추가하고 진행자 대사 정적 파일을 정의 |
