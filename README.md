# Local AI System

Local, containerized Retrieval-Augmented Generation for indexing your own files and chatting with grounded, citation-ready answers.

## Step B Scope

This repository includes the learning foundation, declared learning profile layer, and Step B.1 diagnostics:

- JWT-based authentication with forced password change flow
- role model: `admin`, `user`, `student`
- student restrictions for normal chat and GPT usage
- learning-path domain model with global and user scope
- graph-based skilltree course structure (`schema_version: 2`)
- compatibility migration from legacy linear module/lesson JSON (`schema_version: 1`)
- node prerequisites (`requires_all`, `requires_any`, `recommended`) with deterministic unlock logic
- richer node semantics (`learning_unit`, `practice`, `quiz`, `checkpoint`, `review`, `milestone`, `capstone`, `unlock_gate`, `assessment_hook`)
- node completion modes (`lesson_complete`, `practice_complete`, `quiz_pass`, `checkpoint_pass`, `review_complete`, `assessment_threshold`, `gate_unlock`, `manual`)
- expanded node progress-state model (`locked`, `available`, `awaiting_checkpoint`, `in_progress`, `failed_needs_retry`, `completed`, `mastered`, `optional_skipped`)
- node-level KSA metadata support (`K/S/A`, topic, subtopic, start/target level, contribution weight, assessment-hook flags)
- optional and required branch modeling with effective-required completion behavior
- node reward/unlock metadata (`unlocks`, `recommended_next_node_ids`, `estimated_ksa_gain`, reward tags)
- Phase 3 dynamic progression layer:
  - branch-level completion summaries (`required` vs optional branches)
  - stronger course-completion semantics (required-branch completion + global capstone completion)
  - deterministic recommendation engine (`next_best_node`, `next_branch`, optional/review/KSA suggestions)
  - retrospective and KSA mini-assessment hook summaries
  - remediation and adaptive-unlock metadata on nodes for future adaptive routing
- node progress update API for deterministic per-node transitions (`PUT /api/learning-paths/{id}/nodes/{node_id}/progress`)
- learning-path source scoping through allowed files and tags
- learning-path CRUD API with role-based authorization
- user-scoped declared learning preferences
- user-scoped learner context/background profile
- user-scoped structured learning goals
- versioned docx-driven diagnostic definitions (LAA, MOA, LTA)
- deterministic diagnostic scoring engine (non-LLM)
- diagnostic attempt history with persisted answers and results
- real-time learning state check persistence
- explanation feedback persistence (rating, text, re-explain flag)
- dynamic frontend diagnostic flow and backend-driven charts
- dedicated learning UI sections for preferences, context, goals, and KSA big-map visualization
- KSA profile + initial assessment system:
  - profile API: `/api/learning-profile/ksa`
  - assessment flow APIs: `/api/ksa/assessment/*`
  - deterministic 4-phase scoring with persisted results that replace baseline defaults after completion
- KSA assessment drills system:
  - drill APIs: `/api/ksa/drills/*`
  - topic selection (`1..3` topics), 12-question triple-drill flow per topic
  - top-level KSA refinement + persisted sub-topic nodes (`drill_state`) for future map shattering visuals
  - drill prompt/archetype source: `prds/interaction-archetypes_ksa.json`
- dedicated Courses page with filtering, sorting, template download, and JSON import dialog
- file-backed course definitions under `courses/` with startup validation + bootstrap sync
- web UI sidebar navigation entries for Learning and Courses
- future learning-chat foundation fields (`chat_type`, `learning_path_id`)
- dedicated course editor route (`/courses/:courseId/edit`) with raw JSON editing and MinIO-backed course attachments

Step B (declared preferences) remains separate from Step B.1 (diagnosed preferences and runtime signals).

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

Open:

- web UI: `http://localhost:5173`
- retriever API: `http://localhost:8000`

Detailed setup and architecture notes live in [docs/setup.md](/Users/rknstlr/Workspace/TEST/learning-rag/docs/setup.md), [docs/api.md](/Users/rknstlr/Workspace/TEST/learning-rag/docs/api.md), [docs/authentication.md](/Users/rknstlr/Workspace/TEST/learning-rag/docs/authentication.md), [docs/users.md](/Users/rknstlr/Workspace/TEST/learning-rag/docs/users.md), [docs/admin.md](/Users/rknstlr/Workspace/TEST/learning-rag/docs/admin.md), and [docs/security.md](/Users/rknstlr/Workspace/TEST/learning-rag/docs/security.md).
