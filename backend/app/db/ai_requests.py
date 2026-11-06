# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: data-layer (contracts.yaml ownership)
from uuid import UUID
from datetime import datetime
from .pool import tx

def log_ai_request(*, job_id: UUID | None, purpose: str, model: str, input_tokens: int | None,
                   output_tokens: int | None, latency_ms: int | None, status: str, error_code: str | None) -> None:
    with tx() as cur:
        cur.execute("""INSERT INTO ai_requests(job_id,purpose,model,input_tokens,output_tokens,latency_ms,status,error_code)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",(job_id,purpose,model,input_tokens,output_tokens,latency_ms,status,error_code))

def count_ai_requests(purpose: str, since: datetime | None = None) -> int:
    with tx() as cur:
        cur.execute('SELECT count(*) AS n FROM ai_requests WHERE purpose=%s AND (%s::timestamptz IS NULL OR created_at>=%s)',(purpose,since,since))
        return cur.fetchone()['n']
