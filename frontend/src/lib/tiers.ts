// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// backend/app/contracts.yaml의 tiers 표를 화면 표시용으로 옮긴 상수다. 계약이 바뀌면 함께 고친다.
// 등급을 계산하지 않는다. 서버가 준 estimated_level의 위치를 보여 줄 때만 쓴다.
import type { level } from '../api/types';

export interface TierDef { name: string; label: string; color: string; levels: level[] }

// 아래(브론즈)에서 위(다이아몬드) 순서
export const TIERS: TierDef[] = [
  { name: 'bronze', label: '브론즈', color: '#B0794A', levels: ['NL', 'NM', 'NH'] },
  { name: 'silver', label: '실버', color: '#A8B3BD', levels: ['IL', 'IM1'] },
  { name: 'gold', label: '골드', color: '#E3B341', levels: ['IM2', 'IM3'] },
  { name: 'platinum', label: '플래티넘', color: '#4FC3C7', levels: ['IH'] },
  { name: 'diamond', label: '다이아몬드', color: '#7C8CFF', levels: ['AL'] },
];

export const TIER_NAME: Record<string, string> = Object.fromEntries(TIERS.map((t) => [t.name, t.label]));

export function tierOfLevel(lv: level | null): TierDef | null {
  return lv ? TIERS.find((t) => t.levels.includes(lv)) ?? null : null;
}
