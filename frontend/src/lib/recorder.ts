// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// 후속 수정: 녹음 오류·장치 해제 복구는 OpenAI Codex의 도움으로 작성되었습니다.
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
  readonly mime: string;
  private stream: MediaStream;
  private onLevel?: (rms: number) => void;

  constructor(stream: MediaStream, onLevel?: (rms: number) => void) {
    this.stream = stream;
    this.onLevel = onLevel;
    this.mime = pickMime() ?? 'audio/webm';
  }

  start(maxMs = RECORD_MAX_MS): Promise<Recording> {
    if (this.rec?.state === 'recording') return Promise.reject(new Error('이미 녹음 중입니다.'));
    this.chunks = [];
    this.peak = 0;
    return new Promise((resolve, reject) => {
      let settled = false;
      const tracks = this.stream.getAudioTracks();
      const cleanup = () => {
        window.clearTimeout(this.timer);
        this.stopMeter();
        this.stopMeter = () => {};
        tracks.forEach((track) => track.removeEventListener('ended', ended));
        if (this.rec) {
          this.rec.onstop = null;
          this.rec.onerror = null;
          this.rec.ondataavailable = null;
        }
      };
      const fail = (error: unknown) => {
        if (settled) return;
        settled = true;
        cleanup();
        if (this.rec?.state === 'recording') this.rec.stop();
        reject(error);
      };
      const ended = () => fail(new Error('마이크 연결이 끊어졌어요. 다시 연결한 뒤 녹음해 주세요.'));
      try {
        if (!tracks.some((track) => track.readyState === 'live')) throw new Error('마이크 연결을 확인해 주세요.');
        this.rec = new MediaRecorder(this.stream, { mimeType: this.mime });
        this.rec.ondataavailable = (event) => { if (event.data.size) this.chunks.push(event.data); };
        this.rec.onerror = () => fail(new Error('녹음하지 못했어요. 마이크를 확인하고 다시 시도해 주세요.'));
        this.rec.onstop = () => {
          if (settled) return;
          const type = this.rec?.mimeType || this.mime;
          const blob = new Blob(this.chunks, { type: type.split(';')[0] });
          if (!blob.size) { fail(new Error('녹음된 소리가 없어요. 다시 녹음해 주세요.')); return; }
          settled = true;
          cleanup();
          resolve({ blob, mime: type.split(';')[0], durationMs: performance.now() - this.started, peak: this.peak });
        };
        tracks.forEach((track) => track.addEventListener('ended', ended, { once: true }));
        this.stopMeter = meter(this.stream, (rms) => { this.peak = Math.max(this.peak, rms); this.onLevel?.(rms); });
        this.started = performance.now();
        this.timer = window.setTimeout(() => this.stop(), maxMs);
        this.rec.start(250);
      } catch (error) { fail(error); }
    });
  }

  elapsedMs(): number { return this.rec?.state === 'recording' ? performance.now() - this.started : 0; }

  stop() { if (this.rec?.state === 'recording') this.rec.stop(); }
}
