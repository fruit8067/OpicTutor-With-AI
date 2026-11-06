// AI-assisted: 이 코드는 Claude(Anthropic)의 도움으로 작성되었습니다.
// OWNER: tts-host (contracts.yaml ownership)
//
// 개발용 미리보기: 네 상태와 실제 mp3 재생을 확인한다. 라우트 연결 여부는 frontend 에이전트가 정한다.
// 예) <Route path="/__host" element={<HostDemo />} />
import { useState } from 'react';
import { Host, type HostState } from './Host';
import { useTtsPlayer } from './useTtsPlayer';

const STATES: HostState[] = ['idle', 'speaking', 'listening', 'processing'];

export default function HostDemo() {
  const player = useTtsPlayer();
  const [state, setState] = useState<HostState>('idle');
  const [url, setUrl] = useState('/media/tts/<voice_id>/host/greeting.mp3');
  const [result, setResult] = useState<string>('');

  const playIt = async () => {
    await player.unlock();
    setState('speaking');
    const r = await player.play(url);
    setResult(r);
    setState('idle');
  };

  return (
    <div style={{ maxWidth: 360, margin: '24px auto', fontFamily: 'system-ui' }}>
      <div style={{ width: 220, margin: '0 auto', color: '#3B2F2F' }}>
        <Host state={state} />
      </div>
      <div style={{ display: 'flex', gap: 8, justifyContent: 'center', flexWrap: 'wrap' }}>
        {STATES.map((s) => (
          <button key={s} onClick={() => setState(s)} aria-pressed={state === s}>{s}</button>
        ))}
      </div>
      <div style={{ marginTop: 16 }}>
        <input value={url} onChange={(e) => setUrl(e.target.value)} style={{ width: '100%' }} aria-label="mp3 URL" />
        <button onClick={playIt} disabled={player.isPlaying}>재생</button>
        <button onClick={player.stop}>정지</button>
        <span style={{ marginLeft: 8 }}>{result && `결과: ${result}`}</span>
      </div>
    </div>
  );
}
