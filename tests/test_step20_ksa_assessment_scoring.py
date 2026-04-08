from __future__ import annotations

from services.retriever.services.ksa_assessment import evaluate_assessment, get_assessment_definition


def test_assessment_definition_does_not_expose_correct_answers() -> None:
    definition = get_assessment_definition()
    assert definition["knowledge_questions"]
    assert all("correct" not in item for item in definition["knowledge_questions"])


def test_evaluate_assessment_applies_sieve_and_scoring_rules() -> None:
    answers = {
        "phase1": {
            "stem_it": 8,
            "humanities": 2,
            "business_legal": 2,
            "health": 2,
            "digital_ops": 7,
            "people_strat": 2,
            "research": 2,
        },
        "knowledge": {
            "K.1a": "100°C",
            "K.1b": "Entropy increases",
            "K.2a": "Identify a device on a network",
            "K.2b": "Model too simple",  # hard failed
        },
        "skills": {
            "S.1": "B",
            "S.2": "A",
        },
        "abilities": {
            "A.1": {"answer": "$27", "response_time_seconds": 5},
            "A.2": {"answer": "Light", "response_time_seconds": 7},
            "A.3": {"answer": "Yes", "response_time_seconds": 8},
            "A.4": {"answer": "98", "response_time_seconds": 4},
            "A.5": {"answer": "Mid", "response_time_seconds": 6},
            "A.6": {"answer": "Disinterested/Uncomfortable", "response_time_seconds": 6},
            "A.7": {"answer": "Pen holder, planter, paperweight", "response_time_seconds": 10},
        },
    }

    evaluation = evaluate_assessment(user_id=11, answers=answers)
    profile = evaluation.profile_json

    # Knowledge: triggered topics get verified levels via FS = S * V.
    assert profile["assessment_details"]["knowledge"]["stem_fundamentals"]["status"] == "verified"
    assert profile["assessment_details"]["knowledge"]["stem_fundamentals"]["validation_multiplier"] == 1.5
    assert profile["assessment_details"]["knowledge"]["information_technology"]["validation_multiplier"] == 1.0
    assert profile["knowledge"]["stem_fundamentals"] == 3
    assert profile["knowledge"]["information_technology"] == 3

    # Untriggered knowledge topics are explicitly uncharted.
    assert profile["assessment_details"]["knowledge"]["legal_ethics"]["status"] == "uncharted"
    assert profile["knowledge"]["legal_ethics"] == 1

    # Skills: B => level 3 (competent), A => level 1 (novice), untriggered => uncharted level 1.
    assert profile["skills"]["digital_craft"] == 3
    assert profile["skills"]["operational_skills"] == 1
    assert profile["assessment_details"]["skills"]["strategic_execution"]["status"] == "uncharted"

    # Abilities: correctness + time bonus produce display levels 1..5 and derived speed multiplier.
    assert profile["abilities"]["quantitative_reasoning"] >= 4
    assert profile["abilities"]["executive_function"] >= 4
    assert profile["assessment_details"]["derived"]["learning_speed_multiplier"] == 1.5


def test_divergent_thinking_heuristic_is_deterministic() -> None:
    answers = {
        "phase1": {
            "stem_it": 1,
            "humanities": 1,
            "business_legal": 1,
            "health": 1,
            "digital_ops": 1,
            "people_strat": 1,
            "research": 1,
        },
        "abilities": {
            "A.7": {"answer": "Pen holder, pen holder, planter", "response_time_seconds": 10},
        },
    }
    profile = evaluate_assessment(user_id=11, answers=answers).profile_json
    divergent = profile["assessment_details"]["abilities"]["divergent_thinking"]
    assert divergent["correctness"] == 0.66


def test_ability_answer_normalization_accepts_common_variants() -> None:
    answers = {
        "phase1": {
            "stem_it": 8,
            "humanities": 1,
            "business_legal": 1,
            "health": 1,
            "digital_ops": 1,
            "people_strat": 1,
            "research": 1,
        },
        "knowledge": {
            "K.1a": " 100°c ",
            "K.1b": "  entropy   increases ",
            "K.2a": "identify a device on a network",
            "K.2b": "model fits noise not general data",
        },
        "abilities": {
            "A.1": {"answer": " 27  ", "response_time_seconds": 9},
            "A.2": {"answer": "LIGHT", "response_time_seconds": 9},
            "A.3": {"answer": "  yes ", "response_time_seconds": 9},
            "A.4": {"answer": "the odd one is 98", "response_time_seconds": 9},
            "A.5": {"answer": "Middle", "response_time_seconds": 9},
            "A.6": {"answer": "Probably uncomfortable.", "response_time_seconds": 9},
            "A.7": {"answer": "Pen holder ; planter ; small tool cup", "response_time_seconds": 9},
        },
    }
    profile = evaluate_assessment(user_id=11, answers=answers).profile_json
    abilities = profile["assessment_details"]["abilities"]
    assert abilities["quantitative_reasoning"]["is_correct"] is True
    assert abilities["verbal_comprehension"]["is_correct"] is True
    assert abilities["spatial_visualization"]["is_correct"] is True
    assert abilities["executive_function"]["is_correct"] is True
    assert abilities["sensory_perceptual"]["is_correct"] is True
    assert abilities["social_emotional_capacity"]["is_correct"] is True
    assert abilities["divergent_thinking"]["correctness"] == 1.0
