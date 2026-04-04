from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LearningLessonRead(BaseModel):
    id: str
    module_id: str
    order_index: int
    title: str
    description: str = ""
    objectives: list[str] = Field(default_factory=list)
    teaching_notes: str = ""
    created_at: datetime
    updated_at: datetime


class LearningModuleRead(BaseModel):
    id: str
    learning_path_id: str
    order_index: int
    title: str
    description: str = ""
    learning_objectives: list[str] = Field(default_factory=list)
    lessons: list[LearningLessonRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class LearningPathRead(BaseModel):
    id: str
    scope: str
    owner_user_id: int | None = None
    title: str
    description: str = ""
    subject: str = ""
    difficulty_level: str = ""
    estimated_duration_minutes: int | None = None
    status: str
    allowed_file_ids: list[int] = Field(default_factory=list)
    allowed_tags: list[str] = Field(default_factory=list)
    modules: list[LearningModuleRead] = Field(default_factory=list)
    can_edit: bool = False
    can_delete: bool = False
    created_at: datetime
    updated_at: datetime


class LearningPathListResponse(BaseModel):
    paths: list[LearningPathRead] = Field(default_factory=list)


class LearningPathCreateRequest(BaseModel):
    scope: str = Field(default="user", pattern="^(global|user)$")
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=12000)
    subject: str = Field(default="", max_length=255)
    difficulty_level: str = Field(default="", max_length=64)
    estimated_duration_minutes: int | None = Field(default=None, ge=1, le=100000)
    status: str = Field(default="draft", pattern="^(draft|published|archived)$")
    allowed_file_ids: list[int] = Field(default_factory=list)
    allowed_tags: list[str] = Field(default_factory=list)


class LearningPathUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=12000)
    subject: str | None = Field(default=None, max_length=255)
    difficulty_level: str | None = Field(default=None, max_length=64)
    estimated_duration_minutes: int | None = Field(default=None, ge=1, le=100000)
    status: str | None = Field(default=None, pattern="^(draft|published|archived)$")
    allowed_file_ids: list[int] | None = None
    allowed_tags: list[str] | None = None


class LearningModuleCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=12000)
    learning_objectives: list[str] = Field(default_factory=list)


class LearningModuleUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=12000)
    learning_objectives: list[str] | None = None


class LearningLessonCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=12000)
    objectives: list[str] = Field(default_factory=list)
    teaching_notes: str = Field(default="", max_length=12000)


class LearningLessonUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=12000)
    objectives: list[str] | None = None
    teaching_notes: str | None = Field(default=None, max_length=12000)


class LearningReorderItem(BaseModel):
    id: str = Field(min_length=1)
    order_index: int = Field(ge=0)


class LearningModuleReorderRequest(BaseModel):
    modules: list[LearningReorderItem] = Field(default_factory=list)


class LearningLessonReorderRequest(BaseModel):
    lessons: list[LearningReorderItem] = Field(default_factory=list)
