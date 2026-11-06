# AI-assisted: 소유권 경계 검증은 OpenAI Codex의 도움으로 작성했습니다.
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import yaml
from check_ownership import local_file_forbidden,matches

SCRIPT=Path(__file__).with_name('check_ownership.py')
CONTRACT=SCRIPT.parents[1]/'contracts.yaml'


class OwnershipTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'repo';self.root.mkdir()
        self.git('init','-b','main');self.git('config','user.name','Ownership fixture')
        self.git('config','user.email','fixture@example.invalid')
        self.write('agents/contracts.yaml',CONTRACT.read_text(encoding='utf-8'))
        self.commit('agents/contracts.yaml');self.git('branch','baseline')
        self.trusted=Path(self.temp.name)/'trusted.yaml'
        self.trusted.write_bytes(CONTRACT.read_bytes())

    def git(self,*args):
        return subprocess.run(['git',*args],cwd=self.root,check=True,capture_output=True)

    def write(self,name,text):
        p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')

    def commit(self,*paths):
        self.git('add','--',*paths);self.git('commit','-m','fixture')

    def check(self,role,*args):
        return subprocess.run([sys.executable,str(SCRIPT),role,'--repo',str(self.root),'--base','baseline',*args],capture_output=True).returncode

    def test_globs_and_synthetic_audio_policy(self):
        self.assertTrue(matches('docs/handoff/grader.md','docs/handoff/*.md'))
        self.assertFalse(matches('a/b/c','a/*'))
        for p in ['data/answer.wav','.env.local','backend/.env','backend/raw.mp3','Data/model.pt','backend/.ENV.local']:
            self.assertTrue(local_file_forbidden(p),p)
        for p in ['backend/.env.example','backend/e2e_audio/IL/1.mp3','backend/static/tts/voice/question.wav']:
            self.assertFalse(local_file_forbidden(p),p)

    def test_tts_role_may_commit_synthetic_audio(self):
        path='backend/e2e_audio/IL/1.mp3';self.write(path,'synthetic fixture');self.commit(path)
        self.assertEqual(self.check('tts-host'),0)
        self.assertEqual(self.check('grader'),1)

    def test_trusted_contract_rejects_head_self_grant(self):
        self.write('agents/contracts.yaml',yaml.safe_dump({'ownership':[{'path':'**','owner':'frontend'}]}))
        self.write('backend/app/grading/fixture.py','# fixture')
        self.commit('agents/contracts.yaml','backend/app/grading/fixture.py')
        self.assertEqual(self.check('frontend','--contract',str(self.trusted)),1)
        self.assertEqual(self.check('frontend'),0)

    def test_phase0_cannot_be_reused_after_m0(self):
        self.write('backend/app/config.py','# stub');self.commit('backend/app/config.py')
        self.assertEqual(self.check('bootstrap','--phase0'),0)
        self.assertEqual(self.check('grader','--phase0'),2)
        self.git('branch','-f','baseline','HEAD')
        self.assertEqual(self.check('bootstrap','--phase0'),2)

    def test_explicit_head_inspects_fetched_objects_without_checkout(self):
        self.write('docs/handoff/grader.md','fixture');self.commit('docs/handoff/grader.md')
        self.git('branch','proposal','HEAD');self.git('checkout','baseline')
        self.assertEqual(self.check('grader','--head','proposal'),0)
        self.assertEqual(self.check('frontend','--head','proposal'),1)


if __name__=='__main__': unittest.main()
