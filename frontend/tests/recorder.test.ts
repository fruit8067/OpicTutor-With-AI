// AI-assisted: 녹음 경계 회귀 검증은 OpenAI Codex의 도움으로 작성되었습니다.
// OWNER: frontend.
import { afterEach, beforeEach, test } from 'node:test';
import assert from 'node:assert/strict';
import { Recorder } from '../src/lib/recorder.ts';

let mode = 'normal';
class Track extends EventTarget {
  readyState = 'live';
  listeners = 0;
  active = new Set<unknown>();
  override addEventListener(...args: Parameters<EventTarget['addEventListener']>) { if (!this.active.has(args[1])) this.listeners++; this.active.add(args[1]); super.addEventListener(...args); }
  override removeEventListener(...args: Parameters<EventTarget['removeEventListener']>) { if (this.active.delete(args[1])) this.listeners--; super.removeEventListener(...args); }
}
class Media {
  static isTypeSupported() { return true; }
  state = 'inactive';
  mimeType = 'audio/webm';
  onstop: (() => void) | null = null;
  onerror: (() => void) | null = null;
  ondataavailable: ((event: { data: Blob }) => void) | null = null;
  constructor() { if (mode === 'constructor') throw new Error('constructor failure'); }
  start() {
    this.state = 'recording';
    if (mode === 'error') queueMicrotask(() => this.onerror?.());
  }
  stop() {
    this.state = 'inactive';
    this.ondataavailable?.({ data: new Blob(['synthetic recorded bytes']) });
    this.onstop?.();
  }
}
const globals = globalThis as unknown as { window: unknown; MediaRecorder: unknown };
const originalWindow = globals.window;
const originalMedia = globals.MediaRecorder;
beforeEach(() => {
  mode = 'normal';
  globals.window = { setTimeout, clearTimeout };
  globals.MediaRecorder = Media;
});
afterEach(() => { globals.window = originalWindow; globals.MediaRecorder = originalMedia; });
const recorder = (track: Track) => new Recorder({ getAudioTracks: () => [track] } as unknown as MediaStream);

test('constructor failure rejects and removes device listener', async () => {
  mode = 'constructor'; const track = new Track();
  await assert.rejects(recorder(track).start(100), /constructor failure/);
  assert.equal(track.listeners, 0);
});
test('asynchronous recording error rejects without a partial recording', async () => {
  mode = 'error'; const track = new Track();
  await assert.rejects(recorder(track).start(100), /녹음하지 못했어요/);
  assert.equal(track.listeners, 0);
});
test('device removal rejects and releases its listener', async () => {
  const track = new Track(); const pending = recorder(track).start(100);
  track.readyState = 'ended'; track.dispatchEvent(new Event('ended'));
  await assert.rejects(pending, /연결이 끊어졌어요/);
  assert.equal(track.listeners, 0);
});
test('maximum recording time stops and returns a nonempty recording', async () => {
  const track = new Track(); const value = await recorder(track).start(5);
  assert.ok(value.blob.size > 0); assert.ok(value.durationMs >= 0);
  assert.equal(track.listeners, 0);
});
