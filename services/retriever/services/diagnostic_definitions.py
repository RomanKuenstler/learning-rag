from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path


DIAGNOSTIC_PARSERS = {
    "LAA": "_parse_laa_markdown",
    "MOA": "_parse_moa_markdown",
    "LTA": "_parse_lta_markdown",
}


@dataclass(slots=True)
class ParsedSource:
    diagnostic_type: str
    file_name: str
    file_hash: str
    version: str
    definition: dict[str, object]


def load_parsed_sources(source_dir: Path) -> list[ParsedSource]:
    if not source_dir.exists():
        return []

    result: list[ParsedSource] = []
    for path in sorted(source_dir.glob("*.md")):
        diagnostic_type = _extract_diagnostic_type(path.stem)
        if diagnostic_type is None:
            continue

        parser_name = DIAGNOSTIC_PARSERS.get(diagnostic_type)
        if not parser_name:
            continue

        raw = path.read_bytes()
        file_hash = hashlib.sha256(raw).hexdigest()
        text = raw.decode("utf-8", errors="replace")
        metadata, body = _extract_markdown_metadata(text)
        version = _extract_version(path.stem, metadata)

        parser = globals()[parser_name]
        definition = parser(body, version, metadata)

        question_count = sum(len(section.get("questions") or []) for section in list(definition.get("sections") or []))
        if question_count == 0:
            continue

        result.append(
            ParsedSource(
                diagnostic_type=diagnostic_type,
                file_name=path.name,
                file_hash=file_hash,
                version=version,
                definition=definition,
            )
        )
    return result


def _extract_diagnostic_type(stem: str) -> str | None:
    match = re.match(r"^([a-zA-Z]{3})v\d+$", stem.strip())
    if not match:
        return None
    value = match.group(1).upper()
    if value in DIAGNOSTIC_PARSERS:
        return value
    return None


def _extract_markdown_metadata(text: str) -> tuple[dict[str, object], str]:
    if not text.startswith("---\n"):
        return {}, text

    lines = text.splitlines()
    closing_index = -1
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            closing_index = index
            break
    if closing_index < 0:
        return {}, text

    metadata: dict[str, object] = {}
    for raw in lines[1:closing_index]:
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        metadata[key] = value

    body = "\n".join(lines[closing_index + 1 :])
    return metadata, body


def _extract_version(stem: str, metadata: dict[str, object]) -> str:
    metadata_version = str(metadata.get("version") or "").strip()
    if metadata_version:
        return metadata_version
    match = re.search(r"v(\d+)$", stem, flags=re.IGNORECASE)
    if match:
        return f"{int(match.group(1))}.0"
    return "1.0"


def _clean_markdown_lines(text: str) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        cleaned = line.replace("\xa0", " ").strip()
        if not cleaned:
            continue
        lines.append(cleaned)
    return lines


def _is_separator(line: str) -> bool:
    compact = line.strip()
    if compact in {"⸻", "---", "___"}:
        return True
    if re.fullmatch(r"[-_]{3,}", compact):
        return True
    return False


def _normalize_text(value: str) -> str:
    ascii_only = unicodedata.normalize("NFD", value.lower()).encode("ascii", "ignore").decode("ascii")
    ascii_only = ascii_only.replace("&", " and ")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", ascii_only)).strip()


def _slug(value: str) -> str:
    text = _normalize_text(value)
    return re.sub(r"\s+", "_", text).strip("_")


def _extract_checkbox_option(line: str) -> str | None:
    match = re.match(r"^[•\-*]\s*\(\s*\)\s*(.+)$", line)
    if not match:
        return None
    return match.group(1).strip()


def _extract_bullet_text(line: str) -> str | None:
    match = re.match(r"^[•\-*]\s*(.+)$", line)
    if not match:
        return None
    return match.group(1).strip()


def _normalize_option_label(label: str) -> tuple[str, bool]:
    cleaned = re.sub(r"\s*_+\s*$", "", label).strip()
    if re.match(r"^other\s*:", cleaned, flags=re.IGNORECASE):
        return "Other:", True
    return cleaned, False


