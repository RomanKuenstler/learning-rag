Step A: Add the learning foundation layer — student role, learning path schema, permissions, and basic learning-path CRUD

Work on the existing project and implement the foundation layer for learning mode. This step is not the full teaching workflow yet. Its purpose is to add the core domain model, permissions, and initial CRUD so later steps can build learning preferences, learning chats, progress, and assessments on top of it.

Before making code changes, inspect the current codebase and current auth/roles, chats, GPTs, settings, filtering, library/file ownership, and web UI navigation. Reuse the existing architecture where it is clean, but do not hesitate to refactor if needed for maintainability.

Objective

Introduce the core learning entities and permissions needed for future learning mode, including:
	•	new user role: student
	•	learning path data model
	•	ordered module and lesson structure
	•	global vs user-scoped learning paths
	•	basic CRUD for learning paths
	•	learning-path source scoping rules
	•	a new chat type reserved for future learning chats
	•	student restrictions:
	•	students can only use learning mode in the future
	•	for this step, students must not be able to create/use normal unrestricted chats
	•	no full teaching orchestration yet
	•	no quiz system yet
	•	no full progress/mastery engine yet

This step should leave the project ready for the next learning-related steps.

Important product decisions already chosen

Implement these rules exactly:

1. Roles

Supported roles must now include:
	•	admin
	•	user
	•	student

2. Student behavior

Students are a restricted role.

Students:
	•	are intended to use only learning mode
	•	should not have access to normal unrestricted assistant modes/chats
	•	should not create or use normal chats like user and admin
	•	should be able to access learning-related functionality only

For this step, since full learning chat orchestration is not implemented yet, build the permissions and UI/backend restrictions so students are prepared for that path.

3. Learning path authoring

For the first version:
	•	admin and user can create learning paths
	•	student cannot create learning paths

4. Learning path scope

Learning paths can be:
	•	global
	•	user-scoped

Global learning paths:
	•	system/admin-provided
	•	not editable/deletable by normal users
	•	not editable/deletable by students
	•	editable/deletable by admins only

User-scoped learning paths:
	•	owned by the creating user
	•	visible only to the owner for now
	•	editable/deletable only by the owner or an admin

5. Learning mode grounding

Future learning mode must be grounded in allowed RAG knowledge only.

That means the learning-path foundation must include explicit source scoping rules so a learning path can define what knowledge is allowed for teaching later.

Support source scoping through:
	•	allowed files
	•	allowed tags
	•	or both

Design this cleanly now, even if the full learning chat retrieval enforcement comes in a later step.

6. Learning structure

A learning path must not be just a free-form text blob.

It must support:
	•	ordered modules
	•	ordered lessons/topics inside modules
	•	learning objectives
	•	source scope / allowed knowledge references
	•	future progress linkage

This step is only Step A

Do not implement yet:
	•	full learning assistant mode orchestration
	•	quiz/test generation
	•	mastery tracking
	•	adaptive teaching logic
	•	learning dashboard
	•	student-authored learning paths
	•	assignment workflows
	•	full progress engine

You may add schema hooks/fields that make later steps easier, but do not try to implement the whole learning system now.

Required domain model

Implement a clean backend model for learning foundations.

1. Learning paths

A learning path should support at minimum:
	•	id
	•	owner scope:
	•	global
	•	user-owned
	•	owner user id nullable where appropriate
	•	title
	•	description
	•	subject/domain if useful
	•	difficulty level if useful
	•	estimated duration if useful
	•	status:
	•	draft
	•	published
	•	archived
	•	created_at
	•	updated_at

Choose the cleanest maintainable schema for the existing project.

2. Modules

A learning path contains ordered modules.

A module should support at minimum:
	•	id
	•	learning_path_id
	•	order_index
	•	title
	•	description
	•	learning objectives
	•	created_at
	•	updated_at

3. Lessons

A module contains ordered lessons/topics.

A lesson should support at minimum:
	•	id
	•	module_id
	•	order_index
	•	title
	•	description
	•	objective(s)
	•	optional notes / teaching intent
	•	created_at
	•	updated_at

4. Learning-path source scoping

Each learning path and/or lesson/module must be able to define what RAG knowledge is allowed.

Support clean storage for:
	•	allowed file references
	•	allowed tags

This can be implemented at path level first if that is the cleanest first version, but the design should not block future lesson-level refinement.

Recommended minimal first version:
	•	learning path source rules at path level
	•	path can reference allowed files and allowed tags

5. Learning chat type foundation

Add a clean concept for a future learning chat.

For this step:
	•	add a chat type or equivalent discriminator such as:
	•	normal
	•	gpt
	•	learning
	•	add the structural support needed so future learning chats can be linked to exactly one learning path

Do not implement the full learning assistant flow yet, but make sure the schema and architecture support it.

Permissions and access rules

Implement server-side enforcement for all learning-path actions.

Admin

Admins can:
	•	create global learning paths
	•	edit/delete global learning paths
	•	create user-scoped learning paths
	•	edit/delete any learning path

User

Normal users can:
	•	create user-scoped learning paths
	•	edit/delete their own learning paths
	•	view their own learning paths
	•	view global learning paths if visible/available in the product flow

Users cannot:
	•	edit/delete global learning paths
	•	edit/delete another user’s learning paths

Student

Students cannot:
	•	create learning paths
	•	edit learning paths
	•	delete learning paths
	•	create/use normal unrestricted chats

Students should only be prepared for learning consumption flows.

For this step, they may be allowed to read available learning paths if the UI/API design needs it, but not author them.

Backend/API requirements

