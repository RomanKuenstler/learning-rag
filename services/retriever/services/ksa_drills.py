from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
import json
from pathlib import Path
import random
import re
from typing import Any


DRILL_ASSESSMENT_VERSION = "ksa-drill-v1"
DRILL_STRESS_TIME_LIMIT_SECONDS = 15
ARCHETYPE_FILE_RELATIVE_PATH = "prds/interaction-archetypes_ksa.json"


TOPIC_REGISTRY: list[dict[str, Any]] = [
    {
        "group": "knowledge",
        "key": "stem_fundamentals",
        "name": "STEM Fundamentals",
        "subtopics": [
            "Calculus & Linear Algebra",
            "Classical Mechanics",
            "Molecular Biology",
            "Organic Chemistry",
            "Systems Engineering",
        ],
    },
    {
        "group": "knowledge",
        "key": "information_technology",
        "name": "Information Technology",
        "subtopics": [
            "Cloud Architecture",
            "Cybersecurity",
            "Database Management (SQL/NoSQL)",
            "Networking Protocols",
            "Artificial Intelligence & ML",
        ],
    },
    {
        "group": "knowledge",
        "key": "humanities_social_sciences",
        "name": "Humanities & Social Sciences",
        "subtopics": [
            "Macro/Microeconomics",
            "Cognitive Psychology",
            "Political Theory",
            "Modern World History",
            "Sociology of Culture",
        ],
    },
    {
        "group": "knowledge",
        "key": "languages_linguistics",
        "name": "Languages & Linguistics",
        "subtopics": [
            "Semantic Analysis",
            "Syntax & Morphology",
            "Intercultural Communication",
            "Translation Theory",
        ],
    },
    {
        "group": "knowledge",
        "key": "business_commerce",
        "name": "Business & Commerce",
        "subtopics": [
            "Corporate Finance",
            "Growth Marketing",
            "Supply Chain Logistics",
            "Entrepreneurial Strategy",
            "Organizational Behavior",
        ],
    },
    {
        "group": "knowledge",
        "key": "legal_ethics",
        "name": "Legal & Ethics",
        "subtopics": [
            "Intellectual Property",
            "Data Privacy (GDPR/CCPA)",
            "Contract Law",
            "Bioethics",
            "Corporate Governance",
        ],
    },
    {
        "group": "knowledge",
        "key": "health_wellness",
        "name": "Health & Wellness",
        "subtopics": [
            "Human Anatomy",
            "Nutritional Biochemistry",
            "Neuropsychology",
            "Epidemiology",
            "Kinesiology",
        ],
    },
    {
        "group": "skills",
        "key": "literacy_numeracy",
        "name": "Literacy & Numeracy",
        "subtopics": [
            "Statistical Inferencing",
            "Technical Documentation",
            "Financial Forecasting",
            "Critical Discourse Analysis",
        ],
    },
    {
        "group": "skills",
        "key": "digital_craft",
        "name": "Digital Craft",
        "subtopics": [
            "Full-Stack Development",
            "UI/UX Prototyping",
            "Motion Graphics/Video",
            "3D Modeling (CAD)",
            "DevOps/Version Control",
        ],
    },
    {
        "group": "skills",
        "key": "strategic_execution",
        "name": "Strategic Execution",
        "subtopics": [
            "Agile/Scrum Frameworks",
            "Risk Mitigation Planning",
            "Change Management",
            "Crisis Communication",
        ],
    },
    {
        "group": "skills",
        "key": "operational_skills",
        "name": "Operational Skills",
        "subtopics": [
            "Lean Manufacturing",
            "Quality Assurance (Six Sigma)",
            "Technical Troubleshooting",
            "Supply Chain Optimization",
        ],
    },
    {
        "group": "skills",
        "key": "relational_skills",
        "name": "Relational Skills",
        "subtopics": [
            "High-Stakes Negotiation",
            "Executive Coaching",
            "Public Relations",
            "Cross-Functional Diplomacy",
        ],
    },
    {
        "group": "skills",
        "key": "research_inquiry",
        "name": "Research & Inquiry",
        "subtopics": [
            "Quantitative Survey Design",
            "Ethnographic Research",
            "Data Mining",
            "Academic/Peer-Review Standards",
        ],
    },
    {
        "group": "abilities",
        "key": "quantitative_reasoning",
        "name": "Quantitative Reasoning",
        "subtopics": [
            "Statistical Intuition",
            "Mathematical Patterning",
            "Mental Estimation",
        ],
    },
    {
        "group": "abilities",
        "key": "verbal_comprehension",
        "name": "Verbal Comprehension",
        "subtopics": [
            "Critical Reading Speed",
            "Nuance Detection",
            "Logical Argument Synthesis",
        ],
    },
    {
        "group": "abilities",
        "key": "spatial_visualization",
        "name": "Spatial Visualization",
        "subtopics": [
            "3D Mental Rotation",
            "Abstract Pattern Mapping",
            "Structural Reasoning",
        ],
    },
    {
        "group": "abilities",
        "key": "executive_function",
        "name": "Executive Function",
        "subtopics": [
            "Multi-tasking Switching Cost",
            "Working Memory Span",
            "Sustained Focus (Flow State)",
        ],
    },
    {
        "group": "abilities",
        "key": "sensory_perceptual",
        "name": "Sensory-Perceptual",
        "subtopics": [
            "Visual Pattern Recognition",
            "Auditory Processing",
            "Fine Motor Precision",
        ],
    },
    {
        "group": "abilities",
        "key": "social_emotional_capacity",
        "name": "Social-Emotional Capacity",
        "subtopics": [
            "Cognitive Empathy",
            "Emotional Self-Regulation",
            "Social Boldness",
        ],
    },
    {
        "group": "abilities",
        "key": "divergent_thinking",
        "name": "Divergent Thinking",
        "subtopics": [
            "Associative Fluency",
            "Idea Flexibility",
            "Lateral Problem Solving",
        ],
    },
]

