from __future__ import annotations

from fastapi.testclient import TestClient

from services.retriever.api.app import create_app
from services.retriever.api.dependencies import get_app_auth_context, get_auth_context, get_retriever_service
from services.retriever.auth import AuthContext
from services.common.models import UserAccount
from services.retriever.schemas.chat import (
    AttachmentRead,
    ChatDownloadResponse,
    ChatRead,
    FilterFileRead,
    FilterTagRead,
    GptChatRead,
    GptConfigRead,
    GptDeleteResponse,
    GptFileSettingRead,
    GptPersonalizationRead,
    GptRead,
    GptSettingsRead,
    GptTagSettingRead,
    LibraryFileRead,
    LibraryListResponse,
    LibrarySummaryRead,
    MessageRead,
    PersonalizationRead,
    SettingsRead,
    SourceRead,
)


class StubRetrieverService:
    def __init__(self) -> None:
        self.user = UserAccount(
            id=1,
            username="admin",
            displayname="Admin User",
            password_hash="hash",
            role="admin",
            status="active",
            force_password_change=False,
            created_at="2026-03-29T00:00:00Z",
            updated_at="2026-03-29T00:00:00Z",
        )

    def create_chat(self, *_args, **_kwargs) -> ChatRead:
        return ChatRead(
            id="chat-1",
            chat_name="chat-abc123",
            gpt_id=None,
            is_archived=False,
            created_at="2026-03-29T00:00:00Z",
            updated_at="2026-03-29T00:00:00Z",
        )

    def list_chats(self, *_args, **_kwargs) -> list[ChatRead]:
        return [self.create_chat()]

    def get_chat(self, *_args, chat_id: str | None = None, **_kwargs) -> ChatRead | None:
        if chat_id is None and _args:
            chat_id = _args[-1]
        if chat_id != "chat-1":
            return None
        return self.create_chat()

    def rename_chat(self, *_args, chat_id: str | None = None, chat_name: str | None = None, **_kwargs) -> ChatRead | None:
        if chat_id is None and len(_args) >= 2:
            chat_id = _args[-2]
            chat_name = _args[-1]
        if chat_id != "chat-1":
            return None
        return ChatRead(
            id="chat-1",
            chat_name=chat_name or "Renamed chat",
            gpt_id=None,
            is_archived=False,
            created_at="2026-03-29T00:00:00Z",
            updated_at="2026-03-29T00:00:02Z",
        )

    def list_archived_chats(self, *_args, **_kwargs) -> list[ChatRead]:
        return [
            ChatRead(
                id="chat-2",
                chat_name="archived-chat",
                gpt_id=None,
                is_archived=True,
                created_at="2026-03-29T00:00:00Z",
                updated_at="2026-03-29T00:00:03Z",
            )
        ]

    def archive_chat(self, *_args, chat_id: str | None = None, **_kwargs) -> ChatRead | None:
        if chat_id is None and _args:
            chat_id = _args[-1]
        if chat_id != "chat-1":
            return None
        return ChatRead(
            id="chat-1",
            chat_name="chat-abc123",
            gpt_id=None,
            is_archived=True,
            created_at="2026-03-29T00:00:00Z",
            updated_at="2026-03-29T00:00:03Z",
        )

    def unarchive_chat(self, *_args, chat_id: str | None = None, **_kwargs) -> ChatRead | None:
        if chat_id is None and _args:
            chat_id = _args[-1]
        if chat_id != "chat-2":
            return None
        return ChatRead(
            id="chat-2",
            chat_name="archived-chat",
            gpt_id=None,
            is_archived=False,
            created_at="2026-03-29T00:00:00Z",
            updated_at="2026-03-29T00:00:04Z",
        )

    def delete_chat(self, *_args, chat_id: str | None = None, **_kwargs) -> ChatRead | None:
        if chat_id is None and _args:
            chat_id = _args[-1]
        if chat_id != "chat-1":
            return None
        return self.create_chat()

    def get_chat_messages(self, *_args, chat_id: str | None = None, **_kwargs) -> list[MessageRead]:
        if chat_id is None and _args:
            chat_id = _args[-1]
        if chat_id != "chat-1":
            return []
        return [
            MessageRead(
                id="2",
                chat_id="chat-1",
                gpt_id=None,
                role="assistant",
                content="Grounded answer",
                status="completed",
                has_attachments=False,
                created_at="2026-03-29T00:00:01Z",
                sources=[
                    SourceRead(
                        chunk_id="chunk-1",
                        file_name="manual.pdf",
                        file_path="/app/data/manual.pdf",
                        title="Storage",
                        chapter="Chapter 4",
                        section="Volumes",
                        page_number=18,
                        score=0.812,
                        tags=["docker"],
                    )
                ],
                attachments=[],
            )
        ]

    def send_message(
        self,
        *_args,
        chat_id: str | None = None,
        user_content: str | None = None,
        attachments: list[tuple[str, bytes]] | None = None,
        assistant_mode: str | None = None,
    ):
        if chat_id is None and len(_args) >= 3:
            chat_id = _args[1]
            user_content = _args[2]
        if attachments is None and len(_args) >= 4:
            attachments = _args[3]
        if chat_id != "chat-1":
            return None
        attachment_payload = [
            AttachmentRead(
                file_name="diagram.png",
                file_type="png",
                extraction_method="ocr",
                quality={"score": 0.91},
            )
        ]
        return {
            "chat_id": "chat-1",
            "user_message": MessageRead(
                id="1",
                chat_id="chat-1",
                gpt_id=None,
                role="user",
                content=user_content or "",
                status="completed",
                has_attachments=bool(attachments),
                created_at="2026-03-29T00:00:00Z",
                sources=[],
                attachments=attachment_payload if attachments else [],
            ),
            "assistant_message": MessageRead(
                id="2",
                chat_id="chat-1",
                gpt_id=None,
                role="assistant",
                content="Grounded answer",
                status="completed",
                has_attachments=False,
                created_at="2026-03-29T00:00:01Z",
                sources=[],
                attachments=[],
            ),
            "assistant_mode": assistant_mode or "simple",
            "sources": [
                SourceRead(
                    chunk_id="chunk-1",
                    file_name="manual.pdf",
                    file_path="/app/data/manual.pdf",
                    title="Storage",
                    chapter="Chapter 4",
                    section="Volumes",
                    page_number=18,
                    score=0.812,
                    tags=["docker"],
                )
            ],
            "attachments_used": attachment_payload if attachments else [],
        }

    def download_chat(self, *_args, chat_id: str | None = None, **_kwargs) -> ChatDownloadResponse | None:
        if chat_id is None and _args:
            chat_id = _args[-1]
        if chat_id != "chat-1":
            return None
        return ChatDownloadResponse(
            chat_id="chat-1",
            chat_name="chat-abc123",
            is_archived=False,
            created_at="2026-03-29T00:00:00Z",
            updated_at="2026-03-29T00:00:01Z",
            messages=[
                {
                    "role": "user",
                    "content": "hello",
                    "created_at": "2026-03-29T00:00:00Z",
                    "sources": [],
                    "attachments": [],
                },
                {
                    "role": "assistant",
                    "content": "Grounded answer",
                    "created_at": "2026-03-29T00:00:01Z",
                    "sources": [
                        {
                            "chunk_id": "chunk-1",
                            "file_name": "manual.pdf",
                            "file_path": "/app/data/manual.pdf",
                            "title": "Storage",
                            "chapter": "Chapter 4",
                            "section": "Volumes",
                            "page_number": 18,
                            "score": 0.812,
                            "tags": ["docker"],
                        }
                    ],
                    "attachments": [],
                },
            ],
        )

    def get_settings(self, *_args, **_kwargs) -> SettingsRead:
        return SettingsRead(
            chat_history_messages_count=5,
            max_similarities=8,
            min_similarities=2,
            similarity_score_threshold=0.7,
            default_assistant_mode="simple",
            available_assistant_modes=["simple", "refine", "thinking"],
        )

    def get_personalization(self, *_args, **_kwargs) -> PersonalizationRead:
        return PersonalizationRead(
            base_style="friendly",
            warm="more",
            enthusiastic="default",
            headers_and_lists="more",
            custom_instructions="Keep things practical.",
            nickname="Rik",
            occupation="Platform engineer",
            more_about_user="Prefers examples with Docker or Python.",
        )

    def update_personalization(self, *_args, payload=None, **_kwargs) -> PersonalizationRead:
        if payload is None and _args:
            payload = _args[-1]
        return PersonalizationRead(**payload.model_dump())

    def update_settings(self, *_args, payload=None, **_kwargs) -> SettingsRead:
        if payload is None and _args:
            payload = _args[-1]
        if payload.min_similarities > payload.max_similarities:
            raise ValueError("min similarities cannot be greater than max similarities")
        return SettingsRead(
            chat_history_messages_count=payload.chat_history_messages_count,
            max_similarities=payload.max_similarities,
            min_similarities=payload.min_similarities,
            similarity_score_threshold=payload.similarity_score_threshold,
            default_assistant_mode="simple",
            available_assistant_modes=["simple", "refine", "thinking"],
        )

    def list_library_files(self, *_args, **_kwargs) -> LibraryListResponse:
        return LibraryListResponse(
            files=[
                LibraryFileRead(
                    id=1,
                    file_name="manual.pdf",
                    file_path="/app/data/manual.pdf",
                    file_type="pdf",
                    extension=".pdf",
                    size_bytes=1024,
                    chunk_count=3,
                    tags=["docker"],
                    is_embedded=True,
                    is_enabled=True,
                    processing_status="processed",
                    updated_at="2026-03-29T00:00:00Z",
                )
            ],
            summary=LibrarySummaryRead(total_files=1, embedded_files=1, total_chunks=3),
            allowed_extensions=[".md", ".pdf"],
            max_upload_files=5,
            upload_max_file_size_mb=50,
            default_tag="default",
        )

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
                    "updated_at": "2026-03-29T00:00:00Z",
                    "created_at": "2026-03-29T00:00:00Z",
                }
            ],
            "total": 1,
        }

    def get_course_template(self):
        return {
            "file_name": "path-template.json",
            "template": {"schema_version": 1, "id": "course-template", "title": "Template"},
        }

    def import_courses_from_uploads(self, *_args, **_kwargs):
        return {
            "imported_count": 1,
            "failed_count": 0,
            "results": [
                {
                    "file_name": "course.json",
                    "scope": "global",
                    "success": True,
                    "course_id": "lp-1",
                    "title": "Docker Basics",
                    "error": None,
                }
            ],
        }

    def upload_library_files(self, *_args, uploads=None, tags_by_file_raw: str | None = None, **_kwargs):
        return {"files": self.list_library_files().files}

    def update_library_file(self, *_args, file_id: int | None = None, is_enabled: bool = True, **_kwargs):
        if file_id is None and _args:
            file_id = _args[-1]
        if file_id == 99 and not is_enabled:
            raise PermissionError("Global files cannot be disabled by non-admin users")
        if file_id != 1:
            return None
        record = self.list_library_files().files[0]
        return record.model_copy(update={"is_enabled": is_enabled})

    def delete_library_file(self, *_args, file_id: int | None = None, **_kwargs):
        if file_id is None and _args:
            file_id = _args[-1]
        if file_id != 1:
            return None
        return self.list_library_files().files[0]

    def list_user_file_filters(self, *_args, **_kwargs):
        return {
            "files": [
                FilterFileRead(
                    file_id=1,
                    file_name="manual.pdf",
                    file_path="/app/data/manual.pdf",
                    tags=["docker"],
                    global_is_enabled=True,
                    scoped_is_enabled=True,
                    is_enabled=True,
                    is_locked=False,
                    updated_at="2026-03-29T00:00:00Z",
                )
            ]
        }

    def update_user_file_filter(self, *_args, file_id: int | None = None, is_enabled: bool = True, **_kwargs):
        if file_id is None and _args:
            file_id = _args[-1]
        if file_id == 99 and not is_enabled:
            raise PermissionError("Global files cannot be disabled by non-admin users")
        if file_id != 1:
            return None
        return self.list_user_file_filters()["files"][0].model_copy(
            update={"global_is_enabled": is_enabled, "scoped_is_enabled": is_enabled, "is_enabled": is_enabled}
        )

    def list_chat_file_filters(self, *_args, chat_id: str | None = None, **_kwargs):
        if chat_id is None and _args:
            chat_id = _args[-1]
        if chat_id != "chat-1":
            return None
        return {
            "files": [
                FilterFileRead(
                    file_id=1,
                    file_name="manual.pdf",
                    file_path="/app/data/manual.pdf",
                    tags=["docker"],
                    global_is_enabled=True,
                    scoped_is_enabled=True,
                    is_enabled=True,
                    is_locked=False,
                    updated_at="2026-03-29T00:00:00Z",
                )
            ]
        }

    def update_chat_file_filter(self, *_args, chat_id: str | None = None, file_id: int | None = None, is_enabled: bool = True, **_kwargs):
        if chat_id is None and len(_args) >= 2:
            chat_id = _args[-2]
            file_id = _args[-1]
        if file_id == 99 and not is_enabled:
            raise PermissionError("Global files cannot be disabled by non-admin users")
        if chat_id != "chat-1" or file_id != 1:
            return None
        return self.list_chat_file_filters(chat_id="chat-1")["files"][0].model_copy(
            update={"scoped_is_enabled": is_enabled, "is_enabled": is_enabled}
        )

    def list_user_tag_filters(self, *_args, **_kwargs):
        return {
            "tags": [
                FilterTagRead(
                    tag="docker",
                    file_count=1,
                    global_is_enabled=True,
                    scoped_is_enabled=True,
                    is_enabled=True,
                    is_locked=False,
                )
            ]
        }

    def update_user_tag_filter(self, *_args, tag: str | None = None, is_enabled: bool = True, **_kwargs):
        if tag is None and _args:
            tag = _args[-1]
        if tag != "docker":
            return None
        return self.list_user_tag_filters()["tags"][0].model_copy(
            update={"global_is_enabled": is_enabled, "scoped_is_enabled": is_enabled, "is_enabled": is_enabled}
        )

    def list_chat_tag_filters(self, *_args, chat_id: str | None = None, **_kwargs):
        if chat_id is None and _args:
            chat_id = _args[-1]
        if chat_id != "chat-1":
            return None
        return {
            "tags": [
                FilterTagRead(
                    tag="docker",
                    file_count=1,
                    global_is_enabled=True,
                    scoped_is_enabled=True,
                    is_enabled=True,
                    is_locked=False,
                )
            ]
        }

    def update_chat_tag_filter(self, *_args, chat_id: str | None = None, tag: str | None = None, is_enabled: bool = True, **_kwargs):
        if chat_id is None and len(_args) >= 2:
            chat_id = _args[-2]
            tag = _args[-1]
        if chat_id != "chat-1" or tag != "docker":
            return None
        return self.list_chat_tag_filters(chat_id="chat-1")["tags"][0].model_copy(
            update={"scoped_is_enabled": is_enabled, "is_enabled": is_enabled}
        )

    def _sample_gpt(self) -> GptRead:
        return GptRead(
            id="gpt-1",
            name="Docker GPT",
            description="Answers Docker questions",
            instructions="Stay focused on Docker and Compose.",
            assistant_mode="thinking",
            chat_id="gpt-chat-1",
            created_at="2026-03-29T00:00:00Z",
            updated_at="2026-03-29T00:00:00Z",
            config=GptConfigRead(
                personalization=GptPersonalizationRead(
                    base_style="friendly",
                    warm="more",
                    enthusiastic="default",
                    headers_and_lists="more",
                ),
                settings=GptSettingsRead(
                    chat_history_messages_count=4,
                    max_similarities=7,
                    min_similarities=2,
                    similarity_score_threshold=0.65,
                ),
                files_enabled=True,
                tags_enabled=True,
                file_settings=[GptFileSettingRead(file_id=1, is_enabled=True)],
                tag_settings=[GptTagSettingRead(tag="docker", is_enabled=True)],
            ),
        )

    def list_gpts(self, *_args, **_kwargs) -> list[GptRead]:
        return [self._sample_gpt()]

    def get_gpt(self, *_args, gpt_id: str | None = None, **_kwargs) -> GptRead | None:
        if gpt_id is None and _args:
            gpt_id = _args[-1]
        if gpt_id != "gpt-1":
            return None
        return self._sample_gpt()

    def create_gpt(self, *_args, payload=None, **_kwargs) -> GptRead:
        if payload is None and _args:
            payload = _args[-1]
        base = self._sample_gpt()
        return base.model_copy(update={"name": payload.name, "description": payload.description, "instructions": payload.instructions, "assistant_mode": payload.assistant_mode, "config": payload.config})

    def update_gpt(self, *_args, gpt_id: str | None = None, payload=None, **_kwargs) -> GptRead | None:
        if gpt_id is None and len(_args) >= 2:
            gpt_id = _args[-2]
            payload = _args[-1]
        if gpt_id != "gpt-1":
            return None
        base = self._sample_gpt()
        if payload is None:
            return base
        updates = payload.model_dump(exclude_unset=True)
        if "config" in updates and updates["config"] is not None:
            updates["config"] = payload.config
        return base.model_copy(update=updates)

    def delete_gpt(self, *_args, gpt_id: str | None = None, **_kwargs) -> GptDeleteResponse | None:
        if gpt_id is None and _args:
            gpt_id = _args[-1]
        if gpt_id != "gpt-1":
            return None
        return GptDeleteResponse(id="gpt-1", deleted=True)

    def get_gpt_chat(self, *_args, gpt_id: str | None = None, **_kwargs) -> GptChatRead | None:
        if gpt_id is None and _args:
            gpt_id = _args[-1]
        if gpt_id != "gpt-1":
            return None
        return GptChatRead(
            gpt=self._sample_gpt(),
            messages=[
                MessageRead(
                    id="21",
                    chat_id="gpt-chat-1",
                    gpt_id="gpt-1",
                    role="assistant",
                    content="Docker-focused answer",
                    status="completed",
                    has_attachments=False,
                    created_at="2026-03-29T00:00:01Z",
                    sources=[],
                    attachments=[],
                )
            ],
        )

    def clear_gpt_chat(self, *_args, gpt_id: str | None = None, **_kwargs) -> GptChatRead | None:
        if gpt_id is None and _args:
            gpt_id = _args[-1]
        if gpt_id != "gpt-1":
            return None
        return GptChatRead(gpt=self._sample_gpt(), messages=[])

    def send_gpt_message(self, *_args, gpt_id: str | None = None, user_content: str | None = None, attachments=None, **_kwargs):
        if gpt_id is None and len(_args) >= 3:
            gpt_id = _args[1]
            user_content = _args[2]
        if gpt_id != "gpt-1":
            return None
        return {
            "chat_id": "gpt-chat-1",
            "gpt_id": "gpt-1",
            "user_message": MessageRead(
                id="20",
                chat_id="gpt-chat-1",
                gpt_id="gpt-1",
                role="user",
                content=user_content or "",
                status="completed",
                has_attachments=bool(attachments),
                created_at="2026-03-29T00:00:00Z",
                sources=[],
                attachments=[],
            ),
            "assistant_message": MessageRead(
                id="21",
                chat_id="gpt-chat-1",
                gpt_id="gpt-1",
                role="assistant",
                content="Docker-focused answer",
                status="completed",
                has_attachments=False,
                created_at="2026-03-29T00:00:01Z",
                sources=[],
                attachments=[],
            ),
            "assistant_mode": "thinking",
            "sources": [],
            "attachments_used": [],
        }

    def preview_gpt_message(self, *_args, **_kwargs):
        return {
            "chat_id": "preview",
            "gpt_id": None,
            "user_message": MessageRead(
                id="preview-user",
                chat_id="preview",
                gpt_id=None,
                role="user",
                content="hello",
                status="completed",
                has_attachments=False,
                created_at="2026-03-29T00:00:00Z",
                sources=[],
                attachments=[],
            ),
            "assistant_message": MessageRead(
                id="preview-assistant",
                chat_id="preview",
                gpt_id=None,
                role="assistant",
                content="Preview answer",
                status="completed",
                has_attachments=False,
                created_at="2026-03-29T00:00:01Z",
                sources=[],
                attachments=[],
            ),
            "assistant_mode": "thinking",
            "sources": [],
            "attachments_used": [],
        }

    def download_gpt_chat(self, *_args, gpt_id: str | None = None, **_kwargs) -> ChatDownloadResponse | None:
        if gpt_id is None and _args:
            gpt_id = _args[-1]
        if gpt_id != "gpt-1":
            return None
        return ChatDownloadResponse(
            chat_id="gpt-chat-1",
            chat_name="Docker GPT",
            is_archived=False,
            created_at="2026-03-29T00:00:00Z",
            updated_at="2026-03-29T00:00:01Z",
            messages=[
                {
                    "role": "assistant",
                    "content": "Docker-focused answer",
                    "created_at": "2026-03-29T00:00:01Z",
                    "sources": [],
                    "attachments": [],
                }
            ],
        )


