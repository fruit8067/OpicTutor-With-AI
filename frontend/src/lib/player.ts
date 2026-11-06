// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// OWNER: frontend (contracts.yaml ownership)
// contracts frontend_interfaces.host의 useTtsPlayer를 쓰는 얇은 어댑터.
// tts-host 브랜치가 병합되기 전 bootstrap stub에는 unlock/isPlaying이 없어서, 없으면 안전하게 건너뛴다.
// (병합 후에도 그대로 동작한다. 화면은 이 훅만 쓴다)
import { useTtsPlayer } from '../features/host/useTtsPlayer';

export type PlayResult = 'ended' | 'blocked' | 'error';
export interface Player {
  unlock(): Promise<void>;
  play(url: string): Promise<PlayResult>;
  stop(): void;
}

export function usePlayer(): Player {
  const p = useTtsPlayer() as ReturnType<typeof useTtsPlayer> & { unlock?: () => Promise<void> };
  return {
    unlock: async () => { await p.unlock?.(); },
    play: async (url: string) => {
      try { return await p.play(url); } catch { return 'error'; }
    },
    stop: () => p.stop(),
  };
}
