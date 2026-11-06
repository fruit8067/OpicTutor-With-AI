# 로컬 실행 및 검증

계약은 `agents/contracts.yaml` v3다. 브랜치는 bootstrap → data-layer → session-api → corpus → grader → worker-stt → integrator 순으로 쌓였다.
B의 corpus·grader·worker-stt는 구현되었다. C의 tts-host·frontend와 각 PR 병합 및 실제 키·음성 검증이 남아 있다.

## 준비

Python 3.11+, Node 20+, 실행 중인 Docker Desktop과 마이크가 필요하다.
`backend/.env.example`을 `backend/.env`로 복사하고 LLM_API_KEY, EMBED_API_KEY를 로컬에서 설정한다.
키·원음·data/는 커밋하지 않는다. DB와 API는 127.0.0.1에만 바인딩한다.
`rag_docs/build/`에는 corpus 담당자가 생성한 VERSION, scenarios.json, Q000 및 검토된 v3 태그가 있는 questions.jsonl,
answers.jsonl, rubrics.jsonl, upgrade_patterns.jsonl이 있어야 한다.

## PowerShell

저장소 루트에서:

```powershell
docker compose up -d
Copy-Item backend/.env.example backend/.env # 처음 한 번만, 기존 키 파일을 덮어쓰지 말 것
python -m venv backend/.venv
backend/.venv/Scripts/python -m pip install -r backend/requirements.txt
Set-Location backend
.venv/Scripts/Activate.ps1
python -m scripts.db_reset --yes # 새 개발 DB만. 기존 시험 데이터가 모두 삭제됨
python -m scripts.ingest_rag --dry-run
python -m scripts.ingest_rag
python -m scripts.import_tts ./tts_mp3.zip --activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

별도 터미널에서 각각:

```powershell
Set-Location backend
.venv/Scripts/Activate.ps1
python -m app.worker
```

```powershell
Set-Location frontend
npm ci
npm run dev -- --host 127.0.0.1
```

## bash

```bash
docker compose up -d
test -e backend/.env || cp backend/.env.example backend/.env
python -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
cd backend
python -m scripts.db_reset --yes # 새 개발 DB에서만
python -m scripts.ingest_rag --dry-run
python -m scripts.ingest_rag
python -m scripts.import_tts ./tts_mp3.zip --activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

별도 터미널에서 `cd backend && source .venv/bin/activate && python -m app.worker`.
다른 터미널에서 `cd frontend && npm ci && npm run dev -- --host 127.0.0.1`.

TTS 폴더를 반입하려면 `python -m scripts.import_tts static/tts/VOICE_ID --activate`.
음성 재생성은 [tts-host 인수인계](handoff/tts-host.md)와 `colab/omnivoice_tts.ipynb`를 따른다.
이 문서의 import_tts 및 worker 명령은 해당 PC 구현이 병합된 후에 사용할 수 있다.

## B만 로컬 확인하기

`agent/worker-stt` 또는 최신 `agent/integrator` 브랜치에서 backend 가상환경을 활성화한다.
`python -m app.db.dev seed-session --status in_progress`로 개발용 세션을 만들고,
`python -m app.db.dev seed-answer SESSION_ID ./answer.wav`로 자신이 준비한 녹음을 접수한다.
`python -m app.worker --types stt --once` 후 답변 done과 current_order_no 전진을 확인한다.
`python -m app.stt.engine ./answer.wav`는 명시적인 수동 확인용으로 전사·지표를 출력한다.
코퍼스: `cd rag_docs` 후 `python scripts/build_corpus.py`와 `python scripts/test_corpus_v3.py`.
평가 계획: backend에서 `python -m scripts.eval_exam --traps --plan`은 외부 호출 없이 계획 리포트를 만든다.
실제 평가에는 키·코퍼스 적재와 LLM 입력/출력·검색 임베딩 단가 확인이 필요하다.
순수 TTS stub은 워커가 확보하지 않아 대기 작업을 소진하지 않는다. C 반영 후 워커를 재시작한다.

## Core A 검증

backend 가상환경에서 `pip install pytest httpx pyyaml` 후:

