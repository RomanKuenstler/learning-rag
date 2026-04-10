# Changelog

## 2026-04-10 13:45 UTC

- Reworked LTA scoring into a channel-distribution model:
  - one deterministic counter per channel (`auditiv`, `visuell`, `kinaesthetisch`, `lesen_schreiben`)
  - persisted `channel_counts`, `channel_percentages_0_100`, `top_ranked_channels`, and `total_answers`
  - added deterministic classification and profile metadata (`classification`, `profile_label`, `summary_text`)
  - classification rules:
    - `dominant`: top channel leads second by `>= 2`
    - `mixed`: top two channels when no clear dominant
    - `balanced`: all channels close (`max-min <= 1`)
- Updated LTA result UI from dominant-only donut output to a distribution-first profile card:
  - 4-channel bar distribution with percentages and raw counts
  - generated profile type label (`dominant`/`mixed`/`balanced`)
  - generated user-facing summary text from the computed result
  - removed legacy dominant-only line beneath the LTA chart
- Added LTA scoring tests for:
  - per-answer channel counting
  - percentage conversion
  - dominant, mixed, and balanced detection
  - summary text generation expectations
- Updated docs:
  - `docs/diagnostics.md`
  - `docs/learning.md`
  - `docs/architecture.md`

## 2026-04-10 12:25 UTC

- Reworked LAA scoring from aggregate score behavior into section-based profile logic:
  - per-section structured result payloads (`section_profiles`)
  - per-question/option dimension mapping table for single-choice items
  - deterministic per-dimension normalization to `0..100` based on mapped max envelopes
  - profile-oriented insight generation (no pass/fail or grade-like framing)
- Added/expanded internal LAA dimensions:
  - `zielklarheit`, `zeitdruck`, `strukturbedarf`, `feedbackbedarf`, `selbststeuerung`, `soziale_lernorientierung`, `emotionale_sicherheit`, `frustrationsanfaelligkeit`, `technikaffinitaet`, `praxisorientierung`, `sichtbarkeitsmotivation`
- Implemented LAA emotional subprofile handling:
  - persisted item-level slider values (`1..5`) and normalized values (`0..100`)
  - documented summary indices: `lernsicherheit`, `selbstvertrauen`, `aeusserer_aktivierungsbedarf`
- Implemented LAA multi-select/tag profile model:
  - interests/competencies/everyday-abilities and custom free text are persisted as `profile_tags`
  - removed fake score behavior for multi-select profile areas
- Updated LAA result presentation in diagnostics UI:
  - keeps high-level section bars
  - adds section cards with profile insights, normalized dimension bars, summary indices, tags, and emotional item values
- Added deterministic per-attempt randomization in diagnostic flow:
  - MOA question order randomized per attempt (stable on resume)
  - LTA question order randomized per attempt (stable on resume)
  - LTA option order randomized per question per attempt (stable on resume)
- Expanded scoring tests:
  - section-based LAA profile validation
  - mapping + normalization determinism checks
  - emotional subprofile/indices checks
  - multi-select tag persistence checks
- Updated docs:
  - `docs/diagnostics.md`
  - `docs/learning.md`
  - `docs/architecture.md`

## 2026-04-10 11:05 UTC

- Migrated Learning Preference Diagnostic sources to markdown v2 only:
  - `data/sources/alpd/LAAv2.md`
  - `data/sources/alpd/MOAv2.md`
  - `data/sources/alpd/LTAv2.md`
- Removed legacy diagnostic source artifacts from runtime source directory (`.docx`, `.txt`, and duplicates).
- Reworked diagnostic definition loading to parse markdown dynamically (sections/questions/options/metadata) and removed legacy document fallback parsing logic.
- Added MOA result-block parsing and dynamic pairing logic:
  - MOA now stores parsed result blocks and block index from `MOAv2.md`
  - scoring selects personalized result text based on the computed top motivation pair
  - persisted MOA result now includes `computed_profile`, `selected_result_block_id`, `selected_result_block_title`, and `result_text`
