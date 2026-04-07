from __future__ import annotations

from typing import Any


def score_attempt(definitions: dict[str, dict[str, Any]], answers_by_type: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "LAA": _score_laa(definitions.get("LAA") or {}, answers_by_type.get("LAA") or {}),
        "MOA": _score_moa(definitions.get("MOA") or {}, answers_by_type.get("MOA") or {}),
        "LTA": _score_lta(definitions.get("LTA") or {}, answers_by_type.get("LTA") or {}),
    }


def _score_laa(definition: dict[str, Any], answers: dict[str, Any]) -> dict[str, Any]:
    section_scores: dict[str, float] = {}
    section_max: dict[str, float] = {}

    for section in definition.get("sections", []):
        section_id = str(section.get("id"))
        score = 0.0
        max_score = 0.0
        for question in section.get("questions", []):
            qid = str(question.get("id"))
            qtype = str(question.get("type"))
            raw_value = answers.get(qid)
            if raw_value is None:
                continue
            if qtype == "likert":
                try:
                    numeric = float(raw_value)
                except (TypeError, ValueError):
                    numeric = 0.0
                score += numeric
                max_score += float(question.get("max_value", 5) or 5)
            elif qtype == "multi_choice" and isinstance(raw_value, list):
                score += float(len(raw_value))
                max_score += float(max(len(question.get("options", [])), 1))
            else:
                score += 1.0
                max_score += 1.0
        section_scores[section_id] = score
        section_max[section_id] = max_score

    normalized = {
        section_id: (section_scores[section_id] / section_max[section_id] if section_max[section_id] else 0.0)
        for section_id in section_scores
    }
    dominant = [item[0] for item in sorted(normalized.items(), key=lambda item: item[1], reverse=True)[:3]]
    return {
        "raw_scores": section_scores,
        "normalized": normalized,
        "dominant_traits": dominant,
        "assumptions": definition.get("assumptions", []),
    }


def _score_moa(definition: dict[str, Any], answers: dict[str, Any]) -> dict[str, Any]:
    dimensions: dict[str, float] = {}
    sections = definition.get("sections", [])
    questions = sections[0].get("questions", []) if sections else []
    for question in questions:
        qid = str(question.get("id"))
        scoring = question.get("scoring", {})
        dimension = str(scoring.get("dimension", "unknown"))
        try:
            value = float(answers.get(qid, 0.0))
        except (TypeError, ValueError):
            value = 0.0
        value = max(0.0, min(10.0, value))
        dimensions[dimension] = value

    normalized = {key: value / 10.0 for key, value in dimensions.items()}
    sorted_dimensions = sorted(dimensions.items(), key=lambda item: item[1], reverse=True)
    top_two = [item[0] for item in sorted_dimensions[:2]]
    return {
        "raw_scores": dimensions,
        "normalized": normalized,
        "dominant_traits": top_two,
        "pair_key": " & ".join(top_two) if top_two else "",
    }


def _score_lta(definition: dict[str, Any], answers: dict[str, Any]) -> dict[str, Any]:
    dimensions = {"auditiv": 0.0, "visuell": 0.0, "kinaesthetisch": 0.0, "lesen_schreiben": 0.0}
    total = 0.0
    sections = definition.get("sections", [])
    questions = sections[0].get("questions", []) if sections else []
    for question in questions:
        qid = str(question.get("id"))
        selected = answers.get(qid)
        if selected is None:
            continue
        for option in question.get("options", []):
            if str(option.get("value")) != str(selected):
                continue
            scoring = option.get("scoring", {})
            for dimension, value in scoring.items():
                dimensions[str(dimension)] = float(dimensions.get(str(dimension), 0.0)) + float(value)
                total += float(value)
            break

    normalized = {key: (value / total if total else 0.0) for key, value in dimensions.items()}
    top_value = max(dimensions.values()) if dimensions else 0.0
    dominant = [key for key, value in dimensions.items() if value == top_value and top_value > 0]
    return {
        "raw_scores": dimensions,
        "normalized": normalized,
        "dominant_traits": dominant,
        "dominant_learning_type": dominant[0] if len(dominant) == 1 else " / ".join(dominant),
    }
