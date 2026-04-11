You are generating a structured teaching plan for a learning_unit runtime package.

Return strict JSON object with:
- node_structure_preview (object)
- lesson_steps (array)
- recap_plan (object)
- interaction_hooks (object)

Each lesson_steps item must include:
- step_id
- mini_topic_title
- intro_brief
- lesson_goal
- explanation_requirements (array)
- explanation_constraints (array)
- teaching_brief
- prior_assumptions (array)
- expected_difficulty_points (array)
- ksa_links (array)
- style_hints (array)

recap_plan must include:
- recap_goals (array)
- key_topics_to_summarize (array)
- most_important_takeaways (array)
- likely_questions (array)

interaction_hooks must include booleans for:
- supports_questions_per_lesson
- supports_explanation_rating
- supports_reexplanation_request
- supports_node_feedback

Rules:
- Plan structure only, not full final lesson text.
- Keep outputs concise and reusable for later delivery orchestration.
- Use mini-topics, niveau estimate, KSA signals, and personalization hints.
