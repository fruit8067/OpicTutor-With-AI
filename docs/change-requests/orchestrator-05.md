# CR tts-host-01 승인 — 기존 세션 음성 보존

AI-assisted (OpenAI Codex).

tts-host가 재현한 같은 voice/ref의 문장 변경 반입은 이전 세션이 참조하는 mp3를 덮어썼다. REQUIREMENTS F0/F6·FLOWCHART의 고정 세트/문항 음성 대응을 지키기 위해 승인한다.

계약 v8은 새 반입의 텍스트 해시별 파일 경로와 로컬 manifest의 상대 file_path만 추가한다. Colab ZIP, 기존 평면 경로, HTTP 형식 v3, DB 컬럼·공개 함수·평가 원문은 유지한다. 새 구현은 이 계약의 main 병합 후 적용한다.

이행은 기존 파일 삭제·DB reset 없이 진행한다. 이전 세션 URL/평면 경로 보존, 같은 폴더 재등록, 변경 문장 재반입, stale·준비 상태 검증을 요구한다. 계약 병합은 C 기능 검증 완료를 뜻하지 않는다.
