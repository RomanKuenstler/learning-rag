from __future__ import annotations

import hashlib
import re
import subprocess
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from zipfile import ZipFile
import xml.etree.ElementTree as ET


SOURCE_FILES = {
    "LAA": ["LAA.pdf", "LAA.txt", "LAA.pages", "MythriQ-LAA-Lernartanalyse-20250703a.docx"],
    "MOA": ["MOA.pdf", "MOA.txt", "MOA.pages", "MythriQ-MOA-Motivationsanalyse-20250703a.docx"],
    "LTA": ["LTA.pdf", "LTA.txt", "LTA.pages", "MythriQ-LTA-Lerntypanalyse-20250703a.docx"],
}

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


@dataclass(slots=True)
class ParsedSource:
    diagnostic_type: str
    file_name: str
    file_hash: str
    version: str
    definition: dict[str, object]


def load_parsed_sources(source_dir: Path) -> list[ParsedSource]:
    result: list[ParsedSource] = []
    for diagnostic_type, candidates in SOURCE_FILES.items():
        resolved_source: ParsedSource | None = None
        for candidate in candidates:
            candidate_path = source_dir / candidate
            if not candidate_path.exists():
                continue
            raw = candidate_path.read_bytes()
            file_hash = hashlib.sha256(raw).hexdigest()
            suffix = candidate_path.suffix.lower()
            if suffix == ".docx":
                paragraphs = _read_docx_paragraphs(candidate_path)
            elif suffix == ".pdf":
                paragraphs = _read_pdf_paragraphs(candidate_path)
            elif suffix == ".txt":
                paragraphs = _read_txt_paragraphs(candidate_path)
            else:
                paragraphs = _read_pages_paragraphs(candidate_path)

            version = _extract_version(diagnostic_type, candidate)
            if diagnostic_type == "LAA":
                definition = _parse_laa(paragraphs, version)
            elif diagnostic_type == "MOA":
                definition = _parse_moa(paragraphs, version)
            else:
                definition = _parse_lta(paragraphs, version)
            definition = _translate_definition_to_english(definition)

            question_count = sum(len(section.get("questions") or []) for section in list(definition.get("sections") or []))
            if question_count == 0:
                continue

            resolved_source = ParsedSource(
                diagnostic_type=diagnostic_type,
                file_name=candidate,
                file_hash=file_hash,
                version=version,
                definition=definition,
            )
            break
        if resolved_source is not None:
            result.append(resolved_source)
    return result


def _read_docx_paragraphs(path: Path) -> list[str]:
    xml = ZipFile(path).read("word/document.xml")
    root = ET.fromstring(xml)
    body = root.find("w:body", NS)
    lines: list[str] = []
    assert body is not None
    for child in body:
        tag = child.tag.split("}")[-1]
        if tag != "p":
            continue
        text = "".join(node.text or "" for node in child.findall(".//w:t", NS)).replace("\xa0", " ").strip()
        if text:
            lines.append(text)
    return lines


def _extract_version(diagnostic_type: str, file_name: str) -> str:
    semantic_versions = {"LAA": "1.1", "MOA": "1.0", "LTA": "1.0"}
    if diagnostic_type in semantic_versions:
        return semantic_versions[diagnostic_type]
    match = re.search(r"-(\d{8}[a-z]?)\.docx$", file_name)
    if match:
        return match.group(1)
    if file_name.lower().endswith(".pages"):
        return "1.0"
    return "v1"


def _read_pages_paragraphs(path: Path) -> list[str]:
    try:
        output = subprocess.check_output(["strings", str(path)], text=True)
    except Exception:
        return []
    lines = [line.strip().replace("\xa0", " ") for line in output.splitlines()]
    return [line for line in lines if len(line) >= 3]


def _read_txt_paragraphs(path: Path) -> list[str]:
    lines = [line.strip().replace("\xa0", " ") for line in path.read_text().splitlines()]
    return [line for line in lines if line]


def _read_pdf_paragraphs(path: Path) -> list[str]:
    # Preferred path for `prds/*.pdf`: use pypdf when installed.
    # If unavailable, we fail gracefully so the loader can continue with extracted text fallback files.
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return []

    try:
        reader = PdfReader(str(path))
    except Exception:
        return []

    lines: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        for line in text.splitlines():
            cleaned = line.strip().replace("\xa0", " ")
            if cleaned:
                lines.append(cleaned)
    return lines