```text
python -m pytest tests -q
python -m scripts.e2e_smoke --level IM2
python -m scripts.e2e_smoke --level IL --fail-cases
```

합성 답변은 `backend/e2e_audio/{IM2|IL}/{question_id}.mp3` 또는 `.wav`로 준비한다.
MP3는 계약의 업로드 MIME에 없으므로 smoke가 PyAV로 로컬 WAV로 변환한다. 실제 수험생 원음은 전송하지 않는다.
HTTP 오류·준비 실패·STT 실패·평가 실패·타임아웃은 exit 1이다. 예상 등급 범위 차이는 경고로만 표시한다.

소유권 검사(저장소 루트, 쌓인 브랜치의 직전 단계 기준):

```text
python agents/tools/check_ownership.py bootstrap --phase0
python agents/tools/check_ownership.py data-layer --base agent/bootstrap
python agents/tools/check_ownership.py session-api --base agent/data-layer
python agents/tools/check_ownership.py corpus --base agent/session-api
python agents/tools/check_ownership.py grader --base agent/corpus
python agents/tools/check_ownership.py worker-stt --base agent/grader
python agents/tools/check_ownership.py integrator --base agent/worker-stt
```

위 검사기는 현재 HEAD를 검사하므로 각 단계의 브랜치에서 실행한다. main에 병합한 뒤에는 기본 `--base origin/main` 사용.

## 자동 검증 범위와 수동 확인

`--fail-cases`는 무음 거부→재녹음, 처리 중 추가 업로드(워커 처리 전인 경우), 다른 순서 업로드,
중복 업로드·제출, 조기 제출, 반복 조회의 불변성, 자기소개 근거 배제와 v3 결과 계약을 확인한다.
HTTP만으로 DB의 요청 수나 워커 리스 상태를 볼 수 없으므로 아래는 별도 확인한다.

| 시나리오 | 확인 방법 |
| --- | --- |
| TTS 하나 누락→prepare_failed→복구→동일 세트 retry | 소유자가 파일을 임시 이동하고 원위치 복구, 세션 질문 행의 ID/순서 비교 |
| 시험 중 평가 호출 0, 결과 재조회 10회 후 요청 수 불변 | `app.db.count_ai_requests('evaluate')`를 전후 비교 |
| 잘못된 LLM 키→grading_failed→키 복구→regrade | 원문/키를 기록하지 않고 상태·run_no만 기록 |
| 이전 run의 늦은 완료 무시 | test_db_invariants의 재평가 테스트와 실제 작업 지연 확인 |
| 워커 종료 후 리스 복구 | 로컬 워커 종료·재시작 후 jobs 리스와 attempts 확인 |
| 실제 마이크 8문항 완주 | 브라우저에서 직접 녹음하고 동의를 받은 화면 증거를 integrator-assets/에 보관 |
| 비용·토큰·지연 | ai_requests 메타데이터 합계 및 smoke 시간 표 기록 |

## 자주 나는 오류

- `/health` ready=false: DB → 코퍼스 적재 → 활성 음성 순으로 확인. 초기화 실패해도 API와 `/docs`는 열린다.
- SCENARIO_UNAVAILABLE: Q000·pilot·슬롯 8개·문항 태그·scenarios.json을 corpus 담당자가 검토해야 한다.
- VERSION 누락: 임의 버전을 만들지 말고 corpus M1 결과를 반영한다.
- TTS_FILE_MISSING/TTS_HASH_MISMATCH: 음성을 재생성·반입하고 동일 세션의 prepare/retry. 문항을 교체하지 않는다.
- DB 테스트 skip: 실제 PostgreSQL 검증을 통과한 것이 아니다. Docker를 시작하고 다시 실행한다.
- Docker Desktop dockerInference 시작 오류: 이 PC에서 관찰된 로컬 환경 문제다. 앱의 진단을 확인한다.
  factory reset은 데이터 삭제를 수반하므로 이 실행 절차에는 포함하지 않는다.
- GitHub PR 생성 403: 연결 도구의 권한 문제. push된 브랜치의 GitHub 비교 화면에서 PR을 생성할 수 있다.
