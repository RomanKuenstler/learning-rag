from __future__ import annotations

from services.common.postgres import FileFilterState, TagFilterState
from services.common.models import ChatMessage, ChatSession, FileRecord, GPTRecord, MessageAttachment, RetrievalLog
from services.retriever.schemas.chat import (
    AttachmentRead,
    ChatRead,
    FilterFileRead,
    FilterTagRead,
    GptConfigRead,
    GptFileSettingRead,
    GptPersonalizationRead,
    GptRead,
    GptSettingsRead,
    GptTagSettingRead,
    LibraryFileRead,
    MessageRead,
    SourceRead,
)


def map_chat(chat: ChatSession) -> ChatRead:
    return ChatRead(
        id=chat.id,
        chat_name=chat.chat_name,
        gpt_id=getattr(chat, "gpt_id", None),
        is_archived=chat.is_archived,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
    )


def map_source(log: RetrievalLog) -> SourceRead:
    return SourceRead(
        chunk_id=log.chunk_id,
        file_name=log.source_file_name,
        file_path=log.source_file_path,
        title=log.chunk_title,
        chapter=log.chapter,
        section=log.section,
        page_number=log.page_number,
        score=log.retrieval_score,
        tags=list(log.tags or []),
    )


def map_attachment(attachment: MessageAttachment | dict[str, object]) -> AttachmentRead:
    if isinstance(attachment, MessageAttachment):
        return AttachmentRead(
            file_name=attachment.file_name,
            file_type=attachment.file_type,
            extraction_method=attachment.extraction_method,
            quality=dict(attachment.quality or {}),
        )
    return AttachmentRead(
        file_name=str(attachment["file_name"]),
        file_type=str(attachment["type"]),
        extraction_method=str(attachment.get("extraction_method") or "") or None,
        quality=dict(attachment.get("quality") or {}),
    )


def map_message(message: ChatMessage, sources: list[RetrievalLog] | None = None) -> MessageRead:
    return MessageRead(
        id=str(message.id),
        chat_id=message.session_id,
        gpt_id=getattr(message, "gpt_id", None),
        role=message.role,
        content=message.content,
        status=message.status,
        has_attachments=message.has_attachments,
        created_at=message.created_at,
        sources=[map_source(log) for log in (sources or [])],
    )


def map_gpt(gpt: GPTRecord, *, chat_id: str | None = None) -> GptRead:
    personalization = dict(gpt.personalization or {})
    settings = dict(gpt.settings or {})
    file_settings = dict(gpt.file_settings or {})
    tag_settings = dict(gpt.tag_settings or {})
    return GptRead(
        id=gpt.id,
        name=gpt.name,
        description=gpt.description or "",
        instructions=gpt.instructions or "",
        assistant_mode=gpt.assistant_mode,
        chat_id=chat_id,
        created_at=gpt.created_at,
        updated_at=gpt.updated_at,
        config=GptConfigRead(
            personalization=GptPersonalizationRead(
                base_style=str(personalization.get("base_style") or "default"),
                warm=str(personalization.get("warm") or "default"),
                enthusiastic=str(personalization.get("enthusiastic") or "default"),
                headers_and_lists=str(personalization.get("headers_and_lists") or "default"),
            ),
            settings=GptSettingsRead(
                chat_history_messages_count=int(settings.get("chat_history_messages_count", 5) or 5),
                max_similarities=int(settings.get("max_similarities", 8) or 8),
                min_similarities=int(settings.get("min_similarities", 2) or 2),
                similarity_score_threshold=float(settings.get("similarity_score_threshold", 0.7) or 0.7),
            ),
            files_enabled=bool(settings.get("files_enabled", True)),
            tags_enabled=bool(settings.get("tags_enabled", True)),
            file_settings=[
                GptFileSettingRead(file_id=int(file_id), is_enabled=bool(is_enabled))
                for file_id, is_enabled in sorted(file_settings.items(), key=lambda item: int(item[0]))
            ],
            tag_settings=[
                GptTagSettingRead(tag=str(tag), is_enabled=bool(is_enabled))
                for tag, is_enabled in sorted(tag_settings.items(), key=lambda item: str(item[0]))
            ],
        ),
    )


def map_library_file(
    record: FileRecord,
    *,
    can_delete: bool = False,
    can_toggle_enabled: bool = True,
    owner_user_id: int | None = None,
    owner_username: str | None = None,
    owner_displayname: str | None = None,
    is_global: bool | None = None,
    source_origin: str | None = None,
    is_owned_by_current_user: bool = False,
) -> LibraryFileRead:
    return LibraryFileRead(
        id=record.id,
        file_name=record.file_name,
        file_path=record.file_path,
        file_type=record.file_type,
        extension=record.extension,
        size_bytes=record.size_bytes,
        chunk_count=record.chunk_count,
        tags=list(record.tags or []),
        is_embedded=record.is_embedded,
        is_enabled=record.is_enabled,
        is_system=record.is_system,
        is_global=record.is_global if is_global is None else is_global,
        source_origin=record.source_origin if source_origin is None else source_origin,
        uploaded_by_user_id=record.uploaded_by_user_id,
        owner_user_id=owner_user_id if owner_user_id is not None else record.uploaded_by_user_id,
        owner_username=owner_username,
        owner_displayname=owner_displayname,
        is_owned_by_current_user=is_owned_by_current_user,
        can_delete=can_delete,
        can_disable=can_toggle_enabled,
        can_toggle_enabled=can_toggle_enabled,
        processing_status=record.processing_status,
        updated_at=record.updated_at,
    )


def map_filter_file(record: FileFilterState) -> FilterFileRead:
    return FilterFileRead(
        file_id=record.file_id,
        file_name=record.file_name,
        file_path=record.file_path,
        tags=list(record.tags),
        global_is_enabled=record.global_is_enabled,
        scoped_is_enabled=record.scoped_is_enabled,
        is_enabled=record.is_enabled,
        is_locked=record.is_locked,
        updated_at=record.updated_at,
    )


def map_filter_tag(record: TagFilterState) -> FilterTagRead:
    return FilterTagRead(
        tag=record.tag,
        file_count=record.file_count,
        global_is_enabled=record.global_is_enabled,
        scoped_is_enabled=record.scoped_is_enabled,
        is_enabled=record.is_enabled,
        is_locked=record.is_locked,
    )
