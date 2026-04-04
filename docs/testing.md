# Testing

## Automated Checks

Create a Python 3.11 virtualenv and run:

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -r services/retriever/requirements.txt -r services/embedder/requirements.txt
python -m pytest tests -q
python3 -m compileall services migrations tests webui/src
```

Frontend build smoke check:

```bash
cd webui
npm install
npm run build
```

## Step 7 Checks Covered

- frontend production build after the Step 7 restyle
- existing retrieval and processor regressions
- frontend production build
- migration module importability

## Step 9 Checks Covered

- global file filters through both the library page API and the dedicated user filter API
- chat-level file filters with global disable precedence
- global tag filters
- chat-level tag filters with locked global overrides
- retrieval candidate filtering before score thresholding and result truncation

## Step 11 Checks Covered

- `thinking` mode executes planning, drafting, and refining in sequence
- `planning_result` is passed into drafting and refining
- `draft_result` is passed into refining
- only the final answer is persisted and returned to the API caller
- shared RAG context, personalization, and chat history stay in the prompt flow
- thinking-mode failures fall back gracefully to the simple pipeline

## Step 12 Checks Covered

- GPT CRUD API coverage
- GPT chat fetch, clear, download, and message endpoints
- GPT preview endpoint coverage
- frontend production build with GPT routes, editor state, and sidebar integration
- live docker smoke checks for migration startup, GPT CRUD, preview, and persistent GPT chat

## Step 13 Checks Covered

- global file classification metadata (`is_global`, `source_origin`) for system/admin/user origins
- owner-based default enablement for user-uploaded files (owner true, other users false)
- retrieval exclusion for default-disabled other-user files
- non-admin protection rules for global-file disable and delete actions
- non-admin protection rules for deleting files owned by other users
- library listing support for `include_other_users` query behavior
- web library switch behavior for showing or hiding other users' files

## Step A Learning Foundation Checks Covered

- role validation accepts `student` in auth/admin-user flows
- student restrictions block normal chat and GPT endpoints
- learning-path list and create endpoints with role-aware authorization
- ordered module and lesson CRUD/reorder endpoint coverage
- source scoping persistence fields (`allowed_file_ids`, `allowed_tags`)

## Step B Declared Learning Profile Checks Covered

- user-scoped declared learning preferences load/save
- user-scoped learner context/background load/save
- user-scoped learning-goal create/update/delete
- enum validation for declared preference fields
- student-role access for declared learning profile endpoints
- cross-user goal isolation (`404` on other-user goal mutate attempts)

Recommended focused run:

```bash
./.venv311/bin/pytest tests/test_step6_assistant_modes.py tests/test_step10_personalization.py tests/test_retriever_api.py tests/test_stepb_learning_profile_api.py tests/test_stepb_learning_profile_service.py
cd webui && npm run build
```

Step 12 runtime smoke check:

```bash
docker compose up --build -d
curl http://localhost:8000/api/health
```

## Visual Verification Process

1. Start the stack with `docker compose up --build`.
2. Open the current app and the reference app side by side.
3. Compare the shell first: top bar height, sidebar width, content centering, and bottom composer placement.
4. Compare state styling next: neutral hover, active chat row, disabled controls, menus, dialogs, and empty states.
5. Compare typography and spacing in assistant markdown, user bubbles, table headers, dialogs, and tab navigation.
6. Iterate on any mismatch before calling Step 7 complete.

## Side-by-Side Checklist

- Sidebar proportions, internal padding, and bottom user row match the reference closely.
- Chat layout width and conversation centering match the reference closely.
- Composer width, border, radius, controls, and fixed positioning match the reference closely.
- Assistant messages, user messages, attachment chips, and markdown blocks share the same visual language.
- Sources trigger and sources panel match the reference popover treatment.
- Library summary, table, upload dialog, and action controls feel like the same product.
- Preferences modal, tabs, archive rows, and settings fields follow the same modal design system.

## Interaction Regression Checklist

- Create, open, rename, archive, download, and delete chats.
- Open Library, upload files, toggle file state, and delete files.
- Open `Preferences -> Filter` and confirm global file and tag toggles persist.
- Open a chat menu filter dialog and confirm chat-specific toggles persist.
- Disable a tag globally and confirm the same tag becomes locked in chat scope.
- Disable a file globally and confirm chat scope shows it as unavailable.
- Send messages with and without attachments.
- Change assistant mode from the composer.
- Send at least one message with `thinking` mode and confirm only the final answer appears in the chat UI.
- Open and close sources panels.
- Open Info, Help, Preferences, and Archive-related dialogs.
- Confirm archived chat actions still work.

## Known Styling Decisions

- The implementation keeps the existing React architecture and current product functionality intact instead of copying the reference code.
- A single tokenized stylesheet is still used, but the rules are grouped by shared UI patterns to keep the restyle maintainable.
- Desktop parity is the main target; mobile behavior is preserved with compact responsive fallbacks rather than a separate design.

## Debugging Notes

- If startup fails before the API boots, confirm `alembic` is installed in the active environment.
- If image attachments fail, verify Tesseract is available in the embedder container.
- If attachment context seems missing, inspect the retriever logs and confirm `ATTACHMENT_MAX_TOTAL_CHARS` is not overly restrictive.
- If thinking mode fails, inspect retriever logs for the planning or draft debug entries and confirm the fallback simple response path was used.
- If the Step 7 visuals look inconsistent, inspect the fixed composer width, sidebar padding, and modal variants first because they establish most of the reference rhythm.
