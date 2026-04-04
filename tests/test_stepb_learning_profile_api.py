from __future__ import annotations

from copy import deepcopy

from fastapi.testclient import TestClient

from services.common.models import UserAccount
from services.retriever.api.app import create_app
from services.retriever.api.dependencies import get_app_auth_context, get_auth_context, get_retriever_service
from services.retriever.auth import AuthContext


DEFAULT_BUNDLE = {
    "preferences": {
        "preferred_pace": "balanced",
        "explanation_depth": "balanced",
        "examples_vs_theory": "balanced",
        "structure_preference": "balanced",
        "checkpoint_frequency": "medium",
        "encouragement_level": "balanced",
        "guidance_level": "balanced",
        "recap_frequency": "medium",
        "preferred_learning_format": "mixed",
        "custom_preference_note": "",
        "updated_at": None,
    },
    "context": {
        "education_background": "",
        "current_skill_areas": [],
        "interests": [],
        "professional_context": "",
        "current_reason_for_learning": "",
        "preferred_form_of_address": "",
        "learning_context_notes": "",
        "updated_at": None,
    },
    "goals": [],
    "diagnostics_status": "not_started",
}


class LearningProfileApiStubService:
    def __init__(self) -> None:
        self.bundles: dict[int, dict] = {}
        self.goal_counter = 0

    def _bundle(self, user_id: int) -> dict:
        if user_id not in self.bundles:
            self.bundles[user_id] = deepcopy(DEFAULT_BUNDLE)
        return self.bundles[user_id]

    def get_learning_profile_bundle(self, user: UserAccount):
        return self._bundle(user.id)

    def update_learning_preferences(self, user: UserAccount, payload):
        bundle = self._bundle(user.id)
        bundle["preferences"].update(payload.model_dump(exclude_unset=True))
        return bundle["preferences"]

    def update_learning_context(self, user: UserAccount, payload):
        bundle = self._bundle(user.id)
        bundle["context"].update(payload.model_dump(exclude_unset=True))
        return bundle["context"]

    def create_learning_goal(self, user: UserAccount, payload):
        self.goal_counter += 1
        goal = {
            "id": f"goal-{self.goal_counter}",
            "target_topic": payload.target_topic,
            "reason_for_learning": payload.reason_for_learning,
            "target_level": payload.target_level,
            "deadline": payload.deadline,
            "priority": payload.priority,
            "notes": payload.notes,
            "is_active": payload.is_active,
            "created_at": "2026-04-04T00:00:00Z",
            "updated_at": "2026-04-04T00:00:00Z",
        }
        bundle = self._bundle(user.id)
        bundle["goals"] = [goal] + [item for item in bundle["goals"] if item["id"] != goal["id"]]
        return goal

    def update_learning_goal(self, user: UserAccount, goal_id: str, payload):
        bundle = self._bundle(user.id)
        for index, goal in enumerate(bundle["goals"]):
            if goal["id"] == goal_id:
                updated = {**goal, **payload.model_dump(exclude_unset=True)}
                bundle["goals"][index] = updated
                return updated
        return None

    def delete_learning_goal(self, user: UserAccount, goal_id: str):
        bundle = self._bundle(user.id)
        for goal in bundle["goals"]:
            if goal["id"] == goal_id:
                bundle["goals"] = [item for item in bundle["goals"] if item["id"] != goal_id]
                return goal
        return None


def build_client(user: UserAccount, service: LearningProfileApiStubService | None = None) -> TestClient:
    app = create_app()
    active_service = service or LearningProfileApiStubService()
    auth = AuthContext(
        user=user,
        session=type("Session", (), {"id": "session-1", "expires_at": "2026-04-04T02:00:00Z", "max_expires_at": "2026-04-04T12:00:00Z"})(),
        token="token",
    )
    app.dependency_overrides[get_retriever_service] = lambda: active_service
    app.dependency_overrides[get_auth_context] = lambda: auth
    app.dependency_overrides[get_app_auth_context] = lambda: auth
    client = TestClient(app)
    client.state.stub_service = active_service
    return client


def test_student_can_read_and_update_declared_learning_profile() -> None:
    student = UserAccount(
        id=11,
        username="student",
        displayname="Student",
        password_hash="hash",
        role="student",
        status="active",
        force_password_change=False,
        created_at="2026-04-04T00:00:00Z",
        updated_at="2026-04-04T00:00:00Z",
    )
    client = build_client(student)

    get_response = client.get("/api/learning-profile")
    assert get_response.status_code == 200
    assert get_response.json()["diagnostics_status"] == "not_started"

    patch_response = client.patch(
        "/api/learning-profile/preferences",
        json={"preferred_pace": "fast", "guidance_level": "step_by_step"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["preferred_pace"] == "fast"


def test_invalid_preference_enum_is_rejected() -> None:
    user = UserAccount(
        id=2,
        username="user",
        displayname="User",
        password_hash="hash",
        role="user",
        status="active",
        force_password_change=False,
        created_at="2026-04-04T00:00:00Z",
        updated_at="2026-04-04T00:00:00Z",
    )
    client = build_client(user)

    response = client.patch(
        "/api/learning-profile/preferences",
        json={"preferred_pace": "turbo"},
    )
    assert response.status_code == 422


def test_learning_goals_are_user_scoped() -> None:
    user_a = UserAccount(
        id=101,
        username="alpha",
        displayname="Alpha",
        password_hash="hash",
        role="user",
        status="active",
        force_password_change=False,
        created_at="2026-04-04T00:00:00Z",
        updated_at="2026-04-04T00:00:00Z",
    )
    user_b = UserAccount(
        id=102,
        username="beta",
        displayname="Beta",
        password_hash="hash",
        role="user",
        status="active",
        force_password_change=False,
        created_at="2026-04-04T00:00:00Z",
        updated_at="2026-04-04T00:00:00Z",
    )

    shared_service = LearningProfileApiStubService()
    client_a = build_client(user_a, shared_service)
    create_response = client_a.post(
        "/api/learning-profile/goals",
        json={
            "target_topic": "Docker networking",
            "reason_for_learning": "Work migration",
            "target_level": "intermediate",
            "deadline": None,
            "priority": "high",
            "notes": "Focus on bridge and overlay",
            "is_active": True,
        },
    )
    assert create_response.status_code == 200
    goal_id = create_response.json()["id"]

    client_b = build_client(user_b, shared_service)
    update_response = client_b.patch(
        f"/api/learning-profile/goals/{goal_id}",
        json={"target_level": "advanced"},
    )
    assert update_response.status_code == 404

    delete_response = client_b.delete(f"/api/learning-profile/goals/{goal_id}")
    assert delete_response.status_code == 404
