Step: Move learning paths to a dedicated Courses page, add course JSON import/bootstrap, filtering/sorting, template download, and KSA tab

Work on the existing project and implement this learning/courses management update carefully. Before making code changes, inspect the current codebase and current learning page, learning-path CRUD, Step A/Step B/Step B.1 learning structures, sidebar/navigation, file-upload dialog patterns from the library page, permissions, and backend bootstrap flows such as users.json.

Objective

Refactor the current learning-path UI and backend so that:
	1.	learning paths/courses are moved from the current Learning page tab into a dedicated Courses page
	2.	the sidebar gets a new nav link:
	•	directly below Learning
	•	label: Courses
	3.	the Courses page supports:
	•	course table
	•	sorting
	•	filtering
	•	adding course JSON files via dialog
	•	downloading a JSON template file
	4.	the project gets a courses/ folder for course definition .json files
	5.	course JSON files placed in that folder are automatically validated and bootstrapped into the system, similar in spirit to users.json
	6.	existing learning paths/courses in the system get corresponding JSON files created in that folder
	7.	the old paths tab is removed from the Learning page
	8.	a new Learning page tab called KSA (Knowledge Skills Abilities) is added with dummy placeholder content for now

Important scope rules

This step must include
	•	dedicated Courses page
	•	sidebar navigation update
	•	course table filtering/sorting
	•	backend JSON schema validation for course files
	•	bootstrap/import from courses/ folder
	•	upload dialog for up to 5 course JSON files
	•	custom-styled scope dropdown in dialog
	•	template JSON download
	•	creation of JSON files for existing learning paths/courses
	•	new KSA tab with placeholder content

This step must NOT include
	•	full KSA functionality
	•	redesign of the full learning engine
	•	unrelated learning chat logic changes
	•	unrelated library system redesign
	•	a generic file uploader beyond what is needed here

Core product behavior

1. Courses become their own page

The current “paths” functionality in the Learning page must move into a dedicated Courses page.

2. Sidebar update

Add a new nav link in the side navigation:
	•	below Learning
	•	label: Courses

It should fit the current UI design system and active-state behavior.

3. Learning page update

Remove the existing paths tab from the Learning page.

Add a new tab:
	•	KSA

For now:
	•	insert dummy/placeholder content only
	•	make it visually consistent
	•	do not implement real KSA logic yet

Backend and data model requirements

1. Introduce courses/ folder bootstrap

Add a project folder such as:

/courses

In this folder:
	•	one .json file represents one course / learning path
	•	these files are treated as declarative course definitions
	•	on startup or bootstrap sync, the system should scan this folder
	•	valid files should be created or synced into the system

This should work similarly in spirit to users.json, but it should remain cleanly designed for course data.

2. Existing courses must get JSON files

For the existing learning paths/courses already present in the system:
	•	create corresponding .json files in the courses/ folder
	•	the exported/generated JSON should match the new course schema
	•	this should become the canonical file representation moving forward, as far as practical for this feature

Do this carefully so existing data is not lost.

3. Course JSON schema

Define and implement a clear JSON schema for course files.

A course JSON file should support at minimum:
	•	course/path id or stable identifier if appropriate
	•	title / name
	•	description
	•	scope
	•	global
	•	user
	•	owner information if needed for user-scoped courses
	•	status if needed
	•	modules
	•	lessons
	•	source scoping / allowed files / allowed tags if already part of the learning path model
	•	any existing learning-path metadata that should persist in JSON form

The exact structure should reflect the current learning-path model, not invent a completely unrelated model.

4. Validation

When new course JSON files are found:
	•	validate schema
	•	validate required fields
	•	validate nested structures (modules/lessons/etc.)
	•	validate allowed enum values such as scope
	•	reject invalid files
	•	do not create broken courses in the system

If invalid:
	•	log meaningful backend errors
	•	surface meaningful UI errors where the invalid file came from the upload flow

Do not silently ignore problems.

5. Sync/bootstrap behavior

Implement a clean bootstrap/import process for course files in /courses.

It should:
	•	scan files
	•	validate them
	•	create missing courses
	•	update existing courses cleanly if that is the chosen sync model
	•	avoid duplicate/broken creation
	•	document clearly how file-based course bootstrap behaves

Choose the cleanest maintainable approach for the current project.

