from __future__ import annotations

from datetime import datetime
from typing import Literal

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


class SkilltreeNodePrerequisitesRead(BaseModel):
    requires_all: list[str] = Field(default_factory=list)
    requires_any: list[str] = Field(default_factory=list)
    recommended: list[str] = Field(default_factory=list)


class SkilltreeNodeKsaRead(BaseModel):
    dimension: Literal["K", "S", "A"]
    topic: str
    subtopic: str | None = None
    start_level: int | None = None
    target_level: int | None = None
    contribution_weight: float | None = None
    unlocks_assessment_check: bool = False
    recommends_assessment_check: bool = False


class SkilltreeNodeUnlocksRead(BaseModel):
    node_ids: list[str] = Field(default_factory=list)
    branch_ids: list[str] = Field(default_factory=list)
    recommended_next_node_ids: list[str] = Field(default_factory=list)


class SkilltreeNodeRewardsRead(BaseModel):
    estimated_ksa_gain: dict[str, float] = Field(default_factory=dict)
    effort_score: float | None = None
    reward_tags: list[str] = Field(default_factory=list)


class SkilltreeNodeLayoutRead(BaseModel):
    x: float = 0
    y: float = 0


class SkilltreeNodeRead(BaseModel):
    id: str
    title: str
    description: str = ""
    type: Literal["learning_unit", "practice", "quiz", "checkpoint", "review", "milestone", "capstone", "unlock_gate", "assessment_hook"]
    chapter_id: str | None = None
    branch_id: str | None = None
    required: bool = True
    prerequisites: SkilltreeNodePrerequisitesRead = Field(default_factory=SkilltreeNodePrerequisitesRead)
    completion_mode: Literal[
        "lesson_complete",
        "manual",
        "practice_complete",
        "quiz_pass",
        "checkpoint_pass",
        "review_complete",
        "assessment_threshold",
        "gate_unlock",
    ] = "lesson_complete"
    estimated_duration_minutes: int | None = None
    layout: SkilltreeNodeLayoutRead = Field(default_factory=SkilltreeNodeLayoutRead)
    metadata: dict[str, object] = Field(default_factory=dict)
    display: dict[str, object] = Field(default_factory=dict)
    ksa: list[SkilltreeNodeKsaRead] = Field(default_factory=list)
    unlocks: SkilltreeNodeUnlocksRead = Field(default_factory=SkilltreeNodeUnlocksRead)
    rewards: SkilltreeNodeRewardsRead = Field(default_factory=SkilltreeNodeRewardsRead)


class SkilltreeEdgeRead(BaseModel):
    from_node_id: str
    to_node_id: str
    relationship: Literal["requires_all", "requires_any", "recommended", "optional"] = "requires_all"


class SkilltreeChapterRead(BaseModel):
    id: str
    title: str
    description: str = ""
    order_index: int = 0
    metadata: dict[str, object] = Field(default_factory=dict)


class SkilltreeBranchRead(BaseModel):
    id: str
    title: str
    description: str = ""
    required: bool = True
    metadata: dict[str, object] = Field(default_factory=dict)


class SkilltreeChapterProgressRead(BaseModel):
    chapter_id: str
    title: str
    required_total: int
    required_completed: int
    optional_total: int
    optional_completed: int
    is_complete: bool


class SkilltreeCompletionSummaryRead(BaseModel):
    required_total: int
    required_completed: int
    optional_total: int
    optional_completed: int
    is_complete: bool


class SkilltreeNodeRuntimeRead(BaseModel):
    blocked_by_all: list[str] = Field(default_factory=list)
    blocked_by_any: list[str] = Field(default_factory=list)
    is_entry: bool = False
    is_parallel_available: bool = False
    awaiting_checkpoint: bool = False
    capstone_locked: bool = False
    optional_branch: bool = False
    completion_allowed: bool = False


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
    schema_version: int = 1
    allowed_file_ids: list[int] = Field(default_factory=list)
    allowed_tags: list[str] = Field(default_factory=list)
    chapters: list[SkilltreeChapterRead] = Field(default_factory=list)
    branches: list[SkilltreeBranchRead] = Field(default_factory=list)
    nodes: list[SkilltreeNodeRead] = Field(default_factory=list)
    edges: list[SkilltreeEdgeRead] = Field(default_factory=list)
    entry_node_ids: list[str] = Field(default_factory=list)
    completion_rules: dict[str, object] = Field(default_factory=dict)
    visual_layout: dict[str, object] = Field(default_factory=dict)
    metadata: dict[str, object] = Field(default_factory=dict)
    node_progress: dict[str, str] = Field(default_factory=dict)
    node_runtime: dict[str, SkilltreeNodeRuntimeRead] = Field(default_factory=dict)
    chapter_progress: list[SkilltreeChapterProgressRead] = Field(default_factory=list)
    completion_summary: SkilltreeCompletionSummaryRead | None = None
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
    schema_version: int = 1
    chapter_count: int = 0
    node_count: int = 0
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


class LearningNodeProgressUpdateRequest(BaseModel):
    status: Literal[
        "in_progress",
        "completed",
        "mastered",
        "optional_skipped",
        "failed_needs_retry",
        "reset",
    ]
    evidence: dict[str, object] = Field(default_factory=dict)


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
