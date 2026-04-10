Phase 2: Add richer skilltree node behavior, checkpoint/test nodes, optional and parallel progression behavior, KSA-linked execution metadata, and node completion semantics

Work on the existing project and extend the Phase 1 skilltree course system with richer node behavior.

Before making code changes, inspect the current codebase after Phase 1 and current:
	•	schema v2 course model
	•	node types
	•	unlock logic
	•	node detail panel
	•	user progress model
	•	KSA models
	•	assessment/test systems already present
	•	learning engine / learning chat integration points
	•	any existing quiz/checkpoint infrastructure

Objective

Upgrade the Phase 1 skilltree system so nodes are no longer mainly structural placeholders. They should now represent more meaningful learning events and progression logic.

This phase must add:
	•	richer node types and execution semantics
	•	checkpoint/test nodes
	•	optional nodes and optional branches with clearer behavior
	•	parallel-node handling
	•	stronger KSA-linked metadata
	•	branch milestone/capstone concepts
	•	explicit node completion criteria

This phase should still avoid full adaptive unlocking and deep remediation logic. It is about making the skilltree useful and semantically rich.

⸻

Important scope boundaries

This phase must include
	•	richer node types
	•	node completion modes
	•	test/checkpoint node support
	•	branch milestone/capstone support
	•	optional/parallel progression behavior refinement
	•	KSA-linked node metadata improvement
	•	node reward/unlock metadata
	•	stronger progress semantics
	•	UI updates to reflect richer node types/states

This phase must NOT yet include
	•	fully adaptive unlock rules
	•	dynamic remediation path generation
	•	automatic retrospective generation
	•	KSA mini-assessment execution if not cleanly ready
	•	AI-generated branching logic
	•	full skilltree graph animation system

⸻

Node-type expansion requirements

Extend node types so the system can support at minimum:
	•	learning_unit
	•	practice
	•	quiz
	•	checkpoint
	•	review
	•	milestone
	•	capstone
	•	unlock_gate
	•	assessment_hook

If a smaller subset is cleaner in code behavior, keep the type field extensible and document the implemented subset.

Node completion semantics

Each node must explicitly declare how completion is earned.

Support a clean completion model such as:
	•	lesson_complete
	•	practice_complete
	•	quiz_pass
	•	checkpoint_pass
	•	manual
	•	review_complete
	•	assessment_threshold
	•	gate_unlock

This phase should implement the schema, persistence, and core logic for these completion types where practical.

Do not keep completion as a vague boolean.

⸻

Optional and parallel progression refinement

1. Optional nodes

Optional nodes should:
	•	be clearly marked
	•	not block core path completion unless configured otherwise
	•	still contribute to richer completion, rewards, or KSA growth where appropriate

2. Optional branches

Support branch structures where:
	•	some branches are mandatory
	•	some branches are optional
	•	optional branches enrich completion but do not block final completion

3. Parallel nodes

Support nodes that can be completed in parallel once prerequisites are met.

The system should:
	•	compute availability correctly
	•	display them clearly in the UI
	•	not force an unnecessary sequence when parallel completion is allowed

4. Milestones and capstones

Add milestone/capstone concepts for branch and course progression.

Examples:
	•	milestone node for branch checkpoint
	•	capstone node for branch or course culmination

Support:
	•	display metadata
	•	completion gating
	•	detail panel visibility

⸻

KSA-linked node metadata requirements

Strengthen the KSA linkage from Phase 1.

Each node should now be able to define:
	•	K/S/A dimension
	•	big-map topic
	•	optional subtopic
	•	expected starting level
	•	target level after completion
	•	contribution weight or reward value
	•	whether the node unlocks or recommends a KSA check later

This phase still does not need to fully execute all KSA progression math, but the metadata must be rich enough for the next phases.

⸻

Node reward/unlock metadata

Support useful progression metadata such as:
	•	unlocks node ids
	•	unlocks branch ids
	•	recommended next nodes
	•	estimated KSA gain
	•	estimated effort
	•	optional reward tags/badges for future use

Do not over-gamify yet, but keep the structure ready.

⸻