- Updated diagnostics UI:
  - kept existing MOA chart/diagram
  - added `Personalized Output` section below MOA chart with dynamic backend-driven text
  - upgraded LAA `Other:` UX to inline option-embedded textarea with required input behavior when selected
- Updated diagnostic answer handling so `Other:` data is stored inline with selection (`selected` + `other_text`) instead of detached companion fields.
- Updated tests for v2 source loading and scoring behavior:
  - parser/scoring tests now use `data/sources/alpd`
  - added MOA dynamic result mapping assertions
  - added LAA inline `Other:` answer-shape scoring assertion
  - updated API test payloads to persist structured LAA answers
- Updated documentation:
  - `docs/learning.md`
  - `docs/architecture.md`
  - new `docs/diagnostics.md`

## 2026-04-09 18:20 UTC

- Implemented Phase 3 dynamic progression layer for skilltree courses:
  - branch completion summaries with required/optional branch semantics
  - stronger course completion semantics based on required-branch completion and required global-capstone completion
  - deterministic recommendation engine (`next_best_node`, `next_branch`, optional/review/KSA suggestions)
  - hook-resolution summaries for retrospective, review/remediation, KSA mini-assessment, and adaptive-unlock candidates
- Extended v2 node schema contracts with dynamic metadata:
  - `retrospective_hooks`
  - `ksa_hooks`
  - `remediation`
  - `adaptive_unlock`
- Added additional validation for remediation/adaptive references (node and branch id integrity checks).
- Extended API payload contracts (`LearningPathRead`) with:
  - `branch_progress`
  - richer `completion_summary` (required-branch/global-capstone counters)
  - `recommendations`
  - `hook_summary`
- Updated Courses page UX for dynamic progression visibility:
  - recommendation strip below graph
  - branch progress strip below chapter progress strip
  - side-panel sections for branch/role, hooks/adaptation, and richer course progress semantics
- Updated example DevOps skilltree course to include Phase 3 metadata/hook/adaptive/remediation structures and completion-rule metadata.
- Expanded tests:
  - runtime coverage for branch progress, recommendations, and hook-summary emission
  - schema/parser coverage for new Phase 3 node metadata structures
- Updated docs:
  - `README.md`
  - `docs/learning.md`
  - `docs/courses.md`
  - `docs/architecture.md`
  - `docs/testing.md`

## 2026-04-08 23:05 UTC

- Implemented Phase 2 skilltree semantics upgrade:
  - expanded node types: `learning_unit`, `practice`, `quiz`, `checkpoint`, `review`, `milestone`, `capstone`, `unlock_gate`, `assessment_hook`
  - expanded completion modes: `lesson_complete`, `practice_complete`, `quiz_pass`, `checkpoint_pass`, `review_complete`, `assessment_threshold`, `gate_unlock`, `manual`
- Extended schema v2 models with richer progression metadata:
  - `branches` (`required` vs optional branch routes)
  - per-node `branch_id`
  - richer KSA metadata (`start_level`, target, contribution, assessment hints)
  - node unlock metadata (`unlocks.node_ids|branch_ids|recommended_next_node_ids`)
  - node reward metadata (`rewards.estimated_ksa_gain|effort_score|reward_tags`)
- Extended edge relationship support with `optional` alongside `requires_all|requires_any|recommended`.
- Upgraded runtime progression logic:
  - new runtime states: `awaiting_checkpoint`, `failed_needs_retry`
  - effective-required completion semantics (required nodes inside optional branches do not block final completion)
  - per-node runtime semantics map (`blocked_by_*`, parallel availability, checkpoint wait, capstone lock, completion-allowed)
- Added deterministic node progress transition API:
  - `PUT /api/learning-paths/{learning_path_id}/nodes/{node_id}/progress`
  - mode-aware validation for quiz/checkpoint pass thresholds, assessment thresholds, and gate unlock evidence
  - assessment-hook nodes remain explicit non-executable placeholders in this phase