TOPIC_BY_KEY = {str(item["key"]): item for item in TOPIC_REGISTRY}


def list_drill_topics() -> list[dict[str, Any]]:
    archetypes = _load_archetype_map()
    topics: list[dict[str, Any]] = []
    for topic in TOPIC_REGISTRY:
        topic_name = str(topic["name"])
        archetype_subtopics = sorted(list((archetypes.get(topic_name) or {}).keys()))
        topics.append(
            {
                "key": str(topic["key"]),
                "group": str(topic["group"]),
                "name": topic_name,
                "subtopics": list(topic.get("subtopics") or []),
                "archetype_subtopics": archetype_subtopics,
            }
        )
    return topics


def build_drill_topic_plan(*, selected_topic_keys: list[str], profile_json: dict[str, Any]) -> dict[str, Any]:
    unique_keys: list[str] = []
    for key in selected_topic_keys:
        normalized = str(key).strip()
        if not normalized:
            continue
        if normalized not in TOPIC_BY_KEY:
            raise ValueError(f"Unsupported drill topic: {normalized}")
        if normalized in unique_keys:
            continue
        unique_keys.append(normalized)
    if len(unique_keys) < 1 or len(unique_keys) > 3:
        raise ValueError("Select between 1 and 3 topics")

    all_keys = [str(item["key"]) for item in TOPIC_REGISTRY]
    levels = {key: _read_profile_topic_level(profile_json=profile_json, topic_key=key) for key in all_keys}
    planned: list[str] = list(unique_keys)
    topic_roles: dict[str, str] = {key: "manual" for key in planned}

    remaining = [key for key in all_keys if key not in planned]
    while len(planned) < 3 and remaining:
        good_pool = [key for key in remaining if levels.get(key, 2.0) >= 3.0]
        candidate_pool = good_pool or sorted(remaining, key=lambda key: levels.get(key, 2.0), reverse=True)
        chosen = random.choice(candidate_pool)
        planned.append(chosen)
        topic_roles[chosen] = "auto_good"
        remaining = [key for key in remaining if key != chosen]

    remaining_after_primary = [key for key in all_keys if key not in planned]
    bad_pool = [key for key in remaining_after_primary if levels.get(key, 2.0) <= 2.0]
    if bad_pool:
        challenge = random.choice(bad_pool)
    elif remaining_after_primary:
        challenge = min(remaining_after_primary, key=lambda key: levels.get(key, 2.0))
    else:
        challenge = min(all_keys, key=lambda key: levels.get(key, 2.0))
    if challenge not in planned:
        planned.append(challenge)
    topic_roles[challenge] = "auto_bad"

    return {
        "selected_topic_keys": unique_keys,
        "planned_topic_keys": planned,
        "topic_roles": topic_roles,
    }


