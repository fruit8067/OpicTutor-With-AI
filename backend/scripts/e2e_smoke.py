# AI-assisted: 이 코드는 OpenAI Codex의 도움으로 작성되었습니다.
# OWNER: integrator (contracts.yaml ownership)
"""실제 HTTP API로 합성 답변 8개를 제출한다. 가짜 성공 결과를 만들지 않는다."""
import argparse
import io
import json
import time
import wave
from pathlib import Path
from uuid import uuid4
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


LEVELS = ['NL','NM','NH','IL','IM1','IM2','IM3','IH','AL']
BASE_LEVELS = ['NL','NM','NH','IL','IM','IH','AL']


class SmokeFailure(RuntimeError):
    pass


class Client:
    def __init__(self, base):
        self.base = base.rstrip('/')

    def request(self, method, path, *, data=None, content_type='application/json', expected=(200,)):
        body = json.dumps(data).encode() if data is not None and content_type == 'application/json' else data
        request = Request(self.base+path, data=body, method=method, headers={'Content-Type':content_type})
        try:
            with urlopen(request, timeout=30) as response:
                status, payload = response.status, json.load(response)
        except HTTPError as exc:
            status = exc.code
            try:
                payload = json.load(exc)
            except ValueError:
                raise SmokeFailure(f'{method} {path}: JSON이 아닌 오류 응답 HTTP {status}') from exc
        except (URLError, TimeoutError) as exc:
            raise SmokeFailure(f'{method} {path}: 서버 연결 실패') from exc
        if status not in expected:
            code = payload.get('error',{}).get('code','unknown')
            raise SmokeFailure(f'{method} {path}: HTTP {status} ({code})')
        return payload

    def upload(self, sid, order, key, audio, duration_ms, expected=(202,)):
        boundary = 'opic-'+uuid4().hex
        parts=[]
        for name,value in [('order_no',order),('client_request_id',key),('duration_ms',duration_ms)]:
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="audio"; filename="answer.wav"\r\nContent-Type: audio/wav\r\n\r\n'.encode()+audio+b'\r\n')
        parts.append(f'--{boundary}--\r\n'.encode())
        return self.request('POST',f'/sessions/{sid}/answers',data=b''.join(parts),
            content_type='multipart/form-data; boundary='+boundary,expected=expected)


def check(condition, message):
    if not condition:
        raise SmokeFailure(message)


def poll(read, finished, failed, timeout, label):
    deadline=time.monotonic()+timeout
    while True:
        result=read()
        if failed(result):
            code=result.get('error_code') or result.get('prepare',{})
            raise SmokeFailure(f'{label} 실패: {code}')
        if finished(result):
            return result
        if time.monotonic()>=deadline:
            raise SmokeFailure(f'{label} 제한 시간 초과 ({timeout}s)')
        time.sleep(2)


def wav_audio(path):
    """계약은 MP3 업로드를 허용하지 않으므로 로컬 합성 MP3를 WAV로 변환한다."""
    if path.suffix.lower()=='.wav':
        data=path.read_bytes()
        with wave.open(io.BytesIO(data),'rb') as source:
            duration_ms=round(source.getnframes()*1000/source.getframerate())
        return data,duration_ms
    try:
        import av
    except ImportError as exc:
        raise SmokeFailure('MP3 변환에 av가 필요합니다. pip install -r requirements/worker-stt.txt') from exc
    buffer=io.BytesIO()
    with wave.open(buffer,'wb') as output:
        output.setnchannels(1);output.setsampwidth(2);output.setframerate(16000)
        resampler=av.AudioResampler(format='s16',layout='mono',rate=16000)
        with av.open(str(path)) as source:
            for frame in source.decode(audio=0):
                for converted in resampler.resample(frame):
                    output.writeframes(converted.to_ndarray().tobytes())
            for converted in resampler.resample(None):
                output.writeframes(converted.to_ndarray().tobytes())
    data=buffer.getvalue()
    return data,round((len(data)-44)*1000/32000)


def silence_audio():
    buffer=io.BytesIO()
    with wave.open(buffer,'wb') as out:
        out.setnchannels(1);out.setsampwidth(2);out.setframerate(16000);out.writeframes(b'\0'*(16000*2*3))
    return buffer.getvalue(),3000


def find_audio(root, question_id, order):
    candidates=[root/(question_id+'.mp3'),root/(question_id+'.wav'),root/(str(order)+'.mp3'),
                root/(f'{order:02d}.mp3'),root/(f'{order:02d}_{question_id}.mp3')]
    path=next((p for p in candidates if p.is_file()),None)
    if path is None:
        raise SmokeFailure(f'합성 답변 음성 누락: {root}/{question_id}.mp3')
    return path


