from __future__ import annotations

from collections import defaultdict
from typing import Any

LAA_DIMENSIONS = {
    "zielklarheit": "Goal clarity",
    "zeitdruck": "Time pressure",
    "strukturbedarf": "Need for structure",
    "feedbackbedarf": "Need for feedback",
    "selbststeuerung": "Self-direction",
    "soziale_lernorientierung": "Social learning orientation",
    "emotionale_sicherheit": "Emotional safety",
    "frustrationsanfaelligkeit": "Frustration sensitivity",
    "technikaffinitaet": "Technical affinity",
    "praxisorientierung": "Practical orientation",
    "sichtbarkeitsmotivation": "Progress visibility motivation",
}

LAA_SINGLE_CHOICE_DIMENSION_MAP: dict[str, dict[str, dict[str, float]]] = {
    "laa_q001": {
        "o1": {"zielklarheit": 1, "zeitdruck": 0.5},
        "o2": {"zielklarheit": 1, "zeitdruck": 1},
        "o3": {"selbststeuerung": 1, "zielklarheit": 0.5},
        "o4": {"praxisorientierung": 1},
        "o5": {"strukturbedarf": 1, "feedbackbedarf": 1},
        "o6": {"zeitdruck": 1, "zielklarheit": 1},
        "o7": {"selbststeuerung": 1, "zielklarheit": 0.5},
    },
    "laa_q002": {
        "o1": {"zeitdruck": 1, "zielklarheit": 0.5},
        "o2": {"zielklarheit": 1, "praxisorientierung": 0.5},
        "o3": {"selbststeuerung": 1},
    },
    "laa_q003": {
        "o1": {"zeitdruck": 1, "zielklarheit": 1},
        "o2": {"zeitdruck": 0.75, "zielklarheit": 1},
        "o3": {"zeitdruck": 0.5, "zielklarheit": 0.75},
        "o4": {"zeitdruck": 0.25, "zielklarheit": 0.75},
        "o5": {"selbststeuerung": 1, "zeitdruck": 0},
    },
    "laa_q004": {
        "o1": {"zielklarheit": 1, "sichtbarkeitsmotivation": 0.5},
        "o2": {"praxisorientierung": 1},
        "o3": {"feedbackbedarf": 1, "sichtbarkeitsmotivation": 1},
        "o4": {"selbststeuerung": 1},
        "o5": {"zielklarheit": 0.75},
    },
    "laa_q005": {
        "o1": {"strukturbedarf": 1, "feedbackbedarf": 0.5},
        "o2": {"strukturbedarf": 0.75},
        "o3": {"selbststeuerung": 0.75},
        "o4": {"selbststeuerung": 1},
        "o5": {"praxisorientierung": 1, "zielklarheit": 0.5},
    },
    "laa_q006": {
        "o1": {"emotionale_sicherheit": 1},
        "o2": {"emotionale_sicherheit": 0.6},
        "o3": {"frustrationsanfaelligkeit": 0.7},
        "o4": {"frustrationsanfaelligkeit": 1, "emotionale_sicherheit": 0.2},
        "o5": {"emotionale_sicherheit": 0.5},
    },
    "laa_q007": {
        "o1": {"feedbackbedarf": 1, "strukturbedarf": 0.5},
        "o2": {"praxisorientierung": 1},
        "o3": {"technikaffinitaet": 0.8, "praxisorientierung": 0.4},
        "o4": {"selbststeuerung": 1},
        "o5": {"soziale_lernorientierung": 1},
    },
    "laa_q008": {
        "o1": {"soziale_lernorientierung": 0.7, "zielklarheit": 0.7},
        "o2": {"praxisorientierung": 0.7},
        "o3": {"praxisorientierung": 1},
        "o4": {"strukturbedarf": 0.6},
        "o5": {"zielklarheit": 0.8},
    },
    "laa_q009": {
        "o1": {"zielklarheit": 0.8},
        "o2": {"feedbackbedarf": 1},
        "o3": {"praxisorientierung": 0.7},
        "o4": {"strukturbedarf": 0.8, "frustrationsanfaelligkeit": 0.6},
        "o5": {"frustrationsanfaelligkeit": 0.5},
        "o6": {"zeitdruck": 0.8, "zielklarheit": 0.7},
        "o7": {"frustrationsanfaelligkeit": 1},
        "o8": {"zeitdruck": 0.3},
    },
    "laa_q010": {
        "o1": {"selbststeuerung": 1, "emotionale_sicherheit": 0.7},
        "o2": {"frustrationsanfaelligkeit": 0.8},
        "o3": {"frustrationsanfaelligkeit": 1},
        "o4": {"emotionale_sicherheit": 1},
        "o5": {"selbststeuerung": 1, "praxisorientierung": 0.5},
        "o6": {"frustrationsanfaelligkeit": 0.9},
    },
    "laa_q011": {
        "o1": {"strukturbedarf": 1, "feedbackbedarf": 0.8},
        "o2": {"strukturbedarf": 0.6},
        "o3": {"strukturbedarf": 0.7},
        "o4": {"selbststeuerung": 1},
        "o5": {"selbststeuerung": 0.8, "strukturbedarf": 0.3},
    },
    "laa_q012": {
        "o1": {"feedbackbedarf": 1, "strukturbedarf": 0.6},
        "o2": {"feedbackbedarf": 0.7},
        "o3": {"zielklarheit": 0.6, "feedbackbedarf": 0.6},
        "o4": {"selbststeuerung": 1},
        "o5": {"feedbackbedarf": 0.4},
    },
    "laa_q013": {
        "o1": {"feedbackbedarf": 1},
        "o2": {"feedbackbedarf": 0.8},
        "o3": {"feedbackbedarf": 0.5},
        "o4": {"selbststeuerung": 0.8},
        "o5": {"selbststeuerung": 1},
    },
    "laa_q014": {
        "o1": {"feedbackbedarf": 0.8},
        "o2": {"soziale_lernorientierung": 0.7, "feedbackbedarf": 0.6},
        "o3": {"sichtbarkeitsmotivation": 0.8, "feedbackbedarf": 0.5},
        "o4": {"sichtbarkeitsmotivation": 0.6},
        "o5": {"sichtbarkeitsmotivation": 0.7},
    },
    "laa_q015": {
        "o1": {"zeitdruck": 0.3},
        "o2": {"zeitdruck": 0.4},
        "o3": {"zielklarheit": 0.6},
        "o4": {"zielklarheit": 0.8},
        "o5": {"zielklarheit": 1},
    },
    "laa_q016": {
        "o1": {"selbststeuerung": 0.7},
        "o2": {"selbststeuerung": 0.6},
        "o3": {"selbststeuerung": 0.5},
        "o4": {"strukturbedarf": 0.6},
        "o5": {"selbststeuerung": 0.8},
    },
    "laa_q017": {
        "o1": {"strukturbedarf": 0.8},
        "o2": {"emotionale_sicherheit": 0.6},
        "o3": {"selbststeuerung": 0.8},
        "o4": {"strukturbedarf": 0.7},
        "o5": {"soziale_lernorientierung": 0.5},
    },
    "laa_q018": {
        "o1": {"technikaffinitaet": 1},
        "o2": {"technikaffinitaet": 0.8},
        "o3": {"technikaffinitaet": 0.5},
        "o4": {"technikaffinitaet": 0.2, "strukturbedarf": 0.5},
        "o5": {"technikaffinitaet": 0.1},
    },
    "laa_q019": {
        "o1": {"technikaffinitaet": 1},
        "o2": {"technikaffinitaet": 0.9},
        "o3": {"technikaffinitaet": 0.7},
        "o4": {"technikaffinitaet": 0.5},
        "o5": {"technikaffinitaet": 0.2},
    },
    "laa_q021": {
        "o1": {"zielklarheit": 1, "zeitdruck": 0.9},
        "o2": {"zielklarheit": 1, "praxisorientierung": 0.8},
        "o3": {"praxisorientierung": 1, "zielklarheit": 0.8},
        "o4": {"selbststeuerung": 0.8},
        "o5": {"emotionale_sicherheit": 0.6},
    },
    "laa_q022": {
        "o1": {"zielklarheit": 1, "zeitdruck": 0.8},
        "o2": {"selbststeuerung": 0.8},
        "o3": {"selbststeuerung": 1, "zielklarheit": 0.6},
        "o4": {"selbststeuerung": 0.7, "praxisorientierung": 0.6},
        "o5": {"zielklarheit": 0.4},
    },
    "laa_q023": {
        "o1": {"technikaffinitaet": 1},
        "o2": {"soziale_lernorientierung": 0.4},
        "o3": {"soziale_lernorientierung": 0.8},
        "o4": {"praxisorientierung": 0.6},
        "o5": {"praxisorientierung": 0.8},
    },
    "laa_q024": {
        "o1": {"praxisorientierung": 0.2},
        "o2": {"praxisorientierung": 1},
        "o3": {"soziale_lernorientierung": 0.2},
        "o4": {"technikaffinitaet": 0.3},
        "o5": {"selbststeuerung": 0.7},
    },
    "laa_q025": {
        "o1": {"zielklarheit": 0.9},
        "o2": {"praxisorientierung": 1},
        "o3": {"sichtbarkeitsmotivation": 1},
        "o4": {"emotionale_sicherheit": 0.8},
        "o5": {"selbststeuerung": 0.8},
    },
    "laa_q043": {
        "o1": {"zielklarheit": 0.9},
        "o2": {"frustrationsanfaelligkeit": 1, "strukturbedarf": 0.7},
        "o3": {"feedbackbedarf": 1},
        "o4": {"soziale_lernorientierung": 0.8},
        "o5": {"frustrationsanfaelligkeit": 0.8},
        "o6": {"strukturbedarf": 1},
        "o7": {"emotionale_sicherheit": 0.3, "frustrationsanfaelligkeit": 0.7},
    },
    "laa_q044": {
        "o1": {"strukturbedarf": 1},
        "o2": {"strukturbedarf": 0.6, "feedbackbedarf": 0.6},
        "o3": {"feedbackbedarf": 0.8, "frustrationsanfaelligkeit": 0.6},
        "o4": {"technikaffinitaet": 0.4, "strukturbedarf": 0.6},
        "o5": {"feedbackbedarf": 0.5},
    },
    "laa_q045": {
        "o1": {"strukturbedarf": 1},
        "o2": {"feedbackbedarf": 1},
        "o3": {"soziale_lernorientierung": 1},
        "o4": {"selbststeuerung": 1},
        "o5": {"praxisorientierung": 1},
    },
    "laa_q046": {
        "o1": {"selbststeuerung": 0.9},
        "o2": {"soziale_lernorientierung": 1},
        "o3": {"selbststeuerung": 0.5, "soziale_lernorientierung": 0.5},
        "o4": {"soziale_lernorientierung": 0.8},
        "o5": {"soziale_lernorientierung": 0.9, "strukturbedarf": 0.4},
    },
    "laa_q047": {
        "o1": {"selbststeuerung": 1},
        "o2": {"strukturbedarf": 1},
        "o3": {"selbststeuerung": 0.6, "strukturbedarf": 0.6},
        "o4": {"praxisorientierung": 0.6, "selbststeuerung": 0.5},
        "o5": {"praxisorientierung": 0.4, "strukturbedarf": 0.4},
    },
    "laa_q048": {
        "o1": {"sichtbarkeitsmotivation": 1},
        "o2": {"sichtbarkeitsmotivation": 0.8},
        "o3": {"sichtbarkeitsmotivation": 0.5},
        "o4": {"selbststeuerung": 0.6},
        "o5": {"selbststeuerung": 0.7, "sichtbarkeitsmotivation": 0.2},
    },
    "laa_q049": {
        "o1": {"praxisorientierung": 0.8},
        "o2": {"praxisorientierung": 0.9},
        "o3": {"strukturbedarf": 0.8},
        "o4": {"strukturbedarf": 0.6, "praxisorientierung": 0.6},
        "o5": {"praxisorientierung": 0.5, "strukturbedarf": 0.5},
    },
    "laa_q050": {
        "o1": {"sichtbarkeitsmotivation": 1, "soziale_lernorientierung": 0.4},
        "o2": {"sichtbarkeitsmotivation": 0.7, "soziale_lernorientierung": 0.8},
        "o3": {"selbststeuerung": 0.8, "sichtbarkeitsmotivation": 0.6},
        "o4": {"selbststeuerung": 0.9, "sichtbarkeitsmotivation": 0.2},
        "o5": {"sichtbarkeitsmotivation": 0.2},
    },
}

