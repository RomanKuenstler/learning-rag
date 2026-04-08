# Learning And Courses

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

## Courses Page

A new `/courses` page manages learning paths as courses with:

- table view
- search
- filtering (`scope`, `status`)
- sorting (`name`, `updated`, `modules`, `lessons`, scope-first variants)
- `Download Template` action
- `Add Paths` dialog for uploading up to 5 JSON files

The upload dialog supports per-file scope (`global` or `user`) using styled dropdown controls.

## Course JSON Source Of Truth

Course definitions are file-backed in `courses/`.

- one `.json` file = one course/path
- files are validated at startup
- valid files are synced into learning-path tables
- invalid files are rejected and logged with file-specific errors
- existing DB paths are exported back to `courses/` so each path has a corresponding JSON file

`global` vs `user` scope is validated from JSON. User-scoped courses require `owner_user_id` in file-based bootstrap.

## Diagnostics (Step B.1)

Diagnostic definitions are parsed from:

- `data/diagnostics/source/MythriQ-LAA-Lernartanalyse-20250703a.docx`
- `data/diagnostics/source/MythriQ-MOA-Motivationsanalyse-20250703a.docx`
- `data/diagnostics/source/MythriQ-LTA-Lerntypanalyse-20250703a.docx`

At startup, definitions are versioned and persisted. Runtime data remains in:

- `user_diagnostic_attempts`
- `user_diagnostic_answers`
- `user_diagnostic_results`
- `learning_state_checks`
- `explanation_feedback`

Scoring remains deterministic and backend-only.
