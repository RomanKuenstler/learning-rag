# Diagnostics (LAA / MOA / LTA)

## Source Of Truth

Diagnostic definitions are loaded from markdown v2 files only:

- `data/sources/alpd/LAAv2.md`
- `data/sources/alpd/MOAv2.md`
- `data/sources/alpd/LTAv2.md`

The loader reads `.md` files dynamically, derives diagnostic type from filename (`LAA|MOA|LTA` + version suffix), and parses:

- sections
- questions
- options
- optional frontmatter metadata
- MOA result blocks and pair index

Legacy source fallbacks (`.docx`, `.txt`, `.pages`, `.pdf`) are not part of runtime parsing anymore.

## Flow

Diagnostic dialog flow remains:

1. `LAA`
2. `MOA`
3. `LTA`

Each step is answer-persistent and can be resumed from attempt history.

## LAA "Other:" Handling

For options labeled exactly `Other:`:

- option remains selectable as normal
- selecting it expands an inline textarea inside the same option card
- textarea is required while `Other:` is selected
- value is persisted inline as one answer object:
  - `{"selected": "oX", "other_text": "..."}` (single choice)
  - `{"selected": ["oA", "oX"], "other_text": "..."}` (multi choice)

## LAA Result Model (Section-Based)

LAA is evaluated as a multi-area profile system and not as one monolithic total score.

Each section produces a structured profile with:

- `section_id`, `section_title`
- `dimensions_raw`
- `dimensions_normalized_0_100`
- `insights` (2-4 profile statements)
- optional `profile_tags`
- optional item-level subprofiles (`emotional_items`, `skill_self_assessment_items`)
- optional `summary_indices_0_100`

### Internal Dimensions

Supported internal dimensions include:

- `zielklarheit`
- `zeitdruck`
- `strukturbedarf`
- `feedbackbedarf`
- `selbststeuerung`
- `soziale_lernorientierung`
- `emotionale_sicherheit`
- `frustrationsanfaelligkeit`
- `technikaffinitaet`
- `praxisorientierung`
- `sichtbarkeitsmotivation`

Single-choice options map into these dimensions via an explicit mapping table in backend scoring.

### Normalization

Dimension normalization is deterministic and section-local:

- raw points are summed per dimension
- each dimension has a deterministic section max derived from mapping-table option maxima
- normalized score = `(raw / max) * 100`, clamped to `0..100`

Raw totals are persisted but not used directly as user-facing outputs.

### Emotional Subprofile

The emotional attitude slider block is persisted item-by-item (`1..5`) and also normalized per item (`0..100`).

Defined summary indices:

- `lernsicherheit`
  - based on: stress, fear of mistakes, distractibility, giving up tendency (reversed), plus self-trust
- `selbstvertrauen`
  - based on: self-trust, pride in existing knowledge, fear of mistakes (reversed)
- `aeusserer_aktivierungsbedarf`
  - based on: external pressure need + giving up tendency

Only these documented indices are generated.

### Multi-Select Sections (Tag Model)

Multi-select areas are treated as profile tags, not fake numeric scores.

Examples:

- interests
- competencies
- everyday-used abilities
- custom free-text entries

These are persisted under `profile_tags` and rendered as user-facing profile summaries.

## MOA Dynamic Output

MOA still renders the motivation chart, then adds a personalized output section below it.

Backend scoring now computes:

- normalized motivation profile
- top motivation pair
- selected result block id/title
- rendered personalized result text from `MOAv2.md`

Persisted fields include:

- `computed_profile`
- `selected_result_block_id`
- `selected_result_block_title`
- `result_text`

## LTA Result Model (Channel Distribution)

LTA is evaluated as a four-channel distribution profile:

- `auditiv`
- `visuell`
- `kinaesthetisch`
- `lesen_schreiben`

Each selected answer increments exactly one mapped channel by `+1`.

Persisted result fields include:

- `channel_counts` (raw counts)
- `channel_percentages_0_100` (normalized percentages)
- `top_ranked_channels`
- `classification` (`dominant`, `mixed`, `balanced`)
- `profile_label`
- `summary_text`

### Classification Rules

Deterministic interpretation rules:

- `balanced`: all channel counts are close (`max - min <= 1`)
- `dominant`: top channel leads second channel by at least `2` points
- `mixed`: fallback when no dominant channel exists and profile is not balanced (top two channels form the mixed label)

The UI is distribution-first and displays all four channels, then renders profile type and generated summary text.

## Persistence

Attempt/result storage remains in:

- `user_diagnostic_attempts`
- `user_diagnostic_answers`
- `user_diagnostic_results`

Related learning signals remain unchanged:

- `learning_state_checks`
- `explanation_feedback`