def generate_drill_question_set(*, drill_topic_keys: list[str], topic_roles: dict[str, str] | None = None) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    unique_keys: list[str] = []
    for topic_key in drill_topic_keys:
        normalized = str(topic_key).strip()
        if not normalized:
            continue
        if normalized not in TOPIC_BY_KEY:
            raise ValueError(f"Unsupported drill topic: {normalized}")
        if normalized in unique_keys:
            continue
        unique_keys.append(normalized)
    if len(unique_keys) < 1:
        raise ValueError("No drill topics planned")

    role_map = dict(topic_roles or {})
    for topic_index, topic_key in enumerate(unique_keys):
        topic = dict(TOPIC_BY_KEY[topic_key])
        subtopic_a, subtopic_b = _choose_subtopic_pair(topic)
        topic_source = str(role_map.get(topic_key) or "manual")
        block_index = topic_index + 1
        if topic_source == "auto_bad":
            block_label = "Challenge"
        elif topic_source == "auto_good":
            block_label = "Reinforcement"
        else:
            block_label = f"Selected {block_index}"
        question_plan = [
            (1, "recalibration", "reverse_definition", subtopic_a, None),
            (2, "threshold", "spot_the_flaw", subtopic_a, None),
            (3, "sidestep", "analogy_match", subtopic_b, subtopic_a),
            (4, "stress_test", "power_sprint", subtopic_a, None),
        ]
        for question_index, kind, archetype, subtopic_name, related_subtopic in question_plan:
            prompt = _resolve_archetype_prompt(
                topic_name=str(topic["name"]),
                subtopic_name=subtopic_name,
                archetype=archetype,
                kind=kind,
            )
            question_id = f"{topic_key}-b{block_index}-q{question_index}"
            questions.append(
                {
                    "id": question_id,
                    "topic_key": topic_key,
                    "topic_name": str(topic["name"]),
                    "topic_group": str(topic["group"]),
                    "topic_source": topic_source,
                    "block_index": block_index,
                    "block_label": block_label,
                    "question_index": question_index,
                    "kind": kind,
                    "archetype": archetype,
                    "focus_subtopic": subtopic_name,
                    "related_subtopic": related_subtopic,
                    "prompt": prompt,
                    "time_limit_seconds": DRILL_STRESS_TIME_LIMIT_SECONDS if kind == "stress_test" else None,
                    "expected_keywords": _derive_keywords(
                        topic_name=str(topic["name"]),
                        subtopic_name=subtopic_name,
                        prompt=prompt,
                    ),
                }
            )
    return questions


