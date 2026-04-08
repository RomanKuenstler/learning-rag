from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


KSADrillAttemptStatus = Literal["in_progress", "completed"]


class KSADrillTopicRead(BaseModel):
    key: str
    group: Literal["knowledge", "skills", "abilities"]
    name: str
    subtopics: list[str] = Field(default_factory=list)
    archetype_subtopics: list[str] = Field(default_factory=list)


class KSADrillTopicsRead(BaseModel):
    topics: list[KSADrillTopicRead] = Field(default_factory=list)


class KSADrillQuestionRead(BaseModel):
    id: str
    topic_key: str
    topic_name: str
    topic_group: Literal["knowledge", "skills", "abilities"]
    block_index: int
    block_label: str
    question_index: int
    kind: Literal["recalibration", "threshold", "sidestep", "stress_test"]
    archetype: Literal["reverse_definition", "spot_the_flaw", "analogy_match", "power_sprint"]
    focus_subtopic: str
    related_subtopic: str | None = None
    prompt: str
    time_limit_seconds: int | None = None
    topic_source: Literal["manual", "auto_good", "auto_bad"] | None = None


class KSADrillAttemptRead(BaseModel):
    attempt_id: str
    status: KSADrillAttemptStatus
    version: str
    selected_topic_keys: list[str] = Field(default_factory=list)
    question_set: list[KSADrillQuestionRead] = Field(default_factory=list)
    started_at: datetime
    completed_at: datetime | None = None
    answers: dict[str, object] = Field(default_factory=dict)
    result: dict[str, object] | None = None


class KSADrillAttemptStartRequest(BaseModel):
    topic_keys: list[str] = Field(default_factory=list, min_length=1, max_length=3)


class KSADrillAttemptStartResponse(BaseModel):
    attempt_id: str
    status: KSADrillAttemptStatus
    version: str
    selected_topic_keys: list[str] = Field(default_factory=list)
    question_set: list[KSADrillQuestionRead] = Field(default_factory=list)
    started_at: datetime


class KSADrillAnswersUpsertRequest(BaseModel):
    answers: dict[str, object] = Field(default_factory=dict)


class KSADrillAttemptsRead(BaseModel):
    attempts: list[KSADrillAttemptRead] = Field(default_factory=list)
