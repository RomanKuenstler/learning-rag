from __future__ import annotations

from services.common.models import (
    ChatMessage,
    ChatSession,
    GPTChatSession,
    GPTRecord,
    MessageAttachment,
    RetrievalLog,
    SettingRecord,
    UserAccount,
    UserSessionRecord,
)
from services.retriever.postgres_client import RetrieverPostgresClient


class ChatRepository:
    def __init__(self, postgres_client: RetrieverPostgresClient) -> None:
        self.postgres_client = postgres_client

    def create_chat(self, user_id: int, chat_name: str) -> ChatSession:
        return self.postgres_client.create_chat(user_id, chat_name)

    def ensure_chat(self, user_id: int, chat_id: str, chat_name: str) -> ChatSession:
        return self.postgres_client.ensure_chat(user_id, chat_id, chat_name)

    def list_chats(self, user_id: int, *, archived: bool = False) -> list[ChatSession]:
        return self.postgres_client.list_chats(user_id=user_id, archived=archived)

    def get_chat(self, user_id: int, chat_id: str) -> ChatSession | None:
        return self.postgres_client.get_chat(chat_id, user_id=user_id)

    def rename_chat(self, user_id: int, chat_id: str, chat_name: str) -> ChatSession | None:
        return self.postgres_client.rename_chat(chat_id, user_id=user_id, chat_name=chat_name)

    def delete_chat(self, user_id: int, chat_id: str) -> ChatSession | None:
        return self.postgres_client.delete_chat(chat_id, user_id=user_id)

    def set_chat_archived(self, user_id: int, chat_id: str, is_archived: bool) -> ChatSession | None:
        return self.postgres_client.set_chat_archived(chat_id, user_id=user_id, is_archived=is_archived)

    def list_messages(self, user_id: int, chat_id: str) -> list[ChatMessage]:
        return self.postgres_client.get_chat_messages(chat_id, user_id=user_id)

    def create_message(
        self,
        user_id: int,
        chat_id: str,
        role: str,
        content: str,
        status: str = "completed",
        *,
        gpt_id: str | None = None,
        has_attachments: bool = False,
    ) -> ChatMessage:
        return self.postgres_client.add_chat_message(
            chat_id,
            user_id,
            role,
            content,
            status=status,
            gpt_id=gpt_id,
            has_attachments=has_attachments,
        )

    def add_message_attachments(self, message_id: int, attachments: list[dict[str, object]]) -> list[MessageAttachment]:
        return self.postgres_client.add_message_attachments(message_id, attachments)

    def create_retrieval_logs(
        self,
        *,
        assistant_message_id: int,
        user_message_id: int,
        chat_id: str,
        user_id: int,
        used_chunks: list[dict[str, str | float | list[str] | None]],
    ) -> None:
        self.postgres_client.add_retrieval_logs(
            assistant_message_id=assistant_message_id,
            user_message_id=user_message_id,
            session_id=chat_id,
            user_id=user_id,
            used_chunks=used_chunks,
        )

    def get_recent_history(self, user_id: int, chat_id: str, limit: int) -> list[ChatMessage]:
        return self.postgres_client.get_recent_chat_history(chat_id, user_id=user_id, limit=limit)

    def get_sources_by_assistant_message(self, user_id: int, assistant_message_ids: list[int]) -> dict[int, list[RetrievalLog]]:
        return self.postgres_client.get_retrieval_logs_for_assistant_messages(assistant_message_ids, user_id=user_id)

    def get_attachments_by_message_ids(self, message_ids: list[int]) -> dict[int, list[MessageAttachment]]:
        return self.postgres_client.get_attachments_by_message_ids(message_ids)

    def touch_chat(self, user_id: int, chat_id: str) -> None:
        self.postgres_client.touch_chat(chat_id, user_id=user_id)

    def list_settings(self, user_id: int) -> list[SettingRecord]:
        return self.postgres_client.list_settings(user_id=user_id)

    def upsert_setting(self, user_id: int, key: str, value: str) -> SettingRecord:
        return self.postgres_client.upsert_setting(user_id=user_id, key=key, value=value)

    def list_user_file_filters(self, user_id: int, *, is_admin: bool):
        return self.postgres_client.list_user_file_filters(user_id=user_id, is_admin=is_admin)

    def set_user_file_filter(self, user_id: int, file_id: int, is_enabled: bool, *, is_admin: bool):
        return self.postgres_client.set_user_file_filter(
            user_id=user_id,
            file_id=file_id,
            is_enabled=is_enabled,
            is_admin=is_admin,
        )

    def list_chat_file_filters(self, user_id: int, chat_id: str, *, is_admin: bool):
        return self.postgres_client.list_chat_file_filters(user_id=user_id, chat_id=chat_id, is_admin=is_admin)

    def set_chat_file_filter(self, user_id: int, chat_id: str, file_id: int, is_enabled: bool, *, is_admin: bool):
        return self.postgres_client.set_chat_file_filter(
            user_id=user_id,
            chat_id=chat_id,
            file_id=file_id,
            is_enabled=is_enabled,
            is_admin=is_admin,
        )

    def list_user_tag_filters(self, user_id: int):
        return self.postgres_client.list_user_tag_filters(user_id=user_id)

    def set_user_tag_filter(self, user_id: int, tag: str, is_enabled: bool):
        return self.postgres_client.set_user_tag_filter(user_id=user_id, tag=tag, is_enabled=is_enabled)

    def list_chat_tag_filters(self, user_id: int, chat_id: str):
        return self.postgres_client.list_chat_tag_filters(user_id=user_id, chat_id=chat_id)

    def set_chat_tag_filter(self, user_id: int, chat_id: str, tag: str, is_enabled: bool):
        return self.postgres_client.set_chat_tag_filter(user_id=user_id, chat_id=chat_id, tag=tag, is_enabled=is_enabled)

    def list_gpts(self, user_id: int) -> list[GPTRecord]:
        return self.postgres_client.list_gpts(user_id=user_id)

    def get_gpt(self, user_id: int, gpt_id: str) -> GPTRecord | None:
        return self.postgres_client.get_gpt(gpt_id, user_id=user_id)

    def create_gpt(self, user_id: int, payload: dict[str, object]) -> GPTRecord:
        return self.postgres_client.create_gpt(user_id=user_id, payload=payload)

    def update_gpt(self, user_id: int, gpt_id: str, fields: dict[str, object]) -> GPTRecord | None:
        return self.postgres_client.update_gpt(gpt_id, user_id=user_id, fields=fields)

    def delete_gpt(self, user_id: int, gpt_id: str) -> GPTRecord | None:
        return self.postgres_client.delete_gpt(gpt_id, user_id=user_id)

    def ensure_gpt_chat(self, gpt_id: str) -> GPTChatSession:
        return self.postgres_client.ensure_gpt_chat(gpt_id=gpt_id)

    def get_gpt_chat(self, user_id: int, gpt_id: str) -> GPTChatSession | None:
        return self.postgres_client.get_gpt_chat(gpt_id=gpt_id, user_id=user_id)

    def clear_gpt_chat(self, user_id: int, gpt_id: str) -> GPTChatSession | None:
        return self.postgres_client.clear_gpt_chat(gpt_id=gpt_id, user_id=user_id)

    def list_gpt_messages(self, user_id: int, chat_id: str, gpt_id: str) -> list[ChatMessage]:
        return self.postgres_client.get_chat_messages(chat_id, user_id=user_id, gpt_id=gpt_id)

    def get_recent_gpt_history(self, user_id: int, chat_id: str, gpt_id: str, limit: int) -> list[ChatMessage]:
        return self.postgres_client.get_recent_chat_history(chat_id, user_id=user_id, limit=limit, gpt_id=gpt_id)

    def list_gpt_file_filters(self, *, file_settings: dict[int, bool] | None = None, files_enabled: bool = True):
        return self.postgres_client.list_gpt_file_filters(file_settings=file_settings, files_enabled=files_enabled)

    def list_gpt_tag_filters(self, *, tag_settings: dict[str, bool] | None = None, tags_enabled: bool = True):
        return self.postgres_client.list_gpt_tag_filters(tag_settings=tag_settings, tags_enabled=tags_enabled)

    def list_users(self) -> list[UserAccount]:
        return self.postgres_client.list_users()

    def get_user_by_id(self, user_id: int) -> UserAccount | None:
        return self.postgres_client.get_user_by_id(user_id)

    def get_user_by_username(self, username: str) -> UserAccount | None:
        return self.postgres_client.get_user_by_username(username)

    def create_user(
        self,
        *,
        username: str,
        displayname: str,
        role: str,
        password_hash: str,
        status: str = "active",
        force_password_change: bool = True,
    ) -> UserAccount:
        return self.postgres_client.create_user(
            username=username,
            displayname=displayname,
            role=role,
            password_hash=password_hash,
            status=status,
            force_password_change=force_password_change,
        )

    def update_user(self, user_id: int, **fields: object) -> UserAccount | None:
        return self.postgres_client.update_user(user_id, **fields)

    def delete_user(self, user_id: int) -> UserAccount | None:
        return self.postgres_client.delete_user(user_id)

    def upsert_bootstrap_user(self, *, username: str, displayname: str, role: str, password_hash: str) -> UserAccount:
        return self.postgres_client.upsert_bootstrap_user(
            username=username,
            displayname=displayname,
            role=role,
            password_hash=password_hash,
        )

    def deactivate_users_not_in(self, usernames: set[str]) -> None:
        self.postgres_client.deactivate_users_not_in(usernames)

    def assign_orphaned_records_to_user(self, user_id: int) -> None:
        self.postgres_client.assign_orphaned_records_to_user(user_id)

    def create_user_session(
        self,
        *,
        session_id: str,
        user_id: int,
        issued_at,
        last_refreshed_at,
        last_activity_at,
        expires_at,
        max_expires_at,
    ) -> UserSessionRecord:
        return self.postgres_client.create_user_session(
            session_id=session_id,
            user_id=user_id,
            issued_at=issued_at,
            last_refreshed_at=last_refreshed_at,
            last_activity_at=last_activity_at,
            expires_at=expires_at,
            max_expires_at=max_expires_at,
        )

    def get_user_session(self, session_id: str) -> UserSessionRecord | None:
        return self.postgres_client.get_user_session(session_id)

    def update_user_session_activity(self, session_id: str, *, last_activity_at) -> UserSessionRecord | None:
        return self.postgres_client.update_user_session_activity(session_id, last_activity_at=last_activity_at)

    def refresh_user_session(self, session_id: str, *, last_refreshed_at, last_activity_at, expires_at) -> UserSessionRecord | None:
        return self.postgres_client.refresh_user_session(
            session_id,
            last_refreshed_at=last_refreshed_at,
            last_activity_at=last_activity_at,
            expires_at=expires_at,
        )

    def revoke_user_session(self, session_id: str, *, revoked_at) -> UserSessionRecord | None:
        return self.postgres_client.revoke_user_session(session_id, revoked_at=revoked_at)

    def revoke_all_user_sessions(self, user_id: int, *, revoked_at) -> None:
        self.postgres_client.revoke_all_user_sessions(user_id, revoked_at=revoked_at)