LAA_MULTI_TAG_MAP: dict[str, dict[str, str]] = {
    "laa_q020": {
        "o1": "video-platforms",
        "o2": "note-and-organization-apps",
        "o3": "learning-apps-and-courses",
        "o4": "podcasts-and-audiobooks",
        "o5": "messaging-and-digital-groups",
    },
    "laa_q026": {
        "o1": "sustainability-and-environment",
        "o2": "technology-and-digitalization",
        "o3": "health-and-nutrition",
        "o4": "art-music-and-design",
        "o5": "psychology-communication-and-people",
    },
    "laa_q027": {
        "o1": "languages-and-writing",
        "o2": "digital-tools",
        "o3": "project-and-process-organization",
        "o4": "hands-on-activities",
        "o5": "leadership-facilitation-management",
    },
    "laa_q028": {
        "o1": "communication",
        "o2": "self-organization-and-planning",
        "o3": "creative-work-and-design",
        "o4": "problem-solving",
        "o5": "teamwork",
    },
}

LAA_TAG_GROUPS = {
    "laa_q020": "digital_tools",
    "laa_q026": "interests",
    "laa_q027": "competencies",
    "laa_q028": "everyday_strengths",
}

LAA_SKILLS_LIKERT_DIMENSIONS = {
    "laa_q029": "soziale_lernorientierung",
    "laa_q030": "selbststeuerung",
    "laa_q031": "praxisorientierung",
    "laa_q032": "praxisorientierung",
    "laa_q033": "soziale_lernorientierung",
    "laa_q034": "selbststeuerung",
}

