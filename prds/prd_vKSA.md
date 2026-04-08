Step: Implement the initial KSA assessment for the big-map, including full assessment flow, scoring logic, persistence, and rendering real KSA results in the existing visualization

Work on the existing project and implement the first real KSA assessment system for the Learning page KSA tab.

Before making code changes, inspect the current codebase and current:
	•	Learning page KSA tab
	•	existing KSA radar visualization
	•	Start Assessment button and placeholder dialog
	•	learning models
	•	user profile / student role handling
	•	existing assessment/dialog patterns
	•	chat / learning data persistence
	•	frontend charting/data-loading flow

Objective

Replace the current placeholder KSA assessment dialog with a real initial KSA assessment engine that:
	1.	runs the KSA onboarding assessment flow
	2.	uses the provided topic map exactly
	3.	uses the provided conditional assessment logic
	4.	calculates and persists KSA results
	5.	removes the current student dummy/example KSA values once real assessment data exists
	6.	displays the persisted real results in the existing KSA big-map visualization
	7.	keeps the current KSA visualization layout unchanged

This step is about the first real KSA assessment, not yet about later deep-dive KSA reassessments or micro-assessments.

⸻

Important scope boundaries

This step must include
	•	real Start Assessment flow
	•	multi-phase KSA assessment dialog
	•	conditional question flow
	•	Knowledge scoring
	•	Skills scoring
	•	Abilities scoring
	•	persistence of KSA results
	•	removal/replacement of dummy KSA values when real assessment exists
	•	loading real KSA results into existing charts
	•	backend/API support
	•	validation and result mapping

This step must NOT include
	•	changing the existing KSA big-map chart design/layout
	•	deep-dive KSA section implementation
	•	advanced follow-up mini-assessments
	•	AI-generated KSA explanations
	•	dynamic graph / node-map UI
	•	full KSA reassessment strategy beyond this initial version

Keep the implementation focused on the initial KSA assessment.

⸻

Authoritative KSA map for this step

Use the following top-level KSA categories and topic groups exactly.

1. Knowledge — “The Mental Library”

Top-level Knowledge topics:
	•	STEM Fundamentals
	•	Information Technology
	•	Humanities & Social Sciences
	•	Languages & Linguistics
	•	Business & Commerce
	•	Legal & Ethics
	•	Health & Wellness

Reference meaning:
	•	STEM Fundamentals: Mathematics, Physics, Chemistry, Biology, Engineering principles
	•	Information Technology: Computer Science, Cybersecurity, Data Systems, Networking, Artificial Intelligence
	•	Humanities & Social Sciences: History, Philosophy, Psychology, Sociology, Political Science, Economics
	•	Languages & Linguistics: Grammar structures, Phonetics, Translation, Cross-cultural communication
	•	Business & Commerce: Finance, Marketing, Supply Chain, Entrepreneurship, Organizational Theory
	•	Legal & Ethics: Jurisprudence, Bioethics, Digital Rights, Corporate Governance
	•	Health & Wellness: Anatomy, Nutrition, Mental Health, Pharmacology, Sports Science

2. Skills — “The Toolbox”

Top-level Skills topics:
	•	Literacy & Numeracy
	•	Digital Craft
	•	Strategic Execution
	•	Operational Skills
	•	Relational Skills
	•	Research & Inquiry

Reference meaning:
	•	Literacy & Numeracy: Advanced reading comprehension, Statistical reasoning, Financial modeling
	•	Digital Craft: Software development, UI/UX design, Multimedia production (Video/Audio), CAD/3D Modeling
	•	Strategic Execution: Strategic planning, Risk management, Crisis handling, Change management
	•	Operational Skills: Logistics, Manufacturing processes, Quality control, Technical troubleshooting
	•	Relational Skills: Sales/Negotiation, Mentoring/Coaching, Public Relations, Diplomacy
	•	Research & Inquiry: Data mining, Scientific experimentation, Information synthesis, Academic writing

3. Abilities — “The Engine”

Top-level Abilities topics:
	•	Quantitative Reasoning
	•	Verbal Comprehension
	•	Spatial Visualization
	•	Executive Function
	•	Sensory-Perceptual
	•	Social-Emotional Capacity
	•	Divergent Thinking

