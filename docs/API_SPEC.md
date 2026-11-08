# API 명세 v2 — HTTP 형식 v3

계약 원본은 `agents/contracts.yaml`, 충돌 시 그쪽 우선.

기본 주소 `http://127.0.0.1:8000/api/v1`, JSON은 snake_case다. 아래 UUID와 음성 URL은 형식 설명용 예시다.
202는 작업 접수이며 완료가 아니다. 준비·STT·평가 상태를 2초마다 조회한다.
세션·업로드 client_request_id는 멱등 키다. 재전송은 같은 키, 재녹음은 새 키를 사용한다.
세션 생성 재전송은 저장된 세션을 우선 반환하므로 문제 은행 변경으로 세트를 재생성하지 않는다.
업로드 DB 접수 후 원음 이동이 실패하면 동일 Blob·요청 키 재전송으로 같은 답변을 복구한다. 다른 내용으로 기존 원음을 덮어쓰지 않는다.
자기소개 워밍업을 포함한 8답변을 저장하고 나머지 7문항만 등급 근거에 쓴다.
결과 조회는 읽기 전용이며 AI를 호출하지 않는다. 500 응답에 traceback을 포함하지 않는다.

## 상태 전이

| 현재 | 다음 |
| --- | --- |
| preparing | ready |
| preparing | prepare_failed |
| prepare_failed | preparing |
| preparing | cancelled |
| prepare_failed | cancelled |
| ready | cancelled |
| ready | in_progress |
| in_progress | submitted |
| submitted | grading (마지막 STT 종결 또는 제출 중 나중 트랜잭션) |
| grading | done |
| grading | grading_failed |
| grading_failed | grading |
| done | grading |


답변 STT 상태는 queued → processing → done/rejected/failed다. **v3부터 현재 문항은 업로드 접수 트랜잭션에서 바로 전진한다.**
STT는 이전 문항이거나 제출 후(submitted)여도 반영된다. rejected와 재시도를 소진한 failed는 종결 상태이며, 평가에서 인식 불가 문항으로 처리된다.
제출(submitted)은 남은 STT를 기다리는 상태다. STT가 모두 종결되면 서버가 그 시점의 채택 답변을 고정하고 평가를 등록해 grading으로 넘긴다.
평가 상태는 queued/running/done/failed다. 평가 실패는 세션 grading_failed로 나타난다.
모든 is_scored=false 문항은 문항별 연습 피드백만 제공한다. 영역별 숫자 점수는 없다.

## 엔드포인트

### A1 GET `/health`

HTTP 200.

응답 예시:
```json
{
  "ready": false,
  "db": "ok",
  "worker_seen_at": null,
  "whisper_model": "small.en",
  "corpus_version": null,
  "tts": {
    "voice_id": null,
    "assets": 0,
    "missing_pilot": []
  }
}
```

### A2 GET `/scenarios`

HTTP 200.

응답 예시:
```json
[
  {
    "scenario_id": "default",
    "label": "기본 구성",
    "description": "여러 주제가 섞인 기본 모의고사",
    "question_count": 8
  }
]
```

### A3 GET `/host-lines`

HTTP 200. 활성 음성의 진행자 대사 URL. 세션 시작 전 화면에서도 씀(say_again 등은 세션 링크 값을 우선)

응답 예시:
```json
{
  "greeting": {
    "key": "greeting",
    "text": "Hi, I'm Rin. I'll be your interviewer today. Let's get started.",
    "audio_url": null
  },
  "say_again": {
    "key": "say_again",
    "text": "Sorry, I didn't catch that. Could you say that again?",
    "audio_url": null
  },
  "next": {
    "key": "next",
    "text": "Okay. Let's move on to the next question.",
    "audio_url": null
  },
  "finish": {
    "key": "finish",
    "text": "That's the end of the test. Thank you.",
    "audio_url": null
  }
}
```

### S1 POST `/sessions`

HTTP 202. client_request_id 같으면 같은 세션(200). replaces_session_id 주면 그 세션 취소

요청:
```json
{"client_request_id": "session-request-1", "scenario_id": "default", "mic_check_passed": true, "replaces_session_id": null}
```