LAA_ATTITUDE_ITEM_KEYS = {
    "laa_q035": "lernfreude",
    "laa_q036": "stress_erleben",
    "laa_q037": "fehlerangst",
    "laa_q038": "selbstvertrauen",
    "laa_q039": "ablenkbarkeit",
    "laa_q040": "stolz_auf_wissen",
    "laa_q041": "aufgabe_neigung",
    "laa_q042": "aeusserer_druckbedarf",
}

LAA_INSIGHT_TEMPLATES = {
    "zielklarheit": "You have clear learning goals and benefit from visible milestones.",
    "zeitdruck": "Pace matters for you; short learning cycles help you stay engaged.",
    "strukturbedarf": "You benefit from clear structure, checkpoints, and guidance.",
    "feedbackbedarf": "Regular feedback strongly supports your learning progress.",
    "selbststeuerung": "You tend to learn self-directed and value decision autonomy.",
    "soziale_lernorientierung": "Exchange with others is a strong learning amplifier for you.",
    "emotionale_sicherheit": "A stable and encouraging environment noticeably improves your learning quality.",
    "frustrationsanfaelligkeit": "Overload or missing progress can quickly reduce your motivation.",
    "technikaffinitaet": "Digital formats and tools align well with your learning profile.",
    "praxisorientierung": "You learn especially well through practice, application, and concrete tasks.",
    "sichtbarkeitsmotivation": "Visible progress and recognition can strongly motivate you.",
}


