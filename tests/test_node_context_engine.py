from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from services.common.models import LearningPath
from services.retriever.services.course_files import CourseDefinition
from services.retriever.services.node_context import LearningNodeContextEngine


def _definition() -> CourseDefinition:
    return CourseDefinition.model_validate(
        {
            "schema_version": 2,
            "source_schema_version": 2,
            "id": "course-node-context",
            "title": "Node Context Course",
            "description": "Test graph",
            "scope": "global",
            "owner_user_id": None,
            "subject": "Docker",
            "difficulty_level": "beginner",
            "estimated_duration_minutes": 120,
            "status": "published",
            "allowed_file_ids": [],
            "allowed_tags": [],
            "chapters": [
                {"id": "c1", "title": "Foundations", "description": "", "order_index": 0, "metadata": {}},
                {"id": "c2", "title": "Practice", "description": "", "order_index": 1, "metadata": {}},
            ],
            "branches": [
                {"id": "core", "title": "Core", "description": "", "required": True, "metadata": {}},
                {"id": "opt", "title": "Optional", "description": "", "required": False, "metadata": {}},
            ],
            "nodes": [
                {
                    "id": "n1",
                    "title": "Intro",
                    "description": "Start here",
                    "type": "learning_unit",
                    "chapter_id": "c1",
                    "branch_id": "core",
                    "required": True,
                    "prerequisites": {"requires_all": [], "requires_any": [], "recommended": []},
                    "completion_mode": "lesson_complete",
                    "estimated_duration_minutes": 10,
                    "layout": {"x": 0, "y": 0},
                    "metadata": {"topics": ["docker basics"], "goals": ["understand containers"], "difficulty_level": "beginner"},
                    "display": {},
                    "ksa": [{"dimension": "K", "topic": "information_technology", "start_level": 1, "target_level": 2}],
                    "unlocks": {"node_ids": ["n2"], "branch_ids": [], "recommended_next_node_ids": []},
                    "rewards": {"estimated_ksa_gain": {"K.information_technology": 0.2}, "effort_score": 10, "reward_tags": []},
                    "retrospective_hooks": {"retrospective_after": False, "review_recommended": False, "recap_checkpoint_available": False},
                    "ksa_hooks": {"mini_assessment_available": False, "recommended_reassessment_topics": [], "unlocks_deeper_refinement": False},
                    "remediation": {"is_remediation_node": False, "recommended_if_failed_node_ids": [], "supports_review_for_node_ids": []},
                    "adaptive_unlock": {"ksa_thresholds": [], "requires_branch_completion_ids": [], "requires_checkpoint_node_ids": [], "requires_review_recommended": False, "recommended_only": False},
                },
                {
                    "id": "n2",
                    "title": "Hands-on",
                    "description": "Run commands",
                    "type": "practice",
                    "chapter_id": "c2",
                    "branch_id": "core",
                    "required": True,
                    "prerequisites": {"requires_all": ["n1"], "requires_any": [], "recommended": []},
                    "completion_mode": "practice_complete",
                    "estimated_duration_minutes": 20,
                    "layout": {"x": 100, "y": 0},
                    "metadata": {"topics": ["docker run"], "goals": ["run containers"], "difficulty_level": "intermediate"},
                    "display": {},
                    "ksa": [{"dimension": "S", "topic": "digital_craft", "subtopic": "DevOps/Version Control", "start_level": 1, "target_level": 2}],
                    "unlocks": {"node_ids": ["n3"], "branch_ids": [], "recommended_next_node_ids": ["n3"]},
                    "rewards": {"estimated_ksa_gain": {"S.digital_craft": 0.2}, "effort_score": 20, "reward_tags": []},
                    "retrospective_hooks": {"retrospective_after": False, "review_recommended": False, "recap_checkpoint_available": False},
                    "ksa_hooks": {"mini_assessment_available": False, "recommended_reassessment_topics": [], "unlocks_deeper_refinement": False},
                    "remediation": {"is_remediation_node": False, "recommended_if_failed_node_ids": [], "supports_review_for_node_ids": []},
                    "adaptive_unlock": {"ksa_thresholds": [], "requires_branch_completion_ids": [], "requires_checkpoint_node_ids": [], "requires_review_recommended": False, "recommended_only": False},
                },
                {
                    "id": "n3",
                    "title": "Checkpoint",
                    "description": "Validate",
                    "type": "checkpoint",
                    "chapter_id": "c2",
                    "branch_id": "core",
                    "required": True,
                    "prerequisites": {"requires_all": ["n2"], "requires_any": [], "recommended": []},
                    "completion_mode": "checkpoint_pass",
                    "estimated_duration_minutes": 15,
                    "layout": {"x": 200, "y": 0},
                    "metadata": {"difficulty_level": "intermediate", "pass_threshold": 0.7},
                    "display": {},
                    "ksa": [],
                    "unlocks": {"node_ids": [], "branch_ids": [], "recommended_next_node_ids": []},
                    "rewards": {"estimated_ksa_gain": {}, "effort_score": 10, "reward_tags": []},
                    "retrospective_hooks": {"retrospective_after": False, "review_recommended": True, "recap_checkpoint_available": True},
                    "ksa_hooks": {"mini_assessment_available": True, "recommended_reassessment_topics": ["digital_craft"], "unlocks_deeper_refinement": False},
                    "remediation": {"is_remediation_node": False, "recommended_if_failed_node_ids": [], "supports_review_for_node_ids": []},
                    "adaptive_unlock": {"ksa_thresholds": [], "requires_branch_completion_ids": [], "requires_checkpoint_node_ids": [], "requires_review_recommended": False, "recommended_only": False},
                },
            ],
            "edges": [
                {"from_node_id": "n1", "to_node_id": "n2", "relationship": "requires_all"},
                {"from_node_id": "n2", "to_node_id": "n3", "relationship": "requires_all"},
            ],
            "entry_node_ids": ["n1"],
            "completion_rules": {"required_completion": "all_required_nodes"},
            "visual_layout": {},
            "metadata": {"domain": "containers"},
        }
    )


