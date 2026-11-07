// AI-assisted: 마이크 장치 선택 회귀 테스트는 Claude(Anthropic)의 도움으로 작성되었습니다.
// OWNER: frontend.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { listMics, openMic, toLevel } from '../src/lib/recorder.ts';

type Constraints = { audio: { deviceId?: { exact: string } } };
function install(getUserMedia: (c: Constraints) => Promise<unknown>, devices: unknown[] = []) {
  Object.defineProperty(globalThis, 'navigator', { configurable: true,
    value: { mediaDevices: { getUserMedia, enumerateDevices: async () => devices } } });
  (globalThis as Record<string, unknown>).MediaRecorder = { isTypeSupported: () => true };
}

test('저장된 마이크가 사라졌으면 기본 마이크로 다시 연다', async () => {
  const calls: Constraints[] = [];
  install(async (c) => {
    calls.push(c);
    if (c.audio.deviceId) throw Object.assign(new Error('gone'), { name: 'OverconstrainedError' });
    return 'default-stream';
  });
  assert.equal(await openMic('old-id'), 'default-stream');
  assert.deepEqual(calls.map((c) => c.audio.deviceId?.exact ?? null), ['old-id', null]);
});

test('권한 거부는 기본 마이크로 우회하지 않고 그대로 알린다', async () => {
  install(async () => { throw Object.assign(new Error('no'), { name: 'NotAllowedError' }); });
  await assert.rejects(openMic('some-id'), { name: 'NotAllowedError' });
});

test('마이크 목록은 입력 장치만, 이름이 없으면 번호로 보여 준다', async () => {
  install(async () => null, [
    { kind: 'audioinput', deviceId: 'a', label: '' }, { kind: 'audiooutput', deviceId: 'b', label: 'Speaker' },
    { kind: 'audioinput', deviceId: 'c', label: 'USB Mic' },
  ]);
  assert.deepEqual(await listMics(), [{ deviceId: 'a', label: '마이크 1' }, { deviceId: 'c', label: 'USB Mic' }]);
});

test('표시 음량은 0~1로 자른다', () => {
  assert.equal(toLevel(0), 0);
  assert.equal(toLevel(1), 1);
  assert.ok(toLevel(0.05) > 0.25 && toLevel(0.05) < 0.35);
});
