from __future__ import annotations

from pathlib import Path

from services.common.config import Settings
from services.common.models import UserAccount
from services.retriever.prompt_builder import PromptBuilder
from services.retriever.services.retriever_service import RetrieverAppService, RetrieverDependencies


class LearningPreferenceRecord:
    def __init__(self, user_id: int, **fields) -> None:
        self.user_id = user_id
        self.updated_at = "2026-04-04T00:00:00Z"
        self.preferred_pace = fields.get("preferred_pace", "balanced")
        self.explanation_depth = fields.get("explanation_depth", "balanced")
        self.examples_vs_theory = fields.get("examples_vs_theory", "balanced")
        self.structure_preference = fields.get("structure_preference", "balanced")
        self.checkpoint_frequency = fields.get("checkpoint_frequency", "medium")
        self.encouragement_level = fields.get("encouragement_level", "balanced")
        self.guidance_level = fields.get("guidance_level", "balanced")
        self.recap_frequency = fields.get("recap_frequency", "medium")
        self.preferred_learning_format = fields.get("preferred_learning_format", "mixed")
        self.custom_preference_note = fields.get("custom_preference_note", "")


class LearningProfileRecord:
    def __init__(self, user_id: int, **fields) -> None:
        self.user_id = user_id
        self.updated_at = "2026-04-04T00:00:00Z"
        self.education_background = fields.get("education_background", "")
        self.current_skill_areas = fields.get("current_skill_areas", [])
        self.interests = fields.get("interests", [])
        self.professional_context = fields.get("professional_context", "")
        self.current_reason_for_learning = fields.get("current_reason_for_learning", "")
        self.preferred_form_of_address = fields.get("preferred_form_of_address", "")
        self.learning_context_notes = fields.get("learning_context_notes", "")


class LearningGoalRecord:
    def __init__(self, goal_id: str, user_id: int, payload: dict[str, object]) -> None:
        self.id = goal_id
        self.user_id = user_id
        self.target_topic = str(payload.get("target_topic") or "")
        self.reason_for_learning = str(payload.get("reason_for_learning") or "")
        self.target_level = str(payload.get("target_level") or "")
        self.deadline = payload.get("deadline")
        self.priority = payload.get("priority")
        self.notes = str(payload.get("notes") or "")
        self.is_active = bool(payload.get("is_active", True))
        self.created_at = "2026-04-04T00:00:00Z"
        self.updated_at = "2026-04-04T00:00:00Z"


class LearningProfileRepositoryStub:
    def __init__(self) -> None:
        self.preferences: dict[int, LearningPreferenceRecord] = {}
        self.profiles: dict[int, LearningProfileRecord] = {}
        self.goals: dict[int, list[LearningGoalRecord]] = {}
        self.goal_counter = 0

    def get_user_learning_preference(self, user_id: int):
        return self.preferences.get(user_id)

    def upsert_user_learning_preference(self, user_id: int, fields: dict[str, object]):
        record = self.preferences.get(user_id)
        if record is None:
            record = LearningPreferenceRecord(user_id, **fields)
            self.preferences[user_id] = record
            return record
        for key, value in fields.items():
            setattr(record, key, value)
        return record

    def get_user_learning_profile(self, user_id: int):
        return self.profiles.get(user_id)

    def upsert_user_learning_profile(self, user_id: int, fields: dict[str, object]):
        record = self.profiles.get(user_id)
        if record is None:
            record = LearningProfileRecord(user_id, **fields)
            self.profiles[user_id] = record
            return record
        for key, value in fields.items():
            setattr(record, key, value)
        return record

    def list_user_learning_goals(self, user_id: int):
        return self.goals.get(user_id, [])

    def create_user_learning_goal(self, payload: dict[str, object]):
        user_id = int(payload["user_id"])
        self.goal_counter += 1
        record = LearningGoalRecord(f"goal-{self.goal_counter}", user_id, payload)
        self.goals[user_id] = [record] + self.goals.get(user_id, [])
        return record

    def update_user_learning_goal(self, user_id: int, goal_id: str, fields: dict[str, object]):
        for goal in self.goals.get(user_id, []):
            if goal.id == goal_id:
                for key, value in fields.items():
                    setattr(goal, key, value)
                return goal
        return None

    def delete_user_learning_goal(self, user_id: int, goal_id: str):
        for goal in self.goals.get(user_id, []):
            if goal.id == goal_id:
                self.goals[user_id] = [entry for entry in self.goals.get(user_id, []) if entry.id != goal_id]
                return goal
        return None


class HistoryServiceStub:
    history_limit = 5


class RetrievalServiceStub:
    min_results = 2
    max_results = 8
    score_threshold = 0.7


class LlmClientStub:
    def invoke(self, _messages):
        return "ok"


class LibraryManagerStub:
    pass


class AttachmentClientStub:
    def process_files(self, _files):
        return []


def build_service(repository: LearningProfileRepositoryStub) -> RetrieverAppService:
    settings = Settings(data_dir=str(Path("data")), enable_refine_mode=True, enable_thinking_mode=True, default_assistant_mode="simple")
    return RetrieverAppService(
        RetrieverDependencies(
            chat_repository=repository,
            history_service=HistoryServiceStub(),
            retrieval_service=RetrievalServiceStub(),
            prompt_builder=PromptBuilder(Path("prompts")),
            llm_client=LlmClientStub(),
            library_manager=LibraryManagerStub(),
            attachment_client=AttachmentClientStub(),
            settings=settings,
        )
    )


def user(user_id: int) -> UserAccount:
    return UserAccount(
        id=user_id,
        username=f"user-{user_id}",
        displayname=f"User {user_id}",
        password_hash="hash",
        role="user",
        status="active",
        force_password_change=False,
    )


def test_declared_learning_profile_persists_per_user_and_normalizes_lists() -> None:
    repo = LearningProfileRepositoryStub()
    service = build_service(repo)

    user_one = user(1)
    user_two = user(2)

    service.update_learning_preferences(
        user_one,
        payload=service.get_learning_profile_bundle(user_one).preferences.model_copy(
            update={"preferred_pace": "slow", "custom_preference_note": "  Explain carefully  "}
        ),
    )

    service.update_learning_context(
        user_one,
        payload=service.get_learning_profile_bundle(user_one).context.model_copy(
            update={
                "current_skill_areas": ["Python", " python ", "Docker"],
                "interests": ["AI", "ai", "Education"],
            }
        ),
    )

    one_bundle = service.get_learning_profile_bundle(user_one)
    two_bundle = service.get_learning_profile_bundle(user_two)

    assert one_bundle.preferences.preferred_pace == "slow"
    assert one_bundle.preferences.custom_preference_note == "Explain carefully"
    assert one_bundle.context.current_skill_areas == ["Python", "python", "Docker"]
    assert one_bundle.context.interests == ["AI", "ai", "Education"]

    assert two_bundle.preferences.preferred_pace == "balanced"
    assert two_bundle.context.current_skill_areas == []