응답 예시:
```json
{
  "session_id": "00000000-0000-4000-8000-000000000001",
  "status": "preparing",
  "scenario_id": "default",
  "question_count": 8,
  "current_order_no": 1,
  "all_answered": false,
  "prepare": {
    "total": 12,
    "linked": 0,
    "failures": []
  },
  "latest_evaluation_status": null,
  "created_at": "2026-11-06T08:00:00Z",
  "updated_at": "2026-11-06T08:00:00Z"
}
```

오류: SCENARIO_UNAVAILABLE, MIC_CHECK_REQUIRED.

### S2 GET `/sessions/{session_id}`

HTTP 200.

응답 예시:
```json
{
  "session_id": "00000000-0000-4000-8000-000000000001",
  "status": "preparing",
  "scenario_id": "default",
  "question_count": 8,
  "current_order_no": 1,
  "all_answered": false,
  "prepare": {
    "total": 12,
    "linked": 0,
    "failures": []
  },
  "latest_evaluation_status": null,
  "created_at": "2026-11-06T08:00:00Z",
  "updated_at": "2026-11-06T08:00:00Z"
}
```

오류: SESSION_NOT_FOUND.

### S3 POST `/sessions/{session_id}/prepare/retry`

HTTP 202.

요청 본문 없음.

응답 예시:
```json
{
  "session_id": "00000000-0000-4000-8000-000000000001",
  "status": "preparing",
  "scenario_id": "default",
  "question_count": 8,
  "current_order_no": 1,
  "all_answered": false,
  "prepare": {
    "total": 12,
    "linked": 0,
    "failures": []
  },
  "latest_evaluation_status": null,
  "created_at": "2026-11-06T08:00:00Z",
  "updated_at": "2026-11-06T08:00:00Z"
}
```

오류: INVALID_STATE.

### S4 POST `/sessions/{session_id}/cancel`

HTTP 200.

요청 본문 없음.

응답 예시:
```json
{
  "session_id": "00000000-0000-4000-8000-000000000001",
  "status": "cancelled",
  "scenario_id": "default",
  "question_count": 8,
  "current_order_no": 1,
  "all_answered": false,
  "prepare": null,
  "latest_evaluation_status": null,
  "created_at": "2026-11-06T08:00:00Z",
  "updated_at": "2026-11-06T08:00:00Z"
}
```

오류: INVALID_STATE.

### S5 POST `/sessions/{session_id}/start`

HTTP 200.

요청 본문 없음.

응답 예시:
```json
{
  "session_id": "00000000-0000-4000-8000-000000000001",
  "status": "in_progress",
  "scenario_id": "default",
  "question_count": 8,
  "current_order_no": 1,
  "all_answered": false,
  "prepare": null,
  "latest_evaluation_status": null,
  "created_at": "2026-11-06T08:00:00Z",
  "updated_at": "2026-11-06T08:00:00Z"
}
```

오류: INVALID_STATE.

### Q1 GET `/sessions/{session_id}/current`

HTTP 200. in_progress에서만. 모든 답변 저장 완료면 all_answered=true, question=null

응답 예시:
```json
{
  "session_status": "in_progress",
  "total": 8,
  "all_answered": false,
  "question": {
    "order_no": 1,
    "question_id": "Q000",
    "question_type": "self_intro",
    "is_scored": false,
    "text": "Let's start the interview now. Tell me a little bit about yourself.",
    "audio_url": "/media/tts/example/question/Q000.mp3",
    "duration_sec": 7.4,
    "replay_count": 0,
    "replay_limit": 1
  },
  "pending_answer": null,
  "host_lines": {
    "greeting": {
      "key": "greeting",
      "text": "Hi, I'm Rin. I'll be your interviewer today. Let's get started.",
      "audio_url": null
    },
    "say_again": {
      "key": "say_again",
      "text": "Sorry, I didn't catch that. Could you say that again?",
      "audio_url": null
    },
    "next": {
      "key": "next",
      "text": "Okay. Let's move on to the next question.",
      "audio_url": null
    },
    "finish": {
      "key": "finish",
      "text": "That's the end of the test. Thank you.",
      "audio_url": null
    }
  }
}
```

오류: INVALID_STATE.

### Q2 POST `/sessions/{session_id}/questions/{order_no}/replay`

HTTP 200. 다시 듣기 직전에 호출. 첫 재생은 호출하지 않음

요청 본문 없음.

응답 예시:
```json
{
  "order_no": 1,
  "replay_count": 1,
  "replay_limit": 1
}
```

