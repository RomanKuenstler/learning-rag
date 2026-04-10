Step B: Add the learning profile and declared learning preferences system

Work on the existing project and implement the declared learning profile and learning preferences layer for the new learning system.

This step is about the information a learner explicitly provides about themselves and how they prefer to learn. It is not the adaptive diagnostic engine yet. Do not implement the psychometric/diagnostic system in this step. That belongs to Step B.1.

Before making code changes, inspect the current codebase and current user model, auth/roles, profile/personalization/settings structures, learning foundation from Step A, and current web UI preferences/profile flows.

Objective

Implement a user-scoped learning profile and declared learning preferences system that will later be used by the learning assistant mode.

This step must provide:
	•	persistent learner profile data
	•	persistent declared learning preferences
	•	structured learning goals
	•	clean API and UI for managing these values
	•	integration-ready data for future learning chats

This step is the explicit/self-declared learner profile layer.

Important scope boundaries

This step must include
	•	learner profile data
	•	declared learning preferences
	•	structured learning goals
	•	user-scoped persistence
	•	edit/view UI
	•	backend/API support
	•	validation
	•	future compatibility with learning chats

This step must NOT include yet
	•	LAA / MOA / LTA diagnostic engine
	•	psychometric scoring
	•	dynamic/adaptive question flows
	•	charts/visual diagnostics
	•	real-time feedback system
	•	explanation feedback loop
	•	quiz/test generation
	•	progress/mastery engine

Those belong to later learning steps.

Core product idea

This step answers:

“What does the learner explicitly tell the system about themselves and how they want to learn?”

It should store the base learner context that later learning mode will use before any adaptive refinement is added.

Required data areas

Implement three main data groups.

1. Declared learning preferences

Add structured user-scoped learning preferences at minimum for:
	•	preferred pace
	•	slow
	•	balanced
	•	fast
	•	explanation depth
	•	concise
	•	balanced
	•	detailed
	•	examples vs theory
	•	more_examples
	•	balanced
	•	more_theory
	•	structure preference
	•	more_structured
	•	balanced
	•	more_conversational
	•	quiz/checkpoint frequency
	•	low
	•	medium
	•	high
	•	encouragement level
	•	low
	•	balanced
	•	high
	•	guidance level
	•	step_by_step
	•	balanced
	•	more_independent
	•	recap frequency
	•	low
	•	medium
	•	high
	•	preferred learning format
	•	reading
	•	dialogue
	•	exercises
	•	mixed
	•	optional custom note
	•	free text like:
	•	“Anything that helps the assistant teach you better?”

Choose the cleanest field naming, but keep the meaning explicit.

2. Learner background / learning context

Add a learner profile area that stores useful contextual information for teaching.

At minimum support:
	•	education background
	•	current skill areas
	•	interests
	•	professional context if useful
	•	current reason for learning
	•	preferred form of address if this is not already cleanly available elsewhere
	•	optional personal learning context notes

Do not duplicate existing profile data unnecessarily if a clean reuse path already exists, but keep the learning-specific context clearly separated where appropriate.

3. Learning goals

Add structured learning-goal support.

At minimum support:
	•	target topic / subject
	•	reason for learning
	•	target level or desired level
	•	optional deadline
	•	optional priority
	•	optional notes

This should be user-scoped and editable.

A learner may have one current active learning goal or a small set of goals depending on the cleanest design, but keep the implementation simple and maintainable.

Architectural guidance

1. Keep Step B separate from personalization and diagnostics

This learning-preference system is related to personalization, but it should not be mixed carelessly with the existing generic assistant personalization system.

Keep it conceptually separate because:
	•	generic personalization affects all assistant behavior
	•	learning preferences affect future learning mode specifically

Also keep it separate from Step B.1 diagnostics:
	•	Step B = explicit learner input
	•	Step B.1 = diagnosed/inferred learning profile

2. Build for future composition

The later learning assistant will combine:
	•	Step B declared preferences
	•	Step B.1 diagnostics
	•	later real-time learning-state feedback
	•	later progress/mastery data

Design this step so it can become part of a future unified learning_context without refactoring everything later.

3. Keep the model user-scoped

This data is per user.

It must:
	•	persist per user
	•	not leak across users
	•	respect auth and role boundaries

Backend requirements

1. Data model

Add backend models/tables/schemas for:
	•	user learning preferences
	•	learner background / learning profile
	•	learning goals

You may choose either:
	•	one normalized structure, or
	•	a small number of clearly separated tables

