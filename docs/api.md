# API

## Base URLs

- Retriever API: `http://localhost:8000`
- Internal embedder attachment API: `http://embedder:8001`

## GPTs

### `GET /api/gpts`

Returns all GPTs owned by the authenticated user.

### `POST /api/gpts`

Creates a GPT and eagerly provisions its persistent GPT chat.

### `GET /api/gpts/{gpt_id}`

Returns one GPT record or `404`.

### `PATCH /api/gpts/{gpt_id}`

Updates GPT metadata and GPT-only configuration.

### `DELETE /api/gpts/{gpt_id}`

Deletes the GPT plus its associated GPT chat history.

### `POST /api/gpts/preview/messages`

Runs a non-persistent preview turn with the submitted GPT draft and ephemeral preview history.

### `GET /api/gpts/{gpt_id}/chat`

Returns the GPT definition plus its persistent GPT chat history.

### `POST /api/gpts/{gpt_id}/messages`

Appends a message to the GPT-owned persistent chat and responds using only GPT configuration.

### `DELETE /api/gpts/{gpt_id}/chat`

Clears the persistent GPT chat while keeping the GPT definition intact.

### `GET /api/gpts/{gpt_id}/download`

Exports the GPT chat as JSON.

Student restriction:

- `student` role receives `403` for GPT endpoints in Step A.

## Chats

### `POST /api/chats`

Creates a new chat with a generated placeholder name.

### `GET /api/chats`

Returns non-archived chats ordered by most recently updated first.

### `GET /api/chats/archived`

Returns archived chats ordered by most recently updated first.

### `GET /api/chats/{chat_id}`

Returns one chat record or `404`.

### `PATCH /api/chats/{chat_id}`

Renames a chat.

### `DELETE /api/chats/{chat_id}`

Deletes the chat, messages, attachment metadata, and retrieval logs.

### `PATCH /api/chats/{chat_id}/archive`

Sets `is_archived=true` for the chat.

### `PATCH /api/chats/{chat_id}/unarchive`

Sets `is_archived=false` for the chat.

### `GET /api/chats/{chat_id}/download`

Returns a JSON export payload and includes a download filename in `Content-Disposition`.

### `GET /api/chats/{chat_id}/messages`

Returns full chat history. Messages now include:

- `has_attachments`
- `attachments`
- `sources`

### `POST /api/chats/{chat_id}/messages`

Supports either JSON or multipart form data.

JSON request:

```json
{
  "message": "What does the Docker book say about volumes?",
  "assistant_mode": "thinking"
}
```

Student restriction:

- `student` role receives `403` for normal chat endpoints in Step A.

## Learning Paths

### `GET /api/learning-paths`

Lists learning paths visible to the authenticated user.

### `POST /api/learning-paths`

Creates a learning path.

Permission rules:

- `admin`: can create `global` and `user` scope.
- `user`: can create `user` scope only.
- `student`: `403`.

### `GET /api/learning-paths/{learning_path_id}`

Returns one visible learning path with nested modules and lessons.

### `PATCH /api/learning-paths/{learning_path_id}`

Updates path metadata and source scoping (`allowed_file_ids`, `allowed_tags`).

### `DELETE /api/learning-paths/{learning_path_id}`

Deletes a learning path.

### `POST /api/learning-paths/{learning_path_id}/modules`

Creates a module appended to the end of the path.

### `PATCH /api/learning-paths/{learning_path_id}/modules/reorder`

Reorders modules by explicit `order_index`.

### `PATCH /api/learning-modules/{module_id}`

Updates one module.

### `DELETE /api/learning-modules/{module_id}`

Deletes one module and its lessons.

### `POST /api/learning-modules/{module_id}/lessons`

Creates a lesson appended to the end of the module.

### `PATCH /api/learning-modules/{module_id}/lessons/reorder`

Reorders lessons by explicit `order_index`.

### `PATCH /api/learning-lessons/{lesson_id}`

Updates one lesson.

