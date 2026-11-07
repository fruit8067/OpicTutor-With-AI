# frontend 인수인계

> AI-assisted: this handoff was written with help from Claude (Anthropic).

## 상태

M2 코드 구현·후속 검증 완료, 실제 음성/통합 대기 (2026-11-07) — PR "[frontend] M2". main `5bca38a` 기준. tts-host(`features/host`) 병합 전에는 bootstrap stub이 들어 있어서
**실제 음성 재생은 tts-host PR 병합 후** 동작한다(stub `play()`가 오류를 던짐 → 화면은 "다시 재생"을 보여 줌). mock 완주는 tts-host 브랜치의 host 파일을 겹쳐서 확인했다.

## 디자인 방향

조용한 면접 부스: 차가운 종이 바탕(#F5F7F6)과 청록 잉크(#1E3436·#2C6E68) 한 계열로 긴장을 낮추고, 빨강(#C8463F)은 "지금 녹음 중"에만 써서 상태를 한눈에 구분한다.
시험 화면은 왼쪽 진행자·오른쪽 질문과 하나뿐인 큰 마이크 원, 결과는 카드 나열 대신 목차가 있는 보고서 문서로 읽히게 했다(글꼴 IBM Plex Sans KR 하나).

## 화면과 호출 API

| 경로 | 화면 | API |
|---|---|---|
| `/` | 상태 복구(라우팅 표대로 이동) | S2 |
| `/login` | 더미 로그인(닉네임만, 서버로 안 보냄) | — |
| `/setup` | 마이크 권한·음량·3초 테스트(업로드 안 함)·시나리오 선택 | A2, (S2), S1 |
| `/prepare` | 준비 진행률, 실패 목록, 같은 세트로 다시 준비 / 설정 바꾸기 | S2(2초), S3, S4 |
| `/ready` | 안내 + [시험 시작](unlock 후) | S2, S5 |
| `/exam` | 문항 상태 머신(재생→녹음→업로드→처리→서버 확인 후 다음) | Q1, Q2, U1, U2(2초), U3, E1 |
| `/result` | 채점 중 / 평가 실패(다시 평가) / 보고서 | E2(2초), E3 |

라우팅 표: preparing·prepare_failed → /prepare, ready → /ready, in_progress → /exam, submitted·grading·grading_failed·done → /result,
cancelled·404 → session_id 삭제 후 /setup. 브라우저에는 `session_id`와 표시용 닉네임만 저장(localStorage, try/catch).

지켜진 규칙
- 업로드 202만으로 이동하지 않음: U2에서 `stt_status=done` **그리고** `current_order_no > order_no`(또는 `all_answered`)일 때만 `next` 대사 → Q1
- 새로고침 복구: Q1의 `pending_answer`(queued/processing)면 그 답변을 다시 폴링, failed면 [다시 처리], rejected면 재녹음
- 재생 중 녹음 불가, 다시 듣기는 `replay_count < replay_limit`일 때만, 녹음 형식 webm/opus → ogg → mp4
- 2초 미만·거의 무음은 업로드하지 않고 `say_again` 재생 후 재녹음, 120초에 자동 종료
- 업로드 네트워크 실패: Blob 보관, 1·2·4초 자동 재전송 3회(같은 client_request_id) → [다시 보내기] + 새로고침 유실 경고(beforeunload)
- speechSynthesis 미사용. 문항·순서를 클라이언트가 고르거나 계산하지 않음. 결과 등급을 계산·보정하지 않음
- 결과: 안내 띠(전사 기반·채점 대상 수·자기소개 제외·확인 불가 답변), 예상 등급 + IM 잠정 진단 라벨(항상 함께), IM 세분화 보류 화면,
  insufficient_evidence 화면, 판단 근거 3단, FACT 서술 4영역(점수·막대 없음), fact_evidence 배지(관찰 기회 없음은 중립색), 관찰 범위 표,
  지속/흔들림 2열, 연습 카드(correction/practice 구분·success_condition), 문항별 상세(자기소개는 "채점 제외 · 연습 피드백"으로 맨 아래), 참고(추가 연습 질문·속도 관찰 접이식·한계·disclaimer·rubric_version)
- 키보드만으로 완주(포커스 링, 주요 버튼 autoFocus), aria-live 상태 알림, 버튼 aria-label

## mock 서버 사용법 (커밋하지 않음: `frontend/src/__dev__/`)

```bash
cd frontend
VITE_USE_MOCK=1 npm run dev          # PowerShell: $env:VITE_USE_MOCK=1; npm run dev
```
`src/__dev__/mockServer.ts`는 fetch를 가로채 contracts 스키마 그대로 응답한다. 파일이 없으면 자동으로 건너뛴다(`import.meta.glob`).
시나리오는 브라우저 콘솔에서 `localStorage.setItem('mock.flags', '...')` 후 새로고침:
`prepare_fail`, `reject_once`(3번), `stt_fail_once`(5번), `upload_fail`(2번), `grading_fail`, `slow_grading`,
`result=ih|im2|im_held|insufficient|missing2`. mock 파일이 필요하면 PC-C 담당에게 받거나 이 handoff의 규칙대로 다시 만든다.

## 실제 서버 연결

`VITE_API_BASE`(기본 `http://127.0.0.1:8000/api/v1`). 음성 URL(`/media/tts/...`)은 같은 서버 origin 기준으로 붙인다(`mediaUrl`).
```bash
VITE_API_BASE=http://127.0.0.1:8000/api/v1 npm run dev
```

## 측정값 / 실행 확인

- `npm run build` 경고 0, `npx oxlint src` 경고 0, `tsc -b` 오류 0
- Playwright(가짜 마이크 장치) mock 완주: 일반(IM2) / prepare_fail+reject_once+upload_fail+stt_fail_once+grading_fail+IM 보류 /
  insufficient / 결측 2개 / IH — 결과는 PR 본문 참조

## 알려진 문제

- CR frontend-01: `types.ts`의 `tier` 타입이 문자열 리터럴로 생성됨 → `Result.tsx tierOf()`에서 우회
- `lib/player.ts`: bootstrap stub에 `unlock`이 없어 선택적 호출로 감쌌다. tts-host 병합 후에도 그대로 동작
- Google Fonts를 못 받는 환경에서는 시스템 한글 글꼴로 대체된다
- 실제 마이크·실서버 완주는 M3(integrator)에서 확인

## 다른 에이전트에게 요청

- bootstrap/orchestrator: CR frontend-01 검토
- tts-host: `useTtsPlayer`의 이전 재생 결과 무시 수정(agent/tts-host `0d38581`)이 있어야 개발 모드(StrictMode)에서 첫 문항 재생이 실패하지 않는다


## 2026-11-07 C 후속 보강 (OpenAI Codex)

기존 구현과 Claude 출처를 보존했다. 진행자 greeting/next/say_again/finish도 재생 성공 뒤에만 진행하도록 수정했다. 실패·자동 재생 차단 시 같은 음성의 명시적 재시도를 제공하며 녹음/다음 문항/submit으로 넘어가지 않는다. 화면 이탈 후 업로드 재시도/진행을 막았다. 준비 재시도가 즉시 ready를 반환하면 해당 화면으로 이동한다. 설정의 기존 세션 조회가 네트워크 오류이면 새 세션을 만들지 않는다(SESSION_NOT_FOUND만 새 생성 허용).

- `cd frontend; npm ci; npm run build; npm run lint`: build 성공, lint 경고0.
- Chromium 1280×900에서 **15개 시나리오 통과 / pageerror0 / 유료 요청0**. `frontend/verification/browser-2026-11-07.json`에 결과를 기록한다.
- 키보드 로그인/마이크 사전 녹음(업로드0), 키보드 8문항 녹음·202 처리 대기·완료 후 이동·마지막 음성 후 submit1회를 확인했다. 첫 업로드 네트워크 실패의 재전송은 같은 client_request_id를 유지했다.
- 질문/대사 재생 실패와 자동 재생 차단, 짧은 녹음의 업로드 거부, processing 새로고침 복구, 준비 실패/재시도, 재평가, 결과 IH/IM2/IM보류/근거부족/결측2문항 표시를 확인했다.
- 브라우저 검증은 API 대역·합성 tone MP3·Chromium fake microphone을 사용했다. 테스트 서버는 ignored `src/__dev__/vite.verify.ts`의 명시적 resolver로 tts-host 소유 Host/플레이어를 불러왔다. 다른 역할 소스를 이 브랜치에 복사하거나 stub을 성공으로 바꾸지 않았다. 실제 사람 마이크·OmniVoice 음질·실제 LLM 완료의 증거가 아니다.
- 시험/IM2 결과 화면을 시각 확인했다. 기존 종이/청록 디자인을 유지한다.

### 남은 조건

실제 OmniVoice ZIP 생성/반입과 실제 서버·마이크 연동, M2 병합 순서, M3 통합 후 별도 대화의 독립 reviewer가 남아 있다. mock 모듈은 계약대로 src/__dev__에만 두고 커밋하지 않는다. C 전체/제품 완료를 선언하지 않는다. CR frontend-01은 bootstrap의 별도 PR로 처리하며 공개 HTTP 형식을 바꾸지 않는다.

CR frontend-01은 PR #28/main 0c4ee09에서 해결됐다. 이 브랜치도 rebase한 뒤 Result의 unknown 캐스팅을 제거했다.


## C 요구사항·FLOWCHART 감사 (OpenAI Codex, 2026-11-07)

### 재현·수정

- 취소 네트워크 실패에도 session_id를 지우고 setup으로 이동: 브라우저에서 재현 후 취소 확인 성공/SESSION_NOT_FOUND에만 삭제하도록 수정. ready·prepare 화면에 오류를 표시하고 같은 세션에서 재시도한다.
- current 응답이 all_answered=false/question=null인데 submit: 실제 종료 요청1회를 재현. 현재 문항 조회 실패로 표시하고 다시 불러오며 submit0으로 수정했다.
- MediaRecorder 생성/시작 오류가 unhandled되고 녹음 중에 고정: 재현 후 Promise 거절·오류/장치 해제·빈 결과 정리, 동일 문항 재녹음으로 복구. 미완성 Blob은 업로드하지 않는다.
- 화면 이탈 뒤 늦게 승인된 마이크 스트림이 live로 남음: 재현 후 반환된 스트림을 바로 stop하며 ended를 확인했다. 늦은 상태 조회도 이전 화면으로 이동시키지 않는다.
- 설정의 동일 입력 재시도는 요청 키 유지, 시나리오 변경은 새 키를 사용하도록 보강했다. 요청 중 시나리오 변경은 막는다. 결과의 cancelled 상태도 세션을 지우고 setup으로 복구한다.

### 확인 결과

- 기존 브라우저15개 회귀 재실행 통과. 오류/취소/이탈/녹음 최대시간 경계11개 추가 통과(pageerror0). 늦은 마이크 해제와 설정 재시도 키 분리도 별도 Chromium 검증했다.
- `node --test frontend/tests/recorder.test.ts`: 생성 실패·비동기 오류·장치 해제·최대 시간4개 통과. Node24 기본 TypeScript 실행을 사용하며 제품 의존성을 추가하지 않았다.
- 실제 C Host/음성 + A/B HTTP/DB/워커를 연결한8문항 시험은 done/answers8/evaluations1/ai_requests0. 실제 OmniVoice 206 응답17개, 결과 새로고침 평가 추가0. STT 전사 생성과 평가 추론은 대역이며 실제 사람 마이크·LLM 품질 검증은 아니다.
- build/lint 통과. 새 음성 자산은 원격 tts-host에서 제공됐으며 실제 Colab 재실행을 이번 감사가 수행한 것으로 표시하지 않는다.

상세 요구사항 대조와 수정 전/후 증거는 `docs/C_REQUIREMENTS_VERIFICATION.md` 및 compliance 기록에서 관리한다. 독립 reviewer/M4로 표시하지 않으며 실제 마이크·공급자 품질·M2/M3 조건은 남아 있다.

추가 접근성 대조에서 작은 안내 글자의 대비가 배경에 따라3.165~3.729:1로 AA에 미달했다. 기존 색 계열을 유지하며 --ink-faint를 #586e70, 녹음 문구의 --rec를 #b83e37로 보정했다. 종이/흰색/안내/녹음 배경의 일반 텍스트 대비를4.5:1 이상으로 확인한다. disabled 요소는 별도 기준이다.


## 사용자 요청에 따른 C 구현 main 병합 (2026-11-07, OpenAI Codex)

A/B 선행 구현이 main에 병합된 뒤 최신 main으로 rebase했다. 사용자의 C 병합 요청에 따라 프런트 PR#24를 반영한다. build/lint와 녹음 Node4개를 다시 통과했고 기존 Chromium15·경계11·실제 C/AB HTTP/DB/OmniVoice8문항 검증은 보존한다. 실제 사람 마이크/공급자 품질·M3·독립 reviewer는 후속 조건이며 구현 병합을 제품 완료로 표시하지 않는다.


## 다른 기기 접속 수정 (2026-11-07, OpenAI Codex)

사용자가 본인/지인 외부 테스트 접속을 요청했다. API 기본값을 /api/v1로 바꾸고 Vite에서 /api·/media를 로컬 backend로 중계한다. 명시적 VITE_API_BASE 설정은 계속 우선한다. 다른 기기의 localhost로 API를 보내던 문제를 해결한다. 외부 실행 시 frontend 폴더에서 `npm run dev -- --host 0.0.0.0 --port 5173 --strictPort`를 사용하고 서버 IP의5173포트로 접속한다. 마이크는 외부 HTTP에서 제한되므로 HTTPS 안내를 보강했다.

검증은 build/lint/녹음 Node4개 통과, 실제 Vite 프록시 health200·DB ok·TTS Range206/1024바이트, 기본 API 같은 출처를 확인했다. 네트워크 바인딩은 실행 인자로 지정한다.