def build_client() -> TestClient:
    app = create_app()
    auth = AuthContext(user=StubRetrieverService().user, session=type("Session", (), {"id": "session-1", "expires_at": "2026-03-29T02:00:00Z", "max_expires_at": "2026-03-29T12:00:00Z"})(), token="token")
    app.dependency_overrides[get_retriever_service] = lambda: StubRetrieverService()
    app.dependency_overrides[get_auth_context] = lambda: auth
    app.dependency_overrides[get_app_auth_context] = lambda: auth
    return TestClient(app)


def test_health_endpoint() -> None:
    client = build_client()
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_endpoints() -> None:
    client = build_client()
    response = client.post("/api/chats")
    assert response.status_code == 200
    assert response.json()["chat_name"].startswith("chat-")

    list_response = client.get("/api/chats")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    rename_response = client.patch("/api/chats/chat-1", json={"chat_name": "Renamed chat"})
    assert rename_response.status_code == 200
    assert rename_response.json()["chat_name"] == "Renamed chat"

    delete_response = client.delete("/api/chats/chat-1")
    assert delete_response.status_code == 200

    archived_response = client.get("/api/chats/archived")
    assert archived_response.status_code == 200
    assert archived_response.json()[0]["is_archived"] is True

    archive_response = client.patch("/api/chats/chat-1/archive")
    assert archive_response.status_code == 200
    assert archive_response.json()["is_archived"] is True

    unarchive_response = client.patch("/api/chats/chat-2/unarchive")
    assert unarchive_response.status_code == 200
    assert unarchive_response.json()["is_archived"] is False


