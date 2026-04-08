Phase 1: Rework courses into graph-based skilltree courses with schema v2, migration from linear paths, base skilltree UI, prerequisite logic, and node progress states

Work on the existing project and rework the current learning-path/course system into a graph-based skilltree course system.

Before making code changes, inspect the current codebase and current:
	•	courses/paths page
	•	course JSON schema and import/bootstrap flow
	•	existing learning path data model
	•	course table and detail pages
	•	learning page / Courses page UI
	•	current progress tracking
	•	KSA models
	•	existing course bootstrap from courses/ folder
	•	existing example course JSON files
	•	any sidebar/detail panel patterns already present

Objective

Transform the current course model from a mainly linear module/lesson structure into a graph-based skilltree structure that supports:
	•	nodes
	•	edges
	•	prerequisites
	•	multiple progression routes
	•	optional nodes
	•	parallel nodes
	•	node metadata
	•	node progress states
	•	side-panel detail display
	•	KSA-linked metadata
	•	migration from the old simple course format

This phase is the structural foundation. It must deliver a stable first version of the skilltree system before richer node behavior is added in later phases.

⸻

Important scope boundaries

This phase must include
	•	new course schema v2
	•	graph-based course structure
	•	migration or compatibility path from old linear course JSON
	•	node/edge persistence and import validation
	•	skilltree rendering on the Courses page or course detail page
	•	side panel with node details
	•	prerequisite logic
	•	node unlock logic
	•	progress states
	•	support for optional and parallel nodes
	•	KSA metadata on nodes

This phase must NOT yet include
	•	full quizzes/tests as node execution logic
	•	retrospective tests
	•	KSA mini-assessments inside nodes
	•	adaptive unlock logic
	•	remediation branches
	•	complex animated graph effects
	•	full learning-engine execution inside the tree

This is the structural and UX foundation.

⸻

Core design direction

Courses are no longer primarily:
	•	modules
	•	lessons
	•	strict order

They are now primarily:
	•	graph-based progression systems

Internally, treat them as a directed acyclic graph or equivalent learning graph structure, even if the user-facing language remains “skilltree”.

⸻

New course schema requirements

1. Introduce schema version 2

Add a new course/path JSON schema version for skilltree courses.

Recommended concept:
	•	schema_version: 2

The old course format must either:
	•	still be temporarily supported
	•	or be migrated/imported into the new graph format

Choose the safest maintainable path.

2. New top-level structure

A v2 course should support at minimum:
	•	id
	•	schema version
	•	title
	•	description
	•	scope
	•	owner metadata if needed
	•	status
	•	subject/domain
	•	optional difficulty / estimated duration
	•	chapters or grouping metadata
	•	nodes
	•	edges
	•	entry nodes
	•	completion rules
	•	visual layout metadata

Do not force everything into old module/lesson fields.

3. Nodes

Nodes are now the core unit of progression.

Each node should support at minimum:
	•	id
	•	title
	•	description
	•	type
	•	chapter/group id if applicable
	•	required vs optional
	•	prerequisites
	•	completion rule metadata
	•	KSA-linked metadata
	•	estimated effort/duration
	•	layout coordinates or layout hints
	•	display metadata where useful

For this phase, support at least these node types:
	•	learning_unit
	•	practice
	•	checkpoint
	•	review
	•	milestone

It is okay if some types behave similarly for now, but the type field must exist and be future-ready.

4. Edges / dependencies

Support explicit graph relationships.

At minimum support:
	•	requires_all
	•	requires_any
	•	optional/recommended relationships if cleanly possible

You may store these either:
	•	directly on nodes
	•	or in an explicit edges structure

Choose one clean model and keep it maintainable.

5. Optional and parallel nodes

The model must support:
	•	optional nodes
	•	nodes that can be completed in parallel
	•	branch merging

Do not reduce everything back to simple linear order indexes.

6. Chapters / groupings

Your screenshots suggest a hierarchy like:
	•	course
	•	chapter
	•	unit/node

Support at least one grouping layer such as chapter/cluster so the tree is not flat.

This grouping should help:
	•	visual layout
	•	right-side details
	•	progress summaries

7. KSA metadata on nodes

Each node should be able to declare what KSA areas it supports.

At minimum support metadata like:
	•	K/S/A dimension
	•	big-map topic
	•	optional subtopic
	•	optional target level
	•	optional contribution weight

This phase does not need full execution logic for KSA gain, but the metadata must exist.

⸻

Migration and compatibility requirements

1. Existing course JSON must be migrated or supported

The current course/path JSON format is too linear for the new design.

Implement either:
	•	migration to v2 skilltree JSON
	•	or compatibility import that converts old linear courses into a basic graph internally

Recommended behavior:
	•	old linear sequence becomes a simple linear graph
	•	each old lesson becomes a node
	•	dependencies are generated automatically
	•	grouping/chapter metadata is inferred from existing structure if possible

2. Existing system courses

Current existing courses in the system must continue to work after this phase.

Do not break the whole Courses page or bootstrap pipeline.

3. Export/update existing course files

If the project already stores course JSON in /courses, update or regenerate them so they become valid v2 skilltree-compatible files where appropriate.

Document clearly how migration/export works.

⸻

Backend requirements

1. Data model support

Update backend models/persistence so courses can support:
	•	graph structure
	•	node metadata
	•	edge/dependency logic
	•	progress states per user
	•	chapter/group structure
	•	KSA metadata

