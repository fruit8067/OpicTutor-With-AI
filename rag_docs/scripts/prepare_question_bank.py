# AI-assisted: 문항 분류·태그 준비 코드는 OpenAI Codex의 도움으로 작성했습니다.
"""질문 주석을 원천으로 문항·검토 근거를 준비한다. 답변 본문은 수정하지 않는다."""
import argparse
import re
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'source'
SELF_INTRO = "Let's start the interview now. Tell me a little bit about yourself."

# 전체 질문 문장을 검토한 뒤 혼합 과제의 대표 유형을 지정했다.
ASK = {10,44,52,54,62,78,79,81,*range(108,118),*range(158,168),*range(208,218)}
SOLVE = {11,16,20,21,35,36,55,58,59,60,61,65,76,77,80,82,*range(118,128),*range(168,178),*range(218,228)}
COMPARE = {5,15,29,39,42,43,45,50,51,63,64,67,86,87,*range(98,108),*range(148,158),*range(198,208)}
PAST = {3,4,12,14,19,22,23,24,25,27,28,31,32,34,38,40,46,47,49,53,56,57,66,74,83,84,
        *range(88,98),*range(138,148),*range(188,198)}
ISSUE = {9,17,30,37,68,69,70,71,72,85,*range(133,138),*range(183,188),*range(233,238)}
ROUTINE = {2,7,33,73,75}
MIXED_PAST = {4,15,29,39,42,43,45,50,63,64,67,75,99,102,106,149,154,189,198,199}
MANUAL_REVIEW = {19,40,42,*range(88,98),140,144,192}
FUNCTION = {'self_intro':'self_introduce','description':'describe','routine':'report_routine',
            'past_experience':'narrate_past','roleplay_experience':'narrate_past','comparison':'compare',
            'roleplay_ask':'ask_information','roleplay_solve':'solve_problem','issue':'explain_issue'}


def classify(number):
    if number == 0: return 'self_intro'
    if number in ASK: return 'roleplay_ask'
    if number in SOLVE: return 'roleplay_solve'
    if number == 12: return 'roleplay_experience'
    if number in COMPARE: return 'comparison'
    if number in PAST: return 'past_experience'
    if number in ISSUE: return 'issue'
    if number in ROUTINE: return 'routine'
    return 'description'


def tags(number, text, kind):
    lower=text.lower()
    functions=[FUNCTION[kind]]
    past=kind in ('past_experience','roleplay_experience') or number in MIXED_PAST or number==41
    frames=['past'] if kind in ('past_experience','roleplay_experience') else ['present']
    if number in {4,47}: frames.append('present')
    if number==69:
        frames.append('past');functions.append('narrate_past')  # 산업의 발전 과정과 성장 요인을 실제로 묻는다.
    if number==130: frames=['past']  # 방문 당시 장소의 묘사이며 사건 전개를 요구하지 않는다.
    if past and 'past' not in frames: frames.append('past')
    if re.search(r'\b(compare|similar|different|changed|changes)\b',lower) and number not in SOLVE and number not in ASK:
        functions.append('compare')
    if number in {6,30,37,68,70,71,72,85,133,134,135,136,137,183,184,185,186,187,233,234,235,236,237}:
        functions.append('express_opinion')
    if number in {8,33,39,41,43,75,87,128,129,131,132,178,180,182,206,230,231,232}:
        functions.append('report_routine')
    if number in {41,43,47,75}: functions.append('describe')
    if number==33: functions.append('describe')
    if number==41: functions.append('narrate_past')
    if number==71: frames.append('future')  # "what effects might it have"가 실제 예상 결과를 요구한다.
    contexts=['personal_familiar']
    if kind.startswith('roleplay_'): contexts=['everyday_transaction']
    if kind=='issue' or number in {8,17,23,27,36,48,69,75,128,130,131,132,178,179,180,181,182,188,196,228,229,231,232}:
        contexts=['community_public']
    if kind=='roleplay_solve' or (past and re.search(r'problem|wrong|hurt|cancel|interrupt|unexpected|lost|failed|broke|damaged|misunderstood|mix-up|late|missing|suddenly|not arrive',lower)):
        contexts.append('unexpected_situation')
    return dict(is_scored=number!=0,target_functions=list(dict.fromkeys(functions)),
                target_time_frames=list(dict.fromkeys(frames)),context_scope=list(dict.fromkeys(contexts)))


def topic(text):
    choices=[('housing',r'home|apartment|house|kitchen|neighborhood|housing'),('travel',r'trip|travel|hotel|beach|airport|airline|ferry|vacation'),
        ('transport',r'train|bus|transport|station|car |navigation|pedestrian|walking to'),('exercise_health',r'gym|health|hospital|clinic|dent|yoga|hiking|swimming|sports|trail|mountain'),
        ('culture_leisure',r'concert|festival|movie|theater|music|museum|photograph|arts|performance|hobby'),
        ('food_shopping',r'food|meal|cook|restaurant|grocery|groceries|shopping|store|bookstore|payment|jacket'),
        ('school_work',r'school|university|student|class|project|library|interview|assignment|workshop|semester'),
        ('technology',r'phone|technology|device|electronic|internet|online|app|website|laptop|computer|artificial|cashless'),
        ('community',r'community|volunteer|public|city|cities|country|recycling'),('family_friends',r'family|friend|relative')]
    return next((name for name,pattern in choices if re.search(pattern,text,re.I)),'everyday_life')


