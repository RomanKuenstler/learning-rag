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

Step A introduces a dedicated learning domain:

- `learning_paths` with scope (`global` or `user`), status (`draft|published|archived`), and metadata.
- `learning_modules` ordered per path.
- `learning_lessons` ordered per module.
- `learning_path_allowed_files` and `learning_path_allowed_tags` for learning-path source scoping.

Authorization rules:

- admins can create global and user-scoped learning paths and manage any path.
- users can create and manage only their own user-scoped paths.
- students are read-only for learning paths in Step A.

Future learning chat support is prepared through:

- `chats.chat_type` (`normal|gpt|learning`)
- `chats.learning_path_id` nullable foreign key

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

Step B.1 adds source-of-truth diagnostics loaded from `.docx`:

- source files: `data/diagnostics/source/MythriQ-*.docx`
- parser pipeline: docx XML extraction -> structured diagnostic JSON (`LAA`, `MOA`, `LTA`)
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
