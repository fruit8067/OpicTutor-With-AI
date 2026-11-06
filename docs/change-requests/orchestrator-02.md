# CR session-api-01 승인 기록

2026-11-07 KST. orchestrator는 session-api가 제안한 생성 재전송 DB 조회 함수를 승인한다. 사용자 목표의 A/B 코어 신뢰성 및 요구사항/API/flowchart 준수 범위다. main 병합 시 contracts v5가 정본이 되며 그 전에는 제안이다.

요청: agent/session-api의 `docs/change-requests/session-api-01.md`. 새 함수는 `get_session_id_by_request_id(client_request_id: str) -> UUID | None`이다. 외부 HTTP API 필드·도메인 DB 컬럼·평가 원문을 바꾸지 않는다. API에서 SQL이나 임시 캐시를 사용하지 않는다.

data-layer가 조회·기존 원자적 생성 멱등성을 구현하고 session-api가 저장 세션 우선 조회를 적용한다. 같은 키의 코퍼스 변경 후 재전송, 새 키의 데이터 오류, 동시 생성 중복 방지와 작업 중복 부재를 검증한다. 빈 문자열도 명세의 str 키로 취급할 때 None과 혼동하지 않아야 한다.

다른 역할의 검증/병합 게이트는 그대로 유지한다. C를 새로 구현하지 않는다. 이 CR이 실제 서비스·M1/M2 완료를 의미하지 않는다.
