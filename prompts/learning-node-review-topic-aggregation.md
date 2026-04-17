You are generating topic aggregation for a review node runtime package.

Return strict JSON object with:
- grouped_topics (array)
- key_themes (array)

Each grouped_topics item must include:
- topic
- importance (high|medium|low)
- source_node_ids (array)
- related_ksa (array)
- reinforcement_priority (0..1)

Rules:
- Use review scope window nodes only.
- Emphasize prior learning_unit node intentions and topics.
- Incorporate KSA/drill weakness and strength signals.
- Prefer topics that are important for upcoming validation readiness.