def _path() -> LearningPath:
    now = datetime.now(timezone.utc)
    return LearningPath(
        id="course-node-context",
        scope="global",
        owner_user_id=None,
        title="Node Context Course",
        description="Test graph",
        subject="Docker",
        difficulty_level="beginner",
        estimated_duration_minutes=120,
        status="published",
        schema_version=2,
        skilltree_definition={},
        created_at=now,
        updated_at=now,
    )


class _RepoStub:
    def __init__(self) -> None:
        self.progress_map = {"n1": "completed", "n2": "in_progress"}
        now = datetime.now(timezone.utc)
        self.ksa_profile = SimpleNamespace(
            profile_json={
                "knowledge": {"information_technology": 3},
                "skills": {"digital_craft": 3},
                "abilities": {"executive_function": 2},
                "assessment_details": {"derived": {"learning_speed_multiplier": 1.5}},
                "drill_state": {
                    "topic_nodes": {
                        "digital_craft": {
                            "level": 3.4,
                            "chart_level": 3,
                            "status": "verified",
                            "confidence": 0.74,
                            "map_decay_events_total": 0,
                        }
                    }
                },
            },
            updated_at=now,
        )
        self._saved = None

    def list_user_learning_node_progress(self, *, user_id: int, learning_path_id: str):
        _ = (user_id, learning_path_id)
        return [SimpleNamespace(node_id=node_id, status=status) for node_id, status in self.progress_map.items()]

    def get_user_ksa_profile(self, user_id: int):
        _ = user_id
        return self.ksa_profile

    def list_user_ksa_drill_attempts(self, *, user_id: int, limit: int = 50):
        _ = (user_id, limit)
        return [
            SimpleNamespace(
                id="drill-1",
                completed_at=datetime.now(timezone.utc),
                selected_topic_keys_json=["digital_craft"],
                status="completed",
            )
        ]

    def upsert_user_learning_node_context(self, *, user_id: int, learning_path_id: str, node_id: str, fields: dict[str, object]):
        now = datetime.now(timezone.utc)
        self._saved = SimpleNamespace(
            user_id=user_id,
            learning_path_id=learning_path_id,
            node_id=node_id,
            node_type=fields.get("node_type", ""),
            generation_reason=fields.get("generation_reason", ""),
            source_hash=fields.get("source_hash", ""),
            generated_at=fields.get("generated_at"),
            context_json=dict(fields.get("context_json") or {}),
            course_context_json=dict(fields.get("course_context_json") or {}),
            chapter_branch_context_json=dict(fields.get("chapter_branch_context_json") or {}),
            prior_node_context_json=dict(fields.get("prior_node_context_json") or {}),
            target_node_context_json=dict(fields.get("target_node_context_json") or {}),
            next_node_context_json=dict(fields.get("next_node_context_json") or {}),
            ksa_context_json=dict(fields.get("ksa_context_json") or {}),
            readiness_context_json=dict(fields.get("readiness_context_json") or {}),
            derived_assumptions_json=dict(fields.get("derived_assumptions_json") or {}),
            created_at=now,
            updated_at=now,
        )
        return self._saved


def test_node_context_generation_for_start_node() -> None:
    repo = _RepoStub()
    repo.progress_map = {}
    engine = LearningNodeContextEngine(repo)  # type: ignore[arg-type]
    record = engine.recompute_for_node(
        user_id=7,
        learning_path=_path(),
        definition=_definition(),
        node_id="n1",
        generation_reason="test",
    )
    assert record.prior_node_context_json["is_start_node"] is True
    assert record.target_node_context_json["node_type"] == "learning_unit"
    assert record.next_node_context_json["direct_successors"][0]["node_id"] == "n2"


def test_node_context_generation_for_non_start_node_includes_prior_and_ksa() -> None:
    repo = _RepoStub()
    engine = LearningNodeContextEngine(repo)  # type: ignore[arg-type]
    record = engine.recompute_for_node(
        user_id=7,
        learning_path=_path(),
        definition=_definition(),
        node_id="n2",
        generation_reason="test",
    )
    prior = record.prior_node_context_json
    assert prior["is_start_node"] is False
    assert "n1" in prior["completed_prior_required_node_ids"]
    ksa = record.ksa_context_json
    assert ksa["has_ksa_profile"] is True
    assert any(item["topic"] == "digital_craft" for item in ksa["topic_states"])
    readiness = record.readiness_context_json
    assert "likely_ready" in readiness
    assert "estimated_support_intensity" in readiness