### `DELETE /api/learning-lessons/{lesson_id}`

Deletes one lesson.

## Declared Learning Profile (Step B)

### `GET /api/learning-profile`

Returns the current user bundle:

- `preferences` (declared learning preferences)
- `context` (learner background/context)
- `goals` (structured learning goals)
- `diagnostics_status` (`not_started|in_progress|completed`)

### `PATCH /api/learning-profile/preferences`

Partial update for declared learning preferences.

Supported enum fields:

- `preferred_pace`: `slow|balanced|fast`
- `explanation_depth`: `concise|balanced|detailed`
- `examples_vs_theory`: `more_examples|balanced|more_theory`
- `structure_preference`: `more_structured|balanced|more_conversational`
- `checkpoint_frequency`: `low|medium|high`
- `encouragement_level`: `low|balanced|high`
- `guidance_level`: `step_by_step|balanced|more_independent`
- `recap_frequency`: `low|medium|high`
- `preferred_learning_format`: `reading|dialogue|exercises|mixed`

### `PATCH /api/learning-profile/context`

Partial update for learner background/context:

- `education_background`
- `current_skill_areas`
- `interests`
- `professional_context`
- `current_reason_for_learning`
- `preferred_form_of_address`
- `learning_context_notes`

### `POST /api/learning-profile/goals`

Creates one user-scoped learning goal.

### `PATCH /api/learning-profile/goals/{goal_id}`

Partially updates one user-owned goal (`404` when not owned or missing).

### `DELETE /api/learning-profile/goals/{goal_id}`

Deletes one user-owned goal (`404` when not owned or missing).

## Diagnostics (Step B.1)

### `GET /api/diagnostics/definitions`

Returns active diagnostic definitions loaded from source `.docx`.

### `GET /api/diagnostics/definitions/{diagnostic_type}`

Returns one definition for `LAA|MOA|LTA`.

### `POST /api/diagnostics/attempts`

Starts a new user attempt and snapshots active definition versions.

### `GET /api/diagnostics/attempts`

Returns all attempts for the current user (latest first).

### `GET /api/diagnostics/attempts/latest`

Returns latest attempt with grouped answers and optional result.

### `GET /api/diagnostics/attempts/{attempt_id}`

Returns one user-owned attempt with answers and result.

### `PUT /api/diagnostics/attempts/{attempt_id}/answers`

Upserts answers for one diagnostic step (`LAA|MOA|LTA`).

### `POST /api/diagnostics/attempts/{attempt_id}/complete`

Runs deterministic scoring and persists the result payload.

## Learning State Checks

### `POST /api/learning-state-checks`

Persists a lightweight runtime learning state signal (`mood`, `perceived_difficulty`, `needs_pause_or_input`, `preferred_format`, `notes`, optional `chat_id`).

### `GET /api/learning-state-checks`

Lists latest state checks for the authenticated user.

## Explanation Feedback

### `POST /api/explanation-feedback`

Persists message-level feedback (`message_id`, `rating 1..5`, optional text, `re_explain_requested` flag).

Multipart request:

- `message`: text field
- `assistant_mode`: `simple`, `refine`, or `thinking`
- `files`: up to 3 file parts

Response:

```json
{
  "chat_id": "chat-id",
  "user_message": {
    "id": "1",
    "chat_id": "chat-id",
    "role": "user",
    "content": "Explain the attachment",
    "status": "completed",
    "has_attachments": true,
    "created_at": "2026-03-30T12:00:00Z",
    "sources": [],
    "attachments": [
      {
        "file_name": "diagram.png",
        "file_type": "png",
        "extraction_method": "ocr",
        "quality": {
          "score": 0.91
        }
      }
    ]
  },
  "assistant_message": {
    "id": "2",
    "chat_id": "chat-id",
    "role": "assistant",
    "content": "...",
    "status": "completed",
    "has_attachments": false,
    "created_at": "2026-03-30T12:00:01Z",
    "sources": [],
    "attachments": []
  },
  "assistant_mode": "thinking",
  "sources": [],
  "attachments_used": [
    {
      "file_name": "diagram.png",
      "file_type": "png",
      "extraction_method": "ocr",
      "quality": {
        "score": 0.91
      }
    }
  ]
}
```

