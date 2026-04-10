Act as an expert learning diagnostician and curriculum designer.

I am building a KSA Deep Dive Assessment with 4 rounds.
The user already entered a topic, and we already know their KSA profile and Big Map strengths/weaknesses.

Your task is to select TWO new detailed assessment topics:

1. A "stretch topic":
- It must come from one of the user's stronger Big Map areas
- But NOT from the user's strongest area
- It should be a good adjacent challenge
- It should feel relevant and learnable
- It must be specific enough to generate realistic assessment questions

2. A "growth topic":
- It must come from one of the user's weaker Big Map areas
- It should still be appropriate and not absurdly difficult
- It should target a meaningful developmental gap
- It must be specific enough to generate realistic assessment questions

Inputs you will receive:
- User KSA profile
- Ranked Big Map strengths
- Ranked Big Map weaknesses

Rules:
- Do not choose a topic that is too broad, vague, or generic
- Choose a detailed topic label, not just a broad category
- Prefer topics that can support all 4 archetypes:
  Reverse Definition, Spot the Flaw, Power Sprint, and Analogy Match
- The stretch topic should feel adjacent to the user's competence
- The growth topic should feel developmental, not punishing
- Avoid selecting the absolute best topic area for the stretch topic
- For each selected topic, include a short rationale

Return JSON only in this exact format:

{
  "stretch_topic": {
    "big_map_group": "Knowledge|Skills|Abilities",
    "big_map_subdomain": "string",
    "detailed_topic": "string",
    "rationale": "string"
  },
  "growth_topic": {
    "big_map_group": "Knowledge|Skills|Abilities",
    "big_map_subdomain": "string",
    "detailed_topic": "string",
    "rationale": "string"
  }
}

User KSA profile:
{{USER_KSA_PROFILE}}

Ranked Big Map strengths:
{{BIG_MAP_STRENGTHS}}

Ranked Big Map weaknesses:
{{BIG_MAP_WEAKNESSES}}