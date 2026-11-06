// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// OWNER: tts-host (contracts.yaml ownership)
//
// 진행자 음성 재생기 (contracts.yaml frontend_interfaces.host).
// - HTMLAudioElement + 공유 AudioContext + AnalyserNode(fftSize 512). Host 애니메이션은 getAnalyser()로 같은 컨텍스트를 쓴다.
// - play(url) → 'ended' | 'blocked'(autoplay 차단: 화면이 "눌러서 듣기"로 사용자 동작 재시도) | 'error'(로드 실패: 같은 문항 재시도)
// - speechSynthesis(Web Speech)는 절대 쓰지 않는다. TTS mp3가 없으면 시험을 진행하지 않는 것이 요구사항이다.
import { useCallback, useEffect, useRef, useState } from 'react';

export type PlayResult = 'ended' | 'blocked' | 'error';

export interface TtsPlayer {
  unlock(): Promise<void>;
  play(url: string): Promise<PlayResult>;
  stop(): void;
  isPlaying: boolean;
  getAnalyser(): AnalyserNode | null;
}

// 페이지 전체에서 오디오 그래프는 하나만 둔다(같은 <audio>를 MediaElementSource로 두 번 연결할 수 없음).
let sharedCtx: AudioContext | null = null;
let sharedAnalyser: AnalyserNode | null = null;
let sharedAudio: HTMLAudioElement | null = null;

function ensureGraph(): { ctx: AudioContext | null; audio: HTMLAudioElement; analyser: AnalyserNode | null } {
  if (!sharedAudio) {
    sharedAudio = new Audio();
    sharedAudio.crossOrigin = 'anonymous';
    sharedAudio.preload = 'auto';
  }
  if (!sharedCtx) {
    const Ctor = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (Ctor) {
      try {
        sharedCtx = new Ctor();
        const src = sharedCtx.createMediaElementSource(sharedAudio);
        sharedAnalyser = sharedCtx.createAnalyser();
        sharedAnalyser.fftSize = 512;
        src.connect(sharedAnalyser);
        sharedAnalyser.connect(sharedCtx.destination);
      } catch {
        // Web Audio를 못 쓰는 환경: 재생은 HTMLAudioElement만으로 계속(애니메이션은 재생 이벤트 기반으로 단순화)
        sharedCtx = null;
        sharedAnalyser = null;
      }
    }
  }
  return { ctx: sharedCtx, audio: sharedAudio, analyser: sharedAnalyser };
}

export function useTtsPlayer(): TtsPlayer {
  const [isPlaying, setPlaying] = useState(false);
  const settle = useRef<((r: PlayResult) => void) | null>(null);
  const token = useRef(0);

  const finish = useCallback((r: PlayResult) => {
    setPlaying(false);
    const fn = settle.current;
    settle.current = null;
    fn?.(r);
  }, []);

  const unlock = useCallback(async () => {
    const { ctx } = ensureGraph();
    if (ctx && ctx.state === 'suspended') {
      try {
        await ctx.resume();
      } catch {
        /* 다음 사용자 동작에서 다시 시도 */
      }
    }
  }, []);

  const stop = useCallback(() => {
    token.current++;
    const audio = sharedAudio;
    if (audio) {
      audio.pause();
      audio.currentTime = 0;
    }
    if (settle.current) finish('ended');
  }, [finish]);

  const play = useCallback(
    (url: string) =>
      new Promise<PlayResult>((resolve) => {
        const { ctx, audio } = ensureGraph();
        if (settle.current) finish('ended'); // 이전 재생은 끝난 것으로 처리(동시 재생 없음)
        const my = ++token.current;          // 이 재생의 번호. 늦게 도착한 이전 재생의 결과는 무시한다
        settle.current = resolve;
        const done = (r: PlayResult) => { cleanup(); if (my === token.current) finish(r); };
        const onEnded = () => done('ended');
        const onError = () => done('error');
        const cleanup = () => {
          audio.removeEventListener('ended', onEnded);
          audio.removeEventListener('error', onError);
        };
        audio.addEventListener('ended', onEnded);
        audio.addEventListener('error', onError);
        audio.src = url;
        const start = async () => {
          if (ctx && ctx.state === 'suspended') {
            try { await ctx.resume(); } catch { /* play()가 차단 여부를 알려 준다 */ }
          }
          if (my !== token.current) return;
          try {
            await audio.play();
            if (my === token.current) setPlaying(true);
          } catch (e) {
            const name = (e as { name?: string })?.name;
            if (name === 'AbortError') { cleanup(); return; } // 새 재생/정지로 중단됨 — 오류 아님
            done(name === 'NotAllowedError' ? 'blocked' : 'error');
          }
        };
        void start();
      }),
    [finish],
  );

  useEffect(() => () => { if (settle.current) stop(); }, [stop]);

  const getAnalyser = useCallback(() => sharedAnalyser, []);

  return { unlock, play, stop, isPlaying, getAnalyser };
}
