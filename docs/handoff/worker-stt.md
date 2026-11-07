# worker-stt M2

## 상태
코드·독립 worker CLI·합성 음성/리스 검증 통과, 실제 마이크 및 M2 병합 게이트 대기 (2026-11-07 KST). data-layer M1/M2와 corpus M2가 main에 반영된 기준이다.

## 공개 함수·화면
contracts v7 app.stt/app.worker 및 app.stt.job.handle. 공개 인터페이스 변경 없음. 로컬 Whisper만 사용하며 사용자 원음을 외부로 보내지 않는다.

## 다른 에이전트에게 요청
data-layer M1/M2가 main에 반영되어 DB stub 의존성은 해소됐다. 실제 사용자 마이크 발화 파일은 아직 받지 않았으며 합성 음성 결과와 구분한다. 과거 tx stub 수집 실패는 아래 이력이다.

## 이번 검증

후속 독립 CLI 검증: worker checkout에서 실제 `python -m app.worker --types stt --once` 실행(자식 프로세스에 모듈 조합 없음), 30초 합성 SAPI/캐시된 small.en/CPU int8, 5.046초. answer/job done·attempt1·order1→2, 로그에 전사 없음, 모델 다운로드/외부 요청0. DATA_DIR은 backend 기준 상대 경로로 전달했다. 별도 DB/자식 프로세스는 정리했다. 지표 테스트6개도 독립 checkout에서 통과(0.26초). 증거: 오케스트레이터 PR#26의 docs/compliance/native-standalone-2026-11-07.json. 실제 마이크·C 완주 증거가 아니다.
독립 metrics/audio/worker 경계 16 passed(1.77초). A/B 메모리 조합 검증 101 passed(5.37초)는 전용 테스트 DB에서 실제 queue·HTTP·저장/진행 경계를 연결했다. ASR 추론은 fixture여서 실제 Whisper 품질이나 마이크 검증으로 표시하지 않는다. C 구현은 추가하지 않았다.

## 완료한 것
jobs claim·30초 복구·20초 heartbeat·취소 플래그·유형별 핸들러 지연 로드, 로컬 PyAV/faster-whisper,
VAD/RMS 무음 거부, m1 지표, STT 실패 재시도 및 이전 attempt/리스 결과 차단.
명시적인 NotImplementedError 단일 stub은 확보 전에 제외하여 대기 작업을 소진하지 않는다.

## 실행 방법
PowerShell: `cd backend; .venv/Scripts/python -m app.worker --types stt --once`.
bash: `cd backend && .venv/bin/python -m app.worker --types stt --once`.
계속 실행: `python -m app.worker --types stt,evaluate`.
수동 전사 확인: `python -m app.stt.engine <audio.wav|audio.webm>`.
DB의 SKIP LOCKED로 여러 워커가 서로 다른 작업을 확보한다. 각 워커 ID는 hostname-pid이며 WORKER_ID로 지정 가능.
Ctrl+C는 작업 완료를 최대 lease 동안 기다리고 그 이후에는 만료 복구에 맡긴다.
Whisper 모델은 stt를 담당할 때만 내려받고 로드하며 data/models에 저장한다.

## m1 정의
필러 um/uh/er/ah/hmm/mm/erm을 제외한 단어 수, 전체 시간 WPM, VAD 발화 시간 articulation WPM,
발화 사이 1초 이상 쉼 개수, 필러/유효 단어 100개 비율. 소수 1자리. 하이픈·숫자 각각 1토큰.
like/you know는 필러로 세지 않으며 STT가 제거한 필러는 복원할 수 없다. 등급·발음 점수는 산출하지 않는다.

## 측정값
CPU: AMD Ryzen 5 9600X, 물리 6코어/논리 12개. STT CPU 스레드 4, int8.
small.en/base.en 처리 시간·합성 및 직접 녹음의 검증 결과는 실행 후 기록한다.
실제 마이크 녹음은 아직 미실행이며 합성 음성 테스트와 구분한다.

## 합성 음성 측정 (실제 마이크 아님)

Windows SAPI Zira로 만든 합성 영어 음성을 10/30/60초로 잘랐다. 모델 가중치 다운로드는 로컬 data/models.
모델 warm 상태의 1회 측정이며 실제 수험생 발화의 정확도·처리 속도를 보장하지 않는다.

| 모델 | 10초 | 30초 | 60초 |
| --- | --- | --- | --- |
| small.en | 1.326s | 2.926s | 5.154s |
| base.en | 0.489s | 2.773s | 1.632s |

30초 small.en이 10초 미만이므로 현재 small.en 유지 권장. base.en과의 실제 수험생 정확도 비교는 미실행.

실제 worker --types stt --once: 30초 합성 음성 → answers.done, current_order_no=2. 프로세스 시작 포함 4.827초.
관측 지표 예시(합성 음성):
```json
{
  "wpm": 144.0,
  "speech_sec": 30.0,
  "word_count": 72,
  "duration_sec": 30.0,
  "metrics_version": "m1",
  "articulation_wpm": 144.0,
  "long_pause_count": 0,
  "observed_filler_per100": 5.6
}
```

## 로컬 검증
- backend 전체 테스트 74 passed (PostgreSQL 포함). worker/stt 19개 테스트.
- 무음 3초와 손상 파일을 실제 디코드하여 silence/corrupt 거부 및 순서 유지 확인.
- processing 상태로 남긴 작업의 리스 만료/재확보 후 완료, 이전 attempt 무시, heartbeat 상실 취소 검증.
- API DB 접수→파일 rename 경합은 STT_DECODE_ERROR로 재시도하며 손상 녹음으로 즉시 거부하지 않음.
- tts_prepare 순수 stub은 작업을 확보하지 않고 queued 상태로 유지. 실제 C의 TTS 구현 후 재시작 필요.
- 실제 마이크 녹음과 사용자의 읽기 발화 지표는 미검증. 합성 음성으로 대체 완료했다고 표시하지 않음.

## 실제 프로세스 중단/재시작 결과
자신이 생성한 STT 워커 자식 프로세스만 processing 중에 종료했다. 실제 60초 리스 만료를 기다린 후 새 워커를 시작했다.
- 재시작 returncode=0, answer=done, job=done, attempts=2, current_order_no=2.
- 종료 직후 processing/순서 1을 확인했고 재처리 후 done/순서 2를 확인했다. 리스 시각을 SQL로 앞당기지 않은 실제 복구 실험이다.
- 원음은 합성 60초 파일이며 실제 사용자 마이크 발화는 아니다.
- 공개 PR: https://github.com/fruit8067/OpicTutor-With-AI/pull/7 (Draft).

## tts-host 병합 후 rebase (2026-11-07 11:0x KST)
main 832f898(tts-host M2·계약 v8) 위로 rebase. tts_prepare가 실제 핸들러가 되어 "실제 tts stub 제외" 테스트가 깨졌으므로,
가짜 stub으로 제외 규칙을 확인하는 테스트와 병합된 tts_prepare·stt가 모두 확보 대상인지 확인하는 테스트로 나눴다. 런타임 코드 변경 없음.
backend 전체 69 passed. test_db_ingest 2건은 tiktoken 인코딩 다운로드가 막힌 검증 환경 문제로 main에서도 동일하게 실패한다.
실제 마이크 검증은 아직 대기다.
