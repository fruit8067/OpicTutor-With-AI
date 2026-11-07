// AI-assisted: 유저별 테스트 히스토리 및 누적 학습 기록(/history) 화면입니다.
// OWNER: frontend (contracts.yaml ownership)
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiError, deleteSession, getScenarios, getUserHistory } from '../api/client';
import type { ScenarioOut, SessionHistoryItemOut, UserHistoryOut } from '../api/types';
import { ErrorNote, Shell } from '../components/Shell';
import {
  clearAuth,
  clearSessionId,
  loadAuthToken,
  loadAuthUser,
  loadSessionId,
  routeFor,
  saveSessionId,
} from '../lib/session';

const TIER_NAME: Record<string, string> = {
  bronze: '브론즈',
  silver: '실버',
  gold: '골드',
  platinum: '플래티넘',
  diamond: '다이아몬드',
};

function formatDuration(sec: number): string {
  const total = Math.max(0, Math.round(sec));
  const m = Math.floor(total / 60);
  const s = total % 60;
  if (m === 0) return `${s}초`;
  return `${m}분 ${s}초`;
}

function statusBadge(it: SessionHistoryItemOut): { label: string; cls: string } {
  switch (it.status) {
    case 'done':
      return { label: '평가 완료', cls: 'chip chip-ok' };
    case 'submitted':
    case 'grading':
      return { label: 'AI 채점 중', cls: 'chip chip-soft' };
    case 'grading_failed':
      return { label: '평가 일시 중단', cls: 'chip chip-warn' };
    case 'in_progress':
      return {
        label: `진행 중 (${Math.min(it.current_order_no, it.question_count)}/${it.question_count}문항)`,
        cls: 'chip chip-soft',
      };
    case 'ready':
      return { label: '시작 대기', cls: 'chip chip-soft' };
    case 'preparing':
      return { label: '음성 준비 중', cls: 'chip' };
    case 'prepare_failed':
      return { label: '준비 실패', cls: 'chip chip-warn' };
    case 'cancelled':
      return { label: '취소됨', cls: 'chip' };
  }
}

function levelDisplay(it: {
  assessment_status: string | null;
  base_level: string | null;
  estimated_level: string | null;
}): string {
  if (it.assessment_status === 'insufficient_evidence') return '판단 근거 부족';
  if (it.base_level === 'IM' && !it.estimated_level) return 'IM (세분화 보류)';
  if (it.estimated_level) return `예상 ${it.estimated_level}`;
  if (it.base_level) return `예상 ${it.base_level}`;
  return '미산출';
}