def evaluate_drill_attempt(
    *,
    user_id: int,
    selected_topic_keys: list[str],
    question_set: list[dict[str, Any]],
    answers: dict[str, Any],
    base_profile_json: dict[str, Any],
    ai_validation_overrides: dict[str, bool] | None = None,
) -> dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    profile_json = _normalize_profile_json(base_profile_json=base_profile_json, user_id=user_id)
    drill_state = dict(profile_json.get("drill_state") or {})
    topic_nodes = dict(drill_state.get("topic_nodes") or {})

    per_topic_result: dict[str, Any] = {}

    for topic_key in selected_topic_keys:
        topic = TOPIC_BY_KEY.get(topic_key)
        if topic is None:
            continue
        topic_questions = [item for item in question_set if str(item.get("topic_key")) == topic_key]
        if not topic_questions:
            continue

        existing_node = dict(topic_nodes.get(topic_key) or {})
        current_level = float(existing_node.get("level") or _read_top_level(profile_json, str(topic.get("group")), topic_key))
        current_level = _clamp_level(current_level)
        sub_nodes = dict(existing_node.get("sub_nodes") or {})
        map_decay_events = int(existing_node.get("map_decay_events_total") or 0)

        parent_delta = 0.0
        positive_blocks = 0
        stress_scores: list[float] = []
        block_results: list[dict[str, Any]] = []

        block_indexes = sorted({int(item.get("block_index") or 0) for item in topic_questions if int(item.get("block_index") or 0) > 0})
        for block_index in block_indexes:
            block_questions = sorted(
                [item for item in topic_questions if int(item.get("block_index") or 0) == block_index],
                key=lambda item: int(item.get("question_index") or 0),
            )
            if len(block_questions) < 4:
                continue
            scored: list[dict[str, Any]] = []
            for question in block_questions:
                raw_answer = answers.get(str(question.get("id")))
                answer_text = _extract_answer_text(raw_answer)
                response_seconds = _extract_response_seconds(raw_answer, question)
                keyword_score = _keyword_score(answer_text, list(question.get("expected_keywords") or []))
                override_value = (ai_validation_overrides or {}).get(str(question.get("id")))
                is_correct = bool(override_value) if override_value is not None else keyword_score >= 1.0
                time_limit = int(question.get("time_limit_seconds") or 0)
                if str(question.get("kind")) == "stress_test":
                    time_remaining_ratio = _time_remaining_ratio(response_seconds, time_limit or DRILL_STRESS_TIME_LIMIT_SECONDS)
                    ability_score = (1.0 if is_correct else 0.0) * 0.7 + (time_remaining_ratio * 0.3)
                    stress_scores.append(ability_score)
                else:
                    time_remaining_ratio = None
                    ability_score = None
                scored.append(
                    {
                        "question_id": str(question.get("id")),
                        "kind": str(question.get("kind")),
                        "focus_subtopic": str(question.get("focus_subtopic") or ""),
                        "answer": answer_text,
                        "response_time_seconds": response_seconds,
                        "keyword_score": round(keyword_score, 4),
                        "is_correct": is_correct,
                        "time_remaining_ratio": round(time_remaining_ratio, 4) if time_remaining_ratio is not None else None,
                        "ability_score": round(ability_score, 4) if ability_score is not None else None,
                    }
                )

            q1 = scored[0]
            q2 = scored[1]
            q3 = scored[2]
            q4 = scored[3]
            q1_pass = bool(q1["is_correct"])
            q2_pass = bool(q2["is_correct"])
            q3_pass = bool(q3["is_correct"])

            if q1_pass and q2_pass:
                parent_delta += 0.2
                positive_blocks += 1
            if not q1_pass:
                parent_delta -= 0.1
                map_decay_events += 1

            focus_subtopic = str(block_questions[0].get("focus_subtopic") or "")
            related_subtopic = str(block_questions[2].get("focus_subtopic") or "")
            if focus_subtopic:
                existing_sub = float(sub_nodes.get(focus_subtopic) or max(1.0, current_level - 0.4))
                sub_delta = 0.2 if sum([1 for item in [q1_pass, q2_pass, q3_pass] if item]) >= 2 else 0.05
                sub_nodes[focus_subtopic] = round(_clamp_level(existing_sub + sub_delta), 3)
            if related_subtopic:
                existing_related = float(sub_nodes.get(related_subtopic) or max(1.0, current_level - 0.55))
                related_delta = 0.1 if q3_pass else 0.02
                sub_nodes[related_subtopic] = round(_clamp_level(existing_related + related_delta), 3)

            block_results.append(
                {
                    "block_index": block_index,
                    "q1_pass": q1_pass,
                    "q2_pass": q2_pass,
                    "q3_pass": q3_pass,
                    "map_decay_triggered": not q1_pass,
                    "stress_ability_score": q4.get("ability_score"),
                    "questions": scored,
                }
            )

        next_level = _clamp_level(current_level + parent_delta)
        if str(topic.get("group")) == "abilities" and stress_scores:
            ability_projection = 1.0 + (sum(stress_scores) / max(len(stress_scores), 1)) * 4.0
            next_level = _clamp_level((next_level * 0.7) + (ability_projection * 0.3))

        rounded_level = _to_chart_level(next_level)
        _write_top_level(profile_json, str(topic.get("group")), topic_key, rounded_level)

        previous_confidence = float(existing_node.get("confidence") or 0.7)
        confidence = max(0.0, min(1.0, previous_confidence - (0.15 * (map_decay_events - int(existing_node.get("map_decay_events_total") or 0))) + (0.05 * positive_blocks)))

        topic_nodes[topic_key] = {
            "group": str(topic.get("group")),
            "name": str(topic.get("name")),
            "level": round(next_level, 3),
            "chart_level": rounded_level,
            "status": "map_decay" if map_decay_events > int(existing_node.get("map_decay_events_total") or 0) else "verified",
            "confidence": round(confidence, 3),
            "map_decay_events_total": map_decay_events,
            "sub_nodes": sub_nodes,
            "last_drill_at": now_iso,
        }

        per_topic_result[topic_key] = {
            "topic_name": str(topic.get("name")),
            "group": str(topic.get("group")),
            "source": _topic_source_for_question_set(question_set=question_set, topic_key=topic_key),
            "initial_level": round(current_level, 3),
            "delta": round(next_level - current_level, 3),
            "final_level": round(next_level, 3),
            "chart_level": rounded_level,
            "sub_nodes": sub_nodes,
            "blocks": block_results,
            "map_decay_events_total": map_decay_events,
        }

    drill_attempt_count = int(drill_state.get("attempt_count") or 0) + 1
    drill_state["attempt_count"] = drill_attempt_count
    drill_state["last_drill_at"] = now_iso
    drill_state["topic_nodes"] = topic_nodes
    drill_state["archetype_source"] = ARCHETYPE_FILE_RELATIVE_PATH
    drill_state["selected_topic_keys_last"] = selected_topic_keys

    profile_json["drill_state"] = drill_state
    profile_json["has_assessment"] = bool(profile_json.get("has_assessment", False)) or True
    profile_json["profile_source"] = "assessment"

    assessment_details = dict(profile_json.get("assessment_details") or {})
    derived = dict(assessment_details.get("derived") or {})
    logic_level = float(topic_nodes.get("executive_function", {}).get("level") or _read_top_level(profile_json, "abilities", "executive_function"))
    quant_level = float(topic_nodes.get("quantitative_reasoning", {}).get("level") or _read_top_level(profile_json, "abilities", "quantitative_reasoning"))
    logic_quant_index = (logic_level / 5.0) + (quant_level / 5.0)
    learning_speed_multiplier = 1.5 if logic_quant_index > 1.6 else 1.0
    derived["logic_quantitative_index"] = round(logic_quant_index, 4)
    derived["learning_speed_multiplier"] = learning_speed_multiplier
    assessment_details["derived"] = derived
    profile_json["assessment_details"] = assessment_details

    result_json = {
        "version": DRILL_ASSESSMENT_VERSION,
        "completed_at": now_iso,
        "selected_topic_keys": selected_topic_keys,
        "topic_updates": per_topic_result,
        "archetype_source": ARCHETYPE_FILE_RELATIVE_PATH,
        "drill_flow": {
            "questions_per_topic": 4,
            "block_count": len(selected_topic_keys),
            "structure": ["Q1 Recalibration", "Q2 Threshold", "Q3 Side-Step", "Q4 Stress-Test"],
        },
    }

    return {
        "result_json": result_json,
        "updated_profile_json": profile_json,
    }


