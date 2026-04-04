# Local AI System

Local, containerized Retrieval-Augmented Generation for indexing your own files and chatting with grounded, citation-ready answers.

## Step A Scope

This repository now includes the learning foundation layer:

- JWT-based authentication with forced password change flow
- role model: `admin`, `user`, `student`
- student restrictions for normal chat and GPT usage
- learning-path domain model with global and user scope
- ordered module and lesson structure
- learning-path source scoping through allowed files and tags
- learning-path CRUD API with role-based authorization
- web UI learning-path management page and sidebar navigation entry
- future learning-chat foundation fields (`chat_type`, `learning_path_id`)

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

Open:

- web UI: `http://localhost:5173`
- retriever API: `http://localhost:8000`

Detailed setup and architecture notes live in [docs/setup.md](/Users/rknstlr/Workspace/TEST/learning-rag/docs/setup.md), [docs/api.md](/Users/rknstlr/Workspace/TEST/learning-rag/docs/api.md), [docs/authentication.md](/Users/rknstlr/Workspace/TEST/learning-rag/docs/authentication.md), [docs/users.md](/Users/rknstlr/Workspace/TEST/learning-rag/docs/users.md), [docs/admin.md](/Users/rknstlr/Workspace/TEST/learning-rag/docs/admin.md), and [docs/security.md](/Users/rknstlr/Workspace/TEST/learning-rag/docs/security.md).
