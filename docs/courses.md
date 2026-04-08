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
- KSA-linked node metadata
- layout metadata for UI rendering

## Schema v2

Required top-level fields:

- `schema_version` (`2`)
- `title`
- `scope` (`global|user`)
- `status` (`draft|published|archived`)
- `chapters`
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
- grouping: `chapter_id`
- requiredness: `required`
- prerequisite lists: `prerequisites.requires_all|requires_any|recommended`
- completion mode: `lesson_complete|manual|practice_complete|checkpoint_pass`
- effort: `estimated_duration_minutes`
- layout: `layout.x`, `layout.y`
- metadata: `metadata`, `display`
- KSA links: `ksa[]` with `dimension`, `topic`, optional `subtopic`, `target_level`, `contribution_weight`

Supported node `type` values:

- `learning_unit`
- `practice`
- `checkpoint`
- `review`
- `milestone`

## Dependency Model

Dependencies are stored as explicit edges:

- `requires_all`
- `requires_any`
- `recommended`

Validation guarantees:

- edge node references must exist
- no self-loops
- hard dependency graph (`requires_all` + `requires_any`) must be acyclic

## Progress States

Runtime node progress states:

- `locked`
- `available`
- `in_progress`
- `completed`
- `mastered`
- `optional_skipped`

Unlock behavior:

- entry nodes are available
- required prerequisites gate unlock
- optional/recommended edges do not block required completion

## Completion Semantics

- chapter/branch completion: all required nodes in chapter are completed/mastered
- course completion: all required nodes across the course are completed/mastered

## Compatibility And Migration

Legacy course JSON (`schema_version: 1`) is still supported.

Compatibility flow:

- parse legacy module/lesson payload
- generate linear v2 graph (node-per-lesson)
- auto-generate linear hard dependencies
- infer chapter grouping from modules

Legacy authoring endpoints (`modules`/`lessons`) remain available. Editing linear structures regenerates the persisted skilltree definition.

## Current Phase Limits

This phase only provides structural progression foundations.

Not included yet:

- full quiz/test execution per node
- retrospective testing
- adaptive unlock logic
- remediation branching logic
- deep animated graph interactions
