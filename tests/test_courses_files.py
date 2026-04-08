from __future__ import annotations

from pathlib import Path

import pytest

from services.retriever.services.course_files import CourseFileParser


def test_course_file_parser_accepts_valid_payload() -> None:
    parser = CourseFileParser()
    payload = {
        "schema_version": 1,
        "id": "course-test",
        "title": "Course Test",
        "description": "Test",
        "scope": "global",
        "owner_user_id": None,
        "subject": "Docker",
        "difficulty_level": "beginner",
        "estimated_duration_minutes": 30,
        "status": "draft",
        "allowed_file_ids": [1],
        "allowed_tags": ["Docker", " docker "],
        "modules": [
            {
                "id": "module-1",
                "order_index": 0,
                "title": "Module",
                "description": "",
                "learning_objectives": [" Goal "],
                "lessons": [
                    {
                        "id": "lesson-1",
                        "order_index": 0,
                        "title": "Lesson",
                        "description": "",
                        "objectives": [" Objective "],
                        "teaching_notes": " Note ",
                    }
                ],
            }
        ],
    }

    parsed = parser.parse_payload("course.json", payload)
    assert parsed.allowed_tags == ["docker"]
    assert parsed.modules[0].learning_objectives == ["Goal"]
    assert parsed.modules[0].lessons[0].objectives == ["Objective"]


def test_course_file_parser_accepts_payload_without_ids() -> None:
    parser = CourseFileParser()
    payload = {
        "schema_version": 1,
        "title": "Course Without IDs",
        "description": "",
        "scope": "global",
        "owner_user_id": None,
        "subject": "",
        "difficulty_level": "",
        "estimated_duration_minutes": None,
        "status": "draft",
        "allowed_file_ids": [],
        "allowed_tags": [],
        "modules": [
            {
                "order_index": 0,
                "title": "Module",
                "description": "",
                "learning_objectives": [],
                "lessons": [
                    {
                        "order_index": 0,
                        "title": "Lesson",
                        "description": "",
                        "objectives": [],
                        "teaching_notes": "",
                    }
                ],
            }
        ],
    }

    parsed = parser.parse_payload("course.json", payload)
    assert parsed.id is None
    assert parsed.modules[0].id is None
    assert parsed.modules[0].lessons[0].id is None


def test_course_template_omits_ids() -> None:
    parser = CourseFileParser()
    template = parser.template_payload()
    assert "id" not in template
    assert all("id" not in module for module in template["modules"])
    assert all("id" not in lesson for module in template["modules"] for lesson in module["lessons"])


def test_course_file_parser_rejects_user_scope_without_owner() -> None:
    parser = CourseFileParser()
    payload = {
        "schema_version": 1,
        "id": "course-test",
        "title": "Course Test",
        "description": "",
        "scope": "user",
        "owner_user_id": None,
        "subject": "",
        "difficulty_level": "",
        "estimated_duration_minutes": None,
        "status": "draft",
        "allowed_file_ids": [],
        "allowed_tags": [],
        "modules": [],
    }

    with pytest.raises(ValueError):
        parser.parse_payload("course.json", payload)


def test_course_examples_are_valid_json() -> None:
    parser = CourseFileParser()
    courses_dir = Path("courses")
    assert courses_dir.exists()
    files = sorted(courses_dir.glob("*.json"))
    assert files
    for file in files:
        parser.parse_file(file)