Reference meaning:
	•	Quantitative Reasoning: Ability to manipulate numbers and recognize mathematical patterns
	•	Verbal Comprehension: Ability to understand complex written and spoken nuances quickly
	•	Spatial Visualization: Ability to mentally manipulate 2D and 3D objects
	•	Executive Function: Working memory, cognitive flexibility, and inhibitory control
	•	Sensory-Perceptual: Auditory discrimination, visual monitoring, fine motor coordination
	•	Social-Emotional Capacity: Dispositional empathy, social boldness, self-regulation
	•	Divergent Thinking: Capacity to produce many ideas from a single starting point

Use these exact top-level categories in storage and rendering.

⸻

Assessment design concept

This KSA assessment is a dynamic diagnostic engine, not a static test.

It must follow the intended “sieve” logic:
	1.	Filter / Broad Sieve
	•	self-reported sliders
	•	determines which deeper checks are relevant
	•	avoids frustrating users with irrelevant questions
	•	marks untouched areas as uncharted
	2.	Knowledge Check
	•	easy theoretical question
	•	harder theoretical question
	•	distinguishes Novice / Advanced Beginner / Competent
	3.	Skill Simulation
	•	scenario-based judgment
	•	one response is more novice/reactive
	•	one response is more competent/strategic
	4.	Ability Engine
	•	short timed “brain game” style tasks
	•	measures raw capacity, not Dreyfus proficiency

This logic must be reflected in code, persistence, and UI flow.

⸻

Assessment phases and logic

Implement the following exact assessment phases.

Phase 1 — Level 1 (The Broad Sieve)

Users move through these self-report sliders first.

Phase 1 items

ID	Topic	Interaction	Logic
1.1	STEM/IT	“Rate your technical & scientific literacy.” (1-10)	If >5, trigger K.1 (STEM) & K.2 (IT)
1.2	Humanities	“Rate your understanding of society & history.” (1-10)	If >5, trigger K.3 (Humanities) & K.4 (Languages)
1.3	Business/Law	“How comfortable are you with commerce & legal topics?” (1-10)	If >5, trigger K.5 (Business) & K.6 (Legal)
1.4	Health	“Rate your knowledge of biology & wellness.” (1-10)	If >5, trigger K.7 (Health)
1.5	Digital/Ops	“How skilled are you at using tools/building things?” (1-10)	If >5, trigger S.1 (Digital) & S.2 (Operational)
1.6	People/Strat	“Rate your ability to lead and plan.” (1-10)	If >5, trigger S.3 (Strategic) & S.4 (Relational)
1.7	Research	“How experienced are you in data/scientific inquiry?” (1-10)	If >5, trigger S.5 (Research) & S.6 (Literacy)

Behavior requirements
	•	If threshold is not reached, do not ask the deeper topic questions in this initial run
	•	Instead mark those areas as uncharted
	•	Uncharted areas should still exist in stored results

⸻

Phase 2 — Knowledge Bank

Goal:
	•	move user from Novice → Advanced Beginner → Competent

Use the following questions exactly.

ID	Topic	Level	Question	Options
K.1a	STEM	Easy	“What is the boiling point of water at sea level?”	90°C / 100°C / 110°C
K.1b	STEM	Hard	“What does the Second Law of Thermodynamics imply?”	Energy is created / Entropy increases / Heat flows cold to hot
K.2a	IT	Easy	“What is the purpose of an IP address?”	Identify a device on a network / Store files / Code logic
K.2b	IT	Hard	“In AI, what is ‘Overfitting’?”	Model too simple / Model fits noise, not general data / Model is too fast
K.3a	Humanities	Easy	“What does ‘Socio-economics’ study?”	Only money / Interaction of social and economic factors / History
K.3b	Humanities	Hard	“What is the core idea of ‘Existentialism’?”	Fate is predetermined / Individual freedom/responsibility / Collectivism
K.4a	Languages	Easy	“What is a ‘Suffix’?”	A word ending / A word beginning / A verb
K.4b	Languages	Hard	“What is the study of ‘Phonology’?”	Grammar / Speech sound patterns / Sentence meaning
K.5a	Business	Easy	“What is ‘Market Share’?”	Total profit / Company’s % of total industry sales / Share price
K.5b	Business	Hard	“What does ‘Just-in-Time’ (JIT) manufacturing aim to reduce?”	Labor / Inventory waste / Marketing costs
K.6a	Legal/Eth.	Easy	“What is a ‘Conflict of Interest’?”	Private interests vs professional duties / Two people arguing / A bad law
K.6b	Legal/Eth.	Hard	“What is ‘Deontological Ethics’?”	Results-based / Duty-based / Virtue-based
K.7a	Health	Easy	“What is a ‘Macronutrient’?”	Protein/Carbs/Fats / Vitamins / Water only
K.7b	Health	Hard	“What does ‘Pharmacokinetics’ describe?”	How drugs are made / How the body processes a drug / Drug side effects

