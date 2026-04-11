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

## Learning Foundation Model

The learning domain now supports both legacy linear structures and graph-based skilltree structures:

- `learning_paths` with scope (`global` or `user`), status (`draft|published|archived`), and metadata.
- `learning_modules` ordered per path.
- `learning_lessons` ordered per module.
- `learning_path_allowed_files` and `learning_path_allowed_tags` for learning-path source scoping.
- `learning_paths.schema_version` and `learning_paths.skilltree_definition` for v2 course graph persistence.
- `user_learning_node_progress` for per-user node state persistence.

Authorization rules:

- admins can create global and user-scoped learning paths and manage any path.
- users can create and manage only their own user-scoped paths.
- students are read-only for learning paths in Step A.

Future learning chat support is prepared through:

- `chats.chat_type` (`normal|gpt|learning`)
- `chats.learning_path_id` nullable foreign key

## Learning Node Session Model

A dedicated, non-chat learning session entity is now used for node-specific learning routes:

- table: `learning_node_sessions`
- uniqueness: one row per `(user_id, learning_path_id, node_id)`
- key fields:
  - `status` (`created|in_progress|completed`)
  - `is_archived`
  - `is_deleted` (soft-delete / hidden from sidebar)
  - `started_at`, `completed_at`, `last_opened_at`
  - timestamps (`created_at`, `updated_at`)

This keeps node-session lifecycle separate from:

- normal chats
- GPT chats

Lifecycle integration:

- node Start/Continue ensures or reactivates the existing learning-node session
- first successful learning-node route open marks session opened and transitions `created -> in_progress`
- node-progress updates (`completed|mastered`) synchronize session status to `completed`
- soft-delete hides from active sidebar but keeps DB row restorable

## User Node Context Generation Layer

A reusable node-context engine was added in:

- `services/retriever/services/node_context.py`

Responsibilities:

- load graph structure for a course/node
- resolve prior dependency completion and covered-topic summaries
- resolve target node metadata and immediate successor lookahead
- match node-relevant KSA profile/drill data
- infer structured readiness context
- persist grouped context snapshots for reuse

Persistence + access:

- ORM model/table: `UserLearningNodeContext` / `user_learning_node_contexts`
- repository/postgres upsert/list/get/delete methods
- API reads:
  - `GET /api/learning-paths/{learning_path_id}/nodes/{node_id}/context`
  - `GET /api/learning-paths/{learning_path_id}/node-contexts/available`

Recompute strategy:

- targeted recompute on node progress updates
- user-wide available-node recompute on KSA updates
- path-level invalidation when skilltree structure changes

Current non-goal:

- this layer does not execute node-type teaching logic yet; it only prepares structured context for later execution stages.

## Node Execution Services Layer

A dedicated node execution module is available in:

- `services/retriever/services/node_execution.py`

It implements modular execution logic for:

- `assessment_hook`
- `quiz`
- `practice`
- `checkpoint`
- `capstone`
- `unlock_gate`
- `milestone`

Key architecture points:

- runtime generation is on-demand (at node start), not pre-generated
- generated artifacts and results are persisted (`user_learning_node_execution_attempts`)
- execution consumes persisted user node context + current KSA/profile state
- start flow is resumable by default and supports repeat attempts via `force_new_attempt=true`
- completion updates flow back into node progress and KSA profile refinement
- upload-capable tasks persist artifact references and extracted summaries on the attempt payload
- checkpoint/capstone scoring combines deterministic MC scoring, LLM rubric scoring, and KSA drill scoring

Current non-goal:

- execution services for `learning_unit` and `review`.

## Course File Bootstrap Layer

Course/path definitions are represented as declarative JSON files in `courses/`.

- startup flow: validate files -> upsert valid courses into learning tables -> export current DB courses back to files
- schema validation is strict (required fields, node ids, dependency references, enum checks, cycle checks)
- invalid files are logged with file-specific error details and are not imported
- user-scoped file definitions require `owner_user_id`

Schema behavior:

