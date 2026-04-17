okay now i need a codex prompt for some new step, in this step i want to make preparations for personalizing learning content. So we collected many many informations about the user and now we need to bring all of this together and make it usable for later use for personalization. So basically we will group some of the information etc and use this groups in a later step to write the according prompts, here are the groups we will use:
Group 1 — Identity & Context Layer (WHO the learner is)

Includes:
	•	Background (education, experience, skills, timeline)
	•	Profession / industry
	•	Interests
	•	Bio / self-description
	•	Language, culture, location
	•	Personal context notes
	•	Reason for learning

👉 Core function:
Create relevance, trust, and cognitive anchoring

⸻

Group 2 — Goals & Intent Layer (WHY they learn)

Includes:
	•	Target topic
	•	Target level
	•	Reason for learning
	•	Deadline / urgency
	•	Priority
	•	Success expectations (if added later)

👉 Core function:
Drive direction, difficulty, and decision-making

⸻

Group 3 — Declared Preferences Layer (HOW they WANT to learn)

Includes:
	•	Pace
	•	Depth
	•	Examples vs theory
	•	Structure
	•	Quiz frequency
	•	Encouragement
	•	Guidance
	•	Recap frequency
	•	Learning format
	•	Free note

👉 Core function:
Initial interaction contract

⸻

Group 4 — Diagnosed Learning Model (HOW they ACTUALLY learn)

Includes:
	•	LAA (behavioral learning traits)
	•	MOA (motivation drivers)
	•	LTA (learning modality)
	•	Diagnostic summaries
	•	Strengths / friction points

👉 Core function:
Override + refine declared preferences

⸻

Group 5 — Capability & Knowledge State (WHAT they CAN DO)

Includes:
	•	KSA Big Map levels
	•	KSA drill results
	•	Confidence levels
	•	Learning speed multiplier
	•	Skill tags

👉 Core function:
Difficulty calibration + progression logic

⸻

Group 6 — Live Adaptation Layer (WHAT IS HAPPENING NOW)

Includes:
	•	Mood
	•	Energy
	•	Perceived difficulty
	•	Explanation feedback
	•	Real-time needs (pause / more explanation / etc.)
	•	Behavioral analytics (streaks, drop-offs, time)

👉 Core function:
Real-time correction of teaching strategy

And here are all the informations we collect (and where we collect them) from a user:
Learning page, Profile tab: all user-editable inputs
- Left profile card/dialog: How to address, Location, Title, Date of birth, About.
- Right profile dialog: Work Experience (job/company pairs, add/remove rows), Education (degree/institute pairs, add/remove rows), Skills (comma-separated), Interests (comma-separated).
- Learning Context section: Current reason for learning, Additional learning context notes.
- Learning Goals table/actions:
- Add Goal dialog fields: Target topic, Reason for learning, Target level, Deadline (dd.mm.yyyy), Priority (low/medium/high), Notes.
- Existing goal row editable fields: Deadline (date input), Active toggle; actions Save, Delete.

Learning page, Preferences tab (excluding diagnostic)
- 10 preference controls:
   . Preferred pace: slow/balanced/fast.
   . Explanation depth: concise/balanced/detailed.
   . Examples vs theory: more_examples/balanced/more_theory.
   . Structure preference: more_structured/balanced/more_conversational.
   . Quiz/checkpoint frequency: low/medium/high.
   . Encouragement level: low/balanced/high.
   . Guidance level: step_by_step/balanced/more_independent.
   . Recap frequency: low/medium/high.
   . Preferred learning format: reading/dialogue/exercises/mixed.
   . Custom note (textarea).