- Updated courses frontend and contracts:
  - richer node-type icon handling
  - detail panel now shows completion rule, runtime semantics, KSA start/target/weight/hints, and unlock/reward metadata
  - added node progress action controls (`Start`, `Complete`, `Master`, `Skip Optional`, `Mark Retry`)
- Updated DevOps example course JSON to a richer Phase 2 graph with quiz, milestone, unlock gate, assessment hook, and capstone nodes plus branch metadata.
- Added/updated tests:
  - expanded `tests/test_courses_files.py` for branch + richer schema validation
  - expanded `tests/test_course_skilltree_runtime.py` for effective-required completion, checkpoint wait, capstone lock, and parallel semantics
- Updated docs:
  - `README.md`
  - `docs/learning.md`
  - `docs/courses.md`
  - `docs/architecture.md`
  - `docs/testing.md`

## 2026-04-08 22:10 UTC

- Reworked course model into graph-based skilltree foundation with schema v2.
- Added v2 course JSON support (`chapters`, `nodes`, `edges`, `entry_node_ids`, completion/layout metadata, node KSA links).
- Added compatibility migration path for legacy v1 module/lesson JSON imports.
- Added learning-path persistence fields for skilltree definitions:
  - `learning_paths.schema_version`
  - `learning_paths.skilltree_definition`
- Added per-user node progress persistence table:
  - `user_learning_node_progress`
- Implemented deterministic prerequisite/unlock runtime logic:
  - `requires_all`, `requires_any`, `recommended`
  - node states: `locked`, `available`, `in_progress`, `completed`, `mastered`, `optional_skipped`
  - chapter/branch and course completion summaries for required-node completion
- Updated course import/export/bootstrap flow to use v2 as canonical while preserving legacy linear editing compatibility.
- Reworked Courses detail UI from linear module list to skilltree graph with:
  - node/edge visualization
  - progress-state styling
  - right-side node details panel
  - KSA metadata display
  - chapter and overall completion summaries
- Added new tests:
  - `tests/test_course_skilltree_runtime.py`
  - expanded `tests/test_courses_files.py` for v2 validation + v1 migration + cycle validation
- Updated docs:
  - `README.md`
  - `docs/learning.md`
  - `docs/courses.md`
  - `docs/api.md`
  - `docs/architecture.md`
  - `docs/testing.md`

## 2026-04-08 18:35 UTC

- Added KSA Assessment Drills (deep-dive) flow end-to-end:
  - `Start Assessment Drills` action in Learning KSA tab
  - direct-to-topic-selection drill dialog (no splash)
  - user selection of `1..3` big-map topics
  - deterministic 12-question triple-drill sequence per selected topic
- Added KSA drill persistence model and migration:
  - `user_ksa_drill_attempts`
  - profile-level `drill_state` refinement storage with `topic_nodes`, `sub_nodes`, map-decay metadata, and archetype source
- Added KSA drill APIs:
  - `GET /api/ksa/drills/topics`
  - `POST /api/ksa/drills/attempts`
  - `GET /api/ksa/drills/attempts/latest`
  - `GET /api/ksa/drills/attempts/{attempt_id}`
  - `PUT /api/ksa/drills/attempts/{attempt_id}/answers`
  - `POST /api/ksa/drills/attempts/{attempt_id}/complete`
- Wired drill scoring/refinement logic:
  - parent topic level updates (`+0.2` on Q1+Q2 pass)
  - map-decay signal on Q1 fail
  - sub-topic expansion updates for block 2/3
  - stress-test ability scoring with 15s time target (`correctness*0.7 + time_remaining*0.3`)
- Integrated drill prompt/archetype loading from `prds/interaction-archetypes_ksa.json` with deterministic fallback prompts.
- Improved free-text normalization tolerance for drill scoring (case/punctuation/spacing/morphological token variants).
- Added/updated tests:
  - `tests/test_step21_ksa_drills.py`
  - `tests/test_step14_learning_api.py` drill route coverage

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