def score_attempt(definitions: dict[str, dict[str, Any]], answers_by_type: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "LAA": _score_laa(definitions.get("LAA") or {}, answers_by_type.get("LAA") or {}),
        "MOA": _score_moa(definitions.get("MOA") or {}, answers_by_type.get("MOA") or {}),
        "LTA": _score_lta(definitions.get("LTA") or {}, answers_by_type.get("LTA") or {}),
    }


def _score_laa(definition: dict[str, Any], answers: dict[str, Any]) -> dict[str, Any]:
    section_profiles: dict[str, dict[str, Any]] = {}
    section_titles: dict[str, str] = {}
    section_dimension_max = _build_laa_dimension_max(definition)
    section_overview: dict[str, float] = {}

    for section in definition.get("sections", []):
        section_id = str(section.get("id") or "")
        section_title = str(section.get("title") or section_id)
        section_titles[section_id] = section_title
        dimension_raw: dict[str, float] = defaultdict(float)
        profile_tags: dict[str, list[str]] = {}
        emotional_items: dict[str, dict[str, Any]] = {}
        skill_items: dict[str, dict[str, Any]] = {}

        for question in section.get("questions", []):
            qid = str(question.get("id") or "")
            qtype = str(question.get("type") or "")
            question_text = str(question.get("text") or "")
            raw_value = answers.get(qid)
            selected_values = _extract_selected_values(raw_value)
            other_text = _extract_other_text(raw_value)

            if qtype == "single_choice":
                if not selected_values:
                    continue
                selected = selected_values[0]
                for dimension, points in (LAA_SINGLE_CHOICE_DIMENSION_MAP.get(qid, {}).get(selected, {})).items():
                    dimension_raw[dimension] += float(points)

                tag_group = LAA_TAG_GROUPS.get(qid)
                tag_value = (LAA_MULTI_TAG_MAP.get(qid, {}).get(selected) or "").strip()
                if tag_group and tag_value:
                    profile_tags.setdefault(tag_group, []).append(tag_value)
                if selected and other_text and _is_other_option(question, selected):
                    profile_tags.setdefault("custom_inputs", []).append(other_text)

            elif qtype == "multi_choice":
                tag_group = LAA_TAG_GROUPS.get(qid)
                for selected in selected_values:
                    tag_value = (LAA_MULTI_TAG_MAP.get(qid, {}).get(selected) or "").strip()
                    if tag_group and tag_value:
                        profile_tags.setdefault(tag_group, []).append(tag_value)
                if other_text:
                    profile_tags.setdefault("custom_inputs", []).append(other_text)

            elif qtype == "likert":
                numeric = _extract_likert_value(raw_value, question)
                if numeric is None:
                    continue
                normalized_item = ((numeric - 1.0) / 4.0) * 100.0
                if section_id == "attitude":
                    item_key = LAA_ATTITUDE_ITEM_KEYS.get(qid, qid)
                    emotional_items[item_key] = {
                        "question_id": qid,
                        "label": question_text,
                        "value": numeric,
                        "normalized_0_100": round(normalized_item, 2),
                    }
                elif section_id == "skills_interests":
                    item_key = qid
                    skill_items[item_key] = {
                        "question_id": qid,
                        "label": question_text,
                        "value": numeric,
                        "normalized_0_100": round(normalized_item, 2),
                    }
                    mapped_dimension = LAA_SKILLS_LIKERT_DIMENSIONS.get(qid)
                    if mapped_dimension:
                        dimension_raw[mapped_dimension] += round(normalized_item / 100.0, 4)

        dimension_normalized: dict[str, float] = {}
        for dimension, raw_points in dimension_raw.items():
            max_points = float(section_dimension_max.get(section_id, {}).get(dimension, 0.0))
            if max_points <= 0:
                dimension_normalized[dimension] = 0.0
            else:
                dimension_normalized[dimension] = round(max(0.0, min(100.0, (raw_points / max_points) * 100.0)), 2)

        summary_indices = _build_laa_summary_indices(section_id, emotional_items)
        insights = _build_laa_section_insights(
            section_id=section_id,
            dimensions_normalized=dimension_normalized,
            tags=profile_tags,
            emotional_items=emotional_items,
            summary_indices=summary_indices,
        )

        section_profiles[section_id] = {
            "section_id": section_id,
            "section_title": section_title,
            "dimensions_raw": {key: round(value, 4) for key, value in dimension_raw.items()},
            "dimensions_normalized_0_100": dimension_normalized,
            "profile_tags": {key: sorted(set(values)) for key, values in profile_tags.items()},
            "emotional_items": emotional_items,
            "skill_self_assessment_items": skill_items,
            "summary_indices_0_100": summary_indices,
            "insights": insights,
        }

        if dimension_normalized:
            section_overview[section_id] = round(sum(dimension_normalized.values()) / (100.0 * len(dimension_normalized)), 4)
        elif summary_indices:
            section_overview[section_id] = round(sum(summary_indices.values()) / (100.0 * len(summary_indices)), 4)
        elif skill_items:
            section_overview[section_id] = round(
                sum(item["normalized_0_100"] for item in skill_items.values()) / (100.0 * len(skill_items)),
                4,
            )
        else:
            section_overview[section_id] = 0.0

    dominant = [item[0] for item in sorted(section_overview.items(), key=lambda item: item[1], reverse=True)[:3]]
    personalization_hints = _build_laa_personalization_hints(section_profiles)
    return {
        "raw_scores": section_overview,
        "normalized": section_overview,
        "dominant_traits": dominant,
        "section_profiles": section_profiles,
        "dimensions_catalog": LAA_DIMENSIONS,
        "personalization_hints": personalization_hints,
        "assumptions": definition.get("assumptions", []),
    }


