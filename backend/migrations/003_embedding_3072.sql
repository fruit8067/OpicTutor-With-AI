-- AI-assisted (OpenAI Codex). OWNER: data-layer. CR orchestrator-04 / contract v7.
-- Preserve source documents and domain data. Old derived vectors cannot be reused.
DROP INDEX IF EXISTS rag_docs_embedding;
DO $$
BEGIN
  IF (SELECT format_type(atttypid, atttypmod) FROM pg_attribute
      WHERE attrelid='rag_docs'::regclass AND attname='embedding') <> 'vector(3072)' THEN
    ALTER TABLE rag_docs ALTER COLUMN embedding TYPE vector(3072) USING NULL::vector(3072);
    UPDATE rag_docs SET metadata=metadata - '_embedding_profile';
  END IF;
END $$;
