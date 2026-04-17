Step: Build the learning-personalization rule engine foundation by grouping collected learner data into 6 resolved personalization layers

Work on the existing project and implement the foundation layer for learning-content personalization.

This step is not yet about writing the final teaching prompts.
It is about taking the many pieces of learner data already collected across the system and turning them into stable grouped rule layers that can later be used for prompt generation, teaching strategy, and adaptive learning behavior.

Before making code changes, inspect the current codebase and current:
	•	learning profile data from the Learning page Profile tab
	•	learning goals and active goal logic
	•	declared learning preferences
	•	diagnostics (LAA, MOA, LTA) results and storage
	•	KSA big map and drill result storage
	•	live adaptation data (mood, explanation feedback, session-state-like data)
	•	personalization settings
	•	assistant modes
	•	learning engine / learning chats
	•	persistence layer and migrations
	•	any existing resolved-profile or computed-rule patterns

⸻

Objective

Create a grouped personalization-rule system that transforms raw learner information into six resolved personalization groups.

These groups must:
	•	collect the right source fields
	•	normalize and structure them
	•	compute rule outputs from them
	•	persist the computed/resolved rule sets
	•	update automatically whenever relevant source data changes
	•	be ready for later prompt generation and teaching orchestration

This step is the rule-engine preparation layer for personalized learning content.

⸻

Core concept

The system currently collects a large amount of learner data from:
	•	Learning page Profile tab
	•	Learning page Preferences tab
	•	Learning Preference Diagnostic (LAA/MOA/LTA)
	•	KSA Big Map and KSA drills
	•	Library and user context
	•	Personalization settings
	•	learning goals
	•	live feedback and adaptation signals
	•	course/tree runtime state

This step must bring all of that together into six groups:
	1.	Group 1 — Identity & Context Layer
	2.	Group 2 — Goals & Intent Layer
	3.	Group 3 — Declared Preferences Layer
	4.	Group 4 — Diagnosed Learning Model
	5.	Group 5 — Capability & Knowledge State
	6.	Group 6 — Live Adaptation Layer

Each group must produce:
	•	a structured grouped profile object
	•	a resolved rule set
	•	persistence and recomputation behavior

⸻

Group definitions and required behavior

Group 1 — Identity & Context Layer

Purpose

Answer:
	•	who the learner is
	•	how the system should socially and contextually frame teaching

Source data to use

Use and group the following user data where available:

From Learning page Profile tab:
	•	preferred form of address
	•	full/display name or nickname
	•	location
	•	title
	•	date of birth if useful and legally/safely handled
	•	about / bio
	•	work experience
	•	education
	•	skills
	•	interests
	•	current reason for learning
	•	additional learning context notes

Also include where available:
	•	language / locale / country context
	•	profession / role / industry
	•	study history
	•	personal context notes

Resolved subprofiles to compute

Group 1 should resolve into at minimum:
	•	identity_profile
	•	context_profile
	•	example_relevance_profile
	•	constraints_profile

Rule families this group must control

This group must resolve rules for:

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
	•	frequency of connecting material to job, hobby, project, exam, career, etc.

D. Background assumption rules
	•	whether to assume academic familiarity
	•	whether to assume workplace exposure
	•	whether to avoid discipline-specific jargon

Exact field-to-rule mappings

Implement the following logic:

Preferred form of address
Possible outputs:
	•	address_mode = formal | neutral | informal
	•	name_token = chosen_name
	•	use_direct_name_frequency = low | medium | high

Mapping examples:
	•	formal → use surname/title if available, avoid casual social framing
	•	nickname → use nickname consistently, warmer framing allowed
	•	less formal → plain friendly wording

Language / locale
Possible outputs:
	•	response_language
	•	cultural_example_filter
	•	idiom_usage
	•	technical_vocabulary_ceiling

Mapping examples:
	•	lower non-native confidence → shorter sentences, fewer idioms, simpler phrasing
	•	locale known → regionally familiar examples only where useful

Profession / role / industry
Possible outputs:
	•	preferred_example_domains
	•	preferred_case_types
	•	baseline_domain_familiarity
	•	professional_relevance_weight