오류: REPLAY_LIMIT, ORDER_MISMATCH.

### U1 POST `/sessions/{session_id}/answers`

HTTP 202. 파일은 임시 경로에 쓴 뒤 create_answer 성공 시 최종 경로로 이동. 실패하면 임시 파일 삭제

요청: multipart/form-data의 order_no=1, client_request_id=answer-request-1, duration_ms=3000, audio=<파일>.
허용 MIME: audio/webm, audio/ogg, audio/wav, audio/mp4. codecs 매개변수는 제외하고 검사한다.
최대 10MiB, 2초~120초(클라이언트 길이 오차 허용 +5초). 파일은 임시 저장 후 DB 접수 성공 시 최종 경로로 이동한다.
접수와 동시에 다음 문항으로 넘어간다(v3). 클라이언트는 STT 완료를 기다리지 않는다. 전사·무음·손상 검사는 워커가 수행한다.

응답 예시:
```json
{
  "answer_id": "00000000-0000-4000-8000-000000000002",
  "order_no": 1,
  "attempt_no": 1,
  "stt_status": "queued",
  "reject_reason": null,
  "error_code": null,
  "stt_text": null,
  "metrics": null,
  "session_status": "in_progress",
  "current_order_no": 2,
  "all_answered": false
}
```

오류: INVALID_STATE, ORDER_MISMATCH, ANSWER_PENDING, AUDIO_TOO_SHORT, AUDIO_TOO_LONG, UNSUPPORTED_MEDIA, PAYLOAD_TOO_LARGE.

### U2 GET `/sessions/{session_id}/answers/{answer_id}`

HTTP 200.

응답 예시:
```json
{
  "answer_id": "00000000-0000-4000-8000-000000000002",
  "order_no": 1,
  "attempt_no": 1,
  "stt_status": "queued",
  "reject_reason": null,
  "error_code": null,
  "stt_text": null,
  "metrics": null,
  "session_status": "in_progress",
  "current_order_no": 1,
  "all_answered": false
}
```

오류: ANSWER_NOT_FOUND.

### U3 POST `/sessions/{session_id}/answers/{answer_id}/retry-stt`

HTTP 202.

요청 본문 없음.

응답 예시:
```json
{
  "answer_id": "00000000-0000-4000-8000-000000000002",
  "order_no": 1,
  "attempt_no": 1,
  "stt_status": "queued",
  "reject_reason": null,
  "error_code": null,
  "stt_text": null,
  "metrics": null,
  "session_status": "in_progress",
  "current_order_no": 1,
  "all_answered": false
}
```

세션이 in_progress 또는 submitted(평가 등록 전)이면 이전 문항의 failed 답변도 재처리할 수 있다.

오류: INVALID_STATE.

### E1 POST `/sessions/{session_id}/submit`

HTTP 202.

요청 본문 없음.

응답 예시:
```json
{
  "session_id": "00000000-0000-4000-8000-000000000001",
  "status": "grading",
  "scenario_id": "default",
  "question_count": 8,
  "current_order_no": 9,
  "all_answered": true,
  "prepare": null,
  "latest_evaluation_status": "queued",
  "created_at": "2026-11-06T08:00:00Z",
  "updated_at": "2026-11-06T08:00:00Z"
}
```

모든 문항이 접수되거나 건너뛰어졌으면 STT 완료와 관계없이 제출된다. 남은 STT가 있으면 `status`가 `submitted`이고
`latest_evaluation_status`가 null이며, `stt_progress`로 진행 상황을 보여 준다. 남은 STT가 끝나면 평가가 자동 등록된다.

오류: INVALID_STATE, NOT_ALL_ANSWERED.

### E2 GET `/sessions/{session_id}/result`

HTTP 200. AI를 호출하지 않는다. 저장값만 반환

