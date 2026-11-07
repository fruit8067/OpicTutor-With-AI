# C 요구사항·FLOWCHART 감사와 해결

2026-11-07 KST. AI-assisted (OpenAI Codex). 기준은 REQUIREMENTS_v2, PROJECT_REQUIREMENTS, FLOWCHART, API_SPEC, contracts v8이다. 기존 구현자의 **자체 감사**이며 M3 이후 별도 대화에서 수행할 독립 reviewer/M4를 대신하지 않는다.

## 판정과 증거의 범위

이번에 재현한 코드 위반은 수정하고 재검증했다. 실제 OmniVoice 자산과 A/B HTTP·PostgreSQL·워커를 연결한 C 화면의 8문항 저장/결과 표시도 통과했다. 실제 사람 마이크·STT/LLM 품질·M2/M3/M4 완료는 미검증 조건으로 남긴다.

- [고정 감사 기록](compliance/c-audit-2026-11-07.json): TTS29개, 녹음 Node4개, 기존 Chromium15시나리오, 추가 경계11시나리오 통과. 서로 중복되는 흐름을 합쳐 정확도나 독립 표본 수로 표시하지 않는다.
- [실제 연결 기록](compliance/c-runtime-2026-11-07.json): 실제 음성242개 반입, 실제 미디어206 응답17개, answers8/evaluations1/ai_requests0, 순서9·done. STT 전사 생성과 평가 추론만 대역이다. 테스트용 fake microphone·8배속 재생을 사용했다.
- 실제 voice `ac3049e033`: 질문222/대사4/e2e16, 20,842,506바이트, 측정2,584.18초. 작업 text_sha1 불일치0, missing_pilot=[]. 다른 작업자의 음성 커밋 dd440e3을 보존했으며 이번 감사가 Colab을 재실행한 것은 아니다.
- A/B128 passed/skip0/14.34초. 공개 함수64·TTS 함수5·API 모델29·경로17 차이0. build/lint 및 ownership·이식성 단위6개 통과. A/B 조합의 anyio assertion-rewrite 경고1건은 남아 있다.

## 요구사항·흐름 대조표