@lru_cache(maxsize=1)
def _load_archetype_map() -> dict[str, dict[str, dict[str, str]]]:
    root = Path(__file__).resolve().parents[3]
    path = root / ARCHETYPE_FILE_RELATIVE_PATH
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    result: dict[str, dict[str, dict[str, str]]] = {}
    for section_key in ("knowledge_nodes", "skills_nodes", "abilities_nodes"):
        for node in list(payload.get(section_key) or []):
            parent = str(node.get("parent") or "").strip()
            if not parent:
                continue
            topic_map = result.setdefault(parent, {})
            for subtopic in list(node.get("subtopics") or []):
                subtopic_name = str(subtopic.get("name") or "").strip()
                if not subtopic_name:
                    continue
                archetypes = dict(subtopic.get("archetypes") or {})
                topic_map[subtopic_name] = {
                    "reverse_definition": str(archetypes.get("reverse_definition") or "").strip(),
                    "spot_the_flaw": str(archetypes.get("spot_the_flaw") or "").strip(),
                    "power_sprint": str(archetypes.get("power_sprint") or "").strip(),
                    "analogy_match": str(archetypes.get("analogy_match") or "").strip(),
                }
    return result


def _choose_subtopic_pair(topic: dict[str, Any]) -> tuple[str, str]:
    topic_name = str(topic.get("name") or "")
    all_subtopics = list(topic.get("subtopics") or [])
    source_map = _load_archetype_map().get(topic_name) or {}
    preferred = [name for name in all_subtopics if name in source_map]
    if len(preferred) >= 2:
        return preferred[0], preferred[1]
    if len(preferred) == 1:
        fallback = all_subtopics[1] if len(all_subtopics) > 1 else preferred[0]
        return preferred[0], fallback
    if len(all_subtopics) >= 2:
        return all_subtopics[0], all_subtopics[1]
    if len(all_subtopics) == 1:
        return all_subtopics[0], all_subtopics[0]
    return "General Foundation", "Applied Foundation"


