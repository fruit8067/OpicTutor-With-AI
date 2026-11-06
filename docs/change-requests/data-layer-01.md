# CR data-layer-01 — 평가 저장의 nullable 메타데이터 선언

2026-11-07 KST 승인·반영. PR #16/main a136406/contracts v6 승인 후 타입 주석을 반영했다. A/B 코어 조합에서 IL 결과의 im_rubric_version=None을 정상 저장하는 동작을 확인했다. API와 evaluations DDL은 해당 필드를 nullable로 정의하지만 이전 app.db.finish_evaluation 함수 선언은 str이었다. 근거가 없을 때 corpus_version도 DB상 nullable인데 이전 선언은 str이었다.

현재 → 제안: finish_evaluation의 im_rubric_version 및 corpus_version 인자를 `str | None`으로 정리한다. 기존 런타임/DB/API의 nullable 동작을 정확히 표현하며 새 컬럼·출력·평가 기준을 도입하지 않는다. 다른 함수·필드·필수 검증 조건은 유지한다.

영향: data-layer 공개 타입 선언, grader의 기존 None 전달, orchestrator의 계약/검토. 평가 원문은 유지한다. 승인 전에는 함수 선언을 바꾸지 않는다.

검증: 실제 IL 저장/결과 재조회와 insufficient_evidence 메타데이터가 도메인 DB와 일치하는지 확인한다. DB에 새 값이나 사용자 등급을 조용히 보정하지 않는다.