Learning Preferences Diagnostic (LAA, MOA, LTA) scenario outputs in UI
LAA:
- No fixed “one-of-N final paragraph” blocks.
- UI shows bar chart + section accordions (User needs, Learning experience, Conditions, Objectives, Skills and Interests, Attitude, Support needs, Miscellaneous).
- Texts are assembled dynamically from templates in scoring:
   . Dimension insights (possible): goal clarity, time pressure, structure need, feedback need, self-direction, social orientation, emotional safety, frustration sensitivity, technical affinity, practical orientation, visibility motivation.
   . Section conditionals (possible): “Your strongest interest areas are…”, “In everyday life, you mostly rely on…”, “Your emotional learning stability is strong…/more variable…”, “External activation… can improve rhythm.”, “You benefit from clear plans…”, “Frequent feedback…”, “You prefer flexibility…”, “Visible progress… can motivate…”.
   . Fallbacks: “Your profile shows a balanced pattern in this area.” and “These section signals can be used for adaptive learning support.”
MOA:
- Exactly 45 pair scenarios (top-2 motivation dimensions) with one result block each.
- UI path: Personalized Motivation Profile accordion; it displays intro paragraphs + selected block title/text.
- 45 scenario titles: Knowledge&Creativity, Knowledge&Purpose, Knowledge&Achievement, Knowledge&Experimentation, Knowledge&Autonomy, Knowledge&Influence, Knowledge&Security, Creativity&Purpose, Creativity&Experimentation, Creativity&Achievement, Creativity&Autonomy, Purpose&Connection, Purpose&Influence, Purpose&Status, Connection&Influence, Connection&Status, Connection&Purpose, Connection&Autonomy, Security&Achievement, Security&Connection, Security&Status, Security&Purpose, Security&Influence, Security&Autonomy, Autonomy&Creativity, Autonomy&Experimentation, Autonomy&Influence, Autonomy&Achievement, Autonomy&Purpose, Autonomy&Status, Achievement&Influence, Achievement&Status, Achievement&Experimentation, Achievement&Connection, Achievement&Creativity, Experimentation&Creativity, Experimentation&Influence, Experimentation&Connection, Experimentation&Purpose, Experimentation&Status, Experimentation&Security, Experimentation&Autonomy, Experimentation&Achievement, Experimentation&Knowledge, Influence&Status.
LTA:
- 11 scenarios total (4 dominant + 6 mixed + 1 balanced), each with fixed text shown in Personal Learning Type accordion.
   . Dominant: Auditory, Visual, Kinesthetic, Reading/Writing.
   . Mixed: Auditory–Visual, Auditory–Kinesthetic, Auditory–Reading/Writing, Visual–Kinesthetic, Visual–Reading/Writing, Kinesthetic–Reading/Writing.
   . Balanced: Balanced profile.
- Classification rules used in scoring:
- balanced if max-min channel count <= 1.
- dominant if top-second >= 2.
- otherwise mixed.

KSA Big Map topics and K/S/A classification
K: STEM Fundamentals, Information Technology, Humanities & Social Sciences, Languages & Linguistics, Business & Commerce, Legal & Ethics, Health & Wellness.
S: Literacy & Numeracy, Digital Craft, Strategic Execution, Operational Skills, Relational Skills, Research & Inquiry.
A: Quantitative Reasoning, Verbal Comprehension, Spatial Visualization, Executive Function, Sensory-Perceptual, Social-Emotional Capacity, Divergent Thinking.

KSA Deep Dive drill assessment: what results are produced
User flow:
- Enter topic text.
- Topic classification confirmation (primary_type, optional secondary_type, type_combo, big_map_group, big_map_subdomain, detailed_topic, user_explanation).
- 4-round generated drill; each round generates 4 questions (16 total).
- Question kinds: recalibration, threshold, sidestep, stress_test (15s target for stress test).
- Persisted/computed result output includes:
- topic_updates per topic: initial_level, delta, final_level, chart_level, sub_nodes, block-level pass/fail, map decay counters.
- drill_flow metadata, completion timestamp/version.
- Side effects on profile:
   . KSA levels updated.
   . confidence adjusted.
   . map-decay status may be set.
   . derived learning_speed_multiplier recalculated from executive + quantitative proxies.
- UI result surface:
   . “Assessment Drill Attempts” table with Completed date, topic badges, total DELTA.
   . Expandable rounds list and detailed round topic labels.
   . Completion message: “Drill Assessment Completed… map refined…”

