# frontend 인수인계

> AI-assisted: this handoff was written with help from Claude (Anthropic).

## 상태

M2 완료 (2026-11-07) — PR "[frontend] M2". main `5bca38a` 기준. tts-host(`features/host`) 병합 전에는 bootstrap stub이 들어 있어서
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