- v2 (`schema_version: 2`) is the canonical representation (`chapters`, `branches`, `nodes`, `edges`, `entry_node_ids`, completion/layout metadata).
- v1 (`schema_version: 1`) remains supported and is migrated into a linear v2 graph during import/bootstrap.
- legacy module/lesson CRUD remains available; when used, the service regenerates the skilltree definition from linear structure for compatibility.

Runtime progression behavior:

- deterministic prerequisite evaluation with `requires_all` and `requires_any`
- optional/recommended/optional edges are supported without forcing linear sequencing
- node states computed as `locked`, `available`, `awaiting_checkpoint`, `in_progress`, `failed_needs_retry`, `completed`, `mastered`, `optional_skipped`
- branch-level requiredness is applied through effective-required node computation
- chapter completion and branch completion are computed from effectively-required nodes
- course completion is computed from required-branch completion and required global-capstone completion
- node runtime semantics expose blocked dependencies, parallel availability, checkpoint waiting, and capstone lock markers
- deterministic progression recommendation engine emits next node/branch + optional review/KSA suggestions
- hook-resolution layer emits retrospective, remediation, KSA mini-check, and adaptive-unlock candidate summaries
- node progression transitions are persisted through `PUT /api/learning-paths/{learning_path_id}/nodes/{node_id}/progress` with completion-mode validation
- node `reset` transition is supported by deleting persisted node progress for that node

## Declared Learning Profile Model (Step B)

Step B adds an explicit, user-declared learning profile layer that is separate from:

- generic assistant personalization
- diagnostic/psychometric learning profiling (Step B.1)

New user-scoped tables:

- `user_learning_preferences`
- `user_learning_profiles`
- `user_learning_goals`

This layer stores only learner-provided inputs and is designed for future composition with:

- Step B.1 diagnosed profile signals
- future real-time learning-state feedback
- future mastery/progress systems

## Step B.1 Diagnostic Model

Step B.1 diagnostics are now markdown-first and loaded from:

- source files: `data/sources/alpd/*v2.md` (`LAA`, `MOA`, `LTA`)
- parser pipeline: markdown parsing -> structured diagnostic JSON (`sections`, `questions`, `options`, optional `metadata`)
- MOA parser additionally extracts dynamic result blocks and pair mapping metadata
- immutable/versioned diagnostic storage per definition version
- deterministic scoring from persisted answers (no LLM scoring)

Added persistence entities:

- `diagnostic_definitions`
- `diagnostic_versions`
- `diagnostic_questions`
- `diagnostic_options`
- `diagnostic_scoring_rules`
- `user_diagnostic_attempts`
- `user_diagnostic_answers`
- `user_diagnostic_results`
- `learning_state_checks`
- `explanation_feedback`

Design intent:

- Step B declared preferences remain separate from Step B.1 diagnosed profiles
- final composition target is `LearningContext = declared_preferences + diagnostic_profile + state_signals + feedback_signals`
- LAA `Other:` responses are stored with the selected option as one answer object (`selected`, `other_text`)
- MOA result persistence includes both computed profile values and selected personalized output text

LAA scoring architecture now follows a section-based profile model:

- per-question option-to-dimension mapping for single-choice items
- section-local dimension aggregation
- deterministic normalization (`0..100`) using per-dimension max contribution envelopes
- emotional slider block handled as direct item-level subprofile values with documented compact indices
- multi-select sections handled as structured tag/profile lists instead of synthetic numeric grading

This keeps LAA outputs interpretable, composable for later personalization, and avoids collapsing heterogeneous sections into a single opaque score.

LTA scoring architecture now follows a channel-distribution model:

- answer options map to exactly one channel (`auditiv`, `visuell`, `kinaesthetisch`, `lesen_schreiben`)
- every selected answer increments one channel counter
- results persist both raw channel counts and normalized percentages
- deterministic profile interpretation classifies each attempt as:
  - `dominant` (top channel leads by at least 2)
  - `mixed` (top two channels close without a clear dominant)
  - `balanced` (all channels close; `max-min <= 1`)
- UI uses distribution-first rendering with generated summary text based on the computed classification and channel ranking

