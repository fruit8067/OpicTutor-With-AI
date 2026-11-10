// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// 결과 화면의 9등급 티어 피라미드. 서버가 준 등급의 위치만 표시하고, 점수를 계산하거나 보정하지 않는다.
import type { level } from '../api/types';
import { TIERS, tierOfLevel } from '../lib/tiers';

interface Props {
  estimated: level | null;
  borderline: level[];
  imHeld: boolean;       // base_level=IM, 세분화 보류 → IM1~IM3 후보로 표시
  insufficient: boolean; // 판단 근거 부족 → 위치 표시 없음
}

const IM_SUB: level[] = ['IM1', 'IM2', 'IM3'];
// 위로 갈수록 좁아지는 폭(위 → 아래)
const ROW_WIDTH = ['38%', '52%', '70%', '85%', '100%'];

export function LevelPyramid({ estimated, borderline, imHeld, insufficient }: Props) {
  const rows = [...TIERS].reverse(); // 위: 다이아몬드
  const mine = insufficient ? null : estimated;
  const myTier = tierOfLevel(mine);
  const candidates = new Set<level>(insufficient ? [] : imHeld ? IM_SUB : borderline);
  const summary = insufficient
    ? '9단계 등급표. 판단 근거가 부족해 위치를 표시하지 않았어요.'
    : imHeld
      ? '9단계 등급표에서 IM1~IM3 중 하나로 예상돼요(세분화 보류).'
      : mine
        ? `9단계 등급표 중 ${mine}, ${myTier?.label ?? ''} 티어에 위치해요.`
        : '9단계 등급표';

  return (
    <figure className="level-pyramid" aria-label={summary} style={{ margin: 0 }}>
      <div className="lp-rows" aria-hidden="true">
        {rows.map((t, i) => {
          const tierActive = myTier?.name === t.name;
          return (
            <div key={t.name} className="lp-row">
              <span className={`lp-tier${tierActive ? ' lp-tier-on' : ''}`} style={tierActive ? { color: 'var(--ink)' } : undefined}>
                {t.label}
              </span>
              <div className="lp-cells" style={{ width: ROW_WIDTH[i] }}>
                {t.levels.map((lv) => {
                  const on = lv === mine;
                  const cand = !on && candidates.has(lv);
                  return (
                    <span
                      key={lv}
                      className={`lp-cell${on ? ' lp-on' : ''}${cand ? ' lp-cand' : ''}${insufficient ? ' lp-muted' : ''}`}
                      style={{
                        background: on ? t.color : `${t.color}${cand ? '40' : '26'}`,
                        borderColor: on || cand ? t.color : 'transparent',
                      }}
                    >
                      {lv}
                      {on && <span className="lp-me">나</span>}
                    </span>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
      <figcaption className="lp-legend faint">
        {insufficient ? '판단 근거가 부족해 위치를 표시하지 않았어요' : (
          <>
            {mine && <span><i className="lp-key lp-key-on" />내 위치</span>}
            {candidates.size > 0 && <span><i className="lp-key lp-key-cand" />{imHeld ? '세분화 후보' : '경계 후보'}</span>}
          </>
        )}
      </figcaption>
      <p className="sr-only">{summary}</p>
    </figure>
  );
}
