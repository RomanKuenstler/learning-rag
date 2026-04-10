from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
import json
from pathlib import Path
import random
import re
from typing import Any, Callable


DRILL_ASSESSMENT_VERSION = "ksa-drill-v1"
DRILL_STRESS_TIME_LIMIT_SECONDS = 15
ARCHETYPE_FILE_RELATIVE_PATH = "prds/interaction-archetypes_ksa.json"
PROMPTS_DIR_RELATIVE_PATH = "prompts"
PROMPT_TOPIC_CLASSIFICATION = "ksa-topic-classification.md"
PROMPT_SAME_TOPIC_VARIANT = "ksa-same-topic-variant.md"
PROMPT_DYNAMIC_TOPIC_SELECTION = "ksa-dynamic-topic-selection.md"
PROMPT_ARCHETYPE_GENERATION = "ksa-archetype-generation.md"


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
TOPIC_GROUP_TO_BIG_MAP = {
    "knowledge": "Knowledge",
    "skills": "Skills",
    "abilities": "Abilities",
}
BIG_MAP_TO_TOPIC_GROUP = {value: key for key, value in TOPIC_GROUP_TO_BIG_MAP.items()}
TOPIC_NAME_TO_KEY = {str(item["name"]).casefold(): str(item["key"]) for item in TOPIC_REGISTRY}
ARCHETYPE_KIND_MAP = {
    "REVERSE_DEFINITION": ("recalibration", "reverse_definition"),
    "SPOT_THE_FLAW": ("threshold", "spot_the_flaw"),
    "ANALOGY_MATCH": ("sidestep", "analogy_match"),
    "POWER_SPRINT": ("stress_test", "power_sprint"),
}
REQUIRED_ARCHETYPE_TYPES = {"REVERSE_DEFINITION", "SPOT_THE_FLAW", "POWER_SPRINT", "ANALOGY_MATCH"}


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


def classify_drill_topic_input(
    *,
    source_topic_input: str,
    llm_invoke: Callable[[list[tuple[str, str]]], str],
) -> dict[str, Any]:
    user_input = str(source_topic_input or "").strip()
    if not user_input:
        raise ValueError("Topic input cannot be empty")
    prompt = render_ksa_prompt_template(PROMPT_TOPIC_CLASSIFICATION, {"USER_INPUT": user_input})
    raw = llm_invoke([("system", prompt)])
    parsed = _extract_json_object(raw)
    return _validate_topic_classification(parsed)


def plan_dynamic_drill_rounds(
    *,
    source_topic_input: str,
    topic_classification: dict[str, Any],
    profile_json: dict[str, Any],
    llm_invoke: Callable[[list[tuple[str, str]]], str],
) -> dict[str, Any]:
    classification = _validate_topic_classification(topic_classification)
    rankings = _rank_big_map_topics(profile_json=profile_json)

    round_1 = {
        "round_number": 1,
        "origin": "user_core",
        "type_combo": str(classification["type_combo"]),
        "big_map_group": str(classification["big_map_group"]),
        "big_map_subdomain": str(classification["big_map_subdomain"]),
        "detailed_topic": str(classification["detailed_topic"]),
        "rationale": "Core user-entered topic normalized through classification.",
    }

    variant_prompt = render_ksa_prompt_template(
        PROMPT_SAME_TOPIC_VARIANT,
        {
            "USER_TOPIC": str(source_topic_input).strip(),
            "ROUND_1_TOPIC": str(round_1["detailed_topic"]),
        },
    )
    variant_raw = llm_invoke([("system", variant_prompt)])
    variant_parsed = _extract_json_object(variant_raw)
    round_2_topic = str(variant_parsed.get("round_2_detailed_topic") or "").strip()
    if not round_2_topic:
        raise ValueError("Round 2 topic generation returned empty topic")
    round_2 = {
        "round_number": 2,
        "origin": "user_variant",
        "type_combo": str(classification["type_combo"]),
        "big_map_group": str(classification["big_map_group"]),
        "big_map_subdomain": str(classification["big_map_subdomain"]),
        "detailed_topic": round_2_topic,
        "rationale": str(variant_parsed.get("rationale") or "").strip(),
    }

    selection_prompt = render_ksa_prompt_template(
        PROMPT_DYNAMIC_TOPIC_SELECTION,
        {
            "USER_KSA_PROFILE": json.dumps(profile_json, ensure_ascii=False),
            "BIG_MAP_STRENGTHS": json.dumps(rankings["strengths"], ensure_ascii=False),
            "BIG_MAP_WEAKNESSES": json.dumps(rankings["weaknesses"], ensure_ascii=False),
        },
    )
    selection_raw = llm_invoke([("system", selection_prompt)])
    selection_parsed = _extract_json_object(selection_raw)
    stretch = _validate_dynamic_topic_node(selection_parsed.get("stretch_topic"), label="stretch_topic")
    growth = _validate_dynamic_topic_node(selection_parsed.get("growth_topic"), label="growth_topic")
    stretch, growth = _enforce_dynamic_round_constraints(
        stretch=stretch,
        growth=growth,
        rankings=rankings,
        classification=classification,
    )

    rounds = [
        round_1,
        round_2,
        {
            "round_number": 3,
            "origin": "llm_stretch",
            "type_combo": _group_to_type_combo(str(stretch["big_map_group"])),
            **stretch,
        },
        {
            "round_number": 4,
            "origin": "llm_growth",
            "type_combo": _group_to_type_combo(str(growth["big_map_group"])),
            **growth,
        },
    ]
    return {
        "rounds": rounds,
        "ranking": rankings,
    }


