from __future__ import annotations

import pytest

from services.retriever.services.ksa_drills import evaluate_drill_attempt, generate_drill_question_set, list_drill_topics


def test_drill_topics_and_question_generation_use_archetypes_source() -> None:
    topics = list_drill_topics()
    assert any(topic["key"] == "digital_craft" for topic in topics)
    question_set = generate_drill_question_set(selected_topic_keys=["digital_craft"])
    assert len(question_set) == 12
    assert all(item["topic_key"] == "digital_craft" for item in question_set)
    assert {item["block_label"] for item in question_set} == {"Baseline", "The Drill", "Expansion"}


def test_drill_evaluation_updates_top_level_and_subnodes() -> None:
    question_set = generate_drill_question_set(selected_topic_keys=["digital_craft"])
    answers = {
        item["id"]: {
            "answer": f"{item['topic_name']} {item['focus_subtopic']} strong practical answer",
            "response_time_seconds": 5,
        }
        for item in question_set
    }
    base_profile = {
        "user_id": 11,
        "has_assessment": True,
        "profile_source": "assessment",
        "knowledge": {
            "stem_fundamentals": 2,
            "information_technology": 2,
            "humanities_social_sciences": 2,
            "languages_linguistics": 2,
            "business_commerce": 2,
            "legal_ethics": 2,
            "health_wellness": 2,
        },
        "skills": {
            "literacy_numeracy": 2,
            "digital_craft": 2,
            "strategic_execution": 2,
            "operational_skills": 2,
            "relational_skills": 2,
            "research_inquiry": 2,
        },
        "abilities": {
            "quantitative_reasoning": 2,
            "verbal_comprehension": 2,
            "spatial_visualization": 2,
            "executive_function": 2,
            "sensory_perceptual": 2,
            "social_emotional_capacity": 2,
            "divergent_thinking": 2,
        },
    }
    outcome = evaluate_drill_attempt(
        user_id=11,
        selected_topic_keys=["digital_craft"],
        question_set=question_set,
        answers=answers,
        base_profile_json=base_profile,
    )
    updated_profile = outcome["updated_profile_json"]
    topic_node = updated_profile["drill_state"]["topic_nodes"]["digital_craft"]
    assert updated_profile["skills"]["digital_craft"] >= 2
    assert topic_node["level"] >= 2.0
    assert len(topic_node["sub_nodes"]) >= 1
    assert outcome["result_json"]["triple_drill"]["questions_per_topic"] == 12


def test_drill_question_set_validates_selected_topic_count_and_keys() -> None:
    with pytest.raises(ValueError):
        generate_drill_question_set(selected_topic_keys=[])
    with pytest.raises(ValueError):
        generate_drill_question_set(selected_topic_keys=["digital_craft", "research_inquiry", "stem_fundamentals", "legal_ethics"])
    with pytest.raises(ValueError):
        generate_drill_question_set(selected_topic_keys=["unknown_topic"])


def test_drill_keyword_matching_accepts_case_and_punctuation_variants() -> None:
    question_set = generate_drill_question_set(selected_topic_keys=["digital_craft"])
    answers = {
        item["id"]: {
            "answer": "DIGITAL craft, full-stack DEVELOPING; workflow-focused response",
            "response_time_seconds": 4,
        }
        for item in question_set
    }
    base_profile = {
        "user_id": 11,
        "has_assessment": True,
        "profile_source": "assessment",
        "knowledge": {},
        "skills": {"digital_craft": 2},
        "abilities": {},
    }
    outcome = evaluate_drill_attempt(
        user_id=11,
        selected_topic_keys=["digital_craft"],
        question_set=question_set,
        answers=answers,
        base_profile_json=base_profile,
    )
    node = outcome["updated_profile_json"]["drill_state"]["topic_nodes"]["digital_craft"]
    assert node["level"] > 2.0
