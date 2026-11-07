// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// 후속 수정: CR frontend-01의 타입 우회 제거는 OpenAI Codex의 도움으로 작성되었습니다.
// 후속 수정: 건너뛴 문항 표시, 결과 화면 네비게이션 통합 및 Stitch 리포트 디자인 적용을 반영했습니다.
// OWNER: frontend (contracts.yaml ownership)
//
// 결과: E2 2초 폴링. grading → 채점 중(3분 넘으면 안내, 폴링 계속), grading_failed → [다시 평가](E3), done → 보고서.
// 서버가 준 값을 그대로 보여 준다. 등급을 계산·보정하지 않고, 숫자 점수·막대·별점을 그리지 않는다.
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ApiError, getResult, regrade } from '../api/client';
import type { EvaluationResult, ResultItemOut, ResultOut } from '../api/types';
import { ErrorNote, Live, Shell } from '../components/Shell';
import { Host } from '../features/host/Host';
import {
  CONTEXT_LABEL, FACT_LABEL, FACT_STATUS_LABEL, FULFILL_LABEL, FUNCTION_LABEL, GRADING_ERROR_TEXT, labelOf, TIME_LABEL, TYPE_LABEL,
} from '../lib/messages';
import { clearSessionId, loadSessionId, routeFor } from '../lib/session';
import { usePoll } from '../lib/usePoll';

const SLOW_MS = 180000; // policies.grading_poll_slow_notice_ms
// contracts.yaml tiers: 서버의 객체를 그대로 사용하고 표시 이름만 매핑한다.
const TIER_NAME: Record<string, string> = { bronze: '브론즈', silver: '실버', gold: '골드', platinum: '플래티넘', diamond: '다이아몬드' };

export default function Result() {
  const nav = useNavigate();
  const [searchParams] = useSearchParams();
  const querySessionId = searchParams.get('session_id');
  const id = querySessionId || loadSessionId();
  const [data, setData] = useState<ResultOut | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const startedAt = useRef(0);
  useEffect(() => { startedAt.current = Date.now(); }, [id]);
  const [slow, setSlow] = useState(false);

  const waiting = !data || ['submitted', 'grading'].includes(data.session_status);
  usePoll(async (active) => {
    if (!id) { nav('/setup', { replace: true }); return false; }
    try {
      const r = await getResult(id);
      if (!active()) return false;
      setData(r); setError(null);
      setSlow(Date.now() - startedAt.current > SLOW_MS);
      const to = routeFor(r.session_status);
      if (!to) {
        if (!querySessionId) clearSessionId();
        nav(querySessionId ? '/history' : '/setup', { replace: true });
        return false;
      }
      if (to !== '/result') {
        if (querySessionId) nav('/history', { replace: true });
        else nav(to, { replace: true });
        return false;
      }
      return ['submitted', 'grading'].includes(r.session_status);
    } catch (e) {
      if (!active()) return false;
      if (e instanceof ApiError && (e.code === 'SESSION_NOT_FOUND' || e.code === 'FORBIDDEN')) {
        if (!querySessionId) clearSessionId();
        nav(querySessionId ? '/history' : '/setup', { replace: true });
        return false;
      }
      if (e instanceof ApiError && e.code === 'INVALID_STATE') { nav(querySessionId ? '/history' : '/', { replace: true }); return false; }
      setError(e); return true;
    }
  }, 2000, !!id && waiting);

  const newExam = () => { clearSessionId(); nav('/setup'); };
  const goHistory = () => { nav('/history'); };
  const doRegrade = async () => {
    if (!id) return;
    setBusy(true);
    try { await regrade(id); startedAt.current = Date.now(); setData((d) => (d ? { ...d, session_status: 'grading' } : d)); setError(null); }
    catch (e) { setError(e); } finally { setBusy(false); }
  };

  if (!data || waiting) {
    return (
      <Shell>
        <div className="sheet" style={{ padding: 36, display: 'grid', gridTemplateColumns: 'minmax(160px, 220px) 1fr', gap: 36, alignItems: 'center', maxWidth: 820, margin: '2rem auto' }}>
          <div style={{ color: 'var(--ink)' }}><Host state="processing" /></div>
          <div style={{ display: 'grid', gap: 12 }}>
            <span className="chip chip-soft" style={{ justifySelf: 'start' }}>● AI 정밀 채점 진행 중</span>
            <h1>답변 전체를 평가하고 있어요</h1>
            <p className="muted prose-w">제출한 답변의 전사와 관측 지표를 함께 보고 예상 수준과 연습 방향을 정리하는 중이에요. 이 화면을 닫았다가 다시 와도 이어서 볼 수 있어요.</p>
            {slow && <p className="notice" role="status">평가가 평소보다 오래 걸리고 있어요. 계속 확인하고 있으니 조금만 더 기다려 주세요.</p>}
            <ErrorNote error={error} />
          </div>
        </div>
        <Live>평가 중</Live>
      </Shell>
    );
  }

  if (data.session_status === 'grading_failed') {
    return (
      <Shell>
        <div className="sheet" style={{ padding: 32, display: 'grid', gap: 16, maxWidth: 680, margin: '2rem auto' }}>
          <span className="chip chip-warn" style={{ justifySelf: 'start' }}>평가 일시 중단</span>
          <h1>평가를 마치지 못했어요</h1>
          <p className="muted">{labelOf(GRADING_ERROR_TEXT, data.error_code ?? 'EVAL_INTERNAL')} 저장된 답변은 그대로 있어서, 다시 녹음하지 않고 평가만 다시 할 수 있어요.</p>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <button className="btn" onClick={doRegrade} disabled={busy} autoFocus>다시 평가</button>
            <button className="btn btn-ghost" onClick={newExam}>새 시험 보기</button>
          </div>
          <ErrorNote error={error} />
        </div>
      </Shell>
    );
  }

  if (!data.result) return <Shell><p className="muted">결과를 불러오는 중…</p></Shell>;
  return <Report r={data.result} answers={data.answers} gradedAt={data.graded_at} onNew={newExam} onHistory={goHistory} />;
}

