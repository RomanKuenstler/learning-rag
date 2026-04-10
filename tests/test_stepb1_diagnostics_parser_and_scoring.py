from __future__ import annotations

from pathlib import Path

from services.retriever.services.diagnostic_definitions import load_parsed_sources
from services.retriever.services.diagnostic_scoring import score_attempt


def test_source_parser_extracts_expected_definition_shapes() -> None:
    parsed = {item.diagnostic_type: item for item in load_parsed_sources(Path("data/sources/alpd"))}

    assert set(parsed) == {"LAA", "MOA", "LTA"}
    assert parsed["LAA"].version == "2.0"
    assert parsed["MOA"].version == "2.0"
    assert parsed["LTA"].version == "2.0"

    laa_count = sum(len(section["questions"]) for section in parsed["LAA"].definition["sections"])
    moa_count = sum(len(section["questions"]) for section in parsed["MOA"].definition["sections"])
    lta_count = sum(len(section["questions"]) for section in parsed["LTA"].definition["sections"])

    assert laa_count == 50
    assert moa_count == 10
    assert lta_count == 20
    assert len(parsed["MOA"].definition["result_blocks"]) == 45
    assert len(parsed["LTA"].definition["result_blocks"]) >= 10


def test_scoring_engine_is_deterministic_for_moa_and_lta() -> None:
    definitions = {item.diagnostic_type: item.definition for item in load_parsed_sources(Path("data/sources/alpd"))}

    answers = {
        "LAA": {},
        "MOA": {
            "moa_q01": 10,
            "moa_q02": 4,
            "moa_q03": 2,
            "moa_q04": 3,
            "moa_q05": 1,
            "moa_q06": 5,
            "moa_q07": 6,
            "moa_q08": 7,
            "moa_q09": 0,
            "moa_q10": 9,
        },
        "LTA": {
            "lta_q01": "A",
            "lta_q02": "V",
            "lta_q03": "K",
            "lta_q04": "L",
            "lta_q05": "A",
            "lta_q06": "A",
        },
    }

    result_a = score_attempt(definitions, answers)
    result_b = score_attempt(definitions, answers)

    assert result_a == result_b
    assert len(result_a["MOA"]["dominant_traits"]) == 2
    assert result_a["LTA"]["dominant_learning_type"]
    assert result_a["MOA"]["result_text"]


def test_moa_result_block_mapping_is_dynamic() -> None:
    definitions = {item.diagnostic_type: item.definition for item in load_parsed_sources(Path("data/sources/alpd"))}

    answers = {
        "LAA": {},
        "MOA": {
            "moa_q01": 10,
            "moa_q02": 9,
            "moa_q03": 1,
            "moa_q04": 1,
            "moa_q05": 1,
            "moa_q06": 1,
            "moa_q07": 1,
            "moa_q08": 1,
            "moa_q09": 1,
            "moa_q10": 1,
        },
        "LTA": {},
    }
    result = score_attempt(definitions, answers)

    assert result["MOA"]["dominant_traits"] == ["Knowledge", "Creativity"]
    assert "understand" in result["MOA"]["result_text"].lower()


def test_laa_other_value_is_scored_when_stored_inline() -> None:
    definitions = {item.diagnostic_type: item.definition for item in load_parsed_sources(Path("data/sources/alpd"))}

    answers = {
        "LAA": {
            "laa_q001": {"selected": "o8", "other_text": "Custom reason"},
            "laa_q002": "o1",
        },
        "MOA": {},
        "LTA": {},
    }
    result = score_attempt(definitions, answers)
    assert result["LAA"]["raw_scores"]
    assert any(value > 0 for value in result["LAA"]["raw_scores"].values())


def test_laa_is_section_based_and_not_single_total() -> None:
    definitions = {item.diagnostic_type: item.definition for item in load_parsed_sources(Path("data/sources/alpd"))}
    answers = {
        "LAA": {
            "laa_q001": "o6",
            "laa_q002": "o1",
            "laa_q003": "o1",
            "laa_q011": "o1",
            "laa_q012": "o1",
            "laa_q013": "o1",
        },
        "MOA": {},
        "LTA": {},
    }
    result = score_attempt(definitions, answers)["LAA"]
    section_profiles = result["section_profiles"]

    assert "user_needs" in section_profiles
    assert "learning_experience" in section_profiles
    assert isinstance(section_profiles["user_needs"]["insights"], list)
    assert len(section_profiles["user_needs"]["insights"]) >= 2
    assert "total_score" not in result


def test_laa_dimension_mapping_and_normalization_are_deterministic() -> None:
    definitions = {item.diagnostic_type: item.definition for item in load_parsed_sources(Path("data/sources/alpd"))}
    answers = {
        "LAA": {
            "laa_q002": "o1",
            "laa_q003": "o1",
            "laa_q047": "o2",
            "laa_q045": "o1",
        },
        "MOA": {},
        "LTA": {},
    }
    result_a = score_attempt(definitions, answers)["LAA"]
    result_b = score_attempt(definitions, answers)["LAA"]

    assert result_a == result_b
    user_dims = result_a["section_profiles"]["user_needs"]["dimensions_normalized_0_100"]
    misc_dims = result_a["section_profiles"]["miscellaneous"]["dimensions_normalized_0_100"]
    support_dims = result_a["section_profiles"]["support_needs"]["dimensions_normalized_0_100"]
    assert user_dims["zeitdruck"] > 0
    assert misc_dims["strukturbedarf"] > 0
    assert support_dims["strukturbedarf"] > 0
    assert all(0 <= value <= 100 for value in user_dims.values())