def _likert_1_to_5() -> list[dict[str, object]]:
    return [
        {"key": str(value), "label": str(value), "value": str(value), "allows_text": False}
        for value in range(1, 6)
    ]


def _parse_laa_markdown(text: str, version: str, metadata: dict[str, object]) -> dict[str, object]:
    ordered_sections = [
        ("user_needs", "User needs"),
        ("learning_experience", "Learning experience"),
        ("conditions", "Conditions"),
        ("objectives", "Objectives"),
        ("skills_interests", "Skills and Interests"),
        ("attitude", "Attitude"),
        ("support_needs", "Support needs"),
        ("miscellaneous", "Miscellaneous"),
    ]
    section_lookup = {key: {"id": key, "title": title, "questions": []} for key, title in ordered_sections}

    section_aliases = {
        "user needs": "user_needs",
        "learning experience and self perception": "learning_experience",
        "time and learning conditions": "conditions",
        "learning goals and motivation": "objectives",
        "skills and interests": "skills_interests",
        "interests": "skills_interests",
        "competencies skills self assessment": "skills_interests",
        "soft skills self assessment via scale": "skills_interests",
        "emotional attitude toward learning": "attitude",
        "learning barriers and support needs": "support_needs",
        "additional personalization": "miscellaneous",
    }

    lines = _clean_markdown_lines(text)
    current_section = "user_needs"
    current_question: dict[str, object] | None = None
    question_counter = 0
    pending_multi_choice = False
    in_soft_skills = False
    in_emotional_attitude = False

    def start_question(question_text: str, question_type: str) -> dict[str, object]:
        nonlocal question_counter, current_question
        question_counter += 1
        current_question = {
            "id": f"laa_q{question_counter:03d}",
            "text": question_text.strip(),
            "type": question_type,
            "options": [],
            "scoring": {"method": "derived_section_weight"},
        }
        section_lookup[current_section]["questions"].append(current_question)
        return current_question

    for line in lines:
        if _is_separator(line):
            continue
        if line.lower().startswith("learning style analysis"):
            continue

        normalized_line = _normalize_text(line)
        if normalized_line in section_aliases:
            current_section = section_aliases[normalized_line]
            current_question = None
            pending_multi_choice = False
            in_soft_skills = normalized_line == "soft skills self assessment via scale"
            in_emotional_attitude = normalized_line == "emotional attitude toward learning"
            continue

        if normalized_line.startswith("please rate yourself on a scale"):
            in_soft_skills = True
            in_emotional_attitude = False
            continue

        if normalized_line.startswith("please rate the following statements"):
            in_soft_skills = False
            in_emotional_attitude = True
            continue

        if "multiple answers possible" in normalized_line:
            pending_multi_choice = True
            continue

        checkbox_option = _extract_checkbox_option(line)
        if checkbox_option is not None:
            if current_question is None:
                current_question = start_question("Selection", "multi_choice" if pending_multi_choice else "single_choice")
            label, allows_text = _normalize_option_label(checkbox_option)
            current_question["options"].append(
                {
                    "key": f"o{len(current_question['options']) + 1}",
                    "label": label,
                    "value": f"o{len(current_question['options']) + 1}",
                    "allows_text": allows_text,
                }
            )
            continue

        bullet_text = _extract_bullet_text(line)
        if in_soft_skills and bullet_text is not None and "( )" not in line:
            question = start_question(bullet_text, "likert")
            question["min_value"] = 1
            question["max_value"] = 5
            question["options"] = _likert_1_to_5()
            continue

        numbered_match = re.match(r"^(\d+)\.\s*(.+)$", line)
        if in_emotional_attitude and numbered_match:
            question = start_question(numbered_match.group(2).strip(), "likert")
            question["min_value"] = 1
            question["max_value"] = 5
            question["options"] = _likert_1_to_5()
            continue

        if numbered_match:
            question_text = numbered_match.group(2).strip()
            question_text = re.sub(r"\(Multiple answers possible\)", "", question_text, flags=re.IGNORECASE).strip()
            qtype = "multi_choice" if pending_multi_choice else "single_choice"
            start_question(question_text, qtype)
            pending_multi_choice = False
            continue

        if line.endswith("?") and "( )" not in line:
            qtype = "multi_choice" if pending_multi_choice else "single_choice"
            start_question(line, qtype)
            pending_multi_choice = False
            continue

        if current_question and current_question.get("options"):
            options = list(current_question["options"])
            last_option = dict(options[-1])
            last_option["label"] = f"{last_option.get('label', '')} {line}".strip()
            options[-1] = last_option
            current_question["options"] = options

    sections = [section_lookup[key] for key, _title in ordered_sections if section_lookup[key]["questions"]]
    scoring_rules = {
        "method": "section_aggregation",
        "normalization": "section_score/max_section_score",
        "dominant_count": 3,
    }

    return {
        "id": "diagnostic-laa",
        "type": "LAA",
        "title": "Learning Style Analysis (LAA)",
        "version": version,
        "sections": sections,
        "metadata": metadata,
        "scoring_rules": scoring_rules,
        "assumptions": [
            "Likert items (1-5) use numeric values directly.",
            "For choice questions, each selected option contributes +1 to the section score.",
        ],
    }


