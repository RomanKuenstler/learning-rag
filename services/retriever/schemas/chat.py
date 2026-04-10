from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChatCreateResponse(BaseModel):
    id: str
    chat_name: str
    chat_type: str = "normal"
    learning_path_id: str | None = None
    gpt_id: str | None = None
    created_at: datetime
    updated_at: datetime


class ChatRead(ChatCreateResponse):
    is_archived: bool = False


class ChatUpdateRequest(BaseModel):
    chat_name: str = Field(min_length=1)


class SourceRead(BaseModel):
    chunk_id: str
    file_name: str
    file_path: str
    title: str | None = None
    chapter: str | None = None
    section: str | None = None
    page_number: int | None = None
    score: float
    tags: list[str] = Field(default_factory=list)


class MessageRead(BaseModel):
    id: str
    chat_id: str
    gpt_id: str | None = None
    role: str
    content: str
    status: str
    has_attachments: bool = False
    created_at: datetime
    sources: list[SourceRead] = Field(default_factory=list)
    attachments: list["AttachmentRead"] = Field(default_factory=list)


class MessageCreateRequest(BaseModel):
    message: str = Field(min_length=1)
    assistant_mode: str | None = None


class AttachmentRead(BaseModel):
    file_name: str
    file_type: str
    extraction_method: str | None = None
    quality: dict = Field(default_factory=dict)


class MessageCreateResponse(BaseModel):
    chat_id: str
    gpt_id: str | None = None
    user_message: MessageRead
    assistant_message: MessageRead
    assistant_mode: str
    sources: list[SourceRead] = Field(default_factory=list)
    attachments_used: list[AttachmentRead] = Field(default_factory=list)


class SettingsRead(BaseModel):
    chat_history_messages_count: int
    max_similarities: int
    min_similarities: int
    similarity_score_threshold: float
    default_assistant_mode: str
    available_assistant_modes: list[str] = Field(default_factory=list)


class SettingsUpdateRequest(BaseModel):
    chat_history_messages_count: int = Field(ge=1, le=50)
    max_similarities: int = Field(ge=1, le=50)
    min_similarities: int = Field(ge=1, le=50)
    similarity_score_threshold: float = Field(ge=0.0, le=1.0)


PersonalizationBaseStyle = Literal["default", "professional", "friendly", "direct", "quirky", "efficient", "sceptical"]
PersonalizationLevel = Literal["more", "default", "less"]


class PersonalizationRead(BaseModel):
    base_style: PersonalizationBaseStyle = "default"
    warm: PersonalizationLevel = "default"
    enthusiastic: PersonalizationLevel = "default"
    headers_and_lists: PersonalizationLevel = "default"
    custom_instructions: str = ""
    nickname: str = ""
    occupation: str = ""
    more_about_user: str = ""


class PersonalizationUpdateRequest(BaseModel):
    base_style: PersonalizationBaseStyle
    warm: PersonalizationLevel
    enthusiastic: PersonalizationLevel
    headers_and_lists: PersonalizationLevel
    custom_instructions: str = Field(default="", max_length=4000)
    nickname: str = Field(default="", max_length=255)
    occupation: str = Field(default="", max_length=255)
    more_about_user: str = Field(default="", max_length=4000)


class GptPersonalizationRead(BaseModel):
    base_style: PersonalizationBaseStyle = "default"
    warm: PersonalizationLevel = "default"
    enthusiastic: PersonalizationLevel = "default"
    headers_and_lists: PersonalizationLevel = "default"


class GptPersonalizationUpdateRequest(BaseModel):
    base_style: PersonalizationBaseStyle = "default"
    warm: PersonalizationLevel = "default"
    enthusiastic: PersonalizationLevel = "default"
    headers_and_lists: PersonalizationLevel = "default"


class GptSettingsRead(BaseModel):
    chat_history_messages_count: int = 5
    max_similarities: int = 8
    min_similarities: int = 2
    similarity_score_threshold: float = 0.7


class GptSettingsUpdateRequest(BaseModel):
    chat_history_messages_count: int = Field(ge=1, le=50)
    max_similarities: int = Field(ge=1, le=50)
    min_similarities: int = Field(ge=1, le=50)
    similarity_score_threshold: float = Field(ge=0.0, le=1.0)


class GptFileSettingRead(BaseModel):
    file_id: int
    is_enabled: bool


class GptTagSettingRead(BaseModel):
    tag: str
    is_enabled: bool