Courses page requirements

1. Dedicated Courses page

Create a separate page for courses.

The page should contain:
	•	a table/list of courses
	•	filtering controls
	•	sorting controls
	•	download template button
	•	add paths button

The design should fit the current product style.

2. Course table contents

The Courses table should show meaningful columns. Choose the cleanest useful set based on the current data model.

Recommended columns:
	•	name/title
	•	description (truncated if needed)
	•	scope (global / user)
	•	owner
	•	status
	•	number of modules
	•	number of lessons
	•	updated date
	•	maybe source info or tags if useful
	•	actions if actions already exist or fit cleanly

Do not overload the table, but make it useful.

3. Sorting

Add good practical sorting options.

Recommended sorting options:
	•	name A–Z / Z–A
	•	newest updated
	•	oldest updated
	•	most modules
	•	most lessons
	•	global first / user first if useful

Choose a clean UI pattern for sorting, such as:
	•	a styled dropdown in the table toolbar
	•	or compact sort controls near filters

Do not use ugly browser-default controls if the project already has a styled pattern.

4. Filtering

Add useful filtering options.

Recommended filters:
	•	scope (global, user)
	•	owner (if visible and useful)
	•	status
	•	search by name/title
	•	maybe search by description
	•	maybe module/lesson count range only if it fits cleanly

Suggested layout:
	•	a compact filter/sort toolbar above the table
	•	search on the left or center
	•	filter controls grouped consistently
	•	responsive but desktop-first

Use the current design system.

Upload/add paths requirements

1. Add Paths button

Place a button on the right side below the courses table:
	•	label: Add Paths

2. Download template button

Place another button to the left of the Add Paths button:
	•	label: Download Template

When clicked:
	•	download a path-template.json or similarly named JSON template file
	•	this template must show all supported course/path JSON fields and options
	•	it should be realistic and useful, not a trivial stub

3. Add Paths dialog

Clicking Add Paths must open a dialog patterned after the library upload dialog.

The dialog should include:
	•	centered + Add Files button initially
	•	up to 5 .json files selectable
	•	action buttons:
	•	Cancel
	•	Add

After files are chosen:
	•	display each selected file in the dialog
	•	one per row
	•	next to each file, show a custom-styled dropdown for selecting scope:
	•	global
	•	user

Important:
	•	do not use ugly browser-default select styling
	•	use the project’s styled dropdown pattern/component

4. Upload limits

Users can select up to:
	•	5 .json files

Only valid JSON files should be accepted in this flow.

5. Add action behavior

When the user clicks Add:
	•	upload the JSON file(s)
	•	validate them
	•	apply chosen scope where appropriate
	•	create the course(s) only if valid
	•	return errors clearly for invalid files

The system must not create invalid courses.

Scope and permission requirements

1. Scope selection during upload

In the dialog, each selected file must get a scope dropdown:
	•	global
	•	user

Interpretation:
	•	global should only be allowed where user role/permissions allow it
	•	user creates a user-scoped course

If a non-admin user is not allowed to create global courses, enforce that:
	•	in backend validation
	•	and ideally in the UI too

Do not rely on frontend only.

2. File-based bootstrap and scope

For files placed directly in the /courses folder:
	•	determine how scope should be interpreted from the JSON content
	•	validate it
	•	if invalid or unauthorized for the bootstrap source model, handle clearly and document behavior

Choose a clean consistent rule and document it.

Existing course export/generation requirements

For existing learning paths/courses:
	•	generate matching JSON files in /courses
	•	the generated files should reflect the actual current stored structure
	•	they should be valid against the new course JSON schema
	•	do not lose path/module/lesson/source-scope information

If a migration/export step is needed, implement it cleanly and document it.

Error handling requirements

1. Backend validation errors

When JSON files are invalid:
	•	return detailed validation errors
	•	include enough information to identify which file failed and why
	•	log useful errors for folder-based bootstrap
	•	surface useful errors in the web UI for uploaded files

2. UI error display

For uploaded path JSON files:
	•	show validation errors in or near the dialog, or in a clean error state after submission
	•	do not fail silently
	•	do not close the dialog as if everything worked when some files failed

3. Partial success behavior

If multiple files are uploaded and some are valid while others are invalid:
	•	handle this intentionally
	•	document the behavior
	•	ideally allow valid files to succeed and invalid files to report errors clearly, unless transactionally all-or-nothing is cleaner for the current architecture

