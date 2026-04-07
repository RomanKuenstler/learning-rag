1. Information collected from users in Step B

Step B is the explicit / declared learner profile.

This is the information the user directly provides.

A. Declared learning preferences

These are the settings the learner explicitly chooses.

Pace
	•	slow
	•	balanced
	•	fast

Explanation depth
	•	concise
	•	balanced
	•	detailed

Examples vs theory
	•	more examples
	•	balanced
	•	more theory

Structure preference
	•	more structured / lists
	•	balanced
	•	more conversational

Quiz / checkpoint frequency
	•	low
	•	medium
	•	high

Encouragement level
	•	low
	•	balanced
	•	high

Guidance level
	•	step-by-step
	•	balanced
	•	more independent

Recap frequency
	•	low
	•	medium
	•	high

Preferred learning format
	•	reading
	•	dialogue
	•	exercises
	•	mixed

Free learning note
	•	free text like:
	•	“teach me with practical examples”
	•	“please explain slowly”
	•	“avoid too much theory”

⸻

B. Learner background / learning context

This is the context that makes teaching more relevant.

Education background

Examples:
	•	school level
	•	university
	•	self-taught
	•	vocational training

Current skill areas

What the learner already feels confident in or has experience with.

Interests

Topics that motivate the learner or help create better examples.

Professional context

Examples:
	•	current job
	•	field of work
	•	industry
	•	role

Current reason for learning

Examples:
	•	exam preparation
	•	job change
	•	career growth
	•	hobby / personal interest
	•	project need

Preferred form of address

Examples:
	•	first name
	•	nickname
	•	more formal / less formal

Personal learning context notes

Free text about:
	•	current situation
	•	constraints
	•	preferences
	•	learning challenges

⸻

C. Learning goals

This is what the learner wants to achieve.

Target topic / subject

What they want to learn.

Reason for learning

Why they want to learn it.

Target level

Examples:
	•	beginner
	•	intermediate
	•	advanced

Optional deadline

A target date if the learning has urgency.

Optional priority

How important the goal is compared to others.

Optional notes

Any extra detail about the goal.

⸻

2. Information collected from users in Step B.1

Step B.1 is the diagnosed / inferred learning profile + adaptive signal layer.

This is much richer.

⸻

A. Diagnostic system: LAA / MOA / LTA

A1. LAA — Lernartanalyse

From the screenshots and prior discussion, this captures learning-related dimensions such as:
	•	Zielklarheit
	•	Nachhaltigkeit
	•	Lernerfahrung
	•	Feedbackoffenheit
	•	Lernumgebung
	•	Zielmotivation
	•	Kompetenzprofil
	•	Selbstwirksamkeit
	•	Individualisierungswunsch

Depending on the exact docx content, there may be more or slightly different dimension names, but this is the structure we already identified.

For each of these, the system will store:
	•	raw score
	•	normalized score
	•	interpretation-ready score

This gives you a profile of:
	•	how clearly the learner knows what they want
	•	how reflective they are
	•	how open they are to feedback
	•	how much structure/individualization they need
	•	how strongly they believe in their own ability
	•	how stable and sustainable their learning habits may be

⸻

A2. MOA — Motivationsanalyse

This captures motivational drivers.

From your screenshots and our earlier discussion, this likely includes dimensions like:
	•	Autonomie
	•	Sinn
	•	Status
	•	Kreativität
	•	Sicherheit
	•	soziale Aspekte / Zugehörigkeit
	•	Entwicklung / Wachstum
	•	Einfluss / Wirkung

Exact categories should come from the source documents.

For each motivation dimension, store:
	•	raw score
	•	normalized score
	•	relative weight / distribution

This gives you:
	•	what drives the learner
	•	what keeps them engaged
	•	what kind of reinforcement works best

⸻

A3. LTA — Lerntypanalyse

This produces a weighted learning-type profile such as:
	•	kommunikativ
	•	auditiv
	•	visuell
	•	motorisch

Store:
	•	percentage or score per type
	•	dominant type
	•	maybe secondary type

This tells you:
	•	how content should preferably be presented
	•	which form of explanation is likely to work best

⸻

B. Diagnostic answers themselves

Besides final scores, the system should also store the actual response data.

For each diagnostic attempt:
	•	question id
	•	answer value
	•	answer type
	•	time / sequence
	•	diagnostic version used

This is useful because later you may want:
	•	re-interpretation with new scoring
	•	comparison across time
	•	pattern detection

⸻

C. Diagnostic result summaries