def generate_round_archetypes(
    *,
    rounds: list[dict[str, Any]],
    llm_invoke: Callable[[list[tuple[str, str]]], str],
) -> dict[str, Any]:
    generated_rounds: list[dict[str, Any]] = []
    question_set: list[dict[str, Any]] = []

    for round_node in rounds:
        round_number = int(round_node.get("round_number") or 0)
        detailed_topic = str(round_node.get("detailed_topic") or "").strip()
        if round_number < 1 or not detailed_topic:
            raise ValueError("Invalid round metadata for archetype generation")
        prompt = render_ksa_prompt_template(PROMPT_ARCHETYPE_GENERATION, {"SUBTOPIC": detailed_topic})
        raw = llm_invoke([("system", prompt)])
        parsed = _extract_json_object(raw)
        archetype_questions = _validate_archetype_payload(parsed)
        topic_group = BIG_MAP_TO_TOPIC_GROUP.get(str(round_node.get("big_map_group") or ""), "skills")
        topic_key = _topic_key_from_round(round_node=round_node)
        topic_name = str(round_node.get("big_map_subdomain") or round_node.get("big_map_group") or "Dynamic Topic")
        round_questions: list[dict[str, Any]] = []
        for question_index, archetype_question in enumerate(archetype_questions, start=1):
            archetype_type = str(archetype_question["type"])
            kind, archetype = ARCHETYPE_KIND_MAP[archetype_type]
            choices = [
                str(archetype_question["correct_answer"]),
                *[str(item) for item in list(archetype_question["distractors"])],
            ]
            prompt_text = _compose_multiple_choice_prompt(
                question=str(archetype_question["question"]),
                choices=choices,
            )
            question_id = f"{topic_key}-r{round_number}-q{question_index}"
            payload = {
                "id": question_id,
                "topic_key": topic_key,
                "topic_name": topic_name,
                "topic_group": topic_group,
                "topic_source": str(round_node.get("origin") or "manual"),
                "block_index": round_number,
                "block_label": f"Round {round_number}",
                "question_index": question_index,
                "kind": kind,
                "archetype": archetype,
                "focus_subtopic": detailed_topic,
                "related_subtopic": None,
                "prompt": prompt_text,
                "choices": choices,
                "correct_answer": str(archetype_question["correct_answer"]),
                "distractors": [str(item) for item in list(archetype_question["distractors"])],
                "time_limit_seconds": DRILL_STRESS_TIME_LIMIT_SECONDS if archetype_type == "POWER_SPRINT" else None,
                "expected_keywords": _derive_keywords(
                    topic_name=topic_name,
                    subtopic_name=detailed_topic,
                    prompt=str(archetype_question["correct_answer"]),
                ),
            }
            question_set.append(payload)
            round_questions.append(payload)

        generated_rounds.append(
            {
                **round_node,
                "questions": round_questions,
            }
        )

    if len(question_set) != 16:
        raise ValueError("Dynamic drill generation must produce exactly 16 questions")
    return {
        "rounds": generated_rounds,
        "question_set": question_set,
    }


def render_ksa_prompt_template(template_name: str, variables: dict[str, str]) -> str:
    template = _load_prompt_template(template_name)
    rendered = template
    missing_keys: list[str] = []
    for match in re.finditer(r"\{\{([A-Z0-9_]+)\}\}", template):
        key = str(match.group(1))
        if key not in variables:
            missing_keys.append(key)
    if missing_keys:
        raise ValueError(f"Missing prompt template variables for {template_name}: {', '.join(sorted(set(missing_keys)))}")
    for key, value in variables.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
    return rendered


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