def test_post_message_returns_sources() -> None:
    client = build_client()
    response = client.post("/api/chats/chat-1/messages", json={"message": "hello", "assistant_mode": "thinking"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"]["content"] == "Grounded answer"
    assert payload["assistant_mode"] == "thinking"
    assert payload["sources"][0]["file_name"] == "manual.pdf"
    assert payload["sources"][0]["section"] == "Volumes"


def test_post_message_supports_attachments() -> None:
    client = build_client()
    response = client.post(
        "/api/chats/chat-1/messages",
        data={"message": "Explain this image"},
        files={"files": ("diagram.png", b"fake-bytes", "image/png")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["user_message"]["has_attachments"] is True
    assert payload["attachments_used"][0]["file_name"] == "diagram.png"


def test_missing_chat_returns_404() -> None:
    client = build_client()
    response = client.get("/api/chats/missing")
    assert response.status_code == 404
    assert response.json() == {"detail": "Chat not found"}


def test_library_endpoints() -> None:
    client = build_client()

    list_response = client.get("/api/library/files")
    assert list_response.status_code == 200
    assert list_response.json()["files"][0]["extension"] == ".pdf"

    patch_response = client.patch("/api/library/files/1", json={"is_enabled": False})
    assert patch_response.status_code == 200
    assert patch_response.json()["is_enabled"] is False

    delete_response = client.delete("/api/library/files/1")
    assert delete_response.status_code == 200

    include_other_users_response = client.get("/api/library/files?include_other_users=true")
    assert include_other_users_response.status_code == 200

    forbidden_patch = client.patch("/api/library/files/99", json={"is_enabled": False})
    assert forbidden_patch.status_code == 403


def test_courses_endpoints() -> None:
    client = build_client()

    list_response = client.get("/api/courses?sort=updated_desc")
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    template_response = client.get("/api/courses/template")
    assert template_response.status_code == 200
    assert template_response.json()["file_name"] == "path-template.json"


def test_download_and_settings_endpoints() -> None:
    client = build_client()

    download_response = client.get("/api/chats/chat-1/download")
    assert download_response.status_code == 200
    assert download_response.headers["content-disposition"].endswith('chat-abc123-chat-1.json"')
    assert download_response.json()["messages"][1]["sources"][0]["file_name"] == "manual.pdf"

    settings_response = client.get("/api/settings")
    assert settings_response.status_code == 200
    assert settings_response.json()["max_similarities"] == 8
    assert settings_response.json()["available_assistant_modes"] == ["simple", "refine", "thinking"]

    patch_response = client.patch(
        "/api/settings",
        json={
            "chat_history_messages_count": 6,
            "max_similarities": 9,
            "min_similarities": 3,
            "similarity_score_threshold": 0.75,
        },
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["similarity_score_threshold"] == 0.75

    personalization_response = client.get("/api/personalization")
    assert personalization_response.status_code == 200
    assert personalization_response.json()["nickname"] == "Rik"

    personalization_patch = client.patch(
        "/api/personalization",
        json={
            "base_style": "professional",
            "warm": "less",
            "enthusiastic": "less",
            "headers_and_lists": "default",
            "custom_instructions": "Keep it concise.",
            "nickname": "Rik",
            "occupation": "Engineer",
            "more_about_user": "Values concise answers.",
        },
    )
    assert personalization_patch.status_code == 200
    assert personalization_patch.json()["base_style"] == "professional"
    assert personalization_patch.json()["custom_instructions"] == "Keep it concise."


def test_filter_endpoints() -> None:
    client = build_client()

    user_files = client.get("/api/user/files")
    assert user_files.status_code == 200
    assert user_files.json()["files"][0]["file_name"] == "manual.pdf"

    user_file_patch = client.patch("/api/user/files/1", json={"is_enabled": False})
    assert user_file_patch.status_code == 200
    assert user_file_patch.json()["is_enabled"] is False

    user_tags = client.get("/api/user/tags")
    assert user_tags.status_code == 200
    assert user_tags.json()["tags"][0]["tag"] == "docker"

    user_tag_patch = client.patch("/api/user/tags/docker", json={"is_enabled": False})
    assert user_tag_patch.status_code == 200
    assert user_tag_patch.json()["is_enabled"] is False

    chat_files = client.get("/api/chats/chat-1/files")
    assert chat_files.status_code == 200
    assert chat_files.json()["files"][0]["file_id"] == 1

    chat_file_patch = client.patch("/api/chats/chat-1/files/1", json={"is_enabled": False})
    assert chat_file_patch.status_code == 200
    assert chat_file_patch.json()["scoped_is_enabled"] is False

    global_forbidden = client.patch("/api/user/files/99", json={"is_enabled": False})
    assert global_forbidden.status_code == 403

    chat_global_forbidden = client.patch("/api/chats/chat-1/files/99", json={"is_enabled": False})
    assert chat_global_forbidden.status_code == 403

    chat_tags = client.get("/api/chats/chat-1/tags")
    assert chat_tags.status_code == 200
    assert chat_tags.json()["tags"][0]["tag"] == "docker"

    chat_tag_patch = client.patch("/api/chats/chat-1/tags/docker", json={"is_enabled": False})
    assert chat_tag_patch.status_code == 200
    assert chat_tag_patch.json()["scoped_is_enabled"] is False


def test_gpt_endpoints() -> None:
    client = build_client()

    list_response = client.get("/api/gpts")
    assert list_response.status_code == 200
    assert list_response.json()[0]["name"] == "Docker GPT"

    create_response = client.post(
        "/api/gpts",
        json={
            "name": "New GPT",
            "description": "A test GPT",
            "instructions": "Stay grounded",
            "assistant_mode": "thinking",
            "config": {
                "personalization": {
                    "base_style": "friendly",
                    "warm": "more",
                    "enthusiastic": "default",
                    "headers_and_lists": "more",
                },
                "settings": {
                    "chat_history_messages_count": 4,
                    "max_similarities": 7,
                    "min_similarities": 2,
                    "similarity_score_threshold": 0.65,
                },
                "files_enabled": True,
                "tags_enabled": True,
                "file_settings": [{"file_id": 1, "is_enabled": True}],
                "tag_settings": [{"tag": "docker", "is_enabled": True}],
            },
        },
    )
    assert create_response.status_code == 200
    assert create_response.json()["assistant_mode"] == "thinking"

    get_response = client.get("/api/gpts/gpt-1")
    assert get_response.status_code == 200
    assert get_response.json()["config"]["settings"]["max_similarities"] == 7

    patch_response = client.patch("/api/gpts/gpt-1", json={"description": "Updated"})
    assert patch_response.status_code == 200
    assert patch_response.json()["description"] == "Updated"

    preview_response = client.post(
        "/api/gpts/preview/messages",
        json={
            "message": "hello",
            "gpt": create_response.json(),
            "preview_messages": [],
        },
    )
    assert preview_response.status_code == 200
    assert preview_response.json()["assistant_message"]["content"] == "Preview answer"

    chat_response = client.get("/api/gpts/gpt-1/chat")
    assert chat_response.status_code == 200
    assert chat_response.json()["gpt"]["chat_id"] == "gpt-chat-1"

    message_response = client.post("/api/gpts/gpt-1/messages", json={"message": "hello"})
    assert message_response.status_code == 200
    assert message_response.json()["gpt_id"] == "gpt-1"

    clear_response = client.delete("/api/gpts/gpt-1/chat")
    assert clear_response.status_code == 200
    assert clear_response.json()["messages"] == []

    download_response = client.get("/api/gpts/gpt-1/download")
    assert download_response.status_code == 200
    assert download_response.headers["content-disposition"].endswith('Docker_GPT-gpt-1.json"')

    delete_response = client.delete("/api/gpts/gpt-1")
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True
