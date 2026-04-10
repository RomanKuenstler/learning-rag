Dashboard:
- streak
- analytics
- ongoing paths
- news/announcements

Paths/Skills page incl Filter etc

Learning Chats

Daily Challenge or so



Step A — Foundations: roles, entities, learning-path schema

Goal: create the backend model and permissions foundation.

Implement:
	•	new role student
	•	chat type learning_chat
	•	learning path schema
	•	module/lesson structure
	•	ownership/global distinction
	•	permissions
	•	basic CRUD for learning paths
	•	no teaching logic yet, or only placeholder

This step answers:
	•	what is a learning path
	•	who can create/edit/delete
	•	who can access what

Step B — Learning preferences

Goal: create student-specific learning profile and preferences.

Implement:
	•	learning preferences entity
	•	preference UI + API
	•	maybe a small diagnostic questionnaire
	•	storage of declared preferences
	•	placeholder support in learning prompt builder

This step answers:
	•	how does this student prefer to learn

Step C — Learning chat mode

Goal: create the actual learning assistant mode and learning chats.

Implement:
	•	learning chat type
	•	one learning path per learning chat
	•	learning prompt builder
	•	retrieval constrained to the learning path’s source scope
	•	lesson-aware state
	•	student role restriction: students can only use learning mode

This step answers:
	•	how the teaching actually happens

Step D — Progress tracking and mastery

Goal: make learning state persistent and meaningful.

Implement:
	•	current lesson/module tracking
	•	per-lesson mastery state
	•	completed / needs review / in progress
	•	transitions between lessons
	•	recap/repeat logic

This step answers:
	•	how the system knows where the student is

Step E — Assessments / quizzes / checkpoints

Goal: make the system test understanding.

Implement:
	•	quiz/checkpoint object model
	•	generated questions
	•	answer capture
	•	grading/rubric logic
	•	progress updates from test outcomes
	•	repeat/review recommendations

This step answers:
	•	how the system knows if learning really happened

Step F — Learning UI

Goal: proper frontend experience.

Implement:
	•	learning path list page
	•	create/edit/delete path UI
	•	student learning dashboard
	•	learning chat UI
	•	progress indicators
	•	test display and answer UX

This can overlap with earlier steps, but I would not start with fancy UI first.

Step G — Adaptive teaching improvements

Goal: better personalized teaching.

Implement:
	•	observed learning profile
	•	preferred pace detection
	•	weakness clustering
	•	dynamic recap scheduling
	•	“explain differently” style adaptation