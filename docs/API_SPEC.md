# API 명세 v2 — 구현 계약 v3

계약 원본은 `agents/contracts.yaml`, 충돌 시 그쪽 우선.

기본 주소: `http://127.0.0.1:8000/api/v1`. JSON 필드명은 snake_case다.
202는 작업 접수이며 완료가 아니다. 준비·STT·평가 상태를 2초마다 조회한다.
세션/업로드는 client_request_id로 중복을 방지하며 상태 기반 쓰기도 멱등이다.
자기소개를 포함한 8답변을 저장하고, 채점 대상 7문항만 등급 근거에 쓴다.
결과 조회는 저장된 결과를 반환하며 AI를 호출하지 않는다.

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
| submitted | grading |
| grading | done |
| grading | grading_failed |
| grading_failed | grading |
| done | grading |

## A1 GET `/health`

HTTP 200. 

응답 예시:
```json
{
  "ready": true,
  "db": "ok",
  "worker_seen_at": null,
  "whisper_model": "예시",
  "corpus_version": null,
  "tts": {
    "voice_id": null,
    "assets": 1,
    "missing_pilot": [
      "예시"
    ]
  }
}
```

## A2 GET `/scenarios`

HTTP 200. 

응답 예시:
```json
[
  {
    "scenario_id": "예시",
    "label": "예시",
    "description": "예시",
    "question_count": 1
  }
]
```

## A3 GET `/host-lines`

HTTP 200. 활성 음성의 진행자 대사 URL. 세션 시작 전 화면에서도 씀(say_again 등은 세션 링크 값을 우선)

응답 예시:
```json
{}
```

## S1 POST `/sessions`

HTTP 202. client_request_id 같으면 같은 세션(200). replaces_session_id 주면 그 세션 취소

요청 예시:
```json
{
  "client_request_id": "예시",
  "scenario_id": "예시",
  "mic_check_passed": true,
  "replaces_session_id": null
}
```

응답 예시:
```json
{
  "session_id": "00000000-0000-4000-8000-000000000001",
  "status": "preparing",
  "scenario_id": "예시",
  "question_count": 1,
  "current_order_no": 1,
  "all_answered": true,
  "prepare": null,
  "latest_evaluation_status": null,
  "created_at": "2026-11-06T08:00:00Z",
  "updated_at": "2026-11-06T08:00:00Z"
}
```

오류: SCENARIO_UNAVAILABLE, MIC_CHECK_REQUIRED.

## S2 GET `/sessions/{session_id}`

HTTP 200. 

응답 예시:
```json
{
  "session_id": "00000000-0000-4000-8000-000000000001",
  "status": "preparing",
  "scenario_id": "예시",
  "question_count": 1,
  "current_order_no": 1,
  "all_answered": true,
  "prepare": null,
  "latest_evaluation_status": null,
  "created_at": "2026-11-06T08:00:00Z",
  "updated_at": "2026-11-06T08:00:00Z"
}
```

오류: SESSION_NOT_FOUND.

## S3 POST `/sessions/{session_id}/prepare/retry`

HTTP 202. 

응답 예시:
```json
{
  "session_id": "00000000-0000-4000-8000-000000000001",
  "status": "preparing",
  "scenario_id": "예시",
  "question_count": 1,
  "current_order_no": 1,
  "all_answered": true,
  "prepare": null,
  "latest_evaluation_status": null,
  "created_at": "2026-11-06T08:00:00Z",
  "updated_at": "2026-11-06T08:00:00Z"
}
```

오류: INVALID_STATE.

## S4 POST `/sessions/{session_id}/cancel`

HTTP 200. 

응답 예시:
```json
{
  "session_id": "00000000-0000-4000-8000-000000000001",
  "status": "preparing",
  "scenario_id": "예시",
  "question_count": 1,
  "current_order_no": 1,
  "all_answered": true,
  "prepare": null,
  "latest_evaluation_status": null,
  "created_at": "2026-11-06T08:00:00Z",
  "updated_at": "2026-11-06T08:00:00Z"
}
```

오류: INVALID_STATE.

## S5 POST `/sessions/{session_id}/start`

HTTP 200. 

응답 예시:
```json
{
  "session_id": "00000000-0000-4000-8000-000000000001",
  "status": "preparing",
  "scenario_id": "예시",
  "question_count": 1,
  "current_order_no": 1,
  "all_answered": true,
  "prepare": null,
  "latest_evaluation_status": null,
  "created_at": "2026-11-06T08:00:00Z",
  "updated_at": "2026-11-06T08:00:00Z"
}
```

오류: INVALID_STATE.

## Q1 GET `/sessions/{session_id}/current`

HTTP 200. in_progress에서만. 모든 답변 저장 완료면 all_answered=true, question=null

응답 예시:
```json
{
  "session_status": "preparing",
  "total": 1,
  "all_answered": true,
  "question": null,
  "pending_answer": null,
  "host_lines": {}
}
```

오류: INVALID_STATE.

