from __future__ import annotations

from pathlib import Path

import pytest

from services.retriever.services.course_files import CourseFileParser


def test_course_file_parser_accepts_valid_v2_payload() -> None:
    parser = CourseFileParser()
    payload = {
        "schema_version": 2,
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
        "chapters": [
            {"id": "chapter-1", "order_index": 0, "title": "Chapter", "description": "", "metadata": {}},
        ],
        "branches": [
            {"id": "core", "title": "Core", "description": "", "required": True, "metadata": {}},
            {"id": "optional", "title": "Optional", "description": "", "required": False, "metadata": {}},
        ],
        "nodes": [
            {
                "id": "node-1",
                "title": "Node",
                "description": "",
                "type": "quiz",
                "chapter_id": "chapter-1",
                "branch_id": "core",
                "required": True,
                "prerequisites": {"requires_all": [], "requires_any": [], "recommended": []},
                "completion_mode": "quiz_pass",
                "estimated_duration_minutes": 10,
                "layout": {"x": 100, "y": 100},
                "metadata": {"pass_threshold": 0.75},
                "display": {},
                "ksa": [{"dimension": "K", "topic": "information_technology", "start_level": 1, "target_level": 2}],
                "unlocks": {"node_ids": [], "branch_ids": [], "recommended_next_node_ids": []},
                "rewards": {"estimated_ksa_gain": {"K.information_technology": 0.1}, "effort_score": 10, "reward_tags": ["quiz"]},
            }
        ],
        "edges": [],
        "entry_node_ids": ["node-1"],
        "completion_rules": {"required_completion": "all_required_nodes"},
        "visual_layout": {"layout_engine": "manual"},
        "metadata": {},
    }

    parsed = parser.parse_payload("course.json", payload)
    assert parsed.schema_version == 2
    assert parsed.allowed_tags == ["docker"]
    assert parsed.nodes[0].type == "quiz"
    assert parsed.nodes[0].completion_mode == "quiz_pass"
    assert parsed.nodes[0].branch_id == "core"


def test_course_file_parser_migrates_v1_payload_to_v2_graph() -> None:
    parser = CourseFileParser()
    payload = {
        "schema_version": 1,
        "id": "course-test",
        "title": "Course Test",
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
                        "title": "Lesson A",
                        "description": "",
                        "objectives": [],
                        "teaching_notes": "",
                    },
                    {
                        "order_index": 1,
                        "title": "Lesson B",
                        "description": "",
                        "objectives": [],
                        "teaching_notes": "",
                    },
                ],
            }
        ],
    }

    parsed = parser.parse_payload("course.json", payload)
    assert parsed.schema_version == 2
    assert parsed.source_schema_version == 1
    assert len(parsed.nodes) == 2
    assert len(parsed.edges) == 1
    assert parsed.entry_node_ids


def test_course_template_is_v2_skilltree() -> None:
    parser = CourseFileParser()
    template = parser.template_payload()
    assert template["schema_version"] == 2
    assert "chapters" in template
    assert "nodes" in template
    assert "edges" in template


def test_course_file_parser_rejects_user_scope_without_owner() -> None:
    parser = CourseFileParser()
    payload = {
        "schema_version": 2,
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
        "chapters": [],
        "branches": [],
        "nodes": [],
        "edges": [],
        "entry_node_ids": [],
        "completion_rules": {},
        "visual_layout": {},
        "metadata": {},
    }

    with pytest.raises(ValueError):
        parser.parse_payload("course.json", payload)


def test_course_file_parser_rejects_cycles() -> None:
    parser = CourseFileParser()
    payload = {
        "schema_version": 2,
        "id": "course-test",
        "title": "Cycle",
        "description": "",
        "scope": "global",
        "owner_user_id": None,
        "subject": "",
        "difficulty_level": "",
        "estimated_duration_minutes": None,
        "status": "draft",
        "allowed_file_ids": [],
        "allowed_tags": [],
        "chapters": [{"id": "chapter-1", "order_index": 0, "title": "Chapter", "description": "", "metadata": {}}],
        "branches": [],
        "nodes": [
            {
                "id": "a",
                "title": "A",
                "description": "",
                "type": "learning_unit",
                "chapter_id": "chapter-1",
                "required": True,
                "prerequisites": {"requires_all": ["b"], "requires_any": [], "recommended": []},
                "completion_mode": "lesson_complete",
                "layout": {"x": 10, "y": 10},
                "metadata": {},
                "display": {},
                "ksa": [],
                "unlocks": {"node_ids": [], "branch_ids": [], "recommended_next_node_ids": []},
                "rewards": {"estimated_ksa_gain": {}, "effort_score": None, "reward_tags": []},
            },
            {
                "id": "b",
                "title": "B",
                "description": "",
                "type": "learning_unit",
                "chapter_id": "chapter-1",
                "required": True,
                "prerequisites": {"requires_all": ["a"], "requires_any": [], "recommended": []},
                "completion_mode": "lesson_complete",
                "layout": {"x": 100, "y": 10},
                "metadata": {},
                "display": {},
                "ksa": [],
                "unlocks": {"node_ids": [], "branch_ids": [], "recommended_next_node_ids": []},
                "rewards": {"estimated_ksa_gain": {}, "effort_score": None, "reward_tags": []},
            },
        ],
        "edges": [],
        "entry_node_ids": [],
        "completion_rules": {},
        "visual_layout": {},
        "metadata": {},
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


def test_course_file_parser_rejects_unknown_branch_reference() -> None:
    parser = CourseFileParser()
    payload = {
        "schema_version": 2,
        "id": "course-branch-test",
        "title": "Branch Test",
        "description": "",
        "scope": "global",
        "owner_user_id": None,
        "subject": "",
        "difficulty_level": "",
        "estimated_duration_minutes": None,
        "status": "draft",
        "allowed_file_ids": [],
        "allowed_tags": [],
        "chapters": [{"id": "chapter-1", "order_index": 0, "title": "Chapter", "description": "", "metadata": {}}],
        "branches": [{"id": "core", "title": "Core", "description": "", "required": True, "metadata": {}}],
        "nodes": [
            {
                "id": "node-1",
                "title": "Node",
                "description": "",
                "type": "capstone",
                "chapter_id": "chapter-1",
                "branch_id": "missing-branch",
                "required": True,
                "prerequisites": {"requires_all": [], "requires_any": [], "recommended": []},
                "completion_mode": "checkpoint_pass",
                "layout": {"x": 0, "y": 0},
                "metadata": {},
                "display": {},
                "ksa": [],
            }
        ],
        "edges": [],
        "entry_node_ids": ["node-1"],
        "completion_rules": {},
        "visual_layout": {},
        "metadata": {},
    }

    with pytest.raises(ValueError):
        parser.parse_payload("course.json", payload)
