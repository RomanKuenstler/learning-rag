from __future__ import annotations

from dataclasses import dataclass
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine

from services.common.migrations import run_migrations
from services.common.models import (
    ChatMessage,
    ChatFileSetting,
    ChatSession,
    ChatTagSetting,
    ChunkRecord,
    DiagnosticDefinition,
    DiagnosticOption,
    DiagnosticQuestion,
    DiagnosticScoringRule,
    DiagnosticVersion,
    ExplanationFeedback,
    FileRecord,
    GPTChatSession,
    GPTRecord,
    LearningLesson,
    LearningModule,
    LearningStateCheck,
    LearningPath,
    LearningPathAllowedFile,
    LearningPathAllowedTag,
    MessageAttachment,
    RetrievalLog,
    SettingRecord,
    UserLearningGoal,
    UserLearningPreference,
    UserLearningProfile,
    UserAccount,
    UserFileSetting,
    UserDiagnosticAnswer,
    UserDiagnosticAttempt,
    UserDiagnosticResult,
    UserTagSetting,
    UserSessionRecord,
)
from services.common.retry import retry


@dataclass(slots=True)
class FileFilterState:
    file_id: int
    file_name: str
    file_path: str
    tags: list[str]
    global_is_enabled: bool
    scoped_is_enabled: bool
    is_enabled: bool
    is_locked: bool
    updated_at: datetime


@dataclass(slots=True)
class TagFilterState:
    tag: str
    file_count: int
    global_is_enabled: bool
    scoped_is_enabled: bool
    is_enabled: bool
    is_locked: bool


