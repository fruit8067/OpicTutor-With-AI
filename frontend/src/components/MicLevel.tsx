// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// OWNER: frontend (contracts.yaml ownership)
// 실시간 입력 음량 막대. 최근 음량을 오른쪽에서 왼쪽으로 흘려 보여 줘서 "내 목소리가 들어가고 있다"를 바로 알 수 있게 한다.
import { useEffect, useRef, useState } from 'react';

const BARS = 32;
const SILENT = Array<number>(BARS).fill(0);

export function MicLevel({ level, active, label, variant = 'rec' }: { level: number; active: boolean; label: string; variant?: 'rec' | 'test' }) {
  const [history, setHistory] = useState<number[]>(() => Array(BARS).fill(0));
  const latest = useRef(level);
  useEffect(() => { latest.current = level; }, [level]);
  useEffect(() => {
    if (!active) return;
    const t = window.setInterval(() => setHistory((h) => [...h.slice(1), latest.current]), 70);
    return () => window.clearInterval(t);
  }, [active]);
  const pct = Math.round(level * 100);
  return (
    <div className="miclevel" data-active={active} data-variant={variant} role="meter" aria-label={label}
         aria-valuemin={0} aria-valuemax={100} aria-valuenow={active ? pct : 0}>
      {(active ? history : SILENT).map((v, i) => (
        <span key={i} style={{ height: `${Math.max(8, Math.round(v * 100))}%` }} />
      ))}
    </div>
  );
}
