# AI-assisted: 소유권 검사는 OpenAI Codex의 도움으로 작성했습니다.
"""계약의 첫 일치 경로 규칙으로 origin/main 대비 소유권을 검사한다."""
import argparse
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def matches(path: str, pattern: str) -> bool:
    pieces = re.split(r'(\*\*|\*|\?)', pattern)
    expression = ''.join({'**': '.*', '*': '[^/]*', '?': '[^/]'}.get(p, re.escape(p)) for p in pieces)
    return re.fullmatch(expression, path) is not None


def local_file_forbidden(path: str) -> bool:
    normalized=path.casefold()
    name=Path(normalized).name
    synthetic=normalized.startswith(('backend/static/tts/','backend/e2e_audio/'))
    audio=normalized.endswith(('.webm','.wav','.mp3','.m4a','.ogg','.mp4'))
    return (normalized.startswith('data/') or (name.startswith('.env') and name!='.env.example')
            or (audio and not synthetic) or normalized.endswith(('.pt','.safetensors')))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('agent_id')
    parser.add_argument('--base', default='origin/main')
    parser.add_argument('--head', default='HEAD')
    parser.add_argument('--repo', type=Path, default=ROOT)
    parser.add_argument('--contract', type=Path)
    parser.add_argument('--phase0', action='store_true')
    args = parser.parse_args()
    root = args.repo.resolve()
    if args.phase0:
        if args.agent_id != 'bootstrap':
            parser.error('--phase0는 bootstrap 전용입니다.')
        exists = subprocess.run(['git','cat-file','-e',f'{args.base}:backend/app/config.py'],cwd=root,capture_output=True)
        if exists.returncode == 0:
            parser.error('M0 이후에는 Phase 0 예외를 사용할 수 없습니다.')
    contract_path = args.contract or root / 'agents/contracts.yaml'
    contract = yaml.safe_load(contract_path.read_text(encoding='utf-8'))
    result = subprocess.run(['git','diff','--name-only','-z',f'{args.base}...{args.head}'],cwd=root,check=True,stdout=subprocess.PIPE)
    errors = []
    for path in filter(None,result.stdout.decode('utf-8').split('\0')):
        if local_file_forbidden(path):
            errors.append(f'{path} (금지된 로컬 데이터/키/원음 경로)')
            continue
        if args.phase0:
            if path.startswith('docs/prompts/') or (path.startswith('agents/') and path != 'agents/tools/check_ownership.py'):
                errors.append(f'{path} (Phase 0 골격 생성 범위 아님)')
            continue
        owner = next((r['owner'].replace('{agent_id}',args.agent_id)
                      for r in contract['ownership']
                      if matches(path,r['path'].replace('{agent_id}',args.agent_id))),None)
        if owner != args.agent_id:
            errors.append(f'{path} (owner: {owner})')
    if errors:
        print('\n'.join(errors))
        return 1
    print(f'{args.agent_id}: 소유권 검사 통과' + (' (Phase 0 골격 예외)' if args.phase0 else ''))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
