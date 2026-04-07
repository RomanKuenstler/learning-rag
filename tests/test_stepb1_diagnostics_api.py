from __future__ import annotations

from fastapi.testclient import TestClient

from services.common.models import UserAccount
from services.retriever.api.app import create_app
from services.retriever.api.dependencies import get_app_auth_context, get_auth_context, get_retriever_service
from services.retriever.auth import AuthContext


class DiagnosticsApiStubService:
    def __init__(self) -> None:
        self.attempt = {
            "attempt": {
                "attempt_id": "attempt-1",
                "status": "in_progress",
                "definition_versions": {"LAA": "1.1", "MOA": "1.0", "LTA": "1.0"},
                "started_at": "2026-04-04T00:00:00Z",
                "completed_at": None,
                "is_latest": True,
            },
            "answers": {"LAA": {}, "MOA": {}, "LTA": {}},
            "result": None,
        }

    def list_diagnostic_definitions(self):
        return {
            "definitions": [
                {"id": "diagnostic-laa", "type": "LAA", "title": "LAA", "version": "1.1", "sections": []},
                {"id": "diagnostic-moa", "type": "MOA", "title": "MOA", "version": "1.0", "sections": []},
                {"id": "diagnostic-lta", "type": "LTA", "title": "LTA", "version": "1.0", "sections": []},
            ]
        }

    def get_diagnostic_definition(self, diagnostic_type: str):
        for item in self.list_diagnostic_definitions()["definitions"]:
            if item["type"] == diagnostic_type:
                return item
        return None

    def start_diagnostic_attempt(self, _user: UserAccount):
        return {
            "attempt_id": "attempt-1",
            "status": "in_progress",
            "definition_versions": {"LAA": "1.1", "MOA": "1.0", "LTA": "1.0"},
            "started_at": "2026-04-04T00:00:00Z",
        }

    def list_diagnostic_attempts(self, _user: UserAccount):
        return [self.attempt["attempt"]]

    def get_latest_diagnostic_attempt(self, _user: UserAccount):
        return self.attempt

    def get_diagnostic_attempt(self, _user: UserAccount, attempt_id: str):
        return self.attempt if attempt_id == "attempt-1" else None

    def upsert_diagnostic_answers(self, _user: UserAccount, attempt_id: str, payload):
        if attempt_id != "attempt-1":
            return None
        for item in payload.answers:
            self.attempt["answers"].setdefault(payload.diagnostic_type, {})[item.question_id] = item.value
        return self.attempt

    def complete_diagnostic_attempt(self, _user: UserAccount, attempt_id: str):
        if attempt_id != "attempt-1":
            return None
        self.attempt["attempt"]["status"] = "completed"
        self.attempt["result"] = {"LAA": {"normalized": {}}, "MOA": {"normalized": {}}, "LTA": {"normalized": {}}}
        return {"attempt_id": "attempt-1", "result": self.attempt["result"]}

    def create_learning_state_check(self, user: UserAccount, payload):
        return {
            "id": 1,
            "user_id": user.id,
            "chat_id": payload.chat_id,
            "mood": payload.mood,
            "perceived_difficulty": payload.perceived_difficulty,
            "needs_pause_or_input": payload.needs_pause_or_input,
            "preferred_format": payload.preferred_format,
            "notes": payload.notes,
            "created_at": "2026-04-04T00:00:00Z",
        }

    def list_learning_state_checks(self, user: UserAccount, limit: int = 20):
        _ = user
        _ = limit
        return []

    def create_explanation_feedback(self, user: UserAccount, payload):
        return {
            "id": 1,
            "user_id": user.id,
            "message_id": payload.message_id,
            "rating": payload.rating,
            "feedback_text": payload.feedback_text,
            "re_explain_requested": payload.re_explain_requested,
            "created_at": "2026-04-04T00:00:00Z",
        }


def build_client() -> TestClient:
    app = create_app()
    service = DiagnosticsApiStubService()
    user = UserAccount(
        id=5,
        username="user5",
        displayname="User 5",
        password_hash="hash",
        role="user",
        status="active",
        force_password_change=False,
        created_at="2026-04-04T00:00:00Z",
        updated_at="2026-04-04T00:00:00Z",
    )
    auth = AuthContext(
        user=user,
        session=type("Session", (), {"id": "session-1", "expires_at": "2026-04-04T02:00:00Z", "max_expires_at": "2026-04-04T12:00:00Z"})(),
        token="token",
    )
    app.dependency_overrides[get_retriever_service] = lambda: service
    app.dependency_overrides[get_auth_context] = lambda: auth
    app.dependency_overrides[get_app_auth_context] = lambda: auth
    return TestClient(app)


def test_diagnostics_attempt_flow_routes() -> None:
    client = build_client()

    assert client.get("/api/diagnostics/definitions").status_code == 200
    assert client.post("/api/diagnostics/attempts").status_code == 200

    save = client.put(
        "/api/diagnostics/attempts/attempt-1/answers",
        json={"diagnostic_type": "LAA", "answers": [{"question_id": "laa_q001", "value": "o1"}]},
    )
    assert save.status_code == 200
    assert save.json()["answers"]["LAA"]["laa_q001"] == "o1"

    complete = client.post("/api/diagnostics/attempts/attempt-1/complete")
    assert complete.status_code == 200
    assert complete.json()["attempt_id"] == "attempt-1"


def test_state_check_and_feedback_routes() -> None:
    client = build_client()

    state = client.post(
        "/api/learning-state-checks",
        json={
            "mood": "focused",
            "perceived_difficulty": "medium",
            "needs_pause_or_input": "input",
            "preferred_format": "dialogue",
            "notes": "ok",
        },
    )
    assert state.status_code == 200
    assert state.json()["mood"] == "focused"

    feedback = client.post(
        "/api/explanation-feedback",
        json={"message_id": 12, "rating": 4, "feedback_text": "good", "re_explain_requested": False},
    )
    assert feedback.status_code == 200
    assert feedback.json()["rating"] == 4
