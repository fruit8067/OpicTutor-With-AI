// AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
// OWNER: tts-host (contracts.yaml ownership)
export function useTtsPlayer(): { play: (url: string) => Promise<'ended'|'blocked'|'error'>; stop: () => void; getAnalyser: () => AnalyserNode | null } {
 return {play: async () => {throw new Error('TODO: tts-host');}, stop: () => {}, getAnalyser: () => null};
}