def prepare(phase):
    old=yaml.safe_load((SRC/'question_bank.yaml').read_text(encoding='utf-8'))['questions']
    bank={q['id']:q for q in old}
    change_file=SRC/'question_text_changes.yaml'
    changes=(yaml.safe_load(change_file.read_text(encoding='utf-8')) or {}).get('changed_from_original_bank',[]) if change_file.exists() else []
    if phase=='m2':
        for path in sorted(SRC.glob('contrast_sets_*.yaml')):
            for qid,text in re.findall(r'^#\s*(Q\d+)\s*질문:\s*(.+)$',path.read_text(encoding='utf-8'),re.M):
                if qid in bank and bank[qid]['question']!=text: changes.append(qid)
                number=int(qid[1:]);kind=classify(number)
                bank[qid]=dict(id=qid,question_type=kind,topic=topic(text),survey='topic_based',difficulty='3-6',
                    status='todo' if number in MANUAL_REVIEW else 'pilot',question=text)
    bank['Q000']=dict(id='Q000',question_type='self_intro',topic='self_intro',survey='common',difficulty='1-6',status='pilot',question=SELF_INTRO)
    rationale={}
    for qid,q in sorted(bank.items()):
        n=int(qid[1:])
        if phase=='m1' and n>12: continue
        q.update(tags(n,q['question'],q['question_type']))
        rationale[qid]=dict(question_excerpt=q['question'],target_functions=q['target_functions'],target_time_frames=q['target_time_frames'],
            context_scope=q['context_scope'],review_note='문장 전체를 검토한 규칙 기반 초안. 역할극 설정의 미래 시점만으로 future를 붙이지 않음.'+
            (' 단조성 휴리스틱 경고가 있어 출제는 todo로 보류.' if n in MANUAL_REVIEW else '')+
            (' 혼합 과제: 대표 유형 외의 실제 요구를 추가 태그로 기록.' if n in MIXED_PAST or n in {33,41,43,47,75} else ''))
    header='# AI-assisted: 문항 정리와 태그는 OpenAI Codex의 도움으로 작성했습니다.\n# 교육용 연습문항이며 실제 기출 원문/공식 채점 답안이 아닙니다. 기존 합성 답변 본문은 수정하지 않았습니다.\n'
    (SRC/'question_bank.yaml').write_text(header+yaml.safe_dump({'questions':list(dict(sorted(bank.items())).values())},allow_unicode=True,sort_keys=False),encoding='utf-8')
    (SRC/'question_tags_rationale.yaml').write_text(header+yaml.safe_dump(rationale,allow_unicode=True,sort_keys=False),encoding='utf-8')
    templates=[('self_intro',),('description',),('routine',),('past_experience',),('comparison',),('roleplay_ask',),('roleplay_solve',),('issue','roleplay_experience')]
    groups=[('default','기본 구성','여러 주제가 섞인 8문항 모의고사',None)]
    if phase=='m2':
        groups += [('leisure','여가 중심','여가·문화와 공통 일상 과제',{'culture_leisure','family_friends'}),
                   ('health','운동·건강','운동·건강과 일상 서비스 과제',{'exercise_health'}),
                   ('travel','여행','여행·교통과 일상 서비스 과제',{'travel','transport'})]
    scenarios=[]
    for sid,label,description,topics in groups:
        slots=[]
        for order,kinds in enumerate(templates,1):
            pool=[qid for qid,q in sorted(bank.items()) if q['status']=='pilot' and q['question_type'] in kinds
                  and (phase=='m2' or int(qid[1:])<=12) and (order==1 or topics is None or q['topic'] in topics)]
            slots.append(dict(order_no=order,question_types=list(kinds),is_scored=order!=1,pool=pool))
        scenarios.append(dict(scenario_id=sid,label=label,description=description,slots=slots))
    (SRC/'scenarios.yaml').write_text(header+yaml.safe_dump({'scenarios':scenarios},allow_unicode=True,sort_keys=False),encoding='utf-8')
    (SRC/'question_text_changes.yaml').write_text(header+yaml.safe_dump({'changed_from_original_bank':sorted(set(changes)),
        'note':'Q013~Q030의 기존 뱅크 문장이 대조 세트 질문 주석과 달라 원본 대조 세트에 맞춤. M1 pilot Q000~Q012 문장은 변경 없음.'},allow_unicode=True,sort_keys=False),encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--phase',choices=['m1','m2'],required=True)
    prepare(parser.parse_args().phase)
