from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path

import httpx
from sqlalchemy import text

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
    SystemStatusResponse,
    SystemServiceStatusRead,
)
from services.retriever.schemas.learning import (
    LearningLessonCreateRequest,
    LearningLessonRead,
    LearningLessonReorderRequest,
    LearningLessonUpdateRequest,
    LearningModuleCreateRequest,
    LearningModuleRead,
    LearningModuleReorderRequest,
    LearningModuleUpdateRequest,
    CourseImportFileResultRead,
    CourseImportResponse,
    CourseListItemRead,
    CourseListResponse,
    CourseTemplateResponse,
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
from services.retriever.schemas.diagnostics import (
    DiagnosticAnswerUpsertRequest,
    DiagnosticAttemptDetailsRead,
    DiagnosticAttemptStartResponse,
    DiagnosticAttemptSummaryRead,
    DiagnosticCatalogRead,
    DiagnosticDefinitionRead,
    DiagnosticResultRead,
    ExplanationFeedbackCreateRequest,
    ExplanationFeedbackRead,
    LearningStateCheckCreateRequest,
    LearningStateCheckRead,
)
from services.retriever.schemas.ksa import KSAAbilitiesRead, KSAKnowledgeRead, KSAProfileRead, KSASkillsRead
from services.retriever.schemas.ksa_assessment import (
    KSAAssessmentAttemptRead,
    KSAAssessmentDefinitionRead,
    KSAAssessmentStartResponse,
    KSAAssessmentAnswersUpsertRequest,
)
from services.retriever.schemas.ksa_drills import (
    KSADrillAnswersUpsertRequest,
    KSADrillAttemptRead,
    KSADrillAttemptStartRequest,
    KSADrillAttemptStartResponse,
    KSADrillQuestionRead,
    KSADrillTopicsRead,
)
from services.retriever.services.diagnostic_definitions import load_parsed_sources
from services.retriever.services.diagnostic_scoring import score_attempt
from services.retriever.services.chat_naming import generate_chat_name
from services.retriever.services.library_manager import LibraryManager, UploadFilePayload
from services.retriever.services.course_files import CourseDefinition, CourseFileParser
from services.retriever.services.message_mapper import map_attachment, map_chat, map_filter_file, map_filter_tag, map_gpt, map_message, map_source
from services.retriever.services.ksa_assessment import ASSESSMENT_VERSION, evaluate_assessment, get_assessment_definition
from services.retriever.services.ksa_drills import (
    DRILL_ASSESSMENT_VERSION,
    evaluate_drill_attempt,
    generate_drill_question_set,
    list_drill_topics,
)

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
    "profile_display_name": "",
    "about_me": "",
    "contact_location": "",
    "general_title": "",
    "date_of_birth": "",
    "current_skill_areas": [],
    "skills": [],
    "interests": [],
    "work_experience": [],
    "education_history": [],
    "current_reason_for_learning": "",
    "preferred_form_of_address": "",
    "learning_context_notes": "",
}

SUPPORTED_ROLES = {"admin", "user", "student"}
EXAMPLE_LEARNING_PATH_TITLE = "Example: Docker Fundamentals"
EXAMPLE_LEARNING_PATH_TITLE_SECOND = "Example: Python Learning Sprint"
EXAMPLE_LEARNING_PATH_ID = "course-example-docker-fundamentals"
EXAMPLE_LEARNING_PATH_ID_SECOND = "course-example-python-learning-sprint"
DIAGNOSTIC_DOC_SOURCE_SUBDIR = "diagnostics/source"
DIAGNOSTIC_PAGES_FALLBACK_SUBDIR = "prds"
COURSE_SORT_OPTIONS = {
    "name_asc",
    "name_desc",
    "updated_desc",
    "updated_asc",
    "modules_desc",
    "lessons_desc",
    "scope_global_first",
    "scope_user_first",
}

STUDENT_DEFAULT_KNOWLEDGE = {
    "stem_fundamentals": 2,
    "information_technology": 2,
    "humanities_social_sciences": 3,
    "languages_linguistics": 3,
    "business_commerce": 2,
    "legal_ethics": 1,
    "health_wellness": 2,
}

STUDENT_DEFAULT_SKILLS = {
    "literacy_numeracy": 3,
    "digital_craft": 2,
    "strategic_execution": 2,
    "operational_skills": 2,
    "relational_skills": 3,
    "research_inquiry": 2,
}

STUDENT_DEFAULT_ABILITIES = {
    "quantitative_reasoning": 2,
    "verbal_comprehension": 3,
    "spatial_visualization": 2,
    "executive_function": 2,
    "sensory_perceptual": 3,
    "social_emotional_capacity": 3,
    "divergent_thinking": 3,
}

PLACEHOLDER_BASELINE_KNOWLEDGE = {
    "stem_fundamentals": 2,
    "information_technology": 2,
    "humanities_social_sciences": 2,
    "languages_linguistics": 2,
    "business_commerce": 2,
    "legal_ethics": 2,
    "health_wellness": 2,
}

PLACEHOLDER_BASELINE_SKILLS = {
    "literacy_numeracy": 2,
    "digital_craft": 2,
    "strategic_execution": 2,
    "operational_skills": 2,
    "relational_skills": 2,
    "research_inquiry": 2,
}