def _build_laa_dimension_max(definition: dict[str, Any]) -> dict[str, dict[str, float]]:
    max_scores: dict[str, dict[str, float]] = {}
    for section in definition.get("sections", []):
        section_id = str(section.get("id") or "")
        section_max: dict[str, float] = defaultdict(float)
        for question in section.get("questions", []):
            qid = str(question.get("id") or "")
            option_map = LAA_SINGLE_CHOICE_DIMENSION_MAP.get(qid, {})
            if not option_map:
                continue
            per_question_max: dict[str, float] = defaultdict(float)
            for option_dimensions in option_map.values():
                for dimension, points in option_dimensions.items():
                    per_question_max[dimension] = max(per_question_max[dimension], float(points))
            for dimension, points in per_question_max.items():
                section_max[dimension] += float(points)
        max_scores[section_id] = dict(section_max)
    return max_scores


def _build_laa_summary_indices(section_id: str, emotional_items: dict[str, dict[str, Any]]) -> dict[str, float]:
    if section_id != "attitude" or not emotional_items:
        return {}

    def direct(key: str) -> float:
        item = emotional_items.get(key)
        if not item:
            return 0.0
        return float(item.get("normalized_0_100") or 0.0)

    def reverse(key: str) -> float:
        return 100.0 - direct(key)

    lernsicherheit = _avg(
        [
            reverse("stress_erleben"),
            reverse("fehlerangst"),
            reverse("ablenkbarkeit"),
            reverse("aufgabe_neigung"),
            direct("selbstvertrauen"),
        ]
    )
    selbstvertrauen = _avg(
        [
            direct("selbstvertrauen"),
            direct("stolz_auf_wissen"),
            reverse("fehlerangst"),
        ]
    )
    aeusserer_aktivierungsbedarf = _avg(
        [
            direct("aeusserer_druckbedarf"),
            direct("aufgabe_neigung"),
        ]
    )
    return {
        "lernsicherheit": round(lernsicherheit, 2),
        "selbstvertrauen": round(selbstvertrauen, 2),
        "aeusserer_aktivierungsbedarf": round(aeusserer_aktivierungsbedarf, 2),
    }