def _canonical_moa_dimension(raw: str) -> str:
    normalized = _normalize_text(raw)
    aliases = {
        "knowledge insight": "Knowledge",
        "creativity expression": "Creativity",
        "influence impact": "Influence",
        "purpose contribution": "Purpose",
        "relationships connection": "Connection",
        "structure security": "Security",
        "achievement skill development": "Achievement",
        "autonomy self direction": "Autonomy",
        "status recognition": "Status",
        "experimentation freedom of action": "Experimentation",
    }
    if normalized in aliases:
        return aliases[normalized]
    for key, value in aliases.items():
        if normalized.startswith(key):
            return value
    return raw.strip()


def _result_pair_key(left: str, right: str) -> str:
    pair = sorted([left.strip().lower(), right.strip().lower()])
    return "__".join(pair)


def _parse_moa_markdown(text: str, version: str, metadata: dict[str, object]) -> dict[str, object]:
    lines = _clean_markdown_lines(text)

    statements: list[dict[str, str]] = []
    in_question_block = False
    pending_statement = ""
    for line in lines:
        if _is_separator(line):
            continue
        normalized = _normalize_text(line)
        if "what motivates you when learning" in normalized:
            in_question_block = True
            continue
        if in_question_block and normalized.startswith("evaluation and impact"):
            in_question_block = False
            continue
        if not in_question_block:
            continue

        bullet_text = _extract_bullet_text(line)
        if bullet_text and not bullet_text.startswith("(Motivation:"):
            pending_statement = bullet_text
            continue

        motivation_match = re.match(r"^\(Motivation\s*:\s*(.+)\)$", line, flags=re.IGNORECASE)
        if motivation_match and pending_statement:
            statements.append({
                "text": pending_statement,
                "dimension": _canonical_moa_dimension(motivation_match.group(1).strip()),
            })
            pending_statement = ""

    questions: list[dict[str, object]] = []
    dimensions: list[str] = []
    for index, item in enumerate(statements, start=1):
        dimension = item["dimension"]
        dimensions.append(dimension)
        questions.append(
            {
                "id": f"moa_q{index:02d}",
                "text": item["text"],
                "type": "slider",
                "min_value": 0,
                "max_value": 10,
                "options": [],
                "scoring": {"dimension": dimension, "method": "direct_slider"},
            }
        )

    result_blocks: list[dict[str, object]] = []
    result_index: dict[str, str] = {}
    current_block: dict[str, object] | None = None

    for line in lines:
        if _is_separator(line):
            continue
        heading_match = re.match(r"^(\d+)\.\s*(.+?)\s*&\s*(.+)$", line)
        if heading_match:
            if current_block:
                current_block["text"] = "\n\n".join(current_block.pop("body_lines", []))
                result_blocks.append(current_block)
                pair_key = str(current_block.get("pair_key") or "")
                if pair_key and pair_key not in result_index:
                    result_index[pair_key] = str(current_block.get("id") or "")

            left = _canonical_moa_dimension(heading_match.group(2).strip())
            right = _canonical_moa_dimension(heading_match.group(3).strip())
            current_block = {
                "id": f"moa_result_{int(heading_match.group(1)):02d}_{_slug(left)}_{_slug(right)}",
                "title": f"{left} & {right}",
                "left": left,
                "right": right,
                "pair_key": _result_pair_key(left, right),
                "body_lines": [],
            }
            continue

        if current_block is not None:
            current_block.setdefault("body_lines", [])
            current_block["body_lines"].append(line)

    if current_block:
        current_block["text"] = "\n\n".join(current_block.pop("body_lines", []))
        result_blocks.append(current_block)
        pair_key = str(current_block.get("pair_key") or "")
        if pair_key and pair_key not in result_index:
            result_index[pair_key] = str(current_block.get("id") or "")

    scoring_rules = {
        "dimensions": list(dict.fromkeys(dimensions)),
        "dominant_count": 2,
        "normalization": "value/10",
        "combination_interpretation": "top_2_pair",
    }

    return {
        "id": "diagnostic-moa",
        "type": "MOA",
        "title": "Motivation Analysis (MOA)",
        "version": version,
        "sections": [{"id": "motivation", "title": "Motivation", "questions": questions}],
        "metadata": metadata,
        "scoring_rules": scoring_rules,
        "result_blocks": result_blocks,
        "result_block_index": result_index,
        "assumptions": [],
    }


