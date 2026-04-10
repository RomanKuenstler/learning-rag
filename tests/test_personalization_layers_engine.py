from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace

from services.retriever.services.personalization_layers import (
    GROUP_CAPABILITY_MASTERY,
    GROUP_DECLARED_PREFERENCES,
    GROUP_DIAGNOSED_LEARNING,
    GROUP_GOAL_INTENT,
    GROUP_IDENTITY_CONTEXT,
    GROUP_LIVE_ADAPTATION,
    GROUP_REASON_MAP,
    LearningPersonalizationLayerEngine,
)


@dataclass
class InMemoryLayerRecord:
    user_id: int
    rule_engine_version: str = "v1"
    identity_context_snapshot: dict = None
    resolved_identity_context_rules: dict = None
    goal_intent_snapshot: dict = None
    resolved_goal_rules: dict = None
    declared_preferences_snapshot: dict = None
    resolved_declared_tutor_rules: dict = None
    diagnosed_learning_snapshot: dict = None
    resolved_diagnostic_rules: dict = None
    capability_mastery_snapshot: dict = None
    resolved_capability_rules: dict = None
    live_adaptation_snapshot: dict = None
    resolved_live_adaptation_rules: dict = None
    last_source_hashes_json: dict = None
    source_to_group_trace_json: dict = None
    change_log_json: list = None
    identity_context_updated_at: datetime | None = None
    goal_intent_updated_at: datetime | None = None
    declared_preferences_updated_at: datetime | None = None
    diagnosed_learning_updated_at: datetime | None = None
    capability_mastery_updated_at: datetime | None = None
    live_adaptation_updated_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        self.identity_context_snapshot = self.identity_context_snapshot or {}
        self.resolved_identity_context_rules = self.resolved_identity_context_rules or {}
        self.goal_intent_snapshot = self.goal_intent_snapshot or {}
        self.resolved_goal_rules = self.resolved_goal_rules or {}
        self.declared_preferences_snapshot = self.declared_preferences_snapshot or {}
        self.resolved_declared_tutor_rules = self.resolved_declared_tutor_rules or {}
        self.diagnosed_learning_snapshot = self.diagnosed_learning_snapshot or {}
        self.resolved_diagnostic_rules = self.resolved_diagnostic_rules or {}
        self.capability_mastery_snapshot = self.capability_mastery_snapshot or {}
        self.resolved_capability_rules = self.resolved_capability_rules or {}
        self.live_adaptation_snapshot = self.live_adaptation_snapshot or {}
        self.resolved_live_adaptation_rules = self.resolved_live_adaptation_rules or {}
        self.last_source_hashes_json = self.last_source_hashes_json or {}
        self.source_to_group_trace_json = self.source_to_group_trace_json or {}
        self.change_log_json = self.change_log_json or []


class InMemoryRepository:
    def __init__(self) -> None:
        self.record_by_user: dict[int, InMemoryLayerRecord] = {}
        self.profile = SimpleNamespace(
            preferred_form_of_address="",
            profile_display_name="",
            general_title="",
            date_of_birth="",
            about_me="",
            contact_location="",
            skills=[],
            interests=[],
            work_experience=[],
            education_history=[],
            current_skill_areas=[],
            current_reason_for_learning="",
            learning_context_notes="",
        )
        self.preference = SimpleNamespace(
            preferred_pace="balanced",
            explanation_depth="balanced",
            examples_vs_theory="balanced",
            structure_preference="balanced",
            checkpoint_frequency="medium",
            encouragement_level="balanced",
            guidance_level="balanced",
            recap_frequency="medium",
            preferred_learning_format="mixed",
            custom_preference_note="",
        )
        self.goals = []
        self.settings = {}
        self.ksa_profile = SimpleNamespace(profile_json={})
        self.diagnostic_attempt = None
        self.diagnostic_result = None
        self.state_checks = []
        self.feedback_rows = []

    def get_user_learning_profile(self, _user_id: int):
        return self.profile

    def get_user_learning_preference(self, _user_id: int):
        return self.preference

    def list_user_learning_goals(self, _user_id: int):
        return list(self.goals)

    def list_settings(self, _user_id: int):
        return [SimpleNamespace(key=key, value=value) for key, value in self.settings.items()]

    def get_latest_user_diagnostic_attempt(self, *, user_id: int):
        _ = user_id
        return self.diagnostic_attempt

    def get_user_diagnostic_result(self, *, attempt_id: str):
        _ = attempt_id
        return self.diagnostic_result

    def list_user_diagnostic_attempts(self, *, user_id: int):
        _ = user_id
        return [self.diagnostic_attempt] if self.diagnostic_attempt is not None else []

    def get_user_ksa_profile(self, _user_id: int):
        return self.ksa_profile

    def get_latest_user_ksa_drill_attempt(self, *, user_id: int):
        _ = user_id
        return None

    def list_user_ksa_drill_attempts(self, *, user_id: int, limit: int = 10):
        _ = user_id
        _ = limit
        return []

    def list_learning_state_checks(self, *, user_id: int, limit: int = 20):
        _ = user_id
        return list(self.state_checks)[:limit]

    def list_explanation_feedback(self, *, user_id: int, limit: int = 30):
        _ = user_id
        return list(self.feedback_rows)[:limit]

    def get_user_learning_personalization_layers(self, *, user_id: int):
        return self.record_by_user.get(user_id)

    def upsert_user_learning_personalization_layers(self, *, user_id: int, fields: dict[str, object]):
        record = self.record_by_user.get(user_id)
        if record is None:
            record = InMemoryLayerRecord(user_id=user_id)
            self.record_by_user[user_id] = record
        for key, value in fields.items():
            setattr(record, key, value)
        record.updated_at = datetime.now(timezone.utc)
        return record