Correct-answer mapping

Implement the correct options exactly as implied by the assessment design:
	•	K.1a → 100°C
	•	K.1b → Entropy increases
	•	K.2a → Identify a device on a network
	•	K.2b → Model fits noise, not general data
	•	K.3a → Interaction of social and economic factors
	•	K.3b → Individual freedom/responsibility
	•	K.4a → A word ending
	•	K.4b → Speech sound patterns
	•	K.5a → Company’s % of total industry sales
	•	K.5b → Inventory waste
	•	K.6a → Private interests vs professional duties
	•	K.6b → Duty-based
	•	K.7a → Protein/Carbs/Fats
	•	K.7b → How the body processes a drug

⸻

Phase 3 — Skills Bank

These are scenario-based and should be treated as practical judgment signals.

Use the following exactly.

ID	Topic	Scenario	Choice A (Novice)	Choice B (Competent)
S.1	Digital Craft	“A software UI is confusing users. What do you do?”	“Add more text instructions.”	“Simplify the layout and user flow.”
S.2	Operational	“A process step keeps causing a bottleneck.”	“Tell people to work faster.”	“Redesign the workflow to balance the load.”
S.3	Strategic	“You have a high-impact but high-risk idea.”	“Avoid it to be safe.”	“Create a mitigation plan and test a pilot.”
S.4	Relational	“A client is angry about a late delivery.”	“Explain why it’s not your fault.”	“Acknowledge the frustration and offer a solution.”
S.5	Research	“You find data that contradicts your theory.”	“Ignore it as an outlier.”	“Re-examine your theory based on the data.”
S.6	Literacy	“You need to summarize a 50-page technical report.”	“Read every word and rewrite it.”	“Extract key findings and actionable insights.”

Scoring behavior
	•	Choice B represents the more competent response
	•	This phase should distinguish at least between novice and competent behavior
	•	Persist both the selected option and derived level

⸻

Phase 4 — Abilities Bank

These are timed tasks and represent raw cognitive capacity rather than Dreyfus mastery.

Use the following exactly.

ID	Ability	Task	Expected result
A.1	Quantitative Reasoning	“If 5 shirts cost $45, how much do 3 cost?”	$27
A.2	Verbal Comprehension	“Complete the analogy: ‘Oven’ is to ‘Heat’ as ‘Camera’ is to…”	Light
A.3	Spatial Visualization	“Mental Rotation: Can two ‘L’ shapes form a rectangle?”	Yes
A.4	Executive Function	“Identify the ‘odd one out’ in 5 seconds: 66, 88, 77, 98, 44.”	98
A.5	Sensory-Perceptual	“Listen to three tones: High, Mid, Low. Which was second?”	Mid
A.6	Social-Emotional Capacity	“Someone looks away while you talk. They are likely…”	Disinterested/Uncomfortable
A.7	Divergent Thinking	“Name 3 uses for a coffee mug other than drinking.”	open-ended, example answers such as Pen holder, Planter, Hammer

Ability phase requirements
	•	timed tasks should support a time limit concept
	•	default time limit target: 30 seconds
	•	store correctness and response time
	•	support open-ended handling for divergent thinking with a deterministic first implementation if needed
	•	if exact automated scoring for Divergent Thinking is not yet strong enough, implement a safe initial heuristic and document it

⸻

Scoring logic (authoritative for this step)

Implement the following scoring logic exactly unless a very small technical adjustment is required. If any implementation-specific adjustment is needed, document it clearly.

A. Knowledge scoring — “Trust but Verify”

Inputs
	•	Phase 1 slider score = S
	•	Validation multiplier = V

Multiplier rules
	•	Fail Easy (K.xa) → V = 0.5
	•	Pass Easy, Fail Hard (K.xb) → V = 1.0
	•	Pass Both → V = 1.5

