# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: worker-stt (contracts.yaml ownership)
class RetryableJobError(Exception):
    def __init__(self,error_code,detail=None):
        self.error_code=error_code;self.detail=detail
        super().__init__(error_code)

class PermanentJobError(Exception):
    def __init__(self,error_code,detail=None):
        self.error_code=error_code;self.detail=detail
        super().__init__(error_code)
