# AI-assisted (OpenAI Codex). OWNER: data-layer.
"""A vector is reusable only with the same model, dimensions and public endpoint."""
from hashlib import sha256
from urllib.parse import urlsplit
from app.config import settings

PROFILE_KEY = '_embedding_profile'


def current_profile():
    endpoint=settings.EMBED_BASE_URL.strip().rstrip('/')
    parsed=urlsplit(endpoint)
    if parsed.scheme not in ('http','https') or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('EMBED_BASE_URL은 인증정보·쿼리 없는 공개 API 주소여야 합니다.')
    return {'model':settings.EMBED_MODEL,'dimensions':settings.EMBED_DIM,
            'endpoint_sha256':sha256(endpoint.encode('utf-8')).hexdigest()}
