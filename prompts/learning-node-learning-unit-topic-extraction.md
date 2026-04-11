You are generating a structured teaching-plan input for a learning_unit node.

Return strict JSON object with:
- mini_topics (array, length 3..8)

Each mini_topics item must include:
- title
- focus
- objective
- related_target_topics (array)
- estimated_complexity (low|medium|high)
- ksa_links (array)
- likely_difficulty_points (array)

Rules:
- Use target node topic intent first.
- Use previous node topics as already-known bridge context.
- Use next node topics as upcoming context hints (do not over-teach them).
- Calibrate to difficulty_profile and KSA/drill signals.
- Keep items concise and implementation-ready.
