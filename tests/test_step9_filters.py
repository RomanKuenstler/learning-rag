from __future__ import annotations

from datetime import datetime, timezone

from services.common.models import Base, ChatSession, FileRecord, UserAccount
from services.common.postgres import PostgresClient


def build_client(tmp_path) -> PostgresClient:
    client = PostgresClient(f"sqlite+pysqlite:///{tmp_path / 'filters.db'}")
    Base.metadata.create_all(client.engine)
    return client


def seed_data(client: PostgresClient) -> None:
    now = datetime.now(timezone.utc)
    with client.session() as session:
        user = UserAccount(
            id=1,
            username="john",
            displayname="John",
            password_hash="hash",
            role="user",
            status="active",
            force_password_change=False,
        )
        user_two = UserAccount(
            id=2,
            username="anna",
            displayname="Anna",
            password_hash="hash",
            role="user",
            status="active",
            force_password_change=False,
        )
        chat = ChatSession(id="chat-1", user_id=1, chat_name="Test chat")
        session.add_all(
            [
                user,
                user_two,
                chat,
                FileRecord(
                    id=1,
                    file_path="docker.md",
                    file_name="docker.md",
                    extension=".md",
                    size_bytes=10,
                    chunk_count=1,
                    file_hash="a",
                    content_hash="a",
                    file_type="md",
                    processing_status="processed",
                    is_embedded=True,
                    is_enabled=True,
                    tags=["docker", "ops"],
                    uploaded_by_user_id=1,
                    is_global=False,
                    source_origin="user_upload",
                    updated_at=now,
                ),
                FileRecord(
                    id=2,
                    file_path="kubernetes.md",
                    file_name="kubernetes.md",
                    extension=".md",
                    size_bytes=10,
                    chunk_count=1,
                    file_hash="b",
                    content_hash="b",
                    file_type="md",
                    processing_status="processed",
                    is_embedded=True,
                    is_enabled=True,
                    tags=["kubernetes"],
                    uploaded_by_user_id=2,
                    is_global=False,
                    source_origin="user_upload",
                    updated_at=now,
                ),
                FileRecord(
                    id=3,
                    file_path="manual.pdf",
                    file_name="manual.pdf",
                    extension=".pdf",
                    size_bytes=10,
                    chunk_count=1,
                    file_hash="c",
                    content_hash="c",
                    file_type="pdf",
                    processing_status="processed",
                    is_embedded=True,
                    is_enabled=True,
                    tags=["docs"],
                    is_global=True,
                    source_origin="system_data",
                    updated_at=now,
                ),
            ]
        )


def test_filter_candidates_respects_global_and_chat_precedence(tmp_path) -> None:
    client = build_client(tmp_path)
    seed_data(client)

    client.set_user_file_filter(user_id=1, file_id=1, is_enabled=False, is_admin=False)
    client.set_chat_file_filter(user_id=1, chat_id="chat-1", file_id=2, is_enabled=False, is_admin=False)
    client.set_user_tag_filter(user_id=1, tag="docker", is_enabled=False)

    candidates = [
        {"file_path": "docker.md", "file_name": "docker.md", "chunk_id": "1", "score": 0.9, "text": "docker", "tags": ["docker"]},
        {"file_path": "kubernetes.md", "file_name": "kubernetes.md", "chunk_id": "2", "score": 0.85, "text": "k8s", "tags": ["kubernetes"]},
        {"file_path": "manual.pdf", "file_name": "manual.pdf", "chunk_id": "3", "score": 0.87, "text": "docs", "tags": ["docs"]},
    ]

    filtered = client.filter_retrieval_candidates(candidates, user_id=1, chat_id="chat-1", is_admin=False)

    assert len(filtered) == 1
    assert filtered[0]["file_path"] == "manual.pdf"


def test_chat_tag_filters_lock_globally_disabled_tags(tmp_path) -> None:
    client = build_client(tmp_path)
    seed_data(client)

    client.set_user_tag_filter(user_id=1, tag="docker", is_enabled=False)
    record = client.set_chat_tag_filter(user_id=1, chat_id="chat-1", tag="docker", is_enabled=True)

    assert record is not None
    assert record.global_is_enabled is False
    assert record.scoped_is_enabled is False
    assert record.is_enabled is False
    assert record.is_locked is True


def test_chat_file_filters_reflect_global_disable(tmp_path) -> None:
    client = build_client(tmp_path)
    seed_data(client)

    client.set_user_file_filter(user_id=1, file_id=1, is_enabled=False, is_admin=False)
    record = client.set_chat_file_filter(user_id=1, chat_id="chat-1", file_id=1, is_enabled=True, is_admin=False)

    assert record is not None
    assert record.global_is_enabled is False
    assert record.scoped_is_enabled is False
    assert record.is_enabled is False
    assert record.is_locked is True


def test_other_users_files_default_to_disabled(tmp_path) -> None:
    client = build_client(tmp_path)
    seed_data(client)

    records = client.list_files_for_user(user_id=1, is_admin=False, include_other_users=True)
    by_path = {record.file_path: record for record in records}
    assert by_path["docker.md"].is_enabled is True
    assert by_path["kubernetes.md"].is_enabled is False
    assert by_path["manual.pdf"].is_enabled is True


def test_non_admin_cannot_disable_global_file(tmp_path) -> None:
    client = build_client(tmp_path)
    seed_data(client)

    try:
        client.set_user_file_filter(user_id=1, file_id=3, is_enabled=False, is_admin=False)
        assert False, "expected PermissionError"
    except PermissionError:
        assert True