def _build_laa_section_insights(
    *,
    section_id: str,
    dimensions_normalized: dict[str, float],
    tags: dict[str, list[str]],
    emotional_items: dict[str, dict[str, Any]],
    summary_indices: dict[str, float],
) -> list[str]:
    insights: list[str] = []

    ranked_dimensions = sorted(dimensions_normalized.items(), key=lambda item: item[1], reverse=True)
    for dimension, value in ranked_dimensions:
        if value < 55:
            continue
        template = LAA_INSIGHT_TEMPLATES.get(dimension)
        if template:
            insights.append(template)
        if len(insights) >= 2:
            break

    if section_id == "skills_interests":
        interests = tags.get("interests", [])
        if interests:
            insights.append(f"Your strongest interest areas are: {', '.join(_humanize_tags(interests[:3]))}.")
        competencies = tags.get("everyday_strengths", [])
        if competencies:
            insights.append(
                f"In everyday life, you mostly rely on: {', '.join(_humanize_tags(competencies[:3]))}."
            )

    if section_id == "attitude" and summary_indices:
        if summary_indices.get("lernsicherheit", 0) >= 60:
            insights.append("Your emotional learning stability is strong and supports consistency.")
        else:
            insights.append("Your emotional learning stability is more variable; structure and relief strategies help.")
        if summary_indices.get("aeusserer_aktivierungsbedarf", 0) >= 60:
            insights.append("External activation (reminders, fixed nudges) can significantly improve your learning rhythm.")

    if section_id == "support_needs":
        if dimensions_normalized.get("strukturbedarf", 0) >= 60:
            insights.append("You benefit from clear learning plans with small, reachable milestones.")
        if dimensions_normalized.get("feedbackbedarf", 0) >= 60:
            insights.append("Frequent feedback is a central motivational factor for you.")

    if section_id == "miscellaneous":
        if dimensions_normalized.get("selbststeuerung", 0) >= 60:
            insights.append("You prefer flexibility and want to steer your own learning path.")
        if dimensions_normalized.get("sichtbarkeitsmotivation", 0) >= 60:
            insights.append("Visible progress (for example levels, badges, milestones) can further motivate you.")

    if not insights:
        insights.append("Your profile shows a balanced pattern in this area.")

    unique: list[str] = []
    for statement in insights:
        cleaned = statement.strip()
        if not cleaned or cleaned in unique:
            continue
        unique.append(cleaned)
        if len(unique) >= 4:
            break
    if len(unique) < 2:
        unique.append("These section signals can be used for adaptive learning support.")
    return unique


def _build_laa_personalization_hints(section_profiles: dict[str, dict[str, Any]]) -> dict[str, Any]:
    strongest_dimensions: list[dict[str, Any]] = []
    section_hints: dict[str, list[str]] = {}

    for section_id, profile in section_profiles.items():
        dims = profile.get("dimensions_normalized_0_100") or {}
        if not isinstance(dims, dict):
            continue
        top_dims = sorted(dims.items(), key=lambda item: item[1], reverse=True)[:2]
        section_hints[section_id] = [LAA_DIMENSIONS.get(key, key) for key, _ in top_dims]
        for key, value in top_dims:
            strongest_dimensions.append(
                {"section_id": section_id, "dimension": key, "label": LAA_DIMENSIONS.get(key, key), "score_0_100": value}
            )

    strongest_dimensions.sort(key=lambda item: float(item.get("score_0_100") or 0.0), reverse=True)
    return {
        "section_top_dimensions": section_hints,
        "global_top_dimensions": strongest_dimensions[:5],
    }


def _extract_other_text(raw_value: Any) -> str:
    if not isinstance(raw_value, dict):
        return ""
    value = raw_value.get("other_text")
    return str(value).strip() if isinstance(value, str) else ""


def _is_other_option(question: dict[str, Any], selected: str) -> bool:
    for option in question.get("options") or []:
        resolved = str(option.get("value") or option.get("key") or "")
        if resolved != selected:
            continue
        return bool(option.get("allows_text"))
    return False