def _user() -> SimpleNamespace:
    return SimpleNamespace(id=7, username="sven", displayname="Sven")


def _engine(repo: InMemoryRepository) -> LearningPersonalizationLayerEngine:
    return LearningPersonalizationLayerEngine(
        repo,
        available_assistant_modes=["simple", "refine", "thinking"],
        default_assistant_mode="simple",
    )


def test_declared_preferences_resolution_maps_custom_flags() -> None:
    repo = InMemoryRepository()
    repo.preference.examples_vs_theory = "more_examples"
    repo.preference.guidance_level = "step_by_step"
    repo.preference.custom_preference_note = "Please explain slowly and avoid too much theory"

    record = _engine(repo).recompute_for_reasons(user=_user(), reasons=["learning_preferences_updated"])

    flags = list(record.declared_preferences_snapshot.get("declared_preference_flags") or [])
    resolved = dict(record.resolved_declared_tutor_rules or {})

    assert "explain_slowly" in flags
    assert "avoid_theory" in flags
    assert resolved["explanation_order"] == "example_first"
    assert resolved["resolved_declared_tutor_rules"]["hint_before_answer"] is True


def test_capability_snapshot_keeps_competence_and_confidence_separate() -> None:
    repo = InMemoryRepository()
    repo.ksa_profile = SimpleNamespace(
        profile_json={
            "knowledge": {"stem_fundamentals": 2},
            "skills": {"digital_craft": 2},
            "abilities": {"quantitative_reasoning": 2},
            "drill_state": {
                "topic_nodes": {
                    "stem_fundamentals": {"level": 2.0, "confidence": 0.9, "map_decay_events_total": 1, "status": "map_decay"},
                    "digital_craft": {"level": 4.4, "confidence": 0.4, "map_decay_events_total": 0, "status": "verified"},
                }
            },
            "assessment_details": {"derived": {"learning_speed_multiplier": 1.5}},
        }
    )

    record = _engine(repo).recompute_for_reasons(user=_user(), reasons=["ksa_updated"])

    topic_state = dict(record.capability_mastery_snapshot.get("ksa_topic_state") or {})
    assert float(topic_state["stem_fundamentals"]["competence_level"]) != float(topic_state["stem_fundamentals"]["confidence_level"])
    assert float(record.capability_mastery_snapshot["topic_mastery_estimates"]["digital_craft"]) != float(
        record.capability_mastery_snapshot["topic_confidence_estimates"]["digital_craft"]
    )


def test_live_recompute_does_not_overwrite_identity_snapshot() -> None:
    repo = InMemoryRepository()
    repo.profile.profile_display_name = "Ari"
    engine = _engine(repo)

    first = engine.recompute_for_reasons(user=_user(), reasons=["learning_context_updated"])
    first_name = first.identity_context_snapshot["identity_profile"]["chosen_name"]
    first_hash = str(first.last_source_hashes_json.get(GROUP_IDENTITY_CONTEXT) or "")

    repo.state_checks = [
        SimpleNamespace(
            mood="tired",
            perceived_difficulty="hard",
            needs_pause_or_input="pause",
            preferred_format="dialogue",
            notes="Need a short pause",
        )
    ]
    engine.recompute_for_reasons(user=_user(), reasons=["learning_state_check_created"])
    second = repo.get_user_learning_personalization_layers(user_id=7)

    assert second.identity_context_snapshot["identity_profile"]["chosen_name"] == first_name
    assert str(second.last_source_hashes_json.get(GROUP_IDENTITY_CONTEXT) or "") == first_hash


def test_reason_map_covers_expected_group_triggers() -> None:
    assert GROUP_REASON_MAP["learning_context_updated"] == {GROUP_IDENTITY_CONTEXT}
    assert GROUP_REASON_MAP["learning_goal_updated"] == {GROUP_GOAL_INTENT}
    assert GROUP_REASON_MAP["learning_preferences_updated"] == {GROUP_DECLARED_PREFERENCES}
    assert GROUP_REASON_MAP["diagnostic_completed"] == {GROUP_DIAGNOSED_LEARNING}
    assert GROUP_REASON_MAP["ksa_updated"] == {GROUP_CAPABILITY_MASTERY}
    assert GROUP_REASON_MAP["learning_state_check_created"] == {GROUP_LIVE_ADAPTATION}
    assert GROUP_REASON_MAP["explanation_feedback_created"] == {GROUP_LIVE_ADAPTATION}
