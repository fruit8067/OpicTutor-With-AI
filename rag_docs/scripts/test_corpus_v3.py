# AI-assisted: 코퍼스 검증 회귀 테스트는 OpenAI Codex의 도움으로 작성했습니다.
import copy
import json
import unittest
import corpus_v3 as build


class CorpusTests(unittest.TestCase):
    def setUp(self):
        self.bank=build.load('question_bank.yaml')['questions']
        self.sets=build.load_sets()

    def test_warmup_and_tags_are_mandatory(self):
        self.assertEqual(build.validate_questions(self.bank,self.sets),[])
        warmup=next(q for q in self.bank if q['id']=='Q000')
        warmup['is_scored']=True
        self.assertTrue(build.validate_questions(self.bank,self.sets))
        warmup['is_scored']=False
        del warmup['target_time_frames']
        self.assertTrue(build.validate_questions(self.bank,self.sets))

    def test_matching_and_coverage_guarantee(self):
        bank={q['id']:q for q in self.bank}
        source=build.load('scenarios.yaml')['scenarios'][0]
        result=build.build_scenario(source,bank)
        self.assertIn('past',result['coverage']['time_frames'])
        self.assertNotIn('future',result['coverage']['time_frames'])
        self.assertTrue(result['coverage']['warnings'])
        broken=copy.deepcopy(source)
        broken['slots'][2]['pool']=[]
        with self.assertRaises(ValueError): build.build_scenario(broken,bank)

    def test_all_build_documents_have_one_version_and_unique_ids(self):
        version=(build.OUT/'VERSION').read_text(encoding='utf-8').strip()
        seen=set()
        for path in build.OUT.glob('*.jsonl'):
            for line in path.read_text(encoding='utf-8').splitlines():
                row=json.loads(line)
                self.assertEqual(row['corpus_version'],version)
                self.assertNotIn(row['id'],seen);seen.add(row['id'])
        scenarios=json.loads((build.OUT/'scenarios.json').read_text(encoding='utf-8'))
        self.assertEqual(scenarios['version'],version)


if __name__=='__main__': unittest.main()
