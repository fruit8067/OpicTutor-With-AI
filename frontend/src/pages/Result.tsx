// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// 후속 수정: CR frontend-01의 타입 우회 제거는 OpenAI Codex의 도움으로 작성되었습니다.
// OWNER: frontend (contracts.yaml ownership)
//
// 결과: E2 2초 폴링. grading → 채점 중(3분 넘으면 안내, 폴링 계속), grading_failed → [다시 평가](E3), done → 보고서.
// 서버가 준 값을 그대로 보여 준다. 등급을 계산·보정하지 않고, 숫자 점수·막대·별점을 그리지 않는다.
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
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
  const id = loadSessionId();
  const [data, setData] = useState<ResultOut | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const startedAt = useRef(0);
  useEffect(() => { startedAt.current = Date.now(); }, []);
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
      if (!to) { clearSessionId(); nav('/setup', { replace: true }); return false; }
      if (to !== '/result') { nav(to, { replace: true }); return false; }
      return ['submitted', 'grading'].includes(r.session_status);
    } catch (e) {
      if (!active()) return false;
      if (e instanceof ApiError && e.code === 'SESSION_NOT_FOUND') { clearSessionId(); nav('/setup', { replace: true }); return false; }
      if (e instanceof ApiError && e.code === 'INVALID_STATE') { nav('/', { replace: true }); return false; }
      setError(e); return true;
    }
  }, 2000, !!id && waiting);

  const newExam = () => { clearSessionId(); nav('/setup'); };
  const doRegrade = async () => {
    if (!id) return;
    setBusy(true);
    try { await regrade(id); startedAt.current = Date.now(); setData((d) => (d ? { ...d, session_status: 'grading' } : d)); setError(null); }
    catch (e) { setError(e); } finally { setBusy(false); }
  };

  if (!data || waiting) {
    return (
      <Shell>
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(160px, 220px) 1fr', gap: 40, alignItems: 'center', maxWidth: 820 }}>
          <div style={{ color: 'var(--ink)' }}><Host state="processing" /></div>
          <div style={{ display: 'grid', gap: 12 }}>
            <h1>답변 전체를 평가하고 있어요</h1>
            <p className="muted prose-w">8개 답변의 전사와 관측 지표를 함께 보고 예상 수준과 연습 방향을 정리하는 중이에요. 이 화면을 닫았다가 다시 와도 이어서 볼 수 있어요.</p>
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
        <div style={{ display: 'grid', gap: 16, maxWidth: 680 }}>
          <h1>평가를 마치지 못했어요</h1>
          <p className="muted">{labelOf(GRADING_ERROR_TEXT, data.error_code ?? 'EVAL_INTERNAL')} 저장된 답변 8개는 그대로 있어서, 다시 녹음하지 않고 평가만 다시 할 수 있어요.</p>
          <div style={{ display: 'flex', gap: 12 }}>
            <button className="btn" onClick={doRegrade} disabled={busy} autoFocus>다시 평가</button>
            <button className="btn btn-ghost" onClick={newExam}>새 시험 보기</button>
          </div>
          <ErrorNote error={error} />
        </div>
      </Shell>
    );
  }

  if (!data.result) return <Shell><p className="muted">결과를 불러오는 중…</p></Shell>;
  return <Report r={data.result} answers={data.answers} gradedAt={data.graded_at} onNew={newExam} />;
}

/* ---------------- 보고서 ---------------- */

function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-h`} style={{ display: 'grid', gap: 14, paddingTop: 8, scrollMarginTop: 24 }}>
      <h2 id={`${id}-h`}>{title}</h2>
      {children}
    </section>
  );
}
const Chip = ({ n }: { n: number }) => <a className="chip" href={`#item-${n}`} aria-label={`${n}번 문항 보기`}>{n}번</a>;
const Quote = ({ children }: { children: ReactNode }) => (
  <q lang="en" style={{ display: 'block', borderLeft: '3px solid var(--line-strong)', padding: '2px 0 2px 12px', color: 'var(--ink)', quotes: 'none' }}>{children}</q>
);

