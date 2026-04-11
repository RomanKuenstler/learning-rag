# Learning And Courses

## User Node Context Foundation (Step)

The backend now persists a per-user, per-course-node context snapshot that is generated before node execution.

Endpoints:

- `GET /api/learning-paths/{learning_path_id}/nodes/{node_id}/context`
- `GET /api/learning-paths/{learning_path_id}/node-contexts/available`

Persisted sections per node context:

- `course_context`
- `chapter_branch_context`
- `prior_node_context`
- `target_node_context`
- `next_node_context`
- `ksa_context`
- `readiness_context`
- `derived_assumptions`

Generation behavior:

- supports start nodes and non-start nodes
- resolves prior dependency chain and completed relevant nodes
- aggregates covered topics/goals/concepts from completed relevant nodes
- resolves immediate lookahead (successors + near validations)
- links node-relevant KSA state and related drill attempts
- computes structured readiness flags (`likely_ready`, scaffold/review signals, support intensity)

Recompute and invalidation behavior:

- recomputes on node progress updates
- recomputes on KSA profile/drill updates
- invalidates cached node contexts for a course when course structure changes

Non-goal in this step:

- no node-type-specific execution/prompt behavior yet (`learning_unit`, `practice`, `quiz`, etc. execution remains separate)

## Node-Type Execution Layer (assessment_hook, quiz, practice, checkpoint, capstone, unlock_gate, milestone)

Node execution is now supported via runtime attempts for:

- `assessment_hook`
- `quiz`
- `practice`
- `checkpoint`
- `capstone`
- `unlock_gate`
- `milestone`

API:

- `POST /api/learning-paths/{learning_path_id}/nodes/{node_id}/execution/start?force_new_attempt=true|false`
- `GET /api/learning-paths/{learning_path_id}/nodes/{node_id}/execution/latest`
- `GET /api/learning-paths/{learning_path_id}/nodes/{node_id}/execution/attempts`
- `PUT /api/learning-paths/{learning_path_id}/nodes/{node_id}/execution/attempts/{attempt_id}/responses`
- `POST /api/learning-paths/{learning_path_id}/nodes/{node_id}/execution/attempts/{attempt_id}/uploads`
- `POST /api/learning-paths/{learning_path_id}/nodes/{node_id}/execution/attempts/{attempt_id}/complete`

Runtime generation model:

- runtime-generated node types generate packages only on `start`.
- generated packages are persisted per user/node attempt.
- `start` resumes active attempts by default and `force_new_attempt=true` creates a new attempt while preserving history.
- completion and scoring are persisted on `complete`.

Behavior:

- `assessment_hook`: LLM-assisted selection of 8-16 targeted topics, 4-archetype round generation per topic, full-round completion requirement, result-linked KSA refinement.
- `quiz`: backward node-window resolution, package with 12 MC/SC + 3 deep-dive rounds + 2 free-text questions, deterministic MC scoring, LLM free-text evaluation, persisted pass/fail result.
- `practice`: 3-5 mixed application tasks (scenario free-text + upload-based practical tasks), rubric-based evaluation, required-task completion checks, and threshold-based completion.
- `checkpoint`: mixed validation package with exact composition (10 MC/SC, 3 free-text quiz, 5 scenario practice, 4 deep-dive drill rounds), component-aware scoring, threshold + minimum-component pass logic.
- `capstone`: larger integrative package with exact composition (24 MC/SC, 8 free-text quiz, 8 scenario practice, 8 deep-dive drill rounds), stricter threshold + component minima.
- `unlock_gate`: structural requirement checks and auto-completion when requirements are met.
- `milestone`: structural precursor checks and auto-completion when requirements are met.

KSA-aware calibration:

- generation prompts and deterministic fallbacks use a `difficulty_profile` derived from node context + KSA profile/drill signals.
- package payloads persist this calibration snapshot for debugging/reproducibility.

Upload-based practice/checkpoint/capstone support:

- direct per-attempt uploads are supported via the execution upload endpoint.
- uploaded files are stored in `data/uploads/<username>/node-execution/<attempt_id>/...`.
- attempt responses persist artifact references + extracted summaries (not full binary payloads).

Current non-goal:

- `learning_unit` and `review` node execution logic.

## Learning Page Tabs

The Learning page now contains:

- `Profile`
- `Preferences`
- `KSA` (big-map foundation)

The old `Paths` tab has been removed. Course/path management moved to the dedicated Courses page.

## KSA Big-Map

The `KSA` tab renders the capability overview with:

- top-right `Start Assessment` button
- 3-column radar layout (`Knowledge`, `Skills`, `Abilities`)
- each radar uses a 1-5 Dreyfus scale (`Novice`, `Advanced`, `Competent`, `Proficient`, `Expert`)
- a real multi-phase `KSA Assessment` flow dialog
- a deep-dive placeholder section below the charts
- `Start Assessment Drills` action below deep-dive for voluntary refinement runs