Final score
	•	FS = S × V

Dreyfus mapping
	•	FS < 4 → Level 1 (Novice)
	•	FS 4–7 → Level 2 (Advanced Beginner)
	•	FS > 7 → Level 3 (Competent)

Status behavior

Each Knowledge topic should also support a status such as:
	•	verified
	•	self_reported
	•	uncharted

Interpretation:
	•	if topic passed through validation questions → verified
	•	if future logic later allows self-report only → self_reported
	•	if topic was skipped because the sieve threshold was not met → uncharted

For this initial version, untriggered topics should typically become uncharted.

B. Skills scoring

The provided design says:
	•	scenario-based
	•	if Choice B is picked, user reaches “Competent” in that skill

Implement a clean first version with a simple level mapping such as:
	•	Choice A → Level 1 (Novice)
	•	Choice B → Level 3 (Competent)

You may optionally support an internal intermediate representation for future Advanced Beginner refinement, but do not overcomplicate this step.

Persist:
	•	selected choice
	•	derived level
	•	attempt count

C. Abilities scoring — “Engine Capacity”

Abilities do not use Dreyfus levels.

Use a weighted capacity score:
	•	Capacity = (Correctness × 0.7) + (TimeBonus × 0.3)

Time bonus

Design a stable time-bonus calculation for a 30-second limit.

Example target behavior:
	•	correct answer at 5 seconds → near-perfect result
	•	slower correct answer → lower time bonus
	•	incorrect answer → low score regardless of speed

Choose a clean deterministic formula and document it.

Special derived value

If:
	•	Logic + Quantitative is high enough, support calculation of a learningSpeedMultiplier

Use the provided idea:
	•	if (Logic + Quant) > 1.6, set learningSpeedMultiplier = 1.5x for technical courses

If naming differs because you map Logic to a specific Ability category, document the mapping clearly.

⸻

Persistence requirements

Persist KSA results so they can replace the current dummy student values.

A JSONB column is acceptable if it is the cleanest stable solution, but the overall persistence model must be maintainable and queryable enough for future learning logic.

The stored profile must support at minimum:
	•	user id
	•	KSA result set
	•	timestamp / last update
	•	topic-level levels and scores
	•	statuses for knowledge areas
	•	attempts where relevant
	•	ability scores
	•	derived values such as learning speed multiplier
	•	assessment metadata/version if useful

Example target structure

Use the following as a guiding example, but adapt field names cleanly to the actual codebase:

{
  "userId": "user_123",
  "overallPersona": "Builder",
  "ksaMap": {
    "knowledge": {
      "stem": { "level": 3, "score": 0.85, "status": "verified", "lastUpdate": "2023-10-27" },
      "it": { "level": 1, "score": 0.20, "status": "uncharted", "lastUpdate": null },
      "humanities": { "level": 2, "score": 0.50, "status": "self-reported", "lastUpdate": "2023-10-27" }
    },
    "skills": {
      "digitalCraft": { "level": 2, "proficiency": "Advanced Beginner", "attempts": 1 },
      "strategicExecution": { "level": 1, "proficiency": "Novice", "attempts": 1 }
    },
    "abilities": {
      "quantitative": 0.92,
      "logic": 0.88,
      "empathy": 0.65
    }
  },
  "learningSpeedMultiplier": 1.2
}

Important rule

Do not persist the old dummy student KSA values once a real initial KSA assessment exists.

Behavior should be:
	•	if user has no real KSA assessment → use current default/example values
	•	once first real KSA assessment is completed → use real persisted data instead
	•	no mixing of real and dummy values

⸻

Web UI requirements

1. Replace placeholder assessment dialog content

The KSA Assessment dialog already opens from the KSA tab.

Replace the placeholder starting screen with the real assessment flow.

Dialog requirements
	•	keep the current general dialog style consistent with the product
	•	support multi-step assessment flow
	•	show progress clearly
	•	support the different phase types cleanly
	•	handle timing in the ability phase
	•	support submission and completion

2. Assessment UX

The assessment should feel like a guided diagnostic, not a random survey.

Support:
	•	section transitions
	•	clear question text
	•	clear answer controls
	•	slider UI for Phase 1
	•	single-choice controls for knowledge and skill items
	•	timed interactions for abilities
	•	appropriate progress display

