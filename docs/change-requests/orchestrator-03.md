# CR data-layer-01 승인 기록

2026-11-07 KST. orchestrator는 data-layer의 nullable 평가 메타데이터 선언 정리를 승인한다. 요청은 agent/data-layer의 docs/change-requests/data-layer-01.md이며 기존 API/DB/비 IM 결과 동작과 공개 타입의 불일치를 해소한다.

contracts v6는 finish_evaluation의 im_rubric_version와 corpus_version 인자를 str | None으로 선언한다. API 스키마·DB 컬럼·고정 시스템 프롬프트·등급 판정·상태 전이·검증/병합 조건은 바꾸지 않는다. main 병합 시 정본이 되고 그 뒤 data-layer가 자기 함수의 타입 주석을 반영한다. C 구현은 추가하지 않는다.