Education background
Possible outputs:
	•	assumed_theoretical_tolerance
	•	assumed_academic_jargon_tolerance
	•	need_for_concept_unpacking

Skills / experience / timeline
Possible outputs:
	•	skip_known_basics
	•	analogy_source_priority
	•	bridge_from_prior_knowledge
	•	estimated_transfer_capacity

Interests
Possible outputs:
	•	motivation_context_pool
	•	example_personalization_pool
	•	story_context_pool

Bio / about / personal notes
Possible outputs:
	•	identity_sensitive_framing
	•	constraint_flags
	•	avoidance_flags
	•	relevance_notes

⸻

Group 2 — Goals & Intent Layer

Purpose

Answer:
	•	what the learner is trying to achieve
	•	how urgently
	•	what counts as useful progress

Source data to use

From Learning Goals and related profile/context data:
	•	target topic
	•	target level
	•	reason for learning
	•	deadline
	•	priority
	•	notes
	•	active toggle
	•	future-ready support for success indicators if later added

Persistence recommendation

Implement/support:
	•	learning_goals[]
	•	active_goal_id
	•	goal_rule_snapshot

The goal_rule_snapshot is important and should be precomputed for fast later use.

Rule families this group must control

A. Scope rules
	•	breadth vs focus
	•	essentials-first vs comprehensive

B. Difficulty target rules
	•	beginner/intermediate/advanced target

C. Urgency rules
	•	pacing pressure
	•	recap compression
	•	checkpoint density

D. Utility framing rules
	•	exam-first
	•	project-first
	•	job-first
	•	curiosity-first

Exact field-to-rule mappings

Implement:

Target topic
Controls:
	•	topic_scope
	•	allowed_example_space
	•	concept_dependency_map

Target level
Controls:
	•	target_abstraction_level
	•	target_independence_level
	•	acceptable_scaffolding_depth
	•	mastery_threshold_profile

Reason for learning
Controls:
	•	utility_frame = exam | project | work | hobby | transition
	•	example_selection_priority
	•	assessment_style_bias

Deadline
Controls:
	•	pace_pressure
	•	focus_narrowing
	•	remediation_tolerance
	•	enrichment_suppression

Priority
Controls:
	•	goal_attention_weight
	•	review_frequency_weight

Success indicators
Future-ready support only, if present:
	•	session_success_check_type
	•	end_of_node_reflection_prompt_type

⸻

Group 3 — Declared Preferences Layer

Purpose

Answer:
	•	how the learner says they want the tutor to teach

Source data to use

From Learning page Preferences tab:
	•	preferred pace
	•	explanation depth
	•	examples vs theory
	•	structure preference
	•	quiz/checkpoint frequency
	•	encouragement level
	•	guidance level
	•	recap frequency
	•	preferred learning format
	•	custom note

Persistence recommendation

Store:
	•	declared_preferences
	•	declared_preference_flags
	•	resolved_declared_tutor_rules

Rule families this group must control

This group should resolve initial tutor settings for:
	•	response length
	•	explanation granularity
	•	explanation order
	•	structure density
	•	check frequency
	•	scaffolding strength
	•	recap interval
	•	exercise ratio
	•	tone warmth

Exact field-to-rule mappings

Implement:

Preferred pace
Controls:
	•	step_size
	•	concepts_per_turn
	•	advance_without_confirmation_threshold

Explanation depth
Controls:
	•	default_explanation_depth
	•	definition_density
	•	include_secondary_detail

Examples vs theory
Controls:
	•	explanation_order = example_first | mixed | concept_first
	•	example_density
	•	abstraction_delay

Structure preference
Controls:
	•	format_structure_level
	•	uses_lists
	•	uses_signposting
	•	paragraph_length_target

Quiz frequency
Controls:
	•	micro_check_interval
	•	retrieval_prompt_frequency

Encouragement level
Controls:
	•	encouragement_frequency
	•	affirmation_style

Guidance level
Controls:
	•	scaffolding_strength
	•	hint_before_answer
	•	independence_expectation

Recap frequency
Controls:
	•	recap_interval
	•	mini_summary_frequency

Preferred learning format
Controls:
	•	response_mode_bias = reading | dialogue | exercises | mixed