def validate_result(result):
    check(result.get('rubric_version')=='performance-feedback-actfl-speaking-v3','rubric_version 불일치')
    check(result.get('prompt_version')=='opic-evaluation-system-v3','prompt_version 불일치')
    check(result.get('assessment_basis')=='transcript_and_metrics','assessment_basis 불일치')
    scope=result['evaluation_scope']
    check(scope['feedback_only_order_nos']==[1],'자기소개 채점 제외 위반')
    check(sorted(scope['scored_order_nos'])==list(range(2,9)),'채점 범위 오류')
    check(sorted(scope['submitted_order_nos'])==list(range(1,9)),'제출 범위 오류')
    base,level=result.get('base_level'),result.get('estimated_level')
    status=result.get('assessment_status')
    check(status in ('assessed','insufficient_evidence'),'평가 상태 오류')
    if status=='insufficient_evidence':
        check(base is None and level is None and bool(result.get('insufficient_reason')),'평가 불가 등급/사유 오류')
    else:
        check(base in BASE_LEVELS,'큰 범주 오류')
        check(level in ['IM1','IM2','IM3',None] if base=='IM' else level==base,'2단 등급 불일치')
    if base=='IM':
        if level is not None:
            check(result.get('im_estimation_status')=='provisional','IM 잠정 진단 표시 누락')
            check(result.get('im_rubric_version')=='project-im-v1','IM 기준 버전 불일치')
            check(bool(result.get('provisional_label')),'IM 잠정 진단 문구 누락')
        else:
            check(result.get('im_estimation_status')=='insufficient_evidence' and bool(result.get('insufficient_reason')),'IM 세분화 보류 사유 누락')
    else:
        check(result.get('im_estimation_status')=='not_applicable','IM 외 진단 상태 오류')
    for evidence in result['fact_evidence']:
        check(evidence.get('order_no')!=1,'FACT 근거에 자기소개 혼입')
    for entry in result['dimension_feedback'].values():
        check(1 not in entry['evidence_order_nos'],'영역 근거에 자기소개 혼입')
    for name in ['sustained_performance','breakdown_observations']:
        for entry in result[name]:
            check(all(e['order_no']!=1 for e in entry['evidence']),'수행/붕괴 근거에 자기소개 혼입')
    for entries in result['coverage'].values():
        for entry in entries:
            check(1 not in entry['elicited_order_nos']+entry['usable_order_nos'],'커버리지에 자기소개 혼입')
    for card in result['feedback_cards']:
        check(1 not in card['related_order_nos'],'평가 카드에 자기소개 혼입')
    items=result['items']
    check(sorted(i['order_no'] for i in items)==list(range(1,9)),'문항 피드백 누락/중복')
    check(all(i['evaluation_role']==('feedback_only' if i['order_no']==1 else 'scored') for i in items),'문항 평가 역할 오류')