Choose the cleanest maintainable design for the current codebase.

The model should be ready for future extension without forcing a redesign.

2. API

Add clean authenticated APIs for managing this data.

At minimum support:
	•	get current user learning profile/preferences/goals
	•	create/update learning profile/preferences/goals
	•	partial updates where appropriate

The API should be typed, validated, and consistent with the rest of the project.

3. Permissions

This data is user-owned.

Rules:
	•	a user can read/update their own learning profile/preferences/goals
	•	admins do not need broad edit access unless the current architecture strongly requires admin read-only visibility
	•	students should be able to use this feature, because it is part of their learning setup

4. Validation

Validate all enum-like fields and text inputs carefully.

Examples:
	•	only valid choice values accepted
	•	lengths constrained
	•	optional text fields sanitized appropriately
	•	deadlines validated if included

Frontend requirements

1. Add a learning profile/preferences UI

Create or extend the web UI so users can view and edit their declared learning profile and learning preferences.

This should fit naturally into the learning product area.

A good approach is a dedicated learning preferences/profile page or section, not hidden inside unrelated generic settings.

2. UI sections

The UI should clearly separate:
	•	Learning Preferences
	•	Learning Context / Background
	•	Learning Goals

3. Suggested form contents

Learning Preferences
Use dropdowns, segmented controls, radio groups, or similar clean controls for:
	•	pace
	•	depth
	•	examples vs theory
	•	structure
	•	quiz frequency
	•	encouragement
	•	guidance
	•	recap
	•	preferred format

Learning Context / Background
Use a mix of:
	•	text inputs
	•	tag/chip inputs
	•	textareas
	•	select fields

to collect:
	•	education background
	•	skills
	•	interests
	•	professional context
	•	reason for learning

Learning Goals
Use structured form fields for:
	•	target topic
	•	target level
	•	reason
	•	optional deadline
	•	optional priority
	•	notes

4. Save behavior

The UI should:
	•	load current values
	•	support edit/update
	•	validate user input
	•	persist changes cleanly
	•	reflect saved state clearly

Do not overbuild a wizard unless it truly fits the current UI architecture better.

Integration requirements

1. Prepare for future learning assistant usage

This step should make it easy for the later learning assistant mode to load and use the declared learner profile.

The resulting data should be straightforward to pass into a future prompt builder or orchestration layer.

2. Do not yet force learning chats to use it

The full learning-chat orchestration is not part of this step yet.

Just make sure the data model and APIs are ready.

Suggested data model direction

A clean structure might include something like:
	•	user_learning_preferences
	•	user_learning_profile
	•	user_learning_goals

Or an equivalent structure that remains explicit and maintainable.

Support future extension for:
	•	diagnostic results
	•	observed learning profile
	•	real-time feedback
	•	progress/mastery

Validation requirements

This step is not complete when the tables and forms merely exist.

It is complete only after the declared learning profile system works end to end and is ready for future learning mode integration.

Validate at minimum:
	1.	users can load their learning preferences
	2.	users can save/update their learning preferences
	3.	users can save/update learner background/context
	4.	users can save/update learning goals
	5.	validation works correctly
	6.	the data is user-scoped correctly
	7.	students can use this feature
	8.	data does not leak across users
	9.	the UI behaves cleanly
	10.	the system remains compatible with Step A learning foundations
	11.	no regression from previous steps

If issues are found:
	1.	identify root cause
	2.	debug and fix
	3.	rerun validation
	4.	update docs and changelog

Testing requirements

Update and/or add tests where practical for:
	•	learning preference persistence
	•	learner profile persistence
	•	learning goal persistence
	•	enum validation
	•	auth/user scoping
	•	API request/response validation
	•	frontend save/load behavior

Documentation requirements

Update at minimum:
	•	README.md
	•	docs/architecture.md
	•	docs/api.md
	•	docs/testing.md
	•	docs/setup.md
	•	changelog.md

Also document:
	•	what Step B stores
	•	difference between Step B and Step B.1
	•	learning preferences fields
	•	learner background/context fields
	•	learning goals fields
	•	current limitations before diagnostics are added

Deliverable expectations

When finished:
	•	the project supports user-scoped declared learning preferences
	•	the project supports learner background/context data
	•	the project supports structured learning goals
	•	the API and UI for this are implemented cleanly
	•	the implementation is ready for later learning assistant integration
	•	the code is maintainable
	•	tests/docs/changelog are updated
	•	the result has been verified and debugged if needed