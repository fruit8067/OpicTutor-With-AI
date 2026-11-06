# CR orchestrator-04 — Pickle 연결·large 3072 임베딩

2026-11-07 KST. 사용자 명시 요청에 따라 orchestrator가 승인한다. main 병합 전까지 제안이며 각 소유 역할은 병합 후 rebase해 구현한다.

- 현재 → 제안: 빈 LLM URL/model → `https://llm.pcl.kr/v1` / `pickle-general`. `LLM_API_KEY` 우선, 비어 있으면 `os.getenv("PICKLE_API_KEY")`. OpenAI 키로 LLM 인증을 대체하지 않는다. 채점 temperature=0·고정 프롬프트는 유지한다.
- 임베딩 기본값: `text-embedding-3-small`/1536 → `text-embedding-3-large`/3072. EMBED_API_KEY는 별도다. VECTOR(3072) full precision과 exact cosine 검색을 사용한다. pgvector HNSW vector 인덱스의 2000차원 제한을 차원 축소·반정밀도로 우회하지 않는다.
- 기존 DB: 전진 마이그레이션으로 HNSW 제거, 1536 벡터는 3072로 패딩하지 않는다. 원문·메타데이터·세션/평가를 보존하고 파생 임베딩만 무효화한다. 현재 확인한 로컬 DB는 rag_docs 0행이다. 새 차원 DB에 재실행해 새 벡터를 지우지 않아야 한다.
- 재사용 규칙: text/corpus_version뿐 아니라 모델·차원·endpoint의 해시 프로필이 같을 때만 기존 벡터 재사용. 프로필은 rag_docs.metadata 내부에 저장(키/인증 정보 저장 금지). 검색도 현재 프로필만 사용하며 다른 모델 벡터를 섞지 않는다. direct evidence 조회 정책은 유지한다.
- ingest는 dry-run에서 재임베딩 개수·토큰·표준 OpenAI 예상비용을 출력한다. 실제 키 호출 전 약 $5 예산 안인지 확인하며 중단 후 배치 재개와 프로필 전환을 검증한다. 임베딩 모델 변경만으로 채점 정확도 향상을 주장하지 않는다.
- 영향: bootstrap(config/.env.example/API 설정 문서), data-layer(migrations/ingest/search/검증), grader(키 별칭), orchestrator(검증 도구/증거). 공개 함수·HTTP 형식·평가 판정/원문·C 범위·병합 게이트는 유지한다.

근거: [OpenAI embeddings](https://developers.openai.com/api/docs/guides/embeddings), [large 모델](https://developers.openai.com/api/docs/models/text-embedding-3-large), [pgvector](https://github.com/pgvector/pgvector#exact-search).

AI-assisted (OpenAI Codex).
