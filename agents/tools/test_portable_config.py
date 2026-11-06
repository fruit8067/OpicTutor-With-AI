# AI-assisted (OpenAI Codex). OWNER: orchestrator.
"""Run relocated backend config from an unrelated cwd without real credentials."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


class PortableConfig(unittest.TestCase):
    def test_relocated_checkout_and_relative_env_paths(self):
        repo=Path(__file__).resolve().parents[2]
        # Pre-merge bootstrap worktree or normal single checkout after merge.
        source=repo.parent/'OpicTutor-bootstrap/backend/app/config.py'
        if not source.is_file(): source=repo/'backend/app/config.py'
        with tempfile.TemporaryDirectory(prefix='opic-portable-') as temporary:
            root=Path(temporary);clone=root/'다른 컴퓨터 checkout';backend=clone/'backend'
            (backend/'app').mkdir(parents=True);(root/'unrelated-cwd').mkdir()
            shutil.copyfile(source,backend/'app/config.py')
            (backend/'.env').write_text('DATA_DIR=../local-data\nTTS_DIR=static/tts\nRAG_BUILD_DIR=../rag_docs/build\nEVAL_SYSTEM_PROMPT_PATH=../docs/prompts/opic_evaluation_system.md\nPICKLE_API_KEY=relocated-fixture-key\n',encoding='utf-8')
            script='''import importlib.util,os,sys
from pathlib import Path
from pydantic import ValidationError
clone=Path(sys.argv[1])
s=importlib.util.spec_from_file_location('relocated_config',clone/'backend/app/config.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
assert os.getenv('PICKLE_API_KEY')=='relocated-fixture-key'
assert m.settings.DATA_DIR==clone/'local-data'
assert m.settings.TTS_DIR==clone/'backend/static/tts'
assert m.settings.RAG_BUILD_DIR==clone/'rag_docs/build'
assert m.settings.EVAL_SYSTEM_PROMPT_PATH==clone/'docs/prompts/opic_evaluation_system.md'
assert m.Settings(_env_file=None,DATA_DIR='..\\\\portable-data').DATA_DIR==clone/'portable-data'
for value in ['/var/local-data','C:/local-data','C:local-data',r'\\\\server\\share\\data']:
    try: m.Settings(_env_file=None,DATA_DIR=value)
    except ValidationError: pass
    else: raise AssertionError('absolute/drive path accepted')
print('relocated dotenv, relative paths, unrelated cwd and absolute-path rejection passed')
'''
            environment=os.environ.copy()
            for name in ['DATA_DIR','TTS_DIR','RAG_BUILD_DIR','EVAL_SYSTEM_PROMPT_PATH','PICKLE_API_KEY']:
                environment.pop(name,None)
            result=subprocess.run([sys.executable,'-c',script,str(clone)],cwd=root/'unrelated-cwd',
                                  env=environment,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)


if __name__=='__main__': unittest.main()
