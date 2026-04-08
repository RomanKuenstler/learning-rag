# Setup

## Prerequisites

- Docker and Docker Compose
- A local OpenAI-compatible chat model endpoint
- A local OpenAI-compatible embedding endpoint

The repository defaults point to Docker Model Runner on `http://host.docker.internal:12434/v1`. If your local model runner uses a different endpoint, update `.env`.

## Run Step 3

1. Copy `.env.example` to `.env`.
2. Review the model endpoint and model-name settings.
3. Add `.md`, `.txt`, `.html`, `.htm`, `.pdf`, or `.epub` files to `data/`.
4. Optionally map tags in `data/tags.json`.
5. Start the full Step 3 stack:

```bash
docker compose up --build
```

6. Open:

- web UI: `http://localhost:5173`
- retriever API: `http://localhost:8000/docs`
- learning paths page: `http://localhost:5173/learning`
- courses page: `http://localhost:5173/courses`
- declared learning profile sections are available on the learning page (preferences, context, goals)

## Step A Learning Setup Notes

- Ensure `users.json` includes valid roles only: `admin`, `user`, `student`.
- Student accounts are intentionally restricted from normal chat and GPT flows.
- Learning-path authoring in the UI is available to `admin` and `user` roles.
- Declared learning profile editing is available to all authenticated roles, including `student`.
- Step B.1 diagnostics are available in the Learning `Preferences` flow.
- Course definitions are file-backed in `courses/` and are validated/bootstrapped at retriever startup.

## Optional CLI Retriever

The Step 2 CLI is still available for direct terminal testing:

```bash
docker compose --profile cli run --rm retriever
```

## Important Environment Variables

- `CHUNK_SIZE`
- `CHUNK_OVERLAP`
- `WATCH_INTERVAL`
- `RETRIEVAL_SCORE_THRESHOLD`
- `RETRIEVAL_MIN_RESULTS`
- `RETRIEVAL_MAX_RESULTS`
- `CHAT_HISTORY_LIMIT`
- `API_HOST`
- `API_PORT`
- `CORS_ALLOWED_ORIGINS`
- `VITE_API_BASE_URL`
- `QDRANT_COLLECTION`
- `EMBEDDING_MODEL`
- `EMBEDDING_BASE_URL`
- `LLM_MODEL`
- `LLM_BASE_URL`
- `ENABLE_OCR`
- `PDF_OCR_MODE`
- `PDF_MIN_EXTRACTED_CHARS`
- `PDF_MIN_AVG_CHARS_PER_PAGE`
- `PDF_ENABLE_COLUMN_DETECTION`
- `PDF_RENDER_SCALE`
- `OCR_LANGUAGE`
- `OCR_ENABLE_PREPROCESSING`
- `HTML_CLEANING_STRICT`
- `EPUB_SKIP_FRONT_MATTER`
- `EPUB_REMOVE_REPEATED_CHROME`
- `EPUB_FALLBACK_SCAN_ENABLED`
- `INDEX_SCHEMA_VERSION`
- `PROCESSOR_VERSION`
- `NORMALIZATION_VERSION`
- `EXTRACTION_STRATEGY_VERSION`
- `COURSES_DIR`

## Services

- `embedder`: watches `data/` and updates PostgreSQL + Qdrant
- `retriever-api`: exposes the FastAPI chat endpoints
- `webui`: runs the Vite React interface
- `postgres`: persists indexing and chat data
- `qdrant`: stores embedding vectors
