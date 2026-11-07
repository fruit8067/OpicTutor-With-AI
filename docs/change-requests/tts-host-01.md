# CR tts-host-01 — TTS 음성의 텍스트 버전 보존

AI-assisted (OpenAI Codex).

- 바꿀 항목: contracts data_files.audio_files.tts_url 및 tts_manifest 로컬 반입 메타데이터.
- 현재 → 제안: 같은 voice/kind/ref 단일 mp3 → 새 반입은 voice/kind/ref/text_sha1.mp3. 로컬 manifest item에 file_path를 기록한다. Colab ZIP 입력과 기존 평면 경로는 계속 읽는다.
- 이유: 원래 문항/음성 경로를 참조하는 세션이 있는 상태에서 문장 변경 음성을 같은 voice로 반입하면 기존 파일이 덮어써진다. 실패 회귀에서 old file SHA256이 바뀜을 재현했다. DB cache_key는 해시별로 다르지만 파일 경로는 같았다.
- 영향: tts-host import/status/stale. session-api/frontend는 DB file_path의 불투명 URL을 그대로 사용하므로 공개 함수·HTTP·DB 변경 없음.
- 막힘 여부: 새 경로 구현은 계약 승인 전 대기. 기존 음성/평면 경로는 보존하고 DB reset/파일 삭제 없이 점진 전환한다.
- 승인 후: 변경 문항 재반입 뒤 기존 파일 보존, 레거시 manifest·같은 폴더 재등록·stale 및 실제 DB 세션 URL을 검증한다.

## 처리 결과

PR #30/main a37f85e로 승인된 계약 v8을 따른다. 새 반입만 해시별 경로/file_path로 저장하고 기존 평면 경로·Colab ZIP·기존 세션 등록본은 보존한다. 공개 함수·HTTP·DB 컬럼 변경 없음.
