from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from services.common.config import Settings
from services.common.models import (
    LearningLesson,
    LearningModule,
    LearningPath,
    UserAccount,
    UserLearningGoal,
    UserLearningPreference,
    UserLearningProfile,
)
from services.embedder.chunking import Chunker
from services.embedder.embedding import EmbeddingClient
from services.embedder.postgres_client import EmbedderPostgresClient
from services.embedder.processor import FileProcessor
from services.embedder.qdrant_client import EmbedderQdrantClient
from services.retriever.attachment_client import AttachmentProcessingClient
from services.retriever.auth import AuthContext, AuthManager
from services.retriever.chat_history import ChatHistoryService
from services.retriever.llm_client import LlmClient
from services.retriever.prompt_builder import PromptBuilder
from services.retriever.qdrant_client import RetrieverQdrantClient
from services.retriever.repositories.chat_repository import ChatRepository
from services.retriever.retriever import RetrievalService
from services.retriever.schemas.auth import AdminUserRead, AuthLoginResponse, AuthMeResponse, PasswordChangeResponse
from services.retriever.schemas.chat import (
    ChatDownloadMessageRead,
    ChatDownloadResponse,
    GptChatRead,
    GptConfigRead,
    GptConfigUpdateRequest,
    GptCreateRequest,
    GptDeleteResponse,
    GptPreviewMessageCreateRequest,
    GptRead,
    GptSettingsRead,
    GptUpdateRequest,
    PersonalizationRead,
    PersonalizationUpdateRequest,
    SettingsRead,
    SettingsUpdateRequest,
)
from services.retriever.schemas.learning import (
    LearningLessonCreateRequest,
    LearningLessonRead,
    LearningLessonUpdateRequest,
    LearningLessonReorderRequest,
    LearningModuleCreateRequest,
    LearningModuleRead,
    LearningModuleReorderRequest,
    LearningModuleUpdateRequest,
    LearningPathCreateRequest,
    LearningPathListResponse,
    LearningPathRead,
    LearningPathUpdateRequest,
)
from services.retriever.schemas.learning_profile import (
    LearningGoalCreateRequest,
    LearningGoalRead,
    LearningGoalUpdateRequest,
    LearningPreferencesRead,
    LearningPreferencesUpdateRequest,
    LearningProfileBundleRead,
    LearningProfileContextRead,
    LearningProfileContextUpdateRequest,
)
from services.retriever.services.chat_naming import generate_chat_name
from services.retriever.services.library_manager import LibraryManager, UploadFilePayload
from services.retriever.services.message_mapper import map_attachment, map_chat, map_filter_file, map_filter_tag, map_gpt, map_message, map_source

RUNTIME_SETTING_KEYS = {
    "chat_history_messages_count",
    "max_similarities",
    "min_similarities",
    "similarity_score_threshold",
}

PERSONALIZATION_DEFAULTS = {
    "base_style": "default",
    "warm": "default",
    "enthusiastic": "default",
    "headers_and_lists": "default",
    "custom_instructions": "",
    "nickname": "",
    "occupation": "",
    "more_about_user": "",
}

PERSONALIZATION_SETTING_KEYS = set(PERSONALIZATION_DEFAULTS)
GPT_PERSONALIZATION_DEFAULTS = {
    "base_style": "default",
    "warm": "default",
    "enthusiastic": "default",
    "headers_and_lists": "default",
}
LEARNING_PREFERENCE_DEFAULTS = {
    "preferred_pace": "balanced",
    "explanation_depth": "balanced",
    "examples_vs_theory": "balanced",
    "structure_preference": "balanced",
    "checkpoint_frequency": "medium",
    "encouragement_level": "balanced",
    "guidance_level": "balanced",
    "recap_frequency": "medium",
    "preferred_learning_format": "mixed",
    "custom_preference_note": "",
}

LEARNING_CONTEXT_DEFAULTS = {
    "education_background": "",
    "current_skill_areas": [],
    "interests": [],
    "professional_context": "",
    "current_reason_for_learning": "",
    "preferred_form_of_address": "",
    "learning_context_notes": "",
}

SUPPORTED_ROLES = {"admin", "user", "student"}
EXAMPLE_LEARNING_PATH_TITLE = "Example: Docker Fundamentals"
EXAMPLE_LEARNING_PATH_TITLE_SECOND = "Example: Python Learning Sprint"
logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RetrieverDependencies:
    chat_repository: ChatRepository
    history_service: ChatHistoryService
    retrieval_service: RetrievalService
    prompt_builder: PromptBuilder
    llm_client: LlmClient
    library_manager: LibraryManager
    attachment_client: AttachmentProcessingClient
    settings: Settings
    auth_manager: AuthManager | None = None


