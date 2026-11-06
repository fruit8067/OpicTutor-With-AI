# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: bootstrap (contracts.yaml ownership)
from pathlib import Path, PureWindowsPath
from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]

# os.getenv로 읽는 LLM 키에도 .env를 적용한다. 이미 설정된 프로세스 환경변수가 우선이다.
load_dotenv(BACKEND_DIR / '.env', override=False)

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
    LLM_BASE_URL: str = 'https://llm.pcl.kr/v1'
    LLM_API_KEY: str = ''
    PICKLE_API_KEY: str = ''
    LLM_MODEL: str = 'pickle-general'
    LLM_TIMEOUT_SEC: int = 90
    EMBED_BASE_URL: str = 'https://api.openai.com/v1'
    EMBED_API_KEY: str = ''
    EMBED_MODEL: str = 'text-embedding-3-large'
    EMBED_DIM: int = 3072
    WHISPER_MODEL: str = 'small.en'
    WHISPER_DEVICE: str = 'cpu'
    WHISPER_COMPUTE_TYPE: str = 'int8'
    WORKER_ID: str = ''
    WORKER_JOB_TYPES: str = 'tts_prepare,stt,evaluate'
    LOG_LEVEL: str = 'INFO'

    @field_validator('DATA_DIR','TTS_DIR','RAG_BUILD_DIR','EVAL_SYSTEM_PROMPT_PATH', mode='before')
    @classmethod
    def relative_path_settings(cls, value) -> Path:
        # Stored configuration must move with the repository across Windows/POSIX.
        raw=str(value)
        if Path(raw).is_absolute() or PureWindowsPath(raw).drive or PureWindowsPath(raw).root:
            raise ValueError('파일 설정은 backend/ 기준 상대 경로를 사용하세요.')
        return Path(raw.replace('\\','/'))

    @field_validator('DATA_DIR','TTS_DIR','RAG_BUILD_DIR','EVAL_SYSTEM_PROMPT_PATH', mode='after')
    @classmethod
    def resolve_backend_paths(cls, value: Path) -> Path:
        # Compute from this checkout, never from a developer's home or current cwd.
        return (BACKEND_DIR / value).resolve()

settings = Settings()
