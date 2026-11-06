# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: grader (contracts.yaml ownership)
from app import db
from app.llm.embeddings import embed_texts
from app.schemas.internal import EvidenceBundle
from .rules import contract,token_count

LABEL='합성 학습 예시이며 등급 판정 정답이 아님. 비슷하다는 이유로 같은 등급을 주지 말 것.'
PREFERRED=['IM2','IM1','IM3','IL','IH','NH','AL','NM','NL']

def build_evidence(snapshot: list[dict], *, exclude_contrast_set_ids: list[str] = ()) -> EvidenceBundle:
    excluded=set(exclude_contrast_set_ids)
    version=db.current_corpus_version()
    documents=[]
    for row in snapshot:
        if not row['is_scored']: continue
        qid=row['question_id']
        examples=[] if qid in excluded else db.get_contrast_set(qid,text_style='stt')
        examples=[d for d in examples if d.get('contrast_set_id') not in excluded and (version is None or d.get('corpus_version')==version)]
        text=row.get('stt_text')
        if not examples and row['stt_status']=='done' and isinstance(text,str) and text.strip():
            vector=embed_texts([text])[0]
            found=db.search_similar_answers(vector,question_type=row['question_type'],text_style='stt',
                                           exclude_contrast_set_ids=list(excluded),k=5)
            candidate=next((d.get('contrast_set_id') for d in found if d.get('contrast_set_id') and d['contrast_set_id'] not in excluded),None)
            if candidate:
                examples=[d for d in db.get_contrast_set(candidate,text_style='stt') if d.get('contrast_set_id') not in excluded]
        for d in examples:
            if d.get('doc_type')!='answer' or d.get('text_style')!='stt': continue
            documents.append({k:d.get(k) for k in ['id','doc_type','level','contrast_set_id','text']} |
                             {'order_no':row['order_no'],'label':LABEL})
    for d in db.get_rag_docs('upgrade_pattern',corpus_version=version):
        documents.append({k:d.get(k) for k in ['id','doc_type','text']} | {'label':'보조 연습 자료, 등급 기준 아님'})
    budget=contract()['policies']['evidence_token_budget']
    if token_count(documents)>budget:
        documents=[d for d in documents if d.get('level') not in ('NL','NM')]
    while documents and token_count(documents)>budget:
        counts={}
        for d in documents:
            key=d.get('order_no');counts[key]=counts.get(key,0)+1
        group=max(counts,key=lambda key:(counts[key],-1 if key is None else key))
        candidates=[(index,d) for index,d in enumerate(documents) if d.get('order_no')==group]
        index,_=max(candidates,key=lambda pair:(PREFERRED.index(pair[1]['level']) if pair[1].get('level') in PREFERRED else 99,pair[0]))
        documents.pop(index)
    ids=list(dict.fromkeys(d['id'] for d in documents))
    return EvidenceBundle(docs=documents,corpus_version=version,retrieved_doc_ids=ids)
