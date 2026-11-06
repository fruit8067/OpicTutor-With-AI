# AI-assisted (OpenAI Codex). OWNER: session-api.
"""Verify the network receive boundary, before UploadFile.read or DB writes."""
import asyncio
import json
from starlette import formparsers
from app.main import app
from test_api_upload import client,send as upload


def test_oversized_multipart_stops_before_consuming_the_remaining_body(client,monkeypatch):
    _,sid,_,answers,path=client
    opened=[]
    original=formparsers.SpooledTemporaryFile
    def spool(*args,**kwargs):
        stream=original(*args,**kwargs);opened.append(stream);return stream
    monkeypatch.setattr(formparsers,'SpooledTemporaryFile',spool)
    header=(b'--limit\r\nContent-Disposition: form-data; name="order_no"\r\n\r\n1\r\n'
            b'--limit\r\nContent-Disposition: form-data; name="client_request_id"\r\n\r\nstream\r\n'
            b'--limit\r\nContent-Disposition: form-data; name="duration_ms"\r\n\r\n3000\r\n'
            b'--limit\r\nContent-Disposition: form-data; name="audio"; filename="answer.webm"\r\n'
            b'Content-Type: audio/webm\r\n\r\n')
    consumed=[];messages=[]
    async def exercise():
        chunks=iter([header]+[b'x'*(1024*1024)]*20+[b'\r\n--limit--\r\n'])
        async def receive():
            chunk=next(chunks)
            consumed.append(len(chunk))
            return {'type':'http.request','body':chunk,'more_body':len(consumed)<22}
        async def send(message): messages.append(message)
        route=f'/api/v1/sessions/{sid}/answers'
        await app({'type':'http','asgi':{'version':'3.0'},'http_version':'1.1','method':'POST',
                   'scheme':'http','path':route,'raw_path':route.encode(),'query_string':b'',
                   'root_path':'','headers':[(b'content-type',b'multipart/form-data; boundary=limit')],
                   'client':('127.0.0.1',1),'server':('127.0.0.1',8000)},receive,send)
    asyncio.run(exercise())
    assert next(m for m in messages if m['type']=='http.response.start')['status']==413
    body=b''.join(m.get('body',b'') for m in messages if m['type']=='http.response.body')
    assert json.loads(body)['error']['code']=='PAYLOAD_TOO_LARGE'
    assert len(consumed)<=12, 'must reject after 11MiB, without reading the remaining 9MiB/boundary'
    assert opened and all(stream.closed for stream in opened)
    assert not answers and not [p for p in path.rglob('*') if p.is_file()]


def test_exact_limit_is_accepted_and_malformed_form_has_contract_error(client):
    c,sid,_,answers,_=client
    assert upload(c,sid,data=b'x'*(10*1024*1024)).status_code==202
    assert len(answers)==1
    response=c.post(f'/api/v1/sessions/{sid}/answers',content=b'broken',headers={'content-type':'multipart/form-data'})
    assert response.status_code==422 and response.json()['error']['code']=='VALIDATION_ERROR'


def test_client_disconnect_closes_partial_spool_without_creating_answer(client,monkeypatch):
    _,sid,_,answers,path=client
    opened=[];original=formparsers.SpooledTemporaryFile
    def spool(*args,**kwargs):
        stream=original(*args,**kwargs);opened.append(stream);return stream
    monkeypatch.setattr(formparsers,'SpooledTemporaryFile',spool)
    async def exercise():
        messages=[]
        chunks=iter([{'type':'http.request','body':b'--cut\r\nContent-Disposition: form-data; name="audio"; filename="x.webm"\r\nContent-Type: audio/webm\r\n\r\npartial','more_body':True},
                     {'type':'http.disconnect'}])
        async def receive(): return next(chunks)
        async def send(message): messages.append(message)
        route=f'/api/v1/sessions/{sid}/answers'
        await app({'type':'http','asgi':{'version':'3.0'},'http_version':'1.1','method':'POST',
                   'scheme':'http','path':route,'raw_path':route.encode(),'query_string':b'',
                   'root_path':'','headers':[(b'content-type',b'multipart/form-data; boundary=cut')],
                   'client':('127.0.0.1',1),'server':('127.0.0.1',8000)},receive,send)
        return messages
    messages=asyncio.run(exercise())
    assert next(m for m in messages if m['type']=='http.response.start')['status']==422
    assert opened and all(stream.closed for stream in opened)
    assert not answers and not [p for p in path.rglob('*') if p.is_file()]
