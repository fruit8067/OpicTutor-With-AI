// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// OWNER: frontend (contracts.yaml ownership)
import { useEffect, useRef } from 'react';

/** fn을 즉시 1회, 이후 interval마다 호출. fn이 false를 돌려주면 멈춘다. 이전 호출이 끝나기 전엔 겹치지 않는다. */
export function usePoll(fn: () => Promise<boolean | void>, interval: number, enabled = true) {
  const ref = useRef(fn);
  useEffect(() => { ref.current = fn; });
  useEffect(() => {
    if (!enabled) return;
    const st = { stopped: false, timer: 0 };
    const run = async () => {
      const again = await ref.current().catch(() => true);
      if (!st.stopped && again !== false) st.timer = window.setTimeout(run, interval);
    };
    void run();
    return () => { st.stopped = true; window.clearTimeout(st.timer); };
  }, [interval, enabled]);
}
