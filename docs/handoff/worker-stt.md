# worker-stt M2

## 상태
로컬 워커·STT 구현 및 합성 음성/실제 리스 복구 검증 완료, 마이크 검증 대기 (2026-11-06 KST). agent/grader 위에 쌓은 브랜치.

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
