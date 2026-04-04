# Changelog

## 2026-04-04 16:30 UTC

- Implemented Step A learning foundation with backend schema, API, and web UI integration.
- Added `student` role support throughout auth/admin flows and bootstrap role validation.
- Added learning domain persistence: paths, modules, lessons, and learning-path file/tag scoping tables.
- Added learning CRUD endpoints with permission enforcement for admin/user/student and global vs user-scoped paths.
- Added module and lesson ordering support through explicit reorder endpoints.
- Added chat foundation fields for future learning chats (`chat_type`, `learning_path_id`).
- Enforced student restrictions for normal chat and GPT usage on both backend and frontend.
- Added a new Learning navigation entry and a learning-path management page in the web UI.
- Added focused tests for student restriction API behavior and learning-path endpoint access.

## 2026-04-04 14:45 UTC

- Implemented Step 13 library ownership and visibility rules across ingestion, retrieval, API, and web UI.
- Added file metadata fields `is_global` and `source_origin` plus Alembic migration/backfill logic.
- Updated ingestion classification so direct `data/` files are global system files and admin uploads are global admin-managed files.
- Enforced server-side protections so non-admin users cannot disable global files, delete global files, or delete files owned by other users.
- Reworked default file enablement to be owner-aware: owner-enabled by default, other users disabled by default, and global files enabled by default.
- Updated retrieval filtering to apply ownership defaults and user settings before selecting usable chunks.
- Added library API support for `include_other_users` and expanded library responses with ownership/global metadata and permission flags.
- Added a library-page bottom switch to show or hide other users' files (default off), and ownership/global badges in the table rows.
- Expanded tests and docs for ownership behavior, permission enforcement, retrieval defaults, and library visibility toggling.

## 2026-04-01 18:45 UTC

- Implemented Step 12 user-owned GPTs with isolated personalization, retrieval settings, file and tag overrides, instructions, and assistant mode.
- Added Alembic-backed GPT persistence with `gpts`, `gpt_chats`, and GPT-owned chat message tracking.
- Added GPT CRUD, preview, persistent GPT chat, clear, and download API endpoints.
- Extended retrieval and prompt building so GPT chats ignore user defaults and inject GPT instructions into the prompt flow.
- Added sidebar GPT navigation, full-width GPT editor and preview UX, persistent GPT chat routing, and locked GPT assistant-mode display in the web UI.
- Expanded tests, docs, and docker validation for the Step 12 rollout.

## 2026-04-01 01:00 UTC

- Implemented Step 11 `thinking` mode with a three-stage planning, drafting, and refining pipeline in the retriever service.
- Added dedicated thinking prompt templates plus reusable prompt-builder support for passing prior-step outputs between stages.
- Extended assistant-mode settings and frontend mode selectors so `thinking` is available anywhere `simple` and `refine` are shown.
- Added graceful fallback from thinking mode to the simple pipeline when a thinking stage fails.
- Expanded tests and documentation for prompt composition, API exposure, assistant modes, and Step 11 validation guidance.

## 2026-04-01 00:00 UTC

- Implemented Step 9 user-scoped retrieval filtering with global and chat-level file plus tag settings.
- Added new Alembic schema for `chat_file_settings`, `user_tag_settings`, and `chat_tag_settings`.
- Reworked retrieval candidate filtering so file and tag precedence is enforced before score thresholding and response assembly.
- Added authenticated filter endpoints for user and chat scope and expanded the frontend with global filter management plus chat-specific filter dialogs.
- Added Step 9 tests for retrieval precedence, locking rules, and API coverage, and documented the filtering model across API, frontend, and testing docs.

## 2026-03-29 00:00 UTC