Choose the cleanest stable approach and document it.

KSA tab requirements

Add a new tab in the Learning page:
	•	label: KSA

For now:
	•	add placeholder/dummy content only
	•	keep it visually integrated
	•	make it clear this area exists but is not implemented yet

Do not implement real KSA functionality in this step.

Architecture requirements

1. Keep course file import cleanly separated

Do not bury course-file parsing/validation inside unrelated route code.

Recommended separation:
	•	course file schema
	•	course file parser/validator
	•	bootstrap/sync service
	•	API/service layer
	•	UI page/dialog components

2. Avoid duplication

Reuse patterns from:
	•	library upload dialog
	•	bootstrap/import logic
	•	validation approach
	•	sidebar routing/navigation

But do not copy-paste messy code.

3. Keep future learning steps in mind

The Courses page and course JSON format should remain compatible with future:
	•	learning chats
	•	progress tracking
	•	diagnostics
	•	KSA
	•	assignment systems
	•	adaptive engine work

Data model and migration requirements

Add migrations if needed for:
	•	explicit course/path scope handling improvements
	•	course ownership metadata
	•	any stable file-backed identifier needed for JSON synchronization
	•	any missing status/source metadata needed to support this feature cleanly

Do not create schema drift.

API requirements

Add/update APIs as needed for:
	•	listing courses with filtering/sorting
	•	uploading/importing course JSON files
	•	validating course JSON
	•	downloading template JSON
	•	maybe manual resync/import if needed
	•	retrieving metadata needed for the Courses table

Keep APIs typed, validated, and consistent with the rest of the project.

Validation requirements

This step is not complete when the new page exists and the buttons are visible.

It is complete only after the course management flow works end to end and has been checked, tested, and debugged where necessary.

Validate at minimum:
	1.	the new Courses nav link appears below Learning
	2.	the old paths tab is removed from Learning
	3.	the new KSA tab is added with placeholder content
	4.	the Courses page loads correctly
	5.	sorting works correctly
	6.	filtering works correctly
	7.	search works correctly if implemented
	8.	existing courses are represented as JSON files in /courses
	9.	valid course JSON files placed in /courses are created/synced correctly
	10.	invalid course JSON files in /courses produce useful errors/logs
	11.	Download Template downloads a useful valid template file
	12.	Add Paths dialog works
	13.	up to 5 JSON files can be selected
	14.	each selected file shows a scope dropdown
	15.	uploaded valid JSON files create courses correctly
	16.	invalid uploaded JSON files show useful errors
	17.	permissions around global/user scope are enforced correctly
	18.	no regression from previous learning features

If issues are found:
	1.	identify root cause
	2.	debug and fix
	3.	rerun validation
	4.	update docs and changelog

Testing requirements

Update and/or add tests where practical for:
	•	course JSON schema validation
	•	folder bootstrap import
	•	export/generation of existing courses to JSON
	•	upload validation
	•	scope handling and permission enforcement
	•	filtering and sorting behavior
	•	template generation/download
	•	Courses page UI behavior
	•	KSA tab presence

Documentation requirements

Update at minimum:
	•	README.md
	•	docs/learning.md
	•	docs/api.md
	•	docs/testing.md
	•	docs/setup.md
	•	docs/architecture.md
	•	changelog.md

Also document:
	•	the new Courses page
	•	course JSON schema
	•	/courses folder bootstrap behavior
	•	how existing courses are exported/generated
	•	validation rules
	•	upload flow
	•	template download behavior
	•	current placeholder nature of the KSA tab

Deliverable expectations

When finished:
	•	learning paths/courses are managed through a dedicated Courses page
	•	sidebar navigation includes Courses below Learning
	•	filtering and sorting work cleanly
	•	/courses folder bootstrap works
	•	existing courses have corresponding JSON files
	•	users can upload up to 5 course JSON files through the UI
	•	each uploaded file can be assigned a scope with a styled dropdown
	•	invalid JSON files are rejected with useful errors
	•	a downloadable course JSON template exists
	•	the Learning page has the new KSA placeholder tab
	•	the implementation is clean and maintainable
	•	tests/docs/changelog are updated
	•	the result has been verified and debugged if needed