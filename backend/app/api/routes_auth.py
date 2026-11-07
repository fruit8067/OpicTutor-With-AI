# AI-assisted: 자체 이메일/비밀번호 인증 API 라우터입니다.
# OWNER: session-api (contracts.yaml ownership)
from fastapi import APIRouter, Header
from app import db
from app.errors import AppError
from app.schemas.api import AuthOut, LoginIn, LogoutOut, RegisterIn, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, param = authorization.partition(" ")
    if scheme.lower() != "bearer" or not param.strip():
        return None
    return param.strip()


def optional_current_user(authorization: str | None = Header(default=None)) -> dict | None:
    token = extract_bearer_token(authorization)
    return db.get_user_by_token(token) if token else None


def require_current_user(authorization: str | None = Header(default=None)) -> dict:
    user = optional_current_user(authorization)
    if user is None:
        raise AppError("UNAUTHORIZED")
    return user


@router.post("/register", response_model=AuthOut, status_code=201)
def register(data: RegisterIn):
    user, token = db.create_user(email=data.email, password=data.password, nickname=data.nickname)
    return AuthOut(token=token, user=UserOut(**user))


@router.post("/login", response_model=AuthOut)
def login(data: LoginIn):
    user, token = db.authenticate_user(email=data.email, password=data.password)
    return AuthOut(token=token, user=UserOut(**user))


@router.post("/logout", response_model=LogoutOut)
def logout(authorization: str | None = Header(default=None)):
    token = extract_bearer_token(authorization)
    db.revoke_token(token)
    return LogoutOut(ok=True)


@router.get("/me", response_model=UserOut)
def me(authorization: str | None = Header(default=None)):
    user = require_current_user(authorization)
    return UserOut(**user)

