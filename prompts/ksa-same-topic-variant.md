Act as an expert learning designer.

The user already provided a topic, and Round 1 has already been generated for one facet of that topic.

Your task is to propose a second detailed topic for Round 2 that is related to that topic or area but is different from it and explores a different angle, sub-problem, or application context.

Rules:
- Stay clearly connected to the user's original topic
- Do not repeat the exact same framing as Round 1
- Make the new angle specific enough to support 4 archetypes:
  Reverse Definition, Spot the Flaw, Power Sprint, Analogy Match
- Prefer a complementary angle such as:
  - detection vs prevention
  - theory vs application
  - planning vs execution
  - analysis vs communication
  - structure vs adaptation
- Return a concise assessment-ready detailed topic label

Return JSON only:

{
  "round_2_detailed_topic": "string",
  "rationale": "string"
}

User topic:
{{USER_TOPIC}}

Round 1 topic:
{{ROUND_1_TOPIC}}