Library: what users can do
- View file table with status, tags, size, chunk count, type, embedded state, owner/source labels.
- Upload files (multi-file):
   . per-file tags (comma-separated), default tag auto-applied if empty.
- extension/type checks, max-file limit, duplicate check.
- Enable/disable files (per user scope/permissions).
- Delete files (permission-gated).
- Toggle Show other users' files to include shared/other-user files in listing.
- Tag filtering:
   . In library itself: tags are displayed; no inline tag-filter control there.
   . Actual filter controls live in Preferences dialog Filter tab (global/chat scoped tag/file toggles).

Preferences dialog, Personalization tab options
- - Base style: default, professional, friendly, direct, quirky, efficient, sceptical.
Characteristics (each: more/default/less):
   . Warm
   . Enthusiastic
   . Headers and Lists
- Custom Instructions (textarea).
- Nickname.
- Occupation.
- More about you.

Preferences dialog, Settings tab options
- History Messages (number).
- Max Similarities (number).
- Min Similarities (number).
- Cosine Limit (similarity_score_threshold, 0..1 step 0.01).

Assistant modes and step pipelines
Modes: simple, refine, thinking.
- simple: 1 generation stage (single-pass answer after retrieval/context assembly).
- refine: 2 LLM stages.
   . Step 1: draft generation.
   . Step 2: refine draft into final answer.
- thinking: 3 LLM stages.
   . Step 1: planning.
   . Step 2: drafting.
   . Step 3: refining.
If thinking fails, backend falls back to simple mode.

Courses page: what appears in courses table
- Columns: Name, Scope, Owner, Status, Nodes, Modules, Lessons, Updated, Actions.
- Toolbar filters: search, scope filter, status filter, sort.
- Row actions: Start/Continue, archive/unarchive, edit (placeholder), delete (permission-based).

Course details (DevOps Roadmap Learning Tree): how your course system works
This course (current JSON) has:
- 5 chapters, 3 branches, 41 nodes, 83 edges, 1 entry node.
- Branches (“routes” in this course naming): Core Route (required), Alternative Route (optional), Optional Route (optional).

System model:
- Chapters = content grouping/progression slices.
- Branches = parallel route tracks with required/optional semantics.
- Nodes = executable learning/progression units.
- Edges = dependency/recommendation graph (requires_all, requires_any, recommended, optional).
- Entry nodes = start points.

Node types supported: learning_unit, practice, quiz, checkpoint, review, milestone, capstone, unlock_gate, assessment_hook.

Node completion modes: lesson_complete, practice_complete, quiz_pass, checkpoint_pass, review_complete, manual, gate_unlock, assessment_threshold.

Per-node option groups available in schema:
- prerequisites (requires_all, requires_any, recommended)
- required flag
- chapter_id, branch_id
- estimated duration, layout, metadata/display
- KSA links (dimension/topic/subtopic/start/target/weight/unlocks_assessment_check/recommends_assessment_check)
- unlock metadata (node_ids/branch_ids/recommended_next)
- rewards metadata
- retrospective hooks
- ksa hooks
- remediation metadata
- adaptive unlock rules (KSA thresholds, required branches/checkpoints, review requirements, recommended-only)

Runtime connection to KSA:
- Node KSA mappings drive side-panel “KSA Links”.
- Assessment-hook and KSA hook flags feed recommendation/hook summary logic.
- Progress/runtime states computed from dependencies and completion state (locked, available, in_progress, completed, mastered, optional_skipped, failed_needs_retry, awaiting_checkpoint).
- UI node actions depend on runtime state: Start/Continue, Reset, Skip (optional nodes).


so we need to run this grouping for each group whenever a information/setting etc of one group was changed. so with this grouping we will:

Group 1 — Identity, Context, and Social Framing

This group answers: Who is this learner and how should the system socially and contextually frame teaching?

Includes
	•	preferred form of address
	•	full/display name or nickname
	•	language / locale / country context
	•	profession / role / industry
	•	education background
	•	work experience
	•	study history
	•	skills
	•	interests
	•	bio / about
	•	personal learning context notes
	•	reason for learning

