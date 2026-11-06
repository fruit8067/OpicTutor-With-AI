# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: bootstrap (contracts.yaml ownership)
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / '.env', extra='ignore')
    DATABASE_URL: str = 'postgresql://opic:opic@127.0.0.1:5432/opic'
    API_HOST: str = '127.0.0.1'
    API_PORT: int = 8000
    CORS_ORIGINS: str = 'http://localhost:5173,http://127.0.0.1:5173'
    DATA_DIR: Path = Path('../data')
    TTS_DIR: Path = Path('static/tts')
    RAG_BUILD_DIR: Path = Path('../rag_docs/build')
    EVAL_SYSTEM_PROMPT_PATH: Path = Path('../docs/prompts/opic_evaluation_system.md')
    LLM_BASE_URL: str = 'https://api.openai.com/v1'
    LLM_API_KEY: str = ''
    LLM_MODEL: str = 'gpt-4o-mini'
    LLM_TIMEOUT_SEC: int = 90
    EMBED_BASE_URL: str = 'https://api.openai.com/v1'
    EMBED_API_KEY: str = ''
    EMBED_MODEL: str = 'text-embedding-3-small'
    EMBED_DIM: int = 1536
    WHISPER_MODEL: str = 'small.en'
    WHISPER_DEVICE: str = 'cpu'
    WHISPER_COMPUTE_TYPE: str = 'int8'
    WORKER_ID: str = ''
    WORKER_JOB_TYPES: str = 'tts_prepare,stt,evaluate'
    LOG_LEVEL: str = 'INFO'

    @field_validator('DATA_DIR','TTS_DIR','RAG_BUILD_DIR','EVAL_SYSTEM_PROMPT_PATH', mode='after')
    @classmethod
    def absolute_paths(cls, value: Path) -> Path:
        return (BACKEND_DIR / value).resolve()

settings = Settings()
