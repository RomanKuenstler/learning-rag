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
            "branches": [
                {"id": "core", "title": "Core", "description": "", "required": True, "metadata": {}},
                {"id": "optional", "title": "Optional", "description": "", "required": False, "metadata": {}},
            ],
            "nodes": [
                {
                    "id": "n1",
                    "title": "Entry",
                    "description": "",
                    "type": "learning_unit",
                    "chapter_id": "c1",
                    "branch_id": "core",
                    "required": True,
                    "prerequisites": {"requires_all": [], "requires_any": [], "recommended": []},
                    "completion_mode": "lesson_complete",
                    "layout": {"x": 0, "y": 0},
                    "metadata": {},
                    "display": {},
                    "ksa": [],
                    "unlocks": {"node_ids": [], "branch_ids": [], "recommended_next_node_ids": []},
                    "rewards": {"estimated_ksa_gain": {}, "effort_score": None, "reward_tags": []},
                },
                {
                    "id": "n2",
                    "title": "Branch A",
                    "description": "",
                    "type": "practice",
                    "chapter_id": "c1",
                    "branch_id": "core",
                    "required": True,
                    "prerequisites": {"requires_all": ["n1"], "requires_any": [], "recommended": []},
                    "completion_mode": "practice_complete",
                    "layout": {"x": 100, "y": 0},
                    "metadata": {},
                    "display": {},
                    "ksa": [],
                    "unlocks": {"node_ids": [], "branch_ids": [], "recommended_next_node_ids": []},
                    "rewards": {"estimated_ksa_gain": {}, "effort_score": None, "reward_tags": []},
                },
                {
                    "id": "n3",
                    "title": "Optional Branch",
                    "description": "",
                    "type": "quiz",
                    "chapter_id": "c1",
                    "branch_id": "optional",
                    "required": True,
                    "prerequisites": {"requires_all": ["n1"], "requires_any": [], "recommended": []},
                    "completion_mode": "quiz_pass",
                    "layout": {"x": 100, "y": 80},
                    "metadata": {"pass_threshold": 0.7},
                    "display": {},
                    "ksa": [],
                    "unlocks": {"node_ids": [], "branch_ids": [], "recommended_next_node_ids": []},
                    "rewards": {"estimated_ksa_gain": {}, "effort_score": None, "reward_tags": []},
                },
                {
                    "id": "n4",
                    "title": "Merge",
                    "description": "",
                    "type": "unlock_gate",
                    "chapter_id": "c2",
                    "branch_id": "core",
                    "required": True,
                    "prerequisites": {"requires_all": [], "requires_any": ["n2", "n3"], "recommended": []},
                    "completion_mode": "gate_unlock",
                    "layout": {"x": 220, "y": 40},
                    "metadata": {"gate_key": "release"},
                    "display": {},
                    "ksa": [],
                    "unlocks": {"node_ids": [], "branch_ids": [], "recommended_next_node_ids": []},
                    "rewards": {"estimated_ksa_gain": {}, "effort_score": None, "reward_tags": []},
                },
                {
                    "id": "n5",
                    "title": "Capstone",
                    "description": "",
                    "type": "capstone",
                    "chapter_id": "c2",
                    "branch_id": "core",
                    "required": True,
                    "prerequisites": {"requires_all": ["n4"], "requires_any": [], "recommended": []},
                    "completion_mode": "checkpoint_pass",
                    "layout": {"x": 320, "y": 40},
                    "metadata": {"pass_threshold": 0.8},
                    "display": {},
                    "ksa": [],
                    "unlocks": {"node_ids": [], "branch_ids": [], "recommended_next_node_ids": []},
                    "rewards": {"estimated_ksa_gain": {}, "effort_score": None, "reward_tags": []},
                },
            ],
            "edges": [
                {"from_node_id": "n1", "to_node_id": "n2", "relationship": "requires_all"},
                {"from_node_id": "n1", "to_node_id": "n3", "relationship": "requires_all"},
                {"from_node_id": "n2", "to_node_id": "n4", "relationship": "requires_any"},
                {"from_node_id": "n3", "to_node_id": "n4", "relationship": "requires_any"},
                {"from_node_id": "n4", "to_node_id": "n5", "relationship": "requires_all"},
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


def test_runtime_course_completion_uses_effective_required_nodes() -> None:
    runtime = build_skilltree_runtime(
        _definition(),
        persisted_node_progress={"n1": "completed", "n2": "completed", "n4": "mastered", "n5": "mastered", "n3": "optional_skipped"},
    )
    # n3 is flagged required but belongs to an optional branch, so it does not block completion.
    assert runtime.completion_summary.required_total == 4
    assert runtime.completion_summary.required_completed == 4
    assert runtime.completion_summary.is_complete is True


def test_runtime_marks_checkpoint_wait_state_and_capstone_lock() -> None:
    runtime = build_skilltree_runtime(_definition(), persisted_node_progress={"n1": "completed", "n2": "completed"})
    assert runtime.node_progress["n5"] in {"awaiting_checkpoint", "locked"}
    assert runtime.node_runtime["n5"].capstone_locked is True


def test_runtime_parallel_available_semantics() -> None:
    runtime = build_skilltree_runtime(_definition(), persisted_node_progress={"n1": "completed"})
    assert runtime.node_progress["n2"] == "available"
    assert runtime.node_progress["n3"] == "available"
    assert runtime.node_runtime["n2"].is_parallel_available is True
    assert runtime.node_runtime["n3"].is_parallel_available is True
