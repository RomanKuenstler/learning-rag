Return strict JSON object with:
- mc_questions (exactly 24)
- free_text_quiz_questions (exactly 8)
- scenario_practice_questions (exactly 8)
- drill_topics (exactly 8)

mc question shape:
- id
- type (single|multiple)
- question
- options
- correct_answers
- topic
- explanation

free_text and scenario shape:
- id
- question
- topic
- rubric (array 3..6)

drill topic shape:
- label
- big_map_group
- big_map_subdomain
- detailed_topic
- rationale

Ensure broad representative topic coverage and high rigor.
