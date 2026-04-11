Return strict JSON object with:
- mc_questions (exactly 6)
- review_prompts (exactly 4)

mc question shape:
- id
- type (single|multiple)
- question
- options
- correct_answers
- topic
- explanation

review prompt shape:
- id
- question
- topic
- rubric (array 3..6)

Keep this focused on consolidation and transfer with KSA-aware difficulty.
