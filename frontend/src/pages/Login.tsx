// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// 후속 수정: FastAPI 자체 이메일/비밀번호 인증 연동 및 Stitch sign_in 55:45 분할 화면 구현을 적용했습니다.
// OWNER: frontend (contracts.yaml ownership)
import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { loginUser, registerUser } from '../api/client';
import { ErrorNote, Logo } from '../components/Shell';
import { Host } from '../features/host/Host';
import { clearAuth, loadAuthUser, loadNickname, saveAuth, saveNickname } from '../lib/session';

type Mode = 'login' | 'register';

export default function Login() {
  const nav = useNavigate();
  const existingUser = loadAuthUser();
  const [mode, setMode] = useState<Mode>('login');
  const [email, setEmail] = useState(existingUser?.email ?? '');
  const [password, setPassword] = useState('');
  const [nickname, setNickname] = useState(existingUser?.nickname || loadNickname() || '');
  const [showPw, setShowPw] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res =
        mode === 'login'
          ? await loginUser({ email: email.trim(), password })
          : await registerUser({ email: email.trim(), password, nickname: nickname.trim() || email.split('@')[0] || '수험생' });
      saveAuth(res.token, res.user);
      nav('/setup');
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  const startGuest = () => {
    clearAuth();
    saveNickname(nickname.trim() || '게스트');
    nav('/setup');
  };

  return (
    <div className="signin-layout">
      {/* Left 55% Column: Brand & Educational Immersion Showcase (Stitch sign_in) */}
      <section className="signin-showcase" aria-label="서비스 소개">
        <div className="signin-glow signin-glow-top" aria-hidden="true" />
        <div className="signin-glow signin-glow-bottom" aria-hidden="true" />

        <header style={{ position: 'relative', zIndex: 1, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
          <Logo />
          <span className="chip chip-soft" style={{ gap: 6, fontWeight: 600 }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--primary)' }} aria-hidden="true" />
            대학생·취준생 특화 AI 스피킹
          </span>
        </header>

        <div style={{ position: 'relative', zIndex: 1, display: 'grid', gap: 22, margin: 'auto 0', padding: '1.5rem 0' }}>
          <div style={{ display: 'grid', gap: 10 }}>
            <h1 style={{ fontSize: 'clamp(1.85rem, 3vw, 2.5rem)', lineHeight: 1.22, letterSpacing: '-0.025em' }}>
              AI와 함께하는<br />오픽 실전 연습
            </h1>
            <p className="muted" style={{ fontSize: '1.02rem', maxWidth: '52ch' }}>
              실제 ACTFL 시험 환경 그대로, 진행자 린의 영어 질문과 실시간 음성 답변, FACT 기준의 정밀 진단 리포트를 경험해 보세요.
            </p>
          </div>

          <div className="signin-features">
            <div className="signin-feature-card">
              <div className="signin-feature-icon" style={{ background: 'var(--primary-surface)', color: 'var(--primary)' }} aria-hidden="true">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M9 11l3 3L22 4" /><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" /></svg>
              </div>
              <h2 style={{ fontSize: '0.95rem', fontWeight: 700 }}>실전형 8문항 세트</h2>
              <p className="muted" style={{ fontSize: '0.8125rem' }}>자기소개 워밍업부터 콤보·롤플레이까지 실제 시험 흐름 그대로 출제</p>
            </div>

            <div className="signin-feature-card">
              <div className="signin-feature-icon" style={{ background: 'var(--rec-wash)', color: 'var(--rec)' }} aria-hidden="true">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21" /></svg>
              </div>
              <h2 style={{ fontSize: '0.95rem', fontWeight: 700 }}>실시간 음성 답변</h2>
              <p className="muted" style={{ fontSize: '0.8125rem' }}>마이크 감도 점검 후 진행자 음성을 듣고 실제처럼 녹음·전사 분석</p>
            </div>

            <div className="signin-feature-card">
              <div className="signin-feature-icon" style={{ background: '#e0e7ff', color: 'var(--primary-hover)' }} aria-hidden="true">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M3 3v18h18" /><path d="M7 14l4-4 4 4 5-6" /></svg>
              </div>
              <h2 style={{ fontSize: '0.95rem', fontWeight: 700 }}>FACT 정밀 리포트</h2>
              <p className="muted" style={{ fontSize: '0.8125rem' }}>과제 수행·정확성·맥락·담화 구성 4대 영역 근거 인용과 맞춤 교정 카드</p>
            </div>
          </div>

          <div className="signin-banner">
            <div style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
              <div style={{ width: 72, height: 72, flex: 'none' }}>
                <Host state="idle" />
              </div>
              <div style={{ display: 'grid', gap: 4 }}>
                <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--success)', boxShadow: '0 0 0 4px rgba(16, 185, 129, 0.2)' }} aria-hidden="true" />
                  <strong style={{ fontSize: '0.875rem', color: '#fff' }}>Live Speech Engine & 진행자 린 대기 중</strong>
                </div>
                <span style={{ fontSize: '0.8125rem', color: 'rgba(255,255,255,0.82)' }}>
                  전사(STT) 및 발화 휴지기·속도 관측 엔진이 준비되어 있습니다.
                </span>
              </div>
            </div>
          </div>
        </div>

        <footer style={{ position: 'relative', zIndex: 1 }}>
          <p className="faint" style={{ fontSize: '0.78rem' }}>© 2026 OpicTutor. AI 기반 맞춤형 오픽 스피킹 파트너.</p>
        </footer>
      </section>

      {/* Right 45% Column: Minimalist Academic Login / Register Card */}
      <main className="signin-form-col">
        <div style={{ width: '100%', maxWidth: 420, display: 'grid', gap: 22 }}>
          <div style={{ display: 'grid', gap: 6 }}>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 700 }}>
              {mode === 'login' ? '로그인' : '새 계정 만들기'}
            </h2>
            <p className="muted" style={{ fontSize: '0.9rem' }}>
              {mode === 'login'
                ? 'OpicTutor 계정으로 로그인하여 모의 인터뷰를 시작하세요.'
                : '이메일과 닉네임을 등록하고 나만의 모의 인터뷰 기록을 관리하세요.'}
            </p>
          </div>

          <div className="signin-tabs" role="tablist" aria-label="인증 방식 선택">
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'login'}
              className={`signin-tab ${mode === 'login' ? 'active' : ''}`}
              onClick={() => { setMode('login'); setError(null); }}
            >
              로그인
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'register'}
              className={`signin-tab ${mode === 'register' ? 'active' : ''}`}
              onClick={() => { setMode('register'); setError(null); }}
            >
              회원가입
            </button>
          </div>

          <form onSubmit={onSubmit} style={{ display: 'grid', gap: 16 }}>
            <label className="field">
              <span>이메일</span>
              <input
                className="input"
                type="email"
                name="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@university.ac.kr"
                autoComplete="email"
                required
                autoFocus
              />
            </label>

            {mode === 'register' && (
              <label className="field">
                <span>닉네임 (표시 이름)</span>
                <input
                  className="input"
                  type="text"
                  name="nickname"
                  value={nickname}
                  onChange={(e) => setNickname(e.target.value)}
                  placeholder="예: 김서준"
                  maxLength={20}
                  autoComplete="nickname"
                  required
                />
              </label>
            )}

            <label className="field">
              <span>비밀번호 {mode === 'register' && <span className="faint" style={{ fontSize: '0.75rem' }}>(6자 이상)</span>}</span>
              <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                <input
                  className="input"
                  style={{ width: '100%', paddingRight: '4.5rem', boxSizing: 'border-box' }}
                  type={showPw ? 'text' : 'password'}
                  name="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  minLength={6}
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                  required
                />
                <button
                  type="button"
                  className="btn-quiet"
                  style={{ position: 'absolute', right: 6, minHeight: 30, padding: '0 0.55rem', fontSize: '0.75rem', borderRadius: 6 }}
                  onClick={() => setShowPw((v) => !v)}
                  aria-label={showPw ? '비밀번호 숨기기' : '비밀번호 표시'}
                >
                  {showPw ? '숨기기' : '보기'}
                </button>
              </div>
            </label>

            <button className="btn" type="submit" disabled={busy} style={{ minHeight: 48, width: '100%' }}>
              {busy
                ? '처리하는 중…'
                : mode === 'login'
                  ? '로그인하고 시작하기 →'
                  : '가입하고 시작하기 →'}
            </button>
          </form>

          <ErrorNote error={error} />

          <div style={{ position: 'relative', textAlign: 'center', margin: '4px 0' }}>
            <hr style={{ border: 0, borderTop: '1px solid var(--border-subtle)', margin: 0 }} />
            <span className="faint" style={{ position: 'relative', top: -11, background: '#fff', padding: '0 10px', fontSize: '0.75rem' }}>
              또는 계정 없이 체험하기
            </span>
          </div>

          <button type="button" className="btn btn-ghost" onClick={startGuest} disabled={busy} style={{ width: '100%' }}>
            게스트로 빠른 시작
          </button>

          <p className="faint" style={{ textAlign: 'center', fontSize: '0.8125rem' }}>
            {mode === 'login' ? (
              <>아직 계정이 없으신가요? <button type="button" className="btn-quiet" style={{ fontSize: '0.8125rem', fontWeight: 700, padding: '0 4px' }} onClick={() => { setMode('register'); setError(null); }}>회원가입</button></>
            ) : (
              <>이미 계정이 있으신가요? <button type="button" className="btn-quiet" style={{ fontSize: '0.8125rem', fontWeight: 700, padding: '0 4px' }} onClick={() => { setMode('login'); setError(null); }}>로그인</button></>
            )}
          </p>
        </div>
      </main>
    </div>
  );
}