def _canonical_block(lines: list[str]) -> list[str]:
    canonical: list[str] = []
    for line in lines:
        if line.startswith("=== PAGE"):
            continue
        if line.lower().startswith("machine translated by google"):
            continue
        if line.startswith("🔥 MythriQ"):
            continue
        if "Lernblockaden & Unterstützungsbedarfe1." in line:
            canonical.append("Lernblockaden & Unterstützungsbedarfe")
            canonical.append("1. Ich verliere schnell die Motivation, wenn …")
            continue
        cleaned = _normalize_ocr_line(line)
        if cleaned:
            canonical.append(cleaned)
    return canonical


def _normalize_ocr_line(line: str) -> str:
    text = re.sub(r"\s+", " ", line).strip()
    if not text:
        return ""
    # stitch split words from OCR such as "f urther", "n eeds", while keeping pronoun "I"
    parts = text.split(" ")
    merged: list[str] = []
    index = 0
    while index < len(parts):
        current = parts[index]
        if (
            len(current) == 1
            and current.lower() != "i"
            and index + 1 < len(parts)
            and re.match(r"^[a-z].*", parts[index + 1])
        ):
            merged.append(current + parts[index + 1])
            index += 2
            continue
        merged.append(current)
        index += 1
    text = " ".join(merged)
    return text


def _slug(value: str) -> str:
    text = value.lower().strip()
    text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def _parse_moa(lines: list[str], version: str) -> dict[str, object]:
    canonical = _canonical_block(lines)
    start = next((index for index, line in enumerate(canonical) if "what motivates you to learn" in line.lower()), -1)
    question_zone = canonical[start + 1 :] if start >= 0 else canonical
    blocks = _collect_numbered_blocks(question_zone)

    questions: list[dict[str, object]] = []
    dimensions: list[str] = []
    for index, block in enumerate(blocks, start=1):
        joined = " ".join(block).strip()
        dimension_match = re.search(r"\((?:Motive|Motivation)\s*:\s*([^)]+)\)", joined, flags=re.IGNORECASE)
        if not dimension_match:
            continue
        dimension = re.sub(r"\s+", " ", dimension_match.group(1).strip())
        text = re.sub(r"\((?:Motive|Motivation)\s*:[^)]+\)", "", joined, flags=re.IGNORECASE).strip()
        text = re.sub(r"^\d+\.\s*", "", text)
        if not text:
            continue
        dimensions.append(dimension)
        questions.append(
            {
                "id": f"moa_q{index:02d}",
                "text": text,
                "type": "slider",
                "min_value": 1,
                "max_value": 10,
                "options": [],
                "scoring": {"dimension": dimension, "method": "direct_slider"},
            }
        )

    section = {"id": "motivation", "title": "Was motiviert dich beim Lernen?", "questions": questions}
    scoring_rules = {
        "dimensions": sorted(set(dimensions)),
        "dominant_count": 2,
        "normalization": "value/10",
        "combination_interpretation": "top_2_pair",
    }

    return {
        "id": "diagnostic-moa",
        "type": "MOA",
        "title": "Motivation (MOA)",
        "version": version,
        "sections": [section],
        "scoring_rules": scoring_rules,
        "assumptions": [],
    }


def _parse_lta(lines: list[str], version: str) -> dict[str, object]:
    canonical = _canonical_block(lines)
    start = next((index for index, line in enumerate(canonical) if "questions:" in line.lower()), -1)
    source = canonical[start + 1 :] if start >= 0 else canonical

    questions: list[dict[str, object]] = []
    option_to_dimension = {"A": "auditiv", "V": "visuell", "K": "kinaesthetisch", "L": "lesen_schreiben"}
    current_question: dict[str, object] | None = None
    question_counter = 0

    for raw_line in source:
        line = re.sub(r"^Additional questions.*?:\s*\d+\s*", "", raw_line, flags=re.IGNORECASE).strip()
        if not line:
            continue
        option_line = line
        option_line = re.sub(r"^OK\s*:", "o K:", option_line, flags=re.IGNORECASE)
        option_line = re.sub(r"^O\s*K\s*:", "o K:", option_line, flags=re.IGNORECASE)

        question_match = re.match(r"^\d+\.\s*(.+)$", line)
        if question_match:
            question_counter += 1
            current_question = {
                "id": f"lta_q{question_counter:02d}",
                "text": question_match.group(1).strip(),
                "type": "single_choice",
                "options": [],
                "scoring": {"method": "option_weight"},
            }
            questions.append(current_question)
            continue

        if current_question and current_question.get("options") and len(current_question["options"]) >= 4 and line.endswith("?"):
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

        option_match = re.match(r"^(?:o\s*)?([AVKL])\s*:\s*(.+)$", option_line, flags=re.IGNORECASE)
        if option_match and current_question is not None:
            key = option_match.group(1).upper()
            label = option_match.group(2).strip()
            dimension = option_to_dimension[key]
            current_question["options"].append(
                {
                    "key": key,
                    "label": label,
                    "value": key,
                    "allows_text": False,
                    "scoring": {dimension: 1},
                }
            )
            continue

        if current_question and not current_question.get("options"):
            current_question["text"] = f"{current_question['text']} {line}".strip()
            continue

        if current_question and current_question.get("options"):
            options = current_question["options"]
            options[-1]["label"] = f"{options[-1]['label']} {line}".strip()

    scoring_rules = {
        "dimensions": ["auditiv", "visuell", "kinaesthetisch", "lesen_schreiben"],
        "normalization": "dimension_count/total_answers",
        "dominant_count": 1,
        "ties": "return_all",
    }

    return {
        "id": "diagnostic-lta",
        "type": "LTA",
        "title": "Learning Type (LTA)",
        "version": version,
        "sections": [{"id": "learning_type", "title": "Learning Type", "questions": questions}],
        "scoring_rules": scoring_rules,
        "assumptions": [],
    }