class GptConfigRead(BaseModel):
    personalization: GptPersonalizationRead = Field(default_factory=GptPersonalizationRead)
    settings: GptSettingsRead = Field(default_factory=GptSettingsRead)
    files_enabled: bool = True
    tags_enabled: bool = True
    file_settings: list[GptFileSettingRead] = Field(default_factory=list)
    tag_settings: list[GptTagSettingRead] = Field(default_factory=list)


class GptConfigUpdateRequest(BaseModel):
    personalization: GptPersonalizationUpdateRequest = Field(default_factory=GptPersonalizationUpdateRequest)
    settings: GptSettingsUpdateRequest
    files_enabled: bool = True
    tags_enabled: bool = True
    file_settings: list[GptFileSettingRead] = Field(default_factory=list)
    tag_settings: list[GptTagSettingRead] = Field(default_factory=list)


class GptRead(BaseModel):
    id: str
    name: str
    description: str = ""
    instructions: str = ""
    assistant_mode: str
    chat_id: str | None = None
    created_at: datetime
    updated_at: datetime
    config: GptConfigRead = Field(default_factory=GptConfigRead)


class GptCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=4000)
    instructions: str = Field(default="", max_length=12000)
    assistant_mode: str
    config: GptConfigUpdateRequest


class GptUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    instructions: str | None = Field(default=None, max_length=12000)
    assistant_mode: str | None = None
    config: GptConfigUpdateRequest | None = None


class GptPreviewMessageCreateRequest(BaseModel):
    message: str = Field(min_length=1)
    gpt: GptCreateRequest
    preview_messages: list[MessageRead] = Field(default_factory=list)


class GptChatRead(BaseModel):
    gpt: GptRead
    messages: list[MessageRead] = Field(default_factory=list)


class GptDeleteResponse(BaseModel):
    id: str
    deleted: bool = True


class ChatDownloadMessageRead(BaseModel):
    role: str
    content: str
    created_at: datetime
    sources: list[SourceRead] = Field(default_factory=list)
    attachments: list[AttachmentRead] = Field(default_factory=list)


class ChatDownloadResponse(BaseModel):
    chat_id: str
    chat_name: str
    is_archived: bool = False
    created_at: datetime
    updated_at: datetime
    messages: list[ChatDownloadMessageRead] = Field(default_factory=list)


class LibraryFileRead(BaseModel):
    id: int
    file_name: str
    file_path: str
    file_type: str
    extension: str
    size_bytes: int
    chunk_count: int
    tags: list[str] = Field(default_factory=list)
    is_embedded: bool
    is_enabled: bool
    is_system: bool = False
    is_global: bool = False
    source_origin: str = "unknown"
    uploaded_by_user_id: int | None = None
    owner_user_id: int | None = None
    owner_username: str | None = None
    owner_displayname: str | None = None
    is_owned_by_current_user: bool = False
    can_delete: bool = False
    can_disable: bool = True
    can_toggle_enabled: bool = True
    processing_status: str
    updated_at: datetime


class LibrarySummaryRead(BaseModel):
    total_files: int
    embedded_files: int
    total_chunks: int


class LibraryListResponse(BaseModel):
    files: list[LibraryFileRead] = Field(default_factory=list)
    summary: LibrarySummaryRead
    allowed_extensions: list[str] = Field(default_factory=list)
    max_upload_files: int
    upload_max_file_size_mb: int
    default_tag: str


class LibraryFileUpdateRequest(BaseModel):
    is_enabled: bool | None = None


class LibraryUploadResponse(BaseModel):
    files: list[LibraryFileRead] = Field(default_factory=list)


class FilterFileRead(BaseModel):
    file_id: int
    file_name: str
    file_path: str
    tags: list[str] = Field(default_factory=list)
    global_is_enabled: bool
    scoped_is_enabled: bool
    is_enabled: bool
    is_locked: bool = False
    updated_at: datetime


class FilterFileListResponse(BaseModel):
    files: list[FilterFileRead] = Field(default_factory=list)


class FilterTagRead(BaseModel):
    tag: str
    file_count: int
    global_is_enabled: bool
    scoped_is_enabled: bool
    is_enabled: bool
    is_locked: bool = False


class FilterTagListResponse(BaseModel):
    tags: list[FilterTagRead] = Field(default_factory=list)


class FilterUpdateRequest(BaseModel):
    is_enabled: bool


class ErrorResponse(BaseModel):
    detail: str


class HealthResponse(BaseModel):
    status: str


class SystemServiceStatusRead(BaseModel):
    key: str
    label: str
    description: str
    status: str
    detail: str


class SystemStatusResponse(BaseModel):
    checked_at: datetime
    services: list[SystemServiceStatusRead] = Field(default_factory=list)
