# Changelog

## 2026-04-08 10:30 UTC

- Implemented the first real KSA assessment system end-to-end (definition, flow, scoring, persistence, and chart data integration).
- Added KSA persistence tables and migration:
  - `user_ksa_profiles`
  - `user_ksa_assessment_attempts`
- Added new KSA assessment APIs:
  - `GET /api/ksa/assessment/definition`
  - `POST /api/ksa/assessment/attempts`
  - `GET /api/ksa/assessment/attempts/latest`
  - `GET /api/ksa/assessment/attempts/{attempt_id}`
  - `PUT /api/ksa/assessment/attempts/{attempt_id}/answers`
  - `POST /api/ksa/assessment/attempts/{attempt_id}/complete`
- Implemented deterministic 4-phase assessment logic with authoritative question banks and scoring:
  - sieve-triggered topic selection
  - knowledge `FS = S * V` multiplier scoring with uncharted status handling
  - skill scenario mapping (`A -> level 1`, `B -> level 3`)
  - ability weighted capacity scoring (`correctness*0.7 + time_bonus*0.3`) and derived `learning_speed_multiplier`
- Wired web UI to run the full assessment dialog flow and refresh persisted KSA profile on completion.
- Updated KSA chart header to use one global Dreyfus legend and removed the old extra tag pills.
- Improved assessment-definition security by removing `correct` answers from the frontend definition payload.
- Added scoring-focused tests in `tests/test_step20_ksa_assessment_scoring.py` and extended learning API tests for new KSA routes.

## 2026-04-07 22:55 UTC

- Implemented first real Learning-page KSA tab with a 3-column big-map radar visualization (`Knowledge`, `Skills`, `Abilities`).
- Added `Start Assessment` action and placeholder `KSA Assessment` dialog shell using the existing diagnostic modal pattern.
- Added KSA deep-dive placeholder section below the charts for future expansion.
- Added backend KSA profile foundation endpoint: `GET /api/learning-profile/ksa`.
- Added explicit KSA schema models (`services/retriever/schemas/ksa.py`) with validated 1-5 Dreyfus scale values.
- Added student default baseline KSA values (non-persisted placeholders) and neutral placeholder baseline for non-student users.
- Wired frontend app state to load/render KSA profile data (`useChatApp`, API client types, Learning page integration).
- Added API coverage for KSA endpoint behavior in `tests/test_step14_learning_api.py`.
- Updated README and learning/frontend/architecture/testing documentation for the new KSA big-map foundation.

## 2026-04-07 19:40 UTC

- Moved learning-path/course management into a dedicated `Courses` page and added a new sidebar `Courses` entry below `Learning`.
- Removed the old Learning `Paths` tab and added a new `KSA` tab placeholder with integrated styling.
- Added courses API endpoints for listing with filtering/sorting, JSON template retrieval, and multipart JSON import with per-file scope handling.
- Added strict course JSON schema parsing/validation (`services/retriever/services/course_files.py`) and startup bootstrap sync from `courses/`.
- Added export-back sync so existing learning paths are written as course JSON files in `courses/`.
- Added per-file upload scope enforcement with backend permission checks (`global` scope requires admin).
- Added starter course definition JSON files for existing example courses under `courses/`.
- Added/updated tests for courses routes and course JSON parser validation.
- Updated documentation across README, setup, API, learning, architecture, and testing docs.

## 2026-04-04 20:15 UTC

- Implemented Step B.1 diagnostic system driven by source `.docx` files (`LAA`, `MOA`, `LTA`) under `data/diagnostics/source`.
- Added migration `20260404_0009` with versioned diagnostics, attempts, answers, results, learning-state checks, and explanation feedback tables.
- Added docx parser/import pipeline and deterministic scoring engine (`services/retriever/services/diagnostic_definitions.py`, `diagnostic_scoring.py`).
- Added diagnostics/state/feedback API routes:
  - `/api/diagnostics/*`
  - `/api/learning-state-checks`
  - `/api/explanation-feedback`
- Extended learning profile bundle to include active diagnostics status (`not_started|in_progress|completed`).
- Added dynamic Step B.1 learning-page UI with backend-driven rendering, step flow, persistence, chart visualization, and attempt history.
- Added message-level explanation feedback actions in chat UI.
- Added Step B.1 parser/scoring and API tests:
  - `tests/test_stepb1_diagnostics_parser_and_scoring.py`
  - `tests/test_stepb1_diagnostics_api.py`
- Updated docs (`README.md`, `docs/architecture.md`, `docs/api.md`, `docs/learning.md`).

## 2026-04-04 17:45 UTC

- Implemented Step B declared learning profile layer with dedicated persistence for:
  - user learning preferences
  - learner background/context
  - structured learning goals
- Added Alembic migration `20260404_0008` for `user_learning_preferences`, `user_learning_profiles`, and `user_learning_goals`.
- Added authenticated Step B API endpoints for get/update profile bundle and goal CRUD with strict user ownership.
- Added enum and input validation for declared preference values and goal/context payloads.
- Added learning-page UI sections for `Learning Preferences`, `Learning Context / Background`, and `Learning Goals`.
- Kept Step B explicitly separate from diagnostic profiling; `diagnostics_status` remains `not_started`.
- Added focused Step B API and service tests for validation, role access, and user scoping.

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
