// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// OWNER: frontend (contracts.yaml ownership)
// 마이크 녹음 도우미: 형식 선택(webm/opus → ogg → mp4), 실시간 음량, 최대 음량, 최대 길이 자동 종료.
export const RECORD_MIN_MS = 2000;      // contracts policies.record_min_ms
export const RECORD_MAX_MS = 120000;    // contracts policies.record_max_ms
export const SILENCE_PEAK = 0.02;       // 이보다 작으면 거의 무음으로 보고 업로드하지 않는다(클라이언트 사전 확인)

const CANDIDATES = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/ogg', 'audio/mp4'];
const EXT: Record<string, string> = { 'audio/webm': 'webm', 'audio/ogg': 'ogg', 'audio/mp4': 'm4a' };

export function pickMime(): string | null {
  if (typeof MediaRecorder === 'undefined') return null;
  return CANDIDATES.find((m) => MediaRecorder.isTypeSupported?.(m)) ?? null;
}
export function extFor(mime: string): string { return EXT[mime.split(';')[0]] ?? 'webm'; }

export type MicErrorKind = 'denied' | 'not_found' | 'unsupported' | 'other';
export function micErrorKind(e: unknown): MicErrorKind {
  const n = (e as { name?: string })?.name;
  if (n === 'NotAllowedError' || n === 'SecurityError') return 'denied';
  if (n === 'NotFoundError' || n === 'OverconstrainedError') return 'not_found';
  if (n === 'unsupported') return 'unsupported';
  return 'other';
}

export async function openMic(): Promise<MediaStream> {
  if (!navigator.mediaDevices?.getUserMedia || !pickMime()) throw Object.assign(new Error('unsupported'), { name: 'unsupported' });
  return navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
}

/** 스트림의 실시간 음량(0~1)을 콜백으로 보낸다. 반환값은 정리 함수. */
export function meter(stream: MediaStream, onLevel: (rms: number) => void): () => void {
  const Ctor = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!Ctor) return () => {};
  const ctx = new Ctor();
  const src = ctx.createMediaStreamSource(stream);
  const an = ctx.createAnalyser();
  an.fftSize = 1024;
  src.connect(an);
  const buf = new Float32Array(an.fftSize);
  let raf = 0;
  const tick = () => {
    an.getFloatTimeDomainData(buf);
    let sum = 0;
    for (const v of buf) sum += v * v;
    onLevel(Math.sqrt(sum / buf.length));
    raf = requestAnimationFrame(tick);
  };
  raf = requestAnimationFrame(tick);
  return () => { cancelAnimationFrame(raf); src.disconnect(); void ctx.close(); };
}

export interface Recording { blob: Blob; mime: string; durationMs: number; peak: number }

export class Recorder {
  private rec: MediaRecorder | null = null;
  private chunks: Blob[] = [];
  private started = 0;
  private peak = 0;
  private stopMeter: () => void = () => {};
  private timer = 0;
  private resolve: ((r: Recording) => void) | null = null;
  readonly mime: string;
  private stream: MediaStream;
  private onLevel?: (rms: number) => void;

  constructor(stream: MediaStream, onLevel?: (rms: number) => void) {
    this.stream = stream;
    this.onLevel = onLevel;
    this.mime = pickMime() ?? 'audio/webm';
  }

  start(maxMs = RECORD_MAX_MS): Promise<Recording> {
    this.chunks = [];
    this.peak = 0;
    this.rec = new MediaRecorder(this.stream, { mimeType: this.mime });
    this.rec.ondataavailable = (e) => { if (e.data.size) this.chunks.push(e.data); };
    this.rec.onstop = () => {
      const durationMs = performance.now() - this.started;
      this.stopMeter();
      window.clearTimeout(this.timer);
      const type = this.rec?.mimeType || this.mime;
      this.resolve?.({ blob: new Blob(this.chunks, { type: type.split(';')[0] }), mime: type.split(';')[0], durationMs, peak: this.peak });
      this.resolve = null;
    };
    this.stopMeter = meter(this.stream, (rms) => { this.peak = Math.max(this.peak, rms); this.onLevel?.(rms); });
    this.started = performance.now();
    this.rec.start(250);
    this.timer = window.setTimeout(() => this.stop(), maxMs);
    return new Promise((res) => { this.resolve = res; });
  }

  elapsedMs(): number { return this.rec?.state === 'recording' ? performance.now() - this.started : 0; }

  stop() { if (this.rec?.state === 'recording') this.rec.stop(); }
}