function Report({ r, answers, gradedAt, onNew }: { r: EvaluationResult; answers: ResultItemOut[]; gradedAt: string | null; onNew: () => void }) {
  const scope = r.evaluation_scope;
  const tier = r.tier;
  const insufficient = r.assessment_status === 'insufficient_evidence';
  const imHeld = !insufficient && r.base_level === 'IM' && r.estimated_level === null;
  const byOrder = new Map(answers.map((a) => [a.order_no, a]));
  const items = [...r.items].sort((a, b) => a.order_no - b.order_no);
  const scoredItems = items.filter((i) => i.evaluation_role === 'scored');
  const warmItems = items.filter((i) => i.evaluation_role === 'feedback_only');
  const toc: [string, string][] = [
    ['grade', '예상 수준'], ['why', '판단 근거'], ['fact', '영역별 진단'], ['coverage', '관찰 범위'], ['perf', '지속된 수행과 흔들린 부분'],
    ['cards', '연습 카드'], ['items', '문항별 상세'], ['more', '참고'],
  ];

  return (
    <Shell wide>
      <div style={{ display: 'grid', gridTemplateColumns: '200px minmax(0, 1fr)', gap: 48 }}>
        <nav aria-label="결과 목차" style={{ position: 'sticky', top: 24, alignSelf: 'start', display: 'grid', gap: 4 }}>
          {toc.map(([k, t]) => <a key={k} href={`#${k}`} className="btn-quiet" style={{ display: 'block', padding: '6px 8px', borderRadius: 6, color: 'var(--ink-soft)', textDecoration: 'none' }}>{t}</a>)}
          <button className="btn btn-ghost" style={{ marginTop: 16 }} onClick={onNew}>새 시험 보기</button>
          <button className="btn btn-ghost" disabled aria-label="AI와 더 이야기하기, 준비 중">AI 대화 (준비 중)</button>
        </nav>

        <article style={{ display: 'grid', gap: 40, maxWidth: 820 }}>
          {/* 안내 띠: 항상 */}
          <div className="notice" role="note">
            <p>전사(STT) 기반 추정이에요. 채점 대상 {scope.scored_order_nos.length}문항으로 판단했고, 자기소개({scope.feedback_only_order_nos.join(', ')}번)는 채점에서 제외했어요. 발음은 평가하지 않았어요.</p>
            {scope.unusable_items.length > 0 && (
              <p style={{ marginTop: 6 }}>확인할 수 없었던 답변: {scope.unusable_items.map((u) => `${u.order_no}번(${u.reason})`).join(', ')}. 이 답변은 낮은 점수가 아니라 판단에서 빠졌어요.</p>
            )}
          </div>

          <Section id="grade" title="예상 수준">
            <div className="sheet" style={{ padding: 24, display: 'grid', gap: 14, borderTop: `6px solid ${tier?.color ?? 'var(--line-strong)'}` }}>
              {insufficient ? (
                <>
                  <p style={{ fontSize: '1.6rem', fontWeight: 700 }}>판단 근거가 부족해요</p>
                  <p className="muted prose-w">{r.insufficient_reason}</p>
                </>
              ) : imHeld ? (
                <>
                  <p style={{ fontSize: '1.6rem', fontWeight: 700 }}>예상 IM <span className="muted" style={{ fontSize: '1rem', fontWeight: 500 }}>(세분화 보류)</span></p>
                  <p className="muted prose-w">{r.insufficient_reason}</p>
                </>
              ) : (
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 14, flexWrap: 'wrap' }}>
                  <p style={{ fontSize: '2.25rem', fontWeight: 700, lineHeight: 1 }}>예상 {r.estimated_level}</p>
                  {r.provisional_label && <span className="badge badge-none" style={{ fontSize: '0.9rem' }}>{r.provisional_label}</span>}
                  {tier && <span className="faint">{TIER_NAME[tier.name] ?? tier.name} 티어</span>}
                </div>
              )}
              <p className="prose-w">{r.headline}</p>
              {r.borderline_levels.length > 0 && (
                <p className="muted">경계 후보: {(r.estimated_level ? [r.estimated_level, ...r.borderline_levels] : r.borderline_levels).join(' ↔ ')}
                  {r.uncertainty_reasons.length > 0 && <> — {r.uncertainty_reasons.join(' / ')}</>}</p>
              )}
              {(imHeld || insufficient) && r.additional_tasks_needed.length > 0 && (
                <p className="faint">더 정확히 보려면 아래 "참고"의 추가로 필요한 답변을 연습해 보세요.</p>
              )}
            </div>
          </Section>

          <Section id="why" title="판단 근거">
            <dl style={{ display: 'grid', gap: 16, margin: 0 }}>
              {[['왜 이 수준인가', r.why_this_level], ['아래 수준보다 나은 점', r.why_not_lower], ['다음 수준까지 필요한 것', r.next_level_gap]].map(([t, v]) => (
                <div key={t} style={{ display: 'grid', gridTemplateColumns: '180px 1fr', gap: 16 }}>
                  <dt style={{ fontWeight: 600 }}>{t}</dt><dd style={{ margin: 0 }} className="prose-w">{v}</dd>
                </div>
              ))}
            </dl>
            {r.grade_rationale && <p className="muted prose-w">{r.grade_rationale}</p>}
          </Section>

          <Section id="fact" title="영역별 진단">
            <p className="faint">점수가 아니라 관찰한 내용이에요.</p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 1, background: 'var(--line)', border: '1px solid var(--line)', borderRadius: 'var(--radius-m)', overflow: 'hidden' }}>
              {(['functions_tasks', 'accuracy', 'context_content', 'text_type'] as const).map((k) => {
                const d = r.dimension_feedback[k];
                return (
                  <div key={k} style={{ background: 'var(--sheet)', padding: 18, display: 'grid', gap: 8, alignContent: 'start' }}>
                    <h3>{FACT_LABEL[k]}</h3>
                    <p>{d.summary}</p>
                    {d.evidence_order_nos.length > 0 && <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>{d.evidence_order_nos.map((n) => <Chip key={n} n={n} />)}</div>}
                    {d.limitations.length > 0 && <p className="faint">한계: {d.limitations.join(' / ')}</p>}
                  </div>
                );
              })}
            </div>
            {r.fact_evidence.length > 0 && (
              <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: 10 }}>
                {r.fact_evidence.map((f, i) => (
                  <li key={i} style={{ display: 'grid', gap: 4 }}>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                      <span className={`badge ${f.status === 'demonstrated' ? 'badge-ok' : f.status === 'not_demonstrated' ? 'badge-no' : 'badge-none'}`}>{FACT_STATUS_LABEL[f.status]}</span>
                      <span className="faint">{FACT_LABEL[f.criterion]}</span>
                      {f.order_no != null && <Chip n={f.order_no} />}
                    </div>
                    <p>{f.observation}</p>
                    {f.quote && <Quote>{f.quote}</Quote>}
                  </li>
                ))}
              </ul>
            )}
          </Section>

          <Section id="coverage" title="관찰 범위">
            <p className="faint">이번 시험의 채점 문항이 실제로 물어본 것이에요. 묻지 않은 항목은 감점하지 않아요.</p>
            {([['기능', r.coverage.functions, FUNCTION_LABEL], ['시간대', r.coverage.time_frames, TIME_LABEL], ['맥락', r.coverage.contexts, CONTEXT_LABEL]] as const).map(([t, list, map]) => (
              <div key={t} style={{ display: 'grid', gap: 6 }}>
                <h3>{t}</h3>
                <table style={{ borderCollapse: 'collapse', width: '100%' }}>
                  <thead><tr className="faint" style={{ textAlign: 'left' }}><th scope="col" style={{ padding: '4px 8px' }}>항목</th><th scope="col">출제된 문항</th><th scope="col">확인 가능</th><th scope="col">빈 곳</th></tr></thead>
                  <tbody>
                    {list.map((c) => (
                      <tr key={c.name} style={{ borderTop: '1px solid var(--line)' }}>
                        <th scope="row" style={{ padding: '8px', textAlign: 'left', fontWeight: 500 }}>{labelOf(map, c.name)}</th>
                        <td>{c.elicited_order_nos.length ? c.elicited_order_nos.join(', ') : '묻지 않음'}</td>
                        <td>{c.usable_order_nos.length ? c.usable_order_nos.join(', ') : '-'}</td>
                        <td className="muted">{c.gaps.join(' / ') || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </Section>

          <Section id="perf" title="지속된 수행과 흔들린 부분">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 24 }}>
              <div style={{ display: 'grid', gap: 12, alignContent: 'start' }}>
                <h3>여러 답변에서 유지된 것</h3>
                {r.sustained_performance.length ? r.sustained_performance.map((p, i) => (
                  <div key={i} style={{ display: 'grid', gap: 6 }}>
                    <strong>{p.capability}</strong><p className="muted">{p.summary}</p>
                    {p.evidence.map((e, j) => <div key={j} style={{ display: 'grid', gap: 2 }}><Chip n={e.order_no} /><Quote>{e.quote}</Quote></div>)}
                  </div>
                )) : <p className="faint">기록 없음</p>}
              </div>
              <div style={{ display: 'grid', gap: 12, alignContent: 'start' }}>
                <h3>요구가 커질 때 흔들린 것</h3>
                {r.breakdown_observations.length ? r.breakdown_observations.map((b, i) => (
                  <div key={i} style={{ display: 'grid', gap: 6 }}>
                    <strong>{labelOf(FUNCTION_LABEL, b.demanded_function)}</strong>
                    <p className="muted">{b.communicative_impact}</p>
                    {b.recovery && <p className="faint">회복: {b.recovery}</p>}
                    {b.evidence.map((e, j) => <div key={j} style={{ display: 'grid', gap: 2 }}><Chip n={e.order_no} /><Quote>{e.quote}</Quote></div>)}
                  </div>
                )) : <p className="faint">눈에 띄게 흔들린 부분은 관찰되지 않았어요.</p>}
              </div>
            </div>
          </Section>

          <Section id="cards" title="연습 카드">
            {r.feedback_cards.length === 0 ? <p className="faint">이번 결과로는 연습 카드를 만들 근거가 부족해요.</p> : (
              <ol style={{ margin: 0, paddingLeft: '1.25rem', display: 'grid', gap: 20 }}>
                {r.feedback_cards.map((c, i) => (
                  <li key={i} style={{ display: 'grid', gap: 8 }}>
                    <h3>{c.title}</h3>
                    <p className="muted">{c.why}</p>
                    {c.example_kind === 'correction' && c.before ? (
                      <div style={{ display: 'grid', gridTemplateColumns: '90px 1fr', gap: '6px 12px' }}>
                        <span className="faint">내 답변</span><Quote>{c.before}</Quote>
                        <span className="faint">고쳐 보기</span><p lang="en" style={{ fontWeight: 500 }}>{c.after}</p>
                      </div>
                    ) : (
                      <div style={{ display: 'grid', gridTemplateColumns: '90px 1fr', gap: '6px 12px' }}>
                        <span className="faint">새 연습 예시</span><p lang="en" style={{ fontWeight: 500 }}>{c.after}</p>
                      </div>
                    )}
                    <p><span className="faint">다음 답변에서 확인할 점 </span>{c.success_condition}</p>
                    {c.related_order_nos.length > 0 && <div style={{ display: 'flex', gap: 6 }}>{c.related_order_nos.map((n) => <Chip key={n} n={n} />)}</div>}
                  </li>
                ))}
              </ol>
            )}
          </Section>

          <Section id="items" title="문항별 상세">
            {scoredItems.map((it) => <ItemDetail key={it.order_no} it={it} a={byOrder.get(it.order_no)} />)}
            {warmItems.length > 0 && (
              <div style={{ display: 'grid', gap: 12, borderTop: '1px dashed var(--line-strong)', paddingTop: 16 }}>
                <h3>채점 제외 · 연습 피드백</h3>
                {warmItems.map((it) => <ItemDetail key={it.order_no} it={it} a={byOrder.get(it.order_no)} warm />)}
              </div>
            )}
          </Section>

          <Section id="more" title="참고">
            {r.additional_tasks_needed.length > 0 && (
              <div style={{ display: 'grid', gap: 8 }}>
                <h3>다음에 연습해 볼 질문</h3>
                <p className="faint">이번 시험 문항이 아니라, 더 정확히 확인하려면 필요한 연습 질문이에요.</p>
                <ul style={{ margin: 0, paddingLeft: '1.2rem', display: 'grid', gap: 8 }}>
                  {r.additional_tasks_needed.map((t, i) => <li key={i}><span lang="en">{t.suggested_question}</span><br /><span className="faint">{labelOf(FUNCTION_LABEL, t.target_function)} · {t.reason}</span></li>)}
                </ul>
              </div>
            )}
            <details>
              <summary style={{ cursor: 'pointer', fontWeight: 600 }}>속도·멈춤 관찰 (STT 기반 참고치)</summary>
              <p className="muted prose-w" style={{ marginTop: 8 }}>{r.fluency_observations}</p>
            </details>
            {r.limitations.length > 0 && <div><h3>이번 결과의 한계</h3><ul className="muted" style={{ margin: '6px 0 0', paddingLeft: '1.2rem' }}>{r.limitations.map((l, i) => <li key={i}>{l}</li>)}</ul></div>}
            <p className="faint">{r.disclaimer}</p>
            <p className="faint">기준 {r.rubric_version}{r.im_rubric_version ? ` · IM 세분화 ${r.im_rubric_version}` : ''}{gradedAt ? ` · 평가 ${new Date(gradedAt).toLocaleString('ko-KR')}` : ''}</p>
          </Section>
        </article>
      </div>
      <Live>평가 결과가 준비됐어요</Live>
    </Shell>
  );
}

function ItemDetail({ it, a, warm = false }: { it: EvaluationResult['items'][number]; a?: ResultItemOut; warm?: boolean }) {
  return (
    <details id={`item-${it.order_no}`} className="sheet" style={{ padding: '14px 18px', scrollMarginTop: 24 }} open={false}>
      <summary style={{ cursor: 'pointer', display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
        <strong>{it.order_no}번</strong>
        <span className="faint">{a ? labelOf(TYPE_LABEL, a.question_type) : ''}</span>
        {warm ? <span className="badge badge-none">채점 제외</span>
          : <span className={`badge ${it.task_fulfillment === 'fulfilled' ? 'badge-ok' : it.task_fulfillment === 'not_assessable' ? 'badge-none' : 'badge-no'}`}>{FULFILL_LABEL[it.task_fulfillment]}</span>}
      </summary>
      <div style={{ display: 'grid', gap: 12, marginTop: 12 }}>
        {a && <p lang="en" className="muted">{a.question_text}</p>}
        {a && <div><span className="faint">내 답변(전사)</span><p lang="en">{a.stt_text || '전사 없음'}</p></div>}
        {it.evidence.length > 0 && <div style={{ display: 'grid', gap: 4 }}><span className="faint">근거</span>{it.evidence.map((e, i) => <Quote key={i}>{e}</Quote>)}</div>}
        {it.mistakes.length > 0 && (
          <div style={{ display: 'grid', gap: 8 }}>
            <span className="faint">고칠 점</span>
            {it.mistakes.map((m, i) => <div key={i} style={{ display: 'grid', gap: 2 }}><Quote>{m.quote}</Quote><p className="muted">{m.problem}</p><p lang="en" style={{ fontWeight: 500 }}>{m.fix}</p></div>)}
          </div>
        )}
        {it.upgrade_tip && <p><span className="faint">다음 연습 </span>{it.upgrade_tip}</p>}
        {a?.metrics && (
          <p className="faint">관측치 · 길이 {a.metrics.duration_sec}초 · 단어 {a.metrics.word_count}개 · 분당 {a.metrics.wpm}단어 · 긴 멈춤 {a.metrics.long_pause_count}회
            {a.metrics.observed_filler_per100 != null ? ` · 필러 100단어당 ${a.metrics.observed_filler_per100}` : ''}</p>
        )}
      </div>
    </details>
  );
}