Authoritative radar axes:

- Knowledge: `STEM Fundamentals`, `Information Technology`, `Humanities & Social Sciences`, `Languages & Linguistics`, `Business & Commerce`, `Legal & Ethics`, `Health & Wellness`
- Skills: `Literacy & Numeracy`, `Digital Craft`, `Strategic Execution`, `Operational Skills`, `Relational Skills`, `Research & Inquiry`
- Abilities: `Quantitative Reasoning`, `Verbal Comprehension`, `Spatial Visualization`, `Executive Function`, `Sensory-Perceptual`, `Social-Emotional Capacity`, `Divergent Thinking`

KSA profile source behavior:

- endpoint: `GET /api/learning-profile/ksa`
- if no completed assessment exists:
  - student users receive non-persisted default baseline values
  - non-student users receive neutral baseline values
- once the initial assessment is completed:
  - profile source becomes `assessment`
  - persisted assessment values are returned
  - baseline defaults are no longer used for that user

## KSA Initial Assessment Flow

The onboarding assessment is implemented as a deterministic 4-phase flow:

- Phase 1: broad sieve sliders (`1..10`) decide which knowledge and skill topics are validated in this run.
- Phase 2: knowledge bank (easy + hard checks) with `FS = S * V` where:
  - fail easy => `V=0.5`
  - pass easy, fail hard => `V=1.0`
  - pass both => `V=1.5`
- Phase 3: skill scenarios:
  - choice `A` => level 1
  - choice `B` => level 3
- Phase 4: timed ability tasks using:
  - `capacity = (correctness * 0.7) + (time_bonus * 0.3)`
  - 30s target window

Untriggered knowledge/skill topics are persisted as `uncharted`.

Derived values currently include:

- `logic_quantitative_index` (`executive_function` + `quantitative_reasoning` capacity)
- `learning_speed_multiplier` => `1.5` when index `> 1.6`, otherwise `1.0`

## KSA Assessment Drills (Deep Dive)

Drills are a separate follow-up flow that refines an existing big-map profile.

- button location: below `KSA Deep Dive`
- dialog entry: opens directly into topic selection (no intro splash)
- topic selection: user chooses `1..3` top-level topics
- per selected topic: deterministic 12-question triple-drill sequence
  - Block 1 `Baseline` (Q1 recalibration, Q2 threshold, Q3 side-step, Q4 stress-test)
  - Block 2 `The Drill` (sub-topic A progression)
  - Block 3 `Expansion` (sub-topic B progression)

Drill scoring/persistence behavior:

- parent topic:
  - pass Q1 + Q2 => `+0.2` level delta
  - fail Q1 => map decay signal (`-0.1` + decay event increment)
- block 2/3: create or update sub-topic entries in `drill_state.topic_nodes[*].sub_nodes`
- stress-test questions:
  - 15-second target
  - score uses `ability = correctness*0.7 + time_remaining*0.3`
- top-level chart values are refreshed from refined topic levels

Question source:

- drill prompts/archetypes are loaded from `prds/interaction-archetypes_ksa.json`
- if a specific archetype prompt is missing, deterministic fallback prompt templates are used

Repeatability:

- users can run drills repeatedly
- each attempt is persisted in history
- profile is refined incrementally instead of full blind replacement

## Courses Page

A new `/courses` page manages learning paths as graph-based skilltree courses with:

- table view
- search
- filtering (`scope`, `status`)
- sorting (`name`, `updated`, `modules`, `lessons`, scope-first variants)
- skilltree render in course details (graph nodes + edges)
- right-side node detail panel
- chapter, branch, and course completion summaries
- deterministic next-step recommendation strip (`next node`, `next branch`, optional/review/KSA suggestions)
- `Download Template` action
- `Add Paths` dialog for uploading up to 5 JSON files

The upload dialog supports per-file scope (`global` or `user`) using styled dropdown controls.

## Course JSON Source Of Truth

Course definitions are file-backed in `courses/` and now use skilltree schema v2.

- one `.json` file = one course/path
- files are validated at startup
- valid files are synced into learning-path tables
- invalid files are rejected and logged with file-specific errors
- existing DB paths are exported back to `courses/` so each path has a corresponding JSON file

`global` vs `user` scope is validated from JSON. User-scoped courses require `owner_user_id` in file-based bootstrap.

### Schema v2 Overview