응답 예시:
```json
{
  "session_status": "grading",
  "evaluation_status": "queued",
  "run_no": 1,
  "result": null,
  "answers": [
    {
      "order_no": 1,
      "question_id": "Q000",
      "question_type": "self_intro",
      "question_text": "Example question",
      "is_scored": false,
      "stt_text": "Example answer.",
      "metrics": {
        "duration_sec": 3.0,
        "speech_sec": 2.0,
        "word_count": 2,
        "wpm": 40.0,
        "articulation_wpm": 60.0,
        "long_pause_count": 0,
        "observed_filler_per100": null,
        "metrics_version": "m1"
      }
    },
    {
      "order_no": 2,
      "question_id": "Q002",
      "question_type": "description",
      "question_text": "Example question",
      "is_scored": true,
      "stt_text": "Example answer.",
      "metrics": {
        "duration_sec": 3.0,
        "speech_sec": 2.0,
        "word_count": 2,
        "wpm": 40.0,
        "articulation_wpm": 60.0,
        "long_pause_count": 0,
        "observed_filler_per100": null,
        "metrics_version": "m1"
      }
    },
    {
      "order_no": 3,
      "question_id": "Q003",
      "question_type": "description",
      "question_text": "Example question",
      "is_scored": true,
      "stt_text": "Example answer.",
      "metrics": {
        "duration_sec": 3.0,
        "speech_sec": 2.0,
        "word_count": 2,
        "wpm": 40.0,
        "articulation_wpm": 60.0,
        "long_pause_count": 0,
        "observed_filler_per100": null,
        "metrics_version": "m1"
      }
    },
    {
      "order_no": 4,
      "question_id": "Q004",
      "question_type": "description",
      "question_text": "Example question",
      "is_scored": true,
      "stt_text": "Example answer.",
      "metrics": {
        "duration_sec": 3.0,
        "speech_sec": 2.0,
        "word_count": 2,
        "wpm": 40.0,
        "articulation_wpm": 60.0,
        "long_pause_count": 0,
        "observed_filler_per100": null,
        "metrics_version": "m1"
      }
    },
    {
      "order_no": 5,
      "question_id": "Q005",
      "question_type": "description",
      "question_text": "Example question",
      "is_scored": true,
      "stt_text": "Example answer.",
      "metrics": {
        "duration_sec": 3.0,
        "speech_sec": 2.0,
        "word_count": 2,
        "wpm": 40.0,
        "articulation_wpm": 60.0,
        "long_pause_count": 0,
        "observed_filler_per100": null,
        "metrics_version": "m1"
      }
    },
    {
      "order_no": 6,
      "question_id": "Q006",
      "question_type": "description",
      "question_text": "Example question",
      "is_scored": true,
      "stt_text": "Example answer.",
      "metrics": {
        "duration_sec": 3.0,
        "speech_sec": 2.0,
        "word_count": 2,
        "wpm": 40.0,
        "articulation_wpm": 60.0,
        "long_pause_count": 0,
        "observed_filler_per100": null,
        "metrics_version": "m1"
      }
    },
    {
      "order_no": 7,
      "question_id": "Q007",
      "question_type": "description",
      "question_text": "Example question",
      "is_scored": true,
      "stt_text": "Example answer.",
      "metrics": {
        "duration_sec": 3.0,
        "speech_sec": 2.0,
        "word_count": 2,
        "wpm": 40.0,
        "articulation_wpm": 60.0,
        "long_pause_count": 0,
        "observed_filler_per100": null,
        "metrics_version": "m1"
      }
    },
    {
      "order_no": 8,
      "question_id": "Q008",
      "question_type": "description",
      "question_text": "Example question",
      "is_scored": true,
      "stt_text": "Example answer.",
      "metrics": {
        "duration_sec": 3.0,
        "speech_sec": 2.0,
        "word_count": 2,
        "wpm": 40.0,
        "articulation_wpm": 60.0,
        "long_pause_count": 0,
        "observed_filler_per100": null,
        "metrics_version": "m1"
      }
    }
  ],
  "error_code": null,
  "graded_at": null
}
```

오류: INVALID_STATE.

### E3 POST `/sessions/{session_id}/regrade`

HTTP 202.

요청 본문 없음.

응답 예시:
```json
{
  "session_id": "00000000-0000-4000-8000-000000000001",
  "status": "grading",
  "scenario_id": "default",
  "question_count": 8,
  "current_order_no": 9,
  "all_answered": true,
  "prepare": null,
  "latest_evaluation_status": "queued",
  "created_at": "2026-11-06T08:00:00Z",
  "updated_at": "2026-11-06T08:00:00Z"
}
```

오류: INVALID_STATE.

### H2 GET `/sessions/active`

