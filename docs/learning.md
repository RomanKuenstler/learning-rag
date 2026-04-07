# Learning Diagnostics (Step B.1)

## Source Of Truth

Diagnostic definitions are parsed from:

- `data/diagnostics/source/MythriQ-LAA-Lernartanalyse-20250703a.docx`
- `data/diagnostics/source/MythriQ-MOA-Motivationsanalyse-20250703a.docx`
- `data/diagnostics/source/MythriQ-LTA-Lerntypanalyse-20250703a.docx`

## Parsing And Versioning

At retriever startup, Step B.1 parser/import does:

1. Reads `.docx` XML paragraphs.
2. Converts `LAA`, `MOA`, `LTA` into structured definitions.
3. Stores versioned immutable records in `diagnostic_versions`.
4. Flattens questions/options/rules into dedicated relational tables.

Version is derived from filename suffix (e.g. `20250703a`).

## Scoring

Scoring is deterministic and backend-only (`services/retriever/services/diagnostic_scoring.py`):

- `MOA`: 10 slider values mapped to motive dimensions (0..10, normalized to 0..1).
- `LTA`: option mapping (`A/V/K/L`) aggregated to dominant learning type.
- `LAA`: section-level aggregation derived from questionnaire structure.

## Explicit Assumptions

The source docs are used exactly for question and option text.
Where no formula is explicitly defined:

- assumptions are stored in definition metadata (`assumptions`)
- behavior is documented (not silent)

## Runtime Data

- attempts: `user_diagnostic_attempts`
- answers: `user_diagnostic_answers`
- results: `user_diagnostic_results`
- state signals: `learning_state_checks`
- explanation feedback: `explanation_feedback`

## Frontend Flow

The learning page renders diagnostics dynamically from backend definitions:

- stepper: `LAA -> MOA -> LTA`
- per-step answer save
- deterministic completion and chart rendering
- attempt history and latest result display
