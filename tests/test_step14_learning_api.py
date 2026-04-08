from __future__ import annotations

from fastapi.testclient import TestClient

from services.common.models import UserAccount
from services.retriever.api.app import create_app
from services.retriever.api.dependencies import get_app_auth_context, get_auth_context, get_retriever_service
from services.retriever.auth import AuthContext


class LearningApiStubService:
    def __init__(self) -> None:
        self.student_user = UserAccount(
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
        self.admin_user = UserAccount(
            id=1,
            username="admin",
            displayname="Admin",
            password_hash="hash",
            role="admin",
            status="active",
            force_password_change=False,
            created_at="2026-04-04T00:00:00Z",
            updated_at="2026-04-04T00:00:00Z",
        )

    def create_chat(self, user: UserAccount):
        if user.role == "student":
            raise PermissionError("Students can only use learning mode")
        return {
            "id": "chat-1",
            "chat_name": "chat-1",
            "chat_type": "normal",
            "learning_path_id": None,
            "gpt_id": None,
            "is_archived": False,
            "created_at": "2026-04-04T00:00:00Z",
            "updated_at": "2026-04-04T00:00:00Z",
        }

    def list_gpts(self, user: UserAccount):
        if user.role == "student":
            raise PermissionError("Students cannot create or use GPTs")
        return []

    def list_learning_paths(self, *_args, **_kwargs):
        return {
            "paths": [
                {
                    "id": "lp-1",
                    "scope": "global",
                    "owner_user_id": None,
                    "title": "Docker Basics",
                    "description": "Intro path",
                    "subject": "Docker",
                    "difficulty_level": "beginner",
                    "estimated_duration_minutes": 90,
                    "status": "published",
                    "allowed_file_ids": [1],
                    "allowed_tags": ["docker"],
                    "modules": [],
                    "can_edit": True,
                    "can_delete": True,
                    "created_at": "2026-04-04T00:00:00Z",
                    "updated_at": "2026-04-04T00:00:00Z",
                }
            ]
        }

    def list_courses(self, *_args, **_kwargs):
        return {
            "courses": [
                {
                    "id": "lp-1",
                    "title": "Docker Basics",
                    "description": "Intro path",
                    "scope": "global",
                    "owner_user_id": None,
                    "owner_username": None,
                    "owner_displayname": None,
                    "status": "published",
                    "subject": "Docker",
                    "difficulty_level": "beginner",
                    "module_count": 1,
                    "lesson_count": 2,
                    "created_at": "2026-04-04T00:00:00Z",
                    "updated_at": "2026-04-04T00:00:00Z",
                }
            ],
            "total": 1,
        }

    def get_course_template(self):
        return {
            "file_name": "path-template.json",
            "template": {"schema_version": 1, "id": "course-template", "title": "Template"},
        }

    def get_ksa_profile(self, user: UserAccount):
        if user.role == "student":
            return {
                "user_id": user.id,
                "has_assessment": False,
                "profile_source": "student_default_baseline",
                "scale_min": 1,
                "scale_max": 5,
                "dreyfus_levels": ["Novice", "Advanced", "Competent", "Proficient", "Expert"],
                "knowledge": {
                    "stem_fundamentals": 2,
                    "information_technology": 2,
                    "humanities_social_sciences": 3,
                    "languages_linguistics": 3,
                    "business_commerce": 2,
                    "legal_ethics": 1,
                    "health_wellness": 2,
                },
                "skills": {
                    "literacy_numeracy": 3,
                    "digital_craft": 2,
                    "strategic_execution": 2,
                    "operational_skills": 2,
                    "relational_skills": 3,
                    "research_inquiry": 2,
                },
                "abilities": {
                    "quantitative_reasoning": 2,
                    "verbal_comprehension": 3,
                    "spatial_visualization": 2,
                    "executive_function": 2,
                    "sensory_perceptual": 3,
                    "social_emotional_capacity": 3,
                    "divergent_thinking": 3,
                },
                "updated_at": None,
            }
        return {
            "user_id": user.id,
            "has_assessment": False,
            "profile_source": "placeholder_baseline",
            "scale_min": 1,
            "scale_max": 5,
            "dreyfus_levels": ["Novice", "Advanced", "Competent", "Proficient", "Expert"],
            "knowledge": {
                "stem_fundamentals": 2,
                "information_technology": 2,
                "humanities_social_sciences": 2,
                "languages_linguistics": 2,
                "business_commerce": 2,
                "legal_ethics": 2,
                "health_wellness": 2,
            },
            "skills": {
                "literacy_numeracy": 2,
                "digital_craft": 2,
                "strategic_execution": 2,
                "operational_skills": 2,
                "relational_skills": 2,
                "research_inquiry": 2,
            },
            "abilities": {
                "quantitative_reasoning": 2,
                "verbal_comprehension": 2,
                "spatial_visualization": 2,
                "executive_function": 2,
                "sensory_perceptual": 2,
                "social_emotional_capacity": 2,
                "divergent_thinking": 2,
            },
            "updated_at": None,
        }

    def import_courses_from_uploads(self, user: UserAccount, _uploads, _scopes_by_file_raw):
        if user.role == "student":
            raise PermissionError("Students cannot create learning paths")
        return {
            "imported_count": 1,
            "failed_count": 0,
            "results": [
                {
                    "file_name": "course.json",
                    "scope": "global",
                    "success": True,
                    "course_id": "lp-2",
                    "title": "Admin Path",
                    "error": None,
                }
            ],
        }

    def create_learning_path(self, user: UserAccount, _payload):
        if user.role == "student":
            raise PermissionError("Students cannot create learning paths")
        path = self.list_learning_paths()["paths"][0].copy()
        path["id"] = "lp-2"
        return path

    def list_library_files(self, *_args, **_kwargs):
        return {
            "files": [],
            "summary": {"total_files": 0, "embedded_files": 0, "total_chunks": 0},
            "allowed_extensions": [".md", ".pdf"],
            "max_upload_files": 5,
            "upload_max_file_size_mb": 50,
            "default_tag": "default",
        }


def build_client(*, student: bool) -> TestClient:
    app = create_app()
    service = LearningApiStubService()
    user = service.student_user if student else service.admin_user
    auth = AuthContext(
        user=user,
        session=type("Session", (), {"id": "session-1", "expires_at": "2026-04-04T02:00:00Z", "max_expires_at": "2026-04-04T12:00:00Z"})(),
        token="token",
    )
    app.dependency_overrides[get_retriever_service] = lambda: service
    app.dependency_overrides[get_auth_context] = lambda: auth
    app.dependency_overrides[get_app_auth_context] = lambda: auth
    return TestClient(app)


def test_student_is_forbidden_from_normal_chat_and_gpt_routes() -> None:
    client = build_client(student=True)
    chat_response = client.post("/api/chats")
    assert chat_response.status_code == 403
    assert "learning mode" in chat_response.json()["detail"].lower()

    gpt_response = client.get("/api/gpts")
    assert gpt_response.status_code == 403
    assert "gpts" in gpt_response.json()["detail"].lower()


def test_learning_path_routes_available_and_authoring_restricted_for_student() -> None:
    student_client = build_client(student=True)
    list_response = student_client.get("/api/learning-paths")
    assert list_response.status_code == 200
    assert list_response.json()["paths"][0]["title"] == "Docker Basics"

    create_response = student_client.post(
        "/api/learning-paths",
        json={
            "scope": "user",
            "title": "Student Path",
            "description": "",
            "subject": "",
            "difficulty_level": "",
            "estimated_duration_minutes": None,
            "status": "draft",
            "allowed_file_ids": [],
            "allowed_tags": [],
        },
    )
    assert create_response.status_code == 403

    admin_client = build_client(student=False)
    admin_create = admin_client.post(
        "/api/learning-paths",
        json={
            "scope": "global",
            "title": "Admin Path",
            "description": "",
            "subject": "",
            "difficulty_level": "",
            "estimated_duration_minutes": 60,
            "status": "published",
            "allowed_file_ids": [1],
            "allowed_tags": ["docker"],
        },
    )
    assert admin_create.status_code == 200
    assert admin_create.json()["id"] == "lp-2"


def test_student_can_access_library_api() -> None:
    client = build_client(student=True)
    response = client.get("/api/library/files")
    assert response.status_code == 200


def test_courses_routes_available() -> None:
    client = build_client(student=False)
    list_response = client.get("/api/courses?sort=updated_desc")
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    template_response = client.get("/api/courses/template")
    assert template_response.status_code == 200
    assert template_response.json()["file_name"] == "path-template.json"


def test_ksa_profile_route_uses_student_default_values() -> None:
    student_client = build_client(student=True)
    response = student_client.get("/api/learning-profile/ksa")
    assert response.status_code == 200
    payload = response.json()
    assert payload["profile_source"] == "student_default_baseline"
    assert payload["knowledge"]["legal_ethics"] == 1
    assert payload["skills"]["literacy_numeracy"] == 3
    assert payload["abilities"]["divergent_thinking"] == 3
    assert payload["dreyfus_levels"] == ["Novice", "Advanced", "Competent", "Proficient", "Expert"]
