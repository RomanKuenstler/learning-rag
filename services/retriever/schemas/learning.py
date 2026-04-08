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


class CourseListItemRead(BaseModel):
    id: str
    title: str
    description: str = ""
    scope: str
    owner_user_id: int | None = None
    owner_username: str | None = None
    owner_displayname: str | None = None
    status: str
    subject: str = ""
    difficulty_level: str = ""
    module_count: int = 0
    lesson_count: int = 0
    updated_at: datetime
    created_at: datetime


class CourseListResponse(BaseModel):
    courses: list[CourseListItemRead] = Field(default_factory=list)
    total: int = 0


class CourseImportFileResultRead(BaseModel):
    file_name: str
    scope: str
    success: bool
    course_id: str | None = None
    title: str | None = None
    error: str | None = None


class CourseImportResponse(BaseModel):
    imported_count: int = 0
    failed_count: int = 0
    results: list[CourseImportFileResultRead] = Field(default_factory=list)


class CourseTemplateResponse(BaseModel):
    file_name: str
    template: dict[str, object]


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
