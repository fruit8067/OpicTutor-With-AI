# CR orchestrator-01 — 감사 후 계약·운영 절차 복구

## 상태와 승인

2026-11-06 KST 접수. 사용자의 “해결하는 것 까지가 목표” 지시에 따라 orchestrator가 아래 수정 범위를 승인한다. 과거 v4 제안이나 위반에 대한 소급 승인이 아니다. 이 CR과 수정은 PR로 검증하고 main에 반영될 때만 정본이 된다. M0/M1/M2/M3의 병합·실행 조건은 유지한다.

## 바꿀 항목 / 현재 → 제안

- contracts v3 → v4: 사용자 요청대로 LLM URL/모델 기본값을 비우고 Pickle 값을 명시하며, 키는 os.getenv('LLM_API_KEY')로 읽는다. backend/.env는 override=False로 로드해 프로세스 환경이 우선한다. 임베딩 설정은 유지한다.
- app.grading.tier_of: str → dict 선언을 str | None → dict | None으로 정리한다. grader YAML의 기존 null 처리 요구와 API의 nullable tier를 일치시킨다.
- TTS text_hash: 간략한 SHA1 표현을 Python text.strip().encode('utf-8')의 SHA1으로 명확히 한다. 기존 tts-host 상세 지시와 같다.
- provider 요청 예산: 최초 요청+2 재시도, 총 3회는 실제 HTTP 평가 요청 기준이다. structured-output 미지원 협상과 JSON 대체 요청도 각각 기록·예산에 포함한다. 논리적 평가 시도와 실제 요청 수를 혼동하지 않는다. 고정 시스템 프롬프트·등급 기준·API·도메인 DB 스키마는 바꾸지 않는다.
- attribution: 예시의 Claude 고정 문구를 실제 사용한 도구·제공자를 기록하도록 바꾼다. 기존 원저자의 Claude 출처는 보존한다.
- HANDOFF 병합 체크리스트: 병합 전에 검증 가능한 local_checks/구현 조건과 병합 후 done_when을 구분해 순환 조건을 해소한다. 미실행 검증은 실패/대기로 명시하며 조건을 면제하지 않는다.

## 이유와 영향

감사 I-03/I-05/I-06 및 사용자 Pickle 요청에 필요한 선언 정리다. bootstrap, grader, data-layer, tts-host, integrator와 운영 문서에 영향이 있다. 평가 원문은 수정하지 않는다. 미관찰·결측 검증, 버전 필터, 408 분류는 원래 계약을 이행하는 결함 수정으로 처리한다.

## 운영 복구

.gitattributes, 신뢰한 main 계약/검사기를 사용하는 ownership workflow를 준비한다. GitHub rebase-only·main 보호/필수 ownership을 적용하고 검증한다. 기존 PR 원본 SHA는 보존하고 M0 기준 역할별 증분으로 재구성한다. 지정된 병합 순서·외부 서비스·실제 음성 검증이 미완료인 PR은 Draft를 유지한다.

## 막힘 여부

코드/문서 수정은 가능. 실제 Pickle·임베딩 검증은 URL/모델/키가 필요하며, C·실제 마이크 완주는 별도 작업 범위/자료가 필요하다. 이러한 조건을 완료로 위장하지 않는다.