Custom note
Parse into:
	•	custom_preference_flags[]

Examples:
	•	explain slowly
	•	avoid too much theory
	•	use practical examples

⸻

Group 4 — Diagnosed Learning Profile

Purpose

Answer:
	•	what the system infers about how the learner actually learns best
	•	what support they need

Source data to use

Use:
	•	LAA dimensions and section outputs
	•	MOA results
	•	LTA distribution and result class
	•	diagnostic summaries
	•	strengths
	•	friction points
	•	teaching recommendations
	•	diagnostic answer history
	•	diagnostic versioning

Persistence recommendation

Store/support:
	•	diagnostic_attempts
	•	active_diagnostic_profile
	•	resolved_diagnostic_rules
	•	diagnostic_change_log

Important rule

Do not pass raw diagnostic data directly to future prompt generation.
This group must resolve diagnostics into usable teaching directives.

Rule families this group must control

Resolve into:
	•	support intensity
	•	motivational framing type
	•	format support type
	•	self-regulation support
	•	emotional safety level
	•	feedback density
	•	autonomy vs structure balance

Exact subsystem mappings

4A. LAA
Use dimensions such as:
	•	Zielklarheit
	•	Nachhaltigkeit
	•	Lernerfahrung
	•	Feedbackoffenheit
	•	Lernumgebung
	•	Zielmotivation
	•	Kompetenzprofil
	•	Selbstwirksamkeit
	•	Individualisierungswunsch
	•	structure need
	•	frustration sensitivity
	•	practical orientation
	•	technical affinity
	•	social orientation
	•	emotional safety
	•	time pressure
	•	visibility motivation

Implement rule effects exactly along the provided logic, for example:
	•	low Zielklarheit → goal_restatement_frequency higher
	•	low Nachhaltigkeit → retention_support_level higher
	•	low Selbstwirksamkeit → smaller difficulty jumps, more progress evidence
	•	high Individualisierungswunsch → more visible personalization / more format choices
	•	frustration sensitivity → stronger frustration protection, lower tolerance for repeated failure
	•	technical affinity → higher tool/jargon tolerance
	•	time pressure → more compaction and essentials-first framing

4B. MOA
Use only top 1–2 motivational drivers to produce motivational framing rules.

Possible dominant drivers include:
	•	Autonomy
	•	Purpose / Meaning
	•	Achievement
	•	Status
	•	Creativity
	•	Security
	•	Connection / Belonging
	•	Influence
	•	Knowledge
	•	Experimentation

Resolve into things like:
	•	offer_bounded_choices
	•	relevance_explanation_frequency
	•	performance_feedback_visibility
	•	milestone_framing
	•	open_ended_variants
	•	predictability
	•	human_centered_examples
	•	impact_framing
	•	conceptual_richness_allowed
	•	what_if_exploration

4C. LTA
Use LTA only for representation style, not core pedagogy.

Resolve into things like:
	•	auditory → dialogic_explanation_bias
	•	visual → spatial_structural_wording, comparative formatting
	•	kinesthetic → practice_first_bias, action steps
	•	reading/writing → text_clarity, definitions, summaries
	•	mixed → rotate modes
	•	balanced → no strong bias

⸻

Group 5 — Capability & Knowledge State

Purpose

Answer:
	•	what the learner can currently do
	•	how much support is appropriate right now

Source data to use

Use:
	•	KSA big map
	•	KSA drill results
	•	topic levels
	•	confidence adjustments
	•	learning speed multiplier
	•	pass/fail blocks
	•	weak/strong areas
	•	map decay counters
	•	validated skill tags

Persistence recommendation

Store/support:
	•	ksa_topic_state
	•	topic_mastery_estimates
	•	topic_confidence_estimates
	•	review_decay_state
	•	recent_assessment_history

This group should be highly queryable by topic/subtopic.

Rule families this group must control

This group must control:
	•	starting difficulty
	•	allowed concept jump size
	•	whether to skip basics
	•	whether to use remediation
	•	hint density
	•	whether to ask or tell
	•	node readiness
	•	mastery confidence

Exact mappings

Implement:

Initial/final level per topic
Controls:
	•	topic_difficulty_band
	•	entry_point_depth
	•	skip_intro_basics

