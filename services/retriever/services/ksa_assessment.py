from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any
import unicodedata


ASSESSMENT_VERSION = "ksa-v1"
ABILITY_TIME_LIMIT_SECONDS = 30


PHASE1_SLIDERS: list[dict[str, Any]] = [
    {"id": "1.1", "key": "stem_it", "topic": "STEM/IT", "prompt": "Rate your technical & scientific literacy.", "min": 1, "max": 10, "triggers": ["stem_fundamentals", "information_technology"]},
    {"id": "1.2", "key": "humanities", "topic": "Humanities", "prompt": "Rate your understanding of society & history.", "min": 1, "max": 10, "triggers": ["humanities_social_sciences", "languages_linguistics"]},
    {"id": "1.3", "key": "business_legal", "topic": "Business/Law", "prompt": "How comfortable are you with commerce & legal topics?", "min": 1, "max": 10, "triggers": ["business_commerce", "legal_ethics"]},
    {"id": "1.4", "key": "health", "topic": "Health", "prompt": "Rate your knowledge of biology & wellness.", "min": 1, "max": 10, "triggers": ["health_wellness"]},
    {"id": "1.5", "key": "digital_ops", "topic": "Digital/Ops", "prompt": "How skilled are you at using tools/building things?", "min": 1, "max": 10, "triggers": ["digital_craft", "operational_skills"]},
    {"id": "1.6", "key": "people_strat", "topic": "People/Strat", "prompt": "Rate your ability to lead and plan.", "min": 1, "max": 10, "triggers": ["strategic_execution", "relational_skills"]},
    {"id": "1.7", "key": "research", "topic": "Research", "prompt": "How experienced are you in data/scientific inquiry?", "min": 1, "max": 10, "triggers": ["research_inquiry", "literacy_numeracy"]},
]


KNOWLEDGE_QUESTIONS: list[dict[str, Any]] = [
    {"id": "K.1a", "topic": "stem_fundamentals", "difficulty": "easy", "question": "What is the boiling point of water at sea level?", "options": ["90°C", "100°C", "110°C"], "correct": "100°C"},
    {"id": "K.1b", "topic": "stem_fundamentals", "difficulty": "hard", "question": "What does the Second Law of Thermodynamics imply?", "options": ["Energy is created", "Entropy increases", "Heat flows cold to hot"], "correct": "Entropy increases"},
    {"id": "K.2a", "topic": "information_technology", "difficulty": "easy", "question": "What is the purpose of an IP address?", "options": ["Identify a device on a network", "Store files", "Code logic"], "correct": "Identify a device on a network"},
    {"id": "K.2b", "topic": "information_technology", "difficulty": "hard", "question": "In AI, what is ‘Overfitting’?", "options": ["Model too simple", "Model fits noise, not general data", "Model is too fast"], "correct": "Model fits noise, not general data"},
    {"id": "K.3a", "topic": "humanities_social_sciences", "difficulty": "easy", "question": "What does ‘Socio-economics’ study?", "options": ["Only money", "Interaction of social and economic factors", "History"], "correct": "Interaction of social and economic factors"},
    {"id": "K.3b", "topic": "humanities_social_sciences", "difficulty": "hard", "question": "What is the core idea of ‘Existentialism’?", "options": ["Fate is predetermined", "Individual freedom/responsibility", "Collectivism"], "correct": "Individual freedom/responsibility"},
    {"id": "K.4a", "topic": "languages_linguistics", "difficulty": "easy", "question": "What is a ‘Suffix’?", "options": ["A word ending", "A word beginning", "A verb"], "correct": "A word ending"},
    {"id": "K.4b", "topic": "languages_linguistics", "difficulty": "hard", "question": "What is the study of ‘Phonology’?", "options": ["Grammar", "Speech sound patterns", "Sentence meaning"], "correct": "Speech sound patterns"},
    {"id": "K.5a", "topic": "business_commerce", "difficulty": "easy", "question": "What is ‘Market Share’?", "options": ["Total profit", "Company’s % of total industry sales", "Share price"], "correct": "Company’s % of total industry sales"},
    {"id": "K.5b", "topic": "business_commerce", "difficulty": "hard", "question": "What does ‘Just-in-Time’ (JIT) manufacturing aim to reduce?", "options": ["Labor", "Inventory waste", "Marketing costs"], "correct": "Inventory waste"},
    {"id": "K.6a", "topic": "legal_ethics", "difficulty": "easy", "question": "What is a ‘Conflict of Interest’?", "options": ["Private interests vs professional duties", "Two people arguing", "A bad law"], "correct": "Private interests vs professional duties"},
    {"id": "K.6b", "topic": "legal_ethics", "difficulty": "hard", "question": "What is ‘Deontological Ethics’?", "options": ["Results-based", "Duty-based", "Virtue-based"], "correct": "Duty-based"},
    {"id": "K.7a", "topic": "health_wellness", "difficulty": "easy", "question": "What is a ‘Macronutrient’?", "options": ["Protein/Carbs/Fats", "Vitamins", "Water only"], "correct": "Protein/Carbs/Fats"},
    {"id": "K.7b", "topic": "health_wellness", "difficulty": "hard", "question": "What does ‘Pharmacokinetics’ describe?", "options": ["How drugs are made", "How the body processes a drug", "Drug side effects"], "correct": "How the body processes a drug"},
]