class PostgresClient:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    def initialize(self) -> None:
        retry(lambda: run_migrations(self.database_url))

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_files(self) -> list[FileRecord]:
        with self.session() as session:
            rows = session.scalars(select(FileRecord).order_by(FileRecord.updated_at.desc(), FileRecord.file_name.asc()))
            records = list(rows)
            chunk_counts = self.chunk_counts_by_file_ids([record.id for record in records])
            for record in records:
                if not record.extension:
                    record.extension = Path(record.file_name).suffix.lower()
                resolved_chunk_count = chunk_counts.get(record.id, record.chunk_count)
                if not record.chunk_count and resolved_chunk_count:
                    record.chunk_count = resolved_chunk_count
                if resolved_chunk_count and not record.is_embedded:
                    record.is_embedded = True
                self._materialize_file_record(record)
                session.expunge(record)
            return records

    def list_files_for_user(self, *, user_id: int, is_admin: bool, include_other_users: bool = False) -> list[FileRecord]:
        with self.session() as session:
            records = list(
                session.scalars(select(FileRecord).order_by(FileRecord.updated_at.desc(), FileRecord.file_name.asc()))
            )
            if not include_other_users:
                records = [
                    record
                    for record in records
                    if record.is_global or record.uploaded_by_user_id == user_id
                ]
            file_ids = [record.id for record in records]
            chunk_counts = self.chunk_counts_by_file_ids(file_ids)
            settings = self._user_file_settings_map(session, user_id=user_id, file_ids=file_ids)
            for record in records:
                if not record.extension:
                    record.extension = Path(record.file_name).suffix.lower()
                resolved_chunk_count = chunk_counts.get(record.id, record.chunk_count)
                if not record.chunk_count and resolved_chunk_count:
                    record.chunk_count = resolved_chunk_count
                if resolved_chunk_count and not record.is_embedded:
                    record.is_embedded = True
                record.is_enabled = self._resolve_user_file_enabled(
                    record,
                    user_id=user_id,
                    is_admin=is_admin,
                    explicit_setting=settings.get(record.id),
                )
                self._materialize_file_record(record)
                session.expunge(record)
            return records

    def get_file(self, file_path: str) -> FileRecord | None:
        with self.session() as session:
            return session.scalar(select(FileRecord).where(FileRecord.file_path == file_path))

    def get_file_by_id(self, file_id: int) -> FileRecord | None:
        with self.session() as session:
            return session.get(FileRecord, file_id)

    def upsert_file_with_chunks(
        self,
        *,
        file_payload: dict,
        chunks: list[dict],
    ) -> FileRecord:
        file_path = str(file_payload["file_path"])
        with self.session() as session:
            record = session.scalar(select(FileRecord).where(FileRecord.file_path == file_path))
            if record is None:
                record = FileRecord(**file_payload)
                session.add(record)
                session.flush()
            else:
                for key, value in file_payload.items():
                    if key == "is_enabled" and value is None:
                        continue
                    setattr(record, key, value)
                record.last_processed_at = datetime.now(timezone.utc)
                session.execute(delete(ChunkRecord).where(ChunkRecord.file_id == record.id))
                session.flush()

            for chunk in chunks:
                chunk_payload = dict(chunk)
                if "metadata" in chunk_payload:
                    chunk_payload["chunk_metadata"] = chunk_payload.pop("metadata")
                session.add(ChunkRecord(file_id=record.id, **chunk_payload))

            session.flush()
            session.refresh(record)
            return record

    def delete_file(self, file_path: str) -> FileRecord | None:
        with self.session() as session:
            record = session.scalar(select(FileRecord).where(FileRecord.file_path == file_path))
            if record is None:
                return None
            session.delete(record)
            return record

    def set_file_enabled(self, file_id: int, is_enabled: bool) -> FileRecord | None:
        with self.session() as session:
            record = session.get(FileRecord, file_id)
            if record is None:
                return None
            record.is_enabled = is_enabled
            record.updated_at = datetime.now(timezone.utc)
            session.flush()
            session.refresh(record)
            return record

    def set_file_enabled_for_user(self, *, user_id: int, file_id: int, is_enabled: bool, is_admin: bool) -> FileRecord | None:
        with self.session() as session:
            record = session.get(FileRecord, file_id)
            if record is None:
                return None
            if not is_admin and record.is_global and not is_enabled:
                raise PermissionError("Global files cannot be disabled by non-admin users")
            setting = session.scalar(
                select(UserFileSetting).where(UserFileSetting.user_id == user_id, UserFileSetting.file_id == file_id)
            )
            if setting is None:
                setting = UserFileSetting(user_id=user_id, file_id=file_id, is_enabled=is_enabled)
                session.add(setting)
            else:
                setting.is_enabled = is_enabled
                setting.updated_at = datetime.now(timezone.utc)
            effective_enabled = self._resolve_user_file_enabled(
                record,
                user_id=user_id,
                is_admin=is_admin,
                explicit_setting=is_enabled,
            )
            session.flush()
            session.refresh(record)
            record.is_enabled = effective_enabled
            return record

    def filter_retrieval_candidates(
        self,
        candidates: list[dict[str, object]],
        *,
        user_id: int,
        chat_id: str | None,
        is_admin: bool,
        gpt_overrides: dict[str, object] | None = None,
    ) -> list[dict[str, object]]:
        if not candidates:
            return []
        with self.session() as session:
            file_paths = list({str(candidate.get("file_path", "")) for candidate in candidates if candidate.get("file_path")})
            records = list(session.scalars(select(FileRecord).where(FileRecord.file_path.in_(file_paths))))
            file_ids = [record.id for record in records]
            tags_in_system = self._all_tags_from_records(records)
            user_file_settings = self._user_file_settings_map(session, user_id=user_id, file_ids=file_ids)
            if gpt_overrides:
                file_settings = {
                    int(file_id): bool(is_enabled)
                    for file_id, is_enabled in dict(gpt_overrides.get("file_settings") or {}).items()
                }
                tag_settings = {
                    str(tag): bool(is_enabled)
                    for tag, is_enabled in dict(gpt_overrides.get("tag_settings") or {}).items()
                }
                files_enabled = bool(gpt_overrides.get("files_enabled", True))
                tags_enabled = bool(gpt_overrides.get("tags_enabled", True))
            else:
                chat_file_settings = self._chat_file_settings_map(session, chat_id=chat_id, file_ids=file_ids)
                self._delete_stale_tag_settings(session, user_id=user_id, chat_id=chat_id, valid_tags=tags_in_system)
                user_tag_settings = self._user_tag_settings_map(session, user_id=user_id, tags=tags_in_system)
                chat_tag_settings = self._chat_tag_settings_map(session, chat_id=chat_id, tags=tags_in_system)
            file_map = {record.file_path: record for record in records}
            filtered: list[dict[str, object]] = []
            for candidate in candidates:
                file_path = str(candidate.get("file_path", ""))
                record = file_map.get(file_path)
                if record is None:
                    continue
                global_file_enabled = self._resolve_user_file_enabled(
                    record,
                    user_id=user_id,
                    is_admin=is_admin,
                    explicit_setting=user_file_settings.get(record.id),
                )
                if gpt_overrides:
                    if not global_file_enabled:
                        continue
                    if files_enabled and not file_settings.get(record.id, True):
                        continue
                else:
                    chat_file_enabled = chat_file_settings.get(record.id, True)
                    if not global_file_enabled or not chat_file_enabled:
                        continue
                chunk_tags = [str(tag) for tag in list(candidate.get("tags", []) or [])]
                if gpt_overrides:
                    if not tags_enabled:
                        filtered.append(candidate)
                        continue
                    if all(tag_settings.get(tag, True) for tag in chunk_tags):
                        filtered.append(candidate)
                    continue
                if not global_file_enabled or not chat_file_enabled:
                    continue
                tag_enabled = True
                for tag in chunk_tags:
                    if not user_tag_settings.get(tag, True):
                        tag_enabled = False
                        break
                    if not chat_tag_settings.get(tag, True):
                        tag_enabled = False
                        break
                if tag_enabled:
                    filtered.append(candidate)
            return filtered

    def list_user_file_filters(self, *, user_id: int, is_admin: bool) -> list[FileFilterState]:
        with self.session() as session:
            records = list(session.scalars(select(FileRecord).order_by(FileRecord.file_name.asc())))
            user_file_settings = self._user_file_settings_map(session, user_id=user_id, file_ids=[record.id for record in records])
            result: list[FileFilterState] = []
            for record in records:
                effective_enabled = self._resolve_user_file_enabled(
                    record,
                    user_id=user_id,
                    is_admin=is_admin,
                    explicit_setting=user_file_settings.get(record.id),
                )
                result.append(
                    FileFilterState(
                        file_id=record.id,
                        file_name=record.file_name,
                        file_path=record.file_path,
                        tags=list(record.tags or []),
                        global_is_enabled=effective_enabled,
                        scoped_is_enabled=effective_enabled,
                        is_enabled=effective_enabled,
                        is_locked=record.is_global and not is_admin,
                        updated_at=record.updated_at,
                    )
                )
            return result

    def set_user_file_filter(self, *, user_id: int, file_id: int, is_enabled: bool, is_admin: bool) -> FileFilterState | None:
        with self.session() as session:
            record = session.get(FileRecord, file_id)
            if record is None:
                return None
            if not is_admin and record.is_global and not is_enabled:
                raise PermissionError("Global files cannot be disabled by non-admin users")
            self._upsert_user_file_setting(session, user_id=user_id, file_id=file_id, is_enabled=is_enabled)
            session.flush()
            effective_enabled = self._resolve_user_file_enabled(
                record,
                user_id=user_id,
                is_admin=is_admin,
                explicit_setting=is_enabled,
            )
            return FileFilterState(
                file_id=record.id,
                file_name=record.file_name,
                file_path=record.file_path,
                tags=list(record.tags or []),
                global_is_enabled=effective_enabled,
                scoped_is_enabled=effective_enabled,
                is_enabled=effective_enabled,
                is_locked=record.is_global and not is_admin,
                updated_at=record.updated_at,
            )

    def list_chat_file_filters(self, *, user_id: int, chat_id: str, is_admin: bool) -> list[FileFilterState] | None:
        with self.session() as session:
            if session.scalar(select(ChatSession.id).where(ChatSession.id == chat_id, ChatSession.user_id == user_id)) is None:
                return None
            records = list(session.scalars(select(FileRecord).order_by(FileRecord.file_name.asc())))
            file_ids = [record.id for record in records]
            user_file_settings = self._user_file_settings_map(session, user_id=user_id, file_ids=file_ids)
            chat_file_settings = self._chat_file_settings_map(session, chat_id=chat_id, file_ids=file_ids)
            result: list[FileFilterState] = []
            for record in records:
                global_enabled = self._resolve_user_file_enabled(
                    record,
                    user_id=user_id,
                    is_admin=is_admin,
                    explicit_setting=user_file_settings.get(record.id),
                )
                scoped_enabled = chat_file_settings.get(record.id, True)
                result.append(
                    FileFilterState(
                        file_id=record.id,
                        file_name=record.file_name,
                        file_path=record.file_path,
                        tags=list(record.tags or []),
                        global_is_enabled=global_enabled,
                        scoped_is_enabled=scoped_enabled,
                        is_enabled=global_enabled and scoped_enabled,
                        is_locked=(not global_enabled) or (record.is_global and not is_admin),
                        updated_at=record.updated_at,
                    )
                )
            return result

    def set_chat_file_filter(self, *, user_id: int, chat_id: str, file_id: int, is_enabled: bool, is_admin: bool) -> FileFilterState | None:
        with self.session() as session:
            chat = session.scalar(select(ChatSession).where(ChatSession.id == chat_id, ChatSession.user_id == user_id))
            record = session.get(FileRecord, file_id)
            if chat is None or record is None:
                return None
            global_enabled = self._resolve_user_file_enabled(
                record,
                user_id=user_id,
                is_admin=is_admin,
                explicit_setting=self._user_file_settings_map(session, user_id=user_id, file_ids=[file_id]).get(file_id),
            )
            if not is_admin and record.is_global and not is_enabled:
                raise PermissionError("Global files cannot be disabled by non-admin users")
            if not global_enabled:
                is_enabled = False
            self._upsert_chat_file_setting(session, chat_id=chat_id, file_id=file_id, is_enabled=is_enabled)
            session.flush()
            return FileFilterState(
                file_id=record.id,
                file_name=record.file_name,
                file_path=record.file_path,
                tags=list(record.tags or []),
                global_is_enabled=global_enabled,
                scoped_is_enabled=is_enabled,
                is_enabled=global_enabled and is_enabled,
                is_locked=(not global_enabled) or (record.is_global and not is_admin),
                updated_at=record.updated_at,
            )

    def list_user_tag_filters(self, *, user_id: int) -> list[TagFilterState]:
        with self.session() as session:
            records = list(session.scalars(select(FileRecord)))
            tag_counts = self._tag_counts(records)
            tags = set(tag_counts)
            self._delete_stale_tag_settings(session, user_id=user_id, chat_id=None, valid_tags=tags)
            user_tag_settings = self._user_tag_settings_map(session, user_id=user_id, tags=tags)
            return [
                TagFilterState(
                    tag=tag,
                    file_count=count,
                    global_is_enabled=user_tag_settings.get(tag, True),
                    scoped_is_enabled=user_tag_settings.get(tag, True),
                    is_enabled=user_tag_settings.get(tag, True),
                    is_locked=False,
                )
                for tag, count in sorted(tag_counts.items())
            ]

    def set_user_tag_filter(self, *, user_id: int, tag: str, is_enabled: bool) -> TagFilterState | None:
        normalized_tag = tag.strip().lower()
        if not normalized_tag:
            return None
        with self.session() as session:
            records = list(session.scalars(select(FileRecord)))
            tag_counts = self._tag_counts(records)
            if normalized_tag not in tag_counts:
                return None
            self._delete_stale_tag_settings(session, user_id=user_id, chat_id=None, valid_tags=set(tag_counts))
            self._upsert_user_tag_setting(session, user_id=user_id, tag=normalized_tag, is_enabled=is_enabled)
            session.flush()
            return TagFilterState(
                tag=normalized_tag,
                file_count=tag_counts[normalized_tag],
                global_is_enabled=is_enabled,
                scoped_is_enabled=is_enabled,
                is_enabled=is_enabled,
                is_locked=False,
            )

    def list_chat_tag_filters(self, *, user_id: int, chat_id: str) -> list[TagFilterState] | None:
        with self.session() as session:
            if session.scalar(select(ChatSession.id).where(ChatSession.id == chat_id, ChatSession.user_id == user_id)) is None:
                return None
            records = list(session.scalars(select(FileRecord)))
            tag_counts = self._tag_counts(records)
            tags = set(tag_counts)
            self._delete_stale_tag_settings(session, user_id=user_id, chat_id=chat_id, valid_tags=tags)
            user_tag_settings = self._user_tag_settings_map(session, user_id=user_id, tags=tags)
            chat_tag_settings = self._chat_tag_settings_map(session, chat_id=chat_id, tags=tags)
            return [
                TagFilterState(
                    tag=tag,
                    file_count=count,
                    global_is_enabled=user_tag_settings.get(tag, True),
                    scoped_is_enabled=chat_tag_settings.get(tag, True),
                    is_enabled=user_tag_settings.get(tag, True) and chat_tag_settings.get(tag, True),
                    is_locked=not user_tag_settings.get(tag, True),
                )
                for tag, count in sorted(tag_counts.items())
            ]

    def set_chat_tag_filter(self, *, user_id: int, chat_id: str, tag: str, is_enabled: bool) -> TagFilterState | None:
        normalized_tag = tag.strip().lower()
        if not normalized_tag:
            return None
        with self.session() as session:
            chat = session.scalar(select(ChatSession).where(ChatSession.id == chat_id, ChatSession.user_id == user_id))
            if chat is None:
                return None
            records = list(session.scalars(select(FileRecord)))
            tag_counts = self._tag_counts(records)
            if normalized_tag not in tag_counts:
                return None
            self._delete_stale_tag_settings(session, user_id=user_id, chat_id=chat_id, valid_tags=set(tag_counts))
            global_enabled = self._user_tag_settings_map(session, user_id=user_id, tags={normalized_tag}).get(normalized_tag, True)
            if not global_enabled:
                is_enabled = False
            self._upsert_chat_tag_setting(session, chat_id=chat_id, tag=normalized_tag, is_enabled=is_enabled)
            session.flush()
            return TagFilterState(
                tag=normalized_tag,
                file_count=tag_counts[normalized_tag],
                global_is_enabled=global_enabled,
                scoped_is_enabled=is_enabled,
                is_enabled=global_enabled and is_enabled,
                is_locked=not global_enabled,
            )

    def list_gpt_file_filters(
        self,
        *,
        file_settings: dict[int, bool] | None = None,
        files_enabled: bool = True,
    ) -> list[FileFilterState]:
        with self.session() as session:
            records = list(session.scalars(select(FileRecord).order_by(FileRecord.file_name.asc())))
            overrides = file_settings or {}
            return [
                FileFilterState(
                    file_id=record.id,
                    file_name=record.file_name,
                    file_path=record.file_path,
                    tags=list(record.tags or []),
                    global_is_enabled=record.is_enabled,
                    scoped_is_enabled=overrides.get(record.id, True) if files_enabled else True,
                    is_enabled=record.is_enabled and (overrides.get(record.id, True) if files_enabled else True),
                    is_locked=not record.is_enabled,
                    updated_at=record.updated_at,
                )
                for record in records
            ]

    def list_gpt_tag_filters(
        self,
        *,
        tag_settings: dict[str, bool] | None = None,
        tags_enabled: bool = True,
    ) -> list[TagFilterState]:
        with self.session() as session:
            records = list(session.scalars(select(FileRecord)))
            tag_counts = self._tag_counts(records)
            overrides = tag_settings or {}
            return [
                TagFilterState(
                    tag=tag,
                    file_count=count,
                    global_is_enabled=True,
                    scoped_is_enabled=overrides.get(tag, True) if tags_enabled else True,
                    is_enabled=overrides.get(tag, True) if tags_enabled else True,
                    is_locked=False,
                )
                for tag, count in sorted(tag_counts.items())
            ]

    def chunk_counts_by_file_ids(self, file_ids: list[int]) -> dict[int, int]:
        if not file_ids:
            return {}
        with self.session() as session:
            rows = session.execute(
                select(ChunkRecord.file_id, func.count(ChunkRecord.id)).where(ChunkRecord.file_id.in_(file_ids)).group_by(ChunkRecord.file_id)
            )
            return {int(file_id): int(count) for file_id, count in rows}

    def ensure_chat(self, user_id: int, chat_id: str, chat_name: str) -> ChatSession:
        with self.session() as session:
            chat = session.scalar(select(ChatSession).where(ChatSession.id == chat_id, ChatSession.user_id == user_id))
            if chat is None:
                chat = ChatSession(id=chat_id, user_id=user_id, chat_name=chat_name)
                session.add(chat)
                session.flush()
                session.refresh(chat)
            return chat

    def create_chat(self, user_id: int, chat_name: str, chat_id: str | None = None) -> ChatSession:
        with self.session() as session:
            chat = ChatSession(id=chat_id or None, user_id=user_id, chat_name=chat_name)
            session.add(chat)
            session.flush()
            session.refresh(chat)
            return chat

    def list_gpts(self, *, user_id: int) -> list[GPTRecord]:
        with self.session() as session:
            rows = session.scalars(
                select(GPTRecord).where(GPTRecord.user_id == user_id).order_by(GPTRecord.updated_at.desc(), GPTRecord.created_at.desc())
            )
            return list(rows)

    def get_gpt(self, gpt_id: str, *, user_id: int) -> GPTRecord | None:
        with self.session() as session:
            return session.scalar(select(GPTRecord).where(GPTRecord.id == gpt_id, GPTRecord.user_id == user_id))

    def create_gpt(self, *, user_id: int, payload: dict[str, object]) -> GPTRecord:
        with self.session() as session:
            record = GPTRecord(user_id=user_id, **payload)
            session.add(record)
            session.flush()
            session.refresh(record)
            return record

    def update_gpt(self, gpt_id: str, *, user_id: int, fields: dict[str, object]) -> GPTRecord | None:
        with self.session() as session:
            record = session.scalar(select(GPTRecord).where(GPTRecord.id == gpt_id, GPTRecord.user_id == user_id))
            if record is None:
                return None
            for key, value in fields.items():
                setattr(record, key, value)
            record.updated_at = datetime.now(timezone.utc)
            session.flush()
            session.refresh(record)
            return record

    def delete_gpt(self, gpt_id: str, *, user_id: int) -> GPTRecord | None:
        with self.session() as session:
            record = session.scalar(select(GPTRecord).where(GPTRecord.id == gpt_id, GPTRecord.user_id == user_id))
            if record is None:
                return None
            chat = session.scalar(select(GPTChatSession).where(GPTChatSession.gpt_id == gpt_id))
            if chat is not None:
                session.execute(delete(RetrievalLog).where(RetrievalLog.session_id == chat.id, RetrievalLog.user_id == user_id))
                session.execute(delete(ChatMessage).where(ChatMessage.session_id == chat.id, ChatMessage.gpt_id == gpt_id))
                session.delete(chat)
            session.delete(record)
            return record

    def ensure_gpt_chat(self, *, gpt_id: str) -> GPTChatSession:
        with self.session() as session:
            chat = session.scalar(select(GPTChatSession).where(GPTChatSession.gpt_id == gpt_id))
            if chat is None:
                chat = GPTChatSession(gpt_id=gpt_id)
                session.add(chat)
                session.flush()
                session.refresh(chat)
            return chat

    def get_gpt_chat(self, *, gpt_id: str, user_id: int) -> GPTChatSession | None:
        with self.session() as session:
            return session.scalar(
                select(GPTChatSession)
                .join(GPTRecord, GPTRecord.id == GPTChatSession.gpt_id)
                .where(GPTChatSession.gpt_id == gpt_id, GPTRecord.user_id == user_id)
            )

    def touch_gpt_chat(self, *, gpt_id: str) -> None:
        with self.session() as session:
            chat = session.scalar(select(GPTChatSession).where(GPTChatSession.gpt_id == gpt_id))
            if chat is not None:
                chat.updated_at = datetime.now(timezone.utc)

    def clear_gpt_chat(self, *, gpt_id: str, user_id: int) -> GPTChatSession | None:
        with self.session() as session:
            record = session.scalar(select(GPTRecord).where(GPTRecord.id == gpt_id, GPTRecord.user_id == user_id))
            if record is None:
                return None
            chat = session.scalar(select(GPTChatSession).where(GPTChatSession.gpt_id == gpt_id))
            if chat is None:
                return None
            session.execute(delete(RetrievalLog).where(RetrievalLog.session_id == chat.id, RetrievalLog.user_id == user_id))
            session.execute(delete(ChatMessage).where(ChatMessage.session_id == chat.id, ChatMessage.gpt_id == gpt_id))
            chat.updated_at = datetime.now(timezone.utc)
            session.flush()
            session.refresh(chat)
            return chat

    def list_chats(self, *, user_id: int, archived: bool = False) -> list[ChatSession]:
        with self.session() as session:
            rows = session.scalars(
                select(ChatSession)
                .where(ChatSession.user_id == user_id, ChatSession.is_archived.is_(archived))
                .order_by(ChatSession.updated_at.desc(), ChatSession.created_at.desc())
            )
            return list(rows)

    def get_chat(self, chat_id: str, *, user_id: int) -> ChatSession | None:
        with self.session() as session:
            return session.scalar(select(ChatSession).where(ChatSession.id == chat_id, ChatSession.user_id == user_id))

    def rename_chat(self, chat_id: str, *, user_id: int, chat_name: str) -> ChatSession | None:
        with self.session() as session:
            chat = session.scalar(select(ChatSession).where(ChatSession.id == chat_id, ChatSession.user_id == user_id))
            if chat is None:
                return None
            chat.chat_name = chat_name
            chat.updated_at = datetime.now(timezone.utc)
            session.flush()
            session.refresh(chat)
            return chat

    def delete_chat(self, chat_id: str, *, user_id: int) -> ChatSession | None:
        with self.session() as session:
            chat = session.scalar(select(ChatSession).where(ChatSession.id == chat_id, ChatSession.user_id == user_id))
            if chat is None:
                return None
            session.execute(delete(RetrievalLog).where(RetrievalLog.session_id == chat_id, RetrievalLog.user_id == user_id))
            session.execute(delete(ChatMessage).where(ChatMessage.session_id == chat_id, ChatMessage.user_id == user_id))
            session.delete(chat)
            return chat

    def set_chat_archived(self, chat_id: str, *, user_id: int, is_archived: bool) -> ChatSession | None:
        with self.session() as session:
            chat = session.scalar(select(ChatSession).where(ChatSession.id == chat_id, ChatSession.user_id == user_id))
            if chat is None:
                return None
            chat.is_archived = is_archived
            chat.updated_at = datetime.now(timezone.utc)
            session.flush()
            session.refresh(chat)
            return chat

    def touch_chat(self, chat_id: str, *, user_id: int) -> None:
        with self.session() as session:
            chat = session.scalar(select(ChatSession).where(ChatSession.id == chat_id, ChatSession.user_id == user_id))
            if chat is not None:
                chat.updated_at = datetime.now(timezone.utc)

    def add_chat_message(
        self,
        session_id: str,
        user_id: int,
        role: str,
        content: str,
        status: str = "completed",
        *,
        gpt_id: str | None = None,
        has_attachments: bool = False,
    ) -> ChatMessage:
        with self.session() as session:
            message = ChatMessage(
                user_id=user_id,
                session_id=session_id,
                gpt_id=gpt_id,
                role=role,
                content=content,
                status=status,
                has_attachments=has_attachments,
            )
            session.add(message)
            if gpt_id:
                self._touch_gpt_chat_in_session(session, gpt_id)
            else:
                self._touch_chat_in_session(session, session_id, user_id=user_id)
            session.flush()
            session.refresh(message)
            return message

    def get_chat_messages(self, chat_id: str, *, user_id: int, gpt_id: str | None = None) -> list[ChatMessage]:
        with self.session() as session:
            query = (
                select(ChatMessage)
                .where(ChatMessage.session_id == chat_id, ChatMessage.user_id == user_id)
                .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
            )
            if gpt_id is None:
                query = query.where(ChatMessage.gpt_id.is_(None))
            else:
                query = query.where(ChatMessage.gpt_id == gpt_id)
            rows = session.scalars(query)
            return list(rows)

    def add_message_attachments(self, message_id: int, attachments: list[dict[str, object]]) -> list[MessageAttachment]:
        with self.session() as session:
            records: list[MessageAttachment] = []
            for attachment in attachments:
                record = MessageAttachment(
                    message_id=message_id,
                    file_name=str(attachment["file_name"]),
                    file_type=str(attachment["type"]),
                    extraction_method=str(attachment.get("extraction_method") or "") or None,
                    quality=dict(attachment.get("quality") or {}),
                )
                session.add(record)
                records.append(record)
            session.flush()
            for record in records:
                session.refresh(record)
            return records

    def get_attachments_by_message_ids(self, message_ids: list[int]) -> dict[int, list[MessageAttachment]]:
        if not message_ids:
            return {}
        with self.session() as session:
            rows = session.scalars(
                select(MessageAttachment)
                .where(MessageAttachment.message_id.in_(message_ids))
                .order_by(MessageAttachment.message_id.asc(), MessageAttachment.id.asc())
            )
            grouped: dict[int, list[MessageAttachment]] = {}
            for row in rows:
                grouped.setdefault(row.message_id, []).append(row)
            return grouped

    def get_recent_chat_history(self, session_id: str, *, user_id: int, limit: int, gpt_id: str | None = None) -> list[ChatMessage]:
        with self.session() as session:
            query = (
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id, ChatMessage.user_id == user_id)
                .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
                .limit(limit * 2)
            )
            if gpt_id is None:
                query = query.where(ChatMessage.gpt_id.is_(None))
            else:
                query = query.where(ChatMessage.gpt_id == gpt_id)
            rows = session.scalars(query)
            return list(reversed(list(rows)))

    def get_retrieval_logs_for_assistant_messages(self, assistant_message_ids: list[int], *, user_id: int) -> dict[int, list[RetrievalLog]]:
        if not assistant_message_ids:
            return {}
        with self.session() as session:
            rows = session.scalars(
                select(RetrievalLog)
                .where(RetrievalLog.assistant_message_id.in_(assistant_message_ids), RetrievalLog.user_id == user_id)
                .order_by(RetrievalLog.assistant_message_id.asc(), RetrievalLog.id.asc())
            )
            grouped: dict[int, list[RetrievalLog]] = {}
            for row in rows:
                grouped.setdefault(row.assistant_message_id, []).append(row)
            return grouped

    def add_retrieval_logs(
        self,
        *,
        assistant_message_id: int,
        user_message_id: int,
        session_id: str,
        user_id: int,
        used_chunks: list[dict[str, str | float]],
    ) -> None:
        with self.session() as session:
            for chunk in used_chunks:
                session.add(
                    RetrievalLog(
                        user_id=user_id,
                        assistant_message_id=assistant_message_id,
                        user_message_id=user_message_id,
                        session_id=session_id,
                        source_file_name=str(chunk["file_name"]),
                        source_file_path=str(chunk["file_path"]),
                        chunk_id=str(chunk["chunk_id"]),
                        chunk_text=str(chunk["text"]),
                        chunk_title=str(chunk.get("title") or "") or None,
                        chapter=str(chunk.get("chapter") or "") or None,
                        section=str(chunk.get("section") or "") or None,
                        page_number=chunk.get("page_number"),
                        tags=list(chunk.get("tags", [])),
                        retrieval_score=float(chunk["score"]),
                    )
                )
            self._touch_chat_in_session(session, session_id, user_id=user_id)

    def _touch_chat_in_session(self, session: Session, chat_id: str, *, user_id: int) -> None:
        chat = session.scalar(select(ChatSession).where(ChatSession.id == chat_id, ChatSession.user_id == user_id))
        if chat is not None:
            chat.updated_at = datetime.now(timezone.utc)

    def _touch_gpt_chat_in_session(self, session: Session, gpt_id: str) -> None:
        chat = session.scalar(select(GPTChatSession).where(GPTChatSession.gpt_id == gpt_id))
        if chat is not None:
            chat.updated_at = datetime.now(timezone.utc)

    def list_settings(self, *, user_id: int) -> list[SettingRecord]:
        with self.session() as session:
            rows = session.scalars(
                select(SettingRecord).where(SettingRecord.user_id == user_id).order_by(SettingRecord.key.asc())
            )
            return list(rows)

    def upsert_setting(self, *, user_id: int, key: str, value: str) -> SettingRecord:
        with self.session() as session:
            record = session.scalar(
                select(SettingRecord).where(SettingRecord.user_id == user_id, SettingRecord.key == key)
            )
            if record is None:
                record = SettingRecord(user_id=user_id, key=key, value=value)
                session.add(record)
            else:
                record.value = value
                record.updated_at = datetime.now(timezone.utc)
            session.flush()
            session.refresh(record)
            return record

    def get_user_learning_preference(self, *, user_id: int) -> UserLearningPreference | None:
        try:
            with self.session() as session:
                return session.scalar(select(UserLearningPreference).where(UserLearningPreference.user_id == user_id))
        except Exception as error:
            if "does not exist" not in str(error).lower():
                raise
            run_migrations(self.database_url, force=True)
            with self.session() as session:
                return session.scalar(select(UserLearningPreference).where(UserLearningPreference.user_id == user_id))

    def upsert_user_learning_preference(self, *, user_id: int, fields: dict[str, object]) -> UserLearningPreference:
        try:
            with self.session() as session:
                record = session.scalar(select(UserLearningPreference).where(UserLearningPreference.user_id == user_id))
                if record is None:
                    record = UserLearningPreference(user_id=user_id, **fields)
                    session.add(record)
                else:
                    for key, value in fields.items():
                        setattr(record, key, value)
                    record.updated_at = datetime.now(timezone.utc)
                session.flush()
                session.refresh(record)
                return record
        except Exception as error:
            if "does not exist" not in str(error).lower():
                raise
            run_migrations(self.database_url, force=True)
            with self.session() as session:
                record = session.scalar(select(UserLearningPreference).where(UserLearningPreference.user_id == user_id))
                if record is None:
                    record = UserLearningPreference(user_id=user_id, **fields)
                    session.add(record)
                else:
                    for key, value in fields.items():
                        setattr(record, key, value)
                    record.updated_at = datetime.now(timezone.utc)
                session.flush()
                session.refresh(record)
                return record

    def get_user_learning_profile(self, *, user_id: int) -> UserLearningProfile | None:
        try:
            with self.session() as session:
                return session.scalar(select(UserLearningProfile).where(UserLearningProfile.user_id == user_id))
        except Exception as error:
            if "does not exist" not in str(error).lower():
                raise
            run_migrations(self.database_url, force=True)
            with self.session() as session:
                return session.scalar(select(UserLearningProfile).where(UserLearningProfile.user_id == user_id))

    def upsert_user_learning_profile(self, *, user_id: int, fields: dict[str, object]) -> UserLearningProfile:
        try:
            with self.session() as session:
                record = session.scalar(select(UserLearningProfile).where(UserLearningProfile.user_id == user_id))
                if record is None:
                    record = UserLearningProfile(user_id=user_id, **fields)
                    session.add(record)
                else:
                    for key, value in fields.items():
                        setattr(record, key, value)
                    record.updated_at = datetime.now(timezone.utc)
                session.flush()
                session.refresh(record)
                return record
        except Exception as error:
            if "does not exist" not in str(error).lower():
                raise
            run_migrations(self.database_url, force=True)
            with self.session() as session:
                record = session.scalar(select(UserLearningProfile).where(UserLearningProfile.user_id == user_id))
                if record is None:
                    record = UserLearningProfile(user_id=user_id, **fields)
                    session.add(record)
                else:
                    for key, value in fields.items():
                        setattr(record, key, value)
                    record.updated_at = datetime.now(timezone.utc)
                session.flush()
                session.refresh(record)
                return record

    def list_user_learning_goals(self, *, user_id: int) -> list[UserLearningGoal]:
        try:
            with self.session() as session:
                rows = session.scalars(
                    select(UserLearningGoal)
                    .where(UserLearningGoal.user_id == user_id)
                    .order_by(UserLearningGoal.is_active.desc(), UserLearningGoal.updated_at.desc(), UserLearningGoal.created_at.desc())
                )
                return list(rows)
        except Exception as error:
            if "does not exist" not in str(error).lower():
                raise
            run_migrations(self.database_url, force=True)
            with self.session() as session:
                rows = session.scalars(
                    select(UserLearningGoal)
                    .where(UserLearningGoal.user_id == user_id)
                    .order_by(UserLearningGoal.is_active.desc(), UserLearningGoal.updated_at.desc(), UserLearningGoal.created_at.desc())
                )
                return list(rows)

    def create_user_learning_goal(self, *, payload: dict[str, object]) -> UserLearningGoal:
        try:
            with self.session() as session:
                record = UserLearningGoal(**payload)
                session.add(record)
                session.flush()
                session.refresh(record)
                return record
        except Exception as error:
            if "does not exist" not in str(error).lower():
                raise
            run_migrations(self.database_url, force=True)
            with self.session() as session:
                record = UserLearningGoal(**payload)
                session.add(record)
                session.flush()
                session.refresh(record)
                return record

    def update_user_learning_goal(self, *, user_id: int, goal_id: str, fields: dict[str, object]) -> UserLearningGoal | None:
        try:
            with self.session() as session:
                record = session.scalar(
                    select(UserLearningGoal).where(UserLearningGoal.id == goal_id, UserLearningGoal.user_id == user_id)
                )
                if record is None:
                    return None
                for key, value in fields.items():
                    setattr(record, key, value)
                record.updated_at = datetime.now(timezone.utc)
                session.flush()
                session.refresh(record)
                return record
        except Exception as error:
            if "does not exist" not in str(error).lower():
                raise
            run_migrations(self.database_url, force=True)
            with self.session() as session:
                record = session.scalar(
                    select(UserLearningGoal).where(UserLearningGoal.id == goal_id, UserLearningGoal.user_id == user_id)
                )
                if record is None:
                    return None
                for key, value in fields.items():
                    setattr(record, key, value)
                record.updated_at = datetime.now(timezone.utc)
                session.flush()
                session.refresh(record)
                return record

    def delete_user_learning_goal(self, *, user_id: int, goal_id: str) -> UserLearningGoal | None:
        try:
            with self.session() as session:
                record = session.scalar(
                    select(UserLearningGoal).where(UserLearningGoal.id == goal_id, UserLearningGoal.user_id == user_id)
                )
                if record is None:
                    return None
                session.delete(record)
                return record
        except Exception as error:
            if "does not exist" not in str(error).lower():
                raise
            run_migrations(self.database_url, force=True)
            with self.session() as session:
                record = session.scalar(
                    select(UserLearningGoal).where(UserLearningGoal.id == goal_id, UserLearningGoal.user_id == user_id)
                )
                if record is None:
                    return None
                session.delete(record)
                return record

    def get_user_by_id(self, user_id: int) -> UserAccount | None:
        with self.session() as session:
            return session.get(UserAccount, user_id)

    def get_user_by_username(self, username: str) -> UserAccount | None:
        with self.session() as session:
            return session.scalar(select(UserAccount).where(UserAccount.username == username))

    def list_users(self) -> list[UserAccount]:
        with self.session() as session:
            rows = session.scalars(select(UserAccount).order_by(UserAccount.username.asc()))
            return list(rows)

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
        with self.session() as session:
            user = UserAccount(
                username=username,
                displayname=displayname,
                role=role,
                password_hash=password_hash,
                status=status,
                force_password_change=force_password_change,
            )
            session.add(user)
            session.flush()
            session.refresh(user)
            return user

    def update_user(self, user_id: int, **fields: object) -> UserAccount | None:
        with self.session() as session:
            user = session.get(UserAccount, user_id)
            if user is None:
                return None
            for key, value in fields.items():
                if value is not None:
                    setattr(user, key, value)
            user.updated_at = datetime.now(timezone.utc)
            session.flush()
            session.refresh(user)
            return user

    def delete_user(self, user_id: int) -> UserAccount | None:
        with self.session() as session:
            user = session.get(UserAccount, user_id)
            if user is None:
                return None
            session.delete(user)
            return user

    def upsert_bootstrap_user(
        self,
        *,
        username: str,
        displayname: str,
        role: str,
        password_hash: str,
    ) -> UserAccount:
        with self.session() as session:
            user = session.scalar(select(UserAccount).where(UserAccount.username == username))
            if user is None:
                user = UserAccount(
                    username=username,
                    displayname=displayname,
                    role=role,
                    status="active",
                    force_password_change=True,
                    password_hash=password_hash,
                )
                session.add(user)
            else:
                user.displayname = displayname
                user.role = role
                user.status = "active"
                user.updated_at = datetime.now(timezone.utc)
            session.flush()
            session.refresh(user)
            return user

    def deactivate_users_not_in(self, usernames: set[str]) -> None:
        with self.session() as session:
            session.execute(
                update(UserAccount)
                .where(UserAccount.username.not_in(usernames))
                .values(status="inactive", updated_at=datetime.now(timezone.utc))
            )

    def assign_orphaned_records_to_user(self, user_id: int) -> None:
        now = datetime.now(timezone.utc)
        with self.session() as session:
            session.execute(update(ChatSession).where(ChatSession.user_id.is_(None)).values(user_id=user_id, updated_at=now))
            session.execute(update(ChatMessage).where(ChatMessage.user_id.is_(None)).values(user_id=user_id))
            session.execute(update(RetrievalLog).where(RetrievalLog.user_id.is_(None)).values(user_id=user_id))
            session.execute(update(SettingRecord).where(SettingRecord.user_id.is_(None)).values(user_id=user_id, updated_at=now))

    def create_user_session(
        self,
        *,
        session_id: str,
        user_id: int,
        issued_at: datetime,
        last_refreshed_at: datetime,
        last_activity_at: datetime,
        expires_at: datetime,
        max_expires_at: datetime,
    ) -> UserSessionRecord:
        with self.session() as session:
            record = UserSessionRecord(
                id=session_id,
                user_id=user_id,
                issued_at=issued_at,
                last_refreshed_at=last_refreshed_at,
                last_activity_at=last_activity_at,
                expires_at=expires_at,
                max_expires_at=max_expires_at,
            )
            session.add(record)
            session.flush()
            session.refresh(record)
            return record

    def get_user_session(self, session_id: str) -> UserSessionRecord | None:
        with self.session() as session:
            return session.get(UserSessionRecord, session_id)

    def update_user_session_activity(self, session_id: str, *, last_activity_at: datetime) -> UserSessionRecord | None:
        with self.session() as session:
            record = session.get(UserSessionRecord, session_id)
            if record is None:
                return None
            record.last_activity_at = last_activity_at
            record.updated_at = last_activity_at
            session.flush()
            session.refresh(record)
            return record

    def refresh_user_session(
        self,
        session_id: str,
        *,
        last_refreshed_at: datetime,
        last_activity_at: datetime,
        expires_at: datetime,
    ) -> UserSessionRecord | None:
        with self.session() as session:
            record = session.get(UserSessionRecord, session_id)
            if record is None:
                return None
            record.last_refreshed_at = last_refreshed_at
            record.last_activity_at = last_activity_at
            record.expires_at = expires_at
            record.updated_at = last_activity_at
            session.flush()
            session.refresh(record)
            return record

    def revoke_user_session(self, session_id: str, *, revoked_at: datetime) -> UserSessionRecord | None:
        with self.session() as session:
            record = session.get(UserSessionRecord, session_id)
            if record is None:
                return None
            record.revoked_at = revoked_at
            record.updated_at = revoked_at
            session.flush()
            session.refresh(record)
            return record

    def revoke_all_user_sessions(self, user_id: int, *, revoked_at: datetime) -> None:
        with self.session() as session:
            session.execute(
                update(UserSessionRecord)
                .where(UserSessionRecord.user_id == user_id, UserSessionRecord.revoked_at.is_(None))
                .values(revoked_at=revoked_at, updated_at=revoked_at)
            )

    def list_learning_paths(self, *, user_id: int, role: str) -> list[LearningPath]:
        with self.session() as session:
            query = select(LearningPath).order_by(LearningPath.updated_at.desc(), LearningPath.created_at.desc())
            if role == "admin":
                rows = session.scalars(query)
                return list(rows)
            rows = session.scalars(
                query.where(
                    (LearningPath.scope == "global") | (LearningPath.owner_user_id == user_id)
                )
            )
            return list(rows)

    def get_learning_path(self, learning_path_id: str) -> LearningPath | None:
        with self.session() as session:
            return session.get(LearningPath, learning_path_id)

    def create_learning_path(self, payload: dict[str, object]) -> LearningPath:
        with self.session() as session:
            record = LearningPath(**payload)
            session.add(record)
            session.flush()
            session.refresh(record)
            return record

    def update_learning_path(self, learning_path_id: str, fields: dict[str, object]) -> LearningPath | None:
        with self.session() as session:
            record = session.get(LearningPath, learning_path_id)
            if record is None:
                return None
            for key, value in fields.items():
                setattr(record, key, value)
            record.updated_at = datetime.now(timezone.utc)
            session.flush()
            session.refresh(record)
            return record

    def delete_learning_path(self, learning_path_id: str) -> LearningPath | None:
        with self.session() as session:
            record = session.get(LearningPath, learning_path_id)
            if record is None:
                return None
            session.delete(record)
            return record

    def list_learning_modules(self, learning_path_id: str) -> list[LearningModule]:
        with self.session() as session:
            rows = session.scalars(
                select(LearningModule)
                .where(LearningModule.learning_path_id == learning_path_id)
                .order_by(LearningModule.order_index.asc(), LearningModule.created_at.asc())
            )
            return list(rows)

    def get_learning_module(self, module_id: str) -> LearningModule | None:
        with self.session() as session:
            return session.get(LearningModule, module_id)

    def create_learning_module(self, payload: dict[str, object]) -> LearningModule:
        with self.session() as session:
            record = LearningModule(**payload)
            session.add(record)
            session.flush()
            session.refresh(record)
            return record

    def update_learning_module(self, module_id: str, fields: dict[str, object]) -> LearningModule | None:
        with self.session() as session:
            record = session.get(LearningModule, module_id)
            if record is None:
                return None
            for key, value in fields.items():
                setattr(record, key, value)
            record.updated_at = datetime.now(timezone.utc)
            session.flush()
            session.refresh(record)
            return record

    def delete_learning_module(self, module_id: str) -> LearningModule | None:
        with self.session() as session:
            record = session.get(LearningModule, module_id)
            if record is None:
                return None
            session.delete(record)
            return record

    def reorder_learning_modules(self, learning_path_id: str, module_orders: list[tuple[str, int]]) -> list[LearningModule]:
        with self.session() as session:
            modules = list(
                session.scalars(
                    select(LearningModule).where(LearningModule.learning_path_id == learning_path_id)
                )
            )
            order_map = {module_id: order_index for module_id, order_index in module_orders}
            for module in modules:
                if module.id in order_map:
                    module.order_index = order_map[module.id]
                    module.updated_at = datetime.now(timezone.utc)
            session.flush()
            rows = session.scalars(
                select(LearningModule)
                .where(LearningModule.learning_path_id == learning_path_id)
                .order_by(LearningModule.order_index.asc(), LearningModule.created_at.asc())
            )
            return list(rows)

    def list_learning_lessons(self, module_id: str) -> list[LearningLesson]:
        with self.session() as session:
            rows = session.scalars(
                select(LearningLesson)
                .where(LearningLesson.module_id == module_id)
                .order_by(LearningLesson.order_index.asc(), LearningLesson.created_at.asc())
            )
            return list(rows)

    def get_learning_lesson(self, lesson_id: str) -> LearningLesson | None:
        with self.session() as session:
            return session.get(LearningLesson, lesson_id)

    def create_learning_lesson(self, payload: dict[str, object]) -> LearningLesson:
        with self.session() as session:
            record = LearningLesson(**payload)
            session.add(record)
            session.flush()
            session.refresh(record)
            return record

    def update_learning_lesson(self, lesson_id: str, fields: dict[str, object]) -> LearningLesson | None:
        with self.session() as session:
            record = session.get(LearningLesson, lesson_id)
            if record is None:
                return None
            for key, value in fields.items():
                setattr(record, key, value)
            record.updated_at = datetime.now(timezone.utc)
            session.flush()
            session.refresh(record)
            return record

    def delete_learning_lesson(self, lesson_id: str) -> LearningLesson | None:
        with self.session() as session:
            record = session.get(LearningLesson, lesson_id)
            if record is None:
                return None
            session.delete(record)
            return record

    def reorder_learning_lessons(self, module_id: str, lesson_orders: list[tuple[str, int]]) -> list[LearningLesson]:
        with self.session() as session:
            lessons = list(
                session.scalars(select(LearningLesson).where(LearningLesson.module_id == module_id))
            )
            order_map = {lesson_id: order_index for lesson_id, order_index in lesson_orders}
            for lesson in lessons:
                if lesson.id in order_map:
                    lesson.order_index = order_map[lesson.id]
                    lesson.updated_at = datetime.now(timezone.utc)
            session.flush()
            rows = session.scalars(
                select(LearningLesson)
                .where(LearningLesson.module_id == module_id)
                .order_by(LearningLesson.order_index.asc(), LearningLesson.created_at.asc())
            )
            return list(rows)

    def replace_learning_path_allowed_files(self, learning_path_id: str, file_ids: list[int]) -> None:
        deduped = sorted(set(int(file_id) for file_id in file_ids))
        with self.session() as session:
            session.execute(
                delete(LearningPathAllowedFile).where(LearningPathAllowedFile.learning_path_id == learning_path_id)
            )
            for file_id in deduped:
                session.add(LearningPathAllowedFile(learning_path_id=learning_path_id, file_id=file_id))

    def replace_learning_path_allowed_tags(self, learning_path_id: str, tags: list[str]) -> None:
        normalized_tags = sorted({str(tag).strip().lower() for tag in tags if str(tag).strip()})
        with self.session() as session:
            session.execute(
                delete(LearningPathAllowedTag).where(LearningPathAllowedTag.learning_path_id == learning_path_id)
            )
            for tag in normalized_tags:
                session.add(LearningPathAllowedTag(learning_path_id=learning_path_id, tag=tag))

    def list_learning_path_allowed_files(self, learning_path_id: str) -> list[LearningPathAllowedFile]:
        with self.session() as session:
            rows = session.scalars(
                select(LearningPathAllowedFile)
                .where(LearningPathAllowedFile.learning_path_id == learning_path_id)
                .order_by(LearningPathAllowedFile.file_id.asc())
            )
            return list(rows)

    def list_learning_path_allowed_tags(self, learning_path_id: str) -> list[LearningPathAllowedTag]:
        with self.session() as session:
            rows = session.scalars(
                select(LearningPathAllowedTag)
                .where(LearningPathAllowedTag.learning_path_id == learning_path_id)
                .order_by(LearningPathAllowedTag.tag.asc())
            )
            return list(rows)

    def get_diagnostic_definition(self, diagnostic_type: str) -> DiagnosticDefinition | None:
        with self.session() as session:
            return session.scalar(
                select(DiagnosticDefinition).where(DiagnosticDefinition.diagnostic_type == diagnostic_type)
            )

    def upsert_diagnostic_definition(self, *, diagnostic_type: str, title: str) -> DiagnosticDefinition:
        with self.session() as session:
            record = session.scalar(
                select(DiagnosticDefinition).where(DiagnosticDefinition.diagnostic_type == diagnostic_type)
            )
            if record is None:
                record = DiagnosticDefinition(id=diagnostic_type.lower(), diagnostic_type=diagnostic_type, title=title)
                session.add(record)
            else:
                record.title = title
                record.updated_at = datetime.now(timezone.utc)
            session.flush()
            session.refresh(record)
            return record

    def get_diagnostic_version(self, *, definition_id: str, version: str) -> DiagnosticVersion | None:
        with self.session() as session:
            return session.scalar(
                select(DiagnosticVersion).where(
                    DiagnosticVersion.definition_id == definition_id,
                    DiagnosticVersion.version == version,
                )
            )

    def list_latest_diagnostic_versions(self) -> list[DiagnosticVersion]:
        with self.session() as session:
            rows = session.scalars(
                select(DiagnosticVersion)
                .where(DiagnosticVersion.is_active.is_(True))
                .order_by(DiagnosticVersion.created_at.desc())
            )
            latest_by_type: dict[str, DiagnosticVersion] = {}
            for row in rows:
                if row.definition_id in latest_by_type:
                    continue
                latest_by_type[row.definition_id] = row
            return list(latest_by_type.values())

    def get_latest_diagnostic_version(self, diagnostic_type: str) -> DiagnosticVersion | None:
        with self.session() as session:
            definition = session.scalar(
                select(DiagnosticDefinition).where(DiagnosticDefinition.diagnostic_type == diagnostic_type)
            )
            if definition is None:
                return None
            return session.scalar(
                select(DiagnosticVersion)
                .where(DiagnosticVersion.definition_id == definition.id, DiagnosticVersion.is_active.is_(True))
                .order_by(DiagnosticVersion.created_at.desc())
                .limit(1)
            )

    def create_diagnostic_version(
        self,
        *,
        definition_id: str,
        version: str,
        source_document_name: str,
        source_document_hash: str,
        content_json: dict[str, object],
    ) -> DiagnosticVersion:
        with self.session() as session:
            record = DiagnosticVersion(
                definition_id=definition_id,
                version=version,
                source_document_name=source_document_name,
                source_document_hash=source_document_hash,
                content_json=content_json,
                is_active=True,
            )
            session.add(record)
            session.flush()
            session.refresh(record)
            return record

    def update_diagnostic_version_content(
        self,
        *,
        version_id: str,
        source_document_name: str,
        source_document_hash: str,
        content_json: dict[str, object],
    ) -> DiagnosticVersion | None:
        with self.session() as session:
            record = session.get(DiagnosticVersion, version_id)
            if record is None:
                return None
            record.source_document_name = source_document_name
            record.source_document_hash = source_document_hash
            record.content_json = content_json
            session.flush()
            session.refresh(record)
            return record

    def replace_diagnostic_version_structure(self, *, version_id: str, definition: dict[str, object]) -> None:
        with self.session() as session:
            session.execute(delete(DiagnosticOption).where(DiagnosticOption.question_id.in_(
                select(DiagnosticQuestion.id).where(DiagnosticQuestion.version_id == version_id)
            )))
            session.execute(delete(DiagnosticQuestion).where(DiagnosticQuestion.version_id == version_id))
            session.execute(delete(DiagnosticScoringRule).where(DiagnosticScoringRule.version_id == version_id))
            session.flush()

            order = 0
            for section in list(definition.get("sections") or []):
                section_id = str(section.get("id") or "")
                for question in list(section.get("questions") or []):
                    question_row = DiagnosticQuestion(
                        version_id=version_id,
                        question_key=str(question.get("id") or ""),
                        section_key=section_id,
                        order_index=order,
                        question_type=str(question.get("type") or "single_choice"),
                        question_text=str(question.get("text") or ""),
                        scoring_json=dict(question.get("scoring") or {}),
                        metadata_json={
                            "min_value": question.get("min_value"),
                            "max_value": question.get("max_value"),
                        },
                    )
                    session.add(question_row)
                    session.flush()
                    order += 1

                    for option_index, option in enumerate(list(question.get("options") or [])):
                        session.add(
                            DiagnosticOption(
                                question_id=question_row.id,
                                option_key=str(option.get("key") or f"o{option_index + 1}"),
                                order_index=option_index,
                                label=str(option.get("label") or ""),
                                value_text=str(option.get("value") or ""),
                                scoring_json=dict(option.get("scoring") or {}),
                                metadata_json={"allows_text": bool(option.get("allows_text", False))},
                            )
                        )

            session.add(
                DiagnosticScoringRule(
                    version_id=version_id,
                    rule_key="default",
                    rule_payload=dict(definition.get("scoring_rules") or {}),
                )
            )

    def create_user_diagnostic_attempt(self, *, user_id: int, definition_versions: dict[str, str]) -> UserDiagnosticAttempt:
        now = datetime.now(timezone.utc)
        with self.session() as session:
            session.execute(
                update(UserDiagnosticAttempt)
                .where(UserDiagnosticAttempt.user_id == user_id)
                .values(is_latest=False, updated_at=now)
            )
            record = UserDiagnosticAttempt(
                user_id=user_id,
                definition_versions=definition_versions,
                status="in_progress",
                is_latest=True,
                started_at=now,
                updated_at=now,
            )
            session.add(record)
            session.flush()
            session.refresh(record)
            return record

    def get_user_diagnostic_attempt(self, *, user_id: int, attempt_id: str) -> UserDiagnosticAttempt | None:
        with self.session() as session:
            return session.scalar(
                select(UserDiagnosticAttempt).where(
                    UserDiagnosticAttempt.id == attempt_id, UserDiagnosticAttempt.user_id == user_id
                )
            )

    def get_latest_user_diagnostic_attempt(self, *, user_id: int) -> UserDiagnosticAttempt | None:
        with self.session() as session:
            return session.scalar(
                select(UserDiagnosticAttempt)
                .where(UserDiagnosticAttempt.user_id == user_id, UserDiagnosticAttempt.is_latest.is_(True))
                .order_by(UserDiagnosticAttempt.started_at.desc())
                .limit(1)
            )

    def list_user_diagnostic_attempts(self, *, user_id: int) -> list[UserDiagnosticAttempt]:
        with self.session() as session:
            rows = session.scalars(
                select(UserDiagnosticAttempt)
                .where(UserDiagnosticAttempt.user_id == user_id)
                .order_by(UserDiagnosticAttempt.started_at.desc())
            )
            return list(rows)

    def delete_user_diagnostic_attempt(self, *, user_id: int, attempt_id: str) -> UserDiagnosticAttempt | None:
        with self.session() as session:
            record = session.scalar(
                select(UserDiagnosticAttempt).where(
                    UserDiagnosticAttempt.id == attempt_id,
                    UserDiagnosticAttempt.user_id == user_id,
                )
            )
            if record is None:
                return None
            was_latest = bool(record.is_latest)
            session.delete(record)
            session.flush()
            if was_latest:
                fallback = session.scalar(
                    select(UserDiagnosticAttempt)
                    .where(UserDiagnosticAttempt.user_id == user_id)
                    .order_by(UserDiagnosticAttempt.started_at.desc())
                    .limit(1)
                )
                if fallback is not None:
                    fallback.is_latest = True
                    fallback.updated_at = datetime.now(timezone.utc)
            return record

    def upsert_user_diagnostic_answer(
        self,
        *,
        attempt_id: str,
        diagnostic_type: str,
        question_key: str,
        answer_json: dict[str, object],
    ) -> UserDiagnosticAnswer:
        with self.session() as session:
            record = session.scalar(
                select(UserDiagnosticAnswer).where(
                    UserDiagnosticAnswer.attempt_id == attempt_id,
                    UserDiagnosticAnswer.diagnostic_type == diagnostic_type,
                    UserDiagnosticAnswer.question_key == question_key,
                )
            )
            if record is None:
                record = UserDiagnosticAnswer(
                    attempt_id=attempt_id,
                    diagnostic_type=diagnostic_type,
                    question_key=question_key,
                    answer_json=answer_json,
                )
                session.add(record)
            else:
                record.answer_json = answer_json
                record.updated_at = datetime.now(timezone.utc)
            session.flush()
            session.refresh(record)
            return record

    def list_user_diagnostic_answers(self, *, attempt_id: str) -> list[UserDiagnosticAnswer]:
        with self.session() as session:
            rows = session.scalars(
                select(UserDiagnosticAnswer)
                .where(UserDiagnosticAnswer.attempt_id == attempt_id)
                .order_by(UserDiagnosticAnswer.id.asc())
            )
            return list(rows)

    def upsert_user_diagnostic_result(self, *, attempt_id: str, result_json: dict[str, object]) -> UserDiagnosticResult:
        with self.session() as session:
            record = session.scalar(
                select(UserDiagnosticResult).where(UserDiagnosticResult.attempt_id == attempt_id)
            )
            if record is None:
                record = UserDiagnosticResult(attempt_id=attempt_id, result_json=result_json)
                session.add(record)
            else:
                record.result_json = result_json
                record.updated_at = datetime.now(timezone.utc)
            session.flush()
            session.refresh(record)
            return record

    def get_user_diagnostic_result(self, *, attempt_id: str) -> UserDiagnosticResult | None:
        with self.session() as session:
            return session.scalar(
                select(UserDiagnosticResult).where(UserDiagnosticResult.attempt_id == attempt_id)
            )

    def mark_user_diagnostic_attempt_completed(self, *, attempt_id: str) -> UserDiagnosticAttempt | None:
        with self.session() as session:
            record = session.get(UserDiagnosticAttempt, attempt_id)
            if record is None:
                return None
            now = datetime.now(timezone.utc)
            record.status = "completed"
            record.completed_at = now
            record.updated_at = now
            session.flush()
            session.refresh(record)
            return record

    def create_learning_state_check(self, payload: dict[str, object]) -> LearningStateCheck:
        with self.session() as session:
            record = LearningStateCheck(**payload)
            session.add(record)
            session.flush()
            session.refresh(record)
            return record

    def list_learning_state_checks(self, *, user_id: int, limit: int = 20) -> list[LearningStateCheck]:
        with self.session() as session:
            rows = session.scalars(
                select(LearningStateCheck)
                .where(LearningStateCheck.user_id == user_id)
                .order_by(LearningStateCheck.created_at.desc())
                .limit(limit)
            )
            return list(rows)

    def create_explanation_feedback(self, payload: dict[str, object]) -> ExplanationFeedback:
        with self.session() as session:
            record = ExplanationFeedback(**payload)
            session.add(record)
            session.flush()
            session.refresh(record)
            return record

    def _default_user_file_enabled(self, record: FileRecord, *, user_id: int) -> bool:
        if record.is_global:
            return True
        return bool(record.uploaded_by_user_id == user_id)

    def _materialize_file_record(self, record: FileRecord) -> None:
        _ = (
            record.id,
            record.file_path,
            record.file_name,
            record.file_type,
            record.extension,
            record.size_bytes,
            record.chunk_count,
            list(record.tags or []),
            record.is_embedded,
            record.is_enabled,
            record.is_system,
            record.is_global,
            record.source_origin,
            record.uploaded_by_user_id,
            record.processing_status,
            record.updated_at,
        )

    def _resolve_user_file_enabled(
        self,
        record: FileRecord,
        *,
        user_id: int,
        is_admin: bool,
        explicit_setting: bool | None,
    ) -> bool:
        if record.is_global and not is_admin:
            return True
        if explicit_setting is not None:
            return bool(explicit_setting)
        return self._default_user_file_enabled(record, user_id=user_id)

    def _upsert_user_file_setting(self, session: Session, *, user_id: int, file_id: int, is_enabled: bool) -> None:
        setting = session.scalar(
            select(UserFileSetting).where(UserFileSetting.user_id == user_id, UserFileSetting.file_id == file_id)
        )
        if setting is None:
            session.add(UserFileSetting(user_id=user_id, file_id=file_id, is_enabled=is_enabled))
            return
        setting.is_enabled = is_enabled
        setting.updated_at = datetime.now(timezone.utc)

    def _upsert_chat_file_setting(self, session: Session, *, chat_id: str, file_id: int, is_enabled: bool) -> None:
        setting = session.scalar(
            select(ChatFileSetting).where(ChatFileSetting.chat_id == chat_id, ChatFileSetting.file_id == file_id)
        )
        if setting is None:
            session.add(ChatFileSetting(chat_id=chat_id, file_id=file_id, is_enabled=is_enabled))
            return
        setting.is_enabled = is_enabled
        setting.updated_at = datetime.now(timezone.utc)

    def _upsert_user_tag_setting(self, session: Session, *, user_id: int, tag: str, is_enabled: bool) -> None:
        setting = session.scalar(select(UserTagSetting).where(UserTagSetting.user_id == user_id, UserTagSetting.tag == tag))
        if setting is None:
            session.add(UserTagSetting(user_id=user_id, tag=tag, is_enabled=is_enabled))
            return
        setting.is_enabled = is_enabled
        setting.updated_at = datetime.now(timezone.utc)

    def _upsert_chat_tag_setting(self, session: Session, *, chat_id: str, tag: str, is_enabled: bool) -> None:
        setting = session.scalar(select(ChatTagSetting).where(ChatTagSetting.chat_id == chat_id, ChatTagSetting.tag == tag))
        if setting is None:
            session.add(ChatTagSetting(chat_id=chat_id, tag=tag, is_enabled=is_enabled))
            return
        setting.is_enabled = is_enabled
        setting.updated_at = datetime.now(timezone.utc)

    def _user_file_settings_map(self, session: Session, *, user_id: int, file_ids: list[int]) -> dict[int, bool]:
        if not file_ids:
            return {}
        rows = session.scalars(
            select(UserFileSetting).where(UserFileSetting.user_id == user_id, UserFileSetting.file_id.in_(file_ids))
        )
        return {row.file_id: row.is_enabled for row in rows}

    def _chat_file_settings_map(self, session: Session, *, chat_id: str | None, file_ids: list[int]) -> dict[int, bool]:
        if not chat_id or not file_ids:
            return {}
        rows = session.scalars(
            select(ChatFileSetting).where(ChatFileSetting.chat_id == chat_id, ChatFileSetting.file_id.in_(file_ids))
        )
        return {row.file_id: row.is_enabled for row in rows}

    def _user_tag_settings_map(self, session: Session, *, user_id: int, tags: set[str]) -> dict[str, bool]:
        if not tags:
            return {}
        rows = session.scalars(select(UserTagSetting).where(UserTagSetting.user_id == user_id, UserTagSetting.tag.in_(tags)))
        return {str(row.tag): row.is_enabled for row in rows}

    def _chat_tag_settings_map(self, session: Session, *, chat_id: str | None, tags: set[str]) -> dict[str, bool]:
        if not chat_id or not tags:
            return {}
        rows = session.scalars(select(ChatTagSetting).where(ChatTagSetting.chat_id == chat_id, ChatTagSetting.tag.in_(tags)))
        return {str(row.tag): row.is_enabled for row in rows}

    def _delete_stale_tag_settings(self, session: Session, *, user_id: int, chat_id: str | None, valid_tags: set[str]) -> None:
        session.execute(delete(UserTagSetting).where(UserTagSetting.user_id == user_id, UserTagSetting.tag.not_in(valid_tags or {""})))
        if chat_id:
            session.execute(delete(ChatTagSetting).where(ChatTagSetting.chat_id == chat_id, ChatTagSetting.tag.not_in(valid_tags or {""})))

    def _tag_counts(self, records: list[FileRecord]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for record in records:
            for tag in sorted(set(str(tag) for tag in list(record.tags or []))):
                counts[tag] = counts.get(tag, 0) + 1
        return counts

    def _all_tags_from_records(self, records: list[FileRecord]) -> set[str]:
        return set(self._tag_counts(records))
