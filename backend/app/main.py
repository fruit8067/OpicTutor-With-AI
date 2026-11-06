# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: session-api (contracts.yaml ownership)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.errors import install_error_handlers
from app.api import routes_meta, routes_sessions, routes_answers, routes_results

app = FastAPI(title='OpicTutor', version='3')
install_error_handlers(app)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS.split(','), allow_methods=['*'], allow_headers=['*'])
settings.TTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount('/media/tts', StaticFiles(directory=settings.TTS_DIR), name='tts')
for module in [routes_meta, routes_sessions, routes_answers, routes_results]:
    app.include_router(module.router, prefix='/api/v1')

@app.get('/api/v1/health')
def health():
    return {'ready': False, 'db': 'error', 'worker_seen_at': None, 'whisper_model': settings.WHISPER_MODEL,
            'corpus_version': None, 'tts': {'voice_id': None, 'assets': 0, 'missing_pilot': []}}