SKILL_QUESTIONS: list[dict[str, Any]] = [
    {"id": "S.1", "topic": "digital_craft", "scenario": "A software UI is confusing users. What do you do?", "choice_a": "Add more text instructions.", "choice_b": "Simplify the layout and user flow."},
    {"id": "S.2", "topic": "operational_skills", "scenario": "A process step keeps causing a bottleneck.", "choice_a": "Tell people to work faster.", "choice_b": "Redesign the workflow to balance the load."},
    {"id": "S.3", "topic": "strategic_execution", "scenario": "You have a high-impact but high-risk idea.", "choice_a": "Avoid it to be safe.", "choice_b": "Create a mitigation plan and test a pilot."},
    {"id": "S.4", "topic": "relational_skills", "scenario": "A client is angry about a late delivery.", "choice_a": "Explain why it’s not your fault.", "choice_b": "Acknowledge the frustration and offer a solution."},
    {"id": "S.5", "topic": "research_inquiry", "scenario": "You find data that contradicts your theory.", "choice_a": "Ignore it as an outlier.", "choice_b": "Re-examine your theory based on the data."},
    {"id": "S.6", "topic": "literacy_numeracy", "scenario": "You need to summarize a 50-page technical report.", "choice_a": "Read every word and rewrite it.", "choice_b": "Extract key findings and actionable insights."},
]


ABILITY_QUESTIONS: list[dict[str, Any]] = [
    {"id": "A.1", "topic": "quantitative_reasoning", "task": "If 5 shirts cost $45, how much do 3 cost?", "expected": "$27", "open_ended": False},
    {"id": "A.2", "topic": "verbal_comprehension", "task": "Complete the analogy: ‘Oven’ is to ‘Heat’ as ‘Camera’ is to…", "expected": "Light", "open_ended": False},
    {"id": "A.3", "topic": "spatial_visualization", "task": "Mental Rotation: Can two ‘L’ shapes form a rectangle?", "expected": "Yes", "open_ended": False},
    {"id": "A.4", "topic": "executive_function", "task": "Identify the ‘odd one out’ in 5 seconds: 66, 88, 77, 98, 44.", "expected": "98", "open_ended": False},
    {"id": "A.5", "topic": "sensory_perceptual", "task": "Listen to three tones: High, Mid, Low. Which was second?", "expected": "Mid", "open_ended": False},
    {"id": "A.6", "topic": "social_emotional_capacity", "task": "Someone looks away while you talk. They are likely…", "expected": "Disinterested/Uncomfortable", "open_ended": False},
    {"id": "A.7", "topic": "divergent_thinking", "task": "Name 3 uses for a coffee mug other than drinking.", "expected": "open-ended", "open_ended": True},
]


KNOWLEDGE_TOPICS = [
    "stem_fundamentals",
    "information_technology",
    "humanities_social_sciences",
    "languages_linguistics",
    "business_commerce",
    "legal_ethics",
    "health_wellness",
]
SKILL_TOPICS = [
    "literacy_numeracy",
    "digital_craft",
    "strategic_execution",
    "operational_skills",
    "relational_skills",
    "research_inquiry",
]
ABILITY_TOPICS = [
    "quantitative_reasoning",
    "verbal_comprehension",
    "spatial_visualization",
    "executive_function",
    "sensory_perceptual",
    "social_emotional_capacity",
    "divergent_thinking",
]


@dataclass(slots=True)
class KSAEvaluation:
    profile_json: dict[str, Any]
    knowledge_levels: dict[str, int]
    skills_levels: dict[str, int]
    abilities_levels: dict[str, int]


def get_assessment_definition() -> dict[str, Any]:
    public_knowledge_questions: list[dict[str, Any]] = []
    for question in KNOWLEDGE_QUESTIONS:
        public_knowledge_questions.append(
            {
                "id": question["id"],
                "topic": question["topic"],
                "difficulty": question["difficulty"],
                "question": question["question"],
                "options": list(question.get("options") or []),
            }
        )
    return {
        "version": ASSESSMENT_VERSION,
        "time_limit_seconds": ABILITY_TIME_LIMIT_SECONDS,
        "phase1_sliders": PHASE1_SLIDERS,
        "knowledge_questions": public_knowledge_questions,
        "skill_questions": SKILL_QUESTIONS,
        "ability_questions": ABILITY_QUESTIONS,
    }


