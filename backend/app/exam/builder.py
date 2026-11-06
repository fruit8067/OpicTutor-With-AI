# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: session-api (contracts.yaml ownership)
import hashlib
import random
from app.errors import AppError
from app.schemas.internal import SessionQuestionIn
from .scenarios import load_corpus

def build_question_set(scenario_id: str, seed: str) -> list[SessionQuestionIn]:
    scenarios,bank=load_corpus()
    scenario=scenarios.get(scenario_id)
    if scenario is None: raise AppError('SCENARIO_UNAVAILABLE')
    rng=random.Random(seed)
    slots=sorted(scenario['slots'],key=lambda s:s['order_no'])
    candidates=[]
    for slot in slots:
        pool=list(dict.fromkeys(slot['pool']));rng.shuffle(pool);candidates.append(pool)
    # 겹치는 pool에서도 가능한 완성 세트를 찾는다. 탐욕 선택 실패를 문항 부족으로 오인하지 않는다.
    def choose(index,used):
        if index==len(slots): return []
        for qid in candidates[index]:
            if qid in used: continue
            tail=choose(index+1,used|{qid})
            if tail is not None: return [qid]+tail
        return None
    chosen=choose(0,set())
    if chosen is None: raise AppError('SCENARIO_UNAVAILABLE')
    result=[]
    for slot,qid in zip(slots,chosen):
        q=bank[qid];text=q['question']
        result.append(SessionQuestionIn(order_no=slot['order_no'],question_id=qid,question_version=hashlib.sha1(text.encode()).hexdigest()[:12],
            question_text=text,question_type=q['question_type'],is_scored=q['is_scored'],target_functions=q['target_functions'],
            target_time_frames=q['target_time_frames'],context_scope=q['context_scope']))
    return result
