// AI-assisted: Vite 골격을 OpenAI Codex로 구성했습니다.
// 후속 수정: ngrok 모드(프록시·allowedHosts·HMR)는 Claude(Anthropic)의 도움으로 작성되었습니다.
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// 백엔드(FastAPI)는 로컬에만 열어 두고, Vite가 /api·/media를 대신 전달한다.
const BACKEND = process.env.OPIC_BACKEND_URL ?? 'http://127.0.0.1:8000'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // `npm run dev:ngrok`: ngrok 터널 1개로 프론트·API를 같은 오리진에서 제공한다(CORS 불필요).
  const ngrok = mode === 'ngrok'
  return {
    plugins: [react()],
    // ngrok 모드에서는 API 주소를 같은 오리진 상대 경로로 고정한다. client.ts가 API_ORIGIN을 window.location.origin으로 잡는다.
    define: ngrok ? { 'import.meta.env.VITE_API_BASE': JSON.stringify('/api/v1') } : undefined,
    server: {
      proxy: {
        '/api': { target: BACKEND, changeOrigin: true },
        '/media': { target: BACKEND, changeOrigin: true },
      },
      // Vite는 모르는 Host 헤더를 차단하므로 ngrok 도메인을 항상 허용한다.
      allowedHosts: ['.ngrok-free.app', '.ngrok-free.dev', '.ngrok.app', '.ngrok.dev', '.ngrok.io'],
      // 브라우저는 https://<도메인>:443으로 접속하므로 HMR 웹소켓도 443으로 붙게 한다.
      hmr: ngrok ? { clientPort: 443 } : undefined,
    },
  }
})
