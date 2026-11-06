// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// OWNER: frontend (contracts.yaml ownership)
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import App from './App.tsx';

// 개발용 mock 서버(src/__dev__/, 커밋하지 않음). VITE_USE_MOCK=1일 때만, 파일이 있을 때만 불러온다.
const mocks = import.meta.glob('./__dev__/mockServer.ts');

async function boot() {
  if (import.meta.env.VITE_USE_MOCK === '1' && mocks['./__dev__/mockServer.ts']) await mocks['./__dev__/mockServer.ts']();
  createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>);
}
void boot();