Delta and recent growth
Controls:
	•	challenge_ramp_rate

Confidence
Important: keep competence and confidence separate.

Controls:
	•	confidence_sensitive_support

Support logic such as:
	•	low competence + high confidence → more checking
	•	high competence + low confidence → encourage and require demonstration
	•	low competence + low confidence → heavy scaffolding

Learning speed multiplier
Controls:
	•	response_compaction
	•	practice_count_before_advance

Block pass/fail by sub-node
Controls:
	•	required_remediation_topics[]
	•	cannot_advance_flags[]

Map decay
Controls:
	•	review_priority
	•	recall_check_bias

Strong/weak topics
Controls:
	•	bridge_from_strengths
	•	protect_against_overchallenge_in_weak_topics

⸻

Group 6 — Live Adaptation Layer

Purpose

Answer:
	•	what is happening right now in this session and this node

Source data to use

Use:
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

Persistence recommendation

Split into:

Temporary session-state
	•	current_session_state
	•	node_session_state

Persistent observed adaptation memory
	•	observed_preference_patterns
	•	effective_strategy_patterns
	•	ineffective_strategy_patterns

Important:
	•	do not persist raw mood forever as a stable identity trait
	•	persist longer-term patterns only when repeated

Rule families this group must control

This group should override most others for the current turn.

It controls:
	•	turn length
	•	turn complexity
	•	next teaching move
	•	whether to pause / recap / simplify / challenge
	•	whether to ask fewer questions
	•	whether to switch format now

Exact mappings

Implement:

Mood
Controls:
	•	supportive_tone_adjustment
	•	challenge_suppression_if_needed

Energy
Controls:
	•	response_energy_budget
	•	task_size

Perceived difficulty
Controls:
	•	complexity_adjustment
	•	worked_example_bias

Needs pause
Controls:
	•	offer_pause_or_micro_stop = true

Needs more explanation
Controls:
	•	expand_current_concept = true

Needs more challenge
Controls:
	•	increase_independence = true

Needs different format
Controls:
	•	format_override

Explanation feedback
Update observed preferences such as:
	•	explanation_length_preference_observed
	•	example_bias_observed
	•	structure_need_observed
	•	language_simplicity_need_observed

Examples:
	•	too long → shorten next turn
	•	too abstract → example-first
	•	too complicated → simpler vocabulary
	•	step by step please → stronger scaffolding

Repeated error pattern
Controls:
	•	must_change_strategy = true

Drop-off risk
Controls:
	•	reduce_turn_burden
	•	increase_relevance_visibility
	•	avoid_multi_part_tasks

⸻

Core implementation requirement

Whenever any information/setting/result belonging to one of these groups changes, the system must:
	1.	detect which group(s) are affected
	2.	recompute the grouped profile object
	3.	recompute the resolved rule set for that group
	4.	persist the updated group snapshot and rules
	5.	make the updated resolved rules available for later prompt generation

This must work reliably and not require manual recomputation.

⸻

Required system design

1. Create group resolvers

Implement a clear resolver layer for the six groups.

Suggested pattern:
	•	one resolver per group
	•	each resolver:
	•	reads source data
	•	groups/normalizes it
	•	computes resolved rules
	•	returns structured snapshot + rule set

Do not put this logic directly into route handlers or UI components.

2. Persist grouped results

Each group should persist both:
	•	grouped normalized profile data
	•	resolved rule outputs

Suggested conceptual structure:
	•	identity_context_snapshot
	•	goal_intent_snapshot
	•	declared_preferences_snapshot
	•	diagnosed_learning_snapshot
	•	capability_mastery_snapshot
	•	live_adaptation_snapshot

and/or corresponding resolved rule objects such as:
	•	resolved_identity_context_rules
	•	resolved_goal_rules
	•	resolved_declared_tutor_rules
	•	resolved_diagnostic_rules
	•	resolved_capability_rules
	•	resolved_live_adaptation_rules

Choose a clean maintainable schema structure.

3. Change detection / recomputation

Implement a clear recomputation trigger model.

When relevant source data changes:
	•	recompute only the affected group(s)
	•	and any dependent derived group if applicable

