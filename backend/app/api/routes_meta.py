# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: session-api (contracts.yaml ownership)
import logging
from fastapi import APIRouter
from app import db,tts,exam
from app.config import settings
from app.schemas.api import HealthOut,ScenarioOut,HostLineOut

router=APIRouter()
log=logging.getLogger(__name__)

@router.get('/health',response_model=HealthOut)
def health():
    ok=db.ping();version=None;seen=None
    if ok:
        try: version=db.current_corpus_version();seen=db.last_job_activity()
        except Exception: ok=False
    try: status=tts.tts_status()
    except NotImplementedError: status={'voice_id':None,'assets':0,'missing_pilot':[]}
    except Exception:
        log.warning('TTS 상태 조회 실패')
        status={'voice_id':None,'assets':0,'missing_pilot':[]}
    return HealthOut(ready=bool(ok and version and status['voice_id']),db='ok' if ok else 'error',worker_seen_at=seen,
        whisper_model=settings.WHISPER_MODEL,corpus_version=version,tts=status)

@router.get('/scenarios',response_model=list[ScenarioOut])
def scenarios(): return exam.list_scenarios()

@router.get('/host-lines',response_model=dict[str,HostLineOut])
def host_lines():
    try: voice=tts.active_voice_id()
    except NotImplementedError: voice=None
    result={}
    for key,text in tts.HOST_LINES.items():
        asset=db.find_tts_asset(kind='host',ref_id=key,text_hash=tts.text_hash(text),voice_id=voice) if voice else None
        result[key]=HostLineOut(key=key,text=text,audio_url=tts.tts_url(asset['file_path']) if asset and asset['status']=='available' else None)
    return result
