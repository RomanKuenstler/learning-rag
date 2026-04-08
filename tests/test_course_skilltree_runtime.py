from __future__ import annotations

from services.retriever.services.course_files import CourseDefinition
from services.retriever.services.course_skilltree import build_skilltree_runtime


def _definition() -> CourseDefinition:
    return CourseDefinition.model_validate(
        {
            "schema_version": 2,
            "source_schema_version": 2,
            "id": "course-1",
            "title": "Skilltree",
            "description": "",
            "scope": "global",
            "owner_user_id": None,
            "subject": "",
            "difficulty_level": "",
            "estimated_duration_minutes": None,
            "status": "draft",
            "allowed_file_ids": [],
            "allowed_tags": [],
            "chapters": [
                {"id": "c1", "title": "Foundations", "description": "", "order_index": 0, "metadata": {}},
                {"id": "c2", "title": "Advanced", "description": "", "order_index": 1, "metadata": {}},
            ],
            "nodes": [
                {
                    "id": "n1",
                    "title": "Entry",
                    "description": "",
                    "type": "learning_unit",
                    "chapter_id": "c1",
                    "required": True,
                    "prerequisites": {"requires_all": [], "requires_any": [], "recommended": []},
                    "completion_mode": "lesson_complete",
                    "layout": {"x": 0, "y": 0},
                    "metadata": {},
                    "display": {},
                    "ksa": [],
                },
                {
                    "id": "n2",
                    "title": "Branch A",
                    "description": "",
                    "type": "practice",
                    "chapter_id": "c1",
                    "required": True,
                    "prerequisites": {"requires_all": ["n1"], "requires_any": [], "recommended": []},
                    "completion_mode": "practice_complete",
                    "layout": {"x": 100, "y": 0},
                    "metadata": {},
                    "display": {},
                    "ksa": [],
                },
                {
                    "id": "n3",
                    "title": "Branch B",
                    "description": "",
                    "type": "practice",
                    "chapter_id": "c1",
                    "required": False,
                    "prerequisites": {"requires_all": ["n1"], "requires_any": [], "recommended": []},
                    "completion_mode": "practice_complete",
                    "layout": {"x": 100, "y": 80},
                    "metadata": {},
                    "display": {},
                    "ksa": [],
                },
                {
                    "id": "n4",
                    "title": "Merge",
                    "description": "",
                    "type": "checkpoint",
                    "chapter_id": "c2",
                    "required": True,
                    "prerequisites": {"requires_all": [], "requires_any": ["n2", "n3"], "recommended": []},
                    "completion_mode": "checkpoint_pass",
                    "layout": {"x": 220, "y": 40},
                    "metadata": {},
                    "display": {},
                    "ksa": [],
                },
            ],
            "edges": [
                {"from_node_id": "n1", "to_node_id": "n2", "relationship": "requires_all"},
                {"from_node_id": "n1", "to_node_id": "n3", "relationship": "requires_all"},
                {"from_node_id": "n2", "to_node_id": "n4", "relationship": "requires_any"},
                {"from_node_id": "n3", "to_node_id": "n4", "relationship": "requires_any"},
            ],
            "entry_node_ids": ["n1"],
            "completion_rules": {"required_completion": "all_required_nodes"},
            "visual_layout": {},
            "metadata": {},
        }
    )


def test_runtime_unlocks_entry_and_then_branches() -> None:
    runtime = build_skilltree_runtime(_definition(), persisted_node_progress={})
    assert runtime.node_progress["n1"] == "available"
    assert runtime.node_progress["n2"] == "locked"
    assert runtime.node_progress["n3"] == "locked"


def test_runtime_supports_parallel_and_optional_paths() -> None:
    runtime = build_skilltree_runtime(_definition(), persisted_node_progress={"n1": "completed", "n3": "optional_skipped"})
    assert runtime.node_progress["n2"] == "available"
    assert runtime.node_progress["n4"] == "locked"


def test_runtime_supports_requires_any_merge_completion() -> None:
    runtime = build_skilltree_runtime(_definition(), persisted_node_progress={"n1": "completed", "n2": "completed"})
    assert runtime.node_progress["n4"] == "available"


def test_runtime_course_completion_uses_required_nodes_only() -> None:
    runtime = build_skilltree_runtime(
        _definition(),
        persisted_node_progress={"n1": "completed", "n2": "completed", "n4": "mastered", "n3": "optional_skipped"},
    )
    assert runtime.completion_summary.required_total == 3
    assert runtime.completion_summary.required_completed == 3
    assert runtime.completion_summary.is_complete is True