PLACEHOLDER_BASELINE_ABILITIES = {
    "quantitative_reasoning": 2,
    "verbal_comprehension": 2,
    "spatial_visualization": 2,
    "executive_function": 2,
    "sensory_perceptual": 2,
    "social_emotional_capacity": 2,
    "divergent_thinking": 2,
}
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
        self.course_file_parser = CourseFileParser()
        self.courses_dir = Path(self.settings.courses_dir)
        self.courses_dir.mkdir(parents=True, exist_ok=True)
        if self.auth_manager is not None:
            self.auth_manager.bootstrap_users()
        self._ensure_example_learning_path()
        self._sync_courses_from_files()
        self._dedupe_learning_paths()
        self._export_courses_to_files()
        self._ensure_diagnostic_definitions()

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

    def get_system_status(self, auth: AuthContext) -> SystemStatusResponse:
        services: list[SystemServiceStatusRead] = []

        services.append(
            SystemServiceStatusRead(
                key="webui",
                label="WebUI",
                description="Frontend application session and API connectivity.",
                status="ok",
                detail=f"Session active for {auth.user.username}.",
            )
        )

        services.append(
            SystemServiceStatusRead(
                key="retriever",
                label="Retriever",
                description="Retrieval, prompt assembly, and answer generation service.",
                status="ok",
                detail="Retriever API is running.",
            )
        )

        services.append(self._check_database_status())
        services.append(self._check_embedder_status())
        services.append(self._check_knowledge_base_status(auth.user))

        return SystemStatusResponse(checked_at=datetime.now(timezone.utc), services=services)

    def _check_database_status(self) -> SystemServiceStatusRead:
        try:
            with self.chat_repository.postgres_client.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return SystemServiceStatusRead(
                key="database",
                label="Database",
                description="PostgreSQL storage for users, chats, settings, and diagnostic data.",
                status="ok",
                detail="Connection successful.",
            )
        except Exception as error:
            return SystemServiceStatusRead(
                key="database",
                label="Database",
                description="PostgreSQL storage for users, chats, settings, and diagnostic data.",
                status="error",
                detail=f"Connection failed: {error}",
            )

    def _check_embedder_status(self) -> SystemServiceStatusRead:
        try:
            response = httpx.get(f"{self.settings.embedder_service_url.rstrip('/')}/health", timeout=4.0)
            response.raise_for_status()
            payload = response.json() if response.content else {}
            status_value = str(payload.get("status", "ok"))
            return SystemServiceStatusRead(
                key="embedder",
                label="Embedder",
                description="File processing and embedding pipeline service.",
                status="ok" if status_value.lower() == "ok" else "warn",
                detail=f"Embedder health returned: {status_value}.",
            )
        except Exception as error:
            return SystemServiceStatusRead(
                key="embedder",
                label="Embedder",
                description="File processing and embedding pipeline service.",
                status="error",
                detail=f"Embedder unreachable: {error}",
            )

    def _check_knowledge_base_status(self, user: UserAccount) -> SystemServiceStatusRead:
        detail_segments: list[str] = []
        status = "ok"
        try:
            library = self.library_manager.list_files(user, include_other_users=False)
            files = list(getattr(library, "files", []) or [])
            summary = getattr(library, "summary", None)
            total_files = int(getattr(summary, "total_files", len(files)) if summary is not None else len(files))
            embedded_files = int(
                getattr(summary, "embedded_files", sum(1 for file in files if getattr(file, "is_embedded", False)))
                if summary is not None
                else sum(1 for file in files if getattr(file, "is_embedded", False))
            )
            enabled_files = sum(1 for file in files if getattr(file, "is_enabled", False))
            detail_segments.append(f"{embedded_files}/{total_files} embedded")
            detail_segments.append(f"{enabled_files}/{total_files} enabled")
        except Exception as error:
            status = "error"
            detail_segments.append(f"Library index failed: {error}")

        try:
            collection_exists = bool(self.retrieval_service.qdrant_store.collection_exists())
            detail_segments.append(f"vector index {'ready' if collection_exists else 'not initialized'}")
            if status != "error" and not collection_exists:
                status = "warn"
        except Exception as error:
            status = "error"
            detail_segments.append(f"vector index check failed: {error}")

        return SystemServiceStatusRead(
            key="knowledge_base",
            label="Knowledge Base",
            description="Library files and vector index used for grounded retrieval.",
            status=status,
            detail="; ".join(detail_segments) if detail_segments else "No details available.",
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
        latest_attempt_getter = getattr(self.chat_repository, "get_latest_user_diagnostic_attempt", None)
        latest_attempt = latest_attempt_getter(user_id=user.id) if callable(latest_attempt_getter) else None
        diagnostics_status = "not_started"
        if latest_attempt is not None:
            diagnostics_status = "completed" if latest_attempt.status == "completed" else "in_progress"
        return LearningProfileBundleRead(
            preferences=self._build_learning_preferences_read(preference),
            context=self._build_learning_context_read(profile),
            goals=[self._build_learning_goal_read(goal) for goal in goals],
            diagnostics_status=diagnostics_status,
        )

    def get_ksa_profile(self, user: UserAccount) -> KSAProfileRead:
        persisted = self.chat_repository.get_user_ksa_profile(user.id)
        if persisted is not None and bool(persisted.has_assessment):
            return self._build_ksa_profile_read(
                user_id=user.id,
                profile_json=dict(persisted.profile_json or {}),
                updated_at=persisted.updated_at,
            )
        if str(user.role).lower() == "student":
            return KSAProfileRead(
                user_id=user.id,
                has_assessment=False,
                profile_source="student_default_baseline",
                knowledge=KSAKnowledgeRead(**STUDENT_DEFAULT_KNOWLEDGE),
                skills=KSASkillsRead(**STUDENT_DEFAULT_SKILLS),
                abilities=KSAAbilitiesRead(**STUDENT_DEFAULT_ABILITIES),
                updated_at=None,
            )
        return KSAProfileRead(
            user_id=user.id,
            has_assessment=False,
            profile_source="placeholder_baseline",
            knowledge=KSAKnowledgeRead(**PLACEHOLDER_BASELINE_KNOWLEDGE),
            skills=KSASkillsRead(**PLACEHOLDER_BASELINE_SKILLS),
            abilities=KSAAbilitiesRead(**PLACEHOLDER_BASELINE_ABILITIES),
            updated_at=None,
        )

    def get_ksa_assessment_definition(self, user: UserAccount) -> KSAAssessmentDefinitionRead:
        _ = user
        return KSAAssessmentDefinitionRead(**get_assessment_definition())

    def start_ksa_assessment(self, user: UserAccount) -> KSAAssessmentStartResponse:
        attempt = self.chat_repository.create_user_ksa_assessment_attempt(
            user_id=user.id,
            assessment_version=ASSESSMENT_VERSION,
        )
        return KSAAssessmentStartResponse(
            attempt_id=attempt.id,
            status="in_progress",
            version=attempt.assessment_version,
            started_at=attempt.started_at,
        )

    def get_ksa_assessment_attempt(self, user: UserAccount, attempt_id: str) -> KSAAssessmentAttemptRead | None:
        record = self.chat_repository.get_user_ksa_assessment_attempt(user_id=user.id, attempt_id=attempt_id)
        if record is None:
            return None
        return self._build_ksa_attempt_read(record)

    def get_latest_ksa_assessment_attempt(self, user: UserAccount) -> KSAAssessmentAttemptRead | None:
        record = self.chat_repository.get_latest_user_ksa_assessment_attempt(user_id=user.id)
        if record is None:
            return None
        return self._build_ksa_attempt_read(record)

    def upsert_ksa_assessment_answers(
        self,
        user: UserAccount,
        attempt_id: str,
        payload: KSAAssessmentAnswersUpsertRequest,
    ) -> KSAAssessmentAttemptRead | None:
        record = self.chat_repository.upsert_user_ksa_assessment_answers(
            user_id=user.id,
            attempt_id=attempt_id,
            answers_json=dict(payload.answers or {}),
        )
        if record is None:
            return None
        return self._build_ksa_attempt_read(record)

    def complete_ksa_assessment(self, user: UserAccount, attempt_id: str) -> KSAProfileRead | None:
        attempt = self.chat_repository.get_user_ksa_assessment_attempt(user_id=user.id, attempt_id=attempt_id)
        if attempt is None:
            return None
        evaluation = evaluate_assessment(user_id=user.id, answers=dict(attempt.answers_json or {}))
        completed_attempt = self.chat_repository.complete_user_ksa_assessment_attempt(
            user_id=user.id,
            attempt_id=attempt.id,
            result_json=evaluation.profile_json,
        )
        if completed_attempt is None:
            return None
        self.chat_repository.upsert_user_ksa_profile(
            user_id=user.id,
            has_assessment=True,
            assessment_version=ASSESSMENT_VERSION,
            profile_json=evaluation.profile_json,
        )
        return self._build_ksa_profile_read(
            user_id=user.id,
            profile_json=evaluation.profile_json,
            updated_at=completed_attempt.updated_at,
        )

    def list_ksa_drill_topics(self, user: UserAccount) -> KSADrillTopicsRead:
        _ = user
        return KSADrillTopicsRead(topics=[item for item in list_drill_topics()])

    def start_ksa_drill_attempt(self, user: UserAccount, payload: KSADrillAttemptStartRequest) -> KSADrillAttemptStartResponse:
        selected = [str(item).strip() for item in list(payload.topic_keys or []) if str(item).strip()]
        question_set = generate_drill_question_set(selected_topic_keys=selected)
        attempt = self.chat_repository.create_user_ksa_drill_attempt(
            user_id=user.id,
            assessment_version=DRILL_ASSESSMENT_VERSION,
            selected_topic_keys=selected,
            question_set_json=question_set,
        )
        return KSADrillAttemptStartResponse(
            attempt_id=attempt.id,
            status="in_progress",
            version=attempt.assessment_version,
            selected_topic_keys=list(attempt.selected_topic_keys_json or []),
            question_set=[KSADrillQuestionRead(**item) for item in list(attempt.question_set_json or [])],
            started_at=attempt.started_at,
        )

    def get_ksa_drill_attempt(self, user: UserAccount, attempt_id: str) -> KSADrillAttemptRead | None:
        record = self.chat_repository.get_user_ksa_drill_attempt(user_id=user.id, attempt_id=attempt_id)
        if record is None:
            return None
        return self._build_ksa_drill_attempt_read(record)

    def get_latest_ksa_drill_attempt(self, user: UserAccount) -> KSADrillAttemptRead | None:
        record = self.chat_repository.get_latest_user_ksa_drill_attempt(user_id=user.id)
        if record is None:
            return None
        return self._build_ksa_drill_attempt_read(record)

    def upsert_ksa_drill_answers(
        self,
        user: UserAccount,
        attempt_id: str,
        payload: KSADrillAnswersUpsertRequest,
    ) -> KSADrillAttemptRead | None:
        record = self.chat_repository.upsert_user_ksa_drill_answers(
            user_id=user.id,
            attempt_id=attempt_id,
            answers_json=dict(payload.answers or {}),
        )
        if record is None:
            return None
        return self._build_ksa_drill_attempt_read(record)

    def complete_ksa_drill_attempt(self, user: UserAccount, attempt_id: str) -> KSAProfileRead | None:
        attempt = self.chat_repository.get_user_ksa_drill_attempt(user_id=user.id, attempt_id=attempt_id)
        if attempt is None:
            return None
        persisted_profile = self.chat_repository.get_user_ksa_profile(user.id)
        if persisted_profile is not None:
            base_profile_json = dict(persisted_profile.profile_json or {})
        else:
            fallback_profile = self.get_ksa_profile(user)
            base_profile_json = self._serialize_ksa_profile_read(fallback_profile)

        drill_outcome = evaluate_drill_attempt(
            user_id=user.id,
            selected_topic_keys=list(attempt.selected_topic_keys_json or []),
            question_set=list(attempt.question_set_json or []),
            answers=dict(attempt.answers_json or {}),
            base_profile_json=base_profile_json,
        )
        result_json = dict(drill_outcome.get("result_json") or {})
        profile_json = dict(drill_outcome.get("updated_profile_json") or {})
        completed = self.chat_repository.complete_user_ksa_drill_attempt(
            user_id=user.id,
            attempt_id=attempt.id,
            result_json=result_json,
        )
        if completed is None:
            return None
        self.chat_repository.upsert_user_ksa_profile(
            user_id=user.id,
            has_assessment=True,
            assessment_version=DRILL_ASSESSMENT_VERSION,
            profile_json=profile_json,
        )
        return self._build_ksa_profile_read(
            user_id=user.id,
            profile_json=profile_json,
            updated_at=completed.updated_at,
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
        if "skills" in next_values:
            next_values["skills"] = self._normalize_string_list(next_values["skills"])
        if "interests" in next_values:
            next_values["interests"] = self._normalize_string_list(next_values["interests"])
        if "work_experience" in next_values:
            next_values["work_experience"] = self._normalize_string_list(next_values["work_experience"])
        if "education_history" in next_values:
            next_values["education_history"] = self._normalize_string_list(next_values["education_history"])
        for field_name in {
            "profile_display_name",
            "about_me",
            "contact_location",
            "general_title",
            "date_of_birth",
            "current_reason_for_learning",
            "preferred_form_of_address",
            "learning_context_notes",
        }:
            next_values[field_name] = str(next_values.get(field_name, "")).strip()
        updated = self.chat_repository.upsert_user_learning_profile(
            user.id,
            fields={
                "profile_display_name": next_values["profile_display_name"],
                "about_me": next_values["about_me"],
                "contact_location": next_values["contact_location"],
                "general_title": next_values["general_title"],
                "date_of_birth": next_values["date_of_birth"],
                "current_skill_areas": next_values["current_skill_areas"],
                "skills": next_values["skills"],
                "interests": next_values["interests"],
                "work_experience": next_values["work_experience"],
                "education_history": next_values["education_history"],
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

    def list_diagnostic_definitions(self) -> DiagnosticCatalogRead:
        definitions: list[DiagnosticDefinitionRead] = []
        for record in self.chat_repository.list_latest_diagnostic_versions():
            content = dict(record.content_json or {})
            definitions.append(self._build_diagnostic_definition_read(content))
        return DiagnosticCatalogRead(definitions=sorted(definitions, key=lambda item: item.type))

    def get_diagnostic_definition(self, diagnostic_type: str) -> DiagnosticDefinitionRead | None:
        record = self.chat_repository.get_latest_diagnostic_version(diagnostic_type)
        if record is None:
            return None
        return self._build_diagnostic_definition_read(dict(record.content_json or {}))

    def start_diagnostic_attempt(self, user: UserAccount) -> DiagnosticAttemptStartResponse:
        definition_versions: dict[str, str] = {}
        for diagnostic_type in ("LAA", "MOA", "LTA"):
            version = self.chat_repository.get_latest_diagnostic_version(diagnostic_type)
            if version is not None:
                definition_versions[diagnostic_type] = version.version
        attempt = self.chat_repository.create_user_diagnostic_attempt(
            user_id=user.id,
            definition_versions=definition_versions,
        )
        return DiagnosticAttemptStartResponse(
            attempt_id=attempt.id,
            status=attempt.status,
            definition_versions=dict(attempt.definition_versions or {}),
            started_at=attempt.started_at,
        )

    def list_diagnostic_attempts(self, user: UserAccount) -> list[DiagnosticAttemptSummaryRead]:
        attempts = self.chat_repository.list_user_diagnostic_attempts(user_id=user.id)
        return [self._build_diagnostic_attempt_summary(item) for item in attempts]

    def delete_diagnostic_attempt(self, user: UserAccount, attempt_id: str) -> DiagnosticAttemptSummaryRead | None:
        deleted = self.chat_repository.delete_user_diagnostic_attempt(user_id=user.id, attempt_id=attempt_id)
        if deleted is None:
            return None
        return self._build_diagnostic_attempt_summary(deleted)

    def get_latest_diagnostic_attempt(self, user: UserAccount) -> DiagnosticAttemptDetailsRead | None:
        attempt = self.chat_repository.get_latest_user_diagnostic_attempt(user_id=user.id)
        if attempt is None:
            return None
        return self.get_diagnostic_attempt(user, attempt.id)

    def get_diagnostic_attempt(self, user: UserAccount, attempt_id: str) -> DiagnosticAttemptDetailsRead | None:
        attempt = self.chat_repository.get_user_diagnostic_attempt(user_id=user.id, attempt_id=attempt_id)
        if attempt is None:
            return None
        answers = self.chat_repository.list_user_diagnostic_answers(attempt_id=attempt.id)
        grouped_answers: dict[str, dict[str, object]] = {"LAA": {}, "MOA": {}, "LTA": {}}
        for answer in answers:
            grouped_answers.setdefault(answer.diagnostic_type, {})[answer.question_key] = answer.answer_json.get("value")
        result = self.chat_repository.get_user_diagnostic_result(attempt_id=attempt.id)
        return DiagnosticAttemptDetailsRead(
            attempt=self._build_diagnostic_attempt_summary(attempt),
            answers=grouped_answers,
            result=dict(result.result_json or {}) if result else None,
        )

    def upsert_diagnostic_answers(
        self,
        user: UserAccount,
        attempt_id: str,
        payload: DiagnosticAnswerUpsertRequest,
    ) -> DiagnosticAttemptDetailsRead | None:
        attempt = self.chat_repository.get_user_diagnostic_attempt(user_id=user.id, attempt_id=attempt_id)
        if attempt is None:
            return None
        for item in payload.answers:
            self.chat_repository.upsert_user_diagnostic_answer(
                attempt_id=attempt.id,
                diagnostic_type=payload.diagnostic_type,
                question_key=item.question_id,
                answer_json={"value": item.value},
            )
        return self.get_diagnostic_attempt(user, attempt.id)

    def complete_diagnostic_attempt(self, user: UserAccount, attempt_id: str) -> DiagnosticResultRead | None:
        attempt = self.chat_repository.get_user_diagnostic_attempt(user_id=user.id, attempt_id=attempt_id)
        if attempt is None:
            return None
        answers = self.chat_repository.list_user_diagnostic_answers(attempt_id=attempt.id)
        answers_by_type: dict[str, dict[str, object]] = {"LAA": {}, "MOA": {}, "LTA": {}}
        for answer in answers:
            answers_by_type.setdefault(answer.diagnostic_type, {})[answer.question_key] = answer.answer_json.get("value")

        definitions: dict[str, dict[str, object]] = {}
        for diagnostic_type in ("LAA", "MOA", "LTA"):
            version = self.chat_repository.get_latest_diagnostic_version(diagnostic_type)
            if version is not None:
                definitions[diagnostic_type] = dict(version.content_json or {})

        computed = score_attempt(definitions, answers_by_type)
        persisted = self.chat_repository.upsert_user_diagnostic_result(attempt_id=attempt.id, result_json=computed)
        self.chat_repository.mark_user_diagnostic_attempt_completed(attempt_id=attempt.id)
        return DiagnosticResultRead(attempt_id=attempt.id, result=dict(persisted.result_json or {}))

    def create_learning_state_check(self, user: UserAccount, payload: LearningStateCheckCreateRequest) -> LearningStateCheckRead:
        record = self.chat_repository.create_learning_state_check(
            {
                "user_id": user.id,
                "chat_id": payload.chat_id,
                "mood": payload.mood.strip(),
                "perceived_difficulty": payload.perceived_difficulty.strip(),
                "needs_pause_or_input": payload.needs_pause_or_input.strip(),
                "preferred_format": payload.preferred_format.strip(),
                "notes": payload.notes.strip(),
            }
        )
        return self._build_learning_state_check_read(record)

    def list_learning_state_checks(self, user: UserAccount, limit: int = 20) -> list[LearningStateCheckRead]:
        return [
            self._build_learning_state_check_read(item)
            for item in self.chat_repository.list_learning_state_checks(user_id=user.id, limit=max(1, min(200, limit)))
        ]

    def create_explanation_feedback(self, user: UserAccount, payload: ExplanationFeedbackCreateRequest) -> ExplanationFeedbackRead:
        record = self.chat_repository.create_explanation_feedback(
            {
                "user_id": user.id,
                "message_id": payload.message_id,
                "rating": payload.rating,
                "feedback_text": payload.feedback_text.strip(),
                "re_explain_requested": payload.re_explain_requested,
            }
        )
        return self._build_explanation_feedback_read(record)

    def list_learning_paths(self, user: UserAccount) -> LearningPathListResponse:
        paths = self.chat_repository.list_learning_paths(user_id=user.id, role=user.role)
        return LearningPathListResponse(paths=[self._build_learning_path_read(user, path) for path in paths])

    def list_courses(
        self,
        user: UserAccount,
        *,
        search: str = "",
        scope: str | None = None,
        status: str | None = None,
        owner_user_id: int | None = None,
        sort: str = "updated_desc",
    ) -> CourseListResponse:
        records = self.chat_repository.list_learning_paths(user_id=user.id, role=user.role)
        users_by_id = {account.id: account for account in self.chat_repository.list_users()}
        items: list[CourseListItemRead] = []
        lowered_search = search.strip().lower()
        for record in records:
            if user.role != "admin" and record.status == "archived":
                continue
            if scope and record.scope != scope:
                continue
            if status and record.status != status:
                continue
            if owner_user_id is not None and record.owner_user_id != owner_user_id:
                continue
            if lowered_search:
                haystack = f"{record.title} {record.description or ''}".lower()
                if lowered_search not in haystack:
                    continue
            modules = self.chat_repository.list_learning_modules(record.id)
            module_count = len(modules)
            lesson_count = sum(len(self.chat_repository.list_learning_lessons(module.id)) for module in modules)
            owner = users_by_id.get(record.owner_user_id or -1)
            items.append(
                CourseListItemRead(
                    id=record.id,
                    title=record.title,
                    description=record.description or "",
                    scope=record.scope,
                    owner_user_id=record.owner_user_id,
                    owner_username=owner.username if owner else None,
                    owner_displayname=owner.displayname if owner else None,
                    status=record.status,
                    subject=record.subject or "",
                    difficulty_level=record.difficulty_level or "",
                    module_count=module_count,
                    lesson_count=lesson_count,
                    updated_at=record.updated_at,
                    created_at=record.created_at,
                )
            )
        sorted_items = self._sort_courses(items, sort)
        return CourseListResponse(courses=sorted_items, total=len(sorted_items))

    def import_courses_from_uploads(
        self,
        user: UserAccount,
        uploads: list[UploadFilePayload],
        scopes_by_file_raw: str | None,
    ) -> CourseImportResponse:
        if len(uploads) > 5:
            raise ValueError("Upload supports up to 5 JSON files at a time")
        scopes_by_file = self._parse_course_scope_mapping(scopes_by_file_raw)
        seen_names: set[str] = set()
        results: list[CourseImportFileResultRead] = []
        for upload in uploads:
            file_name = Path(upload.file_name).name
            if not file_name.lower().endswith(".json"):
                results.append(
                    CourseImportFileResultRead(
                        file_name=file_name,
                        scope="user",
                        success=False,
                        error="Only .json files are supported",
                    )
                )
                continue
            if file_name in seen_names:
                results.append(
                    CourseImportFileResultRead(
                        file_name=file_name,
                        scope="user",
                        success=False,
                        error="Duplicate file selected",
                    )
                )
                continue
            seen_names.add(file_name)
            override_scope = scopes_by_file.get(file_name)
            try:
                definition = self.course_file_parser.parse_bytes(file_name, upload.content)
                definition = definition.model_copy(update={"scope": override_scope or definition.scope})
                self._validate_course_scope_for_user(user, definition.scope)
                self._validate_embedded_course_ids(definition, file_name=file_name, target_learning_path_id=None)
                upserted = self._upsert_course_definition(
                    definition,
                    owner_user_id=user.id if definition.scope == "user" else None,
                    enforce_owner=True,
                )
                self._write_course_file_for_path(upserted.id)
                results.append(
                    CourseImportFileResultRead(
                        file_name=file_name,
                        scope=upserted.scope,
                        success=True,
                        course_id=upserted.id,
                        title=upserted.title,
                    )
                )
            except Exception as error:
                results.append(
                    CourseImportFileResultRead(
                        file_name=file_name,
                        scope=override_scope or "user",
                        success=False,
                        error=str(error),
                    )
                )
        imported_count = sum(1 for item in results if item.success)
        failed_count = len(results) - imported_count
        return CourseImportResponse(imported_count=imported_count, failed_count=failed_count, results=results)

    def get_course_template(self) -> CourseTemplateResponse:
        return CourseTemplateResponse(
            file_name=self.course_file_parser.TEMPLATE_FILE_NAME,
            template=self.course_file_parser.template_payload(),
        )

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
        self._write_course_file_for_path(refreshed.id)
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
        self._write_course_file_for_path(refreshed.id)
        return self._build_learning_path_read(user, refreshed)

    def delete_learning_path(self, user: UserAccount, learning_path_id: str) -> LearningPathRead | None:
        record = self.chat_repository.get_learning_path(learning_path_id)
        if record is None:
            return None
        self._ensure_learning_path_edit_allowed(user, record, deleting=True)
        deleted = self.chat_repository.delete_learning_path(learning_path_id)
        if deleted is None:
            return None
        self._delete_course_file_for_course_id(learning_path_id)
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
        self._write_course_file_for_path(learning_path_id)
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
        self._write_course_file_for_path(learning_path.id)
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
        self._write_course_file_for_path(learning_path.id)
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
        self._write_course_file_for_path(learning_path_id)
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
        self._write_course_file_for_path(learning_path.id)
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
        self._write_course_file_for_path(learning_path.id)
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
        self._write_course_file_for_path(learning_path.id)
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
        self._write_course_file_for_path(learning_path.id)
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

    def _sort_courses(self, items: list[CourseListItemRead], sort: str) -> list[CourseListItemRead]:
        sort_key = sort if sort in COURSE_SORT_OPTIONS else "updated_desc"
        if sort_key == "name_asc":
            return sorted(items, key=lambda item: (item.title.lower(), item.updated_at), reverse=False)
        if sort_key == "name_desc":
            return sorted(items, key=lambda item: (item.title.lower(), item.updated_at), reverse=True)
        if sort_key == "updated_asc":
            return sorted(items, key=lambda item: item.updated_at, reverse=False)
        if sort_key == "modules_desc":
            return sorted(items, key=lambda item: (item.module_count, item.updated_at), reverse=True)
        if sort_key == "lessons_desc":
            return sorted(items, key=lambda item: (item.lesson_count, item.updated_at), reverse=True)
        if sort_key == "scope_global_first":
            return sorted(items, key=lambda item: (0 if item.scope == "global" else 1, item.title.lower()))
        if sort_key == "scope_user_first":
            return sorted(items, key=lambda item: (0 if item.scope == "user" else 1, item.title.lower()))
        return sorted(items, key=lambda item: item.updated_at, reverse=True)

    def _parse_course_scope_mapping(self, raw_value: str | None) -> dict[str, str]:
        if not raw_value:
            return {}
        payload = json.loads(raw_value)
        if not isinstance(payload, dict):
            raise ValueError("scopes_by_file must be a JSON object")
        mapping: dict[str, str] = {}
        for key, value in payload.items():
            file_name = Path(str(key)).name
            scope = str(value).strip().lower()
            if scope not in {"global", "user"}:
                raise ValueError(f"Invalid scope for {file_name}: {value}")
            mapping[file_name] = scope
        return mapping

    def _validate_course_scope_for_user(self, user: UserAccount, scope: str) -> None:
        if user.role == "student":
            raise PermissionError("Students cannot create learning paths")
        if scope == "global" and user.role != "admin":
            raise PermissionError("Only admins can create global learning paths")

    def _sync_courses_from_files(self) -> None:
        for path in sorted(self.courses_dir.glob("*.json")):
            try:
                definition = self.course_file_parser.parse_file(path)
                target_course_id = path.stem if self.chat_repository.get_learning_path(path.stem) is not None else None
                self._validate_embedded_course_ids(definition, file_name=path.name, target_learning_path_id=target_course_id)
                upserted = self._upsert_course_definition(
                    definition,
                    owner_user_id=definition.owner_user_id,
                    enforce_owner=False,
                    target_learning_path_id=target_course_id,
                )
                self._write_course_file_for_path(upserted.id)
                canonical_file_name = self.course_file_parser.safe_file_name(upserted.id, upserted.title)
                if path.name != canonical_file_name:
                    path.unlink(missing_ok=True)
            except Exception as error:
                logger.error("Course bootstrap skipped for %s: %s", path.name, error)

    def _export_courses_to_files(self) -> None:
        records = self.chat_repository.list_learning_paths(user_id=0, role="admin")
        for path in records:
            try:
                self._write_course_file_for_path(path.id)
            except Exception:
                logger.exception("Failed to export course file for learning path %s", path.id)
        self._delete_legacy_named_course_files({path.id for path in records})

    def _upsert_course_definition(
        self,
        definition: CourseDefinition,
        *,
        owner_user_id: int | None,
        enforce_owner: bool,
        target_learning_path_id: str | None = None,
    ) -> LearningPath:
        existing: LearningPath | None = None
        if target_learning_path_id:
            existing = self.chat_repository.get_learning_path(target_learning_path_id)
        resolved_owner = owner_user_id
        if definition.scope == "user":
            if enforce_owner and resolved_owner is None:
                raise ValueError("owner_user_id is required for user scope")
            if resolved_owner is not None:
                owner = self.chat_repository.get_user_by_id(resolved_owner)
                if owner is None:
                    raise ValueError(f"owner_user_id does not exist: {resolved_owner}")
            else:
                resolved_owner = definition.owner_user_id
        else:
            resolved_owner = None

        fields = {
            "scope": definition.scope,
            "owner_user_id": resolved_owner,
            "title": definition.title,
            "description": definition.description,
            "subject": definition.subject,
            "difficulty_level": definition.difficulty_level,
            "estimated_duration_minutes": definition.estimated_duration_minutes,
            "status": definition.status,
        }
        if existing is None:
            existing = self.chat_repository.create_learning_path(fields)
        else:
            updated = self.chat_repository.update_learning_path(existing.id, fields)
            if updated is not None:
                existing = updated
        modules_payload: list[dict[str, object]] = []
        for module in sorted(definition.modules, key=lambda item: item.order_index):
            lessons_payload: list[dict[str, object]] = []
            for lesson in sorted(module.lessons, key=lambda item: item.order_index):
                lesson_payload: dict[str, object] = {
                    "order_index": lesson.order_index,
                    "title": lesson.title,
                    "description": lesson.description,
                    "objectives": list(lesson.objectives),
                    "teaching_notes": lesson.teaching_notes,
                }
                lessons_payload.append(lesson_payload)
            module_payload: dict[str, object] = {
                "learning_path_id": existing.id,
                "order_index": module.order_index,
                "title": module.title,
                "description": module.description,
                "learning_objectives": list(module.learning_objectives),
                "lessons": lessons_payload,
            }
            modules_payload.append(module_payload)
        self.chat_repository.replace_learning_path_structure(existing.id, modules_payload)
        self.chat_repository.replace_learning_path_allowed_files(existing.id, definition.allowed_file_ids)
        self.chat_repository.replace_learning_path_allowed_tags(existing.id, definition.allowed_tags)
        refreshed = self.chat_repository.get_learning_path(existing.id)
        if refreshed is None:
            raise ValueError(f"Learning path not found after upsert: {existing.id}")
        return refreshed

    def _write_course_definition_file(self, definition: CourseDefinition) -> None:
        if not definition.id:
            raise ValueError("Cannot write course file without an id")
        file_name = self.course_file_parser.safe_file_name(definition.id, definition.title)
        payload = definition.model_dump()
        target = self.courses_dir / file_name
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self._delete_course_files_for_id(definition.id, keep=target.name)

    def _write_course_file_for_path(self, learning_path_id: str) -> None:
        try:
            path = self.chat_repository.get_learning_path(learning_path_id)
            if path is None:
                return
            modules = self.chat_repository.list_learning_modules(path.id)
            module_payload = []
            for module in modules:
                lessons = self.chat_repository.list_learning_lessons(module.id)
                module_payload.append(
                    {
                        "id": module.id,
                        "order_index": module.order_index,
                        "title": module.title,
                        "description": module.description or "",
                        "learning_objectives": list(module.learning_objectives or []),
                        "lessons": [
                            {
                                "id": lesson.id,
                                "order_index": lesson.order_index,
                                "title": lesson.title,
                                "description": lesson.description or "",
                                "objectives": list(lesson.objectives or []),
                                "teaching_notes": lesson.teaching_notes or "",
                            }
                            for lesson in lessons
                        ],
                    }
                )
            allowed_files = self.chat_repository.list_learning_path_allowed_files(path.id)
            allowed_tags = self.chat_repository.list_learning_path_allowed_tags(path.id)
            definition = CourseDefinition.model_validate(
                {
                    "schema_version": 1,
                    "id": path.id,
                    "title": path.title,
                    "description": path.description or "",
                    "scope": path.scope,
                    "owner_user_id": path.owner_user_id,
                    "subject": path.subject or "",
                    "difficulty_level": path.difficulty_level or "",
                    "estimated_duration_minutes": path.estimated_duration_minutes,
                    "status": path.status,
                    "allowed_file_ids": [item.file_id for item in allowed_files],
                    "allowed_tags": [item.tag for item in allowed_tags],
                    "modules": module_payload,
                }
            )
            self._write_course_definition_file(definition)
        except Exception:
            logger.exception("Failed to export course file for learning path %s", learning_path_id)

    def _delete_course_file_for_course_id(self, course_id: str) -> None:
        self._delete_course_files_for_id(course_id)

    def _delete_course_files_for_id(self, course_id: str, *, keep: str | None = None) -> None:
        for path in self.courses_dir.glob("*.json"):
            stem = path.stem
            if stem == course_id or stem.endswith(f"-{course_id}"):
                if keep is not None and path.name == keep:
                    continue
                path.unlink(missing_ok=True)

    def _delete_legacy_named_course_files(self, valid_course_ids: set[str]) -> None:
        for path in self.courses_dir.glob("*.json"):
            stem = path.stem
            if stem in valid_course_ids:
                continue
            for course_id in valid_course_ids:
                if stem.endswith(f"-{course_id}"):
                    path.unlink(missing_ok=True)
                    break

    def _validate_embedded_course_ids(
        self,
        definition: CourseDefinition,
        *,
        file_name: str,
        target_learning_path_id: str | None,
    ) -> None:
        allowed_module_ids: set[str] = set()
        allowed_lesson_ids: set[str] = set()
        if target_learning_path_id:
            for module in self.chat_repository.list_learning_modules(target_learning_path_id):
                allowed_module_ids.add(module.id)
                for lesson in self.chat_repository.list_learning_lessons(module.id):
                    allowed_lesson_ids.add(lesson.id)

        if definition.id:
            existing = self.chat_repository.get_learning_path(definition.id)
            if existing is not None and existing.id != target_learning_path_id:
                raise ValueError(f"{file_name}: id '{definition.id}' already exists; remove id fields from the JSON file")

        for module in definition.modules:
            if not module.id:
                continue
            existing_module = self.chat_repository.get_learning_module(module.id)
            if existing_module is not None and module.id not in allowed_module_ids:
                raise ValueError(f"{file_name}: module id '{module.id}' already exists; remove id fields from the JSON file")
            for lesson in module.lessons:
                if not lesson.id:
                    continue
                existing_lesson = self.chat_repository.get_learning_lesson(lesson.id)
                if existing_lesson is not None and lesson.id not in allowed_lesson_ids:
                    raise ValueError(f"{file_name}: lesson id '{lesson.id}' already exists; remove id fields from the JSON file")

    def _course_structure_signature(self, learning_path_id: str) -> tuple[tuple[object, ...], tuple[int, ...], tuple[str, ...]]:
        modules = self.chat_repository.list_learning_modules(learning_path_id)
        module_parts: list[object] = []
        for module in sorted(modules, key=lambda item: (item.order_index, item.title)):
            lessons = self.chat_repository.list_learning_lessons(module.id)
            lesson_parts = tuple(
                (
                    lesson.order_index,
                    lesson.title.strip(),
                    (lesson.description or "").strip(),
                    tuple(str(value).strip() for value in (lesson.objectives or [])),
                    (lesson.teaching_notes or "").strip(),
                )
                for lesson in sorted(lessons, key=lambda item: (item.order_index, item.title))
            )
            module_parts.append(
                (
                    module.order_index,
                    module.title.strip(),
                    (module.description or "").strip(),
                    tuple(str(value).strip() for value in (module.learning_objectives or [])),
                    lesson_parts,
                )
            )
        allowed_files = tuple(sorted(item.file_id for item in self.chat_repository.list_learning_path_allowed_files(learning_path_id)))
        allowed_tags = tuple(sorted(item.tag for item in self.chat_repository.list_learning_path_allowed_tags(learning_path_id)))
        return (tuple(module_parts), allowed_files, allowed_tags)

    def _dedupe_learning_paths(self) -> None:
        records = self.chat_repository.list_learning_paths(user_id=0, role="admin")
        grouped: dict[tuple[object, ...], list[LearningPath]] = {}
        for record in records:
            signature = self._course_structure_signature(record.id)
            key = (
                record.scope,
                record.owner_user_id,
                record.title.strip().lower(),
                (record.description or "").strip(),
                (record.subject or "").strip(),
                (record.difficulty_level or "").strip(),
                record.estimated_duration_minutes,
                record.status,
                signature,
            )
            grouped.setdefault(key, []).append(record)

        for group in grouped.values():
            if len(group) < 2:
                continue
            ordered = sorted(group, key=lambda item: (item.updated_at, item.created_at, item.id), reverse=True)
            keep = ordered[0]
            for duplicate in ordered[1:]:
                logger.warning("Deleting duplicate learning path %s (keeping %s)", duplicate.id, keep.id)
                self.chat_repository.delete_learning_path(duplicate.id)
                self._delete_course_file_for_course_id(duplicate.id)

    def _normalize_tags(self, tags: list[str]) -> list[str]:
        return sorted({tag.strip().lower() for tag in tags if tag.strip()})

    def _ensure_example_learning_path(self) -> None:
        try:
            existing_paths = self.chat_repository.list_learning_paths(user_id=0, role="admin")
            existing_titles = {path.title for path in existing_paths}
            if EXAMPLE_LEARNING_PATH_TITLE not in existing_titles:
                path = self.chat_repository.create_learning_path(
                    {
                        "id": EXAMPLE_LEARNING_PATH_ID,
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
                        "id": EXAMPLE_LEARNING_PATH_ID_SECOND,
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

    def _ensure_diagnostic_definitions(self) -> None:
        try:
            source_dirs = [
                Path(__file__).resolve().parents[3] / DIAGNOSTIC_PAGES_FALLBACK_SUBDIR,
                Path(self.settings.data_dir) / DIAGNOSTIC_DOC_SOURCE_SUBDIR,
            ]
            parsed_sources = []
            for source_dir in source_dirs:
                candidate_sources = load_parsed_sources(source_dir)
                if self._has_minimum_diagnostic_coverage(candidate_sources):
                    parsed_sources = candidate_sources
                    break
            for source in parsed_sources:
                definition = self.chat_repository.upsert_diagnostic_definition(
                    diagnostic_type=source.diagnostic_type,
                    title=str(source.definition.get("title") or source.diagnostic_type),
                )
                existing = self.chat_repository.get_diagnostic_version(
                    definition_id=definition.id,
                    version=source.version,
                )
                if existing is not None and existing.source_document_hash == source.file_hash:
                    continue
                if existing is not None:
                    version = self.chat_repository.update_diagnostic_version_content(
                        version_id=existing.id,
                        source_document_name=source.file_name,
                        source_document_hash=source.file_hash,
                        content_json=source.definition,
                    )
                    if version is None:
                        continue
                else:
                    version = self.chat_repository.create_diagnostic_version(
                        definition_id=definition.id,
                        version=source.version,
                        source_document_name=source.file_name,
                        source_document_hash=source.file_hash,
                        content_json=source.definition,
                    )
                self.chat_repository.replace_diagnostic_version_structure(
                    version_id=version.id,
                    definition=source.definition,
                )
        except Exception:
            logger.exception("Failed to ensure diagnostic definitions from source documents")

    def _has_minimum_diagnostic_coverage(self, parsed_sources: list) -> bool:
        if not parsed_sources:
            return False
        by_type = {item.diagnostic_type: item for item in parsed_sources}
        if {"LAA", "MOA", "LTA"} - set(by_type):
            return False
        for diagnostic_type in ("LAA", "MOA", "LTA"):
            definition = dict(getattr(by_type[diagnostic_type], "definition", {}) or {})
            question_count = sum(len(section.get("questions") or []) for section in definition.get("sections") or [])
            if question_count < 5:
                return False
        return True

    def _build_diagnostic_definition_read(self, content: dict[str, object]) -> DiagnosticDefinitionRead:
        return DiagnosticDefinitionRead.model_validate(
            {
                "id": str(content.get("id") or ""),
                "type": str(content.get("type") or "LAA"),
                "title": str(content.get("title") or ""),
                "version": str(content.get("version") or "v1"),
                "sections": content.get("sections") or [],
            }
        )

    def _build_diagnostic_attempt_summary(self, attempt) -> DiagnosticAttemptSummaryRead:
        return DiagnosticAttemptSummaryRead(
            attempt_id=attempt.id,
            status=attempt.status,
            definition_versions=dict(attempt.definition_versions or {}),
            started_at=attempt.started_at,
            completed_at=attempt.completed_at,
            is_latest=attempt.is_latest,
        )

    def _build_learning_state_check_read(self, record) -> LearningStateCheckRead:
        return LearningStateCheckRead(
            id=record.id,
            user_id=record.user_id,
            chat_id=record.chat_id,
            mood=record.mood or "",
            perceived_difficulty=record.perceived_difficulty or "",
            needs_pause_or_input=record.needs_pause_or_input or "",
            preferred_format=record.preferred_format or "",
            notes=record.notes or "",
            created_at=record.created_at,
        )

    def _build_explanation_feedback_read(self, record) -> ExplanationFeedbackRead:
        return ExplanationFeedbackRead(
            id=record.id,
            user_id=record.user_id,
            message_id=record.message_id,
            rating=record.rating,
            feedback_text=record.feedback_text or "",
            re_explain_requested=record.re_explain_requested,
            created_at=record.created_at,
        )

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
            "profile_display_name": profile.profile_display_name or "",
            "about_me": profile.about_me or "",
            "contact_location": profile.contact_location or "",
            "general_title": profile.general_title or "",
            "date_of_birth": profile.date_of_birth or "",
            "current_skill_areas": list(profile.current_skill_areas or []),
            "skills": list(profile.skills or []),
            "interests": list(profile.interests or []),
            "work_experience": list(profile.work_experience or []),
            "education_history": list(profile.education_history or []),
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
            profile_display_name=profile.profile_display_name or "",
            about_me=profile.about_me or "",
            contact_location=profile.contact_location or "",
            general_title=profile.general_title or "",
            date_of_birth=profile.date_of_birth or "",
            current_skill_areas=list(profile.current_skill_areas or []),
            skills=list(profile.skills or []),
            interests=list(profile.interests or []),
            work_experience=list(profile.work_experience or []),
            education_history=list(profile.education_history or []),
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

    def _build_ksa_profile_read(
        self,
        *,
        user_id: int,
        profile_json: dict[str, object],
        updated_at: datetime | None,
    ) -> KSAProfileRead:
        knowledge = dict(profile_json.get("knowledge") or {})
        skills = dict(profile_json.get("skills") or {})
        abilities = dict(profile_json.get("abilities") or {})
        assessment_details = dict(profile_json.get("assessment_details") or {})
        drill_state = dict(profile_json.get("drill_state") or {})
        derived = dict(assessment_details.get("derived") or {})
        return KSAProfileRead(
            user_id=user_id,
            has_assessment=bool(profile_json.get("has_assessment", True)),
            profile_source=str(profile_json.get("profile_source") or "assessment"),
            scale_min=1,
            scale_max=5,
            dreyfus_levels=list(profile_json.get("dreyfus_levels") or ["Novice", "Advanced", "Competent", "Proficient", "Expert"]),
            knowledge=KSAKnowledgeRead(
                stem_fundamentals=max(1, min(5, int(knowledge.get("stem_fundamentals", 1)))),
                information_technology=max(1, min(5, int(knowledge.get("information_technology", 1)))),
                humanities_social_sciences=max(1, min(5, int(knowledge.get("humanities_social_sciences", 1)))),
                languages_linguistics=max(1, min(5, int(knowledge.get("languages_linguistics", 1)))),
                business_commerce=max(1, min(5, int(knowledge.get("business_commerce", 1)))),
                legal_ethics=max(1, min(5, int(knowledge.get("legal_ethics", 1)))),
                health_wellness=max(1, min(5, int(knowledge.get("health_wellness", 1)))),
            ),
            skills=KSASkillsRead(
                literacy_numeracy=max(1, min(5, int(skills.get("literacy_numeracy", 1)))),
                digital_craft=max(1, min(5, int(skills.get("digital_craft", 1)))),
                strategic_execution=max(1, min(5, int(skills.get("strategic_execution", 1)))),
                operational_skills=max(1, min(5, int(skills.get("operational_skills", 1)))),
                relational_skills=max(1, min(5, int(skills.get("relational_skills", 1)))),
                research_inquiry=max(1, min(5, int(skills.get("research_inquiry", 1)))),
            ),
            abilities=KSAAbilitiesRead(
                quantitative_reasoning=max(1, min(5, int(abilities.get("quantitative_reasoning", 1)))),
                verbal_comprehension=max(1, min(5, int(abilities.get("verbal_comprehension", 1)))),
                spatial_visualization=max(1, min(5, int(abilities.get("spatial_visualization", 1)))),
                executive_function=max(1, min(5, int(abilities.get("executive_function", 1)))),
                sensory_perceptual=max(1, min(5, int(abilities.get("sensory_perceptual", 1)))),
                social_emotional_capacity=max(1, min(5, int(abilities.get("social_emotional_capacity", 1)))),
                divergent_thinking=max(1, min(5, int(abilities.get("divergent_thinking", 1)))),
            ),
            assessment_details=assessment_details or None,
            drill_state=drill_state or None,
            learning_speed_multiplier=float(derived.get("learning_speed_multiplier")) if derived.get("learning_speed_multiplier") is not None else None,
            updated_at=updated_at,
        )

    def _build_ksa_attempt_read(self, attempt) -> KSAAssessmentAttemptRead:
        return KSAAssessmentAttemptRead(
            attempt_id=attempt.id,
            status=attempt.status,
            version=attempt.assessment_version,
            started_at=attempt.started_at,
            completed_at=attempt.completed_at,
            answers=dict(attempt.answers_json or {}),
            result=dict(attempt.result_json or {}) if attempt.result_json else None,
        )

    def _build_ksa_drill_attempt_read(self, attempt) -> KSADrillAttemptRead:
        return KSADrillAttemptRead(
            attempt_id=attempt.id,
            status=attempt.status,
            version=attempt.assessment_version,
            selected_topic_keys=list(attempt.selected_topic_keys_json or []),
            question_set=[KSADrillQuestionRead(**item) for item in list(attempt.question_set_json or [])],
            started_at=attempt.started_at,
            completed_at=attempt.completed_at,
            answers=dict(attempt.answers_json or {}),
            result=dict(attempt.result_json or {}) if attempt.result_json else None,
        )

    def _serialize_ksa_profile_read(self, profile: KSAProfileRead) -> dict[str, object]:
        return {
            "user_id": profile.user_id,
            "has_assessment": profile.has_assessment,
            "profile_source": profile.profile_source,
            "scale_min": profile.scale_min,
            "scale_max": profile.scale_max,
            "dreyfus_levels": list(profile.dreyfus_levels),
            "knowledge": profile.knowledge.model_dump(),
            "skills": profile.skills.model_dump(),
            "abilities": profile.abilities.model_dump(),
            "assessment_details": dict(profile.assessment_details or {}),
            "drill_state": dict(profile.drill_state or {}),
        }

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