def _load_prompt_template(template_name: str) -> str:
    root = Path(__file__).resolve().parents[3]
    path = root / PROMPTS_DIR_RELATIVE_PATH / template_name
    if not path.exists():
        raise ValueError(f"Prompt template not found: {template_name}")
    return path.read_text(encoding="utf-8").strip()


def _extract_json_object(text: str) -> dict[str, Any]:
    raw = str(text or "").strip()
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in LLM response")
    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("LLM response JSON is not an object")
    return parsed


def _validate_topic_classification(payload: dict[str, Any]) -> dict[str, Any]:
    type_combo = _normalize_type_combo(payload.get("type_combo"))
    primary = _normalize_single_type(payload.get("primary_type"))
    secondary_raw = payload.get("secondary_type")
    secondary = None if secondary_raw in (None, "", "null", "NULL") else _normalize_single_type(secondary_raw)
    big_map_group = _normalize_big_map_group(payload.get("big_map_group"))
    big_map_subdomain = str(payload.get("big_map_subdomain") or "").strip()
    detailed_topic = str(payload.get("detailed_topic") or "").strip()
    user_explanation = str(payload.get("user_explanation") or "").strip()

    combo_parts = [part for part in type_combo.split("+") if part]
    if primary is None:
        primary = combo_parts[0] if combo_parts else None
    if primary not in {"K", "S", "A"}:
        raise ValueError("Invalid primary_type in topic classification")
    if secondary is not None and secondary not in {"K", "S", "A"}:
        raise ValueError("Invalid secondary_type in topic classification")
    if type_combo not in {"K", "S", "A", "K+S", "K+A", "S+A", "K+S+A"}:
        raise ValueError("Invalid type_combo in topic classification")
    if big_map_group is None:
        big_map_group = _infer_big_map_group_from_subdomain(big_map_subdomain) or _infer_big_map_group_from_type_combo(type_combo)
    if big_map_group not in {"Knowledge", "Skills", "Abilities"}:
        raise ValueError("Invalid big_map_group in topic classification")
    if not big_map_subdomain:
        raise ValueError("Missing big_map_subdomain in topic classification")
    if not detailed_topic:
        raise ValueError("Missing detailed_topic in topic classification")
    if not user_explanation:
        raise ValueError("Missing user_explanation in topic classification")
    if big_map_subdomain.casefold() not in TOPIC_NAME_TO_KEY:
        raise ValueError("Unknown big_map_subdomain in topic classification")

    return {
        "primary_type": primary,
        "secondary_type": secondary,
        "type_combo": type_combo,
        "big_map_group": big_map_group,
        "big_map_subdomain": big_map_subdomain,
        "detailed_topic": detailed_topic,
        "user_explanation": user_explanation,
    }


def _normalize_big_map_group(value: Any) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    lowered = raw.casefold()
    if lowered in {"knowledge", "k"}:
        return "Knowledge"
    if lowered in {"skills", "skill", "s"}:
        return "Skills"
    if lowered in {"abilities", "ability", "a"}:
        return "Abilities"
    return None


def _infer_big_map_group_from_subdomain(subdomain: str) -> str | None:
    key = TOPIC_NAME_TO_KEY.get(str(subdomain or "").casefold())
    if not key:
        return None
    topic = TOPIC_BY_KEY.get(key)
    if not topic:
        return None
    return TOPIC_GROUP_TO_BIG_MAP.get(str(topic.get("group") or ""))


def _infer_big_map_group_from_type_combo(type_combo: str) -> str | None:
    parts = [item for item in str(type_combo or "").split("+") if item]
    if len(parts) == 1:
        if parts[0] == "K":
            return "Knowledge"
        if parts[0] == "S":
            return "Skills"
        if parts[0] == "A":
            return "Abilities"
    return None


def _normalize_single_type(value: Any) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    upper = raw.upper()
    if upper in {"K", "S", "A"}:
        return upper
    letters_only = re.sub(r"[^A-Z]", "", upper)
    if letters_only in {"K", "S", "A"}:
        return letters_only
    lowered = raw.casefold()
    if "knowledge" in lowered:
        return "K"
    if "skill" in lowered:
        return "S"
    if "abilit" in lowered:
        return "A"
    return None


