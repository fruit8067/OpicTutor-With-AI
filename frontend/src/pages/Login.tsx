// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// OWNER: frontend (contracts.yaml ownership)
// 더미 로그인: 닉네임은 화면 표시에만 쓰고 서버로 보내지 않는다. 비밀번호 없음.
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shell } from '../components/Shell';
import { loadNickname, saveNickname } from '../lib/session';

export default function Login() {
  const nav = useNavigate();
  const [nick, setNick] = useState(loadNickname());
  return (
    <Shell>
      <section style={{ maxWidth: 440, margin: '6vh auto 0', display: 'grid', gap: 20 }}>
        <h1>모의 인터뷰를 시작해요</h1>
        <p className="muted">진행자가 8개 질문을 영어로 묻고, 끝나면 답변 전체를 보고 예상 수준과 연습 방향을 알려 드려요.</p>
        <form onSubmit={(e) => { e.preventDefault(); saveNickname(nick.trim()); nav('/setup'); }} style={{ display: 'grid', gap: 16 }}>
          <label className="field">
            <span>닉네임 (선택)</span>
            <input className="input" value={nick} onChange={(e) => setNick(e.target.value)} maxLength={20} autoComplete="nickname" autoFocus />
          </label>
          <button className="btn" type="submit">들어가기</button>
        </form>
        <p className="notice notice-warn">실제 로그인이 아닌 데모예요. 닉네임은 이 브라우저 화면에만 표시되고 서버로 보내지 않아요.</p>
      </section>
    </Shell>
  );
}
