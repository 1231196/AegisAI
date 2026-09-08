"""Runtime settings for backend-ai (Epic 3 ingestion + Epic 4 retrieval)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"

    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_collection: str = "documents"

    # jina-embeddings-v3: strong multilingual retrieval quality,
    # supports Matryoshka truncation (via ``embedding_dim`` below) so
    # the vector size can be reduced later without re-embedding the
    # model architecture itself. 1024 is the model's native size.
    embedding_model: str = "jinaai/jina-embeddings-v3"
    embedding_dim: int = 1024

    # Chunking (US-010): ~1200-1800 tokens/chunk with 15-25% overlap is
    # the sweet spot for retrieval quality vs. chunk count; 1500/300
    # (20% overlap) is the concrete pick.
    chunk_size_tokens: int = 1500
    chunk_overlap_tokens: int = 300

    # OCR fallback (US-009) for scanned/image PDF pages that pymupdf
    # can't extract native text from.
    ocr_lang: str = "en"

    backend_api_url: str = "http://backend-api:8000"
    # Shared secret for backend-ai <-> backend-api calls. Must match
    # backend-api's INTERNAL_SERVICE_TOKEN exactly (see docker-compose.yml).
    internal_service_token: str = "dev-only-internal-token-change-me"

    # --- Epic 4: Retrieval ------------------------------------------------
    # Sparse (BM25-style) embeddings for hybrid search (US-016), paired
    # with a named "sparse" vector on the same Qdrant collection as the
    # dense embeddings. fastembed's ONNX runtime — no torch needed.
    sparse_model: str = "Qdrant/bm25"

    # Multilingual cross-encoder reranker (US-017). Deliberately NOT an
    # English-only reranker (e.g. ms-marco-MiniLM) — that would undercut
    # the multilingual embeddings chosen for search quality. Loads via
    # plain sentence-transformers.CrossEncoder, no trust_remote_code.
    reranker_model: str = "BAAI/bge-reranker-v2-m3"

    # Initial candidate pool pulled from Qdrant before reranking — your
    # "top 50-100" recommendation; 100 is the concrete pick.
    retrieval_initial_k: int = 100
    # Final context size after rerank + dedup (US-018), configurable
    # per-request within [retrieval_min_final_k, retrieval_max_final_k].
    retrieval_default_final_k: int = 10
    retrieval_min_final_k: int = 5
    retrieval_max_final_k: int = 20
    # Candidates whose dense-vector cosine similarity to an already-
    # selected chunk exceeds this are treated as redundant and skipped.
    retrieval_dedup_threshold: float = 0.92

    # --- Epic 5: Chat -------------------------------------------------
    # Read from the GOOGLE_API_KEY env var by pydantic-settings' default
    # field-name-matches-env-var behaviour (same as every other setting
    # here) — set via a root .env file, never committed.
    google_api_key: str = ""
    chat_model: str = "gemini-2.5-flash"
    # How many of a conversation's most recent messages backend-api
    # sends as history context for a new reply.
    chat_history_max_messages: int = 10


settings = Settings()
