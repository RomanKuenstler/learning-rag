from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserAccount(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    displayname: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="user")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    force_password_change: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class UserSessionRecord(Base):
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_refreshed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    max_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class FileRecord(Base):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_path: Mapped[str] = mapped_column(String(1024), unique=True, nullable=False)
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    extension: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_hash: Mapped[str] = mapped_column("hash", String(64), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    file_type: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    processing_status: Mapped[str] = mapped_column(String(64), nullable=False, default="processed")
    is_embedded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_extraction_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    document_title: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    author: Mapped[str | None] = mapped_column(String(512), nullable=True)
    detected_language: Mapped[str | None] = mapped_column(String(64), nullable=True)
    index_schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    processor_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    normalization_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    extraction_strategy_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    chunk_size: Mapped[int] = mapped_column(Integer, nullable=False, default=600)
    chunk_overlap: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    processing_signature: Mapped[str] = mapped_column(String(2048), nullable=False, default="")
    extraction_quality: Mapped[dict] = mapped_column(JSON, default=dict)
    processing_flags: Mapped[dict] = mapped_column(JSON, default=dict)
    ocr_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    uploaded_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_global: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_origin: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    last_processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    chunks: Mapped[list["ChunkRecord"]] = relationship(back_populates="file", cascade="all, delete-orphan")


class ChunkRecord(Base):
    __tablename__ = "chunks"
    __table_args__ = (Index("ix_chunks_file_id_chunk_id", "file_id", "chunk_id", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"), nullable=False)
    chunk_id: Mapped[str] = mapped_column(String(128), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    chapter: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    section: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    heading_path: Mapped[list[str]] = mapped_column(JSON, default=list)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extraction_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    quality_flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    chunk_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    file: Mapped[FileRecord] = relationship(back_populates="chunks")


class ChatSession(Base):
    __tablename__ = "chats"

    id: Mapped[str] = mapped_column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    chat_type: Mapped[str] = mapped_column(String(32), nullable=False, default="normal")
    learning_path_id: Mapped[str | None] = mapped_column(
        ForeignKey("learning_paths.id", ondelete="SET NULL"), nullable=True, index=True
    )
    chat_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class GPTRecord(Base):
    __tablename__ = "gpts"

    id: Mapped[str] = mapped_column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    instructions: Mapped[str] = mapped_column(Text, nullable=False, default="")
    assistant_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="simple")
    personalization: Mapped[dict] = mapped_column(JSON, default=dict)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    file_settings: Mapped[dict] = mapped_column(JSON, default=dict)
    tag_settings: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class GPTChatSession(Base):
    __tablename__ = "gpt_chats"

    id: Mapped[str] = mapped_column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    gpt_id: Mapped[str] = mapped_column(ForeignKey("gpts.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_session_id_created_at", "session_id", "created_at"),
        Index("ix_chat_messages_user_id_created_at", "user_id", "created_at"),
        Index("ix_chat_messages_gpt_id_created_at", "gpt_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False)
    gpt_id: Mapped[str | None] = mapped_column(ForeignKey("gpts.id", ondelete="CASCADE"), nullable=True, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed")
    has_attachments: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    attachments: Mapped[list["MessageAttachment"]] = relationship(back_populates="message", cascade="all, delete-orphan")


class MessageAttachment(Base):
    __tablename__ = "message_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(64), nullable=False)
    extraction_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    quality: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    message: Mapped[ChatMessage] = relationship(back_populates="attachments")


class RetrievalLog(Base):
    __tablename__ = "retrieval_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    assistant_message_id: Mapped[int] = mapped_column(ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False)
    user_message_id: Mapped[int] = mapped_column(ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    source_file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    chunk_id: Mapped[str] = mapped_column(String(128), nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_title: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    chapter: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    section: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    retrieval_score: Mapped[float] = mapped_column(Float, nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SettingRecord(Base):
    __tablename__ = "settings"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_settings_user_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class UserFileSetting(Base):
    __tablename__ = "user_file_settings"
    __table_args__ = (UniqueConstraint("user_id", "file_id", name="uq_user_file_settings_user_file"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ChatFileSetting(Base):
    __tablename__ = "chat_file_settings"
    __table_args__ = (UniqueConstraint("chat_id", "file_id", name="uq_chat_file_settings_chat_file"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[str] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class UserTagSetting(Base):
    __tablename__ = "user_tag_settings"
    __table_args__ = (UniqueConstraint("user_id", "tag", name="uq_user_tag_settings_user_tag"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    tag: Mapped[str] = mapped_column(String(255), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ChatTagSetting(Base):
    __tablename__ = "chat_tag_settings"
    __table_args__ = (UniqueConstraint("chat_id", "tag", name="uq_chat_tag_settings_chat_tag"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[str] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True)
    tag: Mapped[str] = mapped_column(String(255), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class LearningPath(Base):
    __tablename__ = "learning_paths"

    id: Mapped[str] = mapped_column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    scope: Mapped[str] = mapped_column(String(16), nullable=False, default="user")
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    subject: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    difficulty_level: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    estimated_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    skilltree_definition: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class LearningModule(Base):
    __tablename__ = "learning_modules"
    __table_args__ = (UniqueConstraint("learning_path_id", "order_index", name="uq_learning_modules_path_order"),)

    id: Mapped[str] = mapped_column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    learning_path_id: Mapped[str] = mapped_column(
        ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    learning_objectives: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class LearningLesson(Base):
    __tablename__ = "learning_lessons"
    __table_args__ = (UniqueConstraint("module_id", "order_index", name="uq_learning_lessons_module_order"),)

    id: Mapped[str] = mapped_column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    module_id: Mapped[str] = mapped_column(ForeignKey("learning_modules.id", ondelete="CASCADE"), nullable=False, index=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    objectives: Mapped[list[str]] = mapped_column(JSON, default=list)
    teaching_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class LearningPathAllowedFile(Base):
    __tablename__ = "learning_path_allowed_files"
    __table_args__ = (UniqueConstraint("learning_path_id", "file_id", name="uq_learning_path_allowed_files"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    learning_path_id: Mapped[str] = mapped_column(
        ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LearningPathAllowedTag(Base):
    __tablename__ = "learning_path_allowed_tags"
    __table_args__ = (UniqueConstraint("learning_path_id", "tag", name="uq_learning_path_allowed_tags"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    learning_path_id: Mapped[str] = mapped_column(
        ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tag: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class UserLearningNodeProgress(Base):
    __tablename__ = "user_learning_node_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "learning_path_id", "node_id", name="uq_user_learning_node_progress_user_path_node"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    learning_path_id: Mapped[str] = mapped_column(
        ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="in_progress")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class LearningNodeSession(Base):
    __tablename__ = "learning_node_sessions"
    __table_args__ = (
        UniqueConstraint("user_id", "learning_path_id", "node_id", name="uq_learning_node_sessions_user_path_node"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    learning_path_id: Mapped[str] = mapped_column(
        ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    node_type: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    route_path: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="created")
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class UserLearningNodeContext(Base):
    __tablename__ = "user_learning_node_contexts"
    __table_args__ = (
        UniqueConstraint("user_id", "learning_path_id", "node_id", name="uq_user_learning_node_contexts_user_path_node"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    learning_path_id: Mapped[str] = mapped_column(
        ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    node_type: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    generation_reason: Mapped[str] = mapped_column(String(64), nullable=False, default="on_demand")
    context_json: Mapped[dict] = mapped_column(JSON, default=dict)
    course_context_json: Mapped[dict] = mapped_column(JSON, default=dict)
    chapter_branch_context_json: Mapped[dict] = mapped_column(JSON, default=dict)
    prior_node_context_json: Mapped[dict] = mapped_column(JSON, default=dict)
    target_node_context_json: Mapped[dict] = mapped_column(JSON, default=dict)
    next_node_context_json: Mapped[dict] = mapped_column(JSON, default=dict)
    ksa_context_json: Mapped[dict] = mapped_column(JSON, default=dict)
    readiness_context_json: Mapped[dict] = mapped_column(JSON, default=dict)
    derived_assumptions_json: Mapped[dict] = mapped_column(JSON, default=dict)
    source_hash: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class UserLearningNodeExecutionAttempt(Base):
    __tablename__ = "user_learning_node_execution_attempts"

    id: Mapped[str] = mapped_column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    learning_path_id: Mapped[str] = mapped_column(
        ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    node_type: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="in_progress")
    generation_reason: Mapped[str] = mapped_column(String(64), nullable=False, default="on_start")
    package_json: Mapped[dict] = mapped_column(JSON, default=dict)
    responses_json: Mapped[dict] = mapped_column(JSON, default=dict)
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    context_snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)
    source_node_window_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ContentAsset(Base):
    __tablename__ = "content_assets"

    id: Mapped[str] = mapped_column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="downloadable_file", index=True)
    media_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="", index=True)
    bucket_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    normalized_filename: Mapped[str] = mapped_column(String(512), nullable=False, default="", index=True)
    file_extension: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False, default="", index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, default="seeded_course_asset", index=True)
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False, default="course", index=True)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    learning_path_id: Mapped[str | None] = mapped_column(ForeignKey("learning_paths.id", ondelete="SET NULL"), nullable=True, index=True)
    node_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    chapter_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    branch_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    uploaded_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    attempt_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    asset_status: Mapped[str] = mapped_column(String(32), nullable=False, default="ready", index=True)
    alt_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    caption: Mapped[str] = mapped_column(Text, nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    download_label: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    file_category: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    is_optional: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    poster_asset_id: Mapped[str | None] = mapped_column(ForeignKey("content_assets.id", ondelete="SET NULL"), nullable=True)
    transcript_asset_id: Mapped[str | None] = mapped_column(ForeignKey("content_assets.id", ondelete="SET NULL"), nullable=True)
    thumbnail_asset_id: Mapped[str | None] = mapped_column(ForeignKey("content_assets.id", ondelete="SET NULL"), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class UserLearningPreference(Base):
    __tablename__ = "user_learning_preferences"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_learning_preferences_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    preferred_pace: Mapped[str] = mapped_column(String(32), nullable=False, default="balanced")
    explanation_depth: Mapped[str] = mapped_column(String(32), nullable=False, default="balanced")
    examples_vs_theory: Mapped[str] = mapped_column(String(32), nullable=False, default="balanced")
    structure_preference: Mapped[str] = mapped_column(String(32), nullable=False, default="balanced")
    checkpoint_frequency: Mapped[str] = mapped_column(String(32), nullable=False, default="medium")
    encouragement_level: Mapped[str] = mapped_column(String(32), nullable=False, default="balanced")
    guidance_level: Mapped[str] = mapped_column(String(32), nullable=False, default="balanced")
    recap_frequency: Mapped[str] = mapped_column(String(32), nullable=False, default="medium")
    preferred_learning_format: Mapped[str] = mapped_column(String(32), nullable=False, default="mixed")
    custom_preference_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class UserLearningProfile(Base):
    __tablename__ = "user_learning_profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_learning_profiles_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    current_skill_areas: Mapped[list[str]] = mapped_column(JSON, default=list)
    interests: Mapped[list[str]] = mapped_column(JSON, default=list)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    work_experience: Mapped[list[str]] = mapped_column(JSON, default=list)
    education_history: Mapped[list[str]] = mapped_column(JSON, default=list)
    current_reason_for_learning: Mapped[str] = mapped_column(Text, nullable=False, default="")
    preferred_form_of_address: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    profile_display_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    about_me: Mapped[str] = mapped_column(Text, nullable=False, default="")
    contact_location: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    general_title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    date_of_birth: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    learning_context_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class UserLearningGoal(Base):
    __tablename__ = "user_learning_goals"

    id: Mapped[str] = mapped_column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_topic: Mapped[str] = mapped_column(String(255), nullable=False)
    reason_for_learning: Mapped[str] = mapped_column(Text, nullable=False, default="")
    target_level: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    priority: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class UserKSAProfile(Base):
    __tablename__ = "user_ksa_profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_ksa_profiles_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    has_assessment: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    assessment_version: Mapped[str] = mapped_column(String(32), nullable=False, default="ksa-v1")
    profile_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class UserKSAAssessmentAttempt(Base):
    __tablename__ = "user_ksa_assessment_attempts"

    id: Mapped[str] = mapped_column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assessment_version: Mapped[str] = mapped_column(String(32), nullable=False, default="ksa-v1")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="in_progress")
    answers_json: Mapped[dict] = mapped_column(JSON, default=dict)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class UserKSADrillAttempt(Base):
    __tablename__ = "user_ksa_drill_attempts"

    id: Mapped[str] = mapped_column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assessment_version: Mapped[str] = mapped_column(String(32), nullable=False, default="ksa-drill-v1")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="in_progress")
    selected_topic_keys_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    question_set_json: Mapped[list[dict]] = mapped_column(JSON, default=list)
    source_topic_input_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    topic_classification_json: Mapped[dict] = mapped_column(JSON, default=dict)
    rounds_json: Mapped[list[dict]] = mapped_column(JSON, default=list)
    answers_json: Mapped[dict] = mapped_column(JSON, default=dict)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DiagnosticDefinition(Base):
    __tablename__ = "diagnostic_definitions"
    __table_args__ = (UniqueConstraint("diagnostic_type", name="uq_diagnostic_definitions_type"),)

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    diagnostic_type: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DiagnosticVersion(Base):
    __tablename__ = "diagnostic_versions"
    __table_args__ = (UniqueConstraint("definition_id", "version", name="uq_diagnostic_versions_definition_version"),)

    id: Mapped[str] = mapped_column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    definition_id: Mapped[str] = mapped_column(
        ForeignKey("diagnostic_definitions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_document_name: Mapped[str] = mapped_column(String(512), nullable=False)
    source_document_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content_json: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class DiagnosticQuestion(Base):
    __tablename__ = "diagnostic_questions"
    __table_args__ = (UniqueConstraint("version_id", "question_key", name="uq_diagnostic_questions_version_question_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version_id: Mapped[str] = mapped_column(
        ForeignKey("diagnostic_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_key: Mapped[str] = mapped_column(String(128), nullable=False)
    section_key: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    question_type: Mapped[str] = mapped_column(String(32), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    scoring_json: Mapped[dict] = mapped_column(JSON, default=dict)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class DiagnosticOption(Base):
    __tablename__ = "diagnostic_options"
    __table_args__ = (UniqueConstraint("question_id", "option_key", name="uq_diagnostic_options_question_option_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("diagnostic_questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    option_key: Mapped[str] = mapped_column(String(128), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    value_text: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    scoring_json: Mapped[dict] = mapped_column(JSON, default=dict)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class DiagnosticScoringRule(Base):
    __tablename__ = "diagnostic_scoring_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version_id: Mapped[str] = mapped_column(
        ForeignKey("diagnostic_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_key: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class UserDiagnosticAttempt(Base):
    __tablename__ = "user_diagnostic_attempts"

    id: Mapped[str] = mapped_column(String(128), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    definition_versions: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="in_progress")
    is_latest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class UserDiagnosticAnswer(Base):
    __tablename__ = "user_diagnostic_answers"
    __table_args__ = (UniqueConstraint("attempt_id", "diagnostic_type", "question_key", name="uq_user_diagnostic_answer"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    attempt_id: Mapped[str] = mapped_column(
        ForeignKey("user_diagnostic_attempts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    diagnostic_type: Mapped[str] = mapped_column(String(16), nullable=False)
    question_key: Mapped[str] = mapped_column(String(128), nullable=False)
    answer_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class UserDiagnosticResult(Base):
    __tablename__ = "user_diagnostic_results"
    __table_args__ = (UniqueConstraint("attempt_id", name="uq_user_diagnostic_results_attempt"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    attempt_id: Mapped[str] = mapped_column(
        ForeignKey("user_diagnostic_attempts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class LearningStateCheck(Base):
    __tablename__ = "learning_state_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    chat_id: Mapped[str | None] = mapped_column(ForeignKey("chats.id", ondelete="SET NULL"), nullable=True, index=True)
    mood: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    perceived_difficulty: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    needs_pause_or_input: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    preferred_format: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ExplanationFeedback(Base):
    __tablename__ = "explanation_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id: Mapped[int | None] = mapped_column(
        ForeignKey("chat_messages.id", ondelete="SET NULL"), nullable=True, index=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    feedback_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    re_explain_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class UserLearningPersonalizationLayer(Base):
    __tablename__ = "user_learning_personalization_layers"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_learning_personalization_layers_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_engine_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    identity_context_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    resolved_identity_context_rules: Mapped[dict] = mapped_column(JSON, default=dict)
    goal_intent_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    resolved_goal_rules: Mapped[dict] = mapped_column(JSON, default=dict)
    declared_preferences_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    resolved_declared_tutor_rules: Mapped[dict] = mapped_column(JSON, default=dict)
    diagnosed_learning_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    resolved_diagnostic_rules: Mapped[dict] = mapped_column(JSON, default=dict)
    capability_mastery_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    resolved_capability_rules: Mapped[dict] = mapped_column(JSON, default=dict)
    live_adaptation_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    resolved_live_adaptation_rules: Mapped[dict] = mapped_column(JSON, default=dict)
    last_source_hashes_json: Mapped[dict] = mapped_column(JSON, default=dict)
    source_to_group_trace_json: Mapped[dict] = mapped_column(JSON, default=dict)
    change_log_json: Mapped[list[dict]] = mapped_column(JSON, default=list)
    identity_context_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    goal_intent_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    declared_preferences_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    diagnosed_learning_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    capability_mastery_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    live_adaptation_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