## KSA Assessment And Profile Model

KSA is modeled as a separate concept from Step B preferences and Step B.1 diagnostics.

- Profile endpoint: `GET /api/learning-profile/ksa`
- Assessment endpoints: `/api/ksa/assessment/*`
- Drill endpoints: `/api/ksa/drills/*`
- Schema modules:
  - `services/retriever/schemas/ksa.py`
  - `services/retriever/schemas/ksa_assessment.py`
  - `services/retriever/schemas/ksa_drills.py`
- Scoring/definition module:
  - `services/retriever/services/ksa_assessment.py`
  - `services/retriever/services/ksa_drills.py`

Persistence entities:

- `user_ksa_profiles`
- `user_ksa_assessment_attempts`
- `user_ksa_drill_attempts`

Source model:

- `student_default_baseline`: non-persisted baseline for students before first completion
- `placeholder_baseline`: non-persisted neutral fallback before first completion
- `assessment`: persisted scored result after completion

Scale model:

- numeric `1..5` values mapped to Dreyfus levels (`Novice` -> `Expert`)
- chart display uses the same `1..5` scale across `knowledge`, `skills`, and `abilities`

Initial assessment architecture:

- Phase 1 sieve controls which knowledge and skill topics are assessed now.
- Untriggered topics are persisted as `uncharted`.
- Knowledge uses `FS = slider * multiplier` (`0.5`, `1.0`, `1.5`) and maps to levels `1..3`.
- Skills use deterministic scenario mapping (`A -> 1`, `B -> 3`).
- Abilities use deterministic weighted capacity:
  - `capacity = correctness*0.7 + time_bonus*0.3`
  - mapped to display levels `1..5`
- Derived values include `learning_speed_multiplier` based on quantitative + executive-function capacity.

This keeps assessment scoring deterministic and separated from presentation mapping, so future mini-assessments and deep-dive views can extend the system without replacing the current API contract.

KSA drills architecture:

- drill topic and archetype source:
  - `prds/interaction-archetypes_ksa.json`
  - loaded through a dedicated parser/cache in `ksa_drills.py`
- drill flow engine:
  - user selects `1..3` top-level topics
  - system generates deterministic 12-question triple-drill sequence per topic
- persistence model:
  - each drill attempt stores selected topics, generated question set, staged answers, and result payload
  - profile refinement writes into `user_ksa_profiles.profile_json`
  - drill-specific long-lived state is stored under `profile_json.drill_state`
    - `topic_nodes`
    - `sub_nodes`
    - map-decay counters
    - attempt metadata/source markers

Separation intent:

- initial onboarding assessment and deep-dive drills are separate engines
- visualization remains top-level radar based for now
- persistence already supports future node-splitting/shatter visualizations without schema replacement

## Personalization Layer Architecture

A dedicated learning personalization layer engine has been added:

- `services/retriever/services/personalization_layers.py`

Responsibilities:

- collect source data from profile, goals, preferences, diagnostics, KSA, and live adaptation inputs
- resolve six grouped snapshots
- compute six resolved rule sets
- persist grouped outputs and trace metadata

Persistence model:

- `UserLearningPersonalizationLayer` (`user_learning_personalization_layers`)

Integration point:

- `RetrieverAppService` calls targeted recompute after relevant write operations
- recompute is fail-open (warnings logged, primary learning APIs continue)

Debug access:

- `GET /api/learning-profile/personalization-layers`

## Learning Node Execution Architecture (Plan-First)

`LearningNodeExecutionService` now supports plan-first runtime generation for `learning_unit` and `review`.

Key points:

- generation is on-demand at node start (no pre-generation at import time)
- package persistence remains in `user_learning_node_execution_attempts`
- package shape is node-type-specific and includes structured planning artifacts
- KSA/drill and personalization snapshots are injected as calibration signals
- resume/repeat semantics stay consistent with existing node execution behavior

Prompt sources:

- node-generation/evaluation prompts are externalized under `prompts/learning-node-*.md`
- runtime loader reads prompt files directly from disk for easy iteration