⸻

What rules this group should control

This group should control only these rule families:

A. Addressing rules
	•	formality
	•	naming
	•	pronoun/salutation behavior

B. Contextualization rules
	•	example domain
	•	analogy domain
	•	scenario framing
	•	vocabulary familiarity assumptions

C. Relevance framing rules
	•	how often to connect material to job, hobby, project, exam, career, etc.

D. Background assumption rules
	•	whether to assume academic familiarity
	•	whether to assume workplace exposure
	•	whether to avoid discipline-specific jargon

⸻

Exact rule changes by field

1. Preferred form of address

Values
	•	first name
	•	nickname
	•	formal / less formal

Rule effects
	•	address_mode = formal | neutral | informal
	•	name_token = chosen_name
	•	use_direct_name_frequency = low | medium | high

Example mapping
	•	formal → use surname/title if available, avoid overly casual encouragement
	•	nickname → use nickname consistently, warmer social framing allowed
	•	less formal → plain, friendly wording

⸻

2. Language / locale

Rule effects
	•	response_language
	•	cultural_example_filter
	•	idiom_usage = low unless locale-safe
	•	technical_vocabulary_ceiling

Mapping
	•	non-native language confidence low → shorter sentences, fewer idioms, more glossary-style phrasing
	•	locale known → examples may use regionally familiar systems only if pedagogically useful

⸻

3. Profession / role / industry

Rule effects
	•	preferred_example_domains
	•	preferred_case_types
	•	baseline_domain_familiarity
	•	professional_relevance_weight

Mapping
	•	developer → use software examples before generic business examples
	•	nurse → use healthcare workflow examples
	•	student → use study/project/exam examples
	•	unemployed / transition → avoid over-anchoring to one profession

⸻

4. Education background

Rule effects
	•	assumed_theoretical_tolerance
	•	assumed_academic_jargon_tolerance
	•	need_for_concept_unpacking

Mapping
	•	school level → explain terms more explicitly
	•	university → tolerate more abstraction if other signals allow
	•	self-taught → use practical-first framing, define formal terms clearly
	•	vocational → application-first, task-centered framing often preferred

⸻

5. Skills / experience / timeline

Rule effects
	•	skip_known_basics = yes/no by topic
	•	analogy_source_priority
	•	bridge_from_prior_knowledge
	•	estimated_transfer_capacity

Mapping
	•	if learner has adjacent skill → teach by bridge analogy
	•	if direct prior experience exists → compress basics
	•	if inconsistent timeline → do not assume stable mastery

⸻

6. Interests

Rule effects
	•	motivation_context_pool
	•	example_personalization_pool
	•	story_context_pool

Mapping
	•	use interests only to make examples more engaging
	•	never allow interests to distort conceptual accuracy

⸻

7. Bio / about / personal notes

Rule effects
	•	identity_sensitive_framing
	•	constraint_flags
	•	avoidance_flags
	•	relevance_notes

Mapping
	•	“I get overwhelmed easily” → lower default cognitive load
	•	“I’m preparing for an interview” → increase practical, performance-oriented framing
	•	“I hate abstract theory” → stronger example-first default

⸻

Persistence recommendation

Persist all of this as mostly stable profile state, but split into:
	•	identity_profile
	•	context_profile
	•	example_relevance_profile
	•	constraints_profile


Group 2 — Goals and Success Framing

This group answers: What is the learner trying to achieve, how urgently, and what counts as useful progress?

Includes
	•	target topic
	•	target level
	•	reason for learning
	•	deadline
	•	priority
	•	notes
	•	active toggle
	•	optional future addition: success indicators

⸻

What rules this group controls

A. Scope rules
	•	breadth vs focus
	•	essentials-first vs comprehensive

B. Difficulty target rules
	•	beginner/intermediate/advanced level target

C. Urgency rules
	•	pacing pressure
	•	recap compression
	•	checkpoint density

D. Utility framing rules
	•	exam-first
	•	project-first
	•	job-first
	•	curiosity-first