| 기준·단계 | 확인 근거 | 판정·한계 |
| --- | --- | --- |
| F0: 더미 로그인·닉네임은 표시용 | 키보드 로그인, API 클라이언트 생성 payload 대조 | 통과. 실제 인증 기능 추가 없음 |
| F0/§10: 마이크 검사·테스트 녹음은 로컬 | Chromium 사전 검사·업로드0, 사람 목소리 없이 fake device 사용 | 서버로 보내지 않음 확인. 실제 장치/권한 UI는 후속 |
| F0: 선택 시나리오·생성 재전송 | 같은 입력 재시도 키 유지, 시나리오 변경 시 새 키, 요청 중 선택 비활성화 | C09 보강·브라우저 확인 |
| F0: 설정 변경은 이전 세션 취소 후 | ready/prepare의 취소 네트워크 실패·성공 재현 | C01 해결. 실패 시 ID/화면 보존 |
| F0/FLOWCHART: 전체8문항·순서 확정 | 실제 DB 스냅샷·시작·시험 종료 후 같은 question_id 목록 | 연결 검증 통과 |
| F0/F6: 전체 질문·대사 연결 후 ready | 실제 import/claim/prepare, 파일 제거 후 prepare_failed | 통과. 단순202를 준비 완료로 취급하지 않음 |
| F0: 같은 세트 재준비·늦은 작업 무시 | 실제 임시 DB에서 누락 복구·attempt2·attempt1 무시 | 통과 |
| F6: 변경 음성 반입이 기존 세션을 보존 | 기존 실패 회귀의 파일 SHA256 변경, v8 수정 뒤 파일/DB 경로 보존 | C04 해결. CR#30 선승인 |
| F6: ZIP·manifest·버전·누락·손상 검사 | 잘못된 경로/JSON/items/MP3·해시·중복·DB 실패 단위 검증 | C05 해결. 활성화 전에 거부 |
| F6: 기존 평면 경로·동일 폴더 재등록·stale | 레거시 manifest, 재등록, 문장 변경·누락 내보내기 회귀 | v8 호환 확인 |
| F6: 파일이 비어 있으면 시작 준비 불가 | 0바이트 등록 파일의 status/prepare 회귀 | C06 해결 |
| F1/F7: 질문 음성·캐릭터·재생 후 녹음 | 실제 Host·HTML audio·실제 음성 URL, 마이크 활성화 검사 | 통과. 텍스트/Web Speech 대체 없음 |
| F6: 자동 재생 차단·음성 실패 | blocked/404 및 필수 대사 재시도 | 같은 음성 재생 전 진행 차단 확인 |
| F1: 다시 듣기 제한 | UI는 replay_count/replay_limit을 사용, Q2 서버 검사와 A/B 회귀 | 정적 대조+서버 회귀. 별도 브라우저별 제한 차이는 후속 |
| F1/F2: 녹음 시작·종료·최대 시간 | 실제 MediaRecorder 경계11개와 Node4개 | C03 해결. 비동기 오류·장치 해제 시 부분 Blob 업로드0 |
| F2: 최소 길이·무음 거부 | 기존 Chromium 짧은 녹음 검증·A/B 오디오 판정 회귀 | 통과. 실제 환경 잡음 임계값의 품질은 후속 |
| §9: 업로드 실패는 같은 녹음 재전송 | 네트워크 실패 후 같은 client_request_id, Blob 보관·유실 경고 | 통과 |
| F1/FLOWCHART: 202는 STT 완료가 아님 | 브라우저15개와 실제 worker/DB 연결, 서버 답변 done·순서 확인 | 통과. 실제 연결의 전사 생성만 대역 |
| F1: processing 새로고침 | 같은 pending_answer 재폴링, 늦은 응답 무시 | 통과 |
| §5: 문항 조회 실패는 남은 문항 없음이 아님 | all_answered=false/question=null에서 submit1회 재현 → 수정 후0 | C02 해결 |
| F3: 마지막 답변 저장 후 제출·평가 | 실제 답변8/평가1, worker claim/lease/complete 10작업 done | 연결 검증 통과. 평가 추론 대역 |
| F4: 결과 조회·새로고침은 AI 호출 없음 | 실제 결과 reload 후 evaluations1/ai_requests0 유지 | 통과 |
| F4/§9: 평가 실패 후 재평가 | Chromium grading_failed→재평가 대기 및 A/B 재평가 회귀 | 경계 검증 통과. 실제 Pickle 품질은 미완료 |
| F4: IH·잠정IM2·IM보류·근거부족·결측 | 결과5종, 잠정 라벨·자기소개 제외·서술 FACT·카드 구분 | 화면 확인. 사람/독립 평가 정확도는 미측정 |
| F7: idle/speaking/listening/processing | 실제 Host 상태 라벨·화면·음량 그래프 연결 | 확인 |
| F7/접근성: reduced-motion | body transform 고정·listening animate 제거 | Chromium 설정에서 확인 |
| 접근성: 키보드·포커스·AA | 키보드8문항, 포커스 링·상태 알림 대조, 대비 수치 계산 | C10 해결. 전체 스크린리더/장치 행렬은 후속 |
| §7: 화면 이탈 후 폴링/마이크 정리 | 늦은 ready 응답 무시, 늦은 권한 응답의 track live→ended | C07/C08 해결·보강 |
| §10: 로컬 API/DB·키·상대 경로 | loopback HTTP, 설정/번들 점검·이식성 단위 검사 | 구성된 실제 키의 프런트 번들 포함0. 전체 Git 이력 비밀 감사는 기존 감사와 별도 |

## 발견 사항과 수정 전후