def _parse_laa(lines: list[str], version: str) -> dict[str, object]:
    canonical = _canonical_block(lines)

    section_titles = [
        "User needs",
        "Learning experience",
        "Conditions",
        "Objectives",
        "Skills and Interests",
        "Attitude",
        "Support needs",
        "Miscellaneous",
    ]
    sections_by_title = {title: {"id": _slug(title), "title": title, "questions": []} for title in section_titles}

    current_section_title = "User needs"
    current_question: dict[str, object] | None = None
    question_counter = 0
    force_multi_choice = False
    pending_option_text_as_new = False
    assumptions: list[str] = []

    def start_question(text: str, question_type: str) -> dict[str, object]:
        nonlocal question_counter, current_question
        question_counter += 1
        current_question = {
            "id": f"laa_q{question_counter:03d}",
            "text": text.strip(),
            "type": question_type,
            "options": [],
            "scoring": {"method": "derived_section_weight"},
        }
        sections_by_title[current_section_title]["questions"].append(current_question)
        return current_question

    for line in canonical:
        mapped_title = _map_laa_section_title(line)
        if mapped_title:
            current_section_title = mapped_title
            current_question = None
            force_multi_choice = False
            pending_option_text_as_new = False
            continue

        lower_line = line.lower()
        if lower_line.startswith("mythriq") or lower_line.startswith("goal:") or lower_line.startswith("format:"):
            continue
        if lower_line.startswith("please rate") or lower_line.startswith("apply at all"):
            continue
        if "multiple selections possible" in lower_line:
            force_multi_choice = True
            continue

        question_match = re.match(r"^\d+\.\s*(.+)$", line)
        if question_match:
            question_text = question_match.group(1).strip()
            qtype = "multi_choice" if force_multi_choice else "single_choice"
            if current_section_title == "Attitude":
                qtype = "likert"
            if "[ 1 ]" in line:
                qtype = "likert"
                question_text = re.sub(r"\[\s*[1-5]\s*\].*$", "", question_text).strip()
            start_question(question_text, qtype)
            pending_option_text_as_new = False
            if qtype == "likert":
                _set_likert_1_to_5(current_question)
            continue

        if (
            current_section_title == "Skills and Interests"
            and line.endswith("?")
            and not line.startswith("( )")
            and "please rate" not in lower_line
        ):
            start_question(line, "multi_choice")
            pending_option_text_as_new = False
            continue

        if (
            current_section_title in {"Skills and Interests", "Attitude"}
            and "[ 1 ]" in line
            and not line.startswith("( )")
            and " = " not in line
            and re.match(r"^(?:\d+\.\s*)?I\b", line.strip()) is not None
        ):
            text = re.sub(r"\[\s*1\s*\].*$", "", line).strip()
            if not text and current_question:
                _set_likert_1_to_5(current_question)
                continue
            start_question(text, "likert")
            pending_option_text_as_new = False
            _set_likert_1_to_5(current_question)
            continue

        if current_question and current_question["type"] == "likert":
            continuation = re.sub(r"\[\s*[1-5]\s*\]", "", line).strip()
            if continuation:
                current_question["text"] = f"{current_question['text']} {continuation}".strip()
            continue

        if "( )" in line:
            if current_question is None:
                start_question("Selection", "multi_choice" if force_multi_choice else "single_choice")
            prefix, option_labels = _extract_checkbox_options(line)
            if prefix:
                if pending_option_text_as_new:
                    option_key = f"o{len(current_question['options']) + 1}"
                    current_question["options"].append(
                        {
                            "key": option_key,
                            "label": prefix,
                            "value": option_key,
                            "allows_text": "miscellaneous" in prefix.lower() or "other" in prefix.lower(),
                        }
                    )
                elif current_question["options"]:
                    current_question["options"][-1]["label"] = f"{current_question['options'][-1]['label']} {prefix}".strip()
            for option_label in option_labels:
                for resolved_label in _split_laa_merged_option(option_label):
                    option_key = f"o{len(current_question['options']) + 1}"
                    current_question["options"].append(
                        {
                            "key": option_key,
                            "label": resolved_label,
                            "value": option_key,
                            "allows_text": "miscellaneous" in resolved_label.lower() or "other" in resolved_label.lower(),
                        }
                    )
            pending_option_text_as_new = bool(re.search(r"\(\s*\)\s*$", line))
            continue

        # Wrapped option/statement continuation.
        if current_question and current_question["type"] != "likert":
            if pending_option_text_as_new and line and not line.startswith("["):
                option_key = f"o{len(current_question['options']) + 1}"
                current_question["options"].append(
                    {
                        "key": option_key,
                        "label": line.strip(),
                        "value": option_key,
                        "allows_text": "miscellaneous" in line.lower() or "other" in line.lower(),
                    }
                )
                pending_option_text_as_new = False
                continue
            if current_question["options"]:
                current_question["options"][-1]["label"] = f"{current_question['options'][-1]['label']} {line}".strip()
            elif line and not line.startswith("["):
                current_question["text"] = f"{current_question['text']} {line}".strip()
            pending_option_text_as_new = False

    sections = [sections_by_title[title] for title in section_titles if sections_by_title[title]["questions"]]

    # Derived LAA scoring assumptions are documented explicitly because the source has no explicit algorithm.
    assumptions.append(
        "The LAA source does not define an explicit mathematical formula; scores are therefore aggregated per section."
    )
    assumptions.append(
        "Likert items (1-5) use numeric values directly; each selected multi-choice option contributes +1 to the section."
    )

    scoring_rules = {
        "method": "section_aggregation",
        "normalization": "section_score/max_section_score",
        "dominant_count": 3,
    }

    return {
        "id": "diagnostic-laa",
        "type": "LAA",
        "title": "Learning Approach (LAA)",
        "version": version,
        "sections": sections,
        "scoring_rules": scoring_rules,
        "assumptions": assumptions,
    }