⸻

Exact rule changes by field

1. Target topic

Rule effects
	•	topic_scope
	•	allowed_example_space
	•	concept_dependency_map

This should mostly route node/course selection, not conversation style.

⸻

2. Target level

Rule effects
	•	target_abstraction_level
	•	target_independence_level
	•	acceptable_scaffolding_depth
	•	mastery_threshold_profile

Mapping
	•	beginner → define terms, concrete examples, narrow steps
	•	intermediate → less hand-holding, more comparison and application
	•	advanced → synthesis, edge cases, independent reasoning

⸻

3. Reason for learning

Rule effects
	•	utility_frame = exam | project | work | hobby | transition
	•	example_selection_priority
	•	assessment_style_bias

Mapping
	•	exam prep → retrieval practice + concept discrimination
	•	project need → task-first, “do this in context”
	•	career growth → standards and transferable understanding
	•	hobby → lower pressure, curiosity-friendly exploration

⸻

4. Deadline

Rule effects
	•	pace_pressure
	•	focus_narrowing
	•	remediation_tolerance
	•	enrichment_suppression

Mapping
	•	near deadline → cut nice-to-have material, prioritize minimum viable mastery
	•	no deadline → allow broader conceptual depth

⸻

5. Priority

Rule effects
	•	goal_attention_weight
	•	review_frequency_weight

Mapping
	•	high priority → more reminders to connect node to main goal
	•	low priority → less interruption for relevance framing

⸻

6. Success indicators, if you add them

Examples:
	•	“I want to explain it confidently”
	•	“I want to solve tasks without help”

Rule effects
	•	session_success_check_type
	•	end_of_node_reflection_prompt_type

This is worth adding.

⸻

Persistence recommendation

Store as:
	•	learning_goals[]
	•	one active_goal_id
	•	goal_rule_snapshot per active goal

That last part matters. You want a precomputed rule snapshot for fast prompt generation.


Group 3 — Declared Learning Preferences

This group answers: How does the learner say they want the tutor to teach?

Includes
	•	pace
	•	explanation depth
	•	examples vs theory
	•	structure preference
	•	quiz frequency
	•	encouragement level
	•	guidance level
	•	recap frequency
	•	preferred learning format
	•	custom note

⸻

What rules this group controls

This group should produce initial explicit tutor settings:
	•	response length
	•	explanation granularity
	•	explanation order
	•	structure density
	•	check frequency
	•	scaffolding strength
	•	recap interval
	•	exercise ratio
	•	tone warmth

This group should not directly control difficulty or mastery thresholds.

⸻

Exact rule changes by field

1. Preferred pace

Values
	•	slow
	•	balanced
	•	fast

Rule effects
	•	step_size
	•	concepts_per_turn
	•	advance_without_confirmation_threshold

Mapping
	•	slow → 1 concept at a time, explicit transition checks
	•	balanced → normal chunking
	•	fast → larger chunks, fewer confirmation checks

⸻

2. Explanation depth

Rule effects
	•	default_explanation_depth
	•	definition_density
	•	include_secondary_detail

Mapping
	•	concise → shortest viable explanation
	•	balanced → core explanation + one key detail
	•	detailed → layered explanation + nuance

⸻

3. Examples vs theory

Rule effects
	•	explanation_order = example_first | mixed | concept_first
	•	example_density
	•	abstraction_delay

Mapping
	•	more examples → example first, then generalization
	•	balanced → concept + example
	•	more theory → conceptual frame first

⸻

4. Structure preference

Rule effects
	•	format_structure_level
	•	uses_lists
	•	uses_signposting
	•	paragraph_length_target

Mapping
	•	structured → headings, steps, bullets
	•	conversational → natural prose, fewer lists
	•	balanced → moderate structure

⸻

5. Quiz frequency

Rule effects
	•	micro_check_interval
	•	retrieval_prompt_frequency

Mapping
	•	low → fewer interruptions
	•	high → frequent tiny checks

⸻

6. Encouragement level

