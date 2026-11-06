# AI-assisted: 코퍼스 v3 빌드·검증은 OpenAI Codex의 도움으로 작성했습니다.
"""계약 v3 검증을 통과한 pilot만 출제한다. 길이 통계는 등급 판정 기준이 아니다."""
from collections import Counter
from datetime import date
import hashlib
import json
import re
from pathlib import Path
import yaml
from build_corpus import to_stt, WORD
from check_monotonic import feats

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'source';OUT=ROOT/'build'
LEVELS=['NL','NM','NH','IL','IM1','IM2','IM3','IH','AL']
RANK={level:i+1 for i,level in enumerate(LEVELS)}
CONTRACT=yaml.safe_load((ROOT.parent/'agents/contracts.yaml').read_text(encoding='utf-8'))


def load(name): return yaml.safe_load((SRC/name).read_text(encoding='utf-8'))


def load_sets():
    sets={}
    for path in sorted(SRC.glob('contrast_sets_*.yaml')):
        for qid,levels in yaml.safe_load(path.read_text(encoding='utf-8')).items():
            if qid in sets: raise ValueError('중복 대조 세트: '+qid)
            sets[qid]=levels
    return sets


def validate_questions(bank,sets):
    errors=[]
    if len(bank)!=len({q['id'] for q in bank}): errors.append('문항 ID 중복')
    for q in bank:
        qid=q['id']
        if q['question_type'] not in CONTRACT['question_types']: errors.append(qid+': 유형 오류')
        if q['status'] not in ('pilot','todo'): errors.append(qid+': status 오류')
        if not isinstance(q.get('question'),str) or not q['question'].strip(): errors.append(qid+': 질문 누락')
        if q['status']!='pilot': continue
        if type(q.get('is_scored')) is not bool or (not q['is_scored']) != (qid=='Q000' and q['question_type']=='self_intro'):
            errors.append(qid+': 자기소개/채점 태그 오류')
        for field in ['target_functions','target_time_frames','context_scope']:
            tags=q.get(field)
            if not isinstance(tags,list) or not tags or any(tag not in CONTRACT['question_tags'][field] for tag in tags):
                errors.append(qid+': '+field+' 누락/허용 어휘 오류')
        if qid!='Q000' and qid not in sets: errors.append(qid+': 대조 세트 없음')
        if qid in sets:
            levels=sets[qid]
            if set(levels)!=set(LEVELS): errors.append(qid+': 9등급 누락/추가')
            for lv,a in levels.items():
                if not isinstance(a,dict) or not a.get('text') or not a.get('rationale'): errors.append(qid+'-'+lv+': 답변/근거 누락')
    return errors


def build_scenario(source,bank):
    slots=source['slots']
    if [s['order_no'] for s in slots]!=list(range(1,9)): raise ValueError('슬롯 순서는 1..8이어야 함')
    for slot in slots:
        if slot['is_scored'] is not (slot['order_no']!=1): raise ValueError('채점 슬롯 오류')
        if not slot['pool'] or len(set(slot['pool']))!=len(slot['pool']): raise ValueError('빈 pool/중복 ID')
        for qid in slot['pool']:
            q=bank[qid]
            if q['status']!='pilot' or q['question_type'] not in slot['question_types'] or q['is_scored']!=slot['is_scored']:
                raise ValueError('pilot/유형/채점 태그 오류: '+qid)
    matched={}
    def match(index,seen):
        for qid in slots[index]['pool']:
            if qid in seen: continue
            seen.add(qid)
            if qid not in matched or match(matched[qid],seen): matched[qid]=index;return True
        return False
    if not all(match(index,set()) for index in range(8)): raise ValueError('서로 다른 8문항 선택 불가')
    coverage={}
    for name,field in [('functions','target_functions'),('time_frames','target_time_frames'),('contexts','context_scope')]:
        guaranteed=set()
        for slot in slots[1:]:
            guaranteed |= set.intersection(*(set(bank[qid][field]) for qid in slot['pool']))
        coverage[name]=sorted(guaranteed)
    coverage['warnings']=[]
    if 'future' not in coverage['time_frames']: coverage['warnings'].append('future 시간대 요구가 모든 추첨에서 보장되지 않음')
    if 'unexpected_situation' not in coverage['contexts']: coverage['warnings'].append('unexpected_situation 맥락이 모든 추첨에서 보장되지 않음')
    return {**source,'coverage':coverage}


