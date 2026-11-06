# session-api M2

## 상태
API와 출제 빌더 구현, M1 의존성 및 실제 서비스 검증 대기 (2026-11-07 KST).
CR session-api-01/contracts v5 main 90e7835 기준 자기 증분만 있는 독립 브랜치다. 소유권은 기본 origin/main 기준이다.

## 측정값
이번 독립 API 경계 검증 19 passed(0.50초). 생성 재전송의 원본 변경 내성 및 DB 접수 후 파일 rename 실패/재전송 복구를 추가했다. A/B 메모리 조합 검증은 임시 전용 DB에서 101 passed(5.37초)이며 실제 C·provider·마이크 완주와 구분한다.
아래 12/21/25개 테스트 결과는 과거 A 조합의 기록이다. 새 독립 브랜치에서는 data-layer M1 구현 main 반영 전까지 실제 DB 연결 검사를 완료로 세지 않는다. 실제 TTS/STT 업로드 지연·LLM 비용은 미측정이다.

## 핵심 흐름 보강
동일 client_request_id는 저장 세션을 먼저 조회하므로 생성 후 코퍼스가 바뀌어도 같은 세션을 200으로 반환한다. 새 요청은 그대로 출제 검사를 한다. 원음 rename 실패는 같은 Blob/키 재전송으로 기존 answer_id의 파일을 복구하고 STT를 멱등 재시도한다. 다른 Blob이나 이미 저장된 원음을 덮어쓰지 않는다. 파일 복구 직후 DB retry가 실패해도 다음 재전송으로 이어갈 수 있다.

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
- 완료 조건 재점검: 새 업로드는 파일 읽기·저장 전에 상태/순서/처리 중 답변을 확인한다.
  기존 모든 시도의 client_request_ids로 재전송을 구분하여 과거 시도나 제출 이후 재전송도 200을 유지한다.
  최종 판정은 계속 db.create_answer 트랜잭션이 담당한다.
- 추가 회귀 검증 후 backend 전체 테스트: 25 passed, skip 0 (PostgreSQL 포함).
- 실제 uvicorn HTTP: /health 200(ready=false), /docs 200, /openapi.json 200.