HTTP 200. 로그인 필요(Authorization: Bearer). v3 헤더 배지·완료 알림용 가벼운 폴링 응답이며 본인 세션만 반환한다.
`items`는 in_progress/submitted/grading 세션, `recent_finished`는 최근 10분 안에 done/grading_failed가 된 세션이다.

응답 예시:
```json
{
  "items": [{"session_id": "00000000-0000-4000-8000-000000000001", "scenario_id": "default", "status": "submitted",
             "question_count": 8, "current_order_no": 9, "latest_evaluation_status": null,
             "stt_progress": {"total": 8, "done": 6, "pending": 2, "unusable": 0},
             "created_at": "2026-11-08T08:00:00Z", "submitted_at": "2026-11-08T08:20:00Z", "updated_at": "2026-11-08T08:20:00Z"}],
  "recent_finished": [],
  "latest_report_session_id": "00000000-0000-4000-8000-000000000001",
  "in_progress_session_id": null
}
```

오류: UNAUTHORIZED.

### X1 POST `/sessions/{session_id}/chat`

HTTP 501.

요청 본문 없음.

응답 예시:
```json
{
  "error": {
    "code": "NOT_IMPLEMENTED",
    "message": "준비 중인 기능이에요.",
    "detail": {}
  }
}
```

오류: NOT_IMPLEMENTED.

## 오류

형식: `{"error":{"code":"ORDER_MISMATCH","message":"현재 문항이 아니에요. 화면을 새로고침해 주세요.","detail":{}}}`

| 코드 | HTTP | 문구 |
| --- | --- | --- |
| VALIDATION_ERROR | 422 | 요청 형식이 올바르지 않습니다. |
| SERVICE_NOT_READY | 503 | 서버를 준비하고 있어요. 잠시 후 다시 시도해 주세요. |
| SESSION_NOT_FOUND | 404 | 시험 정보를 찾을 수 없어요. |
| ANSWER_NOT_FOUND | 404 | 답변을 찾을 수 없어요. |
| INVALID_STATE | 409 | 지금 단계에서는 할 수 없는 요청이에요. |
| SCENARIO_UNAVAILABLE | 422 | 선택한 시나리오로는 시험을 구성할 수 없어요. 다른 설정을 선택해 주세요. |
| MIC_CHECK_REQUIRED | 422 | 마이크 테스트를 먼저 완료해 주세요. |
| ORDER_MISMATCH | 409 | 현재 문항이 아니에요. 화면을 새로고침해 주세요. |
| ANSWER_PENDING | 409 | 이전 답변을 처리하고 있어요. |
| REPLAY_LIMIT | 409 | 다시 듣기는 한 번만 할 수 있어요. |
| AUDIO_TOO_SHORT | 422 | 녹음이 너무 짧아요. 다시 답변해 주세요. |
| AUDIO_TOO_LONG | 422 | 녹음이 너무 길어요. |
| UNSUPPORTED_MEDIA | 415 | 지원하지 않는 녹음 형식이에요. |
| PAYLOAD_TOO_LARGE | 413 | 녹음 파일이 너무 커요. |
| NOT_ALL_ANSWERED | 409 | 아직 저장되지 않은 답변이 있어요. |
| NOT_IMPLEMENTED | 501 | 준비 중인 기능이에요. |
| INTERNAL_ERROR | 500 | 잠시 후 다시 시도해 주세요. |

작업 오류(error_code 필드): TTS_ASSET_MISSING, TTS_HASH_MISMATCH, TTS_FILE_MISSING, NO_ACTIVE_VOICE, STT_DECODE_ERROR, STT_ENGINE_ERROR, LLM_TRANSIENT, LLM_REFUSED, LLM_INVALID_OUTPUT, EVAL_INPUT_TOO_LARGE, EVAL_INPUT_INVALID, EVAL_INTERNAL.

## 스키마 필드

타입·nullable·고정값은 계약 v3와 backend/app/schemas/api.py 및 frontend/src/api/types.ts를 따른다.

### HealthOut

| 필드 | 타입/의미 |
| --- | --- |
| ready | bool |
| db | ok / error |
| worker_seen_at | datetime / null |
| whisper_model | str |
| corpus_version | str / null |
| tts | {"voice_id": "str / null", "assets": "int", "missing_pilot": "list[str]"} |

### ScenarioOut

| 필드 | 타입/의미 |
| --- | --- |
| scenario_id | str |
| label | str |
| description | str |
| question_count | int |