/* ---------------- 보고서 (Stitch AI Feedback Report + contracts 불변 조건 유지) ---------------- */

function Section({ id, kicker, title, sub, children }: { id: string; kicker?: string; title: string; sub?: string; children: ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-h`} style={{ display: 'grid', gap: 14, scrollMarginTop: 120 }}>
      <div style={{ display: 'grid', gap: 4 }}>
        {kicker && <span className="faint" style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--primary)', letterSpacing: '0.04em', textTransform: 'uppercase' }}>{kicker}</span>}
        <h2 id={`${id}-h`} style={{ fontSize: '1.35rem' }}>{title}</h2>
        {sub && <p className="faint">{sub}</p>}
      </div>
      {children}
    </section>
  );
}

const Chip = ({ n }: { n: number }) => <a className="chip" href={`#item-${n}`} aria-label={`${n}번 문항 보기`} style={{ textDecoration: 'none' }}>Q{String(n).padStart(2, '0')} ({n}번)</a>;

const Quote = ({ children }: { children: ReactNode }) => (
  <q lang="en" style={{ display: 'block', borderLeft: '3px solid var(--primary)', background: 'var(--canvas)', borderRadius: '0 6px 6px 0', padding: '6px 12px', color: 'var(--ink)', quotes: 'none', fontSize: '0.9375rem' }}>{children}</q>
);

function Report({ r, answers, gradedAt, onNew, onHistory }: { r: EvaluationResult; answers: ResultItemOut[]; gradedAt: string | null; onNew: () => void; onHistory: () => void }) {
  const scope = r.evaluation_scope;
  const tier = r.tier;
  const insufficient = r.assessment_status === 'insufficient_evidence';
  const imHeld = !insufficient && r.base_level === 'IM' && r.estimated_level === null;
  const byOrder = new Map(answers.map((a) => [a.order_no, a]));
  const items = [...r.items].sort((a, b) => a.order_no - b.order_no);
  const scoredItems = items.filter((i) => i.evaluation_role === 'scored');
  const warmItems = items.filter((i) => i.evaluation_role === 'feedback_only');
  const toc: [string, string][] = [
    ['grade', '예상 수준'],
    ['why', '판단 근거'],
    ['fact', '영역별 진단'],
    ['coverage', '관찰 범위'],
    ['perf', '지속과 흔들림'],
    ['cards', '연습 카드'],
    ['items', '문항별 상세'],
    ['more', '참고'],
  ];

  return (
    <Shell wide>
      <article style={{ display: 'grid', gap: 28 }}>
        {/* Top Summary & Breadcrumb Header (Stitch ai_feedback_report) */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: 16, flexWrap: 'wrap' }}>
          <div style={{ display: 'grid', gap: 6 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <span className="chip chip-soft">● AI 정밀 진단 리포트</span>
              <span className="faint" style={{ fontSize: '0.8125rem' }}>
                채점 대상 {scope.scored_order_nos.length}문항 · 판단 반영 {scope.usable_order_nos.length}문항
              </span>
              {gradedAt && <span className="faint" style={{ fontSize: '0.8125rem' }}>· {new Date(gradedAt).toLocaleString('ko-KR')}</span>}
            </div>
            <h1 style={{ fontSize: '1.85rem' }}>모의 인터뷰 종합 평가 리포트</h1>
          </div>
          <div className="no-print" style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <button type="button" className="btn btn-ghost" onClick={onHistory}>
              ← 내 시험 기록
            </button>
            <button type="button" className="btn btn-ghost" onClick={() => window.print()}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><path d="M6 9V2h12v7" /><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" /><rect x="6" y="14" width="12" height="8" /></svg>
              PDF / 인쇄
            </button>
            <button type="button" className="btn btn-ghost" disabled aria-label="AI와 더 이야기하기, 준비 중">
              AI 대화 (준비 중)
            </button>
            <button type="button" className="btn" onClick={onNew}>
              새 시험 보기 →
            </button>
          </div>
        </div>

        {/* 통합 상단 스티키 섹션 네비게이션 바 */}
        <nav aria-label="결과 목차" className="report-nav">
          <div className="report-nav-links">
            {toc.map(([k, t]) => (
              <a key={k} href={`#${k}`} className="report-nav-link">{t}</a>
            ))}
          </div>
          <span className="faint" style={{ fontSize: '0.75rem', paddingRight: 6 }}>
            전사(STT) 기반 FACT 서술 진단
          </span>
        </nav>

        {/* 안내 띠: 항상 노출 (계약 불변 조건) */}
        <div className="notice" role="note" style={{ display: 'grid', gap: 6 }}>
          <p style={{ fontWeight: 500 }}>
            전사(STT) 기반 추정이에요. 채점 대상 {scope.scored_order_nos.length}문항으로 판단했고, 자기소개({scope.feedback_only_order_nos.join(', ')}번)는 채점에서 제외했어요. 발음은 평가하지 않았어요.
          </p>
          {scope.unusable_items.length > 0 && (
            <p className="muted" style={{ fontSize: '0.875rem' }}>
              확인할 수 없었던 답변: {scope.unusable_items.map((u) => `${u.order_no}번(${u.reason})`).join(', ')}. 이 답변은 낮은 점수가 아니라 판단에서 빠졌어요.
            </p>
          )}
        </div>

        {/* Big Comprehensive Result Hero Card (예상 수준 + 판단 근거 12컬럼 통합) */}
        <section id="grade" aria-labelledby="grade-h" style={{ scrollMarginTop: 120 }}>
          <h2 id="grade-h" className="sr-only">예상 수준</h2>
          <div className="report-hero" style={{ borderTop: `6px solid ${tier?.color ?? 'var(--primary)'}` }}>
            {/* 좌측: 종합 예상 등급 블록 */}
            <div className="report-hero-grade">
              <div style={{ display: 'grid', gap: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
                  <span className="faint" style={{ fontWeight: 600 }}>종합 예상 평가 수준</span>
                  {tier && (
                    <span className="chip" style={{ borderColor: tier.color, fontWeight: 700 }}>
                      <span style={{ width: 8, height: 8, borderRadius: '50%', background: tier.color }} aria-hidden="true" />
                      {TIER_NAME[tier.name] ?? tier.name} 티어
                    </span>
                  )}
                </div>

                {insufficient ? (
                  <div style={{ display: 'grid', gap: 8 }}>
                    <p style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--ink)' }}>판단 근거가 부족해요</p>
                    <p className="muted">{r.insufficient_reason}</p>
                  </div>
                ) : imHeld ? (
                  <div style={{ display: 'grid', gap: 8 }}>
                    <p style={{ fontSize: '1.85rem', fontWeight: 700, color: 'var(--primary)' }}>
                      예상 IM <span className="muted" style={{ fontSize: '1.05rem', fontWeight: 600 }}>(세분화 보류)</span>
                    </p>
                    <p className="muted">{r.insufficient_reason}</p>
                  </div>
                ) : (
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
                    <p style={{ fontSize: '2.75rem', fontWeight: 800, lineHeight: 1, color: 'var(--primary)', letterSpacing: '-0.03em' }}>
                      예상 {r.estimated_level}
                    </p>
                    {r.provisional_label && (
                      <span className="badge badge-none" style={{ fontSize: '0.85rem', border: '1px solid var(--border-hover)' }}>
                        {r.provisional_label}
                      </span>
                    )}
                  </div>
                )}

                <p style={{ fontSize: '1.02rem', fontWeight: 500, color: 'var(--ink)' }}>{r.headline}</p>

                {r.borderline_levels.length > 0 && (
                  <div className="panel" style={{ padding: '10px 14px', fontSize: '0.875rem' }}>
                    <strong>경계 후보: {(r.estimated_level ? [r.estimated_level, ...r.borderline_levels] : r.borderline_levels).join(' ↔ ')}</strong>
                    {r.uncertainty_reasons.length > 0 && <p className="muted" style={{ marginTop: 2 }}>{r.uncertainty_reasons.join(' / ')}</p>}
                  </div>
                )}

                {(imHeld || insufficient) && r.additional_tasks_needed.length > 0 && (
                  <p className="faint">더 정확히 보려면 아래 "참고"의 추가로 필요한 답변을 연습해 보세요.</p>
                )}
              </div>

              {/* 하단 요약 범위 블록 (숫자 점수 대신 실제 채점 범위만 표시) */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, paddingTop: 12, borderTop: '1px solid var(--border-subtle)' }}>
                <div>
                  <span className="faint" style={{ fontSize: '0.75rem', display: 'block' }}>채점 대상</span>
                  <strong style={{ fontSize: '1rem' }}>{scope.scored_order_nos.length}문항</strong>
                </div>
                <div>
                  <span className="faint" style={{ fontSize: '0.75rem', display: 'block' }}>판단 반영</span>
                  <strong style={{ fontSize: '1rem' }}>{scope.usable_order_nos.length}문항</strong>
                </div>
                <div>
                  <span className="faint" style={{ fontSize: '0.75rem', display: 'block' }}>워밍업 제외</span>
                  <strong style={{ fontSize: '1rem' }}>{scope.feedback_only_order_nos.length}문항</strong>
                </div>
              </div>
            </div>

            {/* 우측: 판단 근거 3단 (why_this_level / why_not_lower / next_level_gap) */}
            <div id="why" style={{ display: 'grid', gap: 12, alignContent: 'start', scrollMarginTop: 120 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>판단 근거</h3>
                <span className="chip">ACTFL · FACT 기준</span>
              </div>
              <dl style={{ display: 'grid', gap: 10, margin: 0 }}>
                {([
                  ['왜 이 수준인가', r.why_this_level, 'var(--primary)'],
                  ['아래 수준보다 나은 점', r.why_not_lower, 'var(--success)'],
                  ['다음 수준까지 필요한 것', r.next_level_gap, 'var(--amber)'],
                ] as const).map(([t, v, accent]) => (
                  <div key={t} className="panel" style={{ padding: '12px 16px', borderLeft: `3px solid ${accent}`, display: 'grid', gap: 4 }}>
                    <dt style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--ink-soft)' }}>{t}</dt>
                    <dd style={{ margin: 0, fontSize: '0.9375rem' }}>{v}</dd>
                  </div>
                ))}
              </dl>
              {r.grade_rationale && <p className="muted" style={{ fontSize: '0.875rem' }}>{r.grade_rationale}</p>}
            </div>
          </div>
        </section>

        {/* FACT 영역별 진단 (숫자 점수/막대 없음) */}
        <Section id="fact" kicker="FACT Assessment" title="영역별 진단" sub="점수가 아니라 제출한 답변에서 관찰한 수행 내용이에요.">
          <div className="report-grid-2">
            {(['functions_tasks', 'accuracy', 'context_content', 'text_type'] as const).map((k) => {
              const d = r.dimension_feedback[k];
              return (
                <div key={k} className="sheet" style={{ padding: 20, display: 'grid', gap: 10, alignContent: 'start' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                    <h3 style={{ fontSize: '1.05rem' }}>{FACT_LABEL[k]}</h3>
                    <span className="chip chip-soft">관찰 요약</span>
                  </div>
                  <p style={{ fontSize: '0.9375rem' }}>{d.summary}</p>
                  {d.evidence_order_nos.length > 0 && (
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                      <span className="faint" style={{ fontSize: '0.75rem' }}>근거 문항:</span>
                      {d.evidence_order_nos.map((n) => <Chip key={n} n={n} />)}
                    </div>
                  )}
                  {d.limitations.length > 0 && <p className="faint" style={{ fontSize: '0.8125rem' }}>한계: {d.limitations.join(' / ')}</p>}
                </div>
              );
            })}
          </div>

          {r.fact_evidence.length > 0 && (
            <div className="sheet" style={{ padding: 20, display: 'grid', gap: 12 }}>
              <h3 style={{ fontSize: '1rem' }}>관찰된 세부 근거</h3>
              <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: 10 }}>
                {r.fact_evidence.map((f, i) => (
                  <li
                    key={i}
                    style={{
                      padding: '12px 14px',
                      borderRadius: 'var(--radius-s)',
                      background: 'var(--canvas)',
                      borderLeft: `3px solid ${f.status === 'demonstrated' ? 'var(--success)' : f.status === 'not_demonstrated' ? 'var(--rec)' : 'var(--slate-400)'}`,
                      display: 'grid',
                      gap: 6,
                    }}
                  >
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                      <span className={`badge ${f.status === 'demonstrated' ? 'badge-ok' : f.status === 'not_demonstrated' ? 'badge-no' : 'badge-none'}`}>
                        {FACT_STATUS_LABEL[f.status]}
                      </span>
                      <span className="faint" style={{ fontWeight: 600 }}>{FACT_LABEL[f.criterion]}</span>
                      {f.order_no != null && <Chip n={f.order_no} />}
                    </div>
                    <p style={{ fontSize: '0.9375rem' }}>{f.observation}</p>
                    {f.quote && <Quote>{f.quote}</Quote>}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Section>

        {/* 관찰 범위 */}
        <Section id="coverage" kicker="Task Coverage" title="관찰 범위" sub="이번 시험의 채점 문항이 실제로 물어본 것이에요. 묻지 않은 항목은 감점하지 않아요.">
          <div className="report-grid-3">
            {([
              ['기능 (Functions)', r.coverage.functions, FUNCTION_LABEL],
              ['시간대 (Time Frames)', r.coverage.time_frames, TIME_LABEL],
              ['맥락 (Contexts)', r.coverage.contexts, CONTEXT_LABEL],
            ] as const).map(([t, list, map]) => (
              <div key={t} className="sheet" style={{ padding: 18, display: 'grid', gap: 10, alignContent: 'start' }}>
                <h3 style={{ fontSize: '1rem' }}>{t}</h3>
                <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: '0.875rem' }}>
                  <thead>
                    <tr className="faint" style={{ textAlign: 'left', fontSize: '0.75rem' }}>
                      <th scope="col" style={{ padding: '6px 6px' }}>항목</th>
                      <th scope="col" style={{ padding: '6px 6px' }}>출제</th>
                      <th scope="col" style={{ padding: '6px 6px' }}>확인</th>
                      <th scope="col" style={{ padding: '6px 6px' }}>빈 곳</th>
                    </tr>
                  </thead>
                  <tbody>
                    {list.map((c) => (
                      <tr key={c.name} style={{ borderTop: '1px solid var(--line)' }}>
                        <th scope="row" style={{ padding: '8px 6px', textAlign: 'left', fontWeight: 600 }}>{labelOf(map, c.name)}</th>
                        <td style={{ padding: '8px 6px' }}>{c.elicited_order_nos.length ? c.elicited_order_nos.join(', ') : '묻지 않음'}</td>
                        <td style={{ padding: '8px 6px' }}>{c.usable_order_nos.length ? c.usable_order_nos.join(', ') : '-'}</td>
                        <td className="muted" style={{ padding: '8px 6px', fontSize: '0.8125rem' }}>{c.gaps.join(' / ') || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        </Section>

        {/* 지속된 수행과 흔들린 부분 */}
        <Section id="perf" kicker="Performance Stability" title="지속된 수행과 흔들린 부분">
          <div className="report-grid-2">
            <div className="sheet" style={{ padding: 20, borderTop: '4px solid var(--success)', display: 'grid', gap: 12, alignContent: 'start' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                <h3 style={{ fontSize: '1.05rem' }}>여러 답변에서 유지된 것</h3>
                <span className="badge badge-ok">지속 수행</span>
              </div>
              {r.sustained_performance.length ? r.sustained_performance.map((p, i) => (
                <div key={i} className="panel" style={{ padding: '12px 14px', display: 'grid', gap: 6 }}>
                  <strong>{p.capability}</strong>
                  <p className="muted" style={{ fontSize: '0.875rem' }}>{p.summary}</p>
                  {p.evidence.map((e, j) => (
                    <div key={j} style={{ display: 'grid', gap: 4 }}>
                      <div><Chip n={e.order_no} /></div>
                      <Quote>{e.quote}</Quote>
                    </div>
                  ))}
                </div>
              )) : <p className="faint">기록 없음</p>}
            </div>

            <div className="sheet" style={{ padding: 20, borderTop: '4px solid var(--amber)', display: 'grid', gap: 12, alignContent: 'start' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                <h3 style={{ fontSize: '1.05rem' }}>요구가 커질 때 흔들린 것</h3>
                <span className="chip chip-warn">보완 포인트</span>
              </div>
              {r.breakdown_observations.length ? r.breakdown_observations.map((b, i) => (
                <div key={i} className="panel" style={{ padding: '12px 14px', display: 'grid', gap: 6 }}>
                  <strong>{labelOf(FUNCTION_LABEL, b.demanded_function)}</strong>
                  <p className="muted" style={{ fontSize: '0.875rem' }}>{b.communicative_impact}</p>
                  {b.recovery && <p className="faint" style={{ fontSize: '0.8125rem' }}>회복: {b.recovery}</p>}
                  {b.evidence.map((e, j) => (
                    <div key={j} style={{ display: 'grid', gap: 4 }}>
                      <div><Chip n={e.order_no} /></div>
                      <Quote>{e.quote}</Quote>
                    </div>
                  ))}
                </div>
              )) : <p className="faint">눈에 띄게 흔들린 부분은 관찰되지 않았어요.</p>}
            </div>
          </div>
        </Section>

        {/* 연습 카드 */}
        <Section id="cards" kicker="Actionable Coaching" title="연습 카드">
          {r.feedback_cards.length === 0 ? <p className="faint">이번 결과로는 연습 카드를 만들 근거가 부족해요.</p> : (
            <ol style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: 16 }}>
              {r.feedback_cards.map((c, i) => (
                <li key={i} className="sheet" style={{ padding: 22, display: 'grid', gap: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span className="chip chip-primary">Coaching {String(i + 1).padStart(2, '0')}</span>
                      <h3 style={{ fontSize: '1.05rem' }}>{c.title}</h3>
                    </div>
                    {c.related_order_nos.length > 0 && (
                      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                        {c.related_order_nos.map((n) => <Chip key={n} n={n} />)}
                      </div>
                    )}
                  </div>
                  <p className="muted">{c.why}</p>
                  {c.example_kind === 'correction' && c.before ? (
                    <div className="report-grid-2">
                      <div className="panel" style={{ padding: '12px 14px', borderLeft: '3px solid var(--amber)', display: 'grid', gap: 4 }}>
                        <span className="faint" style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--warn)' }}>내 답변</span>
                        <q lang="en" style={{ quotes: 'none', color: 'var(--ink)' }}>{c.before}</q>
                      </div>
                      <div className="panel" style={{ padding: '12px 14px', borderLeft: '3px solid var(--success)', background: 'var(--success-surface)', display: 'grid', gap: 4 }}>
                        <span className="faint" style={{ fontSize: '0.75rem', fontWeight: 700, color: '#047857' }}>고쳐 보기</span>
                        <p lang="en" style={{ fontWeight: 600, color: '#065f46' }}>{c.after}</p>
                      </div>
                    </div>
                  ) : (
                    <div className="panel" style={{ padding: '12px 14px', borderLeft: '3px solid var(--primary)', background: 'var(--primary-surface)', display: 'grid', gap: 4 }}>
                      <span className="faint" style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--primary)' }}>새 연습 예시</span>
                      <p lang="en" style={{ fontWeight: 600 }}>{c.after}</p>
                    </div>
                  )}
                  <p style={{ fontSize: '0.9rem' }}>
                    <strong style={{ color: 'var(--primary)' }}>다음 답변에서 확인할 점 · </strong>
                    {c.success_condition}
                  </p>
                </li>
              ))}
            </ol>
          )}
        </Section>

        {/* 문항별 상세 (자기소개는 맨 아래 채점 제외 섹션으로 분리) */}
        <Section id="items" kicker="Question-by-Question Review" title="문항별 상세">
          <div style={{ display: 'grid', gap: 12 }}>
            {scoredItems.map((it) => <ItemDetail key={it.order_no} it={it} a={byOrder.get(it.order_no)} />)}
          </div>
          {warmItems.length > 0 && (
            <div style={{ display: 'grid', gap: 12, borderTop: '1px dashed var(--line-strong)', paddingTop: 18, marginTop: 6 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <h3 style={{ fontSize: '1.05rem' }}>채점 제외 · 연습 피드백</h3>
                <span className="badge badge-none">워밍업 문항</span>
              </div>
              {warmItems.map((it) => <ItemDetail key={it.order_no} it={it} a={byOrder.get(it.order_no)} warm />)}
            </div>
          )}
        </Section>

        {/* 참고 */}
        <Section id="more" kicker="Reference & Limitations" title="참고">
          <div className="sheet" style={{ padding: 22, display: 'grid', gap: 16 }}>
            {r.additional_tasks_needed.length > 0 && (
              <div style={{ display: 'grid', gap: 8 }}>
                <h3 style={{ fontSize: '1rem' }}>다음에 연습해 볼 질문</h3>
                <p className="faint">이번 시험 문항이 아니라, 더 정확히 확인하려면 필요한 연습 질문이에요.</p>
                <ul style={{ margin: 0, paddingLeft: '1.2rem', display: 'grid', gap: 8 }}>
                  {r.additional_tasks_needed.map((t, i) => (
                    <li key={i}>
                      <span lang="en" style={{ fontWeight: 600 }}>{t.suggested_question}</span>
                      <br />
                      <span className="faint">{labelOf(FUNCTION_LABEL, t.target_function)} · {t.reason}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <details className="panel" style={{ padding: '12px 16px' }}>
              <summary style={{ cursor: 'pointer', fontWeight: 600 }}>속도·멈춤 관찰 (STT 기반 참고치)</summary>
              <p className="muted prose-w" style={{ marginTop: 8 }}>{r.fluency_observations}</p>
            </details>

            {r.limitations.length > 0 && (
              <div>
                <h3 style={{ fontSize: '0.95rem' }}>이번 결과의 한계</h3>
                <ul className="muted" style={{ margin: '6px 0 0', paddingLeft: '1.2rem', fontSize: '0.875rem' }}>
                  {r.limitations.map((l, i) => <li key={i}>{l}</li>)}
                </ul>
              </div>
            )}

            <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: 12, display: 'grid', gap: 4 }}>
              <p className="faint">{r.disclaimer}</p>
              <p className="faint" style={{ fontSize: '0.75rem' }}>
                기준 {r.rubric_version}{r.im_rubric_version ? ` · IM 세분화 ${r.im_rubric_version}` : ''}{gradedAt ? ` · 평가 ${new Date(gradedAt).toLocaleString('ko-KR')}` : ''}
              </p>
            </div>
          </div>
        </Section>
      </article>
      <Live>평가 결과가 준비됐어요</Live>
    </Shell>
  );
}

function ItemDetail({ it, a, warm = false }: { it: EvaluationResult['items'][number]; a?: ResultItemOut; warm?: boolean }) {
  return (
    <details id={`item-${it.order_no}`} className="sheet" style={{ padding: '16px 20px', scrollMarginTop: 120 }} open={false}>
      <summary style={{ cursor: 'pointer', display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <span className="chip chip-soft">Question {String(it.order_no).padStart(2, '0')}</span>
          <strong>{it.order_no}번</strong>
          <span className="faint">{a ? labelOf(TYPE_LABEL, a.question_type) : ''}</span>
          {a?.skipped && <span className="badge badge-none">건너뜀</span>}
          {warm
            ? <span className="badge badge-none">채점 제외</span>
            : <span className={`badge ${it.task_fulfillment === 'fulfilled' ? 'badge-ok' : it.task_fulfillment === 'not_assessable' ? 'badge-none' : 'badge-no'}`}>{FULFILL_LABEL[it.task_fulfillment]}</span>}
        </div>
        {a?.metrics && (
          <span className="faint" style={{ fontSize: '0.78rem' }}>
            {a.metrics.duration_sec}초 · {a.metrics.word_count}단어 · {a.metrics.wpm} WPM
          </span>
        )}
      </summary>
      <div style={{ display: 'grid', gap: 14, marginTop: 14, paddingTop: 14, borderTop: '1px solid var(--border-subtle)' }}>
        {a && (
          <div className="panel" style={{ padding: '12px 14px', display: 'grid', gap: 4 }}>
            <span className="faint" style={{ fontSize: '0.75rem', fontWeight: 600 }}>질문 원문</span>
            <p lang="en" style={{ fontWeight: 500 }}>{a.question_text}</p>
          </div>
        )}
        {a && (a.skipped
          ? <p className="muted">이 문항은 건너뛰어서 답변이 없어요.</p>
          : (
            <div className="panel" style={{ padding: '12px 14px', background: 'var(--canvas)', border: '1px solid var(--border-subtle)', display: 'grid', gap: 4 }}>
              <span className="faint" style={{ fontSize: '0.75rem', fontWeight: 600 }}>내 답변(전사)</span>
              <p lang="en">{a.stt_text || '전사 없음'}</p>
            </div>
          ))}
        {it.evidence.length > 0 && (
          <div style={{ display: 'grid', gap: 6 }}>
            <span className="faint" style={{ fontSize: '0.8125rem', fontWeight: 600 }}>근거</span>
            {it.evidence.map((e, i) => <Quote key={i}>{e}</Quote>)}
          </div>
        )}
        {it.mistakes.length > 0 && (
          <div style={{ display: 'grid', gap: 8 }}>
            <span className="faint" style={{ fontSize: '0.8125rem', fontWeight: 600 }}>고칠 점</span>
            {it.mistakes.map((m, i) => (
              <div key={i} className="panel" style={{ padding: '10px 14px', display: 'grid', gap: 4 }}>
                <Quote>{m.quote}</Quote>
                <p className="muted" style={{ fontSize: '0.875rem' }}>{m.problem}</p>
                <p lang="en" style={{ fontWeight: 600, color: '#047857' }}>→ {m.fix}</p>
              </div>
            ))}
          </div>
        )}
        {it.upgrade_tip && (
          <p style={{ fontSize: '0.9rem' }}>
            <strong style={{ color: 'var(--primary)' }}>다음 연습 · </strong>
            {it.upgrade_tip}
          </p>
        )}
        {a?.metrics && (
          <p className="faint" style={{ fontSize: '0.8125rem' }}>
            관측치 · 길이 {a.metrics.duration_sec}초 · 단어 {a.metrics.word_count}개 · 분당 {a.metrics.wpm}단어 · 긴 멈춤 {a.metrics.long_pause_count}회
            {a.metrics.observed_filler_per100 != null ? ` · 필러 100단어당 ${a.metrics.observed_filler_per100}` : ''}
          </p>
        )}
      </div>
    </details>
  );
}