def test_laa_emotional_subprofile_and_indices_are_persisted() -> None:
    definitions = {item.diagnostic_type: item.definition for item in load_parsed_sources(Path("data/sources/alpd"))}
    answers = {
        "LAA": {
            "laa_q035": "5",
            "laa_q036": "4",
            "laa_q037": "4",
            "laa_q038": "2",
            "laa_q039": "3",
            "laa_q040": "2",
            "laa_q041": "4",
            "laa_q042": "5",
        },
        "MOA": {},
        "LTA": {},
    }
    attitude = score_attempt(definitions, answers)["LAA"]["section_profiles"]["attitude"]
    assert len(attitude["emotional_items"]) == 8
    assert "lernsicherheit" in attitude["summary_indices_0_100"]
    assert "selbstvertrauen" in attitude["summary_indices_0_100"]
    assert "aeusserer_aktivierungsbedarf" in attitude["summary_indices_0_100"]


def test_laa_multi_select_sections_generate_profile_tags() -> None:
    definitions = {item.diagnostic_type: item.definition for item in load_parsed_sources(Path("data/sources/alpd"))}
    answers = {
        "LAA": {
            "laa_q026": {"selected": ["o2", "o5"], "other_text": ""},
            "laa_q027": {"selected": ["o2", "o4"], "other_text": ""},
            "laa_q028": {"selected": ["o1", "o3"], "other_text": "Community moderation"},
        },
        "MOA": {},
        "LTA": {},
    }
    profile = score_attempt(definitions, answers)["LAA"]["section_profiles"]["skills_interests"]
    tags = profile["profile_tags"]
    assert "interessen" in tags
    assert "kompetenzen" in tags
    assert "alltagskompetenzen" in tags
    assert "custom_inputs" in tags
    assert any("community moderation" in item.lower() for item in tags["custom_inputs"])


def test_lta_channel_counting_percentages_and_dominant_detection() -> None:
    definitions = {item.diagnostic_type: item.definition for item in load_parsed_sources(Path("data/sources/alpd"))}
    answers = {
        "LAA": {},
        "MOA": {},
        "LTA": {
            "lta_q01": "A",
            "lta_q02": "A",
            "lta_q03": "A",
            "lta_q04": "V",
        },
    }
    lta = score_attempt(definitions, answers)["LTA"]

    assert lta["channel_counts"]["auditiv"] == 3
    assert lta["channel_counts"]["visuell"] == 1
    assert lta["total_answers"] == 4
    assert lta["classification"] == "dominant"
    assert lta["dominant_traits"] == ["auditiv"]
    assert "strongest access channel is Auditory" in lta["summary_text"]

    percentages = lta["channel_percentages_0_100"]
    assert percentages["auditiv"] == 75.0
    assert percentages["visuell"] == 25.0
    assert round(sum(percentages.values()), 2) == 100.0


def test_lta_mixed_profile_detection_uses_top_two_channels() -> None:
    definitions = {item.diagnostic_type: item.definition for item in load_parsed_sources(Path("data/sources/alpd"))}
    answers = {
        "LAA": {},
        "MOA": {},
        "LTA": {
            "lta_q01": "V",
            "lta_q02": "V",
            "lta_q03": "K",
            "lta_q04": "K",
            "lta_q05": "A",
        },
    }
    lta = score_attempt(definitions, answers)["LTA"]

    assert lta["classification"] == "mixed"
    assert lta["dominant_traits"] == ["visuell", "kinaesthetisch"]
    assert lta["profile_label"] == "visuell + kinaesthetisch"
    assert "Your profile is mixed (Visual + Kinesthetic)." in lta["summary_text"]


def test_lta_balanced_profile_detection_when_all_channels_are_close() -> None:
    definitions = {item.diagnostic_type: item.definition for item in load_parsed_sources(Path("data/sources/alpd"))}
    answers = {
        "LAA": {},
        "MOA": {},
        "LTA": {
            "lta_q01": "A",
            "lta_q02": "V",
            "lta_q03": "K",
            "lta_q04": "L",
        },
    }
    lta = score_attempt(definitions, answers)["LTA"]

    assert lta["classification"] == "balanced"
    assert lta["dominant_traits"] == []
    assert lta["summary_text"].startswith("Your profile is relatively balanced")


def test_lta_uses_profile_text_block_from_source() -> None:
    definitions = {item.diagnostic_type: item.definition for item in load_parsed_sources(Path("data/sources/alpd"))}
    answers = {
        "LAA": {},
        "MOA": {},
        "LTA": {
            "lta_q01": "V",
            "lta_q02": "V",
            "lta_q03": "K",
            "lta_q04": "K",
            "lta_q05": "A",
        },
    }
    lta = score_attempt(definitions, answers)["LTA"]

    assert lta["classification"] == "mixed"
    assert lta["selected_result_block_id"]
    assert lta["selected_result_block_title"] == "Visual–Kinesthetic"
    assert "both see and actively apply" in lta["result_text"]
