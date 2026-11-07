# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: bootstrap (contracts.yaml ownership)
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

ERROR_CODES = {'VALIDATION_ERROR': {'http': 422, 'message': '요청 형식이 올바르지 않습니다.'}, 'EMAIL_ALREADY_EXISTS': {'http': 409, 'message': '이미 가입된 이메일이에요. 로그인하거나 다른 이메일을 입력해 주세요.'}, 'INVALID_CREDENTIALS': {'http': 401, 'message': '이메일 또는 비밀번호가 일치하지 않아요.'}, 'UNAUTHORIZED': {'http': 401, 'message': '로그인이 필요해요. 다시 로그인해 주세요.'}, 'FORBIDDEN': {'http': 403, 'message': '본인의 시험 기록만 조회하거나 변경할 수 있어요.'}, 'SERVICE_NOT_READY': {'http': 503, 'message': '서버를 준비하고 있어요. 잠시 후 다시 시도해 주세요.'}, 'SESSION_NOT_FOUND': {'http': 404, 'message': '시험 정보를 찾을 수 없어요.'}, 'ANSWER_NOT_FOUND': {'http': 404, 'message': '답변을 찾을 수 없어요.'}, 'INVALID_STATE': {'http': 409, 'message': '지금 단계에서는 할 수 없는 요청이에요.'}, 'SCENARIO_UNAVAILABLE': {'http': 422, 'message': '선택한 시나리오로는 시험을 구성할 수 없어요. 다른 설정을 선택해 주세요.'}, 'MIC_CHECK_REQUIRED': {'http': 422, 'message': '마이크 테스트를 먼저 완료해 주세요.'}, 'ORDER_MISMATCH': {'http': 409, 'message': '현재 문항이 아니에요. 화면을 새로고침해 주세요.'}, 'ANSWER_PENDING': {'http': 409, 'message': '이전 답변을 처리하고 있어요.'}, 'REPLAY_LIMIT': {'http': 409, 'message': '다시 듣기는 한 번만 할 수 있어요.'}, 'AUDIO_TOO_SHORT': {'http': 422, 'message': '녹음이 너무 짧아요. 다시 답변해 주세요.'}, 'AUDIO_TOO_LONG': {'http': 422, 'message': '녹음이 너무 길어요.'}, 'UNSUPPORTED_MEDIA': {'http': 415, 'message': '지원하지 않는 녹음 형식이에요.'}, 'PAYLOAD_TOO_LARGE': {'http': 413, 'message': '녹음 파일이 너무 커요.'}, 'NOT_ALL_ANSWERED': {'http': 409, 'message': '아직 저장되지 않은 답변이 있어요.'}, 'NOT_IMPLEMENTED': {'http': 501, 'message': '준비 중인 기능이에요.'}, 'INTERNAL_ERROR': {'http': 500, 'message': '잠시 후 다시 시도해 주세요.'}}

class AppError(Exception):
    def __init__(self, code: str, detail: dict | None = None):
        self.code = code
        info = ERROR_CODES.get(code, ERROR_CODES['INTERNAL_ERROR'])
        self.http_status = info['http']
        self.message = info['message']
        self.detail = detail
        super().__init__(code)

def install_error_handlers(app: FastAPI) -> None:
    def response(exc: AppError):
        return JSONResponse(status_code=exc.http_status, content={'error': {
            'code': exc.code, 'message': exc.message, 'detail': exc.detail or {}}})
    @app.exception_handler(AppError)
    async def app_error(request: Request, exc: AppError):
        return response(exc)
    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return response(AppError('VALIDATION_ERROR'))
    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception):
        return response(AppError('INTERNAL_ERROR'))
