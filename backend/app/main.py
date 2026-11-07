# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: session-api (contracts.yaml ownership)
"""실행: uvicorn app.main:app --host 127.0.0.1 --port 8000"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from app import db
from app.config import settings
from app.errors import install_error_handlers
from app.api import routes_meta,routes_auth,routes_sessions,routes_answers,routes_results

@asynccontextmanager
async def lifespan(app):
    try: await run_in_threadpool(db.init_db)
    except Exception: logging.getLogger(__name__).warning('DB 초기화 실패. /api/v1/health를 확인하세요.')
    yield

app=FastAPI(title='OpicTutor',version='3',lifespan=lifespan)
install_error_handlers(app)
app.add_middleware(CORSMiddleware,allow_origins=[v.strip() for v in settings.CORS_ORIGINS.split(',') if v.strip()],
    allow_methods=['*'],allow_headers=['*'])
settings.TTS_DIR.mkdir(parents=True,exist_ok=True)
app.mount('/media/tts',StaticFiles(directory=settings.TTS_DIR),name='tts')
for module in [routes_meta,routes_auth,routes_sessions,routes_answers,routes_results]: app.include_router(module.router,prefix='/api/v1')
