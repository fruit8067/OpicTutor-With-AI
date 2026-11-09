# OpicTutor 프런트엔드

## ngrok으로 외부 기기에서 접속하기

> AI-assisted: 이 절은 Claude(Anthropic)의 도움으로 작성되었습니다.

터널은 **Vite(5173) 하나만** 엽니다. Vite가 `/api/*`와 `/media/*`를 로컬 FastAPI(`127.0.0.1:8000`)로 전달하므로
프런트와 API가 같은 오리진이 되고 CORS 설정을 바꿀 필요가 없습니다. DB와 FastAPI는 계속 `127.0.0.1`에만 열려 있습니다.

1. ngrok 설치 후 토큰을 **PC 전역 설정**에 한 번 저장합니다(레포에 커밋 금지): `ngrok config add-authtoken <토큰>`
2. 평소처럼 DB(`docker compose up -d db`), FastAPI, 워커(`python -m app.worker`)를 실행합니다.
3. 프런트를 ngrok 모드로 실행합니다: `npm run dev:ngrok`
   - `VITE_API_BASE`가 `/api/v1`(같은 오리진)로 고정되고, ngrok 도메인 Host 허용, HMR 443 포트가 켜집니다.
   - 백엔드 주소가 다르면 `OPIC_BACKEND_URL=http://127.0.0.1:8001 npm run dev:ngrok` 처럼 바꿉니다.
4. 다른 터미널에서 `ngrok http 5173` 실행 후 표시된 `https://….ngrok-free.app` 주소로 접속합니다.
   - 무료 도메인은 첫 접속 때 경고 페이지가 한 번 나옵니다. **Visit Site**를 누르면 이후 요청은 통과합니다.
     API 요청에는 `ngrok-skip-browser-warning` 헤더를 붙여 두었습니다.
   - HTTPS로 접속하므로 휴대폰에서도 마이크 권한(getUserMedia)이 동작합니다.

주의
- 주소를 아는 누구나 회원가입·채점을 할 수 있고, 채점마다 LLM·임베딩 크레딧이 소모됩니다. 시연이 끝나면 터널을 닫으세요.
  필요하면 ngrok traffic policy의 Basic Auth로 접근을 제한합니다.
- STT(Whisper)는 이 PC의 CPU에서 돌기 때문에 동시 사용자가 많으면 대기 시간이 늘어납니다.
- 기존 `npm run dev`(로컬 모드)는 동작이 바뀌지 않습니다(프록시만 추가, API 주소 기본값 그대로).

---

# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend enabling type-aware lint rules by installing `oxlint-tsgolint` and editing `.oxlintrc.json`:

```json
{
  "$schema": "./node_modules/oxlint/configuration_schema.json",
  "plugins": ["react", "typescript", "oxc"],
  "options": {
    "typeAware": true
  },
  "rules": {
    "react/rules-of-hooks": "error",
    "react/only-export-components": ["warn", { "allowConstantExport": true }]
  }
}
```

See the [Oxlint rules documentation](https://oxc.rs/docs/guide/usage/linter/rules) for the full list of rules and categories.