class RetrieverAppService:
    def __init__(self, deps: RetrieverDependencies) -> None:
        self.chat_repository = deps.chat_repository
        self.history_service = deps.history_service
        self.retrieval_service = deps.retrieval_service
        self.prompt_builder = deps.prompt_builder
        self.llm_client = deps.llm_client
        self.library_manager = deps.library_manager
        self.attachment_client = deps.attachment_client
        self.auth_manager = deps.auth_manager
        self.settings = deps.settings
        if self.auth_manager is not None:
            self.auth_manager.bootstrap_users()
        self._ensure_example_learning_path()

    def login(self, username: str, password: str) -> AuthLoginResponse:
        assert self.auth_manager is not None
        return self.auth_manager.login(username, password)

    def me(self, auth: AuthContext) -> AuthMeResponse:
        assert self.auth_manager is not None
        return self.auth_manager.me(auth)

    def logout(self, auth: AuthContext) -> None:
        assert self.auth_manager is not None
        self.auth_manager.logout(auth.session.id)

    def change_password(self, auth: AuthContext, *, current_password: str | None, new_password: str, confirm_password: str) -> PasswordChangeResponse:
        assert self.auth_manager is not None
        return self.auth_manager.change_password(
            auth=auth,
            current_password=current_password,
            new_password=new_password,
            confirm_password=confirm_password,
        )

    def list_admin_users(self, auth: AuthContext) -> list[AdminUserRead]:
        assert self.auth_manager is not None
        self.auth_manager.require_admin(auth)
        return self.auth_manager.list_users()

    def create_admin_user(self, auth: AuthContext, *, username: str, displayname: str, role: str) -> AdminUserRead:
        assert self.auth_manager is not None
        self.auth_manager.require_admin(auth)
        normalized_role = role.strip().lower()
        if normalized_role not in SUPPORTED_ROLES:
            raise ValueError("Unsupported role")
        return self.auth_manager.create_user(username=username, displayname=displayname, role=normalized_role)

    def update_admin_user(self, auth: AuthContext, user_id: int, **fields: object) -> AdminUserRead | None:
        assert self.auth_manager is not None
        self.auth_manager.require_admin(auth)
        if auth.user.id == user_id and fields.get("status") == "inactive":
            raise ValueError("Admin cannot deactivate own account")
        if "role" in fields and fields["role"] is not None:
            normalized_role = str(fields["role"]).strip().lower()
            if normalized_role not in SUPPORTED_ROLES:
                raise ValueError("Unsupported role")
            fields["role"] = normalized_role
        return self.auth_manager.update_user(user_id, **fields)

    def delete_admin_user(self, auth: AuthContext, user_id: int) -> AdminUserRead | None:
        assert self.auth_manager is not None
        self.auth_manager.require_admin(auth)
        return self.auth_manager.delete_user(actor=auth, user_id=user_id)

    def create_chat(self, user: UserAccount):
        self._ensure_student_cannot_use_standard_chat(user)
        chat = self.chat_repository.create_chat(user.id, generate_chat_name())
        return map_chat(chat)

    def list_chats(self, user: UserAccount):
        self._ensure_student_cannot_use_standard_chat(user)
        return [map_chat(chat) for chat in self.chat_repository.list_chats(user.id, archived=False)]

    def list_archived_chats(self, user: UserAccount):
        self._ensure_student_cannot_use_standard_chat(user)
        return [map_chat(chat) for chat in self.chat_repository.list_chats(user.id, archived=True)]

    def get_chat(self, user: UserAccount, chat_id: str):
        self._ensure_student_cannot_use_standard_chat(user)
        chat = self.chat_repository.get_chat(user.id, chat_id)
        if chat is None:
            return None
        return map_chat(chat)

    def get_chat_messages(self, user: UserAccount, chat_id: str):
        self._ensure_student_cannot_use_standard_chat(user)
        messages = self.chat_repository.list_messages(user.id, chat_id)
        assistant_ids = [message.id for message in messages if message.role == "assistant"]
        message_ids = [message.id for message in messages]
        sources_by_message = self.chat_repository.get_sources_by_assistant_message(user.id, assistant_ids)
        attachments_by_message = self.chat_repository.get_attachments_by_message_ids(message_ids)
        return [
            map_message(message, sources_by_message.get(message.id)).model_copy(
                update={"attachments": [map_attachment(item) for item in attachments_by_message.get(message.id, [])]}
            )
            for message in messages
        ]

    def rename_chat(self, user: UserAccount, chat_id: str, chat_name: str):
        self._ensure_student_cannot_use_standard_chat(user)
        normalized_name = chat_name.strip()
        if not normalized_name:
            raise ValueError("Chat name cannot be empty")
        chat = self.chat_repository.rename_chat(user.id, chat_id, normalized_name)
        if chat is None:
            return None
        return map_chat(chat)

    def delete_chat(self, user: UserAccount, chat_id: str):
        self._ensure_student_cannot_use_standard_chat(user)
        chat = self.chat_repository.delete_chat(user.id, chat_id)
        if chat is None:
            return None
        return map_chat(chat)

    def archive_chat(self, user: UserAccount, chat_id: str):
        self._ensure_student_cannot_use_standard_chat(user)
        chat = self.chat_repository.set_chat_archived(user.id, chat_id, True)
        if chat is None:
            return None
        return map_chat(chat)

    def unarchive_chat(self, user: UserAccount, chat_id: str):
        self._ensure_student_cannot_use_standard_chat(user)
        chat = self.chat_repository.set_chat_archived(user.id, chat_id, False)
        if chat is None:
            return None
        return map_chat(chat)

    def download_chat(self, user: UserAccount, chat_id: str):
        self._ensure_student_cannot_use_standard_chat(user)
        chat = self.chat_repository.get_chat(user.id, chat_id)
        if chat is None:
            return None

        messages = self.chat_repository.list_messages(user.id, chat_id)
        assistant_ids = [message.id for message in messages if message.role == "assistant"]
        message_ids = [message.id for message in messages]
        sources_by_message = self.chat_repository.get_sources_by_assistant_message(user.id, assistant_ids)
        attachments_by_message = self.chat_repository.get_attachments_by_message_ids(message_ids)

        return ChatDownloadResponse(
            chat_id=chat.id,
            chat_name=chat.chat_name,
            is_archived=chat.is_archived,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
            messages=[
                ChatDownloadMessageRead(
                    role=message.role,
                    content=message.content,
                    created_at=message.created_at,
                    sources=[map_source(log) for log in sources_by_message.get(message.id, [])],
                    attachments=[map_attachment(item) for item in attachments_by_message.get(message.id, [])],
                )
                for message in messages
            ],
        )

    def list_gpts(self, user: UserAccount) -> list[GptRead]:
        self._ensure_student_cannot_use_gpts(user)
        records = self.chat_repository.list_gpts(user.id)
        result: list[GptRead] = []
        for record in records:
            chat = self.chat_repository.get_gpt_chat(user.id, record.id)
            result.append(map_gpt(record, chat_id=chat.id if chat else None))
        return result

    def get_gpt(self, user: UserAccount, gpt_id: str) -> GptRead | None:
        self._ensure_student_cannot_use_gpts(user)
        record = self.chat_repository.get_gpt(user.id, gpt_id)
        if record is None:
            return None
        chat = self.chat_repository.get_gpt_chat(user.id, record.id)
        return map_gpt(record, chat_id=chat.id if chat else None)

    def create_gpt(self, user: UserAccount, payload: GptCreateRequest) -> GptRead:
        self._ensure_student_cannot_use_gpts(user)
        persisted = self.chat_repository.create_gpt(user.id, self._build_gpt_payload(payload))
        chat = self.chat_repository.ensure_gpt_chat(persisted.id)
        return map_gpt(persisted, chat_id=chat.id)

    def update_gpt(self, user: UserAccount, gpt_id: str, payload: GptUpdateRequest) -> GptRead | None:
        self._ensure_student_cannot_use_gpts(user)
        fields = self._build_gpt_update_fields(payload)
        record = self.chat_repository.update_gpt(user.id, gpt_id, fields)
        if record is None:
            return None
        chat = self.chat_repository.ensure_gpt_chat(record.id)
        return map_gpt(record, chat_id=chat.id)

    def delete_gpt(self, user: UserAccount, gpt_id: str) -> GptDeleteResponse | None:
        self._ensure_student_cannot_use_gpts(user)
        record = self.chat_repository.delete_gpt(user.id, gpt_id)
        if record is None:
            return None
        return GptDeleteResponse(id=record.id, deleted=True)

    def get_gpt_chat(self, user: UserAccount, gpt_id: str) -> GptChatRead | None:
        self._ensure_student_cannot_use_gpts(user)
        gpt = self.chat_repository.get_gpt(user.id, gpt_id)
        if gpt is None:
            return None
        chat = self.chat_repository.ensure_gpt_chat(gpt.id)
        messages = self.chat_repository.list_gpt_messages(user.id, chat.id, gpt.id)
        assistant_ids = [message.id for message in messages if message.role == "assistant"]
        message_ids = [message.id for message in messages]
        sources_by_message = self.chat_repository.get_sources_by_assistant_message(user.id, assistant_ids)
        attachments_by_message = self.chat_repository.get_attachments_by_message_ids(message_ids)
        return GptChatRead(
            gpt=map_gpt(gpt, chat_id=chat.id),
            messages=[
                map_message(message, sources_by_message.get(message.id)).model_copy(
                    update={"attachments": [map_attachment(item) for item in attachments_by_message.get(message.id, [])]}
                )
                for message in messages
            ],
        )

    def clear_gpt_chat(self, user: UserAccount, gpt_id: str) -> GptChatRead | None:
        self._ensure_student_cannot_use_gpts(user)
        gpt = self.chat_repository.get_gpt(user.id, gpt_id)
        if gpt is None:
            return None
        chat = self.chat_repository.clear_gpt_chat(user.id, gpt_id)
        if chat is None:
            chat = self.chat_repository.ensure_gpt_chat(gpt_id)
        return GptChatRead(gpt=map_gpt(gpt, chat_id=chat.id), messages=[])

    def download_gpt_chat(self, user: UserAccount, gpt_id: str) -> ChatDownloadResponse | None:
        self._ensure_student_cannot_use_gpts(user)
        payload = self.get_gpt_chat(user, gpt_id)
        if payload is None or payload.gpt.chat_id is None:
            return None
        return ChatDownloadResponse(
            chat_id=payload.gpt.chat_id,
            chat_name=payload.gpt.name,
            is_archived=False,
            created_at=payload.gpt.created_at,
            updated_at=payload.gpt.updated_at,
            messages=[
                ChatDownloadMessageRead(
                    role=message.role,
                    content=message.content,
                    created_at=message.created_at,
                    sources=message.sources,
                    attachments=message.attachments,
                )
                for message in payload.messages
            ],
        )

    def preview_gpt_message(self, user: UserAccount, payload: GptPreviewMessageCreateRequest) -> dict[str, object]:
        self._ensure_student_cannot_use_gpts(user)
        self._validate_gpt_request(payload.gpt)
        gpt_payload = payload.gpt
        gpt_config = self._extract_gpt_runtime_config(gpt_payload.config)
        retrieved_chunks = self.retrieval_service.retrieve(
            payload.message.strip(),
            user_id=user.id,
            chat_id=None,
            is_admin=user.role == "admin",
            gpt_overrides={
                "files_enabled": gpt_config["files_enabled"],
                "tags_enabled": gpt_config["tags_enabled"],
                "file_settings": gpt_config["file_settings"],
                "tag_settings": gpt_config["tag_settings"],
            },
            min_results=gpt_config["settings"]["min_similarities"],
            max_results=gpt_config["settings"]["max_similarities"],
            score_threshold=gpt_config["settings"]["similarity_score_threshold"],
        )
        history = [(message.role, message.content) for message in payload.preview_messages]
        response = self._generate_response(
            assistant_mode=self._resolve_assistant_mode(gpt_payload.assistant_mode),
            user_content=payload.message.strip(),
            history=history,
            retrieved_chunks=retrieved_chunks,
            personalization=gpt_config["personalization"],
            gpt_instructions=gpt_payload.instructions,
            processed_attachments=[],
        )
        user_message = {
            "id": f"preview-user-{len(payload.preview_messages) + 1}",
            "chat_id": "preview",
            "gpt_id": None,
            "role": "user",
            "content": payload.message.strip(),
            "status": "completed",
            "has_attachments": False,
            "created_at": "2026-04-01T00:00:00Z",
            "sources": [],
            "attachments": [],
        }
        assistant_message = {
            "id": f"preview-assistant-{len(payload.preview_messages) + 2}",
            "chat_id": "preview",
            "gpt_id": None,
            "role": "assistant",
            "content": response,
            "status": "completed",
            "has_attachments": False,
            "created_at": "2026-04-01T00:00:00Z",
            "sources": [map_source_from_chunk(chunk) for chunk in retrieved_chunks],
            "attachments": [],
        }
        return {
            "chat_id": "preview",
            "gpt_id": None,
            "user_message": user_message,
            "assistant_message": assistant_message,
            "assistant_mode": self._resolve_assistant_mode(gpt_payload.assistant_mode),
            "sources": assistant_message["sources"],
            "attachments_used": [],
        }

    def list_library_files(self, user: UserAccount, *, include_other_users: bool = False):
        return self.library_manager.list_files(user, include_other_users=include_other_users)

    def update_library_file(self, user: UserAccount, file_id: int, *, is_enabled: bool):
        return self.library_manager.update_file_state(user, file_id, is_enabled=is_enabled)

    def delete_library_file(self, user: UserAccount, file_id: int):
        return self.library_manager.delete_file(user, file_id)

    def upload_library_files(self, user: UserAccount, uploads: list[UploadFilePayload], tags_by_file_raw: str | None):
        tags_by_file = self.library_manager.parse_tags_mapping(tags_by_file_raw)
        files = self.library_manager.upload_files(user, uploads, tags_by_file)
        return {"files": files}

    def list_user_file_filters(self, user: UserAccount):
        return {
            "files": [
                map_filter_file(item)
                for item in self.chat_repository.list_user_file_filters(user.id, is_admin=user.role == "admin")
            ]
        }

    def update_user_file_filter(self, user: UserAccount, file_id: int, *, is_enabled: bool):
        record = self.chat_repository.set_user_file_filter(
            user.id,
            file_id,
            is_enabled,
            is_admin=user.role == "admin",
        )
        if record is None:
            return None
        return map_filter_file(record)

    def list_chat_file_filters(self, user: UserAccount, chat_id: str):
        records = self.chat_repository.list_chat_file_filters(user.id, chat_id, is_admin=user.role == "admin")
        if records is None:
            return None
        return {"files": [map_filter_file(item) for item in records]}

    def update_chat_file_filter(self, user: UserAccount, chat_id: str, file_id: int, *, is_enabled: bool):
        record = self.chat_repository.set_chat_file_filter(
            user.id,
            chat_id,
            file_id,
            is_enabled,
            is_admin=user.role == "admin",
        )
        if record is None:
            return None
        return map_filter_file(record)

    def list_user_tag_filters(self, user: UserAccount):
        return {"tags": [map_filter_tag(item) for item in self.chat_repository.list_user_tag_filters(user.id)]}

    def update_user_tag_filter(self, user: UserAccount, tag: str, *, is_enabled: bool):
        record = self.chat_repository.set_user_tag_filter(user.id, tag, is_enabled)
        if record is None:
            return None
        return map_filter_tag(record)

    def list_chat_tag_filters(self, user: UserAccount, chat_id: str):
        records = self.chat_repository.list_chat_tag_filters(user.id, chat_id)
        if records is None:
            return None
        return {"tags": [map_filter_tag(item) for item in records]}

    def update_chat_tag_filter(self, user: UserAccount, chat_id: str, tag: str, *, is_enabled: bool):
        record = self.chat_repository.set_chat_tag_filter(user.id, chat_id, tag, is_enabled)
        if record is None:
            return None
        return map_filter_tag(record)

    def get_settings(self, user: UserAccount) -> SettingsRead:
        self._load_runtime_settings(user)
        return SettingsRead(
            chat_history_messages_count=self.history_service.history_limit,
            max_similarities=self.retrieval_service.max_results,
            min_similarities=self.retrieval_service.min_results,
            similarity_score_threshold=self.retrieval_service.score_threshold,
            default_assistant_mode=self.settings.default_assistant_mode,
            available_assistant_modes=self.settings.available_assistant_modes,
        )

    def update_settings(self, user: UserAccount, payload: SettingsUpdateRequest) -> SettingsRead:
        if payload.min_similarities > payload.max_similarities:
            raise ValueError("min similarities cannot be greater than max similarities")

        self.history_service.history_limit = payload.chat_history_messages_count
        self.retrieval_service.max_results = payload.max_similarities
        self.retrieval_service.min_results = payload.min_similarities
        self.retrieval_service.score_threshold = payload.similarity_score_threshold

        persisted_values = {
            "chat_history_messages_count": payload.chat_history_messages_count,
            "max_similarities": payload.max_similarities,
            "min_similarities": payload.min_similarities,
            "similarity_score_threshold": payload.similarity_score_threshold,
        }
        for key, value in persisted_values.items():
            self.chat_repository.upsert_setting(user.id, key, json.dumps(value))
        return self.get_settings(user)

    def get_personalization(self, user: UserAccount) -> PersonalizationRead:
        stored_values = self._load_stored_setting_values(user)
        return PersonalizationRead(
            base_style=str(stored_values.get("base_style", PERSONALIZATION_DEFAULTS["base_style"])),
            warm=str(stored_values.get("warm", PERSONALIZATION_DEFAULTS["warm"])),
            enthusiastic=str(stored_values.get("enthusiastic", PERSONALIZATION_DEFAULTS["enthusiastic"])),
            headers_and_lists=str(
                stored_values.get("headers_and_lists", PERSONALIZATION_DEFAULTS["headers_and_lists"])
            ),
            custom_instructions=str(
                stored_values.get("custom_instructions", PERSONALIZATION_DEFAULTS["custom_instructions"])
            ),
            nickname=str(stored_values.get("nickname", PERSONALIZATION_DEFAULTS["nickname"])),
            occupation=str(stored_values.get("occupation", PERSONALIZATION_DEFAULTS["occupation"])),
            more_about_user=str(stored_values.get("more_about_user", PERSONALIZATION_DEFAULTS["more_about_user"])),
        )

    def update_personalization(self, user: UserAccount, payload: PersonalizationUpdateRequest) -> PersonalizationRead:
        for key, value in payload.model_dump().items():
            self.chat_repository.upsert_setting(user.id, key, json.dumps(str(value).strip()))
        return self.get_personalization(user)

    def get_learning_profile_bundle(self, user: UserAccount) -> LearningProfileBundleRead:
        preference = self.chat_repository.get_user_learning_preference(user.id)
        profile = self.chat_repository.get_user_learning_profile(user.id)
        goals = self.chat_repository.list_user_learning_goals(user.id)
        return LearningProfileBundleRead(
            preferences=self._build_learning_preferences_read(preference),
            context=self._build_learning_context_read(profile),
            goals=[self._build_learning_goal_read(goal) for goal in goals],
        )

    def update_learning_preferences(self, user: UserAccount, payload: LearningPreferencesUpdateRequest) -> LearningPreferencesRead:
        existing = self.chat_repository.get_user_learning_preference(user.id)
        fields = payload.model_dump(exclude_unset=True)
        next_values = {
            **LEARNING_PREFERENCE_DEFAULTS,
            **(self._serialize_learning_preference(existing) if existing else {}),
            **fields,
        }
        next_values["custom_preference_note"] = str(next_values.get("custom_preference_note", "")).strip()
        updated = self.chat_repository.upsert_user_learning_preference(
            user.id,
            fields={
                "preferred_pace": next_values["preferred_pace"],
                "explanation_depth": next_values["explanation_depth"],
                "examples_vs_theory": next_values["examples_vs_theory"],
                "structure_preference": next_values["structure_preference"],
                "checkpoint_frequency": next_values["checkpoint_frequency"],
                "encouragement_level": next_values["encouragement_level"],
                "guidance_level": next_values["guidance_level"],
                "recap_frequency": next_values["recap_frequency"],
                "preferred_learning_format": next_values["preferred_learning_format"],
                "custom_preference_note": next_values["custom_preference_note"],
            },
        )
        return self._build_learning_preferences_read(updated)

    def update_learning_context(self, user: UserAccount, payload: LearningProfileContextUpdateRequest) -> LearningProfileContextRead:
        existing = self.chat_repository.get_user_learning_profile(user.id)
        fields = payload.model_dump(exclude_unset=True)
        next_values = {
            **LEARNING_CONTEXT_DEFAULTS,
            **(self._serialize_learning_profile(existing) if existing else {}),
            **fields,
        }
        if "current_skill_areas" in next_values:
            next_values["current_skill_areas"] = self._normalize_string_list(next_values["current_skill_areas"])
        if "interests" in next_values:
            next_values["interests"] = self._normalize_string_list(next_values["interests"])
        for field_name in {
            "education_background",
            "professional_context",
            "current_reason_for_learning",
            "preferred_form_of_address",
            "learning_context_notes",
        }:
            next_values[field_name] = str(next_values.get(field_name, "")).strip()
        updated = self.chat_repository.upsert_user_learning_profile(
            user.id,
            fields={
                "education_background": next_values["education_background"],
                "current_skill_areas": next_values["current_skill_areas"],
                "interests": next_values["interests"],
                "professional_context": next_values["professional_context"],
                "current_reason_for_learning": next_values["current_reason_for_learning"],
                "preferred_form_of_address": next_values["preferred_form_of_address"],
                "learning_context_notes": next_values["learning_context_notes"],
            },
        )
        return self._build_learning_context_read(updated)

    def create_learning_goal(self, user: UserAccount, payload: LearningGoalCreateRequest) -> LearningGoalRead:
        record = self.chat_repository.create_user_learning_goal(
            {
                "user_id": user.id,
                "target_topic": payload.target_topic.strip(),
                "reason_for_learning": payload.reason_for_learning.strip(),
                "target_level": payload.target_level.strip(),
                "deadline": payload.deadline,
                "priority": payload.priority,
                "notes": payload.notes.strip(),
                "is_active": payload.is_active,
            }
        )
        return self._build_learning_goal_read(record)

    def update_learning_goal(self, user: UserAccount, goal_id: str, payload: LearningGoalUpdateRequest) -> LearningGoalRead | None:
        fields = payload.model_dump(exclude_unset=True)
        for field_name in {"target_topic", "reason_for_learning", "target_level", "notes"}:
            if field_name in fields and isinstance(fields[field_name], str):
                fields[field_name] = fields[field_name].strip()
        updated = self.chat_repository.update_user_learning_goal(user.id, goal_id, fields)
        if updated is None:
            return None
        return self._build_learning_goal_read(updated)

    def delete_learning_goal(self, user: UserAccount, goal_id: str) -> LearningGoalRead | None:
        deleted = self.chat_repository.delete_user_learning_goal(user.id, goal_id)
        if deleted is None:
            return None
        return self._build_learning_goal_read(deleted)

    def list_learning_paths(self, user: UserAccount) -> LearningPathListResponse:
        paths = self.chat_repository.list_learning_paths(user_id=user.id, role=user.role)
        return LearningPathListResponse(paths=[self._build_learning_path_read(user, path) for path in paths])

    def create_learning_path(self, user: UserAccount, payload: LearningPathCreateRequest) -> LearningPathRead:
        self._ensure_learning_path_create_allowed(user, payload.scope)
        normalized_tags = self._normalize_tags(payload.allowed_tags)
        record = self.chat_repository.create_learning_path(
            {
                "scope": payload.scope,
                "owner_user_id": None if payload.scope == "global" else user.id,
                "title": payload.title.strip(),
                "description": payload.description.strip(),
                "subject": payload.subject.strip(),
                "difficulty_level": payload.difficulty_level.strip(),
                "estimated_duration_minutes": payload.estimated_duration_minutes,
                "status": payload.status,
            }
        )
        self.chat_repository.replace_learning_path_allowed_files(record.id, payload.allowed_file_ids)
        self.chat_repository.replace_learning_path_allowed_tags(record.id, normalized_tags)
        refreshed = self.chat_repository.get_learning_path(record.id)
        assert refreshed is not None
        return self._build_learning_path_read(user, refreshed)

    def get_learning_path(self, user: UserAccount, learning_path_id: str) -> LearningPathRead | None:
        record = self.chat_repository.get_learning_path(learning_path_id)
        if record is None or not self._can_view_learning_path(user, record):
            return None
        return self._build_learning_path_read(user, record)

    def update_learning_path(
        self,
        user: UserAccount,
        learning_path_id: str,
        payload: LearningPathUpdateRequest,
    ) -> LearningPathRead | None:
        record = self.chat_repository.get_learning_path(learning_path_id)
        if record is None:
            return None
        self._ensure_learning_path_edit_allowed(user, record)
        fields = payload.model_dump(exclude_unset=True)
        if "title" in fields and isinstance(fields["title"], str):
            fields["title"] = fields["title"].strip()
        if "description" in fields and isinstance(fields["description"], str):
            fields["description"] = fields["description"].strip()
        if "subject" in fields and isinstance(fields["subject"], str):
            fields["subject"] = fields["subject"].strip()
        if "difficulty_level" in fields and isinstance(fields["difficulty_level"], str):
            fields["difficulty_level"] = fields["difficulty_level"].strip()
        fields.pop("allowed_file_ids", None)
        fields.pop("allowed_tags", None)
        updated = self.chat_repository.update_learning_path(learning_path_id, fields)
        if updated is None:
            return None
        if payload.allowed_file_ids is not None:
            self.chat_repository.replace_learning_path_allowed_files(updated.id, payload.allowed_file_ids)
        if payload.allowed_tags is not None:
            self.chat_repository.replace_learning_path_allowed_tags(updated.id, self._normalize_tags(payload.allowed_tags))
        refreshed = self.chat_repository.get_learning_path(updated.id)
        assert refreshed is not None
        return self._build_learning_path_read(user, refreshed)

    def delete_learning_path(self, user: UserAccount, learning_path_id: str) -> LearningPathRead | None:
        record = self.chat_repository.get_learning_path(learning_path_id)
        if record is None:
            return None
        self._ensure_learning_path_edit_allowed(user, record, deleting=True)
        deleted = self.chat_repository.delete_learning_path(learning_path_id)
        if deleted is None:
            return None
        return self._build_learning_path_read(user, deleted)

    def create_learning_module(
        self,
        user: UserAccount,
        learning_path_id: str,
        payload: LearningModuleCreateRequest,
    ) -> LearningModuleRead | None:
        learning_path = self.chat_repository.get_learning_path(learning_path_id)
        if learning_path is None:
            return None
        self._ensure_learning_path_edit_allowed(user, learning_path)
        existing = self.chat_repository.list_learning_modules(learning_path_id)
        module = self.chat_repository.create_learning_module(
            {
                "learning_path_id": learning_path_id,
                "order_index": len(existing),
                "title": payload.title.strip(),
                "description": payload.description.strip(),
                "learning_objectives": [item.strip() for item in payload.learning_objectives if item.strip()],
            }
        )
        return self._build_learning_module_read(module, lessons=[])

    def update_learning_module(
        self,
        user: UserAccount,
        module_id: str,
        payload: LearningModuleUpdateRequest,
    ) -> LearningModuleRead | None:
        module = self.chat_repository.get_learning_module(module_id)
        if module is None:
            return None
        learning_path = self.chat_repository.get_learning_path(module.learning_path_id)
        if learning_path is None:
            return None
        self._ensure_learning_path_edit_allowed(user, learning_path)
        fields = payload.model_dump(exclude_unset=True)
        if "title" in fields and isinstance(fields["title"], str):
            fields["title"] = fields["title"].strip()
        if "description" in fields and isinstance(fields["description"], str):
            fields["description"] = fields["description"].strip()
        if "learning_objectives" in fields and fields["learning_objectives"] is not None:
            fields["learning_objectives"] = [
                item.strip() for item in list(fields["learning_objectives"]) if str(item).strip()
            ]
        updated = self.chat_repository.update_learning_module(module_id, fields)
        if updated is None:
            return None
        lessons = self.chat_repository.list_learning_lessons(updated.id)
        return self._build_learning_module_read(updated, lessons=lessons)

    def delete_learning_module(self, user: UserAccount, module_id: str) -> LearningModuleRead | None:
        module = self.chat_repository.get_learning_module(module_id)
        if module is None:
            return None
        learning_path = self.chat_repository.get_learning_path(module.learning_path_id)
        if learning_path is None:
            return None
        self._ensure_learning_path_edit_allowed(user, learning_path)
        deleted = self.chat_repository.delete_learning_module(module_id)
        if deleted is None:
            return None
        return self._build_learning_module_read(deleted, lessons=[])

    def reorder_learning_modules(
        self,
        user: UserAccount,
        learning_path_id: str,
        payload: LearningModuleReorderRequest,
    ) -> list[LearningModuleRead] | None:
        learning_path = self.chat_repository.get_learning_path(learning_path_id)
        if learning_path is None:
            return None
        self._ensure_learning_path_edit_allowed(user, learning_path)
        module_orders = [(item.id, item.order_index) for item in payload.modules]
        modules = self.chat_repository.reorder_learning_modules(learning_path_id, module_orders)
        lessons_by_module = {
            module.id: self.chat_repository.list_learning_lessons(module.id)
            for module in modules
        }
        return [self._build_learning_module_read(module, lessons=lessons_by_module.get(module.id, [])) for module in modules]

    def create_learning_lesson(
        self,
        user: UserAccount,
        module_id: str,
        payload: LearningLessonCreateRequest,
    ) -> LearningLessonRead | None:
        module = self.chat_repository.get_learning_module(module_id)
        if module is None:
            return None
        learning_path = self.chat_repository.get_learning_path(module.learning_path_id)
        if learning_path is None:
            return None
        self._ensure_learning_path_edit_allowed(user, learning_path)
        existing = self.chat_repository.list_learning_lessons(module_id)
        lesson = self.chat_repository.create_learning_lesson(
            {
                "module_id": module_id,
                "order_index": len(existing),
                "title": payload.title.strip(),
                "description": payload.description.strip(),
                "objectives": [item.strip() for item in payload.objectives if item.strip()],
                "teaching_notes": payload.teaching_notes.strip(),
            }
        )
        return self._build_learning_lesson_read(lesson)

    def update_learning_lesson(
        self,
        user: UserAccount,
        lesson_id: str,
        payload: LearningLessonUpdateRequest,
    ) -> LearningLessonRead | None:
        lesson = self.chat_repository.get_learning_lesson(lesson_id)
        if lesson is None:
            return None
        module = self.chat_repository.get_learning_module(lesson.module_id)
        if module is None:
            return None
        learning_path = self.chat_repository.get_learning_path(module.learning_path_id)
        if learning_path is None:
            return None
        self._ensure_learning_path_edit_allowed(user, learning_path)
        fields = payload.model_dump(exclude_unset=True)
        if "title" in fields and isinstance(fields["title"], str):
            fields["title"] = fields["title"].strip()
        if "description" in fields and isinstance(fields["description"], str):
            fields["description"] = fields["description"].strip()
        if "teaching_notes" in fields and isinstance(fields["teaching_notes"], str):
            fields["teaching_notes"] = fields["teaching_notes"].strip()
        if "objectives" in fields and fields["objectives"] is not None:
            fields["objectives"] = [item.strip() for item in list(fields["objectives"]) if str(item).strip()]
        updated = self.chat_repository.update_learning_lesson(lesson_id, fields)
        if updated is None:
            return None
        return self._build_learning_lesson_read(updated)

    def delete_learning_lesson(self, user: UserAccount, lesson_id: str) -> LearningLessonRead | None:
        lesson = self.chat_repository.get_learning_lesson(lesson_id)
        if lesson is None:
            return None
        module = self.chat_repository.get_learning_module(lesson.module_id)
        if module is None:
            return None
        learning_path = self.chat_repository.get_learning_path(module.learning_path_id)
        if learning_path is None:
            return None
        self._ensure_learning_path_edit_allowed(user, learning_path)
        deleted = self.chat_repository.delete_learning_lesson(lesson_id)
        if deleted is None:
            return None
        return self._build_learning_lesson_read(deleted)

    def reorder_learning_lessons(
        self,
        user: UserAccount,
        module_id: str,
        payload: LearningLessonReorderRequest,
    ) -> list[LearningLessonRead] | None:
        module = self.chat_repository.get_learning_module(module_id)
        if module is None:
            return None
        learning_path = self.chat_repository.get_learning_path(module.learning_path_id)
        if learning_path is None:
            return None
        self._ensure_learning_path_edit_allowed(user, learning_path)
        lesson_orders = [(item.id, item.order_index) for item in payload.lessons]
        lessons = self.chat_repository.reorder_learning_lessons(module_id, lesson_orders)
        return [self._build_learning_lesson_read(lesson) for lesson in lessons]

    def send_message(
        self,
        user: UserAccount | str,
        chat_id: str | None = None,
        user_content: str | None = None,
        attachments: list[tuple[str, bytes]] | None = None,
        assistant_mode: str | None = None,
    ):
        if isinstance(user, UserAccount):
            return self._send_message_for_user(
                user,
                chat_id or "",
                user_content or "",
                attachments=attachments,
                assistant_mode=assistant_mode,
        )
        return self._send_message_legacy(
            user,
            chat_id or "",
            attachments=attachments,
            assistant_mode=assistant_mode,
        )

    def send_gpt_message(
        self,
        user: UserAccount,
        gpt_id: str,
        user_content: str,
        *,
        attachments: list[tuple[str, bytes]] | None = None,
    ):
        self._ensure_student_cannot_use_gpts(user)
        gpt = self.chat_repository.get_gpt(user.id, gpt_id)
        if gpt is None:
            return None

        gpt_config = self._extract_gpt_runtime_config(map_gpt(gpt).config)
        chat = self.chat_repository.ensure_gpt_chat(gpt.id)
        processed_attachments = self._process_attachments(attachments or [])
        user_message = self.chat_repository.create_message(
            user.id,
            chat.id,
            "user",
            user_content,
            gpt_id=gpt.id,
            has_attachments=bool(processed_attachments),
        )
        if processed_attachments:
            self.chat_repository.add_message_attachments(user_message.id, processed_attachments)
        history = self.history_service.fetch(
            chat.id,
            user_id=user.id,
            gpt_id=gpt.id,
            exclude_message_id=user_message.id,
            limit=gpt_config["settings"]["chat_history_messages_count"],
        )
        retrieved_chunks = self.retrieval_service.retrieve(
            user_content,
            user_id=user.id,
            chat_id=chat.id,
            is_admin=user.role == "admin",
            gpt_overrides={
                "files_enabled": gpt_config["files_enabled"],
                "tags_enabled": gpt_config["tags_enabled"],
                "file_settings": gpt_config["file_settings"],
                "tag_settings": gpt_config["tag_settings"],
            },
            min_results=gpt_config["settings"]["min_similarities"],
            max_results=gpt_config["settings"]["max_similarities"],
            score_threshold=gpt_config["settings"]["similarity_score_threshold"],
        )
        response = self._generate_response(
            assistant_mode=self._resolve_assistant_mode(gpt.assistant_mode),
            user_content=user_content,
            history=history,
            retrieved_chunks=retrieved_chunks,
            personalization=gpt_config["personalization"],
            gpt_instructions=gpt.instructions or "",
            processed_attachments=processed_attachments,
        )
        assistant_message = self.chat_repository.create_message(
            user.id,
            chat.id,
            "assistant",
            response,
            gpt_id=gpt.id,
        )
        self.chat_repository.create_retrieval_logs(
            assistant_message_id=assistant_message.id,
            user_message_id=user_message.id,
            chat_id=chat.id,
            user_id=user.id,
            used_chunks=retrieved_chunks,
        )
        return {
            "chat_id": chat.id,
            "gpt_id": gpt.id,
            "user_message": map_message(user_message).model_copy(
                update={"attachments": [map_attachment(item) for item in processed_attachments]}
            ),
            "assistant_message": map_message(assistant_message),
            "assistant_mode": self._resolve_assistant_mode(gpt.assistant_mode),
            "sources": [map_source_from_chunk(chunk) for chunk in retrieved_chunks],
            "attachments_used": [map_attachment(item) for item in processed_attachments],
        }

    def _send_message_for_user(
        self,
        user: UserAccount,
        chat_id: str,
        user_content: str,
        *,
        attachments: list[tuple[str, bytes]] | None = None,
        assistant_mode: str | None = None,
    ):
        self._ensure_student_cannot_use_standard_chat(user)
        chat = self.chat_repository.get_chat(user.id, chat_id)
        if chat is None:
            return None

        self._load_runtime_settings(user)
        resolved_mode = self._resolve_assistant_mode(assistant_mode)
        personalization = self.get_personalization(user)
        processed_attachments = self._process_attachments(attachments or [])
        user_message = self.chat_repository.create_message(
            user.id,
            chat_id,
            "user",
            user_content,
            has_attachments=bool(processed_attachments),
        )
        if processed_attachments:
            self.chat_repository.add_message_attachments(user_message.id, processed_attachments)
        history = self.history_service.fetch(chat_id, user_id=user.id, exclude_message_id=user_message.id)
        retrieved_chunks = self.retrieval_service.retrieve(
            user_content,
            user_id=user.id,
            chat_id=chat_id,
            is_admin=user.role == "admin",
        )
        response = self._generate_response(
            assistant_mode=resolved_mode,
            user_content=user_content,
            history=history,
            retrieved_chunks=retrieved_chunks,
            personalization=personalization.model_dump(),
            gpt_instructions="",
            processed_attachments=processed_attachments,
        )
        assistant_message = self.chat_repository.create_message(user.id, chat_id, "assistant", response)
        self.chat_repository.create_retrieval_logs(
            assistant_message_id=assistant_message.id,
            user_message_id=user_message.id,
            chat_id=chat_id,
            user_id=user.id,
            used_chunks=retrieved_chunks,
        )

        return {
            "chat_id": chat_id,
            "gpt_id": None,
            "user_message": map_message(user_message).model_copy(
                update={"attachments": [map_attachment(item) for item in processed_attachments]}
            ),
            "assistant_message": map_message(assistant_message),
            "assistant_mode": resolved_mode,
            "sources": [map_source_from_chunk(chunk) for chunk in retrieved_chunks],
            "attachments_used": [map_attachment(item) for item in processed_attachments],
        }

    def _send_message_legacy(
        self,
        chat_id: str,
        user_content: str,
        *,
        attachments: list[tuple[str, bytes]] | None = None,
        assistant_mode: str | None = None,
    ):
        chat = self.chat_repository.get_chat(chat_id)
        if chat is None:
            return None

        resolved_mode = self._resolve_assistant_mode(assistant_mode)
        processed_attachments = self._process_attachments(attachments or [])
        user_message = self.chat_repository.create_message(
            chat_id,
            "user",
            user_content,
            has_attachments=bool(processed_attachments),
        )
        if processed_attachments:
            self.chat_repository.add_message_attachments(user_message.id, processed_attachments)
        history = self.history_service.fetch(chat_id, exclude_message_id=user_message.id)
        retrieved_chunks = self.retrieval_service.retrieve(user_content)
        response = self._generate_response(
            assistant_mode=resolved_mode,
            user_content=user_content,
            history=history,
            retrieved_chunks=retrieved_chunks,
            personalization=dict(PERSONALIZATION_DEFAULTS),
            gpt_instructions="",
            processed_attachments=processed_attachments,
        )
        assistant_message = self.chat_repository.create_message(chat_id, "assistant", response)
        self.chat_repository.create_retrieval_logs(
            assistant_message_id=assistant_message.id,
            user_message_id=user_message.id,
            chat_id=chat_id,
            used_chunks=retrieved_chunks,
        )

        return {
            "chat_id": chat_id,
            "gpt_id": None,
            "user_message": map_message(user_message).model_copy(
                update={"attachments": [map_attachment(item) for item in processed_attachments]}
            ),
            "assistant_message": map_message(assistant_message),
            "assistant_mode": resolved_mode,
            "sources": [map_source_from_chunk(chunk) for chunk in retrieved_chunks],
            "attachments_used": [map_attachment(item) for item in processed_attachments],
        }

    def _process_attachments(self, attachments: list[tuple[str, bytes]]) -> list[dict[str, object]]:
        if not attachments:
            return []
        if len(attachments) > self.settings.attachment_max_files:
            raise ValueError(f"Maximum {self.settings.attachment_max_files} attachments are allowed per message")

        validated: list[tuple[str, bytes]] = []
        for file_name, content in attachments:
            suffix = Path(file_name).suffix.lower()
            if suffix not in self.settings.attachment_allowed_extension_set:
                raise ValueError(f"Unsupported attachment type: {suffix or file_name}")
            validated.append((file_name, content))

        processed = self.attachment_client.process_files(validated)
        return [attachment for attachment in processed if str(attachment.get("content") or "").strip()]

    def _generate_response(
        self,
        *,
        assistant_mode: str,
        user_content: str,
        history: list[tuple[str, str]],
        retrieved_chunks: list[dict[str, str | float | list[str] | None]],
        personalization: dict[str, str],
        gpt_instructions: str,
        processed_attachments: list[dict[str, object]],
    ) -> str:
        common_kwargs = {
            "user_message": user_content,
            "history": history,
            "retrieved_chunks": retrieved_chunks,
            "personalization": personalization,
            "gpt_instructions": gpt_instructions,
            "attachments": processed_attachments,
            "attachment_char_limit": self.settings.attachment_max_total_chars,
        }
        if assistant_mode == "refine":
            draft = self.llm_client.invoke(self.prompt_builder.build_refine_draft_messages(**common_kwargs))
            return self.llm_client.invoke(
                self.prompt_builder.build_refine_final_messages(draft_answer=draft, **common_kwargs)
            )
        if assistant_mode == "thinking":
            try:
                return self._run_thinking_pipeline(**common_kwargs)
            except Exception:
                logger.exception("Thinking mode failed; falling back to simple mode")
                return self.llm_client.invoke(self.prompt_builder.build_simple_messages(**common_kwargs))
        return self.llm_client.invoke(self.prompt_builder.build_simple_messages(**common_kwargs))

    def _run_thinking_pipeline(
        self,
        *,
        user_message: str,
        history: list[tuple[str, str]],
        retrieved_chunks: list[dict[str, str | float | list[str] | None]],
        personalization: dict[str, str],
        gpt_instructions: str,
        attachments: list[dict[str, object]],
        attachment_char_limit: int,
    ) -> str:
        planning_result = self._run_thinking_planning(
            user_message=user_message,
            history=history,
            retrieved_chunks=retrieved_chunks,
            personalization=personalization,
            gpt_instructions=gpt_instructions,
            attachments=attachments,
            attachment_char_limit=attachment_char_limit,
        )
        draft_result = self._run_thinking_drafting(
            user_message=user_message,
            history=history,
            retrieved_chunks=retrieved_chunks,
            personalization=personalization,
            gpt_instructions=gpt_instructions,
            planning_result=planning_result,
            attachments=attachments,
            attachment_char_limit=attachment_char_limit,
        )
        return self._run_thinking_refining(
            user_message=user_message,
            history=history,
            retrieved_chunks=retrieved_chunks,
            personalization=personalization,
            gpt_instructions=gpt_instructions,
            planning_result=planning_result,
            draft_result=draft_result,
            attachments=attachments,
            attachment_char_limit=attachment_char_limit,
        )

    def _run_thinking_planning(
        self,
        *,
        user_message: str,
        history: list[tuple[str, str]],
        retrieved_chunks: list[dict[str, str | float | list[str] | None]],
        personalization: dict[str, str],
        gpt_instructions: str,
        attachments: list[dict[str, object]],
        attachment_char_limit: int,
    ) -> str:
        planning_result = self.llm_client.invoke(
            self.prompt_builder.build_thinking_plan_messages(
                user_message=user_message,
                history=history,
                retrieved_chunks=retrieved_chunks,
                personalization=personalization,
                gpt_instructions=gpt_instructions,
                attachments=attachments,
                attachment_char_limit=attachment_char_limit,
            )
        )
        logger.debug("Thinking mode planning result: %s", planning_result)
        return planning_result

    def _run_thinking_drafting(
        self,
        *,
        user_message: str,
        history: list[tuple[str, str]],
        retrieved_chunks: list[dict[str, str | float | list[str] | None]],
        personalization: dict[str, str],
        planning_result: str,
        gpt_instructions: str,
        attachments: list[dict[str, object]],
        attachment_char_limit: int,
    ) -> str:
        draft_result = self.llm_client.invoke(
            self.prompt_builder.build_thinking_draft_messages(
                user_message=user_message,
                history=history,
                retrieved_chunks=retrieved_chunks,
                planning_result=planning_result,
                personalization=personalization,
                gpt_instructions=gpt_instructions,
                attachments=attachments,
                attachment_char_limit=attachment_char_limit,
            )
        )
        logger.debug("Thinking mode draft result: %s", draft_result)
        return draft_result

    def _run_thinking_refining(
        self,
        *,
        user_message: str,
        history: list[tuple[str, str]],
        retrieved_chunks: list[dict[str, str | float | list[str] | None]],
        personalization: dict[str, str],
        planning_result: str,
        draft_result: str,
        gpt_instructions: str,
        attachments: list[dict[str, object]],
        attachment_char_limit: int,
    ) -> str:
        return self.llm_client.invoke(
            self.prompt_builder.build_thinking_final_messages(
                user_message=user_message,
                history=history,
                retrieved_chunks=retrieved_chunks,
                planning_result=planning_result,
                draft_answer=draft_result,
                personalization=personalization,
                gpt_instructions=gpt_instructions,
                attachments=attachments,
                attachment_char_limit=attachment_char_limit,
            )
        )

    def _normalize_tags(self, tags: list[str]) -> list[str]:
        return sorted({tag.strip().lower() for tag in tags if tag.strip()})

    def _ensure_example_learning_path(self) -> None:
        try:
            existing_paths = self.chat_repository.list_learning_paths(user_id=0, role="admin")
            existing_titles = {path.title for path in existing_paths}
            if EXAMPLE_LEARNING_PATH_TITLE not in existing_titles:
                path = self.chat_repository.create_learning_path(
                    {
                        "scope": "global",
                        "owner_user_id": None,
                        "title": EXAMPLE_LEARNING_PATH_TITLE,
                        "description": "Starter path demonstrating a complete learning setup.",
                        "subject": "Docker",
                        "difficulty_level": "beginner",
                        "estimated_duration_minutes": 120,
                        "status": "published",
                    }
                )
                intro_module = self.chat_repository.create_learning_module(
                    {
                        "learning_path_id": path.id,
                        "order_index": 0,
                        "title": "Getting Started",
                        "description": "Core concepts and first practical steps.",
                        "learning_objectives": ["Understand images/containers", "Run and inspect containers"],
                    }
                )
                self.chat_repository.create_learning_lesson(
                    {
                        "module_id": intro_module.id,
                        "order_index": 0,
                        "title": "What Docker Is",
                        "description": "Mental model for images, containers, and registries.",
                        "objectives": ["Differentiate image vs container", "Know when to use Docker"],
                        "teaching_notes": "",
                    }
                )
                self.chat_repository.create_learning_lesson(
                    {
                        "module_id": intro_module.id,
                        "order_index": 1,
                        "title": "First Container Run",
                        "description": "Run, stop, and inspect a hello-world style container.",
                        "objectives": ["Use run/ps/stop/logs"],
                        "teaching_notes": "",
                    }
                )
                compose_module = self.chat_repository.create_learning_module(
                    {
                        "learning_path_id": path.id,
                        "order_index": 1,
                        "title": "Compose Basics",
                        "description": "Model multi-service local development.",
                        "learning_objectives": ["Read compose files", "Start and manage service stacks"],
                    }
                )
                self.chat_repository.create_learning_lesson(
                    {
                        "module_id": compose_module.id,
                        "order_index": 0,
                        "title": "Compose File Structure",
                        "description": "Services, volumes, ports, and environment basics.",
                        "objectives": ["Understand core compose keys"],
                        "teaching_notes": "",
                    }
                )

            if EXAMPLE_LEARNING_PATH_TITLE_SECOND not in existing_titles:
                path = self.chat_repository.create_learning_path(
                    {
                        "scope": "global",
                        "owner_user_id": None,
                        "title": EXAMPLE_LEARNING_PATH_TITLE_SECOND,
                        "description": "Practical beginner path to write and reason about Python code quickly.",
                        "subject": "Python",
                        "difficulty_level": "beginner",
                        "estimated_duration_minutes": 150,
                        "status": "published",
                    }
                )
                basics_module = self.chat_repository.create_learning_module(
                    {
                        "learning_path_id": path.id,
                        "order_index": 0,
                        "title": "Python Basics",
                        "description": "Syntax, variables, conditionals, and loops.",
                        "learning_objectives": ["Read basic Python", "Write simple scripts"],
                    }
                )
                self.chat_repository.create_learning_lesson(
                    {
                        "module_id": basics_module.id,
                        "order_index": 0,
                        "title": "Variables and Data Types",
                        "description": "Numbers, strings, booleans, and lists in small examples.",
                        "objectives": ["Choose the right data type", "Use simple transformations"],
                        "teaching_notes": "",
                    }
                )
                self.chat_repository.create_learning_lesson(
                    {
                        "module_id": basics_module.id,
                        "order_index": 1,
                        "title": "Control Flow",
                        "description": "If statements and loops for basic program logic.",
                        "objectives": ["Write conditional logic", "Iterate with for/while"],
                        "teaching_notes": "",
                    }
                )
                functions_module = self.chat_repository.create_learning_module(
                    {
                        "learning_path_id": path.id,
                        "order_index": 1,
                        "title": "Functions and Small Projects",
                        "description": "Reusable functions and basic problem decomposition.",
                        "learning_objectives": ["Define and call functions", "Structure a tiny script project"],
                    }
                )
                self.chat_repository.create_learning_lesson(
                    {
                        "module_id": functions_module.id,
                        "order_index": 0,
                        "title": "Functions and Parameters",
                        "description": "Build reusable code with arguments and return values.",
                        "objectives": ["Write functions", "Use return values effectively"],
                        "teaching_notes": "",
                    }
                )
        except Exception:
            logger.exception("Failed to ensure example learning path")

    def _normalize_string_list(self, values: list[str]) -> list[str]:
        return list(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))

    def _serialize_learning_preference(self, preference: UserLearningPreference) -> dict[str, object]:
        return {
            "preferred_pace": preference.preferred_pace,
            "explanation_depth": preference.explanation_depth,
            "examples_vs_theory": preference.examples_vs_theory,
            "structure_preference": preference.structure_preference,
            "checkpoint_frequency": preference.checkpoint_frequency,
            "encouragement_level": preference.encouragement_level,
            "guidance_level": preference.guidance_level,
            "recap_frequency": preference.recap_frequency,
            "preferred_learning_format": preference.preferred_learning_format,
            "custom_preference_note": preference.custom_preference_note or "",
        }

    def _serialize_learning_profile(self, profile: UserLearningProfile) -> dict[str, object]:
        return {
            "education_background": profile.education_background or "",
            "current_skill_areas": list(profile.current_skill_areas or []),
            "interests": list(profile.interests or []),
            "professional_context": profile.professional_context or "",
            "current_reason_for_learning": profile.current_reason_for_learning or "",
            "preferred_form_of_address": profile.preferred_form_of_address or "",
            "learning_context_notes": profile.learning_context_notes or "",
        }

    def _build_learning_preferences_read(self, preference: UserLearningPreference | None) -> LearningPreferencesRead:
        if preference is None:
            return LearningPreferencesRead(**LEARNING_PREFERENCE_DEFAULTS, updated_at=None)
        return LearningPreferencesRead(
            preferred_pace=preference.preferred_pace,
            explanation_depth=preference.explanation_depth,
            examples_vs_theory=preference.examples_vs_theory,
            structure_preference=preference.structure_preference,
            checkpoint_frequency=preference.checkpoint_frequency,
            encouragement_level=preference.encouragement_level,
            guidance_level=preference.guidance_level,
            recap_frequency=preference.recap_frequency,
            preferred_learning_format=preference.preferred_learning_format,
            custom_preference_note=preference.custom_preference_note or "",
            updated_at=preference.updated_at,
        )

    def _build_learning_context_read(self, profile: UserLearningProfile | None) -> LearningProfileContextRead:
        if profile is None:
            return LearningProfileContextRead(**LEARNING_CONTEXT_DEFAULTS, updated_at=None)
        return LearningProfileContextRead(
            education_background=profile.education_background or "",
            current_skill_areas=list(profile.current_skill_areas or []),
            interests=list(profile.interests or []),
            professional_context=profile.professional_context or "",
            current_reason_for_learning=profile.current_reason_for_learning or "",
            preferred_form_of_address=profile.preferred_form_of_address or "",
            learning_context_notes=profile.learning_context_notes or "",
            updated_at=profile.updated_at,
        )

    def _build_learning_goal_read(self, goal: UserLearningGoal) -> LearningGoalRead:
        return LearningGoalRead(
            id=goal.id,
            target_topic=goal.target_topic,
            reason_for_learning=goal.reason_for_learning or "",
            target_level=goal.target_level or "",
            deadline=goal.deadline,
            priority=goal.priority,
            notes=goal.notes or "",
            is_active=goal.is_active,
            created_at=goal.created_at,
            updated_at=goal.updated_at,
        )

    def _can_view_learning_path(self, user: UserAccount, path: LearningPath) -> bool:
        if user.role == "admin":
            return True
        if path.scope == "global":
            return True
        return path.owner_user_id == user.id

    def _can_edit_learning_path(self, user: UserAccount, path: LearningPath) -> bool:
        if user.role == "admin":
            return True
        if user.role == "student":
            return False
        if path.scope == "global":
            return False
        return path.owner_user_id == user.id

    def _can_delete_learning_path(self, user: UserAccount, path: LearningPath) -> bool:
        return self._can_edit_learning_path(user, path)

    def _ensure_learning_path_create_allowed(self, user: UserAccount, scope: str) -> None:
        if user.role == "student":
            raise PermissionError("Students cannot create learning paths")
        if scope == "global" and user.role != "admin":
            raise PermissionError("Only admins can create global learning paths")

    def _ensure_learning_path_edit_allowed(self, user: UserAccount, path: LearningPath, *, deleting: bool = False) -> None:
        if deleting and not self._can_delete_learning_path(user, path):
            raise PermissionError("You do not have permission to delete this learning path")
        if not deleting and not self._can_edit_learning_path(user, path):
            raise PermissionError("You do not have permission to edit this learning path")

    def _ensure_student_cannot_use_standard_chat(self, user: UserAccount) -> None:
        if user.role == "student":
            raise PermissionError("Students can only use learning mode")

    def _ensure_student_cannot_use_gpts(self, user: UserAccount) -> None:
        if user.role == "student":
            raise PermissionError("Students cannot create or use GPTs")

    def _build_learning_lesson_read(self, lesson: LearningLesson) -> LearningLessonRead:
        return LearningLessonRead(
            id=lesson.id,
            module_id=lesson.module_id,
            order_index=lesson.order_index,
            title=lesson.title,
            description=lesson.description or "",
            objectives=list(lesson.objectives or []),
            teaching_notes=lesson.teaching_notes or "",
            created_at=lesson.created_at,
            updated_at=lesson.updated_at,
        )

    def _build_learning_module_read(self, module: LearningModule, *, lessons: list[LearningLesson]) -> LearningModuleRead:
        return LearningModuleRead(
            id=module.id,
            learning_path_id=module.learning_path_id,
            order_index=module.order_index,
            title=module.title,
            description=module.description or "",
            learning_objectives=list(module.learning_objectives or []),
            lessons=[self._build_learning_lesson_read(lesson) for lesson in lessons],
            created_at=module.created_at,
            updated_at=module.updated_at,
        )

    def _build_learning_path_read(self, user: UserAccount, path: LearningPath) -> LearningPathRead:
        modules = self.chat_repository.list_learning_modules(path.id)
        lessons_by_module = {
            module.id: self.chat_repository.list_learning_lessons(module.id)
            for module in modules
        }
        allowed_files = self.chat_repository.list_learning_path_allowed_files(path.id)
        allowed_tags = self.chat_repository.list_learning_path_allowed_tags(path.id)
        return LearningPathRead(
            id=path.id,
            scope=path.scope,
            owner_user_id=path.owner_user_id,
            title=path.title,
            description=path.description or "",
            subject=path.subject or "",
            difficulty_level=path.difficulty_level or "",
            estimated_duration_minutes=path.estimated_duration_minutes,
            status=path.status,
            allowed_file_ids=[item.file_id for item in allowed_files],
            allowed_tags=[item.tag for item in allowed_tags],
            modules=[
                self._build_learning_module_read(module, lessons=lessons_by_module.get(module.id, []))
                for module in modules
            ],
            can_edit=self._can_edit_learning_path(user, path),
            can_delete=self._can_delete_learning_path(user, path),
            created_at=path.created_at,
            updated_at=path.updated_at,
        )

    def _resolve_assistant_mode(self, assistant_mode: str | None) -> str:
        mode = (assistant_mode or self.settings.default_assistant_mode).strip().lower()
        if not mode:
            mode = "simple"
        if mode not in self.settings.available_assistant_modes:
            raise ValueError(f"Unsupported assistant mode: {mode}")
        return mode

    def _load_runtime_settings(self, user: UserAccount) -> None:
        stored_values = self._load_stored_setting_values(user)

        self.history_service.history_limit = max(
            1,
            int(stored_values.get("chat_history_messages_count", self.settings.history_limit)),
        )
        self.retrieval_service.min_results = max(
            1,
            int(stored_values.get("min_similarities", self.settings.retrieval_min_results)),
        )
        self.retrieval_service.max_results = max(
            self.retrieval_service.min_results,
            int(stored_values.get("max_similarities", self.settings.retrieval_max_results)),
        )
        self.retrieval_service.score_threshold = min(
            max(float(stored_values.get("similarity_score_threshold", self.settings.retrieval_score_threshold)), 0.0),
            1.0,
        )

    def _load_stored_setting_values(self, user: UserAccount) -> dict[str, object]:
        stored_values: dict[str, object] = {}
        supported_keys = RUNTIME_SETTING_KEYS | PERSONALIZATION_SETTING_KEYS
        for record in self.chat_repository.list_settings(user.id):
            if record.key not in supported_keys:
                continue
            try:
                stored_values[record.key] = json.loads(record.value)
            except json.JSONDecodeError:
                continue
        return stored_values

    def _default_gpt_settings(self) -> dict[str, object]:
        return {
            "chat_history_messages_count": self.settings.history_limit,
            "max_similarities": self.settings.retrieval_max_results,
            "min_similarities": self.settings.retrieval_min_results,
            "similarity_score_threshold": self.settings.retrieval_score_threshold,
            "files_enabled": True,
            "tags_enabled": True,
        }

    def _validate_gpt_request(self, payload: GptCreateRequest) -> None:
        resolved_mode = self._resolve_assistant_mode(payload.assistant_mode)
        if payload.config.settings.min_similarities > payload.config.settings.max_similarities:
            raise ValueError("min similarities cannot be greater than max similarities")
        payload.assistant_mode = resolved_mode

    def _build_gpt_payload(self, payload: GptCreateRequest) -> dict[str, object]:
        self._validate_gpt_request(payload)
        return {
            "name": payload.name.strip(),
            "description": payload.description.strip(),
            "instructions": payload.instructions.strip(),
            "assistant_mode": payload.assistant_mode,
            "personalization": payload.config.personalization.model_dump(),
            "settings": {
                **payload.config.settings.model_dump(),
                "files_enabled": payload.config.files_enabled,
                "tags_enabled": payload.config.tags_enabled,
            },
            "file_settings": {str(item.file_id): item.is_enabled for item in payload.config.file_settings},
            "tag_settings": {item.tag: item.is_enabled for item in payload.config.tag_settings},
        }

    def _build_gpt_update_fields(self, payload: GptUpdateRequest) -> dict[str, object]:
        fields: dict[str, object] = {}
        if payload.name is not None:
            fields["name"] = payload.name.strip()
        if payload.description is not None:
            fields["description"] = payload.description.strip()
        if payload.instructions is not None:
            fields["instructions"] = payload.instructions.strip()
        if payload.assistant_mode is not None:
            fields["assistant_mode"] = self._resolve_assistant_mode(payload.assistant_mode)
        if payload.config is not None:
            if payload.config.settings.min_similarities > payload.config.settings.max_similarities:
                raise ValueError("min similarities cannot be greater than max similarities")
            fields["personalization"] = payload.config.personalization.model_dump()
            fields["settings"] = {
                **payload.config.settings.model_dump(),
                "files_enabled": payload.config.files_enabled,
                "tags_enabled": payload.config.tags_enabled,
            }
            fields["file_settings"] = {str(item.file_id): item.is_enabled for item in payload.config.file_settings}
            fields["tag_settings"] = {item.tag: item.is_enabled for item in payload.config.tag_settings}
        return fields

    def _extract_gpt_runtime_config(self, config: GptConfigRead | GptConfigUpdateRequest) -> dict[str, object]:
        if isinstance(config, GptConfigUpdateRequest):
            personalization = config.personalization.model_dump()
            settings = config.settings.model_dump()
            file_settings = {item.file_id: item.is_enabled for item in config.file_settings}
            tag_settings = {item.tag: item.is_enabled for item in config.tag_settings}
            files_enabled = config.files_enabled
            tags_enabled = config.tags_enabled
        else:
            personalization = config.personalization.model_dump()
            settings = config.settings.model_dump()
            file_settings = {item.file_id: item.is_enabled for item in config.file_settings}
            tag_settings = {item.tag: item.is_enabled for item in config.tag_settings}
            files_enabled = config.files_enabled
            tags_enabled = config.tags_enabled
        return {
            "personalization": personalization,
            "settings": {
                **self._default_gpt_settings(),
                **settings,
            },
            "file_settings": file_settings,
            "tag_settings": tag_settings,
            "files_enabled": files_enabled,
            "tags_enabled": tags_enabled,
        }


