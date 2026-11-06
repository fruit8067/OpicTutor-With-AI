# AI-assisted (OpenAI Codex). OWNER: session-api.
"""Bound file parts while multipart data arrives, before FastAPI spools them all."""
from contextlib import aclosing
from fastapi.routing import APIRoute
from starlette.formparsers import MultiPartException,MultiPartParser
from starlette.requests import ClientDisconnect
from app.errors import AppError
from .deps import UPLOAD_MAX_BYTES


class _FileTooLarge(MultiPartException):
    pass


class _LimitedMultipartParser(MultiPartParser):
    def on_part_begin(self):
        super().on_part_begin()
        self._file_bytes=0

    def on_part_data(self,data,start,end):
        if self._current_part.file is not None:
            self._file_bytes+=end-start
            if self._file_bytes>UPLOAD_MAX_BYTES:
                raise _FileTooLarge('File limit exceeded')
        super().on_part_data(data,start,end)


class UploadRoute(APIRoute):
    def get_route_handler(self):
        original=super().get_route_handler()
        async def handle(request):
            multipart=request.headers.get('content-type','').split(';',1)[0].strip().lower()=='multipart/form-data'
            if request.method!='POST' or not self.path.endswith('/answers') or not multipart:
                return await original(request)
            parser=_LimitedMultipartParser(request.headers,request.stream())
            form=None
            try:
                # FastAPI reuses Request's parsed form cache. Parsing outside its
                # handler also preserves the contract error envelope for failures.
                async with aclosing(parser.stream):
                    try: form=await parser.parse()
                    except _FileTooLarge: raise AppError('PAYLOAD_TOO_LARGE') from None
                    except (MultiPartException,ClientDisconnect): raise AppError('VALIDATION_ERROR') from None
                request._form=form
                return await original(request)
            finally:
                if form is not None: await form.close()
                else:
                    # Also cover client disconnection on older Starlette releases.
                    for stream in parser._files_to_close_on_error: stream.close()
        return handle
