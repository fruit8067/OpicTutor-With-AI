# session-api M2

## 상태
API와 출제 빌더 구현, 검증 진행 중 (2026-11-06 KST).
브랜치는 agent/data-layer 위에 쌓음. 소유권 비교 기준은 agent/data-layer.

## 완료한 것
| 엔드포인트 | 구현 |
| --- | --- |
| A1 health / A2 scenarios / A3 host-lines | 완료 |
| S1 생성 / S2 조회 / S3 준비 재시도 / S4 취소 / S5 시작 | 완료 |
| Q1 현재 문항 / Q2 다시 듣기 | 완료 |
| U1 업로드 / U2 답변 조회 / U3 STT 재시도 | 완료 |
| E1 제출 / E2 결과 / E3 재평가 | 완료 |
| X1 채팅 | 계약대로 501 |

## 실행 방법
PowerShell: `cd backend; .venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
bash: `cd backend && .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
PowerShell 예시: `Invoke-RestMethod http://127.0.0.1:8000/api/v1/health`
세션: `$body = @{client_request_id=[guid]::NewGuid().ToString(); scenario_id='default'; mic_check_passed=$true} | ConvertTo-Json`
후 `Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/sessions -ContentType application/json -Body $body`.
bash: `curl -X POST http://127.0.0.1:8000/api/v1/sessions -H 'Content-Type: application/json' -d '{"client_request_id":"demo-1","mic_check_passed":true}'`
업로드: `curl -F order_no=1 -F client_request_id=answer-1 -F duration_ms=3000 -F 'audio=@answer.webm;type=audio/webm' http://127.0.0.1:8000/api/v1/sessions/SESSION_ID/answers`.
PowerShell 7: `Invoke-RestMethod -Method Post -Uri "$base/sessions/$sid/answers" -Form @{order_no=1;client_request_id=[guid]::NewGuid().ToString();duration_ms=3000;audio=Get-Item ./answer.webm}`.

## 공개 함수
계약 엔드포인트 전부. SQL을 직접 호출하지 않고 app.db에 위임한다.
coverage는 실제 선택된 채점 문항의 태그 합집합과 시나리오 경고로 저장한다.

## 알려진 문제 및 다른 에이전트에게 요청
- corpus M1의 Q000·시나리오·태그가 필요하다. 없으면 SCENARIO_UNAVAILABLE, 임의 문항 대체 없음.
- tts-host가 stub을 구현해야 문항 재생 URL과 준비 완료가 동작한다.
- 실제 PostgreSQL/API 연결은 검증했으나 실제 음성 STT·AI 완주는 다른 PC 구현이 필요하다.
- 모든 DB 함수가 계약에 존재하므로 추가 DB 함수 CR은 필요 없음.
- 업로드의 크기 제한은 UploadFile 스트림을 64KB씩 읽어 적용한다. ASGI 서버가 multipart를 파싱할 때의
  임시 스풀은 Starlette가 담당하며 인터넷 배포용 프록시 제한은 범위 밖이다.

## 실행 확인
- pytest tests/test_exam_builder.py tests/test_api_upload.py: 12 passed.
- FastAPI OpenAPI: 계약의 API 경로 17개, schemas 생성 성공.
- 동일 업로드 키를 STT 순서 전진 후 재전송해도 기존 답변을 돌려주도록 최종 상태 판정을 DB에 위임.
- 실제 PostgreSQL + TestClient로 세션 생성/중복 생성→음성 asset 링크→start→8개 업로드·중복·순서 검사
  → STT 완료 콜백→submit 2회→결과 조회 10회(평가 호출 증가 0)를 검증했다.
  이 연결 테스트는 TTS URL과 STT 계산만 명시적인 fixture로 대체하며 실제 음성·AI 완주가 아니다.
- 1.5초/125초 초과/11MB/text/plain/빈 파일 거부와 임시 파일 정리, 다른 세션 답변 접근 거부 확인.
- backend 전체 테스트: 21 passed, skip 0 (2026-11-06 KST).
- 실제 uvicorn HTTP: /health 200(ready=false), /docs 200, /openapi.json 200.