## Settings

### `GET /api/settings`

Returns live retriever settings and available assistant modes. Step 11 mode lists may include `simple`, `refine`, and `thinking`.

### `PATCH /api/settings`

Updates retriever settings immediately and persists them.

Request:

```json
{
  "chat_history_messages_count": 5,
  "max_similarities": 8,
  "min_similarities": 2,
  "similarity_score_threshold": 0.7
}
```

## Library

### `GET /api/library/files`

Returns embedded library files and upload constraints.

Query params:

- `include_other_users` (boolean, default `false`)

When `false`, the list includes:

- global files
- files owned by the authenticated user

When `true`, other users' files are also included.

### `POST /api/library/files/upload`

Multipart upload endpoint used by the web UI.

Rules:

- max file count comes from `MAX_UPLOAD_FILES`
- allowed extensions come from `ALLOWED_UPLOAD_EXTENSIONS`
- tags default to `DEFAULT_TAG`
- duplicate names are rejected
- admin uploads are persisted as global files (`is_global=true`, `source_origin=admin_upload`)
- non-admin uploads are persisted as user-owned files (`is_global=false`, `source_origin=user_upload`)

### `PATCH /api/library/files/{file_id}`

Toggles `is_enabled` without deleting vectors.

Permission rules:

- normal users cannot disable global files (`403`)
- admins can toggle any file

### `DELETE /api/library/files/{file_id}`

Deletes the library file from local storage, PostgreSQL, Qdrant, and tag metadata.

Permission rules:

- normal users cannot delete global files (`403`)
- normal users cannot delete other users' files (`403`)
- admins can delete any file

## Internal Embedder Attachment Job

### `POST /internal/process-attachments`

Used only by the retriever service.

Request payload:

```json
{
  "type": "attachment_processing",
  "files": [
    {
      "file_name": "table.csv",
      "content_base64": "..."
    }
  ]
}
```

This endpoint extracts text and returns ephemeral attachment metadata. It does not persist vectors or file content.
# API

## Authentication

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `POST /api/auth/change-password`

## Admin

- `GET /api/admin/users`
- `POST /api/admin/users`
- `PATCH /api/admin/users/{id}`
- `DELETE /api/admin/users/{id}`

## Authenticated App Endpoints

All existing chat, library, and settings endpoints now require a bearer token.

Responses may include:

- `X-Auth-Token`
- `X-Auth-Expires-At`
- `X-Auth-Max-Expires-At`

When present, the frontend should replace the stored token with the refreshed one.

## Step 9 Filtering

- `GET /api/user/files`
- `PATCH /api/user/files/{file_id}`
- `GET /api/user/tags`
- `PATCH /api/user/tags/{tag}`
- `GET /api/chats/{chat_id}/files`
- `PATCH /api/chats/{chat_id}/files/{file_id}`
- `GET /api/chats/{chat_id}/tags`
- `PATCH /api/chats/{chat_id}/tags/{tag}`

All filter endpoints are authenticated and user-scoped.

### Response Shape

File filters return:

- `file_id`
- `file_name`
- `file_path`
- `tags`
- `global_is_enabled`
- `scoped_is_enabled`
- `is_enabled`
- `is_locked`
- `updated_at`

File filter permissions:

- `PATCH /api/user/files/{file_id}` returns `403` when a non-admin tries to disable a global file
- `PATCH /api/chats/{chat_id}/files/{file_id}` returns `403` for the same restriction

Tag filters return:

- `tag`
- `file_count`
- `global_is_enabled`
- `scoped_is_enabled`
- `is_enabled`
- `is_locked`

`PATCH` requests accept:

```json
{
  "is_enabled": false
}
```