| ID·심각도 | 위치·재현 | 수정·재검증 |
| --- | --- | --- |
| C01 🔴 | `frontend/src/lib/actions.ts`, Prepare/Ready: 취소 요청을 네트워크 실패로 만들면 세션 ID가 삭제되고 setup 이동 | 성공/확인된 없음에만 삭제. 두 화면 모두 같은 세션 보존·오류 표시·성공 후 삭제 확인 |
| C02 🟠 | `pages/Exam.tsx`: current의 question=null/all_answered=false 응답에서 submit 호출1 | all_answered만 종료 근거로 사용. 문항 누락은 오류·재조회, submit0 |
| C03 🟠 | `lib/recorder.ts`, Setup/Exam: MediaRecorder 생성 예외로 pageerror와 녹음 중 고정 | 생성·start·비동기 error·track ended의 거절/정리 및 같은 문항 재시도. Node4/브라우저 재현 통과 |
| C04 🔴 | `scripts/import_tts.py`: 같은 voice/ref의 다른 text_sha1 반입 시 이전 파일 SHA256 변경 | CR tts-host-01→PR#30/main→v8 해시별 경로. 이전 세션 파일/URL·레거시 경로 보존 확인 |
| C05 🟠 | `app/tts/assets.py`: list/items=null/id=[] manifest에서 AttributeError/TypeError | 비정상 index는 사용 불가 처리, 반입 오류는 활성화 전 거부 |
| C06 🟠 | `app/tts/prepare.py`: 등록 파일을0바이트로 만들어도 is_file만 통과 | 빈 파일을 누락으로 분류, ready 연결 차단 회귀 통과 |
| C07 🟠 | `pages/Setup.tsx`: 권한 응답을 지연하고 뒤로 이동하면 늦은 stream의 track이 live | 이탈 후 반환 stream stop. 같은 재현에서 ended |
| C08 🟠 | `usePoll.ts`, Boot/Ready/Result: 늦은 응답·cancelled 처리 누락을 정적 확인 | 이탈한 callback 무시·cancelled→setup. 늦은 ready 응답과 cancelled 결과 재현 통과 |
| C09 🟠 | `pages/Setup.tsx`: reqId가 시나리오 변경에도 고정인 것을 정적 확인 | 동일 입력 재시도는 유지, 다른 입력은 새 키. 요청 중 선택 잠금. 브라우저 확인 |
| C10 🟠 | `index.css`, `Host.tsx`: 작은 안내 글자 대비3.165~3.729:1, 녹음/REC 문구도 점검 | 색 계열 유지·안내/녹음 문구 최소4.595/4.712:1(검사 배경4종). 비활성 컨트롤은 별도 기준 |

이 표의 🔴/🟠는 발견 당시 심각도다. 위 재현 사례는 수정 후 통과했으며, 모든 잠재 결함이 없다는 보장은 아니다. API·DB가 조기 제출을 막던 C02도 잘못된 UI 요청이므로 수정했다.

실제 음성·TTS 코드 PR#19는 필수 ownership 성공과 최신 main 확인 후 rebase 방식으로 main 832f898에 병합됐다. 프런트 PR#24는 최신 main으로 rebase/build/lint한 Draft이며 앞선 A/B M2 병합 순서를 유지한다.

## 재현 방법과 남은 조건

PowerShell/bash에서 가상환경을 활성화하고 역할 저장소 기준으로 실행한다.

```text
cd backend
python -m pytest tests/test_tts_pipeline.py -q
```

frontend 역할 저장소에서는 `node --test frontend/tests/recorder.test.ts`, frontend 폴더에서는 `npm run build`, `npm run lint`를 실행한다. 미병합 Host는 ignored 개발 resolver로 명시적으로 연결하며 다른 역할 운영 소스를 복사하지 않는다. API 대역은 계약대로 `src/__dev__/`에만 둔다.

실제 HTTP/DB/음성 연결 재현은 ignored resolver로 실제 C Host를 로드하는 로컬 frontend를 띄운 뒤 저장소 루트에서 다음 도구를 실행한다. PostgreSQL 계정에 임시 DB 생성/삭제 권한과 설치된 Chromium/Playwright가 필요하다. 기존 DB와 실제 자산은 reset/삭제하지 않는다.

```text
python docs/compliance/verify_c_runtime.py --workspace .. --frontend-url http://127.0.0.1:5175 --report docs/compliance/c-runtime-local.json
```

실제 사람 마이크·Whisper/LLM을 모두 사용하는 제품 완주, Pickle 할당량 회복 후 남은35시험·반복/함정, 브라우저/장치/스크린리더 행렬, M2/M3/M4는 남아 있다. 실제 음성 파일 미제공은 이번에 해소됐지만 음질을 사람이 청취해 승인한 것으로 표시하지 않는다. 재현 도구의 경계 대역을 제거한 결과로 오해하지 않도록 한다.
