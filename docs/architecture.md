# Architecture

Step 2 delivers a local RAG pipeline with four runtime components:

- `embedder`: polls `data/`, selects a processor per file type, extracts normalized semantic blocks, chunks them, creates embeddings, and synchronizes Qdrant plus PostgreSQL state
- `retriever`: CLI chat loop that embeds user questions, retrieves scored chunks, builds the RAG prompt, calls the local chat model, stores history plus retrieval evidence, and prints the sources used
- `postgres`: stores file metadata, chunks, chat messages, and retrieval logs
- `qdrant`: stores chunk embeddings and retrieval payload metadata

The system is intentionally split into small modules so later UI, multi-user, and streaming work can extend the current services instead of replacing them.

## Data Flow

1. The embedder scans `data/` on an interval.
2. The watcher triggers reprocessing when file content changes or when chunking/schema/processor versions change.
3. The processor registry routes each supported file to a specialized processor.
4. The processor extracts text, evaluates extraction quality, applies shared normalization, and emits semantic blocks plus metadata.
5. The chunker performs semantic-first chunking followed by size-based splitting with metadata carried forward.
6. Chunk vectors and metadata are written to Qdrant, while file and chunk state are written to PostgreSQL.
7. Files with no useful extracted text are stored in PostgreSQL with failure metadata and are not indexed into Qdrant.
8. The retriever embeds each user query and performs a cosine-similarity search in Qdrant.
9. Chunks that meet the configured threshold are inserted into the RAG context and also rendered back to the CLI source section.
10. The assistant response, chat history, and retrieval evidence are persisted in PostgreSQL.

## Library Ownership Model

Library files persist ownership and origin metadata in PostgreSQL:

- `uploaded_by_user_id`: uploader/owner (nullable for system files)
- `is_global`: global availability marker
- `source_origin`: `system_data`, `admin_upload`, `user_upload`, or fallback `unknown`

Effective user enablement is resolved server-side:

- global files default to enabled for all users
- user-owned files default to enabled for the owner
- user-owned files default to disabled for non-owners

Permission enforcement is also server-side:

- non-admin users cannot disable global files
- non-admin users cannot delete global files
- non-admin users cannot delete files owned by other users
