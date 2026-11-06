# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성했습니다.
# OWNER: worker-stt (contracts.yaml ownership)
import argparse
import logging
from app.config import settings
from .runner import run

def main():
    parser=argparse.ArgumentParser(description='로컬 작업 워커. STT 원음은 외부로 전송하지 않는다.')
    parser.add_argument('--types',default=settings.WORKER_JOB_TYPES)
    parser.add_argument('--once',action='store_true')
    args=parser.parse_args();types=list(dict.fromkeys(t.strip() for t in args.types.split(',') if t.strip()))
    if not types or any(t not in ['tts_prepare','stt','evaluate'] for t in types):
        parser.error('--types는 tts_prepare,stt,evaluate 중 쉼표로 구분하세요.')
    logging.basicConfig(level=settings.LOG_LEVEL,format='%(message)s')
    # 라이브러리 DEBUG 전사/요청 본문이 일반 작업 로그에 섞이지 않도록 제한한다.
    for name in ['faster_whisper','openai','httpx','httpx2','httpcore','httpcore2','huggingface_hub']:
        logging.getLogger(name).setLevel(logging.WARNING)
    return run(types,args.once)

if __name__=='__main__': raise SystemExit(main())
