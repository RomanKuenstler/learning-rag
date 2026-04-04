Step: Update library ownership and visibility rules for global/admin files vs user-owned files

Work on the existing project and implement this library-management behavior update carefully. Before making changes, inspect the current codebase and current library/file ownership, auth/role logic, file enable/disable logic, upload flow, filtering, and web UI library page behavior.

Objective

Update the library system so file ownership and access behavior works like this:

1. Global files

Files that are:
	•	placed directly in the data/ folder, or
	•	uploaded by users with the admin role

must be treated as global files.

Global files must:
	•	be visible as global/system-wide library knowledge
	•	not be possible to disable by normal users
	•	not be possible to delete by normal users

2. User-owned files

Files uploaded by a normal user must be treated as user-owned files.

For user-owned files:
	•	the owner should have them enabled by default
	•	all other users should have them disabled by default
	•	other users must not be able to delete them
	•	ownership and permissions must be enforced server-side

3. Library page visibility toggle

In the web UI library page, add a switcher at the bottom:
	•	label/behavior: show or hide other users’ files in the table
	•	default state: do not show other users’ files

This is a visibility toggle for the table display only. It must not change actual ownership or access rules.

Core business rules

Implement these rules exactly.

Rule A: Global file definition

A file is global if either:
	•	it was placed directly into the data/ folder by the system/admin flow, or
	•	it was uploaded through the UI/API by a user whose role is admin

Rule B: Global file protections

For normal users:
	•	global files cannot be disabled
	•	global files cannot be deleted

Admins may still manage global files according to existing admin permissions.

Rule C: User-owned file default enablement

When a normal user uploads a file:
	•	for the owner: enabled = true by default
	•	for all other users: enabled = false by default

This default behavior must be enforced in persistence and retrieval behavior, not only in UI.

Rule D: Other-user file delete restriction

A user must never be able to delete a file owned by another user unless the acting user is an admin.

Rule E: Other-user file visibility toggle in library page

The library page table should, by default, show:
	•	global files
	•	the current user’s own files

It should not show other users’ files by default.

If the bottom switcher is turned on, the table should additionally show other users’ files.

This toggle is only a UI visibility preference unless a clean persisted user preference already exists and can be reused safely.

Required implementation scope

1. Review current file ownership model

Inspect the current schema and logic for:
	•	file ownership
	•	file source/origin
	•	admin uploads
	•	direct data/ folder ingestion
	•	user-specific file enable/disable state
	•	library page listing
	•	delete permission checks

Then update the model cleanly.

2. Distinguish file origin and ownership clearly

The backend/data model must be able to distinguish at minimum:
	•	global/system file
	•	admin-uploaded global file
	•	user-owned file

If the current schema is not explicit enough, add the needed fields/migrations.

A clean model would likely need fields such as:
	•	owner_user_id nullable
	•	is_global
	•	source_origin or equivalent

Choose the cleanest maintainable design for the existing codebase.

3. Update file ingestion rules

When files are discovered in data/ directly:
	•	mark them as global/system-managed
	•	ensure they are treated as protected for non-admin users

When files are uploaded by admins:
	•	mark them as global
	•	ensure they are treated as protected for non-admin users

When files are uploaded by non-admin users:
	•	mark them as user-owned
	•	default-enable them for the owner only
	•	default-disable them for all other users

4. Update user-specific file enable/disable defaults

Review the current user file settings/default logic and update it so:
	•	global files are effectively enabled/available globally and cannot be user-disabled if the acting user is a normal user
	•	user-owned files are enabled by default for the owner
	•	user-owned files are disabled by default for everyone else

Be careful here:
	•	this must work correctly for existing users
	•	this must work correctly for newly created users
	•	this must work correctly for newly uploaded files

5. Update retrieval behavior

Ensure retrieval respects the new rules.

That means:
	•	if a file is disabled for a user, it is not allowed as a retrieval source
	•	user-owned files uploaded by someone else should remain excluded by default unless later enabled by a supported mechanism
	•	global files should remain available according to the intended global behavior

Do not break existing filtering logic for:
	•	tag filtering
	•	chat-specific file filtering
	•	GPT-specific filtering if applicable

6. Update permission checks

Enforce permissions server-side for:
	•	disabling files
	•	deleting files
	•	managing files

At minimum:
	•	normal users cannot disable global files
	•	normal users cannot delete global files
	•	normal users cannot delete files owned by other users
	•	admins can still manage all files according to current admin rules

Do not rely on frontend hiding only.

7. Update library listing APIs

