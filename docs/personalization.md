# Learning Personalization Layers

## Scope

This document describes the personalization rule-engine foundation used by learning flows.

This step is intentionally prompt-free:

- it resolves personalization layers from stored learner data
- it persists grouped snapshots and rule outputs
- it does not generate final teaching prompt text

## Six Resolved Groups

1. `identity_context`
2. `goal_intent`
3. `declared_preferences`
4. `diagnosed_learning`
5. `capability_mastery`
6. `live_adaptation`

## Persistence

Table:

- `user_learning_personalization_layers`

Stored per user:

- group snapshots (`*_snapshot`)
- resolved rules (`resolved_*_rules`)
- per-group recompute timestamps (`*_updated_at`)
- trace/debug fields:
  - `last_source_hashes_json`
  - `source_to_group_trace_json`
  - `change_log_json`
- `rule_engine_version`

## Resolver Design

Implementation entry point:

- `services/retriever/services/personalization_layers.py`

Pattern:

- one resolver per group
- each resolver reads relevant source data, normalizes grouped data, computes rules, and returns snapshot + rule set
- recompute execution is coordinated through `LearningPersonalizationLayerEngine.recompute_for_reasons(...)`

## Triggered Recompute

Recompute uses targeted reason-to-group mapping:

- `learning_context_updated`, `personalization_updated` -> Group 1
- `learning_goal_updated` -> Group 2
- `learning_preferences_updated` -> Group 3
- `diagnostic_completed` -> Group 4
- `ksa_updated` -> Group 5
- `learning_state_check_created`, `explanation_feedback_created`, `learning_node_progress_updated` -> Group 6

## Service Integration

`RetrieverAppService` calls safe recompute after relevant writes.

Debug/read endpoint:

- `GET /api/learning-profile/personalization-layers`

Response includes all groups with snapshots, resolved rules, per-group update times, trace metadata, and change log.

## Current Non-Goal

Not part of this step:

- constructing final tutor prompt text from these rules
- replacing existing prompt templates

This foundation is the data/rule layer that later prompt-building will consume.