def evaluate_assessment(*, user_id: int, answers: dict[str, Any]) -> KSAEvaluation:
    slider_answers = _normalize_slider_answers(dict(answers.get("phase1") or {}))
    knowledge_answers = dict(answers.get("knowledge") or {})
    skill_answers = dict(answers.get("skills") or {})
    ability_answers = dict(answers.get("abilities") or {})
    triggered = _compute_triggered_topics(slider_answers)

    knowledge_result: dict[str, Any] = {}
    knowledge_levels: dict[str, int] = {}
    for topic in KNOWLEDGE_TOPICS:
        topic_trigger = triggered["knowledge"].get(topic)
        if not topic_trigger:
            knowledge_result[topic] = {
                "status": "uncharted",
                "level": 1,
                "self_report_slider": topic_trigger,
                "validation_multiplier": None,
                "final_score": 0.0,
                "answers": {},
            }
            knowledge_levels[topic] = 1
            continue
        easy = _question_for_topic(topic, "easy")
        hard = _question_for_topic(topic, "hard")
        easy_answer = str(knowledge_answers.get(easy["id"], "")).strip()
        hard_answer = str(knowledge_answers.get(hard["id"], "")).strip()
        easy_correct = _text_equals(easy_answer, str(easy["correct"]))
        hard_correct = _text_equals(hard_answer, str(hard["correct"]))
        if not easy_correct:
            multiplier = 0.5
        elif easy_correct and not hard_correct:
            multiplier = 1.0
        else:
            multiplier = 1.5
        final_score = float(topic_trigger) * multiplier
        if final_score < 4:
            level = 1
        elif final_score <= 7:
            level = 2
        else:
            level = 3
        knowledge_result[topic] = {
            "status": "verified",
            "level": level,
            "self_report_slider": topic_trigger,
            "validation_multiplier": multiplier,
            "final_score": round(final_score, 4),
            "answers": {
                easy["id"]: {"value": easy_answer, "correct": easy_correct},
                hard["id"]: {"value": hard_answer, "correct": hard_correct},
            },
        }
        knowledge_levels[topic] = level

    skills_result: dict[str, Any] = {}
    skills_levels: dict[str, int] = {}
    for question in SKILL_QUESTIONS:
        topic = str(question["topic"])
        selected = str(skill_answers.get(question["id"], "")).strip().upper()
        if not triggered["skills"].get(topic):
            skills_result[topic] = {
                "status": "uncharted",
                "level": 1,
                "selected_choice": None,
                "attempts": 0,
            }
            skills_levels[topic] = 1
            continue
        level = 3 if selected == "B" else 1
        skills_result[topic] = {
            "status": "verified",
            "level": level,
            "selected_choice": "B" if selected == "B" else "A",
            "attempts": 1,
        }
        skills_levels[topic] = level

    abilities_result: dict[str, Any] = {}
    abilities_levels: dict[str, int] = {}
    for question in ABILITY_QUESTIONS:
        topic = str(question["topic"])
        submitted = dict(ability_answers.get(question["id"]) or {})
        answer_value = str(submitted.get("answer", "")).strip()
        response_time_seconds = _normalize_response_time(submitted.get("response_time_seconds"))
        is_open_ended = bool(question.get("open_ended"))
        if is_open_ended:
            correctness = _score_divergent_thinking(answer_value)
            expected_match = None
        else:
            expected = str(question.get("expected", "")).strip()
            expected_match = _match_ability_answer(question_id=str(question["id"]), answer=answer_value, expected=expected)
            correctness = 1.0 if expected_match else 0.0
        time_bonus = _time_bonus(response_time_seconds, ABILITY_TIME_LIMIT_SECONDS)
        capacity = (correctness * 0.7) + (time_bonus * 0.3)
        level = _ability_level_from_capacity(capacity)
        abilities_result[topic] = {
            "capacity_score": round(capacity, 4),
            "display_level": level,
            "correctness": round(correctness, 4),
            "time_bonus": round(time_bonus, 4),
            "response_time_seconds": response_time_seconds,
            "answer": answer_value,
            "is_correct": expected_match,
        }
        abilities_levels[topic] = level

    logic_quant_index = float(abilities_result.get("executive_function", {}).get("capacity_score", 0.0)) + float(
        abilities_result.get("quantitative_reasoning", {}).get("capacity_score", 0.0)
    )
    learning_speed_multiplier = 1.5 if logic_quant_index > 1.6 else 1.0

    profile_json: dict[str, Any] = {
        "version": ASSESSMENT_VERSION,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "has_assessment": True,
        "profile_source": "assessment",
        "scale_min": 1,
        "scale_max": 5,
        "dreyfus_levels": ["Novice", "Advanced", "Competent", "Proficient", "Expert"],
        "knowledge": knowledge_levels,
        "skills": skills_levels,
        "abilities": abilities_levels,
        "assessment_details": {
            "knowledge": knowledge_result,
            "skills": skills_result,
            "abilities": abilities_result,
            "triggered_topics": triggered,
            "phase1": slider_answers,
            "derived": {
                "logic_quantitative_index": round(logic_quant_index, 4),
                "learning_speed_multiplier": learning_speed_multiplier,
                "logic_proxy": "executive_function",
                "quantitative_proxy": "quantitative_reasoning",
            },
        },
        "user_id": user_id,
    }
    return KSAEvaluation(
        profile_json=profile_json,
        knowledge_levels=knowledge_levels,
        skills_levels=skills_levels,
        abilities_levels=abilities_levels,
    )


