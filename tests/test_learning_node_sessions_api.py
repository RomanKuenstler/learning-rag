from __future__ import annotations

from fastapi.testclient import TestClient

from services.common.models import UserAccount
from services.retriever.api.app import create_app
from services.retriever.api.dependencies import get_app_auth_context, get_auth_context, get_retriever_service
from services.retriever.auth import AuthContext


class LearningNodeSessionApiStub:
    def __init__(self) -> None:
        self.user = UserAccount(
            id=7,
            username="student1",
            displayname="Student One",
            password_hash="hash",
            role="student",
            status="active",
            force_password_change=False,
            created_at="2026-04-11T00:00:00Z",
            updated_at="2026-04-11T00:00:00Z",
        )
        self.sessions = {
            "sess-1": {
                "id": "sess-1",
                "user_id": 7,
                "learning_path_id": "course-1",
                "node_id": "node-1",
                "node_type": "learning_unit",
                "route_path": "/learning/nodes/sess-1",
                "node_title": "Containers Basics",
                "course_title": "Docker Fundamentals",
                "status": "created",
                "is_archived": False,
                "is_deleted": False,
                "is_completed": False,
                "started_at": None,
                "completed_at": None,
                "last_opened_at": None,
                "created_at": "2026-04-11T00:00:00Z",
                "updated_at": "2026-04-11T00:00:00Z",
            },
            "sess-2": {
                "id": "sess-2",
                "user_id": 7,
                "learning_path_id": "course-1",
                "node_id": "node-2",
                "node_type": "practice",
                "route_path": "/learning/nodes/sess-2",
                "node_title": "Compose Practice",
                "course_title": "Docker Fundamentals",
                "status": "in_progress",
                "is_archived": True,
                "is_deleted": False,
                "is_completed": False,
                "started_at": "2026-04-11T00:05:00Z",
                "completed_at": None,
                "last_opened_at": "2026-04-11T00:06:00Z",
                "created_at": "2026-04-11T00:05:00Z",
                "updated_at": "2026-04-11T00:06:00Z",
            },
        }

    def list_learning_node_sessions(self, _user: UserAccount):
        return {
            "sessions": [
                value
                for value in self.sessions.values()
                if not value["is_archived"] and not value["is_deleted"]
            ]
        }

    def list_archived_learning_node_sessions(self, _user: UserAccount):
        return {
            "sessions": [
                value
                for value in self.sessions.values()
                if value["is_archived"] and not value["is_deleted"]
            ]
        }

    def ensure_learning_node_session(self, _user: UserAccount, learning_path_id: str, node_id: str):
        for value in self.sessions.values():
            if value["learning_path_id"] == learning_path_id and value["node_id"] == node_id:
                value["is_deleted"] = False
                value["is_archived"] = False
                return value
        created = {
            "id": "sess-new",
            "user_id": 7,
            "learning_path_id": learning_path_id,
            "node_id": node_id,
            "node_type": "learning_unit",
            "route_path": "/learning/nodes/sess-new",
            "node_title": "New Node",
            "course_title": "Docker Fundamentals",
            "status": "created",
            "is_archived": False,
            "is_deleted": False,
            "is_completed": False,
            "started_at": None,
            "completed_at": None,
            "last_opened_at": None,
            "created_at": "2026-04-11T01:00:00Z",
            "updated_at": "2026-04-11T01:00:00Z",
        }
        self.sessions["sess-new"] = created
        return created

    def get_learning_node_session(self, _user: UserAccount, session_id: str, *, mark_opened: bool = False):
        record = self.sessions.get(session_id)
        if record is None:
            return None
        if mark_opened and record["status"] == "created":
            record["status"] = "in_progress"
            record["started_at"] = "2026-04-11T01:10:00Z"
        return record

    def archive_learning_node_session(self, _user: UserAccount, session_id: str):
        record = self.sessions.get(session_id)
        if record is None:
            return None
        record["is_archived"] = True
        return record

    def unarchive_learning_node_session(self, _user: UserAccount, session_id: str):
        record = self.sessions.get(session_id)
        if record is None:
            return None
        record["is_archived"] = False
        return record

    def soft_delete_learning_node_session(self, _user: UserAccount, session_id: str):
        record = self.sessions.get(session_id)
        if record is None:
            return None
        record["is_deleted"] = True
        record["is_archived"] = False
        return record

    def reset_learning_node_session(self, _user: UserAccount, session_id: str):
        return self.sessions.get(session_id)

    def download_learning_node_session(self, _user: UserAccount, session_id: str):
        record = self.sessions.get(session_id)
        if record is None:
            return None
        return {"session": record, "message": "Download is not implemented yet."}


def build_client(stub: LearningNodeSessionApiStub) -> TestClient:
    app = create_app()

    def override_service() -> LearningNodeSessionApiStub:
        return stub

    def override_auth() -> AuthContext:
        return AuthContext(user=stub.user, session=None, token="token", refreshed_token=None)

    app.dependency_overrides[get_retriever_service] = override_service
    app.dependency_overrides[get_auth_context] = override_auth
    app.dependency_overrides[get_app_auth_context] = override_auth
    return TestClient(app)


def test_learning_node_sessions_list_archive_soft_delete_and_restore() -> None:
    stub = LearningNodeSessionApiStub()
    client = build_client(stub)

    active = client.get("/api/learning-node-sessions")
    assert active.status_code == 200
    assert [item["id"] for item in active.json()["sessions"]] == ["sess-1"]

    archived = client.get("/api/learning-node-sessions/archived")
    assert archived.status_code == 200
    assert [item["id"] for item in archived.json()["sessions"]] == ["sess-2"]

    deleted = client.patch("/api/learning-node-sessions/sess-1/delete")
    assert deleted.status_code == 200
    assert deleted.json()["is_deleted"] is True

    active_after_delete = client.get("/api/learning-node-sessions")
    assert active_after_delete.status_code == 200
    assert active_after_delete.json()["sessions"] == []

    restored = client.post("/api/learning-paths/course-1/nodes/node-1/session")
    assert restored.status_code == 200
    assert restored.json()["id"] == "sess-1"
    assert restored.json()["is_deleted"] is False


def test_learning_node_session_open_archive_and_download() -> None:
    stub = LearningNodeSessionApiStub()
    client = build_client(stub)

    opened = client.get("/api/learning-node-sessions/sess-1?mark_opened=true")
    assert opened.status_code == 200
    assert opened.json()["status"] == "in_progress"

    archived = client.patch("/api/learning-node-sessions/sess-1/archive")
    assert archived.status_code == 200
    assert archived.json()["is_archived"] is True

    unarchived = client.patch("/api/learning-node-sessions/sess-1/unarchive")
    assert unarchived.status_code == 200
    assert unarchived.json()["is_archived"] is False

    downloaded = client.get("/api/learning-node-sessions/sess-1/download")
    assert downloaded.status_code == 200
    assert downloaded.json()["session"]["id"] == "sess-1"
    assert "not implemented" in downloaded.json()["message"].lower()