def _resolve_archetype_prompt(*, topic_name: str, subtopic_name: str, archetype: str, kind: str) -> str:
    source = _load_archetype_map().get(topic_name) or {}
    subtopic_archetypes = source.get(subtopic_name) or {}
    prompt = str(subtopic_archetypes.get(archetype) or "").strip()
    if prompt:
        return prompt
    if kind == "recalibration":
        return f"In {topic_name}, explain a core principle of {subtopic_name} in one or two sentences."
    if kind == "threshold":
        return f"Identify a common advanced mistake in {subtopic_name} and explain why it fails."
    if kind == "sidestep":
        return f"Use an analogy to connect {subtopic_name} to a practical real-world system."
    return f"Power sprint (15s): give a concise applied answer in {subtopic_name}."


def _normalize_text(value: str) -> str:
    text = str(value or "").casefold()
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _derive_keywords(*, topic_name: str, subtopic_name: str, prompt: str) -> list[str]:
    seed = f"{topic_name} {subtopic_name} {prompt}"
    normalized = _normalize_text(seed)
    tokens = [token for token in normalized.split(" ") if len(token) >= 4]
    dedup: list[str] = []
    for token in tokens:
        if token not in dedup:
            dedup.append(token)
    return dedup[:8]


def _extract_answer_text(raw_answer: Any) -> str:
    if isinstance(raw_answer, dict):
        if "value" in raw_answer:
            return str(raw_answer.get("value") or "").strip()
        return str(raw_answer.get("answer") or "").strip()
    return str(raw_answer or "").strip()


def _extract_response_seconds(raw_answer: Any, question: dict[str, Any]) -> float:
    default_limit = float(question.get("time_limit_seconds") or DRILL_STRESS_TIME_LIMIT_SECONDS)
    if not isinstance(raw_answer, dict):
        return default_limit
    try:
        value = float(raw_answer.get("response_time_seconds"))
    except Exception:
        return default_limit
    if value < 0:
        return 0.0
    return min(value, default_limit)


