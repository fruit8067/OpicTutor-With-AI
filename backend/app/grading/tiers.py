# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: grader (contracts.yaml ownership)
from .rules import contract

def tier_of(level: str | None) -> dict | None:
    if level is None: return None
    for name,info in contract()['tiers'].items():
        if level in info['levels']: return {'name':name,'color':info['color']}
    raise ValueError('허용되지 않은 등급')
