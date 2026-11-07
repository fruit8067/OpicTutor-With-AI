# tts-host 인수인계

> AI-assisted: this handoff was written with help from Claude (Anthropic).

## 상태

**M2 code 검증·보강 완료, M2 audio 대기 (2026-11-07)** — 코드 PR "[tts-host] M2 code". **음성(mp3)은 아직 없음**: Colab(T4 GPU) 실행은 사람이 해야 한다.
음성 PR "[tts-host] M2 audio"는 아래 "운영자 절차"로 zip을 반입한 뒤 따로 올린다. 브랜치는 main `8e8fd59` 기준으로 rebase했다.

## 완료한 것

- `app/tts/assets.py`: `text_hash`(sha1(strip utf-8)), `cache_key`, `active_voice_id`, `tts_url`, `tts_status`
  (`tts_status`는 DB 없이 활성 manifest + 디스크 파일 + `questions.jsonl` pilot로 계산 → `/health`가 DB 장애와 섞이지 않음)
- `scripts/export_tts_jobs.py`: pilot 전부(Q000 포함) + 진행자 대사 4개 → `backend/static/tts/jobs.jsonl`. `--stale`(활성 voice와 해시·파일 비교), `--e2e`(IM2·IL 각 8개)
- `scripts/import_tts.py <zip|폴더> [--activate] [--no-db]`: manifest 필수 키·`settings_version` 재계산·파일 존재·mp3 길이(PyAV) 검사 →
  `{TTS_DIR}/{voice_id}/` 반입(기존 manifest와 병합, `--stale` 반입 지원) → `db.upsert_tts_asset` → `--activate` 시 `active_voice.json`.
  `e2e_answer`는 `backend/e2e_audio/{level}/{order:02d}.mp3`로도 복사(integrator `e2e_smoke`의 `{order:02d}.mp3` 후보와 일치)
- `app/tts/prepare.py`: tts_prepare 핸들러. attempt 불일치·preparing 아님 → 무시, 활성 voice 없음 → `NO_ACTIVE_VOICE`,
  항목별 `TTS_ASSET_MISSING` / `TTS_HASH_MISMATCH`(활성 manifest에 같은 id가 다른 해시로 있을 때) / `TTS_FILE_MISSING`,
  하나라도 있으면 `fail_prepare(전체 목록)`, 없으면 `complete_prepare`. 취소 플래그면 저장 안 함. 자동 재생성·대체 없음
- `colab/omnivoice_tts.ipynb`(구조 유지): 출력 `{kind}/{ref_id}.mp3`, manifest에 `model_revision`(HF 조회, 실패 시 unknown)·`settings_version`,
  zip 최상위 폴더 = `settings_version`(= voice_id), 11번 셀 e2e 답변용 **다른 목소리**(선택), 실존 인물 음성 복제 금지 문구 유지
- `frontend/src/features/host/useTtsPlayer.ts`: 공유 AudioContext + AnalyserNode(fftSize 512), `unlock/play/stop/isPlaying/getAnalyser`,
  `NotAllowedError → 'blocked'`, 로드 실패 → `'error'`, `crossOrigin="anonymous"`, **speechSynthesis 없음**
- `frontend/src/features/host/Host.tsx`: 오리지널 SVG 캐릭터 "린"(둥근 도형). idle 숨쉬기 / speaking 음량 반응(지수 평활 0.25) /
  listening 귀 기울임 + REC / processing 점 3개. `prefers-reduced-motion`이면 입 모양만. `Host.demo.tsx` 미리보기
- `requirements/tts-host.txt`: av, numpy
- pytest `tests/test_tts_pipeline.py` 10개, `npm run build` 통과(타입 오류 0), oxlint 경고 0

## 실행 방법 — 운영자용 음성 생성·재생성 절차

```bash
cd backend
python -m scripts.export_tts_jobs --e2e          # 처음: pilot 전부 + 대사 + e2e 답변 → static/tts/jobs.jsonl
python -m scripts.export_tts_jobs --stale        # 문장 변경·문항 추가 후: 바뀐/없는 항목만
```
1. colab.research.google.com → `colab/omnivoice_tts.ipynb` 업로드 → 런타임 T4 GPU
2. 셀 순서대로 실행. 4번 셀에서 `jobs.jsonl` 업로드. 6번 기준 음성이 마음에 들 때까지 3번 `SEED`·`INSTRUCT` 조정
   (재생성 때는 같은 값 + 저장해 둔 `host_voice.pt` 사용 → 같은 voice_id)
3. e2e 항목이 있으면 11번 셀(다른 목소리)까지 실행 → 마지막 셀에서 `tts_mp3.zip`, `host_voice.pt` 내려받기
4. 반입(압축 직접 풀지 않음):
   ```bash
   python -m scripts.import_tts tts_mp3.zip --activate      # DB가 떠 있어야 함(data-layer). DB 없이 파일만: --no-db
   ```
5. `backend/static/tts/{voice_id}/`, `active_voice.json`, `backend/e2e_audio/` 커밋 → PR "[tts-host] M2 audio"
   (`jobs.jsonl`은 생성물이라 커밋해도 되고 안 해도 됨. 64kbps mono 기준 전체 수 MB 예상)