Rule effects
	•	encouragement_frequency
	•	affirmation_style

Mapping
	•	low → minimal encouragement, mostly neutral
	•	high → frequent but evidence-based encouragement

⸻

7. Guidance level

Rule effects
	•	scaffolding_strength
	•	hint_before_answer
	•	independence_expectation

Mapping
	•	step-by-step → explicit sequence, no large jumps
	•	more independent → shorter prompts, more learner effort first

⸻

8. Recap frequency

Rule effects
	•	recap_interval
	•	mini_summary_frequency

⸻

9. Preferred learning format

Rule effects
	•	response_mode_bias = reading | dialogue | exercises | mixed

Mapping
	•	reading → explanation-heavy
	•	dialogue → interactive Socratic style
	•	exercises → action-first
	•	mixed → rotate format

⸻

10. Custom note

This should be parsed into additional explicit flags.

Examples:
	•	“please explain slowly” → reinforce low step size
	•	“avoid too much theory” → lower abstraction
	•	“use practical examples” → example-first

Rule effects
	•	custom_preference_flags[]

⸻

Persistence recommendation

Store:
	•	raw preferences
	•	parsed flags
	•	resolved initial rule set

For example:
	•	declared_preferences
	•	declared_preference_flags
	•	resolved_declared_tutor_rules


Group 4 — Diagnosed Learning Profile

This group answers: What does the system infer about how the learner learns best and what support they need?

Includes
	•	LAA dimensions
	•	MOA dimensions
	•	LTA distribution
	•	summaries
	•	strengths
	•	friction points
	•	teaching recommendations
	•	diagnostic answer history
	•	versioning

⸻

What rules this group controls

This group should not be passed raw to the model. It should resolve into:
	•	support intensity
	•	motivational framing type
	•	format support type
	•	self-regulation support
	•	emotional safety level
	•	feedback density
	•	autonomy vs structure balance

⸻

Exact rule changes by subsystem

⸻

4A. LAA

I’ll use the dimensions you listed.

Zielklarheit / goal clarity

Rule effects
	•	goal_restatement_frequency
	•	orientation_density

Mapping
	•	low → frequently state why current step matters
	•	high → less orientation overhead

⸻

Nachhaltigkeit

Rule effects
	•	retention_support_level
	•	spacing_recap_bias

Mapping
	•	low → more recap and retrieval
	•	high → normal recap

⸻

Lernerfahrung

Rule effects
	•	novice_handling_level

Mapping
	•	low → more explicit teaching mechanics
	•	high → quicker progression

⸻

Feedbackoffenheit

Rule effects
	•	feedback_directness
	•	error_correction_explicitness

Mapping
	•	low → gentler feedback wording
	•	high → more direct corrective feedback

⸻

Lernumgebung

Rule effects
	•	distraction_resilience_support
	•	chunk_size_adjustment

Mapping
	•	unstable learning environment → shorter tasks and stronger re-orientation

⸻

Zielmotivation

Rule effects
	•	motivation_reminder_frequency

Mapping
	•	low → more relevance reminders
	•	high → less motivational scaffolding

⸻

Kompetenzprofil

Rule effects
	•	mostly routing and difficulty calibration with KSA

⸻

Selbstwirksamkeit

Rule effects
	•	confidence_support_level
	•	difficulty_jump_limit
	•	mistake_normalization_frequency

Mapping
	•	low → smaller jumps, more progress evidence
	•	high → allow more challenge

⸻

Individualisierungswunsch

Rule effects
	•	personalization_visibility
	•	choice_frequency

Mapping
	•	high → more explicit adaptation and more format choices
	•	low → less overt personalization

⸻

structure need

Rule effects
	•	structure_level_override

⸻

frustration sensitivity

Rule effects
	•	frustration_protection_level
	•	max_consecutive_failures_before_reframe

⸻

practical orientation

Rule effects
	•	application_bias

⸻

technical affinity

Rule effects
	•	tool_jargon_tolerance
	•	system_example_complexity

⸻

social orientation

Rule effects
	•	collaborative_framing_bias

