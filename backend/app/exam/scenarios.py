# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: session-api (contracts.yaml ownership)
"""mtime와 파일 크기에 따른 코퍼스 캐시. 원본이 없거나 잘못되면 명시적으로 실패한다."""
import json
import logging
import threading
from app.config import settings
from app.errors import AppError
from app.schemas.api import ScenarioOut

_cache=None
_lock=threading.RLock()
FUNCTIONS={'self_introduce','describe','report_routine','narrate_past','compare','ask_information','solve_problem','explain_issue','state_future_plan','express_opinion'}
TIME_FRAMES={'present','past','future'}
CONTEXTS={'personal_familiar','everyday_transaction','community_public','unexpected_situation'}

def load_corpus():
    global _cache
    paths=[settings.RAG_BUILD_DIR/name for name in ['scenarios.json','questions.jsonl']]
    try:
        with _lock:
            signature=tuple((str(p),p.stat().st_mtime_ns,p.stat().st_size) for p in paths)
            if _cache and _cache[0]==signature: return _cache[1],_cache[2]
            data=json.loads(paths[0].read_text(encoding='utf-8'))
            rows=[json.loads(line) for line in paths[1].read_text(encoding='utf-8').splitlines() if line.strip()]
            if len({q['id'] for q in rows})!=len(rows): raise ValueError('문항 ID 중복')
            questions={q['id']:q for q in rows if q.get('status')=='pilot'}
            scenarios={s['scenario_id']:s for s in data['scenarios']}
            if len(scenarios)!=len(data['scenarios']): raise ValueError('시나리오 ID 중복')
            for s in scenarios.values(): validate_scenario(s,questions)
            _cache=signature,scenarios,questions
            return scenarios,questions
    except (OSError,ValueError,KeyError,TypeError) as exc:
        logging.getLogger(__name__).warning('출제 코퍼스 파일 또는 v3 문항 태그를 확인하세요.')
        raise AppError('SCENARIO_UNAVAILABLE') from exc

def validate_scenario(s,questions):
    slots=sorted(s['slots'],key=lambda slot:slot['order_no'])
    if [slot['order_no'] for slot in slots]!=list(range(1,9)): raise ValueError('슬롯 순서 오류')
    if not isinstance(s.get('coverage'),dict): raise ValueError('커버리지 누락')
    for slot in slots:
        if slot.get('is_scored') is not (slot['order_no']!=1) or not slot['pool']: raise ValueError('채점 슬롯 오류')
        for qid in slot['pool']:
            q=questions[qid]
            if q['question_type'] not in slot['question_types'] or q.get('is_scored') is not slot['is_scored']:
                raise ValueError('문항 유형/채점 태그 오류')
            for field,allowed in [('target_functions',FUNCTIONS),('target_time_frames',TIME_FRAMES),('context_scope',CONTEXTS)]:
                values=q.get(field)
                if not isinstance(values,list) or not values or not all(isinstance(v,str) and v in allowed for v in values):
                    raise ValueError('문항 태그 오류')
            if not isinstance(q.get('question'),str) or not q['question'].strip(): raise ValueError('문항 텍스트 누락')
    # 전체 슬롯에서 서로 다른 문항 선택이 가능한지 검사한다(이분 매칭).
    matched={}
    def match(no,seen):
        for qid in slots[no]['pool']:
            if qid in seen: continue
            seen.add(qid)
            if qid not in matched or match(matched[qid],seen): matched[qid]=no;return True
        return False
    if not all(match(no,set()) for no in range(8)): raise ValueError('서로 다른 8문항 선택 불가')

def list_scenarios() -> list[ScenarioOut]:
    scenarios,_=load_corpus()
    return [ScenarioOut(scenario_id=s['scenario_id'],label=s['label'],description=s['description'],question_count=len(s['slots'])) for s in scenarios.values()]

def coverage_for(scenario_id,questions):
    scenarios,_=load_corpus()
    original=scenarios[scenario_id]['coverage']
    scored=[q for q in questions if q.is_scored]
    result={name:sorted({tag for q in scored for tag in getattr(q,field)}) for name,field in
        [('functions','target_functions'),('time_frames','target_time_frames'),('contexts','context_scope')]}
    warnings=list(original.get('warnings',[]))
    if 'future' not in result['time_frames']: warnings.append('future 시간대 요구 문항 없음')
    if 'unexpected_situation' not in result['contexts']: warnings.append('unexpected_situation 맥락 요구 문항 없음')
    result['warnings']=list(dict.fromkeys(warnings))
    return result