def _normalize_slider_answers(values: dict[str, Any]) -> dict[str, int]:
    result: dict[str, int] = {}
    for item in PHASE1_SLIDERS:
        key = str(item["key"])
        raw = values.get(key, 1)
        try:
            parsed = int(raw)
        except Exception:
            parsed = 1
        result[key] = max(1, min(10, parsed))
    return result


def _compute_triggered_topics(slider_answers: dict[str, int]) -> dict[str, dict[str, int | None]]:
    knowledge: dict[str, int | None] = {key: None for key in KNOWLEDGE_TOPICS}
    skills: dict[str, int | None] = {key: None for key in SKILL_TOPICS}
    for slider in PHASE1_SLIDERS:
        slider_key = str(slider["key"])
        score = int(slider_answers.get(slider_key, 1))
        if score <= 5:
            continue
        for topic in list(slider.get("triggers") or []):
            topic_key = str(topic)
            if topic_key in knowledge:
                knowledge[topic_key] = score
            if topic_key in skills:
                skills[topic_key] = score
    return {"knowledge": knowledge, "skills": skills}


def _question_for_topic(topic: str, difficulty: str) -> dict[str, Any]:
    for question in KNOWLEDGE_QUESTIONS:
        if str(question["topic"]) == topic and str(question["difficulty"]) == difficulty:
            return question
    raise ValueError(f"Missing knowledge question for topic={topic} difficulty={difficulty}")


def _normalize_response_time(raw: Any) -> float:
    try:
        value = float(raw)
    except Exception:
        value = ABILITY_TIME_LIMIT_SECONDS
    if value < 0:
        return 0.0
    return min(value, float(ABILITY_TIME_LIMIT_SECONDS))


def _time_bonus(response_time_seconds: float, limit_seconds: int) -> float:
    return max(0.0, min(1.0, (float(limit_seconds) - response_time_seconds) / float(limit_seconds)))


def _ability_level_from_capacity(capacity: float) -> int:
    if capacity <= 0.2:
        return 1
    if capacity <= 0.4:
        return 2
    if capacity <= 0.6:
        return 3
    if capacity <= 0.8:
        return 4
    return 5


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = text.casefold()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _text_equals(left: str, right: str) -> bool:
    return _normalize_text(left) == _normalize_text(right)


def _match_numeric_answer(answer: str, expected_number: float) -> bool:
    normalized = _normalize_text(answer)
    numeric_fragments = re.findall(r"\d+(?:\.\d+)?", normalized)
    for fragment in numeric_fragments:
        try:
            if abs(float(fragment) - expected_number) < 1e-6:
                return True
        except Exception:
            continue
    return False


def _match_ability_answer(*, question_id: str, answer: str, expected: str) -> bool:
    normalized = _normalize_text(answer)
    if question_id == "A.1":
        return _match_numeric_answer(answer, 27.0)
    if question_id == "A.2":
        return "light" in normalized
    if question_id == "A.3":
        return normalized in {"yes", "y", "true"}
    if question_id == "A.4":
        return _match_numeric_answer(answer, 98.0)
    if question_id == "A.5":
        return normalized in {"mid", "middle", "medium", "second", "2", "the middle one"}
    if question_id == "A.6":
        return ("disinterested" in normalized) or ("uninterested" in normalized) or ("uncomfortable" in normalized)
    return _text_equals(answer, expected)


def _score_divergent_thinking(answer: str) -> float:
    raw_parts = re.split(r"[,\n;|]+", answer)
    normalized_parts = {_normalize_text(part) for part in raw_parts}
    unique_parts = {part for part in normalized_parts if part}
    # Initial deterministic heuristic:
    # 0 ideas -> 0.0, 1 idea -> 0.33, 2 ideas -> 0.66, >=3 ideas -> 1.0
    count = min(3, len(unique_parts))
    if count <= 0:
        return 0.0
    if count == 1:
        return 0.33
    if count == 2:
        return 0.66
    return 1.0