def _normalize_type_combo(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("Invalid type_combo in topic classification")
    upper = raw.upper()
    if upper in {"K", "S", "A", "K+S", "K+A", "S+A", "K+S+A"}:
        return upper

    lowered = raw.casefold()
    inferred: list[str] = []
    if "knowledge" in lowered:
        inferred.append("K")
    if "skill" in lowered:
        inferred.append("S")
    if "abilit" in lowered:
        inferred.append("A")

    if not inferred:
        letter_hits = [hit for hit in re.findall(r"[KSA]", upper) if hit in {"K", "S", "A"}]
        ordered: list[str] = []
        for key in ("K", "S", "A"):
            if key in letter_hits and key not in ordered:
                ordered.append(key)
        inferred = ordered

    if not inferred:
        raise ValueError("Invalid type_combo in topic classification")
    normalized = "+".join(inferred)
    if normalized not in {"K", "S", "A", "K+S", "K+A", "S+A", "K+S+A"}:
        raise ValueError("Invalid type_combo in topic classification")
    return normalized


def _rank_big_map_topics(*, profile_json: dict[str, Any]) -> dict[str, Any]:
    topic_nodes = dict(dict(profile_json.get("drill_state") or {}).get("topic_nodes") or {})
    ranked: list[dict[str, Any]] = []
    for topic in TOPIC_REGISTRY:
        key = str(topic["key"])
        group = str(topic["group"])
        node_level = topic_nodes.get(key, {}).get("level")
        if node_level is not None:
            try:
                score = float(node_level)
            except Exception:
                score = _read_profile_topic_level(profile_json=profile_json, topic_key=key)
        else:
            score = _read_profile_topic_level(profile_json=profile_json, topic_key=key)
        ranked.append(
            {
                "topic_key": key,
                "big_map_group": TOPIC_GROUP_TO_BIG_MAP.get(group, "Skills"),
                "big_map_subdomain": str(topic["name"]),
                "score": round(_clamp_level(score), 3),
            }
        )
    strengths = sorted(ranked, key=lambda item: float(item["score"]), reverse=True)
    weaknesses = sorted(ranked, key=lambda item: float(item["score"]))
    strongest_key = str(strengths[0]["topic_key"]) if strengths else ""
    strong_not_strongest = [item for item in strengths if str(item["topic_key"]) != strongest_key]
    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "strong_not_strongest": strong_not_strongest,
    }


