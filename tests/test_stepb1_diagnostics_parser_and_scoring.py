from __future__ import annotations

from pathlib import Path

from services.retriever.services.diagnostic_definitions import load_parsed_sources
from services.retriever.services.diagnostic_scoring import score_attempt


def test_source_parser_extracts_expected_definition_shapes() -> None:
    parsed = {item.diagnostic_type: item for item in load_parsed_sources(Path("data/diagnostics/source"))}

    assert set(parsed) == {"LAA", "MOA", "LTA"}
    assert parsed["LAA"].version == "1.1"
    assert parsed["MOA"].version == "1.0"
    assert parsed["LTA"].version == "1.0"

    laa_count = sum(len(section["questions"]) for section in parsed["LAA"].definition["sections"])
    moa_count = sum(len(section["questions"]) for section in parsed["MOA"].definition["sections"])
    lta_count = sum(len(section["questions"]) for section in parsed["LTA"].definition["sections"])

    assert laa_count == 48
    assert moa_count == 10
    assert lta_count == 18


def test_scoring_engine_is_deterministic_for_moa_and_lta() -> None:
    definitions = {item.diagnostic_type: item.definition for item in load_parsed_sources(Path("data/diagnostics/source"))}

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
