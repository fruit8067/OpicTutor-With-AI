# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
"""계약의 첫 일치 경로 규칙으로 브랜치 소유권을 검사한다."""
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('agent_id')
    parser.add_argument('--base', default='origin/main')
    parser.add_argument('--phase0', action='store_true')
    args = parser.parse_args()
    if args.phase0:
        if args.agent_id != 'bootstrap':
            parser.error('--phase0는 bootstrap 전용입니다.')
        print('bootstrap Phase 0: 계약 골격 생성 예외')
        return 0
    contract = yaml.safe_load((ROOT / 'agents/contracts.yaml').read_text(encoding='utf-8'))
    result = subprocess.run(['git', 'diff', '--name-only', '-z', f'{args.base}...HEAD'],
                            cwd=ROOT, check=True, stdout=subprocess.PIPE)
    errors = []
    for path in filter(None, result.stdout.decode('utf-8').split('\0')):
        owner = next((r['owner'].replace('{agent_id}', args.agent_id)
                      for r in contract['ownership']
                      if matches(path, r['path'].replace('{agent_id}', args.agent_id))), None)
        if owner != args.agent_id:
            errors.append(f'{path} (owner: {owner})')
    if errors:
        print('\n'.join(errors))
        return 1
    print(f'{args.agent_id}: 소유권 검사 통과')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