def _extract_likert_value(raw_value: Any, question: dict[str, Any]) -> float | None:
    selected = raw_value
    if isinstance(raw_value, dict):
        selected = raw_value.get("selected")
    if selected is None or selected == "":
        return None
    try:
        numeric = float(selected)
    except (TypeError, ValueError):
        return None
    minimum = float(question.get("min_value", 1) or 1)
    maximum = float(question.get("max_value", 5) or 5)
    return max(minimum, min(maximum, numeric))


def _humanize_tags(tags: list[str]) -> list[str]:
    return [tag.replace("-", " ") for tag in tags]


def _avg(values: list[float]) -> float:
    valid = [float(value) for value in values if value is not None]
    return sum(valid) / len(valid) if valid else 0.0


def _score_moa(definition: dict[str, Any], answers: dict[str, Any]) -> dict[str, Any]:
    dimensions: dict[str, float] = {}
    sections = definition.get("sections", [])
    questions = sections[0].get("questions", []) if sections else []
    for question in questions:
        qid = str(question.get("id"))
        scoring = question.get("scoring", {})
        dimension = str(scoring.get("dimension", "unknown"))
        raw_answer = answers.get(qid, 0.0)
        if isinstance(raw_answer, dict):
            raw_answer = raw_answer.get("selected", 0.0)
        try:
            value = float(raw_answer)
        except (TypeError, ValueError):
            value = 0.0
        value = max(0.0, min(10.0, value))
        dimensions[dimension] = value

    normalized = {key: value / 10.0 for key, value in dimensions.items()}
    sorted_dimensions = sorted(dimensions.items(), key=lambda item: (-item[1], str(item[0]).lower()))
    top_two = [item[0] for item in sorted_dimensions[:2]]
    pair_key = " & ".join(top_two) if top_two else ""

    result_block_id = ""
    result_block_title = ""
    result_text = ""
    if len(top_two) == 2:
        selected_pair_key = _pair_key(top_two[0], top_two[1])
        block_index = definition.get("result_block_index") or {}
        block_id = str(block_index.get(selected_pair_key) or "")
        if block_id:
            for block in definition.get("result_blocks") or []:
                if str(block.get("id") or "") != block_id:
                    continue
                result_block_id = block_id
                result_block_title = str(block.get("title") or "")
                result_text = str(block.get("text") or "")
                break

        if not result_text:
            result_block_title = f"{top_two[0]} & {top_two[1]}"
            result_text = (
                f"Your strongest motivations are {top_two[0]} and {top_two[1]}. "
                "Learning formats should prioritize this combination."
            )

    return {
        "raw_scores": dimensions,
        "normalized": normalized,
        "dominant_traits": top_two,
        "pair_key": pair_key,
        "computed_profile": {
            "sorted_dimensions": [{"dimension": name, "score": score} for name, score in sorted_dimensions],
            "top_pair": top_two,
        },
        "selected_result_block_id": result_block_id,
        "selected_result_block_title": result_block_title,
        "result_text": result_text,
    }


