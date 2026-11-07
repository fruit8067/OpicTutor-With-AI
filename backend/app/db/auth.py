# AI-assisted: 자체 이메일/비밀번호 인증 및 토큰 발급·검증 모듈입니다.
# OWNER: data-layer (contracts.yaml ownership)
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import re
import secrets
from uuid import UUID
from psycopg.errors import UniqueViolation
from app.errors import AppError
from .pool import tx

PBKDF2_ITERATIONS = 200_000
TOKEN_TTL_DAYS = 7
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize_email(email: str) -> str:
    norm = (email or "").strip().lower()
    if not norm or len(norm) > 254 or not EMAIL_RE.match(norm):
        raise AppError("VALIDATION_ERROR", {"field": "email"})
    return norm


def _hash_password(password: str) -> str:
    if not password or len(password) < 6 or len(password) > 128:
        raise AppError("VALIDATION_ERROR", {"field": "password"})
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iters_str, salt, digest_hex = stored.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", (password or "").encode("utf-8"), bytes.fromhex(salt), int(iters_str))
        return hmac.compare_digest(dk.hex(), digest_hex)
    except Exception:
        return False


def _token_hash(raw_token: str) -> str:
    return hashlib.sha256((raw_token or "").encode("utf-8")).hexdigest()


def _issue_token_in_tx(cur, user_id: UUID) -> str:
    raw = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=TOKEN_TTL_DAYS)
    cur.execute(
        "INSERT INTO auth_tokens(token_hash, user_id, expires_at) VALUES (%s, %s, %s)",
        (_token_hash(raw), user_id, expires_at),
    )
    return raw


def create_user(*, email: str, password: str, nickname: str) -> tuple[dict, str]:
    norm_email = _normalize_email(email)
    clean_nick = (nickname or "").strip()
    if not clean_nick or len(clean_nick) > 30:
        raise AppError("VALIDATION_ERROR", {"field": "nickname"})
    pw_hash = _hash_password(password)
    try:
        with tx() as cur:
            cur.execute(
                """INSERT INTO users(email, password_hash, nickname)
                   VALUES (%s, %s, %s)
                   RETURNING id, email, nickname, created_at""",
                (norm_email, pw_hash, clean_nick),
            )
            user = cur.fetchone()
            token = _issue_token_in_tx(cur, user["id"])
            return user, token
    except UniqueViolation as exc:
        raise AppError("EMAIL_ALREADY_EXISTS") from exc


def authenticate_user(*, email: str, password: str) -> tuple[dict, str]:
    norm_email = (email or "").strip().lower()
    if not norm_email or not password:
        raise AppError("INVALID_CREDENTIALS")
    with tx() as cur:
        cur.execute(
            "SELECT id, email, password_hash, nickname, created_at FROM users WHERE email=%s",
            (norm_email,),
        )
        row = cur.fetchone()
        if row is None or not _verify_password(password, row["password_hash"]):
            raise AppError("INVALID_CREDENTIALS")
        token = _issue_token_in_tx(cur, row["id"])
        user = {k: row[k] for k in ("id", "email", "nickname", "created_at")}
        return user, token


def get_user_by_token(raw_token: str | None) -> dict | None:
    if not raw_token:
        return None
    th = _token_hash(raw_token.strip())
    with tx() as cur:
        cur.execute(
            """SELECT u.id, u.email, u.nickname, u.created_at
               FROM auth_tokens t
               JOIN users u ON u.id = t.user_id
               WHERE t.token_hash = %s AND t.expires_at > now()""",
            (th,),
        )
        return cur.fetchone()


def revoke_token(raw_token: str | None) -> bool:
    if not raw_token:
        return False
    th = _token_hash(raw_token.strip())
    with tx() as cur:
        cur.execute("DELETE FROM auth_tokens WHERE token_hash = %s", (th,))
        return cur.rowcount > 0