## Q2 POST `/sessions/{session_id}/questions/{order_no}/replay`

HTTP 200. 다시 듣기 직전에 호출. 첫 재생은 호출하지 않음

응답 예시:
```json
{
  "order_no": 1,
  "replay_count": 1,
  "replay_limit": 1
}
```

오류: REPLAY_LIMIT, ORDER_MISMATCH.

## U1 POST `/sessions/{session_id}/answers`

HTTP 202. 파일은 임시 경로에 쓴 뒤 create_answer 성공 시 최종 경로로 이동. 실패하면 임시 파일 삭제

요청: multipart/form-data — order_no(int), client_request_id(str), duration_ms(int), audio(file).

응답 예시:
```json
{
  "answer_id": "00000000-0000-4000-8000-000000000001",
  "order_no": 1,
  "attempt_no": 1,
  "stt_status": "예시",
  "reject_reason": null,
  "error_code": null,
  "stt_text": null,
  "metrics": null,
  "session_status": "preparing",
  "current_order_no": 1,
  "all_answered": true
}
```

오류: INVALID_STATE, ORDER_MISMATCH, ANSWER_PENDING, AUDIO_TOO_SHORT, AUDIO_TOO_LONG, UNSUPPORTED_MEDIA, PAYLOAD_TOO_LARGE.

## U2 GET `/sessions/{session_id}/answers/{answer_id}`

HTTP 200. 

응답 예시:
```json
{
  "answer_id": "00000000-0000-4000-8000-000000000001",
  "order_no": 1,
  "attempt_no": 1,
  "stt_status": "예시",
  "reject_reason": null,
  "error_code": null,
  "stt_text": null,
  "metrics": null,
  "session_status": "preparing",
  "current_order_no": 1,
  "all_answered": true
}
```

오류: ANSWER_NOT_FOUND.

## U3 POST `/sessions/{session_id}/answers/{answer_id}/retry-stt`

HTTP 202. 

응답 예시:
```json
{
  "answer_id": "00000000-0000-4000-8000-000000000001",
  "order_no": 1,
  "attempt_no": 1,
  "stt_status": "예시",
  "reject_reason": null,
  "error_code": null,
  "stt_text": null,
  "metrics": null,
  "session_status": "preparing",
  "current_order_no": 1,
  "all_answered": true
}
```

오류: INVALID_STATE.

## E1 POST `/sessions/{session_id}/submit`

HTTP 202. 

응답 예시:
```json
{
  "session_id": "00000000-0000-4000-8000-000000000001",
  "status": "preparing",
  "scenario_id": "예시",
  "question_count": 1,
  "current_order_no": 1,
  "all_answered": true,
  "prepare": null,
  "latest_evaluation_status": null,
  "created_at": "2026-11-06T08:00:00Z",
  "updated_at": "2026-11-06T08:00:00Z"
}
```

오류: INVALID_STATE, NOT_ALL_ANSWERED.

## E2 GET `/sessions/{session_id}/result`

HTTP 200. AI를 호출하지 않는다. 저장값만 반환

응답 예시:
```json
{
  "session_status": "preparing",
  "evaluation_status": null,
  "run_no": null,
  "result": null,
  "answers": [
    {
      "order_no": 1,
      "question_id": "예시",
      "question_type": "예시",
      "question_text": "예시",
      "is_scored": true,
      "stt_text": "예시",
      "metrics": {
        "duration_sec": 1,
        "speech_sec": 1,
        "word_count": 1,
        "wpm": 1,
        "articulation_wpm": null,
        "long_pause_count": 1,
        "observed_filler_per100": null,
        "metrics_version": "예시"
      }
    }
  ],
  "error_code": null,
  "graded_at": null
}
```

오류: INVALID_STATE.

## E3 POST `/sessions/{session_id}/regrade`

HTTP 202. 

응답 예시:
```json
{
  "session_id": "00000000-0000-4000-8000-000000000001",
  "status": "preparing",
  "scenario_id": "예시",
  "question_count": 1,
  "current_order_no": 1,
  "all_answered": true,
  "prepare": null,
  "latest_evaluation_status": null,
  "created_at": "2026-11-06T08:00:00Z",
  "updated_at": "2026-11-06T08:00:00Z"
}
```

오류: INVALID_STATE.

## X1 POST `/sessions/{session_id}/chat`

HTTP 501. 

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

## 폴링 흐름

설정 → POST /sessions → GET /sessions/{id} 반복 → ready → POST /start
→ GET /current → 음성 재생 → 녹음 → POST /answers → GET /answers/{answer_id} 반복
→ done 확인 후 GET /current → 전체 답변 저장 → POST /submit
→ GET /result 반복 → evaluation_status=done이면 저장된 결과 표시.
rejected/failed는 현재 문항에서 재녹음/재처리한다. prepare_failed는 같은 세트로 준비 재시도한다.
grading_failed는 저장된 전체 답변으로 regrade한다. TTS 오류 시 다른 음성 엔진으로 대체하지 않는다.