The system should also store generated or computed summaries such as:
	•	dominant learner profile
	•	dominant motivational profile
	•	dominant learning type
	•	strengths
	•	likely friction points
	•	suggested teaching recommendations

Even if first implementation is rule-based, these summaries are valuable.

⸻

D. Historical attempts / versioning

Per user:
	•	diagnostic attempt history
	•	latest active result
	•	previous results
	•	version of questionnaire used

This allows:
	•	retakes
	•	comparing changes over time
	•	seeing whether a learner profile is stable or shifting

⸻

E. Real-time learning state checks

From the screenshots and the “Ämber” concept, this is a lightweight in-session signal set.

Examples of state data:
	•	current mood / emotional state
	•	current energy level
	•	perceived difficulty right now
	•	whether the learner needs:
	•	a pause
	•	more explanation
	•	more challenge
	•	different format
	•	whether the current goal still feels right
	•	what format would help now:
	•	examples
	•	simpler explanation
	•	structure
	•	practice

This is temporary but extremely valuable because it captures:
	•	how the learner feels now
	•	whether the current teaching style is still working

⸻

F. Explanation feedback loop

From your last screenshots, this captures whether the learner was satisfied with a given explanation.

Explicit fields
	•	explanation rating
	•	e.g. emoji scale or 1–5
	•	free-text feedback
	•	“too complicated”
	•	“more examples”
	•	“too long”
	•	“explain step by step”

Derived fields later

From repeated feedback patterns, the system could infer:
	•	prefers simpler language
	•	prefers shorter explanations
	•	prefers more examples
	•	prefers step-by-step breakdowns
	•	dislikes long paragraphs
	•	wants more structure

This is one of the strongest personalization signals because it is tied to actual teaching output.

⸻

3. Additional user-related information visible in the screenshots

From the screenshots beyond Step B/B.1, there are other user data areas that are useful for learning personalization too.

A. Personal details / profile info

Visible or implied in the onboarding/profile screenshots:
	•	full name
	•	display name / nickname
	•	gender or salutation preferences if collected
	•	profile picture/avatar
	•	country / language context if relevant

Useful for:
	•	tone
	•	language
	•	respectful addressing
	•	culturally relevant examples

⸻

B. Bio / self-description

A free text area about the person.

Useful for:
	•	richer contextual examples
	•	understanding identity and self-concept
	•	motivation framing

⸻

C. Skills

A list/tag structure of skills the learner already has.

Useful for:
	•	assessing prior knowledge
	•	choosing analogies
	•	skipping basics
	•	difficulty calibration

⸻

D. Experience / timeline

Your screenshots suggest a history/timeline style data model.

This can include:
	•	previous jobs
	•	projects
	•	study history
	•	certifications
	•	milestones

Useful for:
	•	using relevant examples
	•	estimating current competence
	•	grounding learning in real-world context

⸻

E. Interests

Topics the learner likes.

Useful for:
	•	motivation
	•	tailored examples
	•	keeping attention
	•	story/context choice

⸻

F. Analytics / behavior history

From your later screenshots you also hinted at:
	•	streaks
	•	time spent
	•	monthly activity
	•	completed items
	•	progress metrics

This is not exactly Step B/B.1 input, but it becomes very important later for adaptive teaching.

⸻

4. What all this data is useful for in teaching

Here is the practical mapping.

A. Tone and explanation style

Use:
	•	encouragement level
	•	structure preference
	•	explanation depth
	•	explanation feedback
	•	learning type
	•	mood/state

To decide:
	•	more supportive vs more direct
	•	more structured vs more conversational
	•	shorter vs deeper explanations

⸻

B. Content format

Use:
	•	preferred learning format
	•	LTA learning type
	•	examples vs theory
	•	state checks
	•	explanation feedback

To decide:
	•	more examples
	•	more dialogue
	•	more exercises
	•	more visual language
	•	more step-by-step walkthroughs

⸻

C. Pacing and progression

Use:
	•	preferred pace
	•	recap frequency
	•	current difficulty state
	•	self-efficacy / Selbstwirksamkeit
	•	goal urgency / deadline
	•	progress history

To decide:
	•	slower
	•	normal
	•	accelerated
	•	more recaps
	•	more repetition before advancing

⸻

D. Motivation strategy

Use:
	•	MOA motivation profile
	•	reason for learning
	•	goal priority
	•	interests
	•	real-time emotional state