def main():
    OUT.mkdir(exist_ok=True)
    bank_list=load('question_bank.yaml')['questions'];sets=load_sets();rub=load('rubrics.yaml');constraints=load('level_constraints.yaml')
    source_questions={qid:text for path in sorted(SRC.glob('contrast_sets_*.yaml'))
        for qid,text in re.findall(r'^#\s*(Q\d+)\s*질문:\s*(.+)$',path.read_text(encoding='utf-8'),re.M)}
    errors=validate_questions(bank_list,sets)
    if errors:
        (OUT/'report.md').write_text('# 빌드 오류\n'+'\n'.join('- '+e for e in errors)+'\n',encoding='utf-8')
        print('\n'.join(errors));return 1
    mismatched=[q['id'] for q in bank_list if q['id'] in source_questions and q['question']!=source_questions[q['id']]]
    if any(q['status']=='pilot' and q['id'] in mismatched for q in bank_list):
        print('pilot 질문이 대조 세트 질문과 다름:',mismatched);return 1
    bank={q['id']:q for q in bank_list};scenarios=[];scenario_errors=[]
    for source in load('scenarios.yaml')['scenarios']:
        try: scenarios.append(build_scenario(source,bank))
        except (KeyError,TypeError,ValueError) as exc: scenario_errors.append(source['scenario_id']+': '+str(exc))
    # 버전은 원본 내용과 연결한다. 같은 원본으로 재빌드하면 같은 버전/문서가 나온다.
    digest=hashlib.sha256()
    for path in sorted([*SRC.glob('*.yaml'),*(ROOT/'scripts').glob('*.py')]):
        digest.update(path.name.encode());digest.update(path.read_bytes())
    version='2026-11-06.'+str(int(digest.hexdigest()[:12],16))
    docs={name:[] for name in ['rubrics','upgrade_patterns','questions','answers']}
    for r in rub['levels']:
        body='\n'.join(f'{k}: {v}' for k,v in r.items() if k not in ['level','level_rank','source_tier'])
        docs['rubrics'].append(dict(id='RUBRIC-'+r['level'],doc_type='rubric',level=r['level'],level_rank=r['level_rank'],
            source_tier=r['source_tier'],text=f"[참고 자료: {r['level']}]\n{body}",license='paraphrased_with_attribution'))
    for u in rub['upgrade_patterns']:
        docs['upgrade_patterns'].append(dict(id=f"UPGRADE-{u['from']}-{u['to']}",doc_type='upgrade_pattern',from_level=u['from'],
            to_level=u['to'],level_rank=RANK[u['from']],source_tier='B',text=f"[보조 연습 자료]\n{u['key_shift']}\n"+'\n'.join(u['actions'])+
            f"\nBefore: {u['example_before']}\nAfter: {u['example_after']}",license='self_authored'))
    length_notes=[];monotonic=[];profile_notes=[];stats={level:[] for level in LEVELS}
    for qid,q in sorted(bank.items()):
        docs['questions'].append({**q,'doc_type':'question','text':q['question']})
        if qid not in sets: continue
        if qid in mismatched: continue  # 다른 질문에 달린 답변을 잘못된 메타데이터로 적재하지 않는다.
        levels=sets[qid]
        if set(levels)!=set(LEVELS): continue
        features={lv:feats(a['text']) for lv,a in levels.items()}
        for metric in ['words','sent_len','conn_adv']:
            values=[features[lv][metric] for lv in LEVELS]
            for index in range(7):
                if values[index]>values[index+2]*1.15 and values[index]-values[index+2]>1:
                    monotonic.append(f'{qid} {metric}: {LEVELS[index]} {values[index]:.1f} > {LEVELS[index+2]} {values[index+2]:.1f}; todo로 출제 보류. 연결어/문장 길이는 등급 기준이 아니므로 원문을 기계적으로 고치지 않음.')
        for lv in ['IM1','IM2','IM3']:
            if re.search(r'단어\s*수|길이|\d+\s*단어',levels[lv].get('rationale','')):
                profile_notes.append(f'{qid}-{lv}: 근거에 길이 언급 포함. project-im-v1 내용 확장·지속성 검토 필요(등급 오류 확정 아님).')
        # todo도 검색 보조 자료로 보존하되 출제는 scenarios의 pilot만 사용한다.
        for lv,a in levels.items():
            cfg=constraints[lv];wc=len(WORD.findall(a['text']));stats[lv].append(wc)
            if not cfg['words'][0]<=wc<=cfg['words'][1]: length_notes.append(f'{qid}-{lv}: {wc} words, 참고 범위 {cfg["words"]}')
            for style in ['clean','stt']:
                text=a['text'] if style=='clean' else to_stt(a['text'],lv,cfg['stt'],qid+'-'+lv)
                docs['answers'].append(dict(id=f'{qid}-{lv}-{style}',doc_type='answer',level=lv,level_rank=RANK[lv],
                    question_id=qid,question_type=q['question_type'],topic=q['topic'],survey=q['survey'],question=q['question'],
                    word_count=wc,est_seconds=max(1,round(wc/(1.3 if RANK[lv]<=4 else 2.0))),
                    features={k:cfg[k] for k in ['sentence_level','tense','error_rate']},rationale=a['rationale'],upgrade_tip=a.get('upgrade_tip'),
                    next_level=LEVELS[RANK[lv]] if RANK[lv]<9 else None,contrast_set_id=qid,source_tier='C',
                    verified_by=['source_author_review','structural_validation'],license='self_generated',text_style=style,answer_text=text,
                    text=f"[합성 학습 예시, 등급 정답 아님]\n[Q] {q['question']}\n[A·{lv}] {text}\n[보조 근거] {a['rationale']}"))
    for name,rows in docs.items():
        for row in rows: row['corpus_version']=version
        (OUT/(name+'.jsonl')).write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows),encoding='utf-8')
    (OUT/'scenarios.json').write_text(json.dumps(dict(version=version,scenarios=scenarios),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'VERSION').write_text(version+'\n',encoding='utf-8')
    pilot=[q for q in bank_list if q['status']=='pilot'];todo=[q for q in bank_list if q['status']=='todo']
    lines=['# 코퍼스 v3 빌드 리포트','',f'- corpus_version: {version}',f'- 문항 {len(bank)} / pilot {len(pilot)} / todo {len(todo)}',
        f'- 문서 수: '+str({name:len(rows) for name,rows in docs.items()}),f'- 예상 임베딩 대상: {len(docs["questions"])+len(docs["answers"])}',
        '- 자동 형식 검증은 실제 수험생 채점 정확도나 태그의 독립적인 사람 검증을 의미하지 않음.',
        '- 고정 평가 기준: performance-feedback-actfl-speaking-v3. rubrics.jsonl은 참고용이며 기본 채점 기준이 아님.',
        '', '## pilot 유형별 수',str(dict(Counter(q['question_type'] for q in pilot))), '', '## 시나리오']
    for s in scenarios: lines += [f'### {s["scenario_id"]}',str([(slot['order_no'],len(slot['pool'])) for slot in s['slots']]),json.dumps(s['coverage'],ensure_ascii=False)]
    lines += ['','## 시나리오 제외 사유',*(scenario_errors or ['없음']),'','## todo 문항과 사유',
        *(f"- {q['id']}: "+('기존 질문과 대조 세트 질문 불일치, 답변 빌드 제외' if q['id'] in mismatched else '단조성 휴리스틱 경고 수동 검토 대기') for q in todo),'','## 단조성 점검',*(monotonic or ['경고 없음']),
        '', '## IM 프로필 검토 목록',*(profile_notes or ['길이만으로 설명한 명시적 근거 없음. 내용 확장·시간 관계를 별도로 검토해야 함.']),
        '', '## 길이 참고 통계 (공식 등급 경계·pilot 탈락 기준 아님)',f'- 참고 범위 밖 {len(length_notes)}건',*length_notes,
        '', '## 미래 시간대', ('Q071의 effects might it have를 future 요구로 태그하고 default issue pool에 포함. 모든 추첨에서 보장되지는 않으므로 경고를 유지.' if 'Q071' in bank else 'M1 기본 세트는 future 시간대 요구를 보장하지 않으므로 경고를 유지.'),
        '', '## 출처/질문 변경', '원본 대조 세트의 실제 기출 원문 아님 문구와 답변을 보존함. Q013~Q030 기존 뱅크/대조 질문 불일치는 question_text_changes.yaml 참조.']
    (OUT/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines[:10]));print('scenarios:',[s['scenario_id'] for s in scenarios]);return 0 if scenarios else 1