### HostLineOut

| 필드 | 타입/의미 |
| --- | --- |
| key | str |
| text | str |
| audio_url | str / null |

### CreateSessionIn

| 필드 | 타입/의미 |
| --- | --- |
| client_request_id | str |
| scenario_id | str (기본 'default') |
| mic_check_passed | bool |
| replaces_session_id | UUID / null |

### PrepareFailure

| 필드 | 타입/의미 |
| --- | --- |
| order_no | int / null |
| host_key | str / null |
| ref_id | str |
| error_code | str |

### PrepareProgress

| 필드 | 타입/의미 |
| --- | --- |
| total | int |
| linked | int |
| failures | list[PrepareFailure] |

### SessionOut

| 필드 | 타입/의미 |
| --- | --- |
| session_id | UUID |
| status | session_status |
| scenario_id | str |
| question_count | int |
| current_order_no | int |
| all_answered | bool |
| prepare | PrepareProgress / null |
| latest_evaluation_status | evaluation_status / null |
| stt_progress | SttProgress / null (v3, in_progress 이후) |
| created_at | datetime |
| updated_at | datetime |

### SttProgress

건너뛰지 않고 답변이 접수된 문항 기준(v3).

| 필드 | 타입/의미 |
| --- | --- |
| total | int, 접수된 문항 수 |
| done | int |
| pending | int, queued + processing |
| unusable | int, rejected + failed (평가에서 인식 불가) |

### QuestionOut

| 필드 | 타입/의미 |
| --- | --- |
| order_no | int |
| question_id | str |
| question_type | str |
| is_scored | bool |
| text | str |
| audio_url | str |
| duration_sec | float / null |
| replay_count | int |
| replay_limit | int |

### CurrentQuestionOut

| 필드 | 타입/의미 |
| --- | --- |
| session_status | session_status |
| total | int |
| all_answered | bool |
| question | QuestionOut / null |
| pending_answer | AnswerOut / null |
| host_lines | dict[str, HostLineOut] |
| stt_progress | SttProgress / null (v3) |

### ReplayOut

| 필드 | 타입/의미 |
| --- | --- |
| order_no | int |
| replay_count | int |
| replay_limit | int |

### Metrics

| 필드 | 타입/의미 |
| --- | --- |
| duration_sec | float |
| speech_sec | float |
| word_count | int |
| wpm | float |
| articulation_wpm | float / null |
| long_pause_count | int |
| observed_filler_per100 | float / null |
| metrics_version | str |

### AnswerOut

| 필드 | 타입/의미 |
| --- | --- |
| answer_id | UUID |
| order_no | int |
| attempt_no | int |
| stt_status | answer_stt_status |
| reject_reason | str / null |
| error_code | str / null |
| stt_text | str / null |
| metrics | Metrics / null |
| session_status | session_status |
| current_order_no | int |
| all_answered | bool |

### Mistake

| 필드 | 타입/의미 |
| --- | --- |
| quote | str |
| problem | str |
| fix | str |

### ItemFeedback

| 필드 | 타입/의미 |
| --- | --- |
| order_no | int |
| evaluation_role | evaluation_role |
| task_fulfillment | task_fulfillment |
| evidence | list[str] |
| mistakes | list[Mistake] |
| upgrade_tip | str |

### FeedbackCard

| 필드 | 타입/의미 |
| --- | --- |
| title | str |
| why | str |
| before | str / null |
| after | str |
| example_kind | example_kind |
| related_order_nos | list[int] |
| success_condition | str |

### DimensionFeedback

| 필드 | 타입/의미 |
| --- | --- |
| summary | str |
| evidence_order_nos | list[int] |
| limitations | list[str] |

### DimensionFeedbackSet

| 필드 | 타입/의미 |
| --- | --- |
| functions_tasks | DimensionFeedback |
| accuracy | DimensionFeedback |
| context_content | DimensionFeedback |
| text_type | DimensionFeedback |

### QuoteRef

| 필드 | 타입/의미 |
| --- | --- |
| order_no | int |
| quote | str |

### FactEvidence

| 필드 | 타입/의미 |
| --- | --- |
| criterion | functions_tasks / accuracy / context_content / text_type |
| observation | str |
| status | fact_status |
| order_no | int / null |
| quote | str / null |