Assessment/test/checkpoint integration requirements

This phase should integrate with existing or emerging test/checkpoint capability enough so that:
	•	quiz nodes can represent a quiz-based progression step
	•	checkpoint nodes can represent a branch or chapter validation step
	•	assessment_hook nodes can point to future KSA mini-assessment opportunities
	•	review nodes can represent recap/remediation opportunities

If a fully executable node action is not yet available for every type, implement clean placeholders and clear status handling rather than fake completion.

⸻

UI requirements

1. Skilltree visuals

Update the skilltree UI so different node types are visually distinguishable.

Recommended cues:
	•	icons
	•	color accents
	•	border styles
	•	badges
	•	state styling

Keep the result visually clean and consistent with the product.

2. Node detail panel

Enhance the right-side detail panel to show:
	•	node type
	•	completion rule
	•	KSA targets / gains
	•	estimated effort
	•	required vs optional
	•	unlock/reward information
	•	milestone/capstone meaning where applicable

3. Progress messaging

Show clearer progression semantics such as:
	•	required
	•	optional
	•	available
	•	parallel available
	•	blocked by prerequisite
	•	checkpoint pending
	•	capstone locked

Avoid clutter, but make the tree understandable.

⸻

Backend requirements

1. Schema updates

Extend schema v2 and/or persistence so richer node semantics are modeled cleanly.

2. Progress state updates

Support richer progress statuses if needed, for example:
	•	locked
	•	available
	•	in_progress
	•	completed
	•	mastered
	•	optional_skipped
	•	failed_needs_retry
	•	awaiting_checkpoint

Choose a clean maintainable set.

3. Completion evaluation

Add deterministic logic for:
	•	whether a node can be marked complete
	•	whether a branch milestone/capstone is unlockable
	•	whether optional nodes affect required completion
	•	whether branch completion is satisfied

Do not leave these semantics ambiguous.

⸻

Architecture requirements

1. Keep skilltree semantics separate from adaptive tutoring

This phase is still about course graph semantics and execution metadata, not the full AI learning orchestration.

2. Reuse and extend Phase 1 components

Build on:
	•	graph validation
	•	unlock logic
	•	progress state computation
	•	node rendering

Do not duplicate logic.

3. Future readiness

Prepare for Phase 3 where:
	•	retrospective logic
	•	KSA mini-assessment integration
	•	adaptive unlocks
	•	remediation paths

may be added.

⸻

Validation requirements

This phase is not complete when more node types exist in JSON and a few icons appear.

It is complete only after richer node behavior and progress semantics work end to end and have been checked, tested, and debugged where necessary.

Validate at minimum:
	1.	richer node types are supported by schema and validation
	2.	node completion modes are modeled cleanly
	3.	quiz/checkpoint/milestone/capstone nodes are represented correctly
	4.	optional node behavior works
	5.	optional branch behavior works
	6.	parallel availability works
	7.	milestone/capstone progression logic works
	8.	KSA-linked metadata is stored and displayed correctly
	9.	node detail panel reflects the richer semantics
	10.	progress state computation still works
	11.	no regression from Phase 1

If issues are found:
	1.	identify root cause
	2.	debug and fix
	3.	rerun validation
	4.	update docs and changelog

⸻

Testing requirements

Update and/or add tests where practical for:
	•	richer node-type validation
	•	completion-mode handling
	•	optional vs required logic
	•	parallel unlock logic
	•	milestone/capstone behavior
	•	KSA metadata mapping
	•	node detail UI data contracts
	•	progress-state transitions

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
	•	richer node types
	•	completion semantics
	•	optional/parallel behavior
	•	milestone and capstone concepts
	•	KSA-linked node metadata
	•	current limits before adaptive progression is added

⸻

Deliverable expectations

When finished:
	•	skilltree nodes have richer semantics
	•	optional and parallel progression behavior is supported
	•	milestones/capstones are modeled and displayed
	•	KSA-linked node metadata is richer and useful
	•	node completion is no longer just a vague boolean
	•	the implementation remains clean and extensible
	•	tests/docs/changelog are updated
	•	the result has been verified and debugged if needed