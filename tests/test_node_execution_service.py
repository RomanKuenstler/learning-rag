from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from services.common.models import LearningPath, UserAccount
from services.retriever.services.course_files import CourseDefinition, CourseNodeDefinition
from services.retriever.services.node_execution import LearningNodeExecutionService


def _user() -> UserAccount:
    now = datetime.now(timezone.utc)
    return UserAccount(
        id=7,
        username="anna",
        displayname="Anna",
        password_hash="hash",
        role="user",
        status="active",
        force_password_change=False,
        created_at=now,
        updated_at=now,
    )


def _path() -> LearningPath:
    now = datetime.now(timezone.utc)
    return LearningPath(
        id="course-x",
        scope="user",
        owner_user_id=7,
        title="DevOps Course",
        description="",
        subject="DevOps",
        difficulty_level="intermediate",
        estimated_duration_minutes=120,
        status="published",
        schema_version=2,
        skilltree_definition={},
        created_at=now,
        updated_at=now,
    )


def _definition() -> CourseDefinition:
    return CourseDefinition.model_validate(
        {
            "schema_version": 2,
            "source_schema_version": 2,
            "id": "course-x",
            "title": "DevOps Course",
            "description": "",
            "scope": "user",
            "owner_user_id": 7,
            "subject": "DevOps",
            "difficulty_level": "intermediate",
            "estimated_duration_minutes": 120,
            "status": "published",
            "allowed_file_ids": [],
            "allowed_tags": [],
            "chapters": [{"id": "c1", "title": "C1", "description": "", "order_index": 0, "metadata": {}}],
            "branches": [{"id": "b1", "title": "B1", "description": "", "required": True, "metadata": {}}],
            "nodes": [
                {
                    "id": "n1",
                    "title": "Intro",
                    "description": "",
                    "type": "learning_unit",
                    "chapter_id": "c1",
                    "branch_id": "b1",
                    "required": True,
                    "prerequisites": {"requires_all": [], "requires_any": [], "recommended": []},
                    "completion_mode": "lesson_complete",
                    "layout": {"x": 0, "y": 0},
                    "metadata": {"topics": ["linux", "networking"]},
                    "display": {},
                    "ksa": [{"dimension": "K", "topic": "information_technology"}],
                    "unlocks": {"node_ids": ["n2"], "branch_ids": [], "recommended_next_node_ids": []},
                    "rewards": {"estimated_ksa_gain": {}, "effort_score": None, "reward_tags": []},
                    "retrospective_hooks": {"retrospective_after": False, "review_recommended": False, "recap_checkpoint_available": False},
                    "ksa_hooks": {"mini_assessment_available": False, "recommended_reassessment_topics": [], "unlocks_deeper_refinement": False},
                    "remediation": {"is_remediation_node": False, "recommended_if_failed_node_ids": [], "supports_review_for_node_ids": []},
                    "adaptive_unlock": {"ksa_thresholds": [], "requires_branch_completion_ids": [], "requires_checkpoint_node_ids": [], "requires_review_recommended": False, "recommended_only": False},
                },
                {
                    "id": "n2",
                    "title": "Quiz",
                    "description": "",
                    "type": "quiz",
                    "chapter_id": "c1",
                    "branch_id": "b1",
                    "required": True,
                    "prerequisites": {"requires_all": ["n1"], "requires_any": [], "recommended": []},
                    "completion_mode": "quiz_pass",
                    "layout": {"x": 1, "y": 0},
                    "metadata": {"pass_threshold": 0.7, "topics": ["containers", "ci/cd"]},
                    "display": {},
                    "ksa": [{"dimension": "S", "topic": "digital_craft"}],
                    "unlocks": {"node_ids": ["n3"], "branch_ids": [], "recommended_next_node_ids": []},
                    "rewards": {"estimated_ksa_gain": {}, "effort_score": None, "reward_tags": []},
                    "retrospective_hooks": {"retrospective_after": False, "review_recommended": False, "recap_checkpoint_available": False},
                    "ksa_hooks": {"mini_assessment_available": False, "recommended_reassessment_topics": [], "unlocks_deeper_refinement": False},
                    "remediation": {"is_remediation_node": False, "recommended_if_failed_node_ids": [], "supports_review_for_node_ids": []},
                    "adaptive_unlock": {"ksa_thresholds": [], "requires_branch_completion_ids": [], "requires_checkpoint_node_ids": [], "requires_review_recommended": False, "recommended_only": False},
                },
                {
                    "id": "n3",
                    "title": "Gate",
                    "description": "",
                    "type": "unlock_gate",
                    "chapter_id": "c1",
                    "branch_id": "b1",
                    "required": True,
                    "prerequisites": {"requires_all": ["n2"], "requires_any": [], "recommended": []},
                    "completion_mode": "gate_unlock",
                    "layout": {"x": 2, "y": 0},
                    "metadata": {},
                    "display": {},
                    "ksa": [],
                    "unlocks": {"node_ids": [], "branch_ids": [], "recommended_next_node_ids": []},
                    "rewards": {"estimated_ksa_gain": {}, "effort_score": None, "reward_tags": []},
                    "retrospective_hooks": {"retrospective_after": False, "review_recommended": False, "recap_checkpoint_available": False},
                    "ksa_hooks": {"mini_assessment_available": False, "recommended_reassessment_topics": [], "unlocks_deeper_refinement": False},
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
            "metadata": {},
        }
    )


class RepoStub:
    def __init__(self) -> None:
        self.progress = {"n1": "completed", "n2": "available", "n3": "available"}
        self.attempts = {}
        self._idx = 0
        now = datetime.now(timezone.utc)
        self.profile = SimpleNamespace(
            profile_json={
                "knowledge": {"information_technology": 3},
                "skills": {"digital_craft": 3},
                "abilities": {},
                "assessment_details": {"derived": {"learning_speed_multiplier": 1.0}},
                "drill_state": {},
            },
            updated_at=now,
        )

    def list_user_learning_node_progress(self, *, user_id: int, learning_path_id: str):
        _ = (user_id, learning_path_id)
        return [SimpleNamespace(node_id=k, status=v) for k, v in self.progress.items()]

    def upsert_user_learning_node_progress(self, *, user_id: int, learning_path_id: str, node_id: str, status: str, started_at=None, completed_at=None):
        _ = (user_id, learning_path_id, started_at, completed_at)
        self.progress[node_id] = status
        return SimpleNamespace(node_id=node_id, status=status)

    def get_user_ksa_profile(self, user_id: int):
        _ = user_id
        return self.profile

    def upsert_user_ksa_profile(self, *, user_id: int, has_assessment: bool, assessment_version: str, profile_json: dict):
        _ = (user_id, has_assessment, assessment_version)
        self.profile.profile_json = profile_json
        return self.profile

    def create_user_learning_node_execution_attempt(self, payload: dict):
        self._idx += 1
        now = datetime.now(timezone.utc)
        attempt = SimpleNamespace(
            id=f"a-{self._idx}",
            user_id=payload["user_id"],
            learning_path_id=payload["learning_path_id"],
            node_id=payload["node_id"],
            node_type=payload["node_type"],
            status=payload["status"],
            generation_reason=payload["generation_reason"],
            package_json=dict(payload.get("package_json") or {}),
            responses_json=dict(payload.get("responses_json") or {}),
            result_json=dict(payload.get("result_json") or {}),
            context_snapshot_json=dict(payload.get("context_snapshot_json") or {}),
            source_node_window_json=list(payload.get("source_node_window_json") or []),
            started_at=payload.get("started_at", now),
            completed_at=None,
            created_at=now,
            updated_at=now,
        )
        self.attempts[attempt.id] = attempt
        return attempt

    def get_user_learning_node_execution_attempt(self, *, user_id: int, attempt_id: str):
        attempt = self.attempts.get(attempt_id)
        if attempt is None or attempt.user_id != user_id:
            return None
        return attempt

    def update_user_learning_node_execution_attempt(self, *, user_id: int, attempt_id: str, fields: dict):
        attempt = self.get_user_learning_node_execution_attempt(user_id=user_id, attempt_id=attempt_id)
        if attempt is None:
            return None
        for key, value in fields.items():
            attr = {
                "package_json": "package_json",
                "responses_json": "responses_json",
                "result_json": "result_json",
                "status": "status",
                "completed_at": "completed_at",
            }.get(key, key)
            setattr(attempt, attr, value)
        attempt.updated_at = datetime.now(timezone.utc)
        return attempt


def llm_stub(messages: list[tuple[str, str]]) -> str:
    text = "\n".join(content for _, content in messages)
    if "key topics" in text:
        topics = [{"label": f"Topic {idx}", "related_node_ids": ["n1"], "related_ksa": {"dimension": "S", "topic": "digital_craft"}, "why": "test"} for idx in range(1, 9)]
        return json_dumps({"topics": topics})
    if "mc_questions" in text and "free_text_questions" in text:
        return json_dumps({})
    return json_dumps(
        {
            "questions": [
                {"type": "REVERSE_DEFINITION", "question": "Q1", "correct_answer": "A1", "distractors": ["B1", "C1"]},
                {"type": "SPOT_THE_FLAW", "question": "Q2", "correct_answer": "A2", "distractors": ["B2", "C2"]},
                {"type": "POWER_SPRINT", "question": "Q3", "correct_answer": "A3", "distractors": ["B3", "C3"]},
                {"type": "ANALOGY_MATCH", "question": "Q4", "correct_answer": "A4", "distractors": ["B4", "C4"]},
            ]
        }
    )


def json_dumps(payload: dict) -> str:
    import json
    return json.dumps(payload)


def _context() -> dict:
    return {
        "prior_node_context": {"prior_topic_summary": ["linux"], "prior_concept_summary": ["networking"], "completed_relevant_nodes": []},
        "target_node_context": {"node_topics": ["containers"], "node_concepts": ["pipelines"]},
        "ksa_context": {"topic_states": [{"topic": "digital_craft", "level": 3, "confidence": 0.7}]},
    }


def test_assessment_hook_start_generates_8_topics_and_rounds() -> None:
    repo = RepoStub()
    service = LearningNodeExecutionService(repo, llm_invoke=llm_stub)  # type: ignore[arg-type]
    definition = _definition()
    node = CourseNodeDefinition.model_validate(
        {
            **next(item.model_dump() for item in definition.nodes if item.id == "n2"),
            "id": "a-hook",
            "type": "assessment_hook",
            "completion_mode": "assessment_threshold",
            "prerequisites": {"requires_all": ["n1"], "requires_any": [], "recommended": []},
        }
    )
    definition = definition.model_copy(update={"nodes": [definition.nodes[0], node, definition.nodes[2]], "entry_node_ids": ["n1"]})
    result = service.start(user=_user(), learning_path=_path(), definition=definition, node=node, node_context=_context())
    topics = list(result.attempt.package_json.get("generated_topics") or [])
    rounds = list(result.attempt.package_json.get("rounds") or [])
    assert 8 <= len(topics) <= 16
    assert len(rounds) == len(topics)


def test_quiz_start_generates_required_package_shape() -> None:
    repo = RepoStub()
    service = LearningNodeExecutionService(repo, llm_invoke=llm_stub)  # type: ignore[arg-type]
    definition = _definition()
    node = next(item for item in definition.nodes if item.id == "n2")
    result = service.start(user=_user(), learning_path=_path(), definition=definition, node=node, node_context=_context())
    package = dict(result.attempt.package_json or {})
    assert len(list(package.get("mc_questions") or [])) == 12
    assert len(list(package.get("free_text_questions") or [])) == 2
    assert len(list(package.get("deep_dive_rounds") or [])) == 3


def test_unlock_gate_start_auto_completes_when_prereqs_met() -> None:
    repo = RepoStub()
    repo.progress["n2"] = "completed"
    service = LearningNodeExecutionService(repo, llm_invoke=llm_stub)  # type: ignore[arg-type]
    definition = _definition()
    node = next(item for item in definition.nodes if item.id == "n3")
    result = service.start(user=_user(), learning_path=_path(), definition=definition, node=node, node_context=_context())
    assert result.auto_completed is True
    assert repo.progress["n3"] == "completed"
