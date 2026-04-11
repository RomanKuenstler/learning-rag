You are generating a structured recap plan for a review node runtime package.

Return strict JSON object with:
- recap_goal
- content_aware_recap_summary (object)
- recap_steps (array)
- key_takeaways (array)
- likely_questions (array)

content_aware_recap_summary must include:
- what_was_learned (array)
- what_to_reinforce (array)
- upcoming_validation_preparation (array)

Each recap_steps item must include:
- step_id
- title
- focus_topics (array)
- brief
- goal
- interaction_hooks (array)

Rules:
- Produce recap structure and briefs, not long final recap monologues.
- Use grouped topics, difficulty profile, and KSA-informed reinforcement priorities.
- Keep steps practical for in-app guided recap flow.
