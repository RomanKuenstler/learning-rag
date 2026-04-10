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
    topic_source: Literal["manual", "auto_good", "auto_bad", "user_core", "user_variant", "llm_stretch", "llm_growth"] | None = None
    choices: list[str] = Field(default_factory=list)
    correct_answer: str | None = None
    distractors: list[str] = Field(default_factory=list)


class KSADrillTopicClassificationRead(BaseModel):
    primary_type: Literal["K", "S", "A"]
    secondary_type: Literal["K", "S", "A"] | None = None
    type_combo: Literal["K", "S", "A", "K+S", "K+A", "S+A", "K+S+A"]
    big_map_group: Literal["Knowledge", "Skills", "Abilities"]
    big_map_subdomain: str = Field(min_length=1)
    detailed_topic: str = Field(min_length=1)
    user_explanation: str = Field(min_length=1)


class KSADrillRoundRead(BaseModel):
    round_number: Literal[1, 2, 3, 4]
    origin: Literal["user_core", "user_variant", "llm_stretch", "llm_growth"]
    type_combo: str = Field(min_length=1)
    big_map_group: Literal["Knowledge", "Skills", "Abilities"]
    big_map_subdomain: str = Field(min_length=1)
    detailed_topic: str = Field(min_length=1)
    rationale: str = ""
    questions: list[KSADrillQuestionRead] = Field(default_factory=list)


class KSADrillAttemptRead(BaseModel):
    attempt_id: str
    status: KSADrillAttemptStatus
    version: str
    selected_topic_keys: list[str] = Field(default_factory=list)
    question_set: list[KSADrillQuestionRead] = Field(default_factory=list)
    source_topic_input: str | None = None
    topic_classification: KSADrillTopicClassificationRead | None = None
    rounds: list[KSADrillRoundRead] = Field(default_factory=list)
    started_at: datetime
    completed_at: datetime | None = None
    answers: dict[str, object] = Field(default_factory=dict)
    result: dict[str, object] | None = None


class KSADrillAttemptStartRequest(BaseModel):
    source_topic_input: str = Field(min_length=1, max_length=2000)
    topic_classification: KSADrillTopicClassificationRead


class KSADrillAttemptStartResponse(BaseModel):
    attempt_id: str
    status: KSADrillAttemptStatus
    version: str
    selected_topic_keys: list[str] = Field(default_factory=list)
    question_set: list[KSADrillQuestionRead] = Field(default_factory=list)
    source_topic_input: str | None = None
    topic_classification: KSADrillTopicClassificationRead | None = None
    rounds: list[KSADrillRoundRead] = Field(default_factory=list)
    started_at: datetime


class KSADrillTopicClassifyRequest(BaseModel):
    source_topic_input: str = Field(min_length=1, max_length=2000)


class KSADrillTopicClassifyResponse(BaseModel):
    source_topic_input: str
    classification: KSADrillTopicClassificationRead


class KSADrillAnswersUpsertRequest(BaseModel):
    answers: dict[str, object] = Field(default_factory=dict)


class KSADrillAttemptsRead(BaseModel):
    attempts: list[KSADrillAttemptRead] = Field(default_factory=list)