Examples:
	•	profile form change → Group 1
	•	goal add/update/activate → Group 2
	•	learning preference change → Group 3
	•	LAA/MOA/LTA completion → Group 4
	•	KSA assessment or drill change → Group 5
	•	live session state / explanation feedback update → Group 6

Do not recompute everything blindly unless the implementation truly requires it and performance remains acceptable. Prefer targeted recomputation.

4. Keep this step prompt-free

This step must not yet generate the final teaching prompt text.

It only prepares the grouped rule foundation that later prompt-building will consume.

⸻

Backend/API requirements

Add/update backend support for:
	•	resolving grouped personalization layers
	•	persisting snapshots and resolved rules
	•	re-resolving groups on change
	•	retrieving grouped/resolved data for inspection/debugging if useful

If needed, add internal service APIs or admin/debug endpoints, but do not expose unsafe sensitive data unnecessarily.

⸻

Data model requirements

Add/extend schema as needed to support:
	•	grouped snapshots
	•	resolved rule sets
	•	change timestamps
	•	rule versioning if useful
	•	source-to-group traceability if useful

Keep migrations clean and maintainable.

⸻

Debuggability requirements

This step is foundational and will affect later learning personalization heavily.

Therefore implement enough observability so developers can inspect:
	•	source data used by a group
	•	grouped normalized output
	•	resolved rule output
	•	last recompute time
	•	why a group changed

This can be:
	•	internal debug logging
	•	internal admin/dev inspection output
	•	structured service logs

Do not leave the rule resolution as a black box.

⸻

Frontend/UI requirements

No major end-user UI redesign is required in this step unless necessary.

But if useful, you may add:
	•	minimal internal/dev inspection views
	•	or prepare data access for later personalization-debug UIs

Do not overbuild UI here.

⸻

Validation requirements

This step is not complete when the group names exist in code.

It is complete only after real learner data is grouped correctly, rule sets are resolved correctly, recomputation works reliably, and the result is ready for later prompt-generation use.

Validate at minimum:
	1.	Group 1 resolves correctly from identity/context/profile inputs
	2.	Group 2 resolves correctly from goals and active goal state
	3.	Group 3 resolves correctly from declared learning preferences
	4.	Group 4 resolves correctly from LAA/MOA/LTA outputs
	5.	Group 5 resolves correctly from KSA data and drill history
	6.	Group 6 resolves correctly from live session signals and explanation feedback
	7.	updating source data recomputes the right group(s)
	8.	grouped snapshots persist correctly
	9.	resolved rule sets persist correctly
	10.	competence and confidence remain distinct in Group 5
	11.	live session-state does not incorrectly overwrite stable identity/profile data
	12.	the system remains ready for later prompt-building
	13.	no regression in existing learning features

If issues are found:
	1.	identify root cause
	2.	debug and fix
	3.	rerun validation
	4.	update docs and changelog

⸻

Testing requirements

Update and/or add tests where practical for:
	•	group resolver correctness
	•	field-to-rule mapping correctness
	•	recomputation triggers
	•	persistence of snapshots/rules
	•	separation of stable vs live signals
	•	Group 4 diagnostic resolution
	•	Group 5 capability/confidence resolution
	•	Group 6 live override logic
	•	migration/data-integrity coverage

⸻

Documentation requirements

Update at minimum:
	•	docs/learning.md
	•	docs/personalization.md
	•	docs/architecture.md
	•	docs/testing.md
	•	changelog.md

Also document:
	•	the 6 personalization groups
	•	source fields for each group
	•	resolved rule families for each group
	•	recomputation behavior
	•	persistence structure
	•	how this prepares later prompt generation
	•	current non-goal: no final teaching prompts yet

⸻

Deliverable expectations

When finished:
	•	all major learner data is grouped into the 6 defined layers
	•	each layer produces a normalized grouped profile and resolved rule set
	•	relevant changes automatically recompute the correct group(s)
	•	grouped and resolved outputs are persisted cleanly
	•	the implementation is debuggable and maintainable
	•	the system is ready for the next step: prompt-building for personalized teaching
	•	tests/docs/changelog are updated
	•	the result has been verified and debugged if needed