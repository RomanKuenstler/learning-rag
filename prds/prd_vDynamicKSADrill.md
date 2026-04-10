You are working in an existing application codebase. Rework the “KSA Deep Dive Assessment Drills” flow from a static setup to a dynamic LLM-driven setup.

## Goal

Replace:
- static topic pickers
- static interaction archetype content generation

with a dynamic assessment flow that:
1. lets the user enter a free-text topic or topic description
2. classifies that input into K / S / A (or a combination) plus Big Map mapping
3. shows the classification to the user before starting
4. lets the user cancel or start
5. dynamically plans 4 rounds
6. dynamically generates the 4 archetypes for each round
7. stores attempts in a richer structure
8. updates the attempts table so rows behave like an accordion
9. shows collapsed badges as `<K/S/A> - <Big Map Topic>`
10. shows detailed topics only when the accordion row is expanded

## Important prompt files

The prompts already exist in `prompts/` and must be used, not recreated:

- `prompts/ksa-archetype-generation.md`
- `prompts/ksa-same-topic-variant.md`
- `prompts/ksa-topic-classification.md`
- `prompts/ksa-dynamic-topic-selection.md`

Load and use these prompt files in the implementation.

## Big functional changes required

### 1. Replace static topic picker with free-text topic input
In the KSA Deep Dive Assessment Drills entry flow:
- remove or bypass the static topic picker UI
- add a text input / textarea where users can enter:
  - a topic
  - or a description of a topic
- add validation so empty input cannot proceed

### 2. Add topic classification step before assessment start
When the user submits the topic:
- call the LLM using `prompts/ksa-topic-classification.md`
- pass the user input into the prompt
- parse the structured response
- expected output includes:
  - primary type
  - secondary type
  - type combo
  - big map group
  - big map subdomain
  - detailed topic
  - user explanation

If parsing fails:
- handle gracefully
- show a retryable error state
- do not start the assessment

### 3. Add confirmation screen
After successful topic classification, show a confirmation state before assessment generation.

Display:
- original user input
- primary type
- secondary type if present
- type combo
- big map group
- big map subdomain
- normalized detailed topic
- short user-facing explanation

Actions:
- Cancel
- Start Assessment

Cancel should return the user to the topic input step.
Start Assessment should continue to round planning.

### 4. Dynamically plan the 4 rounds
When the user starts the assessment, generate four round topics:

#### Round 1
Based directly on the classified user topic:
- use the normalized detailed topic from classification

#### Round 2
Use `prompts/ksa-same-topic-variant.md`
- generate a second detailed topic
- it must stay within the same overall user topic area
- it must explore a different angle/facet than round 1

#### Round 3
Use `prompts/ksa-dynamic-topic-selection.md`
- choose a “stretch topic”
- this must come from one of the user’s stronger Big Map areas
- but NOT their strongest area
- it should be a good adjacent challenge
- it must be specific enough for archetype generation

#### Round 4
Also use `prompts/ksa-dynamic-topic-selection.md`
- choose a “growth topic”
- this must come from one of the user’s weaker Big Map areas
- it should still be developmentally appropriate
- it must be specific enough for archetype generation

## Important for rounds 3 and 4
Use the user’s existing KSA / Big Map results from the app.
Find the current source of truth in the codebase for:
- KSA profile
- ranked strengths
- ranked weaknesses
- Big Map topic performance

Do not hardcode this. Reuse the existing user profile / results pipeline where possible.

If exact “best”, “good but not best”, and “bad” rankings are not already available in one place:
- compute them in one central helper
- keep the logic explicit and testable

### 5. Generate archetypes dynamically for each round
For each of the 4 rounds:
- call the LLM with `prompts/ksa-archetype-generation.md`
- pass the round’s detailed topic
- parse the structured result
- generate exactly 4 questions:
  - REVERSE_DEFINITION
  - SPOT_THE_FLAW
  - POWER_SPRINT
  - ANALOGY_MATCH

Each round should therefore contain 4 archetypes.
Total assessment = 4 rounds x 4 questions.

### 6. Preserve or improve current assessment UX
Keep the current assessment experience intact where possible, but adapt it to the new dynamic round source.

