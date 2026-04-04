# Authentication

Step 8 adds provisioned authentication to the RAG system.

## Login

- Users sign in with `username` and `password`.
- There is no public signup flow.
- Provisioned users come from [`users.json`](/Users/rknstlr/Workspace/TEST/learning-rag/users.json).

## Roles

- `admin`: full platform access, user management, global learning-path authoring, and unrestricted library management.
- `user`: standard app access, user-scoped learning-path authoring, and own-resource management.
- `student`: restricted role for learning consumption flows.

Student restrictions in Step A:

- cannot create or use normal chats
- cannot create or use GPTs
- cannot author learning paths, modules, or lessons
- can read visible learning paths for future learning-mode consumption

## Password Handling

- Passwords are never stored in plaintext.
- Hashing uses Argon2 over `password + PASSWORD_SALT`.
- Default bootstrap password is `Passw0rd!`.

## Sessions

- Auth uses JWT bearer tokens.
- Default token lifetime is 2 hours.
- Active sessions refresh after 1 hour of activity.
- Sessions hard-expire after 12 hours total and then require login again.
- Logout revokes the server-side session record and clears the client token.

## Forced Password Change

- Bootstrap users and newly created admin-managed users start with `force_password_change = true`.
- Those users can call `/api/auth/me`, `/api/auth/logout`, and `/api/auth/change-password`.
- All app routes remain blocked until the password is changed successfully.
