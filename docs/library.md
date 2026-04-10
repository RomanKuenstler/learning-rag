# Library

## Purpose

Step 4 adds a dedicated Library page to the web UI for managing embedded knowledge files without leaving the app shell.

## Page Behavior

- the sidebar stays visible while the Library page is open
- `Library` sits directly below `New chat`
- selecting `New chat` or a chat item leaves the Library view and opens the normal chat screen
- the Library view refreshes after uploads, enable or disable changes, and deletions
- by default, the table shows only global files and the current user's own files
- a bottom switch controls whether files owned by other users are shown in the table

## File Table Columns

Each row shows:

- file name
- status
- tags
- size
- chunks
- extension
- embedded
- updated
- actions

Each row also shows ownership metadata in the name cell:

- `global` badge for system-wide files
- `owned by you` badge for the uploader
- owner display name or username for other-user files
- `admin upload` marker when a global file came from an admin upload flow

## Ownership and Origin Rules

- `system_data` global files are files placed directly in `data/`
- `admin_upload` global files are files uploaded by users with role `admin`
- `user_upload` files are owned by the uploader and are not global

Default file enablement:

- global files are enabled by default for every user
- user-owned files are enabled by default for the owner
- user-owned files are disabled by default for every other user

## Status Semantics

- `Active`: file is enabled and can contribute chunks to retrieval
- `Disabled`: file remains indexed but is ignored during retrieval

## Disable vs Delete

Disable:

- keeps the physical file in `data/`
- keeps Postgres metadata and chunk rows
- keeps Qdrant vectors
- blocks the file from retrieval results

Permission rules:

- normal users cannot disable global files
- normal users cannot delete global files
- normal users cannot delete files owned by another user
- admins can disable or delete any file

Delete:

- removes the physical file from `data/`
- removes Postgres metadata and chunk rows
- removes Qdrant vectors
- removes stored tags from `tags.json`

## Extension Colors

- `.pdf` and `.epub`: red badge
- `.txt` and `.md`: grey badge
- `.html` and `.htm`: blue badge
