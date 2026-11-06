# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: worker-stt (contracts.yaml ownership)
import ast
import importlib
import inspect
from functools import lru_cache
from pathlib import Path
import textwrap
import yaml

@lru_cache(maxsize=None)
def get_handler(kind):
    contract=yaml.safe_load((Path(__file__).resolve().parents[3]/'agents/contracts.yaml').read_text(encoding='utf-8'))
    module,name=contract['job_types'][kind]['handler'].split(':')
    return getattr(importlib.import_module(module),name)

def is_stub(handler):
    try:
        tree=ast.parse(textwrap.dedent(inspect.getsource(handler)))
    except (OSError,TypeError,IndentationError,SyntaxError): return False
    body=tree.body[0].body
    if body and isinstance(body[0],ast.Expr) and isinstance(body[0].value,ast.Constant) and isinstance(body[0].value.value,str): body=body[1:]
    return (len(body)==1 and isinstance(body[0],ast.Raise) and isinstance(body[0].exc,ast.Call)
            and isinstance(body[0].exc.func,ast.Name) and body[0].exc.func.id=='NotImplementedError')

def available_types(types):
    # 요청한 종류만 처음 필요할 때 import한다. 명시적인 stub 작업은 확보하지 않아 개발 중 유실을 막는다.
    return [kind for kind in types if not is_stub(get_handler(kind))]
