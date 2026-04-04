# Local AI System

Local, containerized Retrieval-Augmented Generation for indexing your own files and chatting with grounded, citation-ready answers.

## Step 10 Scope

This repository now includes the Step 10 PRD implementation:

- JWT-based authentication with forced password change flow
- multi-user chat, retrieval log, and settings isolation
- admin user management UI and API
- bootstrap provisioning from `users.json`
- global library protection rules for system files and admin uploads
- user-owned file defaults: owner-enabled, other-users-disabled
- library visibility toggle to show or hide other users' files in the table
- user-scoped personalization stored in preferences and applied to every chat prompt
- updated docs, tests, and Docker validation for the Step 10 rollout

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

Open:

- web UI: `http://localhost:5173`
- retriever API: `http://localhost:8000`

Detailed setup and architecture notes live in [docs/setup.md](/Users/rknstlr/Workspace/TEST/learning-rag/docs/setup.md), [docs/api.md](/Users/rknstlr/Workspace/TEST/learning-rag/docs/api.md), [docs/authentication.md](/Users/rknstlr/Workspace/TEST/learning-rag/docs/authentication.md), [docs/users.md](/Users/rknstlr/Workspace/TEST/learning-rag/docs/users.md), [docs/admin.md](/Users/rknstlr/Workspace/TEST/learning-rag/docs/admin.md), and [docs/security.md](/Users/rknstlr/Workspace/TEST/learning-rag/docs/security.md).
