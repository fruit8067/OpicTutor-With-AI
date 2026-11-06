# AI-assisted (OpenAI Codex). OWNER: orchestrator.
"""Real loopback HTTP: reject an oversized upload before its declared body ends.

Uvicorn lifespan is off: this checks the HTTP/parser boundary only, without a
database, model, TTS fixture, microphone, or provider call. No production C code.
"""
import argparse
import http.client
import json
from pathlib import Path
import socket
from threading import Thread
import time
from uuid import uuid4
import uvicorn
from verify_core import compose_sources


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    compose_sources(args.workspace,emit_manifest=False)
    from app.main import app
    listener=socket.socket()
    listener.bind(('127.0.0.1',0));listener.listen(128)
    port=listener.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,lifespan='off',log_level='error',access_log=False))
    thread=Thread(target=server.run,kwargs={'sockets':[listener]},daemon=True)
    thread.start()
    try:
        deadline=time.monotonic()+10
        while not server.started:
            if not thread.is_alive() or time.monotonic()>deadline: raise RuntimeError('Own loopback server failed to start')
            time.sleep(.02)
        header=(b'--wire\r\nContent-Disposition: form-data; name="audio"; filename="answer.webm"\r\n'
                b'Content-Type: audio/webm\r\n\r\n')
        declared=len(header)+20*1024*1024+len(b'\r\n--wire--\r\n')
        sent_file=10*1024*1024+64*1024
        with socket.create_connection(('127.0.0.1',port),timeout=10) as client:
            request=(f'POST /api/v1/sessions/{uuid4()}/answers HTTP/1.1\r\nHost: 127.0.0.1\r\n'
                     f'Content-Type: multipart/form-data; boundary=wire\r\nContent-Length: {declared}\r\nConnection: close\r\n\r\n').encode()
            client.sendall(request+header)
            for _ in range(sent_file//65536): client.sendall(b'x'*65536)
            # Do not send remaining bytes or terminating boundary. Wait for 413 now.
            response=http.client.HTTPResponse(client);response.begin()
            body=json.loads(response.read())
        result={'transport':'real loopback socket + uvicorn HTTP/1.1',
                'scope':'upload/parser boundary only; lifespan off; no DB or inference',
                'declared_body_bytes':declared,'sent_file_bytes':sent_file,
                'multipart_terminator_sent':False,'status':response.status,'error_code':body['error']['code'],
                'external_provider_calls':0,'c_implementation_added':False}
        assert result['status']==413 and result['error_code']=='PAYLOAD_TOO_LARGE'
        if args.report: args.report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result))
    finally:
        server.should_exit=True
        thread.join(timeout=10)
        listener.close()
        if thread.is_alive(): raise RuntimeError('Own loopback server did not stop')
    return 0


if __name__=='__main__': raise SystemExit(main())