def run(args):
    client=Client(args.base_url)
    health=client.request('GET','/health')
    check(health['ready'],'서버가 준비되지 않았습니다. DB·코퍼스·활성 TTS 음성을 확인하세요.')
    created=client.request('POST','/sessions',data={'client_request_id':str(uuid4()),'scenario_id':'default',
        'mic_check_passed':True},expected=(200,202))
    sid=created['session_id'];print(f'session_id={sid}')
    prefix=f'/sessions/{sid}'
    poll(lambda:client.request('GET',prefix),lambda s:s['status']=='ready',
        lambda s:s['status'] in ('prepare_failed','cancelled'),args.timeout,'TTS 준비')
    client.request('POST',prefix+'/start')
    rows=[];first_key=None;first_answer=None;first_audio=None
    for order in range(1,9):
        current=client.request('GET',prefix+'/current');question=current['question']
        check(question and question['order_no']==order,'현재 문항 순서 오류')
        check(question['is_scored']==(order!=1),'워밍업 채점 태그 오류')
        again=client.request('GET',prefix+'/current')
        check(again['question']==question,'문항 조회가 확정 세트를 변경함')
        path=find_audio(args.audio_dir,question['question_id'],order)
        audio,duration=wav_audio(path)
        check(2000<=duration<=125000 and len(audio)<=10485760,'합성 답변의 길이/용량이 계약 제한을 벗어남')
        if args.fail_cases and order==1:
            silent,ms=silence_audio()
            rejected=client.upload(sid,order,str(uuid4()),silent,ms)
            out=poll(lambda:client.request('GET',prefix+'/answers/'+rejected['answer_id']),
                lambda a:a['stt_status']=='rejected',lambda a:a['stt_status'] in ('done','failed'),args.timeout,'무음 거부')
            check(out['current_order_no']==1,'무음 거부가 문항 순서를 전진시킴')
        key=str(uuid4());started=time.monotonic();accepted=client.upload(sid,order,key,audio,duration)
        # 빠른 워커가 응답 직전에 완료할 수 있으므로 접수 응답만으로 전진 주체를 단정하지 않는다.
        check(accepted['current_order_no'] in (order,order+1),'접수 응답의 문항 순서 오류')
        duplicate=client.upload(sid,order,key,audio,duration,expected=(200,))
        check(duplicate['answer_id']==accepted['answer_id'],'업로드 멱등성 오류')
        if order==1:
            first_key,first_answer,first_audio=key,accepted['answer_id'],(audio,duration)
        if args.fail_cases:
            # 워커가 빨리 끝난 경우를 고려해 queued/processing일 때만 pending 검사를 수행한다.
            state=client.request('GET',prefix+'/answers/'+accepted['answer_id'])
            if state['stt_status'] in ('queued','processing'):
                pending=client.upload(sid,order,str(uuid4()),audio,duration,expected=(409,))
                if pending['error']['code']=='ORDER_MISMATCH':
                    completed=client.request('GET',prefix+'/answers/'+accepted['answer_id'])
                    check(completed['stt_status']=='done','처리 중 추가 답변 차단 오류')
                    print(f'{order}번: 워커 완료 경합으로 pending 검사는 관찰하지 못함')
                else:
                    check(pending['error']['code']=='ANSWER_PENDING','처리 중 추가 답변 차단 오류')
            wrong_order=0  # current_order_no가 전진하는 경합과 관계없이 항상 과거/미래 문항이다.
            mismatch=client.upload(sid,wrong_order,str(uuid4()),audio,duration,expected=(409,))
            check(mismatch['error']['code']=='ORDER_MISMATCH','다른 문항 업로드 차단 오류')
        done=poll(lambda:client.request('GET',prefix+'/answers/'+accepted['answer_id']),
            lambda a:a['stt_status']=='done',lambda a:a['stt_status'] in ('failed','rejected'),args.timeout,f'{order}번 STT')
        check(done['current_order_no']==order+1,'STT 완료 후 순서 전진 오류')
        rows.append((str(order),f'{time.monotonic()-started:.2f}s','done'))
        if args.fail_cases and order==7:
            early=client.request('POST',prefix+'/submit',expected=(409,))
            check(early['error']['code']=='NOT_ALL_ANSWERED','조기 제출 차단 오류')
    if args.fail_cases:
        duplicate=client.upload(sid,1,first_key,*first_audio,expected=(200,))
        check(duplicate['answer_id']==first_answer and duplicate['current_order_no']==9,'완료 후 업로드 재전송 오류')
    started=time.monotonic()
    client.request('POST',prefix+'/submit',expected=(202,))
    client.request('POST',prefix+'/submit',expected=(202,))
    result=poll(lambda:client.request('GET',prefix+'/result'),lambda r:r['evaluation_status']=='done',
        lambda r:r['evaluation_status']=='failed',args.timeout,'종합 평가')
    check(result['run_no']==1,'중복 제출로 평가 실행이 중복됨')
    validate_result(result['result'])
    for _ in range(10):
        refreshed=client.request('GET',prefix+'/result')
        check(refreshed==result,'결과 재조회로 저장된 결과가 변경됨')
    rows.append(('평가',f'{time.monotonic()-started:.2f}s',str(result['result']['estimated_level'])))
    print('| 단계 | 시간 | 결과 |\n| --- | --- | --- |')
    for row in rows:
        print('| '+' | '.join(row)+' |')
    base,level=result['result']['base_level'],result['result']['estimated_level']
    expected=(base=='IM') if args.level=='IM2' else level in ['NH','IL','IM1']
    if not expected:
        print('경고: 합성 세트 예상 범위 밖. 정확도 실패로 간주하지 않으며 grader 리포트와 비교하세요.')
    print('PASS: HTTP 완주. AI 요청 수/비용·리스 복구·키 오류·TTS 파일 복구·실제 마이크는 RUNBOOK 수동 검증 필요.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--level',choices=['IM2','IL'],default='IM2')
    parser.add_argument('--fail-cases',action='store_true')
    parser.add_argument('--base-url',default='http://127.0.0.1:8000/api/v1')
    parser.add_argument('--timeout',type=int,default=300)
    parser.add_argument('--audio-dir',type=Path)
    args=parser.parse_args()
    if args.timeout<=0:
        parser.error('--timeout은 양수여야 합니다.')
    args.audio_dir=args.audio_dir or Path(__file__).resolve().parents[1]/'e2e_audio'/args.level
    try:
        run(args)
    except (SmokeFailure,OSError,ValueError,KeyError,TypeError) as exc:
        parser.exit(1,f'FAIL: {exc}\n')


if __name__=='__main__':
    main()
