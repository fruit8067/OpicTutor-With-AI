# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: data-layer (contracts.yaml ownership)
"""개발·테스트 전용 데이터 생성. API에서 import하지 않는다."""
import argparse
import hashlib
import json
import mimetypes
import math
import shutil
from pathlib import Path
from uuid import UUID,uuid4
from app import db
from app.config import settings
from app.schemas.internal import SessionQuestionIn
from app.errors import AppError
from .pool import tx

def seed_questions(scenario_id):
    try:
        from app.exam import build_question_set
        return build_question_set(scenario_id,str(uuid4()))
    except NotImplementedError:
        if scenario_id!='default': raise AppError('SCENARIO_UNAVAILABLE')
        # 계약 v3 태그가 없는 기존 파일을 추측해서 보정하지 않는다.
        rows=[json.loads(line) for line in (settings.RAG_BUILD_DIR/'questions.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
        kinds=['self_intro','description','routine','past_experience','comparison','roleplay_ask','roleplay_solve','issue']
        selected=[]
        for no,kind in enumerate(kinds,1):
            q=next((q for q in rows if q['status']=='pilot' and q['question_type']==kind),None)
            if q is None or any(k not in q for k in ['is_scored','target_functions','target_time_frames','context_scope']):
                raise ValueError('corpus M1의 Q000 및 검토된 v3 태그가 필요합니다.')
            text=q['question'] if 'question' in q else q['text']
            selected.append(SessionQuestionIn(order_no=no,question_id=q['id'],question_version=hashlib.sha1(text.encode()).hexdigest()[:12],
                question_text=text,question_type=kind,**{k:q[k] for k in ['is_scored','target_functions','target_time_frames','context_scope']}))
        return selected

def seed_session(status: str = 'ready', scenario_id: str = 'default', link_tts: bool = False) -> UUID:
    if status not in ('preparing','ready','in_progress'): raise ValueError('seed 상태는 preparing/ready/in_progress만 지원합니다.')
    sid,_=db.create_session(client_request_id=str(uuid4()),scenario_id=scenario_id,
        settings_json={'development_seed':True},questions=seed_questions(scenario_id),replaces_session_id=None)
    if link_tts:
        from app.tts import active_voice_id,text_hash,HOST_LINES
        voice=active_voice_id()
        if voice is None: raise ValueError('활성 TTS 음성이 없습니다.')
        def asset(kind,ref,text):
            a=db.find_tts_asset(kind=kind,ref_id=ref,text_hash=text_hash(text),voice_id=voice)
            if not a: raise ValueError('TTS 자산 누락: '+ref)
            return a['id']
        db.complete_prepare(sid,1,{q['order_no']:asset('question',q['question_id'],q['question_text']) for q in db.list_session_questions(sid)},
            {key:asset('host',key,text) for key,text in HOST_LINES.items()})
    else:
        with tx() as cur: cur.execute('UPDATE sessions SET status=%s WHERE id=%s',(status,sid))
    if link_tts and status=='in_progress': db.start_session(sid)
    return sid

def seed_queued_answer(session_id: UUID, audio_path: str, order_no: int | None = None) -> UUID:
    s=db.get_session(session_id)
    if s['status']=='ready': s=db.start_session(session_id)
    source=Path(audio_path);aid=uuid4()
    target=settings.DATA_DIR/'audio'/str(session_id)/(str(aid)+source.suffix)
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    try:
        db.create_answer(session_id=session_id,order_no=order_no or s['current_order_no'],client_request_id=str(uuid4()),
            audio_path=str(target),audio_mime=mimetypes.guess_type(source)[0] or 'audio/webm',audio_bytes=target.stat().st_size,
            audio_hash=hashlib.sha256(target.read_bytes()).hexdigest(),client_duration_ms=3000,answer_id=aid)
    except Exception:
        target.unlink(missing_ok=True);raise
    return aid

def seed_grading_session(level: str = 'IM2', text_style: str = 'stt') -> tuple[UUID,UUID]:
    if level not in ['NL','NM','NH','IL','IM1','IM2','IM3','IH','AL']: raise ValueError('지원하지 않는 등급')
    if text_style not in ('clean','stt'): raise ValueError('지원하지 않는 답변 변형')
    questions=seed_questions('default')
    answers=[json.loads(line) for line in (settings.RAG_BUILD_DIR/'answers.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    prepared=[]
    for q in questions:
        row=next((a for a in answers if a['question_id']==q.question_id and a['level']==level and a['text_style']==text_style),None)
        if row is None and q.order_no==1 and not q.is_scored and q.question_type=='self_intro':
            row={'answer_text':'My name is Alex. I live in a small town and enjoy walking with my friends.',
                 'est_seconds':30,'fixed_warmup':True}
        if row is None: raise ValueError('코퍼스 답변 누락: '+q.question_id)
        if not isinstance(row.get('answer_text'),str) or not row['answer_text'].strip():
            raise ValueError('코퍼스 답변 본문 누락: '+q.question_id)
        try: duration=float(row.get('est_seconds') or 30)
        except (TypeError,ValueError) as exc: raise ValueError('코퍼스 답변 시간 오류: '+q.question_id) from exc
        if not math.isfinite(duration) or duration<=0: raise ValueError('코퍼스 답변 시간 오류: '+q.question_id)
        row={**row,'est_seconds':duration}
        prepared.append((q,row))
    # 원본의 필수 답변이 없을 때 부분 세션/작업을 남기지 않도록 생성 전에 확인한다.
    sid,_=db.create_session(client_request_id=str(uuid4()),scenario_id='default',
        settings_json={'development_seed':True,'seed_level':level,
                       'fixed_warmup':any(row.get('fixed_warmup') for _,row in prepared)},
        questions=questions,replaces_session_id=None)
    with tx() as cur: cur.execute("UPDATE sessions SET status='in_progress' WHERE id=%s",(sid,))
    for q,row in prepared:
        text=row['answer_text'];duration=float(row.get('est_seconds') or 30);count=len(text.split());aid=uuid4()
        db.create_answer(session_id=sid,order_no=q.order_no,client_request_id=str(uuid4()),audio_path='dev:synthetic',
            audio_mime='audio/webm',audio_bytes=0,audio_hash='development',client_duration_ms=int(duration*1000),answer_id=aid)
        db.complete_stt(aid,text=text,timestamps=[],metrics={'duration_sec':duration,'speech_sec':duration,'word_count':count,
            'wpm':count*60/duration,'articulation_wpm':None,'long_pause_count':0,'observed_filler_per100':None,'metrics_version':'m1'},
            stt_version='dev:synthetic-fixed-warmup:v1' if row.get('fixed_warmup') else 'dev:synthetic:m1')
        with tx() as cur:
            cur.execute("UPDATE jobs SET status='done' WHERE type='stt' AND target_id=%s AND status='queued'",(aid,))
    return sid,db.submit_session(sid)

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    s=sub.add_parser('seed-session');s.add_argument('--status',default='ready');s.add_argument('--link-tts',action='store_true')
    s=sub.add_parser('seed-answer');s.add_argument('session_id',type=UUID);s.add_argument('audio_path')
    s=sub.add_parser('seed-grading');s.add_argument('--level',default='IM2')
    args=p.parse_args()
    if args.command=='seed-session': print(seed_session(status=args.status,link_tts=args.link_tts))
    elif args.command=='seed-answer': print(seed_queued_answer(args.session_id,args.audio_path))
    else: print(seed_grading_session(level=args.level))

if __name__=='__main__': main()