def _collect_numbered_blocks(lines: Iterable[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if re.match(r"^\d+\.\s*", line):
            if current:
                blocks.append(current)
            current = [line]
            continue
        if current:
            current.append(line)
    if current:
        blocks.append(current)
    return blocks


def _map_laa_section_title(line: str) -> str | None:
    normalized = normalize_text(line)
    mapping = {
        "user needs": "User needs",
        "nutzerbedurfnisse": "User needs",
        "learning experience and self image": "Learning experience",
        "lernerfahrung und selbstbild": "Learning experience",
        "time framework": "Conditions",
        "zeit und rahmenbedingungen": "Conditions",
        "zeit rahmenbedingungen": "Conditions",
        "learning objectives motivation": "Objectives",
        "lernziele motivation": "Objectives",
        "skills interests": "Skills and Interests",
        "interests": "Skills and Interests",
        "competencies skills self assessment": "Skills and Interests",
        "soft skills self assessment via slider": "Skills and Interests",
        "emotional attitude towards learning": "Attitude",
        "emotionale haltung zum lernen": "Attitude",
        "learning blocks support needs": "Support needs",
        "lernblockaden unterstutzungsbedarfe": "Support needs",
        "other personalization options": "Miscellaneous",
        "sonstiges zur personalisierung": "Miscellaneous",
    }
    return mapping.get(normalized)


def _set_likert_1_to_5(question: dict[str, object] | None) -> None:
    if question is None:
        return
    question["type"] = "likert"
    question["min_value"] = 1
    question["max_value"] = 5
    question["options"] = [
        {"key": str(value), "label": str(value), "value": str(value), "allows_text": False}
        for value in range(1, 6)
    ]


def _extract_checkbox_options(line: str) -> tuple[str, list[str]]:
    # Split lines that can contain multiple "( ) option" chunks.
    # Returns optional prefix text (continuation for previous option) and extracted option labels.
    parts = re.split(r"\(\s*\)", line)
    if not parts:
        return "", []
    prefix = parts[0].strip()
    labels = [re.sub(r"\s+", " ", part).strip() for part in parts[1:] if part.strip()]
    return prefix, labels


def _split_laa_merged_option(label: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", label).strip()
    split_match = re.match(
        r"^(I don't know what I'm learning something for)\s+(it becomes too difficult.*)$",
        cleaned,
        flags=re.IGNORECASE,
    )
    if split_match:
        return [split_match.group(1), split_match.group(2)]
    return [cleaned]


def normalize_text(value: str) -> str:
    base = (
        value.lower()
        .replace("&", " ")
        .replace("/", " ")
        .replace("–", " ")
        .replace("-", " ")
        .replace("'", "")
    )
    ascii_only = unicodedata.normalize("NFD", base).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_only).strip()


def _translate_definition_to_english(definition: dict[str, object]) -> dict[str, object]:
    translated = dict(definition)
    translated["title"] = _translate_text(str(translated.get("title") or ""))

    next_sections: list[dict[str, object]] = []
    for section in list(translated.get("sections") or []):
        section_dict = dict(section)
        section_dict["title"] = _translate_section_title(str(section_dict.get("title") or ""))
        section_dict["id"] = _slug(section_dict["title"])
        next_questions: list[dict[str, object]] = []
        for question in list(section_dict.get("questions") or []):
            question_dict = dict(question)
            question_dict["text"] = _translate_text(str(question_dict.get("text") or ""))
            next_options: list[dict[str, object]] = []
            for option in list(question_dict.get("options") or []):
                option_dict = dict(option)
                option_dict["label"] = _translate_text(str(option_dict.get("label") or ""))
                next_options.append(option_dict)
            question_dict["options"] = next_options
            scoring = dict(question_dict.get("scoring") or {})
            if "dimension" in scoring:
                scoring["dimension"] = _translate_text(str(scoring.get("dimension") or ""))
            question_dict["scoring"] = scoring
            next_questions.append(question_dict)
        section_dict["questions"] = next_questions
        next_sections.append(section_dict)

    translated["sections"] = next_sections
    return translated


def _translate_section_title(value: str) -> str:
    normalized = value.strip()
    mapping = {
        "Nutzerbedürfnisse": "User needs",
        "Lernerfahrung und Selbstbild": "Learning experience",
        "Zeit & Rahmenbedingungen": "Conditions",
        "Zeit und Rahmenbedingungen": "Conditions",
        "Lernziele & Motivation": "Objectives",
        "Skills & Interessen": "Skills and Interests",
        "INTERESSEN": "Skills and Interests",
        "KOMPETENZEN / SKILLS (Selbsteinschätzung)": "Skills and Interests",
        "SOFT SKILLS (Selbsteinschätzung via Regler)": "Skills and Interests",
        "Emotionale Haltung zum Lernen": "Attitude",
        "Lernblockaden & Unterstützungsbedarfe": "Support needs",
        "Sonstiges zur Personalisierung": "Miscellaneous",
        "Was motiviert dich beim Lernen?": "Motivation",
    }
    return mapping.get(normalized, _translate_text(normalized))


def _translate_text(value: str) -> str:
    text = value.strip()
    if not text:
        return text
    replacements = {
        "MythriQ": "",
        "Lernartanalyse (LAA)": "Learning Approach (LAA)",
        "Motivationsanalyse (MOA)": "Motivation (MOA)",
        "Lerntypanalyse (LTA)": "Learning Type (LTA)",
        "Nutzerbedürfnisse": "User needs",
        "Lernerfahrung und Selbstbild": "Learning experience",
        "Zeit & Rahmenbedingungen": "Conditions",
        "Zeit und Rahmenbedingungen": "Conditions",
        "Lernziele & Motivation": "Objectives",
        "Skills & Interessen": "Skills and Interests",
        "Emotionale Haltung zum Lernen": "Attitude",
        "Lernblockaden & Unterstützungsbedarfe": "Support needs",
        "Sonstiges zur Personalisierung": "Miscellaneous",
        "Sonstiges": "Miscellaneous",
        "Fragen:": "Questions:",
        "Mehrfachauswahl möglich": "Multiple selection possible",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = re.sub(r"\s+", " ", text).strip()
    return text