- top-level: `schema_version`, metadata, `chapters`, `branches`, `nodes`, `edges`, `entry_node_ids`, `completion_rules`, `visual_layout`
- node types: `learning_unit`, `practice`, `quiz`, `checkpoint`, `review`, `milestone`, `capstone`, `unlock_gate`, `assessment_hook`
- completion modes: `lesson_complete`, `practice_complete`, `quiz_pass`, `checkpoint_pass`, `review_complete`, `assessment_threshold`, `gate_unlock`, `manual`
- dependency relationships: `requires_all`, `requires_any`, `recommended`, `optional`
- optional and parallel progression are supported through node `required` and graph dependencies
- node KSA metadata supports `start_level`, `target_level`, contribution weight, and assessment-hook hints
- node metadata also supports unlock/reward contracts (`unlocks`, `rewards`)
- dynamic progression metadata is now supported per node:
  - `retrospective_hooks`
  - `ksa_hooks`
  - `remediation`
  - `adaptive_unlock`

### Compatibility And Migration

- legacy `schema_version: 1` module/lesson files are still accepted
- legacy payloads are converted into a linear v2 graph during import/bootstrap
- existing linear CRUD endpoints continue to work, with automatic graph regeneration from module/lesson edits

### Progress States

Node runtime states currently support:

- `locked`
- `available`
- `awaiting_checkpoint`
- `in_progress`
- `failed_needs_retry`
- `completed`
- `mastered`
- `optional_skipped`

The system computes deterministic unlock states from prerequisites and persisted node progress.

Phase 3 runtime also computes:

- branch progress (`required` vs optional branches)
- stronger course completion (`required branches + global capstones`)
- deterministic recommendations for next node/branch and optional review/KSA hooks
- hook summaries for retrospective, remediation, KSA mini-assessment, and adaptive-unlock candidates

### Node Progress Update API

Node progression can be persisted with:

- `PUT /api/learning-paths/{learning_path_id}/nodes/{node_id}/progress`
- payload: `status` (`in_progress|completed|mastered|optional_skipped|failed_needs_retry`) + optional `evidence`
- reset support: `status=reset` clears persisted node progress for that node (when currently `in_progress` or `completed`)

Mode-aware validation is enforced:

- `quiz_pass`/`checkpoint_pass`: pass evidence (or score above threshold)
- `assessment_threshold`: assessment score threshold in node metadata
- `gate_unlock`: gate evidence (`gate_unlocked` or matching `gate_key`)
- `assessment_hook` completion remains intentionally non-executable in this phase

## Diagnostics (Step B.1)

Diagnostic definitions are markdown-driven and loaded dynamically from:

- `data/sources/alpd/LAAv2.md`
- `data/sources/alpd/MOAv2.md`
- `data/sources/alpd/LTAv2.md`

Behavior updates:

- startup sync imports only `.md` diagnostics from `data/sources/alpd` (v2 source-of-truth)
- parser extracts sections/questions/options, metadata frontmatter (if present), and MOA result text blocks
- old `.docx/.txt/.pages/.pdf` diagnostic source fallbacks are removed from the runtime loading path
- LAA `Other:` options render an inline textarea directly inside the selected option card and persist as one combined value (`selected` + `other_text`)
- LAA scoring is section-based (profile logic), not one global test score:
  - single-choice options map to internal dimensions
  - section dimensions are normalized to `0..100`
  - emotional slider items are persisted as item-level values and compact subprofile indices
  - multi-select areas are persisted and rendered as profile tags
- MOA scoring now selects and persists a dynamic personalized text block based on the top motivation pair (`selected_result_block_id`, `selected_result_block_title`, `result_text`)
- MOA UI keeps the existing chart and shows a personalized output section below it
- LTA now uses distribution-first channel scoring and presentation:
  - one counter per channel (`auditiv`, `visuell`, `kinaesthetisch`, `lesen_schreiben`)
  - persisted raw counts plus percentages (`channel_counts`, `channel_percentages_0_100`)
  - deterministic classification (`dominant`, `mixed`, `balanced`)
  - generated summary text rendered from actual result (`summary_text`)
  - full 4-channel distribution shown in result UI instead of dominant-only output

At startup, definitions are versioned and persisted. Runtime data remains in:

- `user_diagnostic_attempts`
- `user_diagnostic_answers`
- `user_diagnostic_results`
- `learning_state_checks`
- `explanation_feedback`

Scoring remains deterministic and backend-only.

## Personalization Rule Engine Foundation

A new resolver layer now computes stable grouped personalization outputs from existing learner data.

Groups:

1. `identity_context`
2. `goal_intent`
3. `declared_preferences`
4. `diagnosed_learning`
5. `capability_mastery`
6. `live_adaptation`

Each group persists:

- normalized grouped snapshot
- resolved rule set
- per-group recompute timestamp
- source hash + reason trace entries

Storage:

- `user_learning_personalization_layers`

This foundation is prompt-free by design. It prepares rule inputs for later prompt/orchestration steps but does not yet generate final teaching prompts.

Recompute triggers are targeted:

- profile/context + personalization settings -> Group 1
- goals add/update/delete -> Group 2
- declared learning preferences updates -> Group 3
- diagnostic completion (LAA/MOA/LTA) -> Group 4
- KSA assessment/drill completion -> Group 5
- live checks/feedback/node runtime signals -> Group 6