def _parse_lta_markdown(text: str, version: str, metadata: dict[str, object]) -> dict[str, object]:
    lines = _clean_markdown_lines(text)
    option_to_dimension = {
        "A": "auditiv",
        "V": "visuell",
        "K": "kinaesthetisch",
        "L": "lesen_schreiben",
    }

    questions: list[dict[str, object]] = []
    current_question: dict[str, object] | None = None
    question_counter = 0

    in_result_block = False
    for line in lines:
        if _is_separator(line):
            continue
        if line.lower().startswith("learning type analysis"):
            continue
        if line.lower().startswith("resulting text samples"):
            in_result_block = True
            current_question = None
            continue
        if in_result_block:
            continue
        if line.lower().startswith("additional questions for profile refinement"):
            current_question = None
            continue

        option_match = re.match(r"^[•\-*]\s*([AVKL])(?:\s*\([^)]+\))?\s*:\s*(.+)$", line, flags=re.IGNORECASE)
        if option_match and current_question is not None:
            key = option_match.group(1).upper()
            label = option_match.group(2).strip()
            current_question["options"].append(
                {
                    "key": key,
                    "label": label,
                    "value": key,
                    "allows_text": False,
                    "scoring": {option_to_dimension[key]: 1},
                }
            )
            continue

        if line.endswith("?"):
            question_counter += 1
            current_question = {
                "id": f"lta_q{question_counter:02d}",
                "text": line,
                "type": "single_choice",
                "options": [],
                "scoring": {"method": "option_weight"},
            }
            questions.append(current_question)
            continue

        if current_question and current_question.get("options"):
            options = list(current_question["options"])
            tail = dict(options[-1])
            tail["label"] = f"{tail.get('label', '')} {line}".strip()
            options[-1] = tail
            current_question["options"] = options

    result_blocks, result_index = _parse_lta_result_blocks(lines)

    scoring_rules = {
        "dimensions": ["auditiv", "visuell", "kinaesthetisch", "lesen_schreiben"],
        "normalization": "dimension_count/total_answers",
        "dominant_count": 1,
        "ties": "return_all",
    }

    return {
        "id": "diagnostic-lta",
        "type": "LTA",
        "title": "Learning Type Analysis (LTA)",
        "version": version,
        "sections": [{"id": "learning_type", "title": "Learning Type", "questions": questions}],
        "metadata": metadata,
        "scoring_rules": scoring_rules,
        "result_blocks": result_blocks,
        "result_block_index": result_index,
        "assumptions": [],
    }


