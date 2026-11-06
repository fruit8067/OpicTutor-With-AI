# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: data-layer (contracts.yaml ownership)
"""자기 컴퓨터의 개발 DB 초기화. --yes 필수."""
import argparse
from psycopg import sql
from app.db import init_db
from app.db.pool import tx

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--yes',action='store_true')
    if not parser.parse_args().yes: parser.error('초기화하려면 --yes를 지정하세요.')
    with tx() as cur:
        for name in ['ai_requests','jobs','evaluations','answers','session_host_lines','session_questions',
                     'tts_assets','sessions','rag_docs','schema_migrations']:
            cur.execute(sql.SQL('DROP TABLE IF EXISTS {} CASCADE').format(sql.Identifier(name)))
    init_db()
    print('개발 DB 초기화 완료')

if __name__=='__main__': main()
