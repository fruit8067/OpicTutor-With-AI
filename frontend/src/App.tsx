// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// OWNER: frontend (contracts.yaml ownership)
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import Boot from './pages/Boot';
import Exam from './pages/Exam';
import History from './pages/History';
import Login from './pages/Login';
import Prepare from './pages/Prepare';
import Ready from './pages/Ready';
import Result from './pages/Result';
import Setup from './pages/Setup';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Boot />} />
        <Route path="/login" element={<Login />} />
        <Route path="/history" element={<History />} />
        <Route path="/setup" element={<Setup />} />
        <Route path="/prepare" element={<Prepare />} />
        <Route path="/ready" element={<Ready />} />
        <Route path="/exam" element={<Exam />} />
        <Route path="/result" element={<Result />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
