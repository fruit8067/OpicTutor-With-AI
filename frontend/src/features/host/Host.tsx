// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// 후속 수정: REC 문구의 AA 대비는 OpenAI Codex의 도움으로 작성되었습니다.
// OWNER: tts-host (contracts.yaml ownership)
//
// 진행자 캐릭터 "린"(오리지널 SVG, 단순 도형). 실존 시험 진행자·알려진 캐릭터를 닮지 않게 만든 둥근 말풍선형 캐릭터.
// state: idle(느린 숨쉬기) / speaking(음량 → 통통·미세 회전·입 크기) / listening(귀 기울임 + 녹음 점) / processing(생각 점 3개)
// - 음량은 useTtsPlayer와 같은 AnalyserNode(공유 그래프)에서 읽고 지수 평활 0.25로 부드럽게 한다.
// - prefers-reduced-motion이면 몸 움직임 없이 입 모양만 바뀐다. 크기는 viewBox로 부모에 맞춘다.
import { useEffect, useRef, useState } from 'react';
import { useTtsPlayer } from './useTtsPlayer';

export type HostState = 'idle' | 'speaking' | 'listening' | 'processing';

const SMOOTH = 0.25;

function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(
    () => typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches,
  );
  useEffect(() => {
    const mq = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    if (!mq) return;
    const on = () => setReduced(mq.matches);
    mq.addEventListener('change', on);
    return () => mq.removeEventListener('change', on);
  }, []);
  return reduced;
}

export function Host({ state, className }: { state: HostState; className?: string }) {
  const { getAnalyser } = useTtsPlayer();
  const reduced = usePrefersReducedMotion();
  const [frame, setFrame] = useState({ level: 0, t: 0 });
  const level = useRef(0);
  const buf = useRef<Uint8Array<ArrayBuffer> | null>(null);
  const raf = useRef(0);

  useEffect(() => {
    const start = performance.now();
    const tick = (now: number) => {
      let target = 0;
      if (state === 'speaking') {
        const an = getAnalyser();
        if (an) {
          if (!buf.current || buf.current.length !== an.fftSize) buf.current = new Uint8Array(an.fftSize);
          an.getByteTimeDomainData(buf.current);
          let sum = 0;
          for (const v of buf.current) { const x = (v - 128) / 128; sum += x * x; }
          target = Math.min(1, Math.sqrt(sum / buf.current.length) * 4);
        } else {
          target = 0.35 + 0.25 * Math.sin(now / 90); // Web Audio 없는 환경: 재생 중 고정 리듬
        }
      }
      level.current += (target - level.current) * SMOOTH;
      setFrame({ level: level.current, t: (now - start) / 1000 });
      raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current);
  }, [state, getAnalyser]);

  const { level: lv, t } = frame;
  const move = !reduced;
  const breathe = move ? Math.sin(t * 1.6) * 1.5 : 0;
  const bounce = move && state === 'speaking' ? -lv * 6 : 0;
  const tilt = move ? (state === 'speaking' ? Math.sin(t * 5) * lv * 3 : state === 'listening' ? -8 : 0) : 0;
  const mouthOpen = state === 'speaking' ? 2 + lv * 12 : state === 'processing' ? 1.5 : 2;
  const blink = move && Math.sin(t * 0.9) > 0.985;
  const label = { idle: '진행자 대기 중', speaking: '진행자가 말하는 중', listening: '답변을 듣는 중', processing: '답변을 처리하는 중' }[state];

  return (
    <svg viewBox="0 0 200 200" className={className} role="img" aria-label={label} data-state={state}
         style={{ width: '100%', height: 'auto', overflow: 'visible' }}>
      <ellipse cx="100" cy="186" rx={46 - lv * 6} ry="6" fill="currentColor" opacity="0.12" />
      <g transform={`translate(0 ${breathe + bounce}) rotate(${tilt} 100 110)`}>
        {/* 귀(둥근 안테나) */}
        <circle cx="52" cy="58" r="13" fill="#FFB4A2" />
        <circle cx="148" cy="58" r={state === 'listening' ? 16 : 13} fill="#FFB4A2" />
        {/* 몸 */}
        <rect x="40" y="52" width="120" height="122" rx="56" fill="#FFD6C9" />
        <rect x="58" y="128" width="84" height="34" rx="17" fill="#FFC1AE" />
        {/* 눈 */}
        <g fill="#3B2F2F">
          {blink ? (
            <>
              <rect x="70" y="98" width="16" height="3" rx="1.5" />
              <rect x="114" y="98" width="16" height="3" rx="1.5" />
            </>
          ) : (
            <>
              <circle cx="78" cy="99" r="7" />
              <circle cx="122" cy="99" r="7" />
              <circle cx="80.5" cy="96.5" r="2" fill="#fff" />
              <circle cx="124.5" cy="96.5" r="2" fill="#fff" />
            </>
          )}
        </g>
        {/* 볼 */}
        <circle cx="66" cy="116" r="7" fill="#FF8FA3" opacity="0.45" />
        <circle cx="134" cy="116" r="7" fill="#FF8FA3" opacity="0.45" />
        {/* 입 */}
        <ellipse cx="100" cy="122" rx={state === 'speaking' ? 9 + lv * 3 : 8} ry={mouthOpen} fill="#7A2E3A" />
      </g>
      {state === 'listening' && (
        <g aria-hidden="true">
          <circle cx="172" cy="28" r="7" fill="#b83e37">
            {move && <animate attributeName="opacity" values="1;0.3;1" dur="1.2s" repeatCount="indefinite" />}
          </circle>
          <text x="160" y="32" fontSize="11" textAnchor="end" fill="#b83e37" fontWeight="600">REC</text>
        </g>
      )}
      {state === 'processing' && (
        <g aria-hidden="true" fill="currentColor" opacity="0.6">
          {[0, 1, 2].map((i) => (
            <circle key={i} cx={150 + i * 12} cy="30" r="4"
                    opacity={move ? 0.3 + 0.7 * Math.max(0, Math.sin(t * 4 - i * 0.8)) : 0.7} />
          ))}
        </g>
      )}
    </svg>
  );
}
