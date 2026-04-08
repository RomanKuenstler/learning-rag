from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


KSAAttemptStatus = Literal["in_progress", "completed"]


class KSAAssessmentDefinitionRead(BaseModel):
    version: str
    time_limit_seconds: int = 30
    phase1_sliders: list[dict[str, object]] = Field(default_factory=list)
    knowledge_questions: list[dict[str, object]] = Field(default_factory=list)
    skill_questions: list[dict[str, object]] = Field(default_factory=list)
    ability_questions: list[dict[str, object]] = Field(default_factory=list)


class KSAAssessmentStartResponse(BaseModel):
    attempt_id: str
    status: KSAAttemptStatus
    version: str
    started_at: datetime


class KSAAssessmentAnswersUpsertRequest(BaseModel):
    answers: dict[str, object] = Field(default_factory=dict)


class KSAAssessmentAttemptRead(BaseModel):
    attempt_id: str
    status: KSAAttemptStatus
    version: str
    started_at: datetime
    completed_at: datetime | None = None
    answers: dict[str, object] = Field(default_factory=dict)
    result: dict[str, object] | None = None