def build_retriever_app_service(
    *,
    database_url: str,
    embedding_model: str,
    embedding_base_url: str,
    embedding_api_key: str,
    embedding_max_input_tokens: int,
    qdrant_url: str,
    qdrant_collection: str,
    retrieval_score_threshold: float,
    retrieval_min_results: int,
    retrieval_max_results: int,
    llm_model: str,
    llm_base_url: str,
    llm_api_key: str,
    prompts_dir: Path,
    history_limit: int,
    settings: Settings,
) -> RetrieverAppService:
    from services.retriever.postgres_client import RetrieverPostgresClient

    postgres_client = RetrieverPostgresClient(database_url)
    postgres_client.initialize()
    embedder_postgres_client = EmbedderPostgresClient(database_url)
    embedder_postgres_client.initialize()
    chat_repository = ChatRepository(postgres_client)
    auth_manager = AuthManager(repository=chat_repository, settings=settings)
    data_dir = Path(settings.data_dir)
    library_processor = FileProcessor(
        data_dir=data_dir,
        chunker=Chunker(settings.chunk_size, settings.chunk_overlap),
        embedding_client=EmbeddingClient(
            model=embedding_model,
            base_url=embedding_base_url,
            api_key=embedding_api_key,
            max_input_tokens=embedding_max_input_tokens,
        ),
        postgres_client=embedder_postgres_client,
        qdrant_client=EmbedderQdrantClient(settings.qdrant_url, settings.qdrant_collection),
        tags_map={},
        settings=settings,
    )
    deps = RetrieverDependencies(
        chat_repository=chat_repository,
        history_service=ChatHistoryService(postgres_client, history_limit),
        retrieval_service=RetrievalService(
            embedding_client=EmbeddingClient(
                model=embedding_model,
                base_url=embedding_base_url,
                api_key=embedding_api_key,
                max_input_tokens=embedding_max_input_tokens,
            ),
            qdrant_store=RetrieverQdrantClient(qdrant_url, qdrant_collection),
            score_threshold=retrieval_score_threshold,
            min_results=retrieval_min_results,
            max_results=retrieval_max_results,
            candidate_filter=postgres_client.filter_retrieval_candidates,
        ),
        prompt_builder=PromptBuilder(prompts_dir),
        llm_client=LlmClient(
            model=llm_model,
            base_url=llm_base_url,
            api_key=llm_api_key,
            timeout=settings.llm_timeout_seconds,
        ),
        library_manager=LibraryManager(data_dir=data_dir, processor=library_processor, settings=settings),
        attachment_client=AttachmentProcessingClient(settings.embedder_service_url),
        auth_manager=auth_manager,
        settings=settings,
    )
    return RetrieverAppService(deps)