def _keyword_score(answer: str, expected_keywords: list[str]) -> float:
    normalized = _normalize_text(answer)
    if not normalized:
        return 0.0
    answer_tokens = _normalize_tokens(normalized.split(" "))
    keywords = [_normalize_text(keyword) for keyword in expected_keywords]
    keywords = [item for item in keywords if item]
    normalized_answer_spaced = f" {normalized} "
    if not keywords:
        return 1.0 if len(answer_tokens) >= 3 else 0.0
    hits = 0
    for keyword in keywords:
        keyword_tokens = _normalize_tokens(keyword.split(" "))
        keyword_token = next(iter(keyword_tokens), "")
        if keyword and f" {keyword} " in normalized_answer_spaced:
            hits += 1
            continue
        if keyword_token and any(_tokens_match(answer_token, keyword_token) for answer_token in answer_tokens):
            hits += 1
    if hits >= 2:
        return 1.0
    if hits == 1 and len(answer_tokens) >= 6:
        return 1.0
    return 0.0


def _normalize_tokens(tokens: list[str]) -> set[str]:
    normalized: set[str] = set()
    for token in tokens:
        value = str(token).strip()
        if not value:
            continue
        if len(value) > 4 and value.endswith("ing"):
            value = value[:-3]
        elif len(value) > 3 and value.endswith("ed"):
            value = value[:-2]
        elif len(value) > 3 and value.endswith("es"):
            value = value[:-2]
        elif len(value) > 3 and value.endswith("s"):
            value = value[:-1]
        if value:
            normalized.add(value)
    return normalized


def _tokens_match(left: str, right: str) -> bool:
    if left == right:
        return True
    if len(left) >= 4 and len(right) >= 4:
        return left.startswith(right) or right.startswith(left)
    return False


def _time_remaining_ratio(response_seconds: float, limit_seconds: int) -> float:
    if limit_seconds <= 0:
        return 0.0
    return max(0.0, min(1.0, (float(limit_seconds) - response_seconds) / float(limit_seconds)))


def _clamp_level(value: float) -> float:
    return max(1.0, min(5.0, float(value)))


def _to_chart_level(value: float) -> int:
    return max(1, min(5, int(round(value))))


def _normalize_profile_json(*, base_profile_json: dict[str, Any], user_id: int) -> dict[str, Any]:
    knowledge = dict(base_profile_json.get("knowledge") or {})
    skills = dict(base_profile_json.get("skills") or {})
    abilities = dict(base_profile_json.get("abilities") or {})
    for topic in TOPIC_REGISTRY:
        group = str(topic["group"])
        key = str(topic["key"])
        if group == "knowledge" and key not in knowledge:
            knowledge[key] = 2
        if group == "skills" and key not in skills:
            skills[key] = 2
        if group == "abilities" and key not in abilities:
            abilities[key] = 2
    return {
        **base_profile_json,
        "user_id": int(base_profile_json.get("user_id") or user_id),
        "scale_min": 1,
        "scale_max": 5,
        "dreyfus_levels": list(base_profile_json.get("dreyfus_levels") or ["Novice", "Advanced", "Competent", "Proficient", "Expert"]),
        "knowledge": knowledge,
        "skills": skills,
        "abilities": abilities,
    }


def _read_profile_topic_level(*, profile_json: dict[str, Any], topic_key: str) -> float:
    topic = TOPIC_BY_KEY.get(topic_key)
    if topic is None:
        return 2.0
    group = str(topic.get("group") or "")
    section = dict(profile_json.get(group) or {})
    try:
        return _clamp_level(float(section.get(topic_key) or 2.0))
    except Exception:
        return 2.0


def _topic_source_for_question_set(*, question_set: list[dict[str, Any]], topic_key: str) -> str:
    for item in question_set:
        if str(item.get("topic_key")) == topic_key:
            value = str(item.get("topic_source") or "").strip()
            if value:
                return value
    return "manual"


def _read_top_level(profile_json: dict[str, Any], group: str, topic_key: str) -> int:
    return int(dict(profile_json.get(group) or {}).get(topic_key) or 2)


def _write_top_level(profile_json: dict[str, Any], group: str, topic_key: str, value: int) -> None:
    section = dict(profile_json.get(group) or {})
    section[topic_key] = int(value)
    profile_json[group] = section