3. Result handling

After completion:
	•	compute results
	•	persist results
	•	close or transition cleanly
	•	refresh the KSA tab so the existing big-map visualization shows the real results

4. Keep KSA big-map visualization unchanged

Do not redesign the current KSA big-map layout.

Use the existing visualization and feed it real data.

If any minor adjustments are needed for data loading or labels, keep them minimal and do not change the overall presentation.

5. Uncharted territory behavior

For skipped topics:
	•	the stored result should reflect uncharted
	•	the UI mapping to the current chart should be handled cleanly
	•	if the current chart cannot visually distinguish status yet, store it anyway for future use

Do not force a new visualization redesign in this step.

⸻

Backend/API requirements

Add or update clean authenticated APIs for at minimum:
	•	getting KSA assessment definition/flow if backend-driven
	•	starting an assessment attempt
	•	saving answers
	•	completing/scoring an assessment
	•	fetching current KSA profile for the current user
	•	fetching last assessment result if needed

Keep request/response models typed and validated.

If a backend-driven definition model is cleaner, use it. Do not hardcode a brittle flow that will be impossible to extend later.

⸻

Architecture requirements

1. Keep KSA assessment separate from KSA display

Separate:
	•	KSA result storage
	•	KSA assessment flow
	•	KSA visualization mapping

This will make later reassessments and deep-dive steps easier.

2. Prepare for future mini-assessments

Although not implemented now, the architecture should support later:
	•	small follow-up attempts
	•	topic-specific reassessments
	•	partial map updates

Do not implement them now, but do not block them.

3. Keep scoring deterministic

For this initial assessment, prefer rule-based/deterministic scoring.

Do not use LLM scoring for the main core logic unless absolutely necessary for a limited sub-case, and if so document it clearly.

⸻

Validation requirements

This step is not complete when the dialog simply contains questions and produces some numbers.

It is complete only after the assessment flow, scoring, persistence, and result display work end to end and have been checked, tested, and debugged where necessary.

Validate at minimum:
	1.	Start Assessment opens the real KSA assessment flow
	2.	Phase 1 sliders work
	3.	Phase 1 correctly controls which topics are triggered
	4.	Knowledge questions render and score correctly
	5.	Skills questions render and score correctly
	6.	Ability tasks render and score correctly
	7.	timing works correctly for ability tasks
	8.	knowledge scoring follows the provided formula
	9.	skills scoring maps correctly
	10.	abilities scoring uses correctness + time bonus
	11.	untriggered areas are stored as uncharted
	12.	KSA results are persisted correctly
	13.	current dummy/example values are replaced by real results once assessment exists
	14.	existing KSA big-map visualization loads the real data correctly
	15.	no regression in the Learning page or related learning features

If issues are found:
	1.	identify root cause
	2.	debug and fix
	3.	rerun validation
	4.	update docs and changelog

⸻

Testing requirements

Update and/or add tests where practical for:
	•	Phase 1 trigger logic
	•	knowledge scoring formula
	•	skills level mapping
	•	abilities weighted score logic
	•	timing calculation
	•	persistence shape / JSONB mapping if used
	•	API flows for assessment start/save/complete
	•	loading KSA profile into chart data
	•	dummy-value override behavior
	•	frontend assessment flow

⸻

Documentation requirements

Update at minimum:
	•	README.md
	•	docs/learning.md
	•	docs/api.md
	•	docs/architecture.md
	•	docs/testing.md
	•	changelog.md

Also document:
	•	the KSA initial assessment flow
	•	the four phases
	•	the knowledge/skills/abilities scoring logic
	•	the meaning of uncharted
	•	how real KSA values replace dummy values
	•	current limitations before mini-assessments and deep-dive KSA are added

⸻

Deliverable expectations

When finished:
	•	the KSA Start Assessment dialog runs a real initial assessment
	•	the assessment uses the provided topic map and question bank
	•	the sieve logic works
	•	scoring works according to the provided algorithm
	•	KSA results are persisted cleanly
	•	the old dummy/example KSA values are no longer used once real data exists
	•	the existing KSA visualization now displays real assessment results
	•	the implementation is clean and future-ready
	•	tests/docs/changelog are updated
	•	the result has been verified and debugged if needed