from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


LearningPreferencePace = Literal["slow", "balanced", "fast"]
LearningPreferenceDepth = Literal["concise", "balanced", "detailed"]
LearningPreferenceExamplesTheory = Literal["more_examples", "balanced", "more_theory"]
LearningPreferenceStructure = Literal["more_structured", "balanced", "more_conversational"]
LearningPreferenceFrequency = Literal["low", "medium", "high"]
LearningPreferenceEncouragement = Literal["low", "balanced", "high"]
LearningPreferenceGuidance = Literal["step_by_step", "balanced", "more_independent"]
LearningPreferenceFormat = Literal["reading", "dialogue", "exercises", "mixed"]
LearningGoalPriority = Literal["low", "medium", "high"]


class LearningPreferencesRead(BaseModel):
    preferred_pace: LearningPreferencePace = "balanced"
    explanation_depth: LearningPreferenceDepth = "balanced"
    examples_vs_theory: LearningPreferenceExamplesTheory = "balanced"
    structure_preference: LearningPreferenceStructure = "balanced"
    checkpoint_frequency: LearningPreferenceFrequency = "medium"
    encouragement_level: LearningPreferenceEncouragement = "balanced"
    guidance_level: LearningPreferenceGuidance = "balanced"
    recap_frequency: LearningPreferenceFrequency = "medium"
    preferred_learning_format: LearningPreferenceFormat = "mixed"
    custom_preference_note: str = ""
    updated_at: datetime | None = None


class LearningPreferencesUpdateRequest(BaseModel):
    preferred_pace: LearningPreferencePace | None = None
    explanation_depth: LearningPreferenceDepth | None = None
    examples_vs_theory: LearningPreferenceExamplesTheory | None = None
    structure_preference: LearningPreferenceStructure | None = None
    checkpoint_frequency: LearningPreferenceFrequency | None = None
    encouragement_level: LearningPreferenceEncouragement | None = None
    guidance_level: LearningPreferenceGuidance | None = None
    recap_frequency: LearningPreferenceFrequency | None = None
    preferred_learning_format: LearningPreferenceFormat | None = None
    custom_preference_note: str | None = Field(default=None, max_length=4000)


class LearningProfileContextRead(BaseModel):
    education_background: str = ""
    current_skill_areas: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    professional_context: str = ""
    current_reason_for_learning: str = ""
    preferred_form_of_address: str = ""
    learning_context_notes: str = ""
    updated_at: datetime | None = None


class LearningProfileContextUpdateRequest(BaseModel):
    education_background: str | None = Field(default=None, max_length=4000)
    current_skill_areas: list[str] | None = None
    interests: list[str] | None = None
    professional_context: str | None = Field(default=None, max_length=4000)
    current_reason_for_learning: str | None = Field(default=None, max_length=4000)
    preferred_form_of_address: str | None = Field(default=None, max_length=255)
    learning_context_notes: str | None = Field(default=None, max_length=4000)

    @field_validator("current_skill_areas", "interests")
    @classmethod
    def validate_string_list_size(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        if len(value) > 50:
            raise ValueError("Maximum 50 items allowed")
        return value


class LearningGoalRead(BaseModel):
    id: str
    target_topic: str
    reason_for_learning: str = ""
    target_level: str = ""
    deadline: date | None = None
    priority: LearningGoalPriority | None = None
    notes: str = ""
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class LearningGoalCreateRequest(BaseModel):
    target_topic: str = Field(min_length=1, max_length=255)
    reason_for_learning: str = Field(default="", max_length=4000)
    target_level: str = Field(default="", max_length=128)
    deadline: date | None = None
    priority: LearningGoalPriority | None = None
    notes: str = Field(default="", max_length=4000)
    is_active: bool = True


class LearningGoalUpdateRequest(BaseModel):
    target_topic: str | None = Field(default=None, min_length=1, max_length=255)
    reason_for_learning: str | None = Field(default=None, max_length=4000)
    target_level: str | None = Field(default=None, max_length=128)
    deadline: date | None = None
    priority: LearningGoalPriority | None = None
    notes: str | None = Field(default=None, max_length=4000)
    is_active: bool | None = None


class LearningProfileBundleRead(BaseModel):
    preferences: LearningPreferencesRead
    context: LearningProfileContextRead
    goals: list[LearningGoalRead] = Field(default_factory=list)
    diagnostics_status: Literal["not_started"] = "not_started"