def _parse_lta_result_blocks(lines: list[str]) -> tuple[list[dict[str, object]], dict[str, str]]:
    result_blocks: list[dict[str, object]] = []
    result_index: dict[str, str] = {}
    in_result_block = False
    current_block: dict[str, object] | None = None

    def flush_current() -> None:
        nonlocal current_block
        if not current_block:
            return
        text = "\n\n".join(current_block.pop("body_lines", []))
        current_block["text"] = text.strip()
        result_blocks.append(current_block)
        lookup_key = str(current_block.get("lookup_key") or "")
        if lookup_key and lookup_key not in result_index:
            result_index[lookup_key] = str(current_block.get("id") or "")
        current_block = None

    for line in lines:
        if line.lower().startswith("resulting text samples"):
            in_result_block = True
            continue
        if not in_result_block:
            continue
        if _is_separator(line):
            continue

        normalized = _normalize_text(line)
        if normalized in {
            "1 dominant types",
            "2 mixed types pairs",
            "3 balanced profile",
            "dominant types",
            "mixed types pairs",
            "balanced profile",
        }:
            continue

        dominant_channel = _lta_channel_from_heading(line)
        if dominant_channel:
            flush_current()
            label = _format_lta_channel_label(dominant_channel)
            current_block = {
                "id": f"lta_result_dominant_{dominant_channel}",
                "title": label,
                "classification": "dominant",
                "lookup_key": f"dominant:{dominant_channel}",
                "body_lines": [],
            }
            continue

        pair = _lta_pair_from_heading(line)
        if pair:
            flush_current()
            left, right = pair
            left_label = _format_lta_channel_label(left)
            right_label = _format_lta_channel_label(right)
            current_block = {
                "id": f"lta_result_mixed_{left}_{right}",
                "title": f"{left_label}–{right_label}",
                "classification": "mixed",
                "lookup_key": f"mixed:{_result_pair_key(left, right)}",
                "left": left,
                "right": right,
                "body_lines": [],
            }
            continue

        if normalized == "balanced":
            flush_current()
            current_block = {
                "id": "lta_result_balanced",
                "title": "Balanced",
                "classification": "balanced",
                "lookup_key": "balanced",
                "body_lines": [],
            }
            continue

        if current_block is not None:
            current_block.setdefault("body_lines", [])
            current_block["body_lines"].append(line)

    flush_current()
    return result_blocks, result_index


def _lta_channel_from_heading(raw: str) -> str:
    compact = raw.strip()
    if not compact:
        return ""
    compact = re.sub(r"\s*\([A-Z]\)\s*$", "", compact, flags=re.IGNORECASE).strip()
    normalized = _normalize_text(compact)
    mapping = {
        "auditory": "auditiv",
        "visual": "visuell",
        "kinesthetic": "kinaesthetisch",
        "reading writing": "lesen_schreiben",
        "reading and writing": "lesen_schreiben",
    }
    return mapping.get(normalized, "")


def _lta_pair_from_heading(raw: str) -> tuple[str, str] | None:
    compact = raw.strip()
    if "–" in compact:
        parts = [item.strip() for item in compact.split("–", 1)]
    elif "-" in compact:
        parts = [item.strip() for item in compact.split("-", 1)]
    else:
        return None
    if len(parts) != 2:
        return None
    left = _lta_channel_from_heading(parts[0])
    right = _lta_channel_from_heading(parts[1])
    if not left or not right or left == right:
        return None
    return left, right


def _format_lta_channel_label(channel_key: str) -> str:
    labels = {
        "auditiv": "Auditory",
        "visuell": "Visual",
        "kinaesthetisch": "Kinesthetic",
        "lesen_schreiben": "Reading/Writing",
    }
    return labels.get(channel_key, channel_key)
