Return strict JSON with:
- mc_questions (exactly 12)
- free_text_questions (exactly 2)
- deep_dive_topics (exactly 3)

Each mc question must include:
- id
- type (single|multiple)
- question
- options (>=3)
- correct_answers (1..n)
- topic
- explanation

Each free text question must include:
- id
- question
- topic
- rubric (3..6 short criteria)

Each deep dive topic must include:
- label
- big_map_group (Knowledge|Skills|Abilities)
- big_map_subdomain
- detailed_topic
- rationale

Match difficulty_profile and avoid superficial recall.
