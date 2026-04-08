from __future__ import annotations

from services.common.models import (
    ChatMessage,
    ChatSession,
    DiagnosticDefinition,
    DiagnosticVersion,
    ExplanationFeedback,
    GPTChatSession,
    GPTRecord,
    LearningLesson,
    LearningStateCheck,
    LearningModule,
    LearningPath,
    LearningPathAllowedFile,
    LearningPathAllowedTag,
    MessageAttachment,
    RetrievalLog,
    SettingRecord,
    UserLearningGoal,
    UserKSAAssessmentAttempt,
    UserKSAProfile,
    UserLearningPreference,
    UserLearningProfile,
    UserDiagnosticAnswer,
    UserDiagnosticAttempt,
    UserDiagnosticResult,
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

    def get_user_learning_preference(self, user_id: int) -> UserLearningPreference | None:
        return self.postgres_client.get_user_learning_preference(user_id=user_id)

    def upsert_user_learning_preference(self, user_id: int, fields: dict[str, object]) -> UserLearningPreference:
        return self.postgres_client.upsert_user_learning_preference(user_id=user_id, fields=fields)

    def get_user_learning_profile(self, user_id: int) -> UserLearningProfile | None:
        return self.postgres_client.get_user_learning_profile(user_id=user_id)

    def upsert_user_learning_profile(self, user_id: int, fields: dict[str, object]) -> UserLearningProfile:
        return self.postgres_client.upsert_user_learning_profile(user_id=user_id, fields=fields)

    def list_user_learning_goals(self, user_id: int) -> list[UserLearningGoal]:
        return self.postgres_client.list_user_learning_goals(user_id=user_id)

    def create_user_learning_goal(self, payload: dict[str, object]) -> UserLearningGoal:
        return self.postgres_client.create_user_learning_goal(payload=payload)

    def update_user_learning_goal(self, user_id: int, goal_id: str, fields: dict[str, object]) -> UserLearningGoal | None:
        return self.postgres_client.update_user_learning_goal(user_id=user_id, goal_id=goal_id, fields=fields)

    def delete_user_learning_goal(self, user_id: int, goal_id: str) -> UserLearningGoal | None:
        return self.postgres_client.delete_user_learning_goal(user_id=user_id, goal_id=goal_id)

    def get_user_ksa_profile(self, user_id: int) -> UserKSAProfile | None:
        return self.postgres_client.get_user_ksa_profile(user_id=user_id)

    def upsert_user_ksa_profile(
        self,
        user_id: int,
        *,
        has_assessment: bool,
        assessment_version: str,
        profile_json: dict[str, object],
    ) -> UserKSAProfile:
        return self.postgres_client.upsert_user_ksa_profile(
            user_id=user_id,
            has_assessment=has_assessment,
            assessment_version=assessment_version,
            profile_json=profile_json,
        )

    def create_user_ksa_assessment_attempt(self, *, user_id: int, assessment_version: str) -> UserKSAAssessmentAttempt:
        return self.postgres_client.create_user_ksa_assessment_attempt(
            user_id=user_id,
            assessment_version=assessment_version,
        )

    def get_user_ksa_assessment_attempt(self, *, user_id: int, attempt_id: str) -> UserKSAAssessmentAttempt | None:
        return self.postgres_client.get_user_ksa_assessment_attempt(user_id=user_id, attempt_id=attempt_id)

    def get_latest_user_ksa_assessment_attempt(self, *, user_id: int) -> UserKSAAssessmentAttempt | None:
        return self.postgres_client.get_latest_user_ksa_assessment_attempt(user_id=user_id)

    def upsert_user_ksa_assessment_answers(
        self,
        *,
        user_id: int,
        attempt_id: str,
        answers_json: dict[str, object],
    ) -> UserKSAAssessmentAttempt | None:
        return self.postgres_client.upsert_user_ksa_assessment_answers(
            user_id=user_id,
            attempt_id=attempt_id,
            answers_json=answers_json,
        )

    def complete_user_ksa_assessment_attempt(
        self,
        *,
        user_id: int,
        attempt_id: str,
        result_json: dict[str, object],
    ) -> UserKSAAssessmentAttempt | None:
        return self.postgres_client.complete_user_ksa_assessment_attempt(
            user_id=user_id,
            attempt_id=attempt_id,
            result_json=result_json,
        )

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

    def list_learning_paths(self, *, user_id: int, role: str) -> list[LearningPath]:
        return self.postgres_client.list_learning_paths(user_id=user_id, role=role)

    def get_learning_path(self, learning_path_id: str) -> LearningPath | None:
        return self.postgres_client.get_learning_path(learning_path_id)

    def create_learning_path(self, payload: dict[str, object]) -> LearningPath:
        return self.postgres_client.create_learning_path(payload)

    def update_learning_path(self, learning_path_id: str, fields: dict[str, object]) -> LearningPath | None:
        return self.postgres_client.update_learning_path(learning_path_id, fields)

    def delete_learning_path(self, learning_path_id: str) -> LearningPath | None:
        return self.postgres_client.delete_learning_path(learning_path_id)

    def list_learning_modules(self, learning_path_id: str) -> list[LearningModule]:
        return self.postgres_client.list_learning_modules(learning_path_id)

    def create_learning_module(self, payload: dict[str, object]) -> LearningModule:
        return self.postgres_client.create_learning_module(payload)

    def get_learning_module(self, module_id: str) -> LearningModule | None:
        return self.postgres_client.get_learning_module(module_id)

    def update_learning_module(self, module_id: str, fields: dict[str, object]) -> LearningModule | None:
        return self.postgres_client.update_learning_module(module_id, fields)

    def delete_learning_module(self, module_id: str) -> LearningModule | None:
        return self.postgres_client.delete_learning_module(module_id)

    def reorder_learning_modules(self, learning_path_id: str, module_orders: list[tuple[str, int]]) -> list[LearningModule]:
        return self.postgres_client.reorder_learning_modules(learning_path_id, module_orders)

    def list_learning_lessons(self, module_id: str) -> list[LearningLesson]:
        return self.postgres_client.list_learning_lessons(module_id)

    def create_learning_lesson(self, payload: dict[str, object]) -> LearningLesson:
        return self.postgres_client.create_learning_lesson(payload)

    def get_learning_lesson(self, lesson_id: str) -> LearningLesson | None:
        return self.postgres_client.get_learning_lesson(lesson_id)

    def update_learning_lesson(self, lesson_id: str, fields: dict[str, object]) -> LearningLesson | None:
        return self.postgres_client.update_learning_lesson(lesson_id, fields)

    def delete_learning_lesson(self, lesson_id: str) -> LearningLesson | None:
        return self.postgres_client.delete_learning_lesson(lesson_id)

    def reorder_learning_lessons(self, module_id: str, lesson_orders: list[tuple[str, int]]) -> list[LearningLesson]:
        return self.postgres_client.reorder_learning_lessons(module_id, lesson_orders)

    def replace_learning_path_structure(self, learning_path_id: str, modules: list[dict[str, object]]) -> list[LearningModule]:
        return self.postgres_client.replace_learning_path_structure(learning_path_id, modules)

    def replace_learning_path_allowed_files(self, learning_path_id: str, file_ids: list[int]) -> None:
        self.postgres_client.replace_learning_path_allowed_files(learning_path_id, file_ids)

    def replace_learning_path_allowed_tags(self, learning_path_id: str, tags: list[str]) -> None:
        self.postgres_client.replace_learning_path_allowed_tags(learning_path_id, tags)

    def list_learning_path_allowed_files(self, learning_path_id: str) -> list[LearningPathAllowedFile]:
        return self.postgres_client.list_learning_path_allowed_files(learning_path_id)

    def list_learning_path_allowed_tags(self, learning_path_id: str) -> list[LearningPathAllowedTag]:
        return self.postgres_client.list_learning_path_allowed_tags(learning_path_id)

    def get_diagnostic_definition(self, diagnostic_type: str) -> DiagnosticDefinition | None:
        return self.postgres_client.get_diagnostic_definition(diagnostic_type)

    def upsert_diagnostic_definition(self, *, diagnostic_type: str, title: str) -> DiagnosticDefinition:
        return self.postgres_client.upsert_diagnostic_definition(diagnostic_type=diagnostic_type, title=title)

    def get_diagnostic_version(self, *, definition_id: str, version: str) -> DiagnosticVersion | None:
        return self.postgres_client.get_diagnostic_version(definition_id=definition_id, version=version)

    def list_latest_diagnostic_versions(self) -> list[DiagnosticVersion]:
        return self.postgres_client.list_latest_diagnostic_versions()

    def get_latest_diagnostic_version(self, diagnostic_type: str) -> DiagnosticVersion | None:
        return self.postgres_client.get_latest_diagnostic_version(diagnostic_type)

    def create_diagnostic_version(
        self,
        *,
        definition_id: str,
        version: str,
        source_document_name: str,
        source_document_hash: str,
        content_json: dict[str, object],
    ) -> DiagnosticVersion:
        return self.postgres_client.create_diagnostic_version(
            definition_id=definition_id,
            version=version,
            source_document_name=source_document_name,
            source_document_hash=source_document_hash,
            content_json=content_json,
        )

    def update_diagnostic_version_content(
        self,
        *,
        version_id: str,
        source_document_name: str,
        source_document_hash: str,
        content_json: dict[str, object],
    ) -> DiagnosticVersion | None:
        return self.postgres_client.update_diagnostic_version_content(
            version_id=version_id,
            source_document_name=source_document_name,
            source_document_hash=source_document_hash,
            content_json=content_json,
        )

    def replace_diagnostic_version_structure(self, *, version_id: str, definition: dict[str, object]) -> None:
        self.postgres_client.replace_diagnostic_version_structure(version_id=version_id, definition=definition)

    def create_user_diagnostic_attempt(self, *, user_id: int, definition_versions: dict[str, str]) -> UserDiagnosticAttempt:
        return self.postgres_client.create_user_diagnostic_attempt(user_id=user_id, definition_versions=definition_versions)

    def get_user_diagnostic_attempt(self, *, user_id: int, attempt_id: str) -> UserDiagnosticAttempt | None:
        return self.postgres_client.get_user_diagnostic_attempt(user_id=user_id, attempt_id=attempt_id)

    def get_latest_user_diagnostic_attempt(self, *, user_id: int) -> UserDiagnosticAttempt | None:
        return self.postgres_client.get_latest_user_diagnostic_attempt(user_id=user_id)

    def list_user_diagnostic_attempts(self, *, user_id: int) -> list[UserDiagnosticAttempt]:
        return self.postgres_client.list_user_diagnostic_attempts(user_id=user_id)

    def delete_user_diagnostic_attempt(self, *, user_id: int, attempt_id: str) -> UserDiagnosticAttempt | None:
        return self.postgres_client.delete_user_diagnostic_attempt(user_id=user_id, attempt_id=attempt_id)

    def upsert_user_diagnostic_answer(
        self,
        *,
        attempt_id: str,
        diagnostic_type: str,
        question_key: str,
        answer_json: dict[str, object],
    ) -> UserDiagnosticAnswer:
        return self.postgres_client.upsert_user_diagnostic_answer(
            attempt_id=attempt_id,
            diagnostic_type=diagnostic_type,
            question_key=question_key,
            answer_json=answer_json,
        )

    def list_user_diagnostic_answers(self, *, attempt_id: str) -> list[UserDiagnosticAnswer]:
        return self.postgres_client.list_user_diagnostic_answers(attempt_id=attempt_id)

    def upsert_user_diagnostic_result(self, *, attempt_id: str, result_json: dict[str, object]) -> UserDiagnosticResult:
        return self.postgres_client.upsert_user_diagnostic_result(attempt_id=attempt_id, result_json=result_json)

    def get_user_diagnostic_result(self, *, attempt_id: str) -> UserDiagnosticResult | None:
        return self.postgres_client.get_user_diagnostic_result(attempt_id=attempt_id)

    def mark_user_diagnostic_attempt_completed(self, *, attempt_id: str) -> UserDiagnosticAttempt | None:
        return self.postgres_client.mark_user_diagnostic_attempt_completed(attempt_id=attempt_id)

    def create_learning_state_check(self, payload: dict[str, object]) -> LearningStateCheck:
        return self.postgres_client.create_learning_state_check(payload)

    def list_learning_state_checks(self, *, user_id: int, limit: int = 20) -> list[LearningStateCheck]:
        return self.postgres_client.list_learning_state_checks(user_id=user_id, limit=limit)

    def create_explanation_feedback(self, payload: dict[str, object]) -> ExplanationFeedback:
        return self.postgres_client.create_explanation_feedback(payload)
