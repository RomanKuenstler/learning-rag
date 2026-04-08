# Learning And Courses

## Learning Page Tabs

The Learning page now contains:

- `Profile`
- `Preferences`
- `KSA` (big-map foundation)

The old `Paths` tab has been removed. Course/path management moved to the dedicated Courses page.

## KSA Big-Map (Step Foundation)

The `KSA` tab now renders a first real capability overview:

- top-right `Start Assessment` button
- 3-column radar layout (`Knowledge`, `Skills`, `Abilities`)
- each radar uses a 1-5 Dreyfus scale (`Novice`, `Advanced`, `Competent`, `Proficient`, `Expert`)
- a placeholder `KSA Assessment` dialog shell using the diagnostic modal style
- a deep-dive placeholder section below the charts

Authoritative radar axes:

- Knowledge: `STEM Fundamentals`, `Information Technology`, `Humanities & Social Sciences`, `Languages & Linguistics`, `Business & Commerce`, `Legal & Ethics`, `Health & Wellness`
- Skills: `Literacy & Numeracy`, `Digital Craft`, `Strategic Execution`, `Operational Skills`, `Relational Skills`, `Research & Inquiry`
- Abilities: `Quantitative Reasoning`, `Verbal Comprehension`, `Spatial Visualization`, `Executive Function`, `Sensory-Perceptual`, `Social-Emotional Capacity`, `Divergent Thinking`

Profile source behavior in this step:

- endpoint: `GET /api/learning-profile/ksa`
- student users receive a non-persisted default baseline profile (sample values, no completed assessment yet)
- non-student users receive a neutral placeholder baseline profile
- this is intentionally structured so real assessment persistence can replace defaults later without UI refactors

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
