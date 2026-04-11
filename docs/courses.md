# Courses And Skilltree Schema

## Persistent User Node Context

A dedicated user-node-context layer now precomputes graph + learner state for each node.

Persistence model:

- table: `user_learning_node_contexts`
- unique key: `(user_id, learning_path_id, node_id)`
- stores grouped sections and an aggregate context payload
- stores `source_hash`, `generation_reason`, and `generated_at` for traceability

Context categories:

- course-level context
- chapter/branch placement context
- backward-looking prior-node coverage context
- targeted-node local metadata context
- forward-looking successor/checkpoint context
- related KSA capability/drill context
- readiness and derived assumption context

Design goal:

- later node-type handlers can consume one stable context object without repeating graph traversal and KSA matching.

## Node Execution Attempts

Node runtime execution now persists attempt artifacts in:

- `user_learning_node_execution_attempts`

Each attempt stores:

- generated runtime package
- responses
- evaluation result
- node context snapshot used at generation time
- source node window/scope metadata
- status/timestamps

Execution semantics:

- runtime node packages are generated only on explicit `start`.
- default `start` resumes an active attempt for that user/path/node.
- `force_new_attempt=true` starts a new attempt and marks the previous active attempt as superseded.
- users can inspect attempt history through `GET /api/learning-paths/{learning_path_id}/nodes/{node_id}/execution/attempts`.
- upload-based tasks are attached to attempts through `POST /api/learning-paths/{learning_path_id}/nodes/{node_id}/execution/attempts/{attempt_id}/uploads`.

This enables resumability, reproducible scoring/completion decisions, and later analytics.

## Overview

Courses are represented as graph-based skilltrees (`schema_version: 2`).

The graph model supports:

- nodes
- edges
- prerequisite rules (`requires_all`, `requires_any`)
- optional nodes
- parallel progression
- chapter grouping
- branch grouping (`required` vs optional branch routes)
- KSA-linked node metadata
- node unlock and reward metadata
- layout metadata for UI rendering

## Schema v2

Required top-level fields:

- `schema_version` (`2`)
- `title`
- `scope` (`global|user`)
- `status` (`draft|published|archived`)
- `chapters`
- `branches` (optional but recommended)
- `nodes`
- `edges`
- `entry_node_ids`

Common metadata fields:

- `id`
- `description`
- `subject`
- `difficulty_level`
- `estimated_duration_minutes`
- `allowed_file_ids`
- `allowed_tags`
- `completion_rules`
- `visual_layout`
- `metadata`

## Node Model

Each node supports:

- identity: `id`, `title`, `description`, `type`
- grouping: `chapter_id`, optional `branch_id`
- requiredness: `required`
- prerequisite lists: `prerequisites.requires_all|requires_any|recommended`
- completion mode:
  - `lesson_complete`
  - `practice_complete`
  - `quiz_pass`
  - `checkpoint_pass`
  - `review_complete`
  - `assessment_threshold`
  - `gate_unlock`
  - `manual`
- effort: `estimated_duration_minutes`
- layout: `layout.x`, `layout.y`
- metadata: `metadata`, `display`
- KSA links: `ksa[]` with `dimension`, `topic`, optional `subtopic`, `start_level`, `target_level`, `contribution_weight`, and assessment-hook flags
- unlock/reward contracts:
  - `unlocks.node_ids|branch_ids|recommended_next_node_ids`
  - `rewards.estimated_ksa_gain|effort_score|reward_tags`
- dynamic progression contracts:
  - `retrospective_hooks.retrospective_after|review_recommended|recap_checkpoint_available`
  - `ksa_hooks.mini_assessment_available|recommended_reassessment_topics|unlocks_deeper_refinement`
  - `remediation.is_remediation_node|recommended_if_failed_node_ids|supports_review_for_node_ids`
  - `adaptive_unlock.ksa_thresholds|requires_branch_completion_ids|requires_checkpoint_node_ids|requires_review_recommended|recommended_only`

Supported node `type` values:

- `learning_unit`
- `practice`
- `quiz`
- `checkpoint`
- `review`
- `milestone`
- `capstone`
- `unlock_gate`
- `assessment_hook`

## Dependency Model

Dependencies are stored as explicit edges:

- `requires_all`
- `requires_any`
- `recommended`
- `optional`

Validation guarantees:

- edge node references must exist
- no self-loops
- hard dependency graph (`requires_all` + `requires_any`) must be acyclic

## Progress States

Runtime node progress states:

- `locked`
- `available`
- `awaiting_checkpoint`
- `in_progress`
- `failed_needs_retry`
- `completed`
- `mastered`
- `optional_skipped`

Unlock behavior:

- entry nodes are available
- required prerequisites gate unlock
- optional/recommended edges do not block required completion
- checkpoint/gate bottlenecks can produce `awaiting_checkpoint`

## Completion Semantics

- chapter completion: all effectively-required nodes in chapter are completed/mastered
- branch completion: all effectively-required nodes in that branch are completed/mastered
- optional branches do not block final completion unless configured as required
- course completion: required branches must be complete and required global capstones must be complete

Node transition API:

- `PUT /api/learning-paths/{learning_path_id}/nodes/{node_id}/progress`
- validates completion against node completion mode and prerequisites

## Recommendation Logic

Runtime emits deterministic recommendations:

- `next_best_node_id`
- `next_branch_id`
- `suggested_optional_node_id`
- `suggested_review_node_id`
- `suggested_ksa_assessment_node_id`

No LLM routing is used; recommendations are graph-rule based.

## Hooks And Adaptive Preparation

Runtime also emits hook summaries for:

- retrospective-capable nodes
- review/remediation candidates
- KSA mini-assessment hook candidates
- adaptive-unlock candidate nodes

This prepares adaptive behavior without generating new nodes or auto-mutating the graph in this phase.

## Compatibility And Migration

Legacy course JSON (`schema_version: 1`) is still supported.

Compatibility flow:

- parse legacy module/lesson payload
- generate linear v2 graph (node-per-lesson)
- auto-generate linear hard dependencies
- infer chapter grouping from modules

Legacy authoring endpoints (`modules`/`lessons`) remain available. Editing linear structures regenerates the persisted skilltree definition.

## Current Phase Limits

Current phase is semantically rich but still intentionally bounded.

Not included yet:

- adaptive unlock strategies based on learner model
- automatic remediation branch generation
- retrospective graph generation
- AI-generated branch authoring
- full in-node assessment engine execution for all node types

## Runtime Node Plans

Node start execution now includes structured-plan runtime generation for:

- `learning_unit`: phased teaching-plan package with mini-topic lesson briefs and recap plan.
- `review`: recap/remediation plan package over the bounded backward review window.

These plans are persisted per attempt and designed for later delivery orchestration, questions, and feedback handling.