def map_source_from_chunk(chunk: dict[str, str | float | list[str] | None]):
    return map_source(
        RetrievalLogProxy(
            chunk_id=str(chunk.get("chunk_id", "")),
            source_file_name=str(chunk.get("file_name", "")),
            source_file_path=str(chunk.get("file_path", "")),
            chunk_title=_to_optional_str(chunk.get("title")),
            chapter=_to_optional_str(chunk.get("chapter")),
            section=_to_optional_str(chunk.get("section")),
            page_number=chunk.get("page_number"),
            tags=list(chunk.get("tags", []) or []),
            retrieval_score=float(chunk.get("score", 0.0) or 0.0),
        )
    )


class RetrievalLogProxy:
    def __init__(
        self,
        *,
        chunk_id: str,
        source_file_name: str,
        source_file_path: str,
        chunk_title: str | None,
        chapter: str | None,
        section: str | None,
        page_number: int | None,
        tags: list[str],
        retrieval_score: float,
    ) -> None:
        self.chunk_id = chunk_id
        self.source_file_name = source_file_name
        self.source_file_path = source_file_path
        self.chunk_title = chunk_title
        self.chapter = chapter
        self.section = section
        self.page_number = page_number
        self.tags = tags
        self.retrieval_score = retrieval_score


def _to_optional_str(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None