Make sure:
- loading states exist for:
  - classification
  - round planning
  - question generation
- errors are handled clearly
- retries are possible where appropriate
- assessment does not partially initialize in broken states

If the app currently preloads questions:
- preserve that behavior if it improves UX
- otherwise use a round-by-round loading strategy, whichever fits the existing architecture better

## Data model changes

Refactor attempt storage so attempts contain enough metadata for later display and analytics.

At minimum, persist:
- original source topic input
- topic classification result
- all 4 rounds
- for each round:
  - round number
  - origin (`user_core`, `user_variant`, `llm_stretch`, `llm_growth`)
  - type combo
  - big map group
  - big map subdomain
  - detailed topic
  - generated archetypes/questions
- timestamps
- completion status / score fields already in use
- any existing attempt identifiers

Prefer extending the existing attempt schema rather than inventing a parallel one, unless the current shape makes that unsafe.

## Attempts table / accordion behavior

Update the attempts table UI.

### Collapsed row behavior
In the topics column, show badges like:
- `<K/S/A combo> - <Big Map Topic>`

Use one badge or badge set per round, based on the saved round metadata.

Examples:
- `K+S - Information Technology`
- `S - Research & Inquiry`
- `A - Executive Function`

### Expanded accordion behavior
Each attempt row should be expandable like an accordion.

When expanded, show the detailed topics used:
- round 1 detailed topic
- round 2 detailed topic
- round 3 detailed topic
- round 4 detailed topic

Important:
- the detailed topics must only be visible when the accordion row is open
- the collapsed row should remain compact and badge-focused

### UX expectations
- preserve existing table sorting / pagination / styling where possible
- make the accordion interaction accessible
- do not break mobile layouts

## Architecture requirements

### Prompt loading
Create or reuse a centralized prompt-loading utility.
The implementation should:
- read prompt templates from `prompts/`
- inject runtime variables safely
- avoid scattering prompt strings throughout components

### LLM integration
Find the existing LLM service layer or API route.
Integrate the new prompt flow there instead of placing fetch logic directly in UI components.

Recommended flow:
1. classify topic
2. generate round plan
3. generate archetypes for each round

Keep these as separate functions so they are testable and maintainable.

### Parsing
Use strict structured parsing wherever possible.
If the existing codebase has schema validation utilities, use them.
Otherwise add runtime validation for each prompt result.

At minimum validate:
- classification response
- round selection response
- archetype generation response

Handle malformed responses safely.

## Reuse and refactor expectations

Before coding:
- inspect the current KSA Deep Dive Assessment Drills implementation
- identify all static topic picker logic
- identify all static archetype / question definitions
- identify current attempt storage and attempts table rendering
- identify any existing KSA profile data source

Then refactor cleanly.

Avoid:
- duplicated logic
- dead static configs left behind unused
- mixing prompt orchestration into presentation components

Prefer:
- helpers
- services
- typed models
- well-named transformations

## Implementation details to respect

### Round origins
Use these internal origin labels:
- `user_core`
- `user_variant`
- `llm_stretch`
- `llm_growth`

### Topic badges
For collapsed attempt rows, badge labels should use:
- type combo
- Big Map group or display topic label, depending on the current UI width and component conventions

If the existing table already has a “topics” column, adapt it rather than adding redundant columns.

### Confirmation copy
Use the classification result to populate a simple preflight review state before the user starts.

### Graceful fallback
If dynamic generation fails at any stage:
- do not silently substitute static questions
- show an explicit error
- allow retry
- keep the flow deterministic and debuggable

## Deliverables

Implement the full rework end to end.

After making changes:
1. summarize what files you changed
2. explain the new assessment flow
3. list any schema changes
4. mention any follow-up migration or seed steps if needed

## Constraints
- Do not recreate the prompt text inline if prompt files already exist
- Do not hardcode topic mappings that should come from prompt outputs
- Do not break existing attempt history
- Preserve styling conventions already used in the app
- Prefer minimal invasive changes, but complete the feature fully

Now inspect the codebase and implement this dynamic KSA Deep Dive Assessment Drills flow.