- Added a full Step 1 local RAG scaffold with dedicated `embedder` and `retriever` services.
- Added shared configuration, logging, retry, PostgreSQL schema, and Qdrant integration modules.
- Implemented polling-based file ingestion for `.md` and `.txt` files with normalization, chunking, hashing, tag loading, embedding, and delete handling.
- Implemented CLI retrieval flow with prompt assembly, chat history persistence, retrieval score filtering, and retrieval evidence logging.
- Added Dockerfiles, Compose service wiring, `.env.example`, and starter `data/tags.json`.
- Added Step 1 documentation for architecture, embedder behavior, retriever behavior, database schema, and setup.

## 2026-03-29 01:00 UTC

- Reworked the embedder into a processor-based pipeline for `.txt`, `.md`, `.html`, `.htm`, `.pdf`, and `.epub`.
- Added shared normalization, extraction quality validation, richer semantic chunk metadata, and reindex triggers tied to processing configuration.
- Added PDF page-aware extraction, OCR fallback configuration, EPUB spine-order parsing, HTML cleanup, and repeated chrome reduction.
- Extended PostgreSQL and Qdrant metadata payloads for Step 2 source transparency and indexing provenance.
- Updated the retriever CLI to print source metadata below each answer and expanded retrieval logging accordingly.
- Added Step 2 docs for parsers, OCR, metadata, testing, and refreshed the existing setup, architecture, embedder, retriever, and database docs.
- Added focused pytest coverage and smoke-test guidance for the Step 2 ingestion and source-formatting paths.

## 2026-03-29 02:00 UTC

- Refactored the retriever into reusable chat, repository, schema, and service layers and added a FastAPI entry point for Step 3.
- Added persisted chat metadata, chat-scoped message loading, assistant source lookups, and API responses tailored for the web UI.
- Added a React + Vite frontend with sidebar chat navigation, optimistic message sending, loading/error handling, and per-answer Sources panels.
- Updated Docker Compose, environment examples, and service images to run the web UI and retriever API together.
- Added Step 3 documentation for the frontend, API, chat model, setup, testing, and updated database/retriever notes.

## 2026-03-29 03:00 UTC

- Added Step 4 library management with backend file listing, upload, enable or disable, and full deletion endpoints.
- Extended file metadata persistence for extension, size, chunk count, embedded state, enabled state, and default-tag handling.
- Added synchronous upload processing into the shared `data/` directory plus `tags.json` persistence and duplicate upload guards.
- Updated retrieval to ignore disabled files even while their vectors remain indexed.
- Added chat rename and delete backend actions with message and retrieval-log cleanup.
- Reworked the web UI into routed chat and library views with sidebar `Library` navigation, upload dialogs, file actions, and chat hover menus.
- Added safe assistant markdown rendering with `react-markdown`, GitHub-flavored markdown support, and sanitization.
- Added Step 4 API and backend tests, refreshed frontend build validation, and documented library, upload, chat-management, frontend, API, and testing behavior.

## 2026-03-30 00:00 UTC

- Implemented Step 5 attachment handling across the web UI, retriever API, prompt builder, and embedder service.
- Added ephemeral attachment extraction for `.csv` plus OCR-backed image attachments without persisting file content or vectors.
- Added message attachment metadata persistence and expanded message API payloads with `has_attachments`, `attachments`, and `attachments_used`.
- Introduced Alembic migrations and switched database initialization to migration-driven schema upgrades.
- Reworked the web UI toward the Step 5 reference structure with attachment previews and disabled placeholder controls for unimplemented areas.
- Updated environment defaults, testing guidance, API/frontend docs, and repository ignore rules for a cleaner project root.

## 2026-03-30 01:00 UTC

- Implemented Step 7 as a full web UI restyle pass against the reference UI without changing product scope.
- Reworked the shared visual system with centralized color, radius, border, shadow, and transition tokens.
- Restyled the fixed shell, sidebar, chat layout, composer, message rendering, source popovers, library sections, dialogs, and preferences modal for closer reference parity.
- Refined the preferences architecture into a wide tabbed modal and aligned library and archive surfaces with the same design language.
- Updated frontend, testing, and new design-system documentation for the Step 7 styling model and verification workflow.
