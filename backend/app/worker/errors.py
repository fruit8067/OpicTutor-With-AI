# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: worker-stt (contracts.yaml ownership)
class RetryableJobError(Exception):
    pass

class PermanentJobError(Exception):
    pass