Add the backend/API foundation for learning paths.

Implement clean endpoints for at minimum:

Learning paths
	•	list learning paths visible to the current user
	•	create learning path
	•	get learning path details
	•	update learning path
	•	delete learning path

Modules
	•	create module
	•	update module
	•	delete module
	•	reorder modules if that fits cleanly

Lessons
	•	create lesson
	•	update lesson
	•	delete lesson
	•	reorder lessons if that fits cleanly

Source scoping

Support CRUD or update operations for:
	•	allowed files
	•	allowed tags

The API design should be typed, validated, and consistent with the existing project style.

Do not expose unsafe cross-user access.

Web UI requirements

Add the minimum UI needed to manage learning paths in this step.

Do not try to build the full future learning experience yet.

1. Navigation

Add an entry point for learning paths in the web UI navigation where it fits best with the current design.

This should:
	•	be visible for admin and user
	•	be hidden or read-only for student depending on the UX you implement
	•	fit the current design system

2. Learning path list page

Create a page to list learning paths.

It should support at minimum:
	•	global learning paths
	•	owned learning paths
	•	clear indication of scope/ownership
	•	create button for allowed roles
	•	edit/delete actions where allowed

3. Learning path create/edit page

Create a page or editor flow for creating and editing a learning path.

It should support:
	•	title
	•	description
	•	basic metadata if included
	•	ordered modules
	•	ordered lessons
	•	allowed files
	•	allowed tags
	•	save/update

Keep the UI practical and maintainable. It does not need to be extremely polished in this step, but it should be usable and consistent.

4. Student restrictions in UI

Students must not see normal chat functionality as if they could use it unrestricted.

For this step:
	•	hide or disable normal chat creation and normal assistant-mode UI for students where appropriate
	•	do not rely on frontend hiding alone; backend must enforce restrictions too

Data model and migration requirements

Add proper migrations for all schema changes.

Review the existing auth/user/chat schema and update it cleanly to support:
	•	new role student
	•	learning paths
	•	modules
	•	lessons
	•	source scoping
	•	future learning chats

If existing enums or role validation currently assume only admin and user, update them carefully.

Make sure migrations are production-safe and consistent with the existing migration strategy.

Architecture requirements

1. Keep the design extensible

This step must prepare for future steps:
	•	learning preferences
	•	learning chats
	•	progress tracking
	•	quizzes/tests
	•	adaptive tutoring

Do not overbuild those features now, but design the foundation so they can be added cleanly later.

2. Clean separation

Keep learning-specific code separate from normal chat/GPT code where reasonable.

Recommended separation areas:
	•	learning schemas/models
	•	learning routes
	•	learning services
	•	learning repositories/data access
	•	learning UI pages/components

3. Avoid overloading existing chat/GPT logic

Do not force learning paths into the GPT system or normal chat system in a hacky way.
Learning is its own domain concept.

Student restriction implementation requirements

Implement the first part of student restriction behavior now.

At minimum:

Backend
	•	students cannot create normal chats
	•	students cannot use normal assistant modes
	•	students cannot create GPTs
	•	students cannot access authoring endpoints they should not have

Frontend
	•	hide or disable normal chat/GPT authoring flows for students
	•	route students toward learning-only relevant pages
	•	keep UX clear and not misleading

This can be a minimal but correct first restriction pass. Full learning-chat UX comes later.

Validation requirements

This step is not complete when the tables and endpoints merely exist.

It is complete only after the new domain model, permissions, and UI flows have been checked, tested, and debugged where necessary.

Validate at minimum:
	1.	role student exists and is handled correctly
	2.	existing auth/login/user management still works
	3.	admins can create/edit/delete global learning paths
	4.	users can create/edit/delete their own learning paths
	5.	users cannot edit/delete global learning paths
	6.	users cannot edit/delete another user’s learning paths
	7.	students cannot create/edit/delete learning paths
	8.	learning path CRUD works end to end
	9.	module creation/edit/order works
	10.	lesson creation/edit/order works
	11.	allowed files and tags can be stored on learning paths
	12.	normal chat access is restricted correctly for students
	13.	normal assistant modes are not usable by students
	14.	GPT creation/use restrictions for students are enforced as intended
	15.	no regression from previous steps

If issues are found:
	1.	identify root cause
	2.	debug and fix
	3.	rerun validation
	4.	update docs and changelog

Testing requirements

Update and/or add tests where practical for:
	•	role validation with student
	•	learning path CRUD permissions
	•	module CRUD/reordering
	•	lesson CRUD/reordering
	•	allowed file/tag source scoping persistence
	•	student restriction rules
	•	admin vs user vs student authorization
	•	migration coverage for new tables/role changes
	•	API validation for learning endpoints

Documentation requirements

Update at minimum:
	•	README.md
	•	docs/architecture.md
	•	docs/api.md
	•	docs/testing.md
	•	docs/setup.md
	•	docs/authentication.md
	•	changelog.md

Also document:
	•	the new student role
	•	learning path concepts
	•	global vs user-scoped learning paths
	•	module and lesson structure
	•	source scoping with files/tags
	•	current limitations of Step A
	•	what later learning steps will build on top of this

Deliverable expectations

When finished:
	•	the project supports the new student role
	•	the project has a clean learning-path foundation
	•	learning paths support ordered modules and lessons
	•	learning paths can define allowed files/tags for future grounded teaching
	•	learning path CRUD exists with correct permissions
	•	the code is clean and maintainable
	•	student restrictions are enforced correctly for this stage
	•	migrations/tests/docs/changelog are updated
	•	the result has been verified and debugged if needed