from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


DiagnosticType = Literal["LAA", "MOA", "LTA"]
QuestionType = Literal["single_choice", "multi_choice", "likert", "slider", "text"]


class DiagnosticOptionRead(BaseModel):
    key: str
    label: str
    value: str | None = None
    allows_text: bool = False


class DiagnosticQuestionRead(BaseModel):
    id: str
    text: str
    type: QuestionType
    options: list[DiagnosticOptionRead] = Field(default_factory=list)
    min_value: int | None = None
    max_value: int | None = None


class DiagnosticSectionRead(BaseModel):
    id: str
    title: str
    questions: list[DiagnosticQuestionRead] = Field(default_factory=list)


class DiagnosticDefinitionRead(BaseModel):
    id: str
    type: DiagnosticType
    title: str
    version: str
    sections: list[DiagnosticSectionRead] = Field(default_factory=list)


class DiagnosticCatalogRead(BaseModel):
    definitions: list[DiagnosticDefinitionRead] = Field(default_factory=list)


class DiagnosticAnswerItem(BaseModel):
    question_id: str
    value: Any


class DiagnosticAnswerUpsertRequest(BaseModel):
    diagnostic_type: DiagnosticType
    answers: list[DiagnosticAnswerItem] = Field(default_factory=list)


class DiagnosticAttemptStartResponse(BaseModel):
    attempt_id: str
    status: str
    definition_versions: dict[str, str]
    started_at: datetime


class DiagnosticAttemptSummaryRead(BaseModel):
    attempt_id: str
    status: str
    definition_versions: dict[str, str]
    started_at: datetime
    completed_at: datetime | None = None
    is_latest: bool


class DiagnosticAttemptDetailsRead(BaseModel):
    attempt: DiagnosticAttemptSummaryRead
    answers: dict[str, dict[str, Any]] = Field(default_factory=dict)
    result: dict[str, Any] | None = None


class DiagnosticResultRead(BaseModel):
    attempt_id: str
    result: dict[str, Any]


class LearningStateCheckCreateRequest(BaseModel):
    chat_id: str | None = None
    mood: str = Field(default="", max_length=64)
    perceived_difficulty: str = Field(default="", max_length=64)
    needs_pause_or_input: str = Field(default="", max_length=64)
    preferred_format: str = Field(default="", max_length=64)
    notes: str = Field(default="", max_length=4000)


class LearningStateCheckRead(BaseModel):
    id: int
    user_id: int
    chat_id: str | None = None
    mood: str
    perceived_difficulty: str
    needs_pause_or_input: str
    preferred_format: str
    notes: str
    created_at: datetime


class ExplanationFeedbackCreateRequest(BaseModel):
    message_id: int | None = None
    rating: int = Field(ge=1, le=5)
    feedback_text: str = Field(default="", max_length=4000)
    re_explain_requested: bool = False


class ExplanationFeedbackRead(BaseModel):
    id: int
    user_id: int
    message_id: int | None = None
    rating: int
    feedback_text: str
    re_explain_requested: bool
    created_at: datetime