A normalized schema or a JSONB-backed course definition model is acceptable as long as it is maintainable and validated.

2. Validation

Add robust validation for schema v2 course JSON:
	•	required fields
	•	valid node ids
	•	valid dependency references
	•	no broken edge references
	•	valid node types
	•	valid completion metadata
	•	valid scope values
	•	valid KSA metadata shape

Also validate that the graph does not create obvious invalid structures such as impossible/self-loop references if your model should remain acyclic.

3. Progress state foundation

Add node-level progress state support.

At minimum support:
	•	locked
	•	available
	•	in_progress
	•	completed
	•	mastered
	•	optional_skipped

This phase must implement the foundation and basic computation of locked vs available based on dependencies.

4. Unlock logic

Implement basic unlock logic:
	•	entry nodes are available
	•	nodes become available when prerequisite rules are satisfied
	•	optional nodes do not block required progression unless explicitly configured

This logic must be deterministic and testable.

⸻

Frontend requirements

1. Replace linear course display with skilltree-style display

Rework the visual display of a course into a skilltree-like structure inspired by the provided examples.

Do not attempt a perfect game UI yet, but the result should clearly feel like:
	•	a branching progression tree
	•	not a plain table/list of lessons

2. Visual separation of logic vs layout

The frontend should render based on:
	•	graph/node logic
	•	stored layout metadata

Do not derive visual layout only from dependency logic.

3. Right-side node detail panel

When a node is selected, show a detail panel on the right side.

The panel should display at minimum:
	•	title
	•	description
	•	node type
	•	KSA metadata if present
	•	required/optional
	•	prerequisites
	•	current progress state
	•	estimated duration if available

4. Progress indicators

Show useful indicators for:
	•	completed nodes
	•	available nodes
	•	locked nodes
	•	optional nodes if relevant
	•	chapter or branch completion summaries where practical

5. Keep the UI stable and readable

You may use a graph visualization library if it fits cleanly, but do not overcomplicate the first version with heavy animation.

A pragmatic, readable, maintainable skilltree UI is better than a flashy but brittle one.

⸻

Completion logic requirements

1. Node completion semantics

Even if full execution is not implemented yet, each node should already support a completion mode field such as:
	•	lesson_complete
	•	manual
	•	practice_complete
	•	checkpoint_pass

The real behaviors can be richer later, but the schema should already allow this.

2. Branch and course completion

Implement a first-pass completion model:
	•	a branch is complete when all required nodes in it are complete
	•	a course is complete when all required nodes/branches are complete

Keep it deterministic and simple in this phase.

⸻

Architecture requirements

1. Keep skilltree logic separate from learning-engine execution

Do not mix:
	•	skilltree graph model
	•	learning chat execution
	•	quiz logic
	•	KSA assessment logic

This phase is about the course progression structure and UI.

2. Reusable graph components

Where practical, create reusable components/services for:
	•	node normalization
	•	graph validation
	•	unlock-state computation
	•	layout mapping
	•	node detail rendering

3. Future readiness

This phase must prepare for later phases that will add:
	•	richer node behaviors
	•	assessments
	•	KSA mini-checks
	•	retrospective logic
	•	adaptive unlocks

Do not hardcode assumptions that every node is just a lesson.

⸻

Validation requirements

This phase is not complete when the course schema changes and a graph renders vaguely.

It is complete only after the graph-based course system works end to end and has been checked, tested, and debugged where necessary.

Validate at minimum:
	1.	v2 course schema exists and validates correctly
	2.	old courses still load through migration or compatibility logic
	3.	old linear paths are converted into valid linear graphs
	4.	nodes and edges render in a skilltree-like layout
	5.	node detail side panel works
	6.	entry nodes are available
	7.	locked/available state logic works
	8.	prerequisite logic works
	9.	optional nodes are supported
	10.	parallel nodes are supported
	11.	basic branch/course completion logic works
	12.	KSA metadata is stored and displayed on nodes
	13.	no regression in course import/bootstrap
	14.	no regression in learning path/course pages

If issues are found:
	1.	identify root cause
	2.	debug and fix
	3.	rerun validation
	4.	update docs and changelog

⸻

Testing requirements

Update and/or add tests where practical for:
	•	schema v2 validation
	•	migration from old linear format
	•	dependency resolution
	•	unlock-state computation
	•	optional node handling
	•	branch completion
	•	node detail data mapping
	•	KSA metadata validation
	•	skilltree rendering data contracts

⸻

Documentation requirements

Update at minimum:
	•	README.md
	•	docs/learning.md
	•	docs/courses.md
	•	docs/api.md
	•	docs/architecture.md
	•	docs/testing.md
	•	changelog.md

Also document:
	•	schema v2 structure
	•	graph concepts
	•	node types
	•	dependency model
	•	migration/compatibility behavior
	•	progress states
	•	KSA metadata on nodes
	•	current limitations before richer node execution is added

⸻

Deliverable expectations

When finished:
	•	courses are represented as graph-based skilltree courses
	•	old linear courses still work through migration or compatibility
	•	the UI displays a skilltree-like course structure
	•	nodes have detail metadata and states
	•	prerequisite and unlock logic works
	•	KSA metadata is attached to nodes
	•	the implementation is clean and extensible
	•	tests/docs/changelog are updated
	•	the result has been verified and debugged if needed