To decide:
	•	whether to motivate through:
	•	autonomy
	•	meaning
	•	achievement
	•	creativity
	•	security
	•	progress
	•	what kind of encouragement works best

⸻

E. Personal relevance of examples

Use:
	•	profession
	•	interests
	•	skills
	•	background
	•	learning goals

To decide:
	•	examples from their work
	•	examples from their hobbies
	•	more technical vs more everyday analogies

⸻

F. Difficulty and support level

Use:
	•	target level
	•	self-efficacy
	•	competence profile
	•	learner history
	•	current state
	•	explanation feedback

To decide:
	•	how challenging to be
	•	how many hints to give
	•	when to simplify
	•	when to ask instead of tell

⸻

5. Additional information that would be very useful later

These are not strictly part of current Step B / B.1, but would be highly valuable.

A. Available study time

Examples:
	•	minutes per session
	•	sessions per week
	•	preferred study times

Very useful for:
	•	planning lesson length
	•	pacing
	•	recap scheduling

⸻

B. Preferred device / environment

Examples:
	•	mobile
	•	desktop
	•	tablet
	•	quiet vs noisy environment

Useful for:
	•	choosing content length
	•	interaction style
	•	audio vs text balance later

⸻

C. Language proficiency

Especially important if the learning language is not the native language.

Examples:
	•	native language
	•	preferred response language
	•	confidence in technical English / German etc.

Useful for:
	•	vocabulary complexity
	•	bilingual explanations
	•	reducing cognitive overload

⸻

D. Accessibility needs

Examples:
	•	reading difficulties
	•	auditory preference
	•	visual accessibility needs
	•	concentration difficulties

Very important for:
	•	inclusive teaching
	•	better content format choices

⸻

E. Confidence per topic

Not just general self-efficacy, but:
	•	confidence in subtopics

Very useful for:
	•	adaptive starting point
	•	repetition targeting

⸻

F. Preferred assessment style

Examples:
	•	multiple choice
	•	open answer
	•	mini practical tasks
	•	flashcards
	•	oral style later

Useful for:
	•	quiz design
	•	frustration reduction

⸻

G. Frustration triggers / avoidance preferences

Examples:
	•	“don’t overload me with jargon”
	•	“don’t ask too many questions in a row”
	•	“don’t be too playful”
	•	“don’t use too many lists”

This can dramatically improve learner satisfaction.

⸻

H. Success indicators

Ask:
	•	“How do you know this session was helpful?”
	•	“What would make you feel progress?”

Useful for:
	•	better session-end summaries
	•	motivation framing

⸻

6. Clean consolidated master list

If you want a compact “all collected data” list for process/prompt design, here it is:

Explicit / declared
	•	preferred pace
	•	explanation depth
	•	examples vs theory
	•	structure preference
	•	quiz frequency
	•	encouragement level
	•	guidance level
	•	recap frequency
	•	preferred learning format
	•	learning-specific free note
	•	education background
	•	current skills
	•	interests
	•	profession / context
	•	reason for learning
	•	preferred form of address
	•	personal learning context notes
	•	target topic
	•	target level
	•	goal reason
	•	deadline
	•	priority
	•	goal notes

Diagnosed / computed
	•	LAA dimension scores
	•	MOA motivation scores
	•	LTA type distribution
	•	dominant learning type
	•	dominant motivation pattern
	•	dominant strengths / challenges
	•	diagnostic summaries
	•	historical attempts
	•	active/current diagnostic profile

Dynamic / adaptive
	•	current mood
	•	energy
	•	perceived difficulty
	•	need for pause/input/variation
	•	desired current format
	•	explanation satisfaction rating
	•	free-text explanation feedback
	•	derived recurring explanation preferences

Additional profile/context from screenshots
	•	bio
	•	skill tags
	•	experience timeline
	•	profile identity fields
	•	activity/progress analytics

⸻

7. My recommendation for your next internal design work

When you work on the process and prompts, I would organize all of this into 4 layers:

Layer 1 — Learner Identity

Who is this person?
	•	background
	•	interests
	•	profession
	•	goals
	•	skills

Layer 2 — Declared Preferences

How do they say they want to learn?
	•	pace
	•	depth
	•	structure
	•	examples
	•	recap etc.

Layer 3 — Diagnosed Preferences

How does the system believe they learn best?
	•	LAA
	•	MOA
	•	LTA

Layer 4 — Live Adaptation Signals

How is learning going right now?
	•	state checks
	•	explanation feedback
	•	later progress/mastery

That structure will make your future prompt/orchestration design much cleaner.