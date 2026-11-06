# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: session-api (contracts.yaml ownership)
import hashlib
from pathlib import Path
from uuid import UUID,uuid4
from typing import Annotated
from fastapi import APIRouter,UploadFile,File,Form,Response
from starlette.concurrency import run_in_threadpool
from app import db
from app.config import settings
from app.errors import AppError
from app.schemas.api import AnswerOut
from .deps import (preflight_upload,require_answer,answer_out,MIME_EXT,
    RECORD_MIN_MS,RECORD_MAX_MS,UPLOAD_TOLERANCE_MS,UPLOAD_MAX_BYTES)

router=APIRouter()

@router.post('/sessions/{session_id}/answers',response_model=AnswerOut,status_code=202)
async def upload(session_id: UUID,response: Response,order_no: Annotated[int,Form()],
                 client_request_id: Annotated[str,Form()],duration_ms: Annotated[int,Form()],
                 audio: Annotated[UploadFile,File()]):
    await run_in_threadpool(preflight_upload,session_id,order_no,client_request_id)
    mime=(audio.content_type or '').split(';',1)[0].strip().lower()
    if mime not in MIME_EXT: raise AppError('UNSUPPORTED_MEDIA')
    if duration_ms<RECORD_MIN_MS: raise AppError('AUDIO_TOO_SHORT')
    if duration_ms>RECORD_MAX_MS+UPLOAD_TOLERANCE_MS: raise AppError('AUDIO_TOO_LONG')
    aid=uuid4();folder=settings.DATA_DIR/'audio'/str(session_id);temp=folder/'.tmp'/str(aid)
    final=folder/(str(aid)+'.'+MIME_EXT[mime]);temp.parent.mkdir(parents=True,exist_ok=True)
    size=0;digest=hashlib.sha256()
    try:
        with temp.open('wb') as stream:
            while chunk:=await audio.read(64*1024):
                size+=len(chunk)
                if size>UPLOAD_MAX_BYTES: raise AppError('PAYLOAD_TOO_LARGE')
                digest.update(chunk);stream.write(chunk)
        if size==0: raise AppError('AUDIO_TOO_SHORT')
        row,created=await run_in_threadpool(db.create_answer,session_id=session_id,order_no=order_no,
            client_request_id=client_request_id,audio_path=str(final),audio_mime=mime,audio_bytes=size,
            audio_hash=digest.hexdigest(),client_duration_ms=duration_ms,answer_id=aid)
        if created:
            try: temp.replace(final)
            except OSError:
                # DB 접수와 파일 이동은 원자적이지 않다. 재전송이 성공처럼 보이지 않도록 실패 상태를 남긴다.
                await run_in_threadpool(db.fail_stt,aid,'STT_DECODE_ERROR')
                raise AppError('INTERNAL_ERROR')
        elif (row['stt_status']=='failed' and row.get('error_code')=='STT_DECODE_ERROR'
              and row['audio_hash']==digest.hexdigest() and row['audio_bytes']==size
              and row['audio_mime']==mime and row['client_duration_ms']==duration_ms):
            # DB 접수 후 rename 실패는 같은 Blob/키 재전송으로 원래 답변을 복구한다.
            # 다른 내용이나 이미 저장된 원음을 덮어쓰지 않고 STT retry의 멱등 가드를 사용한다.
            current=await run_in_threadpool(db.get_session,session_id)
            if current and current['status']=='in_progress' and current['current_order_no']==order_no:
                stored=Path(row['audio_path'])
                if stored.resolve().parent!=folder.resolve(): raise AppError('INTERNAL_ERROR')
                if not stored.is_file():
                    try: temp.replace(stored)
                    except OSError: raise AppError('INTERNAL_ERROR')
                try: await run_in_threadpool(db.retry_stt,row['id'])
                except AppError as exc:
                    # 다른 재녹음/순서 전진이 이긴 경우에도 원래 요청의 조회 멱등성은 유지한다.
                    if exc.code not in ('INVALID_STATE','ANSWER_PENDING'): raise
                row=await run_in_threadpool(db.get_answer,row['id'])
        response.status_code=202 if created else 200
        return await run_in_threadpool(answer_out,row)
    finally:
        temp.unlink(missing_ok=True)
        await audio.close()

@router.get('/sessions/{session_id}/answers/{answer_id}',response_model=AnswerOut)
def get_answer(session_id: UUID,answer_id: UUID): return answer_out(require_answer(session_id,answer_id))

@router.post('/sessions/{session_id}/answers/{answer_id}/retry-stt',response_model=AnswerOut,status_code=202)
def retry(session_id: UUID,answer_id: UUID):
    require_answer(session_id,answer_id);db.retry_stt(answer_id)
    return answer_out(require_answer(session_id,answer_id))