⸻

emotional safety

Rule effects
	•	correction_softness
	•	failure_language_sensitivity

⸻

time pressure

Rule effects
	•	response_compaction
	•	focus_on_essentials

⸻

visibility motivation

Rule effects
	•	progress_visibility_frequency

⸻

4B. MOA

This should map into motivation strategy rules, not general style.

For each dominant dimension, assign framing patterns.

Autonomy
	•	offer_bounded_choices = true
	•	command_tone = reduced
	•	self-direction prompts = increased

Purpose / meaning
	•	relevance_explanation_frequency = high

Achievement
	•	performance_feedback_visibility = high
	•	challenge_signal = moderate-high

Status
	•	milestone framing = stronger
	•	visible standards = stronger

Creativity
	•	open-ended variants = more allowed

Security
	•	predictability = high
	•	surprise tasking = low

Connection / belonging
	•	human-centered examples = higher

Influence
	•	impact framing = stronger

Knowledge
	•	conceptual richness allowed = higher

Experimentation
	•	what-if exploration = increased

Important:
Use only top 1–2 motivational drivers. Do not blend all.

⸻

4C. LTA

This should only affect representation style, not core pedagogy.

Auditory
	•	dialogic_explanation_bias
	•	read-aloud natural phrasing

Visual
	•	spatial/structural wording
	•	comparative formatting
	•	described diagrams where relevant

Kinesthetic
	•	practice-first bias
	•	action steps

Reading/Writing
	•	text clarity + definitions + summaries

Mixed
	•	rotate modes

Balanced
	•	no strong bias

⸻

Persistence recommendation

Store:
	•	raw diagnostic results
	•	normalized dimensions
	•	resolved teaching directives
	•	history over time

Suggested entities:
	•	diagnostic_attempts
	•	active_diagnostic_profile
	•	resolved_diagnostic_rules
	•	diagnostic_change_log


Group 5 — Capability and Mastery State

This group answers: What can the learner currently do, and how much support is appropriate right now?

Includes
	•	KSA big map
	•	deep dive drill results
	•	topic levels
	•	confidence adjustments
	•	learning speed multiplier
	•	pass/fail blocks
	•	weak/strong areas
	•	map decay counters
	•	skill tags if validated

⸻

What rules this group controls

This is one of the strongest groups. It should control:
	•	starting difficulty
	•	allowed concept jump size
	•	whether to skip basics
	•	whether to use remediation
	•	hint density
	•	whether to ask or tell
	•	node readiness
	•	mastery confidence

⸻

Exact rule changes

1. Initial level / final level per topic

Rule effects
	•	topic_difficulty_band
	•	entry_point_depth
	•	skip_intro_basics

Mapping
	•	low level → start concrete
	•	medium → medium abstraction
	•	high → independent application first

⸻

2. Delta and recent growth

Rule effects
	•	challenge_ramp_rate

Mapping
	•	strong recent positive delta → can increase challenge
	•	negative/flat → hold or reduce challenge

⸻

3. Confidence

Rule effects
	•	confidence_sensitive_support

Important:
Confidence should not equal competence.

You need both:
	•	competence_estimate
	•	confidence_estimate

Rule examples:
	•	low competence + high confidence → increase checking
	•	high competence + low confidence → encourage and require demonstration
	•	low competence + low confidence → scaffold heavily

⸻

4. Learning speed multiplier

Rule effects
	•	response_compaction
	•	practice_count_before_advance

Use carefully. This should tune pacing, not quality.

⸻

5. Block pass/fail by sub-node

Rule effects
	•	required_remediation_topics[]
	•	cannot_advance_flags[]

⸻

6. Map decay counters

Rule effects
	•	review_priority
	•	recall_check_bias

⸻

7. Strong topics / weak topics

Rule effects
	•	bridge_from_strengths
	•	protect_against_overchallenge_in_weak_topics

⸻

Persistence recommendation

Store this separately as a dynamic capability model:
	•	ksa_topic_state
	•	topic_mastery_estimates
	•	topic_confidence_estimates
	•	review_decay_state
	•	recent_assessment_history