Update the library listing behavior so it can support:
	•	default view without other users’ files
	•	optional inclusion of other users’ files when requested by the UI toggle

A clean approach is to support a query parameter or equivalent such as:
	•	include other users’ files = true/false

The backend must still enforce visibility and permission rules correctly.

8. Update web UI library page

At the bottom of the library page, add a switcher to control whether other users’ files are shown in the table.

Requirements:
	•	default state: off
	•	when off:
	•	hide other users’ files
	•	when on:
	•	show other users’ files too
	•	global files and own files should still appear normally
	•	the UI must clearly reflect which files are:
	•	global/system/admin-managed
	•	owned by the current user
	•	owned by another user

9. Improve table metadata where useful

Where it helps clarity, update the library table to show ownership/source information in a clean way.

Useful examples:
	•	owner display name or username
	•	badge for global
	•	badge for admin
	•	badge or metadata for owned by you

Do this only if it fits cleanly with the current UI.

10. Keep current UX stable

Do not redesign the whole library page in this step.

Only update what is needed for:
	•	ownership visibility
	•	protections
	•	new bottom switcher behavior

Data model / migration requirements

Review and update schema as needed.

The implementation likely needs enough structure to support:
	•	explicit file ownership
	•	explicit global/system/admin-managed distinction
	•	correct default enablement behavior per user
	•	stable permission checks

Add migrations if needed. Do not rely on ad-hoc inferred behavior if the schema is too weak.

Also ensure existing data can be handled sensibly:
	•	existing system/global files should be classified correctly
	•	existing uploaded files should be mapped to owner/global behavior correctly where possible

API requirements

Update backend APIs as needed for:
	•	library file listing with/without other users’ files
	•	file action permission enforcement
	•	correct ownership-aware responses

Where useful, return metadata such as:
	•	owner_user_id
	•	owner_username
	•	owner_displayname
	•	is_global
	•	is_owned_by_current_user
	•	can_disable
	•	can_delete

Only expose what is useful and safe.

Frontend requirements

Update the library page so it:
	•	defaults to hiding other users’ files
	•	has a bottom switcher to show/hide other users’ files
	•	updates the table correctly when toggled
	•	disables or hides actions the current user is not allowed to perform
	•	still relies on backend enforcement as the source of truth

The UI should make it clear when:
	•	a file is global/system/admin-managed
	•	a file belongs to the current user
	•	a file belongs to another user

Validation requirements

This step is not complete when the UI toggle exists or some permissions are hidden.

It is complete only after the new ownership and access rules are correctly enforced in backend behavior, retrieval behavior, and UI behavior.

Validate at minimum:
	1.	files placed directly in data/ are treated as global
	2.	files uploaded by admins are treated as global
	3.	normal users cannot disable global files
	4.	normal users cannot delete global files
	5.	normal users can upload files that become owner-enabled by default
	6.	those user-owned files are disabled by default for other users
	7.	other users cannot delete those files
	8.	admins can still manage files according to admin permissions
	9.	retrieval respects the new default enablement rules
	10.	library page hides other users’ files by default
	11.	library page shows other users’ files when the switcher is enabled
	12.	actions in the UI reflect permissions correctly
	13.	backend rejects unauthorized file actions even if called directly
	14.	no regression from previous steps

If issues are found:
	1.	identify root cause
	2.	debug and fix
	3.	rerun validation
	4.	update docs and changelog

Testing requirements

Update and/or add tests where practical for:
	•	file ownership classification
	•	global file detection
	•	admin-uploaded file behavior
	•	user-owned file default enablement
	•	cross-user visibility rules
	•	delete permission enforcement
	•	disable permission enforcement
	•	retrieval exclusion for default-disabled other-user files
	•	library listing with visibility toggle parameter
	•	frontend library toggle behavior

Documentation requirements

Update at minimum:
	•	README.md
	•	docs/library.md
	•	docs/api.md
	•	docs/testing.md
	•	docs/architecture.md
	•	changelog.md

Also document:
	•	what counts as a global file
	•	ownership/default enablement behavior
	•	visibility rules on the library page
	•	permission rules for disable/delete
	•	any migration/data-backfill behavior

Deliverable expectations

When finished:
	•	global/admin/system files are protected from normal-user disable/delete
	•	user-owned uploads are enabled by default only for the owner
	•	user-owned uploads are disabled by default for all other users
	•	the library page hides other users’ files by default
	•	the library page can optionally show other users’ files via the new bottom switcher
	•	retrieval respects the new ownership-based enablement behavior
	•	backend enforcement is correct
	•	tests/docs/changelog are updated
	•	the result has been verified and debugged if needed