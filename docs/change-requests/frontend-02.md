# CR frontend-02 — ngrok 외부 접속 지원

> AI-assisted: written with help from Claude (Anthropic).

- 바꿀 항목: `frontend/vite.config.ts`, `frontend/package.json`(`dev:ngrok` 스크립트), `frontend/src/api/client.ts`(경고 우회 헤더), `frontend/README.md`
- 현재 → 제안: 프런트가 `http://127.0.0.1:8000/api/v1`을 직접 호출 → `npm run dev:ngrok` 모드에서 같은 오리진 `/api/v1`을 호출하고 Vite가 `/api`·`/media`를 로컬 FastAPI로 프록시
- 이유: ngrok으로 외부 기기에서 접속하면 브라우저가 자기 기기의 127.0.0.1을 호출해 실패한다. Vite 6+는 모르는 Host를 차단한다. 터널 1개·단일 오리진이면 CORS/`.env` 변경 없이 동작한다.
- 다른 소유자 파일 변경: 없음. `backend/app/main.py` CORS, `backend/.env.example`, `docker-compose.yml`은 그대로 둔다.
  `.env.ngrok`는 `check_ownership.py`가 `.env*`를 금지하므로 만들지 않고 Vite `--mode ngrok`의 `define`으로 대신한다.
- 영향 받는 에이전트: integrator(실행 문서에 "ngrok http 5173" 단계 추가 권장), 사용자(README 루트 실행 절 갱신은 소유자 없는 파일이라 별도 결정)
- 막힘 여부: 없음.

## 검증 (2026-11-09, Claude)

- `npm ci && npm run build` 통과.
- `npm run dev:ngrok` + 가짜 백엔드(127.0.0.1:8000)로 `Host: *.ngrok-free.app` 요청 시 `/api/v1/health`, `/media/tts/...` 프록시 200, 임의 Host는 Vite가 차단.
- ngrok 모드 `import.meta.env.VITE_API_BASE` = `/api/v1`, HMR `hmrPort = 443` 확인. 일반 `vite` 모드는 기본값(`http://127.0.0.1:8000/api/v1`) 유지.
- 미검증: 실제 ngrok 터널, 무료 도메인 경고 페이지 통과 후 `<audio>` TTS 재생, 휴대폰 LTE 환경 녹음·업로드. 실제 터널로 확인이 필요하다.