This should be highly queryable by topic/subtopic.


Group 6 — Live Session Adaptation

This group answers: How is the learner doing right now in this session and this node?

Includes
	•	mood
	•	energy
	•	current difficulty perception
	•	need for pause
	•	need for more explanation
	•	need for more challenge
	•	need for different format
	•	explanation rating
	•	explanation free text
	•	recurring feedback patterns
	•	response latency
	•	struggle streak
	•	success streak
	•	drop-off risk

⸻

What rules this group controls

This group should override most others for the current turn. It controls:
	•	turn length
	•	turn complexity
	•	next teaching move
	•	whether to pause / recap / simplify / challenge
	•	whether to ask fewer questions
	•	whether to switch format now

⸻

Exact rule changes

1. Mood

Rule effects
	•	supportive_tone_adjustment
	•	challenge_suppression_if_needed

Mapping:
	•	low/negative mood → reduce friction, use less demanding wording

⸻

2. Energy

Rule effects
	•	response_energy_budget
	•	task_size

Mapping:
	•	low energy → short turns, one action only

⸻

3. Perceived difficulty

Rule effects
	•	complexity_adjustment
	•	worked_example_bias

Mapping:
	•	too difficult → simplify and work through example
	•	too easy → increase challenge or reduce explanation

⸻

4. Needs pause

Rule effects
	•	offer_pause_or_micro-stop = true

⸻

5. Needs more explanation

Rule effects
	•	expand_current_concept = true

⸻

6. Needs more challenge

Rule effects
	•	increase_independence = true

⸻

7. Needs different format

Rule effects
	•	format_override

⸻

8. Explanation rating + feedback

Rule effects
These should update:
	•	explanation_length_preference_observed
	•	example_bias_observed
	•	structure_need_observed
	•	language_simplicity_need_observed

Examples:
	•	“too long” → shorten next turn
	•	“too abstract” → example-first
	•	“too complicated” → simpler vocabulary
	•	“step by step please” → stronger scaffolding

⸻

9. Repeated error pattern

Rule effects
	•	must_change_strategy = true

This is very important.

⸻

10. Drop-off risk

Rule effects
	•	reduce_turn_burden
	•	increase_relevance_visibility
	•	avoid_multi-part tasks

⸻

Persistence recommendation

Split this into:

session-state

temporary
	•	current_session_state
	•	node_session_state

persistent learned adaptation memory

longer-lived
	•	observed_preference_patterns
	•	effective_strategy_patterns
	•	ineffective_strategy_patterns

Do not persist raw mood forever as a stable identity trait. Persist only patterns if repeated.









Group 1 resolved_identity_context_rules
address_mode: neutral
name_token: "Anna Smith"
technical_vocabulary_ceiling: medium
need_for_concept_unpacking: high

Group 2 resolved_goal_rules
utility_frame: project
target_abstraction_level: mixed
pace_pressure: low
assessment_style_bias: deliverable_based

Group 3 resolved_declared_tutor_rules
response_length: standard
explanation_order: mixed
scaffolding_strength: medium
nested tutor rules include step_size: small, concepts_per_turn: 1, hint_before_answer: true, response_mode_bias: mixed

Group 4 resolved_diagnostic_rules
support_intensity: medium
motivational_framing_type: achievement
format_support_type: neutral
technical_jargon_tolerance: high
moa_directives: conceptual richness + high feedback visibility
lta_directives: classification: balanced, dominant includes visuell

Group 5 resolved_capability_rules
starting_difficulty: medium
use_remediation: true
node_readiness: needs_review
recall_check_bias: high
remediation topics currently include stem_fundamentals, information_technology, humanities_social_sciences, languages_linguistics, business_commerce, digital_craft, quantitative_reasoning, verbal_comprehension, social_emotional_capacity

Group 6 resolved_live_adaptation_rules
next_teaching_move: continue_balanced
turn_length: medium
turn_complexity: medium
increase_relevance_visibility: true
no active pause/challenge/format override flags