## 공개 함수·화면 (contracts.yaml과 동일)

- `app.tts`: `HOST_LINES`, `text_hash`, `active_voice_id`, `tts_url`, `tts_status`, `prepare.handle` (+ 내부 보조 `cache_key`, `asset_rel_path`, `split_item_id`, `load_manifest`, `manifest_index`, `pilot_questions`)
- frontend: `Host({state, className?})`, `useTtsPlayer()` — 화면은 이 두 개만 import

```tsx
import { Host, type HostState } from '@/features/host/Host';   // 경로 별칭이 없으면 상대 경로
import { useTtsPlayer } from '@/features/host/useTtsPlayer';

const player = useTtsPlayer();
const [host, setHost] = useState<HostState>('idle');
async function playQuestion(url: string) {
  await player.unlock();                 // 첫 사용자 클릭 핸들러 안에서
  setHost('speaking');
  const r = await player.play(url);      // 'ended' | 'blocked' | 'error'
  setHost('idle');
  if (r === 'blocked') showTapToListen(); // 사용자 동작으로 play 재시도
  if (r === 'error') showRetry();         // 같은 문항 재시도(다음 문항으로 넘기지 않음)
}
<Host state={host} className="w-48" />
```

## 측정값

| 항목 | 값 |
|---|---|
| instruct / seed / speed | (Colab 실행 후 기록) |
| voice_id | (Colab 실행 후 기록) |
| 생성 개수 | jobs: question 13 + host 4 + e2e 16 = 33 (corpus M1 기준. M2 병합 후 pilot 222 + 4 + 16) |
| 총 길이·용량 | (반입 후 `import_tts` 요약값 기록) |

## 알려진 문제

- 음성 미생성이므로 `tts_status().missing_pilot`은 아직 전 문항. done_when(누락 0)은 audio PR에서 충족한다.
- DB 연동 local_checks(preparing 세션 → `--types tts_prepare --once` → ready, mp3 삭제 → `TTS_FILE_MISSING`)는
  data-layer 병합 후 실행. 핸들러 흐름은 가짜 db pytest로 확인했다.
- `TTS_HASH_MISMATCH`는 활성 manifest 기준으로 판별한다(DB에는 정확한 해시 조회 함수만 있어서).

## 다른 에이전트에게 요청

- frontend: `Host.demo.tsx`를 개발용 라우트(`/__host`)에 연결할지 결정해 주세요.
- integrator: e2e 음성은 `backend/e2e_audio/{IM2|IL}/{01..08}.mp3`(슬롯 순서)로 생성됩니다.


## 2026-11-07 C 후속 검증 (OpenAI Codex)

사용자가 C 작업 진행과 코드 우선/Colab 나중을 선택했다. 기존 Claude 구현과 출처를 보존하고 경로 검사를 보강했다. ZIP의 Windows drive/root/backslash·상위 경로, item ID의 경로 구분자를 거부하고 DB 파일 경로가 TTS_DIR 밖이면 준비 실패로 처리한다. 활성 voice_id는 계약의 sha1[:10] 형식만 허용한다.

- `cd backend` 후 활성화한 Python으로 `python -m pytest tests/test_tts_pipeline.py -q`: **19 passed / 1.01초**.
- 실제 PostgreSQL 임시 DB + 실제 반입/MP3 디코드/작업 claim/prepare: 합성 파일12개 등록 → ready → host/next 파일 제거 → prepare_failed/TTS_FILE_MISSING → 파일 복구·retry attempt2 → ready. 같은8문항 보존, attempt1 무시, AI요청0, 임시 DB/파일 정리. worker CLI 통합이나 실제 OmniVoice 음질 검증으로 표시하지 않는다.
- `cd frontend` 후 `npm ci`, `npm run build`: 성공. `npx oxlint src/features/host`: 경고0. 전체 lint의18개 경고는 main의 API stub 경로이며 tts-host 소유 밖이라 수정하지 않았다.
- 노트북 코드 셀11개 Python 구문 검사 통과. Colab/GPU 실행은 하지 않았다.
- `python -m scripts.export_tts_jobs --e2e`: 현재 corpus M2에서 **242개 = 질문222 + 대사4 + e2e16**, 총38,342자. 작업 파일은 `backend/static/tts/jobs.jsonl`에 커밋한다.

### 다음 Colab 작업

저장소의 `colab/omnivoice_tts.ipynb`와 위 `jobs.jsonl`을 사용한다. 기존 운영자 절차대로 T4에서 진행자 기준 음성을 정하고, e2e 답변은 별도 합성 목소리로 생성한다. ZIP과 host_voice.pt는 로컬에 내려받는다. ZIP은 backend 기준 상대 경로를 사용해 `python -m scripts.import_tts <상대경로/tts_mp3.zip> --activate`로 반입한다. 코드 테스트용 tone MP3를 실제 진행자 자산으로 활성화하지 않는다.

실제 instruct/seed/speed/voice_id·길이·용량은 **미정/미측정**이다. 현재 실제 자산 누락은 남아 있으므로 missing_pilot=[]/M2 audio 완료/제품 완주를 주장하지 않는다. 전체 M2 후 M3 통합과 별도 대화의 독립 reviewer 검토가 필요하다.