def _score_lta(definition: dict[str, Any], answers: dict[str, Any]) -> dict[str, Any]:
    channel_order = ["auditiv", "visuell", "kinaesthetisch", "lesen_schreiben"]
    dimensions = {key: 0.0 for key in channel_order}
    total = 0.0
    sections = definition.get("sections", [])
    questions = sections[0].get("questions", []) if sections else []
    for question in questions:
        qid = str(question.get("id"))
        selected = answers.get(qid)
        if isinstance(selected, dict):
            selected = selected.get("selected")
        if selected is None:
            continue
        selected_channel = ""
        for option in question.get("options", []):
            if str(option.get("value")) != str(selected):
                continue
            scoring = option.get("scoring", {})
            for dimension, value in scoring.items():
                selected_channel = str(dimension)
                dimensions[selected_channel] = float(dimensions.get(selected_channel, 0.0)) + float(value)
                total += float(value)
            break
        if not selected_channel:
            fallback = _map_lta_option_to_channel(str(selected))
            if fallback:
                dimensions[fallback] = float(dimensions.get(fallback, 0.0)) + 1.0
                total += 1.0

    normalized = {key: (value / total if total else 0.0) for key, value in dimensions.items()}
    percentages_0_100 = {key: round(value * 100.0, 2) for key, value in normalized.items()}
    sorted_channels = sorted(
        dimensions.items(),
        key=lambda item: (-item[1], channel_order.index(item[0]) if item[0] in channel_order else 99),
    )
    top_channel = sorted_channels[0][0] if sorted_channels else ""
    top_value = float(sorted_channels[0][1]) if sorted_channels else 0.0
    second_value = float(sorted_channels[1][1]) if len(sorted_channels) > 1 else 0.0
    max_value = top_value
    min_value = float(sorted_channels[-1][1]) if sorted_channels else 0.0

    # Classification rules:
    # - balanced: all channel counts within 1 point (max-min <= 1)
    # - dominant: top channel leads second by at least 2 points
    # - mixed: otherwise top two channels are the primary mixed profile
    if total <= 0:
        classification = "balanced"
        profile_label = "Balanced profile"
        dominant = []
    elif (max_value - min_value) <= 1.0:
        classification = "balanced"
        profile_label = "Balanced profile"
        dominant = []
    elif (top_value - second_value) >= 2.0:
        classification = "dominant"
        profile_label = top_channel
        dominant = [top_channel]
    else:
        classification = "mixed"
        top_two = [item[0] for item in sorted_channels[:2]]
        profile_label = " + ".join(top_two)
        dominant = top_two

    summary_text = _build_lta_summary_text(
        classification=classification,
        sorted_channels=sorted_channels,
    )

    result_block_id = ""
    result_block_title = ""
    result_text = ""
    result_lookup_key = ""
    if classification == "dominant" and dominant:
        result_lookup_key = f"dominant:{dominant[0]}"
    elif classification == "mixed" and len(dominant) >= 2:
        result_lookup_key = f"mixed:{_pair_key(dominant[0], dominant[1])}"
    elif classification == "balanced":
        result_lookup_key = "balanced"

    result_index = definition.get("result_block_index")
    if isinstance(result_index, dict) and result_lookup_key:
        matched_block_id = result_index.get(result_lookup_key)
        if matched_block_id:
            for block in definition.get("result_blocks") or []:
                if str(block.get("id")) != str(matched_block_id):
                    continue
                result_block_id = str(block.get("id") or "")
                result_block_title = str(block.get("title") or "")
                result_text = str(block.get("text") or "")
                break
    if not result_text:
        result_text = summary_text

    top_ranked_channels = [
        {
            "channel": key,
            "count": int(value),
            "percentage_0_100": percentages_0_100.get(key, 0.0),
        }
        for key, value in sorted_channels
    ]

    return {
        "raw_scores": dimensions,
        "channel_counts": {key: int(value) for key, value in dimensions.items()},
        "normalized": normalized,
        "channel_percentages_0_100": percentages_0_100,
        "total_answers": int(total),
        "top_ranked_channels": top_ranked_channels,
        "classification": classification,
        "profile_label": profile_label,
        "summary_text": summary_text,
        "selected_result_block_id": result_block_id,
        "selected_result_block_title": result_block_title,
        "result_text": result_text,
        "dominant_traits": dominant,
        "dominant_learning_type": (
            _format_lta_channel_label(dominant[0]) if len(dominant) == 1
            else " / ".join(_format_lta_channel_label(item) for item in dominant)
        ),
    }


def _extract_selected_values(raw_value: Any) -> list[str]:
    if isinstance(raw_value, dict):
        selected = raw_value.get("selected")
    else:
        selected = raw_value
    if isinstance(selected, list):
        return [str(item) for item in selected]
    if selected is None or selected == "":
        return []
    return [str(selected)]


def _pair_key(left: str, right: str) -> str:
    pair = sorted([str(left).strip().lower(), str(right).strip().lower()])
    return "__".join(pair)


def _map_lta_option_to_channel(option_value: str) -> str:
    mapping = {
        "A": "auditiv",
        "V": "visuell",
        "K": "kinaesthetisch",
        "L": "lesen_schreiben",
    }
    return mapping.get(option_value.upper(), "")


def _format_lta_channel_label(channel_key: str) -> str:
    labels = {
        "auditiv": "Auditory",
        "visuell": "Visual",
        "kinaesthetisch": "Kinesthetic",
        "lesen_schreiben": "Reading/Writing",
    }
    return labels.get(channel_key, channel_key)


def _build_lta_summary_text(*, classification: str, sorted_channels: list[tuple[str, float]]) -> str:
    if not sorted_channels:
        return "No LTA profile could be derived yet."

    top = sorted_channels[0][0]
    second = sorted_channels[1][0] if len(sorted_channels) > 1 else ""
    top_label = _format_lta_channel_label(top)
    second_label = _format_lta_channel_label(second) if second else ""

    if classification == "dominant":
        return f"Your strongest access channel is {top_label}, with {second_label} as a secondary support channel."
    if classification == "mixed":
        return (
            f"Your profile is mixed ({top_label} + {second_label}). "
            "You are likely to benefit from combining both channels consistently."
        )
    return (
        "Your profile is relatively balanced across all channels. "
        "A blended mix of visual, auditory, practical, and text-based formats should work well for you."
    )