export default function History() {
  const nav = useNavigate();
  const token = loadAuthToken();
  const user = loadAuthUser();
  const currentLocalSid = loadSessionId();

  const [history, setHistory] = useState<UserHistoryOut | null>(null);
  const [scenarios, setScenarios] = useState<Record<string, ScenarioOut>>({});
  const [loading, setLoading] = useState(Boolean(token));
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [reloadTick, setReloadTick] = useState(0);

  const triggerReload = () => {
    setLoading(true);
    setError(null);
    setReloadTick((t) => t + 1);
  };

  useEffect(() => {
    if (!loadAuthToken()) return;
    let cancelled = false;
    Promise.all([
      getUserHistory(),
      getScenarios().catch(() => [] as ScenarioOut[]),
    ])
      .then(([h, sc]) => {
        if (cancelled) return;
        setHistory(h);
        const map: Record<string, ScenarioOut> = {};
        for (const s of sc) map[s.scenario_id] = s;
        setScenarios(map);
      })
      .catch((e) => {
        if (cancelled) return;
        if (e instanceof ApiError && e.code === 'UNAUTHORIZED') {
          clearAuth();
          nav('/login', { replace: true });
          return;
        }
        setError(e);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [nav, reloadTick]);

  const startNewExam = () => {
    clearSessionId();
    nav('/setup');
  };

  const resumeSession = (it: SessionHistoryItemOut) => {
    saveSessionId(it.session_id);
    const to = routeFor(it.status);
    nav(to ?? '/setup');
  };

  const openReport = (it: SessionHistoryItemOut) => {
    nav(`/result?session_id=${encodeURIComponent(it.session_id)}`);
  };

  const onDelete = async (it: SessionHistoryItemOut) => {
    if (!window.confirm('이 시험 기록을 삭제할까요? 삭제된 답변과 리포트는 복구할 수 없어요.')) return;
    setDeletingId(it.session_id);
    setError(null);
    try {
      await deleteSession(it.session_id);
      if (currentLocalSid === it.session_id) clearSessionId();
      triggerReload();
    } catch (e) {
      setError(e);
    } finally {
      setDeletingId(null);
    }
  };

  if (!token) {
    return (
      <Shell>
        <div className="sheet" style={{ padding: 36, maxWidth: 640, margin: '2rem auto', display: 'grid', gap: 16 }}>
          <span className="chip chip-soft" style={{ justifySelf: 'start' }}>회원 전용 학습 기록</span>
          <h1>로그인하고 나만의 시험 히스토리를 관리해 보세요</h1>
          <p className="muted">
            로그인 상태에서 진행한 모든 모의 인터뷰는 계정별로 안전하게 분리 저장되며, 과거 회차의 상세 리포트와 등급 추이를 언제든 다시 확인할 수 있어요.
          </p>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 4 }}>
            <button type="button" className="btn" onClick={() => nav('/login')}>
              로그인 / 회원가입하기 →
            </button>
            <button type="button" className="btn btn-ghost" onClick={startNewExam}>
              게스트로 새 시험 시작
            </button>
          </div>
        </div>
      </Shell>
    );
  }

  const summary = history?.summary;
  const items = history?.items ?? [];
  const completedChronological = [...items]
    .filter((i) => i.status === 'done')
    .reverse();

  return (
    <Shell wide>
      <div style={{ display: 'grid', gap: 28 }}>
        {/* 상단 헤더 (Stitch learning_statistics 스타일) */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: 16, flexWrap: 'wrap' }}>
          <div style={{ display: 'grid', gap: 6 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <span className="chip chip-soft">● 계정별 독립 히스토리</span>
              {user?.email && <span className="faint" style={{ fontSize: '0.8125rem' }}>{user.email}</span>}
            </div>
            <h1 style={{ fontSize: '1.85rem' }}>{user?.nickname || '수험생'} 님의 모의 인터뷰 기록</h1>
            <p className="muted" style={{ fontSize: '0.925rem' }}>
              응시한 모의 인터뷰의 누적 발화 기록과 회차별 FACT 진단 리포트를 한눈에 확인하세요.
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <button type="button" className="btn btn-ghost" onClick={triggerReload} disabled={loading}>
              새로고침
            </button>
            <button type="button" className="btn" onClick={startNewExam}>
              + 새 모의 인터뷰 시작 →
            </button>
          </div>
        </div>

        <ErrorNote error={error} />

        {/* 4대 누적 학습 요약 KPI 카드 */}
        {summary && (
          <section aria-label="누적 학습 요약" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
            <div className="sheet" style={{ padding: 22, display: 'grid', gap: 6 }}>
              <span className="faint" style={{ fontSize: '0.78rem', fontWeight: 700 }}>완료한 모의 인터뷰</span>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                <strong style={{ fontSize: '1.9rem', fontWeight: 800, color: 'var(--ink)' }}>{summary.completed_sessions}회</strong>
                <span className="muted" style={{ fontSize: '0.85rem' }}>/ 총 {summary.total_sessions}회</span>
              </div>
              <span className="faint" style={{ fontSize: '0.78rem' }}>
                {summary.in_progress_sessions > 0
                  ? `진행 중 세션 ${summary.in_progress_sessions}개 이어하기 가능`
                  : '모든 진행 세션 완료'}
              </span>
            </div>

            <div className="sheet" style={{ padding: 22, display: 'grid', gap: 6 }}>
              <span className="faint" style={{ fontSize: '0.78rem', fontWeight: 700 }}>누적 실제 발화 시간</span>
              <strong style={{ fontSize: '1.9rem', fontWeight: 800, color: 'var(--ink)' }}>
                {formatDuration(summary.total_speech_sec)}
              </strong>
              <span className="faint" style={{ fontSize: '0.78rem' }}>제출된 음성 답변의 실제 발화 구간 합산</span>
            </div>

            <div className="sheet" style={{ padding: 22, display: 'grid', gap: 6 }}>
              <span className="faint" style={{ fontSize: '0.78rem', fontWeight: 700 }}>누적 전사(STT) 완료 답변</span>
              <strong style={{ fontSize: '1.9rem', fontWeight: 800, color: 'var(--ink)' }}>
                {summary.total_answered_questions}문항
              </strong>
              <span className="faint" style={{ fontSize: '0.78rem' }}>음성 인식 및 발화 지표 분석 완료 기준</span>
            </div>

            <div className="sheet" style={{ padding: 22, display: 'grid', gap: 6, borderColor: 'var(--primary-border)', background: 'linear-gradient(180deg, #ffffff 0%, var(--primary-surface) 160%)' }}>
              <span className="faint" style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--primary)' }}>최근 완료 시험 예상 수준</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <strong style={{ fontSize: '1.65rem', fontWeight: 800, color: 'var(--primary)' }}>
                  {summary.completed_sessions > 0
                    ? levelDisplay({
                        assessment_status: summary.latest_assessment_status,
                        base_level: summary.latest_base_level,
                        estimated_level: summary.latest_estimated_level,
                      })
                    : '기록 없음'}
                </strong>
              </div>
              <span className="faint" style={{ fontSize: '0.75rem' }}>
                {summary.latest_provisional_label ?? '전사(STT) 기반 참고용 추정 등급'}
              </span>
            </div>
          </section>
        )}

        {/* 회차별 등급 추이 타임라인 */}
        {completedChronological.length > 0 && (
          <section className="sheet" aria-label="회차별 예상 수준 흐름" style={{ padding: 24, display: 'grid', gap: 14 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
              <div>
                <h2 style={{ fontSize: '1.15rem' }}>회차별 예상 수준 흐름</h2>
                <p className="faint" style={{ fontSize: '0.8125rem' }}>카드를 클릭하면 해당 회차의 AI 피드백 리포트로 바로 이동합니다.</p>
              </div>
              <span className="chip">{completedChronological.length}개 완료 회차</span>
            </div>
            <div style={{ display: 'flex', gap: 12, overflowX: 'auto', paddingBottom: 4 }}>
              {completedChronological.map((it, idx) => (
                <button
                  key={it.session_id}
                  type="button"
                  onClick={() => openReport(it)}
                  className="sheet-inset"
                  style={{
                    minWidth: 175,
                    padding: '12px 14px',
                    display: 'grid',
                    gap: 6,
                    textAlign: 'left',
                    cursor: 'pointer',
                    border: '1px solid var(--border-subtle)',
                    background: '#fff',
                    fontFamily: 'inherit',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 6 }}>
                    <span className="faint" style={{ fontSize: '0.75rem', fontWeight: 700 }}>{idx + 1}회차</span>
                    <span className="faint" style={{ fontSize: '0.72rem' }}>
                      {new Date(it.created_at).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })}
                    </span>
                  </div>
                  <strong style={{ fontSize: '1.05rem', color: 'var(--primary)' }}>
                    {levelDisplay(it)}
                  </strong>
                  {it.provisional_label && (
                    <span className="faint" style={{ fontSize: '0.7rem' }}>{it.provisional_label}</span>
                  )}
                </button>
              ))}
            </div>
          </section>
        )}

        {/* 내 시험 히스토리 목록 */}
        <section aria-label="시험 기록 목록" style={{ display: 'grid', gap: 14 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ fontSize: '1.25rem' }}>응시 내역 ({items.length})</h2>
          </div>

          {loading && !history ? (
            <div className="sheet" style={{ padding: 32 }}>
              <p className="muted" aria-live="polite">내 시험 기록을 불러오는 중…</p>
            </div>
          ) : items.length === 0 ? (
            <div className="sheet" style={{ padding: 40, textAlign: 'center', display: 'grid', gap: 14, justifyItems: 'center' }}>
              <span className="chip chip-soft">첫 모의 인터뷰 대기 중</span>
              <h3 style={{ fontSize: '1.25rem' }}>아직 저장된 시험 기록이 없어요</h3>
              <p className="muted" style={{ maxWidth: '46ch' }}>
                지금 첫 모의 인터뷰를 시작하면 답변 전사와 FACT 기준 정밀 피드백 리포트가 이곳에 차곡차곡 기록됩니다.
              </p>
              <button type="button" className="btn" onClick={startNewExam} style={{ marginTop: 4 }}>
                첫 모의 인터뷰 시작하기 →
              </button>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 12 }}>
              {items.map((it) => {
                const badge = statusBadge(it);
                const scLabel = scenarios[it.scenario_id]?.label ?? `시나리오 (${it.scenario_id})`;
                const canReport = ['done', 'submitted', 'grading', 'grading_failed'].includes(it.status);
                const canResume = ['in_progress', 'ready', 'preparing', 'prepare_failed'].includes(it.status);
                const isCurrentLocal = currentLocalSid === it.session_id;

                return (
                  <article
                    key={it.session_id}
                    className="sheet"
                    style={{
                      padding: '20px 24px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      gap: 20,
                      flexWrap: 'wrap',
                      borderLeft: it.status === 'done' ? '4px solid var(--primary)' : '4px solid var(--border-default)',
                    }}
                  >
                    <div style={{ display: 'grid', gap: 8, flex: '1 1 420px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                        <span className={badge.cls}>{badge.label}</span>
                        {isCurrentLocal && canResume && (
                          <span className="chip" style={{ fontSize: '0.72rem' }}>현재 브라우저 활성 세션</span>
                        )}
                        <strong style={{ fontSize: '1rem', color: 'var(--ink)' }}>{scLabel}</strong>
                        <span className="faint" style={{ fontSize: '0.8125rem' }}>
                          · {new Date(it.created_at).toLocaleString('ko-KR')}
                        </span>
                      </div>

                      {it.status === 'done' && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                          <span className="chip chip-soft" style={{ fontWeight: 700 }}>
                            {levelDisplay(it)}
                          </span>
                          {it.tier && (
                            <span className="chip" style={{ gap: 6 }}>
                              <span style={{ width: 8, height: 8, borderRadius: 99, background: it.tier.color }} aria-hidden="true" />
                              {TIER_NAME[it.tier.name] ?? it.tier.name}
                            </span>
                          )}
                          {it.provisional_label && (
                            <span className="faint" style={{ fontSize: '0.78rem' }}>{it.provisional_label}</span>
                          )}
                          {it.headline && (
                            <span style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--ink)' }}>
                              “{it.headline}”
                            </span>
                          )}
                        </div>
                      )}

                      <div className="faint" style={{ display: 'flex', gap: 14, flexWrap: 'wrap', fontSize: '0.8125rem' }}>
                        <span>녹음 답변 {it.answered_count}/{it.question_count}문항</span>
                        {it.skipped_count > 0 && <span>건너뜀 {it.skipped_count}문항</span>}
                        <span>실제 발화 {formatDuration(it.total_speech_sec)}</span>
                        {it.graded_at && <span>채점 완료 {new Date(it.graded_at).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}</span>}
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                      {canReport && (
                        <button type="button" className="btn" onClick={() => openReport(it)}>
                          {it.status === 'done' ? '리포트 보기 →' : '채점 상태 보기 →'}
                        </button>
                      )}
                      {canResume && (
                        <button type="button" className="btn" onClick={() => resumeSession(it)}>
                          이어하기 →
                        </button>
                      )}
                      <button
                        type="button"
                        className="btn btn-ghost"
                        style={{ color: 'var(--danger)' }}
                        disabled={deletingId === it.session_id}
                        onClick={() => void onDelete(it)}
                      >
                        {deletingId === it.session_id ? '삭제 중…' : '기록 삭제'}
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>
      </div>
    </Shell>
  );
}