def _validate_dynamic_topic_node(payload: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError(f"Missing {label} in dynamic topic selection")
    big_map_group = str(payload.get("big_map_group") or "").strip()
    big_map_subdomain = str(payload.get("big_map_subdomain") or "").strip()
    detailed_topic = str(payload.get("detailed_topic") or "").strip()
    rationale = str(payload.get("rationale") or "").strip()
    if big_map_group not in {"Knowledge", "Skills", "Abilities"}:
        raise ValueError(f"Invalid {label}.big_map_group")
    if not big_map_subdomain:
        raise ValueError(f"Missing {label}.big_map_subdomain")
    if big_map_subdomain.casefold() not in TOPIC_NAME_TO_KEY:
        raise ValueError(f"Unknown {label}.big_map_subdomain")
    if not detailed_topic:
        raise ValueError(f"Missing {label}.detailed_topic")
    return {
        "big_map_group": big_map_group,
        "big_map_subdomain": big_map_subdomain,
        "detailed_topic": detailed_topic,
        "rationale": rationale,
    }


def _enforce_dynamic_round_constraints(
    *,
    stretch: dict[str, Any],
    growth: dict[str, Any],
    rankings: dict[str, Any],
    classification: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    strengths = [dict(item) for item in list(rankings.get("strengths") or [])]
    weaknesses = [dict(item) for item in list(rankings.get("weaknesses") or [])]
    strong_not_strongest = [dict(item) for item in list(rankings.get("strong_not_strongest") or [])]
    strongest_subdomain = str((strengths[0] if strengths else {}).get("big_map_subdomain") or "")
    strongest_group = str((strengths[0] if strengths else {}).get("big_map_group") or "")

    stretch_subdomain = str(stretch.get("big_map_subdomain") or "")
    stretch_group = str(stretch.get("big_map_group") or "")
    if not strong_not_strongest or (
        stretch_subdomain == strongest_subdomain and stretch_group == strongest_group
    ):
        fallback = strong_not_strongest[0] if strong_not_strongest else (strengths[1] if len(strengths) > 1 else (strengths[0] if strengths else None))
        if fallback is not None:
            fallback_subdomain = str(fallback.get("big_map_subdomain") or stretch.get("big_map_subdomain") or "")
            stretch = {
                "big_map_group": str(fallback.get("big_map_group") or stretch.get("big_map_group")),
                "big_map_subdomain": fallback_subdomain,
                "detailed_topic": fallback_subdomain,
                "rationale": str(stretch.get("rationale") or "Selected from strong-but-not-strongest profile area."),
            }

    growth_subdomain = str(growth.get("big_map_subdomain") or "")
    growth_group = str(growth.get("big_map_group") or "")
    weak_set = {(str(item.get("big_map_group") or ""), str(item.get("big_map_subdomain") or "")) for item in weaknesses[:8]}
    if weak_set and (growth_group, growth_subdomain) not in weak_set:
        fallback = next((item for item in weaknesses if (str(item.get("big_map_group") or ""), str(item.get("big_map_subdomain") or "")) != (stretch_group, stretch_subdomain)), weaknesses[0])
        fallback_subdomain = str(fallback.get("big_map_subdomain") or growth.get("big_map_subdomain") or "")
        growth = {
            "big_map_group": str(fallback.get("big_map_group") or growth.get("big_map_group")),
            "big_map_subdomain": fallback_subdomain,
            "detailed_topic": fallback_subdomain,
            "rationale": str(growth.get("rationale") or "Selected from weaker profile area."),
        }

    # Keep growth from simply duplicating the core classified domain unless the weak profile ranking also points there.
    core_pair = (str(classification.get("big_map_group") or ""), str(classification.get("big_map_subdomain") or ""))
    growth_pair = (str(growth.get("big_map_group") or ""), str(growth.get("big_map_subdomain") or ""))
    if growth_pair == core_pair and len(weaknesses) > 1:
        fallback = next((item for item in weaknesses if (str(item.get("big_map_group") or ""), str(item.get("big_map_subdomain") or "")) != core_pair), weaknesses[0])
        growth["big_map_group"] = str(fallback.get("big_map_group") or growth["big_map_group"])
        growth["big_map_subdomain"] = str(fallback.get("big_map_subdomain") or growth["big_map_subdomain"])
        if not str(growth.get("detailed_topic") or "").strip():
            growth["detailed_topic"] = str(fallback.get("big_map_subdomain") or "")
    return stretch, growth


def _group_to_type_combo(big_map_group: str) -> str:
    if big_map_group == "Knowledge":
        return "K"
    if big_map_group == "Abilities":
        return "A"
    return "S"


def _validate_archetype_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    questions = list(payload.get("questions") or [])
    if len(questions) != 4:
        raise ValueError("Archetype generation must return exactly 4 questions")
    validated: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in questions:
        if not isinstance(item, dict):
            raise ValueError("Invalid archetype question payload")
        q_type = str(item.get("type") or "").strip().upper()
        if q_type not in REQUIRED_ARCHETYPE_TYPES:
            raise ValueError(f"Unsupported archetype type: {q_type}")
        seen.add(q_type)
        question = str(item.get("question") or "").strip()
        correct = str(item.get("correct_answer") or "").strip()
        distractors = [str(x).strip() for x in list(item.get("distractors") or []) if str(x).strip()]
        options = [str(x).strip() for x in list(item.get("options") or []) if str(x).strip()]
        if len(distractors) < 2 and options:
            candidate_distractors = [option for option in options if option != correct]
            for candidate in candidate_distractors:
                if candidate and candidate not in distractors:
                    distractors.append(candidate)
                if len(distractors) >= 2:
                    break
        if len(distractors) > 2:
            distractors = distractors[:2]
        if not question or not correct or len(distractors) < 2:
            raise ValueError("Each archetype question requires question, correct_answer, and 2 distractors")
        validated.append(
            {
                "type": q_type,
                "question": question,
                "correct_answer": correct,
                "distractors": distractors,
            }
        )
    if seen != REQUIRED_ARCHETYPE_TYPES:
        raise ValueError("Archetype generation missing required question types")
    ordered: list[dict[str, Any]] = []
    for archetype_type in ("REVERSE_DEFINITION", "SPOT_THE_FLAW", "POWER_SPRINT", "ANALOGY_MATCH"):
        ordered.append(next(item for item in validated if str(item["type"]) == archetype_type))
    return ordered


def _topic_key_from_round(*, round_node: dict[str, Any]) -> str:
    subdomain = str(round_node.get("big_map_subdomain") or "").casefold()
    key = TOPIC_NAME_TO_KEY.get(subdomain)
    if key:
        return key
    group = BIG_MAP_TO_TOPIC_GROUP.get(str(round_node.get("big_map_group") or ""), "skills")
    fallback = next((item for item in TOPIC_REGISTRY if str(item.get("group")) == group), TOPIC_REGISTRY[0])
    return str(fallback["key"])


def _compose_multiple_choice_prompt(*, question: str, choices: list[str]) -> str:
    if len(choices) < 3:
        return question
    return f"{question}\nA) {choices[0]}\nB) {choices[1]}\nC) {choices[2]}"
