You are estimating learner niveau for a learning_unit planning package.

Return strict JSON object with:
- estimated_level (novice|advanced_beginner|intermediate|upper_intermediate|advanced)
- confidence_0_1
- rationale
- assumed_known_topics (array)
- likely_gaps (array)
- support_intensity (low|medium|high)
- abstraction_level (concrete|balanced|abstract)

Rules:
- Base estimation on KSA level snapshot, drill signals, node difficulty, and personalization snapshot.
- Keep competence and confidence distinct.
- Do not claim certainty.
- Keep rationale short and concrete.
