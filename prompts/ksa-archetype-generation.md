Act as an expert Instructional Designer, Psychometrician, and Cognitive Assessment Designer.

You are generating a high-quality KSA (Knowledge, Skills, Abilities) assessment round.

Your task is to create 4 assessment questions (Archetypes) for the following subtopic:

SUBTOPIC:
{{SUBTOPIC}}

CONTEXT:
- This is part of a multi-round adaptive assessment.
- Questions must be realistic, precise, and cognitively meaningful.
- Avoid trivia, vague phrasing, or purely theoretical definitions.
- Focus on real-world application, decision-making, and understanding.

GENERAL RULES:
- Each question must have exactly 1 correct answer and 2 plausible distractors.
- Distractors must be believable and from the same conceptual space (not obviously wrong).
- Avoid repeating the same concept across archetypes.
- Keep questions concise but concrete.
- Difficulty: medium to moderately challenging (not trivial, not expert-only).
- Do NOT use generic textbook phrasing.

---

# ARCHETYPES

### 1. REVERSE_DEFINITION (Knowledge)
Goal: Test conceptual understanding through real-world recognition.
Formula: [Scenario describing a specific outcome] + "This is a primary example of..."
Distractors: Use two related but incorrect terms from the same parent category.

- Create a short, concrete scenario with a clear outcome.
- The user must identify the correct concept from the subtopic.
- Avoid directly naming the concept in the scenario.
- Distractors must be related concepts from the same domain.

---

### 2. SPOT_THE_FLAW (Skills)
Goal: Test applied judgment and ability to detect suboptimal execution.
Formula: [A person/system performs Task X] + [Description of a suboptimal action] + "What is the professional flaw here?"
Distractors: One "distraction" answer (irrelevant) and one "Novice" answer (sounds okay but is inefficient).

- Describe a realistic situation where a person performs a task incorrectly or inefficiently.
- The mistake should be subtle (not obvious failure).
- Ask: what is the key professional flaw?
- Correct answer = core mistake.
- Distractors:
  - one irrelevant explanation
  - one "novice-sounding but incomplete" explanation

---

### 3. POWER_SPRINT (Abilities)
Goal: Test fast reasoning, pattern recognition, or cognitive processing.
Formula: [Direct Logic/Pattern/Calculation Question] + "Answer in 15 seconds."
Evaluation: Focus on accuracy and response time.

- Create a short, time-constrained challenge (≤15 seconds).
- Use logic, pattern recognition, prioritization, or quick calculation.
- Keep it lightweight but non-trivial.
- No long reading required.
- Must have a clearly correct answer.

---

### 4. ANALOGY_MATCH (Transfer)
Goal: Test abstraction and cross-domain transfer.
Formula: "Concept [A] in [Subtopic] is most functionally similar to [Concept B] in [Different Domain]."

- Compare a concept from the subtopic to something from a completely different domain.
- The analogy must reflect functional similarity (not superficial similarity).
- Ask the user to identify the best match.
- Distractors should be partially correct but weaker analogies.

---

# OUTPUT FORMAT (STRICT JSON)

Return ONLY valid JSON in this structure:

{
  "subtopic": "{{SUBTOPIC}}",
  "questions": [
    {
      "type": "REVERSE_DEFINITION",
      "question": "string",
      "correct_answer": "string",
      "distractors": ["string", "string"]
    },
    {
      "type": "SPOT_THE_FLAW",
      "question": "string",
      "correct_answer": "string",
      "distractors": ["string", "string"]
    },
    {
      "type": "POWER_SPRINT",
      "question": "string",
      "correct_answer": "string",
      "distractors": ["string", "string"]
    },
    {
      "type": "ANALOGY_MATCH",
      "question": "string",
      "correct_answer": "string",
      "distractors": ["string", "string"]
    }
  ]
}

---

# QUALITY CHECK BEFORE OUTPUT

Before finalizing:
- Ensure all distractors are plausible and not obviously incorrect
- Ensure each question tests a DIFFERENT aspect of the subtopic
- Ensure no answer can be guessed without understanding
- Ensure wording is clear, natural, and user-friendly

Return only the JSON.