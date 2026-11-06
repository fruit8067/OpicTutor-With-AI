# CR session-api-01 — 생성 재전송은 저장 세션을 우선 조회

## 상태

2026-11-07 KST 제안. A/B 코어를 요구사항·flowchart 기준으로 심화 검증하며 발견했다. 아직 정본 반영 전이며 API 구현은 계약 승인 후 변경한다.

## 바꿀 항목

contracts.module_interfaces.app.db에 `get_session_id_by_request_id(client_request_id: str) -> UUID | None`을 추가한다. 기존 함수와 HTTP 요청/응답 형식은 유지한다.

## 현재 → 제안

현재 S1은 같은 client_request_id의 재전송도 출제 원본을 먼저 읽는다. 생성 이후 시나리오 제거·코퍼스 오류가 발생하면 이미 확정한 세션이 있어도 SCENARIO_UNAVAILABLE로 실패한다. 새 read 함수로 저장 세션 ID를 먼저 조회해 기존 세션이면 200으로 반환하고 출제·교체·작업 등록을 다시 수행하지 않는다. 새 요청의 경쟁 조건은 기존 create_session의 advisory lock/unique key가 계속 보장한다.

## 근거와 영향

REQUIREMENTS_v2 F0 및 §7은 진행 중 세트가 원본 변경에 영향을 받지 않도록 요구한다. API_SPEC은 세션 client_request_id 재전송에 같은 세션을 반환하도록 한다. data-layer와 session-api가 영향을 받으며 API 필드·스키마·DB 컬럼·고정 평가 원문은 변경하지 않는다.

## 검증

첫 세션 생성 후 출제 함수가 SCENARIO_UNAVAILABLE를 내도록 바꿔도 같은 요청 키의 재전송은 200/같은 session_id여야 한다. 새 요청 키는 계속 데이터 오류를 반환해야 한다. 다른 세션의 취소나 준비 작업을 중복 생성하면 안 된다.

## 막힘 여부

서명 추가가 필요하므로 정식 계약 승인 대기다. API에서 직접 SQL을 쓰거나 메모리 캐시로 저장 세션을 대신하지 않는다.
