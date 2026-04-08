# Local AI System

Local, containerized Retrieval-Augmented Generation for indexing your own files and chatting with grounded, citation-ready answers.

## Step B Scope

This repository includes the learning foundation, declared learning profile layer, and Step B.1 diagnostics:

- JWT-based authentication with forced password change flow
- role model: `admin`, `user`, `student`
- student restrictions for normal chat and GPT usage
- learning-path domain model with global and user scope
- ordered module and lesson structure
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
- KSA baseline profile API (`/api/learning-profile/ksa`) with student default values on a Dreyfus 1-5 scale
- dedicated Courses page with filtering, sorting, template download, and JSON import dialog
- file-backed course definitions under `courses/` with startup validation + bootstrap sync
- web UI sidebar navigation entries for Learning and Courses
- future learning-chat foundation fields (`chat_type`, `learning_path_id`)

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