### CoverageEntry

| 필드 | 타입/의미 |
| --- | --- |
| name | str |
| elicited_order_nos | list[int] |
| usable_order_nos | list[int] |
| gaps | list[str] |

### Coverage

| 필드 | 타입/의미 |
| --- | --- |
| functions | list[CoverageEntry] |
| time_frames | list[CoverageEntry] |
| contexts | list[CoverageEntry] |

### SustainedPerformance

| 필드 | 타입/의미 |
| --- | --- |
| capability | str |
| evidence | list[QuoteRef] |
| summary | str |

### BreakdownObservation

| 필드 | 타입/의미 |
| --- | --- |
| demanded_function | str |
| evidence | list[QuoteRef] |
| communicative_impact | str |
| recovery | str |

### UnusableItem

| 필드 | 타입/의미 |
| --- | --- |
| order_no | int |
| reason | str |

### EvaluationScope

| 필드 | 타입/의미 |
| --- | --- |
| submitted_order_nos | list[int] |
| scored_order_nos | list[int] |
| feedback_only_order_nos | list[int] |
| usable_order_nos | list[int] |
| unusable_items | list[UnusableItem] |

### AdditionalTask

| 필드 | 타입/의미 |
| --- | --- |
| target_function | str |
| reason | str |
| suggested_question | str |

### EvaluationResult

| 필드 | 타입/의미 |
| --- | --- |
| assessment_status | assessment_status |
| assessment_basis | transcript_and_metrics |
| rubric_version | str |
| prompt_version | str |
| im_rubric_version | str / null |
| evaluation_scope | EvaluationScope |
| input_issues | list[str] |
| base_level | base_level / null |
| estimated_level | level / null |
| im_estimation_status | im_estimation_status |
| provisional_label | str / null  (IM 세분값이면 policies.im_provisional_label, 서버가 붙임) |
| tier | {name,color} / null |
| headline | str |
| grade_rationale | str |
| dimension_feedback | DimensionFeedbackSet |
| coverage | Coverage |
| fact_evidence | list[FactEvidence] |
| sustained_performance | list[SustainedPerformance] |
| breakdown_observations | list[BreakdownObservation] |
| fluency_observations | str |
| why_this_level | str |
| why_not_lower | str |
| next_level_gap | str |
| borderline_levels | list[level] |
| uncertainty_reasons | list[str] |
| items | list[ItemFeedback] |
| feedback_cards | list[FeedbackCard] |
| additional_tasks_needed | list[AdditionalTask] |
| limitations | list[str] |
| insufficient_reason | str / null |
| disclaimer | str |

### ResultItemOut

| 필드 | 타입/의미 |
| --- | --- |
| order_no | int |
| question_id | str |
| question_type | str |
| question_text | str |
| is_scored | bool |
| stt_text | str |
| metrics | Metrics |
| skipped | bool |
| stt_status | answer_stt_status / null (v3, 인식 불가 표시용) |

### ResultOut

| 필드 | 타입/의미 |
| --- | --- |
| session_status | session_status |
| evaluation_status | evaluation_status / null |
| run_no | int / null |
| result | EvaluationResult / null |
| answers | list[ResultItemOut] |
| error_code | str / null |
| graded_at | datetime / null |
| stt_progress | SttProgress / null (v3) |

## 클라이언트 폴링 흐름

설정 → POST /sessions → GET /sessions/{id} 반복 → ready → POST /start
→ GET /current → TTS 재생 → 녹음 → POST /answers(202, 응답에서 이미 다음 문항) → 바로 다음 문항 재생 (v3)
→ 8문항 접수 → POST /submit(STT가 남았으면 submitted)
→ GET /result 반복(submitted면 stt_progress 표시) → 서버가 마지막 STT 종결 시 평가 등록 → evaluation_status=done이면 저장된 결과 표시.
→ 어느 화면에서든 GET /sessions/active(대기 세션이 있을 때만 5초)로 헤더 배지·완료 알림을 표시한다.
준비 실패는 동일 세트 prepare/retry, 답변 rejected/failed는 현재 문항에서 재녹음/원음 재처리,
평가 실패는 전체 답변으로 regrade한다. TTS 실패는 현재 단계에서 복구한다.
재평가 중 이전 성공 결과는 보존하며 새 결과 성공 저장 후 교체한다.
