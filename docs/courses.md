# Courses And Skilltree Schema

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
- optional branches do not block final completion unless configured as required
- course completion: all effectively-required nodes across the course are completed/mastered

Node transition API:

- `PUT /api/learning-paths/{learning_path_id}/nodes/{node_id}/progress`
- validates completion against node completion mode and prerequisites

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
