Phase 3: Add dynamic progression logic, branch completion behavior, retrospective and KSA-assessment hooks, and preparation for adaptive unlocks

Work on the existing project and extend the skilltree course system from Phases 1 and 2 with dynamic progression behavior.

Before making code changes, inspect the current codebase after Phases 1 and 2 and current:
	•	graph-based course model
	•	node semantics
	•	progress-state computation
	•	milestone/capstone logic
	•	KSA assessment systems
	•	learning engine integration points
	•	existing retrospective/checkpoint/test structures if any

Objective

Add the first layer of dynamic progression intelligence to the skilltree course system.

This phase must add:
	•	branch completion logic
	•	stronger course completion logic
	•	retrospective hooks
	•	KSA mini-assessment hooks
	•	improved unlock/recommendation behavior
	•	data structures for remediation and adaptive progression preparation

This phase should make the skilltree feel more alive and progression-aware without yet becoming a fully autonomous adaptive curriculum engine.

⸻

Important scope boundaries

This phase must include
	•	branch completion computation
	•	stronger course completion computation
	•	retrospective-test hooks
	•	KSA mini-assessment hooks
	•	recommended next-node logic
	•	data structure support for remediation/review paths
	•	adaptive unlock preparation
	•	UI indicators for richer progression status

This phase must NOT yet include
	•	fully automatic AI-generated branching
	•	live generation of new graph nodes
	•	full remediation engine
	•	full adaptive personalization engine
	•	heavy graph animation or full gameification systems

This is the “dynamic logic layer,” not the final autonomous skilltree system.

⸻

Branch completion requirements

1. Branch identity

Support branch or path identity within the skilltree where appropriate.

A branch may be:
	•	an explicit graph group
	•	a chapter pathway
	•	a labeled route through nodes

Choose a clean representation.

2. Branch completion logic

Implement deterministic logic so a branch is complete when:
	•	all required nodes in that branch are completed
	•	optional nodes do not block completion unless configured otherwise

3. Course completion logic

A course becomes complete when:
	•	all required branches are complete
	•	all global capstone/final required nodes are complete

Make this explicit and testable.

⸻

Retrospective and assessment hooks

1. Retrospective hooks

Support node or branch metadata indicating:
	•	after this node/branch, a retrospective may be triggered later
	•	review is recommended
	•	recap checkpoint is available

You do not need to implement full retrospective generation now, but the graph logic and metadata should support it.

2. KSA mini-assessment hooks

Support metadata and logic so certain nodes or milestones can indicate:
	•	mini KSA check available
	•	recommended reassessment for a KSA subtopic
	•	unlock condition for deeper KSA refinement

Do not fully build the mini-assessment engine here unless it fits extremely cleanly. Focus on the hook architecture and progression behavior.

⸻

Recommended-next-step logic

Implement a first-pass recommendation engine for:
	•	next best available node
	•	next branch to continue
	•	suggested optional enrichment node
	•	suggested review node if applicable

This should be deterministic and rule-based, not LLM-driven.

Use factors such as:
	•	available nodes
	•	branch completion state
	•	milestone status
	•	optional vs required priority
	•	maybe lightweight KSA relevance if already stored

This will improve the UX significantly.

⸻

Remediation preparation

Add structure to support future remediation paths.

At minimum:
	•	allow certain nodes to be marked as remediation/review-support nodes
	•	allow relationships like “recommended if failed checkpoint X”
	•	support storing these relationships even if the full remediation engine is not implemented yet

Do not overbuild, but make sure the schema can express it.

⸻

Adaptive unlock preparation

This phase should prepare for future adaptive unlocks.

Support metadata such as:
	•	unlock if KSA threshold reached
	•	unlock if branch completed
	•	unlock if review recommended
	•	unlock if checkpoint passed
	•	recommended but not required

Do not implement fully AI-driven unlock decisions yet, but make the graph model capable of expressing richer unlock rules.

⸻

UI requirements

1. Branch and course completion visibility

Expose branch and course completion status in the UI more clearly.

Examples:
	•	branch progress summaries
	•	chapter completion
	•	overall required-completion status

2. Node recommendation visibility

Show useful recommendations such as:
	•	“Next recommended node”
	•	“Checkpoint available”
	•	“Review suggested”
	•	“KSA check available”

Keep it clean and not noisy.

3. Side panel enhancement

Enhance the side panel to display:
	•	branch membership
	•	completion role (required/optional/capstone)
	•	retrospective/KSA hook presence
	•	recommendation status where useful

⸻

Backend requirements

1. Completion services

Implement deterministic services/functions for:
	•	branch completion
	•	course completion
	•	recommended next node
	•	optional-path recommendation
	•	retrospective hook detection
	•	KSA hook detection

2. Data model updates

Update schema/persistence only as needed to support:
	•	branch identity/grouping
	•	recommendation metadata
	•	retrospective hooks
	•	KSA hooks
	•	remediation references
	•	richer unlock-rule metadata

⸻

Architecture requirements

1. Keep dynamic progression logic modular

Do not bury all progression computation in route handlers or frontend components.

Recommended separation:
	•	completion engine
	•	recommendation engine
	•	hook resolution
	•	graph rule evaluation

2. Prepare for later adaptive curriculum behavior

This phase should make it possible later to add:
	•	adaptive unlock decisions
	•	remediation path activation
	•	personalized branch suggestions
	•	KSA-informed route changes

without redoing the whole graph model.

⸻

Validation requirements

This phase is not complete when some recommendation text appears in the UI.

It is complete only after branch/course completion, hooks, and dynamic progression logic work end to end and have been checked, tested, and debugged where necessary.

Validate at minimum:
	1.	branch completion logic works correctly
	2.	course completion logic works correctly
	3.	optional branches do not incorrectly block course completion
	4.	recommended-next-node logic works
	5.	retrospective hooks are represented and surfaced correctly
	6.	KSA mini-assessment hooks are represented and surfaced correctly
	7.	remediation/review hook metadata works
	8.	richer unlock-rule preparation is in place
	9.	UI shows progression information clearly
	10.	no regression from Phases 1 and 2

If issues are found:
	1.	identify root cause
	2.	debug and fix
	3.	rerun validation
	4.	update docs and changelog

⸻

Testing requirements

Update and/or add tests where practical for:
	•	branch completion
	•	course completion
	•	recommendation engine behavior
	•	retrospective hook resolution
	•	KSA hook resolution
	•	unlock-rule evaluation
	•	UI progression summaries
	•	side-panel recommendation metadata

⸻

Documentation requirements

Update at minimum:
	•	README.md
	•	docs/learning.md
	•	docs/courses.md
	•	docs/architecture.md
	•	docs/testing.md
	•	changelog.md

Also document:
	•	branch completion rules
	•	course completion rules
	•	recommendation logic
	•	retrospective hooks
	•	KSA mini-assessment hooks
	•	remediation preparation
	•	current limitations before full adaptive progression is added

⸻

Deliverable expectations

When finished:
	•	the skilltree supports meaningful branch and course completion logic
	•	the system can recommend the next nodes/routes
	•	retrospective and KSA-assessment hooks exist in the graph model
	•	the UI exposes richer progression information
	•	the architecture is prepared for future adaptive unlocking and remediation
	•	tests/docs/changelog are updated
	•	the result has been verified and debugged if needed