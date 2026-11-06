# CR frontend-01

> AI-assisted: written with help from Claude (Anthropic).

- 바꿀 항목: `frontend/src/api/types.ts`(bootstrap 소유)의 `EvaluationResult.tier`
- 현재 → 제안: `tier: "{name: string; color: string}" | null;` (문자열 리터럴 타입) → `tier: Tier | null;` 와 `export interface Tier { name: string; color: string }`
- 이유: 타입 생성기가 객체 타입을 문자열로 출력했다. 서버(`app/schemas/api.py Tier`)는 객체를 보내므로 지금 타입으로는 `r.tier.color`를 쓸 수 없다.
- 영향 받는 에이전트: frontend(결과 화면), bootstrap(types.ts 생성)
- 막힘 여부: 우회 가능 — `pages/Result.tsx`의 `tierOf()`에서 `unknown` 경유로 객체로 해석한다(`// CR frontend-01` 주석). 수정되면 그 함수만 지우면 된다.
