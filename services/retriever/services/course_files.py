from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, model_validator

COURSE_NODE_TYPES = {
    "learning_unit",
    "practice",
    "quiz",
    "checkpoint",
    "review",
    "milestone",
    "capstone",
    "unlock_gate",
    "assessment_hook",
}
EDGE_RELATIONSHIPS = {"requires_all", "requires_any", "recommended", "optional"}
COMPLETION_MODES = {
    "lesson_complete",
    "manual",
    "practice_complete",
    "quiz_pass",
    "checkpoint_pass",
    "review_complete",
    "assessment_threshold",
    "gate_unlock",
}


class CourseLessonDefinition(BaseModel):
    id: str | None = None
    order_index: int = Field(default=0, ge=0)
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=12000)
    objectives: list[str] = Field(default_factory=list)
    teaching_notes: str = Field(default="", max_length=12000)


class CourseModuleDefinition(BaseModel):
    id: str | None = None
    order_index: int = Field(default=0, ge=0)
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=12000)
    learning_objectives: list[str] = Field(default_factory=list)
    lessons: list[CourseLessonDefinition] = Field(default_factory=list)


class LegacyCourseDefinition(BaseModel):
    schema_version: int = Field(default=1, ge=1)
    id: str | None = Field(default=None, min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=12000)
    scope: str = Field(pattern="^(global|user)$")
    owner_user_id: int | None = None
    subject: str = Field(default="", max_length=255)
    difficulty_level: str = Field(default="", max_length=64)
    estimated_duration_minutes: int | None = Field(default=None, ge=1, le=100000)
    status: str = Field(default="draft", pattern="^(draft|published|archived)$")
    allowed_file_ids: list[int] = Field(default_factory=list)
    allowed_tags: list[str] = Field(default_factory=list)
    modules: list[CourseModuleDefinition] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_scope_owner(self) -> "LegacyCourseDefinition":
        if self.scope == "user" and self.owner_user_id is None:
            raise ValueError("owner_user_id is required for user-scoped courses")
        return self


class CourseChapterDefinition(BaseModel):
    id: str
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=12000)
    order_index: int = Field(default=0, ge=0)
    metadata: dict[str, object] = Field(default_factory=dict)


class CourseBranchDefinition(BaseModel):
    id: str
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=12000)
    required: bool = True
    metadata: dict[str, object] = Field(default_factory=dict)


class CourseNodePrerequisites(BaseModel):
    requires_all: list[str] = Field(default_factory=list)
    requires_any: list[str] = Field(default_factory=list)
    recommended: list[str] = Field(default_factory=list)


class CourseNodeKsaMetadata(BaseModel):
    dimension: Literal["K", "S", "A"]
    topic: str = Field(min_length=1, max_length=255)
    subtopic: str | None = Field(default=None, max_length=255)
    start_level: int | None = Field(default=None, ge=1, le=5)
    target_level: int | None = Field(default=None, ge=1, le=5)
    contribution_weight: float | None = Field(default=None, gt=0, le=1)
    unlocks_assessment_check: bool = False
    recommends_assessment_check: bool = False


class CourseNodeUnlocksMetadata(BaseModel):
    node_ids: list[str] = Field(default_factory=list)
    branch_ids: list[str] = Field(default_factory=list)
    recommended_next_node_ids: list[str] = Field(default_factory=list)


class CourseNodeRewardMetadata(BaseModel):
    estimated_ksa_gain: dict[str, float] = Field(default_factory=dict)
    effort_score: float | None = Field(default=None, ge=0)
    reward_tags: list[str] = Field(default_factory=list)


class CourseNodeRetrospectiveHooks(BaseModel):
    retrospective_after: bool = False
    review_recommended: bool = False
    recap_checkpoint_available: bool = False


class CourseNodeKsaHooks(BaseModel):
    mini_assessment_available: bool = False
    recommended_reassessment_topics: list[str] = Field(default_factory=list)
    unlocks_deeper_refinement: bool = False


class CourseNodeRemediationMetadata(BaseModel):
    is_remediation_node: bool = False
    recommended_if_failed_node_ids: list[str] = Field(default_factory=list)
    supports_review_for_node_ids: list[str] = Field(default_factory=list)


class CourseNodeKsaThresholdRule(BaseModel):
    dimension: Literal["K", "S", "A"]
    topic: str = Field(min_length=1, max_length=255)
    min_level: int = Field(ge=1, le=5)


class CourseNodeAdaptiveUnlockMetadata(BaseModel):
    ksa_thresholds: list[CourseNodeKsaThresholdRule] = Field(default_factory=list)
    requires_branch_completion_ids: list[str] = Field(default_factory=list)
    requires_checkpoint_node_ids: list[str] = Field(default_factory=list)
    requires_review_recommended: bool = False
    recommended_only: bool = False


class CourseNodeLayout(BaseModel):
    x: float = 0
    y: float = 0


class CourseNodeDefinition(BaseModel):
    id: str
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=12000)
    type: Literal[
        "learning_unit",
        "practice",
        "quiz",
        "checkpoint",
        "review",
        "milestone",
        "capstone",
        "unlock_gate",
        "assessment_hook",
    ] = "learning_unit"
    chapter_id: str | None = Field(default=None)
    branch_id: str | None = Field(default=None)
    required: bool = True
    prerequisites: CourseNodePrerequisites = Field(default_factory=CourseNodePrerequisites)
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
    estimated_duration_minutes: int | None = Field(default=None, ge=1, le=100000)
    layout: CourseNodeLayout = Field(default_factory=CourseNodeLayout)
    metadata: dict[str, object] = Field(default_factory=dict)
    display: dict[str, object] = Field(default_factory=dict)
    ksa: list[CourseNodeKsaMetadata] = Field(default_factory=list)
    unlocks: CourseNodeUnlocksMetadata = Field(default_factory=CourseNodeUnlocksMetadata)
    rewards: CourseNodeRewardMetadata = Field(default_factory=CourseNodeRewardMetadata)
    retrospective_hooks: CourseNodeRetrospectiveHooks = Field(default_factory=CourseNodeRetrospectiveHooks)
    ksa_hooks: CourseNodeKsaHooks = Field(default_factory=CourseNodeKsaHooks)
    remediation: CourseNodeRemediationMetadata = Field(default_factory=CourseNodeRemediationMetadata)
    adaptive_unlock: CourseNodeAdaptiveUnlockMetadata = Field(default_factory=CourseNodeAdaptiveUnlockMetadata)


class CourseEdgeDefinition(BaseModel):
    from_node_id: str
    to_node_id: str
    relationship: Literal["requires_all", "requires_any", "recommended", "optional"] = "requires_all"


class CourseDefinition(BaseModel):
    schema_version: Literal[2] = 2
    source_schema_version: int = 2
    id: str | None = Field(default=None, min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=12000)
    scope: str = Field(pattern="^(global|user)$")
    owner_user_id: int | None = None
    subject: str = Field(default="", max_length=255)
    difficulty_level: str = Field(default="", max_length=64)
    estimated_duration_minutes: int | None = Field(default=None, ge=1, le=100000)
    status: str = Field(default="draft", pattern="^(draft|published|archived)$")
    allowed_file_ids: list[int] = Field(default_factory=list)
    allowed_tags: list[str] = Field(default_factory=list)
    chapters: list[CourseChapterDefinition] = Field(default_factory=list)
    branches: list[CourseBranchDefinition] = Field(default_factory=list)
    nodes: list[CourseNodeDefinition] = Field(default_factory=list)
    edges: list[CourseEdgeDefinition] = Field(default_factory=list)
    entry_node_ids: list[str] = Field(default_factory=list)
    completion_rules: dict[str, object] = Field(default_factory=lambda: {"required_completion": "all_required_nodes"})
    visual_layout: dict[str, object] = Field(default_factory=dict)
    metadata: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_scope_owner(self) -> "CourseDefinition":
        if self.scope == "user" and self.owner_user_id is None:
            raise ValueError("owner_user_id is required for user-scoped courses")

        node_ids = [node.id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("nodes must have unique ids")
        chapter_ids = [chapter.id for chapter in self.chapters]
        if len(chapter_ids) != len(set(chapter_ids)):
            raise ValueError("chapters must have unique ids")
        branch_ids = [branch.id for branch in self.branches]
        if len(branch_ids) != len(set(branch_ids)):
            raise ValueError("branches must have unique ids")

        node_id_set = set(node_ids)
        chapter_id_set = set(chapter_ids)
        branch_id_set = set(branch_ids)
        for node in self.nodes:
            if node.chapter_id and node.chapter_id not in chapter_id_set:
                raise ValueError(f"node '{node.id}' references unknown chapter_id '{node.chapter_id}'")
            if node.branch_id and node.branch_id not in branch_id_set:
                raise ValueError(f"node '{node.id}' references unknown branch_id '{node.branch_id}'")
            for required_id in node.prerequisites.requires_all + node.prerequisites.requires_any + node.prerequisites.recommended:
                if required_id not in node_id_set:
                    raise ValueError(f"node '{node.id}' references unknown prerequisite node '{required_id}'")
                if required_id == node.id:
                    raise ValueError(f"node '{node.id}' cannot depend on itself")
            for unlocked_node_id in node.unlocks.node_ids + node.unlocks.recommended_next_node_ids:
                if unlocked_node_id not in node_id_set:
                    raise ValueError(f"node '{node.id}' references unknown unlock/recommend node '{unlocked_node_id}'")
            for unlocked_branch_id in node.unlocks.branch_ids:
                if unlocked_branch_id not in branch_id_set:
                    raise ValueError(f"node '{node.id}' references unknown unlock branch '{unlocked_branch_id}'")
            for failed_node_id in node.remediation.recommended_if_failed_node_ids + node.remediation.supports_review_for_node_ids:
                if failed_node_id not in node_id_set:
                    raise ValueError(f"node '{node.id}' references unknown remediation node '{failed_node_id}'")
            for required_branch_id in node.adaptive_unlock.requires_branch_completion_ids:
                if required_branch_id not in branch_id_set:
                    raise ValueError(f"node '{node.id}' references unknown adaptive branch '{required_branch_id}'")
            for required_checkpoint_id in node.adaptive_unlock.requires_checkpoint_node_ids:
                if required_checkpoint_id not in node_id_set:
                    raise ValueError(f"node '{node.id}' references unknown adaptive checkpoint node '{required_checkpoint_id}'")

        for edge in self.edges:
            if edge.from_node_id not in node_id_set:
                raise ValueError(f"edge has unknown from_node_id '{edge.from_node_id}'")
            if edge.to_node_id not in node_id_set:
                raise ValueError(f"edge has unknown to_node_id '{edge.to_node_id}'")
            if edge.from_node_id == edge.to_node_id:
                raise ValueError(f"edge '{edge.from_node_id}' -> '{edge.to_node_id}' cannot be a self-loop")

        for entry_node_id in self.entry_node_ids:
            if entry_node_id not in node_id_set:
                raise ValueError(f"entry node '{entry_node_id}' does not exist")

        self._assert_hard_dependency_acyclic()
        return self

    def _assert_hard_dependency_acyclic(self) -> None:
        adjacency: dict[str, set[str]] = {node.id: set() for node in self.nodes}
        for edge in self.edges:
            if edge.relationship in {"requires_all", "requires_any"}:
                adjacency.setdefault(edge.from_node_id, set()).add(edge.to_node_id)

        state: dict[str, int] = {node_id: 0 for node_id in adjacency}

        def dfs(node_id: str) -> bool:
            state[node_id] = 1
            for child_id in adjacency.get(node_id, set()):
                child_state = state.get(child_id, 0)
                if child_state == 1:
                    return True
                if child_state == 0 and dfs(child_id):
                    return True
            state[node_id] = 2
            return False

        for candidate in adjacency:
            if state[candidate] == 0 and dfs(candidate):
                raise ValueError("hard dependencies must be acyclic")


@dataclass(slots=True)
class CourseFileValidationError:
    file_name: str
    message: str


class CourseFileParser:
    TEMPLATE_FILE_NAME = "path-template.json"

    def parse_bytes(self, file_name: str, content: bytes) -> CourseDefinition:
        try:
            payload = json.loads(content.decode("utf-8"))
        except UnicodeDecodeError as error:
            raise ValueError(f"{file_name}: file must be UTF-8 encoded") from error
        except json.JSONDecodeError as error:
            raise ValueError(f"{file_name}: invalid JSON ({error.msg})") from error
        return self.parse_payload(file_name, payload)

    def parse_file(self, path: Path) -> CourseDefinition:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"{path.name}: invalid JSON ({error.msg})") from error
        return self.parse_payload(path.name, payload)

    def parse_payload(self, file_name: str, payload: object) -> CourseDefinition:
        if not isinstance(payload, dict):
            raise ValueError(f"{file_name}: root JSON value must be an object")

        schema_version = int(payload.get("schema_version", 1))
        normalized_payload: dict[str, object]
        source_schema_version = schema_version

        try:
            if schema_version == 2:
                normalized_payload = dict(payload)
            elif schema_version == 1:
                legacy = LegacyCourseDefinition.model_validate(payload)
                normalized_payload = self._convert_legacy_payload(legacy)
            else:
                raise ValueError(f"{file_name}: unsupported schema_version '{schema_version}'")

            normalized_payload["source_schema_version"] = source_schema_version
            parsed = CourseDefinition.model_validate(normalized_payload)
        except ValidationError as error:
            first = error.errors()[0]
            location = ".".join(str(item) for item in first.get("loc", []))
            msg = str(first.get("msg", "invalid payload"))
            where = f" ({location})" if location else ""
            raise ValueError(f"{file_name}: {msg}{where}") from error

        return self._normalize_course_definition(parsed)

    def safe_file_name(self, course_id: str, title: str) -> str:
        _ = title
        return f"{course_id}.json"

    def template_payload(self) -> dict[str, object]:
        return {
            "schema_version": 2,
            "title": "Course Example Template (All Node Types)",
            "description": "Comprehensive draft example course containing all supported node types and representative value combinations.",
            "scope": "user",
            "owner_user_id": 1,
            "subject": "DevOps",
            "difficulty_level": "intermediate",
            "estimated_duration_minutes": 300,
            "status": "draft",
            "allowed_file_ids": [],
            "allowed_tags": ["template", "example", "devops"],
            "modules": [
                {
                    "id": "module-foundations",
                    "order_index": 0,
                    "title": "Module 1: Foundations",
                    "description": "Core concepts and base setup.",
                    "learning_objectives": ["Understand fundamentals", "Set up workspace"],
                    "lessons": [
                        {"id": "lesson-foundations-1", "order_index": 0, "title": "Core concepts", "description": "Baseline understanding.", "objectives": ["Terminology"], "teaching_notes": ""},
                        {"id": "lesson-foundations-2", "order_index": 1, "title": "Hands-on setup", "description": "Prepare tooling.", "objectives": ["Local setup"], "teaching_notes": ""},
                    ],
                },
                {
                    "id": "module-delivery",
                    "order_index": 1,
                    "title": "Module 2: Delivery",
                    "description": "Build and release practices.",
                    "learning_objectives": ["Delivery workflow", "Quality gates"],
                    "lessons": [
                        {"id": "lesson-delivery-1", "order_index": 0, "title": "Pipelines", "description": "Delivery pipelines.", "objectives": ["CI/CD"], "teaching_notes": ""},
                    ],
                },
                {
                    "id": "module-operations",
                    "order_index": 2,
                    "title": "Module 3: Operations",
                    "description": "Operate and improve systems.",
                    "learning_objectives": ["Monitoring", "Reliability", "Optimization"],
                    "lessons": [
                        {"id": "lesson-ops-1", "order_index": 0, "title": "Observability", "description": "Metrics and alerting.", "objectives": ["Monitoring"], "teaching_notes": ""},
                    ],
                },
            ],
            "chapters": [
                {"id": "chapter-core", "order_index": 0, "title": "Core", "description": "Core delivery knowledge."},
                {"id": "chapter-advanced", "order_index": 1, "title": "Advanced", "description": "Advanced integration and capstone."},
            ],
            "branches": [
                {"id": "branch-main", "title": "Main Route", "description": "Primary required route.", "required": True},
                {"id": "branch-accelerator", "title": "Accelerator Route", "description": "Optional fast-track route.", "required": False},
            ],
            "nodes": [
                {
                    "id": "node-learning-unit-1",
                    "title": "Container Basics",
                    "description": "Learn containerization principles.",
                    "type": "learning_unit",
                    "chapter_id": "chapter-core",
                    "branch_id": "branch-main",
                    "required": True,
                    "completion_mode": "lesson_complete",
                    "estimated_duration_minutes": 25,
                    "layout": {"x": 120, "y": 130},
                    "display": {"route_name": "Main"},
                    "prerequisites": {"requires_all": [], "requires_any": [], "recommended": []},
                    "ksa": [{"dimension": "K", "topic": "Information Technology", "subtopic": "Container Concepts", "start_level": 1, "target_level": 2, "contribution_weight": 0.4, "recommends_assessment_check": True}],
                    "unlocks": {"node_ids": ["node-practice-1"], "branch_ids": [], "recommended_next_node_ids": ["node-review-1"]},
                    "rewards": {"estimated_ksa_gain": {"K.Information Technology.Container Concepts": 0.2}, "effort_score": 15, "reward_tags": ["foundation"]},
                    "retrospective_hooks": {"retrospective_after": False, "review_recommended": False, "recap_checkpoint_available": False},
                    "ksa_hooks": {"mini_assessment_available": False, "recommended_reassessment_topics": [], "unlocks_deeper_refinement": False},
                    "remediation": {"is_remediation_node": False, "recommended_if_failed_node_ids": [], "supports_review_for_node_ids": []},
                    "adaptive_unlock": {"ksa_thresholds": [], "requires_branch_completion_ids": [], "requires_checkpoint_node_ids": [], "requires_review_recommended": False, "recommended_only": False},
                },
                {
                    "id": "node-practice-1",
                    "title": "Practice Lab",
                    "description": "Apply basics in a guided lab.",
                    "type": "practice",
                    "chapter_id": "chapter-core",
                    "branch_id": "branch-main",
                    "required": True,
                    "completion_mode": "practice_complete",
                    "estimated_duration_minutes": 35,
                    "layout": {"x": 320, "y": 130},
                    "display": {"route_name": "Main"},
                    "prerequisites": {"requires_all": ["node-learning-unit-1"], "requires_any": [], "recommended": []},
                    "ksa": [{"dimension": "S", "topic": "Operational Skills", "subtopic": "Technical Troubleshooting", "start_level": 1, "target_level": 3, "contribution_weight": 0.6}],
                    "unlocks": {"node_ids": ["node-quiz-1"], "branch_ids": ["branch-accelerator"], "recommended_next_node_ids": []},
                    "rewards": {"estimated_ksa_gain": {"S.Operational Skills.Technical Troubleshooting": 0.3}, "effort_score": 24, "reward_tags": ["hands_on"]},
                    "retrospective_hooks": {"retrospective_after": True, "review_recommended": False, "recap_checkpoint_available": False},
                    "ksa_hooks": {"mini_assessment_available": True, "recommended_reassessment_topics": ["S.Operational Skills.Technical Troubleshooting"], "unlocks_deeper_refinement": False},
                    "remediation": {"is_remediation_node": False, "recommended_if_failed_node_ids": [], "supports_review_for_node_ids": []},
                    "adaptive_unlock": {"ksa_thresholds": [{"dimension": "S", "topic": "Operational Skills", "min_level": 2}], "requires_branch_completion_ids": [], "requires_checkpoint_node_ids": [], "requires_review_recommended": False, "recommended_only": False},
                },
                {
                    "id": "node-quiz-1",
                    "title": "Knowledge Check Quiz",
                    "description": "Quiz covering core concepts.",
                    "type": "quiz",
                    "chapter_id": "chapter-core",
                    "branch_id": "branch-main",
                    "required": True,
                    "completion_mode": "quiz_pass",
                    "estimated_duration_minutes": 20,
                    "layout": {"x": 520, "y": 130},
                    "display": {"route_name": "Main"},
                    "prerequisites": {"requires_all": ["node-practice-1"], "requires_any": [], "recommended": []},
                    "ksa": [{"dimension": "K", "topic": "Information Technology", "subtopic": "Cloud Architecture", "start_level": 2, "target_level": 3}],
                    "unlocks": {"node_ids": ["node-checkpoint-1"], "branch_ids": [], "recommended_next_node_ids": []},
                    "rewards": {"estimated_ksa_gain": {"K.Information Technology.Cloud Architecture": 0.25}, "effort_score": 18, "reward_tags": ["quiz"]},
                    "retrospective_hooks": {"retrospective_after": False, "review_recommended": True, "recap_checkpoint_available": False},
                    "ksa_hooks": {"mini_assessment_available": True, "recommended_reassessment_topics": ["K.Information Technology.Cloud Architecture"], "unlocks_deeper_refinement": True},
                    "remediation": {"is_remediation_node": False, "recommended_if_failed_node_ids": ["node-practice-1"], "supports_review_for_node_ids": []},
                    "adaptive_unlock": {"ksa_thresholds": [], "requires_branch_completion_ids": [], "requires_checkpoint_node_ids": [], "requires_review_recommended": False, "recommended_only": False},
                },
                {
                    "id": "node-checkpoint-1",
                    "title": "Checkpoint Validation",
                    "description": "Combined quiz/practice checkpoint.",
                    "type": "checkpoint",
                    "chapter_id": "chapter-core",
                    "branch_id": "branch-main",
                    "required": True,
                    "completion_mode": "checkpoint_pass",
                    "estimated_duration_minutes": 30,
                    "layout": {"x": 720, "y": 130},
                    "display": {"route_name": "Main"},
                    "prerequisites": {"requires_all": ["node-quiz-1"], "requires_any": [], "recommended": []},
                    "ksa": [{"dimension": "A", "topic": "Strategic Execution", "subtopic": "Risk Mitigation Planning", "start_level": 1, "target_level": 2}],
                    "unlocks": {"node_ids": ["node-assessment-hook-1"], "branch_ids": [], "recommended_next_node_ids": ["node-review-1"]},
                    "rewards": {"estimated_ksa_gain": {"A.Strategic Execution.Risk Mitigation Planning": 0.2}, "effort_score": 22, "reward_tags": ["checkpoint"]},
                    "retrospective_hooks": {"retrospective_after": True, "review_recommended": True, "recap_checkpoint_available": True},
                    "ksa_hooks": {"mini_assessment_available": True, "recommended_reassessment_topics": ["A.Strategic Execution.Risk Mitigation Planning"], "unlocks_deeper_refinement": True},
                    "remediation": {"is_remediation_node": False, "recommended_if_failed_node_ids": ["node-practice-1"], "supports_review_for_node_ids": ["node-quiz-1"]},
                    "adaptive_unlock": {"ksa_thresholds": [], "requires_branch_completion_ids": [], "requires_checkpoint_node_ids": [], "requires_review_recommended": True, "recommended_only": False},
                },
                {
                    "id": "node-assessment-hook-1",
                    "title": "Assessment Hook",
                    "description": "Targeted adaptive KSA drill node.",
                    "type": "assessment_hook",
                    "chapter_id": "chapter-advanced",
                    "branch_id": "branch-main",
                    "required": True,
                    "completion_mode": "assessment_threshold",
                    "estimated_duration_minutes": 25,
                    "layout": {"x": 920, "y": 130},
                    "display": {"route_name": "Main"},
                    "prerequisites": {"requires_all": ["node-checkpoint-1"], "requires_any": [], "recommended": []},
                    "ksa": [{"dimension": "S", "topic": "Operational Skills", "subtopic": "Incident Response", "start_level": 2, "target_level": 4, "unlocks_assessment_check": True}],
                    "unlocks": {"node_ids": ["node-unlock-gate-1"], "branch_ids": [], "recommended_next_node_ids": []},
                    "rewards": {"estimated_ksa_gain": {"S.Operational Skills.Incident Response": 0.35}, "effort_score": 20, "reward_tags": ["assessment"]},
                    "retrospective_hooks": {"retrospective_after": False, "review_recommended": False, "recap_checkpoint_available": False},
                    "ksa_hooks": {"mini_assessment_available": True, "recommended_reassessment_topics": ["S.Operational Skills.Incident Response"], "unlocks_deeper_refinement": True},
                    "remediation": {"is_remediation_node": False, "recommended_if_failed_node_ids": ["node-checkpoint-1"], "supports_review_for_node_ids": []},
                    "adaptive_unlock": {"ksa_thresholds": [{"dimension": "S", "topic": "Operational Skills", "min_level": 3}], "requires_branch_completion_ids": [], "requires_checkpoint_node_ids": ["node-checkpoint-1"], "requires_review_recommended": False, "recommended_only": False},
                },
                {
                    "id": "node-review-1",
                    "title": "Optional Review",
                    "description": "Optional remediation and recap.",
                    "type": "review",
                    "chapter_id": "chapter-advanced",
                    "branch_id": "branch-accelerator",
                    "required": False,
                    "completion_mode": "review_complete",
                    "estimated_duration_minutes": 15,
                    "layout": {"x": 720, "y": 290},
                    "display": {"route_name": "Accelerator"},
                    "prerequisites": {"requires_all": [], "requires_any": ["node-practice-1", "node-quiz-1"], "recommended": ["node-checkpoint-1"]},
                    "ksa": [{"dimension": "K", "topic": "Information Technology", "subtopic": "Monitoring", "start_level": 2, "target_level": 3}],
                    "unlocks": {"node_ids": [], "branch_ids": [], "recommended_next_node_ids": []},
                    "rewards": {"estimated_ksa_gain": {"K.Information Technology.Monitoring": 0.1}, "effort_score": 8, "reward_tags": ["optional", "review"]},
                    "retrospective_hooks": {"retrospective_after": True, "review_recommended": True, "recap_checkpoint_available": True},
                    "ksa_hooks": {"mini_assessment_available": False, "recommended_reassessment_topics": [], "unlocks_deeper_refinement": False},
                    "remediation": {"is_remediation_node": True, "recommended_if_failed_node_ids": ["node-quiz-1"], "supports_review_for_node_ids": ["node-practice-1"]},
                    "adaptive_unlock": {"ksa_thresholds": [], "requires_branch_completion_ids": [], "requires_checkpoint_node_ids": [], "requires_review_recommended": True, "recommended_only": True},
                },
                {
                    "id": "node-unlock-gate-1",
                    "title": "Readiness Unlock Gate",
                    "description": "Non-interactive gate used for progression control.",
                    "type": "unlock_gate",
                    "chapter_id": "chapter-advanced",
                    "branch_id": "branch-main",
                    "required": True,
                    "completion_mode": "gate_unlock",
                    "estimated_duration_minutes": 5,
                    "layout": {"x": 1120, "y": 130},
                    "display": {"route_name": "Main"},
                    "prerequisites": {"requires_all": ["node-assessment-hook-1"], "requires_any": ["node-review-1"], "recommended": []},
                    "ksa": [],
                    "unlocks": {"node_ids": ["node-milestone-1"], "branch_ids": [], "recommended_next_node_ids": []},
                    "rewards": {"estimated_ksa_gain": {}, "effort_score": 2, "reward_tags": ["gate"]},
                    "retrospective_hooks": {"retrospective_after": False, "review_recommended": False, "recap_checkpoint_available": False},
                    "ksa_hooks": {"mini_assessment_available": False, "recommended_reassessment_topics": [], "unlocks_deeper_refinement": False},
                    "remediation": {"is_remediation_node": False, "recommended_if_failed_node_ids": [], "supports_review_for_node_ids": []},
                    "adaptive_unlock": {"ksa_thresholds": [{"dimension": "K", "topic": "Information Technology", "min_level": 2}], "requires_branch_completion_ids": ["branch-main"], "requires_checkpoint_node_ids": ["node-checkpoint-1"], "requires_review_recommended": False, "recommended_only": False},
                },
                {
                    "id": "node-milestone-1",
                    "title": "Milestone Marker",
                    "description": "Celebrates completion of major required segment.",
                    "type": "milestone",
                    "chapter_id": "chapter-advanced",
                    "branch_id": "branch-main",
                    "required": True,
                    "completion_mode": "manual",
                    "estimated_duration_minutes": 5,
                    "layout": {"x": 1320, "y": 130},
                    "display": {"route_name": "Main"},
                    "prerequisites": {"requires_all": ["node-unlock-gate-1"], "requires_any": [], "recommended": []},
                    "ksa": [],
                    "unlocks": {"node_ids": ["node-capstone-1"], "branch_ids": [], "recommended_next_node_ids": ["node-practice-optional-1"]},
                    "rewards": {"estimated_ksa_gain": {}, "effort_score": 3, "reward_tags": ["milestone"]},
                    "retrospective_hooks": {"retrospective_after": True, "review_recommended": False, "recap_checkpoint_available": True},
                    "ksa_hooks": {"mini_assessment_available": False, "recommended_reassessment_topics": [], "unlocks_deeper_refinement": False},
                    "remediation": {"is_remediation_node": False, "recommended_if_failed_node_ids": [], "supports_review_for_node_ids": []},
                    "adaptive_unlock": {"ksa_thresholds": [], "requires_branch_completion_ids": ["branch-main"], "requires_checkpoint_node_ids": [], "requires_review_recommended": False, "recommended_only": False},
                },
                {
                    "id": "node-practice-optional-1",
                    "title": "Optional Accelerator Practice",
                    "description": "Optional external-solving practice in accelerator route.",
                    "type": "practice",
                    "chapter_id": "chapter-advanced",
                    "branch_id": "branch-accelerator",
                    "required": False,
                    "completion_mode": "practice_complete",
                    "estimated_duration_minutes": 20,
                    "layout": {"x": 1320, "y": 300},
                    "display": {"route_name": "Accelerator"},
                    "prerequisites": {"requires_all": [], "requires_any": ["node-review-1", "node-milestone-1"], "recommended": []},
                    "ksa": [{"dimension": "A", "topic": "Strategic Execution", "subtopic": "Continuous Improvement", "start_level": 2, "target_level": 3}],
                    "unlocks": {"node_ids": ["node-capstone-1"], "branch_ids": [], "recommended_next_node_ids": []},
                    "rewards": {"estimated_ksa_gain": {"A.Strategic Execution.Continuous Improvement": 0.15}, "effort_score": 12, "reward_tags": ["optional", "accelerator"]},
                    "retrospective_hooks": {"retrospective_after": False, "review_recommended": False, "recap_checkpoint_available": False},
                    "ksa_hooks": {"mini_assessment_available": False, "recommended_reassessment_topics": [], "unlocks_deeper_refinement": False},
                    "remediation": {"is_remediation_node": False, "recommended_if_failed_node_ids": [], "supports_review_for_node_ids": []},
                    "adaptive_unlock": {"ksa_thresholds": [], "requires_branch_completion_ids": ["branch-accelerator"], "requires_checkpoint_node_ids": [], "requires_review_recommended": False, "recommended_only": True},
                },
                {
                    "id": "node-capstone-1",
                    "title": "Final Capstone",
                    "description": "Summative combined capstone for full route completion.",
                    "type": "capstone",
                    "chapter_id": "chapter-advanced",
                    "branch_id": "branch-main",
                    "required": True,
                    "completion_mode": "checkpoint_pass",
                    "estimated_duration_minutes": 45,
                    "layout": {"x": 1520, "y": 130},
                    "display": {"route_name": "Main"},
                    "prerequisites": {"requires_all": ["node-milestone-1"], "requires_any": ["node-practice-optional-1"], "recommended": ["node-review-1"]},
                    "ksa": [{"dimension": "S", "topic": "Operational Skills", "subtopic": "Release Management", "start_level": 2, "target_level": 4, "contribution_weight": 0.7}],
                    "unlocks": {"node_ids": [], "branch_ids": [], "recommended_next_node_ids": []},
                    "rewards": {"estimated_ksa_gain": {"S.Operational Skills.Release Management": 0.4}, "effort_score": 30, "reward_tags": ["capstone", "completion"]},
                    "retrospective_hooks": {"retrospective_after": True, "review_recommended": True, "recap_checkpoint_available": True},
                    "ksa_hooks": {"mini_assessment_available": True, "recommended_reassessment_topics": ["S.Operational Skills.Release Management"], "unlocks_deeper_refinement": True},
                    "remediation": {"is_remediation_node": False, "recommended_if_failed_node_ids": ["node-checkpoint-1"], "supports_review_for_node_ids": ["node-review-1"]},
                    "adaptive_unlock": {"ksa_thresholds": [{"dimension": "S", "topic": "Operational Skills", "min_level": 3}], "requires_branch_completion_ids": ["branch-main"], "requires_checkpoint_node_ids": ["node-checkpoint-1"], "requires_review_recommended": False, "recommended_only": False},
                },
            ],
            "edges": [
                {"from_node_id": "node-learning-unit-1", "to_node_id": "node-practice-1", "relationship": "requires_all"},
                {"from_node_id": "node-practice-1", "to_node_id": "node-quiz-1", "relationship": "requires_all"},
                {"from_node_id": "node-quiz-1", "to_node_id": "node-checkpoint-1", "relationship": "requires_all"},
                {"from_node_id": "node-checkpoint-1", "to_node_id": "node-assessment-hook-1", "relationship": "requires_all"},
                {"from_node_id": "node-assessment-hook-1", "to_node_id": "node-unlock-gate-1", "relationship": "requires_all"},
                {"from_node_id": "node-unlock-gate-1", "to_node_id": "node-milestone-1", "relationship": "requires_all"},
                {"from_node_id": "node-milestone-1", "to_node_id": "node-capstone-1", "relationship": "requires_all"},
                {"from_node_id": "node-practice-1", "to_node_id": "node-review-1", "relationship": "recommended"},
                {"from_node_id": "node-review-1", "to_node_id": "node-practice-optional-1", "relationship": "optional"},
                {"from_node_id": "node-practice-optional-1", "to_node_id": "node-capstone-1", "relationship": "requires_any"},
            ],
            "entry_node_ids": ["node-learning-unit-1"],
            "completion_rules": {"required_completion": "all_required_nodes", "optional_completion": "tracked_separately"},
            "visual_layout": {"layout_engine": "manual", "canvas_width": 1800, "canvas_height": 520},
            "metadata": {"domain": "devops", "template_type": "example_all_node_types", "routes": ["Main", "Accelerator"]},
        }

    def _convert_legacy_payload(self, legacy: LegacyCourseDefinition) -> dict[str, object]:
        chapters: list[dict[str, object]] = []
        nodes: list[dict[str, object]] = []
        edges: list[dict[str, object]] = []
        entry_node_ids: list[str] = []
        previous_node_id: str | None = None
        total_lessons = sum(len(module.lessons) for module in legacy.modules)
        fallback_duration = (
            max(5, int((legacy.estimated_duration_minutes or 0) / max(1, total_lessons)))
            if total_lessons > 0
            else None
        )

        global_index = 0
        for module_index, module in enumerate(sorted(legacy.modules, key=lambda item: item.order_index)):
            chapter_id = module.id or f"chapter-{module_index + 1}"
            chapters.append(
                {
                    "id": chapter_id,
                    "order_index": module.order_index,
                    "title": module.title,
                    "description": module.description,
                    "metadata": {
                        "learning_objectives": list(module.learning_objectives),
                        "migrated_from": "module",
                    },
                }
            )

            module_lessons = sorted(module.lessons, key=lambda item: item.order_index)
            if not module_lessons:
                module_lessons = [
                    CourseLessonDefinition(
                        id=None,
                        order_index=0,
                        title=f"{module.title} Overview",
                        description=module.description,
                        objectives=list(module.learning_objectives),
                        teaching_notes="",
                    )
                ]

            for lesson_index, lesson in enumerate(module_lessons):
                global_index += 1
                node_id = lesson.id or f"node-{module_index + 1}-{lesson_index + 1}"
                if previous_node_id:
                    edges.append(
                        {
                            "from_node_id": previous_node_id,
                            "to_node_id": node_id,
                            "relationship": "requires_all",
                        }
                    )
                else:
                    entry_node_ids.append(node_id)

                nodes.append(
                    {
                        "id": node_id,
                        "title": lesson.title,
                        "description": lesson.description,
                        "type": "learning_unit",
                        "chapter_id": chapter_id,
                        "branch_id": None,
                        "required": True,
                        "completion_mode": "lesson_complete",
                        "estimated_duration_minutes": fallback_duration,
                        "layout": {"x": 120 + ((global_index - 1) * 180), "y": 120 + (module_index * 170)},
                        "prerequisites": {
                            "requires_all": [previous_node_id] if previous_node_id else [],
                            "requires_any": [],
                            "recommended": [],
                        },
                        "metadata": {
                            "objectives": list(lesson.objectives),
                            "teaching_notes": lesson.teaching_notes,
                            "migrated_from": "lesson",
                        },
                        "ksa": [],
                        "display": {},
                        "unlocks": {"node_ids": [], "branch_ids": [], "recommended_next_node_ids": []},
                        "rewards": {"estimated_ksa_gain": {}, "effort_score": None, "reward_tags": []},
                        "retrospective_hooks": {"retrospective_after": False, "review_recommended": False, "recap_checkpoint_available": False},
                        "ksa_hooks": {"mini_assessment_available": False, "recommended_reassessment_topics": [], "unlocks_deeper_refinement": False},
                        "remediation": {"is_remediation_node": False, "recommended_if_failed_node_ids": [], "supports_review_for_node_ids": []},
                        "adaptive_unlock": {"ksa_thresholds": [], "requires_branch_completion_ids": [], "requires_checkpoint_node_ids": [], "requires_review_recommended": False, "recommended_only": False},
                    }
                )
                previous_node_id = node_id

        if not nodes:
            chapter_id = "chapter-1"
            node_id = "node-1"
            chapters.append(
                {
                    "id": chapter_id,
                    "order_index": 0,
                    "title": "Chapter 1",
                    "description": "",
                    "metadata": {"migrated_from": "module", "generated": True},
                }
            )
            nodes.append(
                {
                    "id": node_id,
                    "title": legacy.title,
                    "description": legacy.description,
                    "type": "milestone",
                    "chapter_id": chapter_id,
                    "branch_id": None,
                    "required": True,
                    "completion_mode": "manual",
                    "estimated_duration_minutes": legacy.estimated_duration_minutes,
                    "layout": {"x": 120, "y": 120},
                    "prerequisites": {"requires_all": [], "requires_any": [], "recommended": []},
                    "metadata": {"generated": True},
                    "ksa": [],
                    "display": {},
                    "unlocks": {"node_ids": [], "branch_ids": [], "recommended_next_node_ids": []},
                    "rewards": {"estimated_ksa_gain": {}, "effort_score": None, "reward_tags": []},
                    "retrospective_hooks": {"retrospective_after": False, "review_recommended": False, "recap_checkpoint_available": False},
                    "ksa_hooks": {"mini_assessment_available": False, "recommended_reassessment_topics": [], "unlocks_deeper_refinement": False},
                    "remediation": {"is_remediation_node": False, "recommended_if_failed_node_ids": [], "supports_review_for_node_ids": []},
                    "adaptive_unlock": {"ksa_thresholds": [], "requires_branch_completion_ids": [], "requires_checkpoint_node_ids": [], "requires_review_recommended": False, "recommended_only": False},
                }
            )
            entry_node_ids = [node_id]

        return {
            "schema_version": 2,
            "id": legacy.id,
            "title": legacy.title,
            "description": legacy.description,
            "scope": legacy.scope,
            "owner_user_id": legacy.owner_user_id,
            "subject": legacy.subject,
            "difficulty_level": legacy.difficulty_level,
            "estimated_duration_minutes": legacy.estimated_duration_minutes,
            "status": legacy.status,
            "allowed_file_ids": list(legacy.allowed_file_ids),
            "allowed_tags": list(legacy.allowed_tags),
            "chapters": chapters,
            "branches": [],
            "nodes": nodes,
            "edges": edges,
            "entry_node_ids": entry_node_ids,
            "completion_rules": {"required_completion": "all_required_nodes", "migrated_from_schema": 1},
            "visual_layout": {"layout_engine": "manual", "migrated_from_schema": 1},
            "metadata": {"migrated_from_schema": 1},
        }

    def _normalize_course_definition(self, parsed: CourseDefinition) -> CourseDefinition:
        normalized_nodes: list[CourseNodeDefinition] = []
        for node in parsed.nodes:
            normalized_nodes.append(
                node.model_copy(
                    update={
                        "title": node.title.strip(),
                        "description": node.description.strip(),
                        "chapter_id": node.chapter_id.strip() if node.chapter_id else None,
                        "branch_id": node.branch_id.strip() if node.branch_id else None,
                        "prerequisites": CourseNodePrerequisites(
                            requires_all=list(dict.fromkeys(item.strip() for item in node.prerequisites.requires_all if item.strip())),
                            requires_any=list(dict.fromkeys(item.strip() for item in node.prerequisites.requires_any if item.strip())),
                            recommended=list(dict.fromkeys(item.strip() for item in node.prerequisites.recommended if item.strip())),
                        ),
                        "ksa": [
                            item.model_copy(
                                update={
                                    "topic": item.topic.strip(),
                                    "subtopic": item.subtopic.strip() if item.subtopic else None,
                                }
                            )
                            for item in node.ksa
                        ],
                        "unlocks": CourseNodeUnlocksMetadata(
                            node_ids=list(dict.fromkeys(item.strip() for item in node.unlocks.node_ids if item.strip())),
                            branch_ids=list(dict.fromkeys(item.strip() for item in node.unlocks.branch_ids if item.strip())),
                            recommended_next_node_ids=list(
                                dict.fromkeys(item.strip() for item in node.unlocks.recommended_next_node_ids if item.strip())
                            ),
                        ),
                        "rewards": CourseNodeRewardMetadata(
                            estimated_ksa_gain={str(key): float(value) for key, value in (node.rewards.estimated_ksa_gain or {}).items()},
                            effort_score=node.rewards.effort_score,
                            reward_tags=list(dict.fromkeys(tag.strip().lower() for tag in node.rewards.reward_tags if tag.strip())),
                        ),
                        "ksa_hooks": CourseNodeKsaHooks(
                            mini_assessment_available=node.ksa_hooks.mini_assessment_available,
                            recommended_reassessment_topics=list(
                                dict.fromkeys(item.strip() for item in node.ksa_hooks.recommended_reassessment_topics if item.strip())
                            ),
                            unlocks_deeper_refinement=node.ksa_hooks.unlocks_deeper_refinement,
                        ),
                        "retrospective_hooks": CourseNodeRetrospectiveHooks(
                            retrospective_after=node.retrospective_hooks.retrospective_after,
                            review_recommended=node.retrospective_hooks.review_recommended,
                            recap_checkpoint_available=node.retrospective_hooks.recap_checkpoint_available,
                        ),
                        "remediation": CourseNodeRemediationMetadata(
                            is_remediation_node=node.remediation.is_remediation_node,
                            recommended_if_failed_node_ids=list(
                                dict.fromkeys(item.strip() for item in node.remediation.recommended_if_failed_node_ids if item.strip())
                            ),
                            supports_review_for_node_ids=list(
                                dict.fromkeys(item.strip() for item in node.remediation.supports_review_for_node_ids if item.strip())
                            ),
                        ),
                        "adaptive_unlock": CourseNodeAdaptiveUnlockMetadata(
                            ksa_thresholds=[
                                CourseNodeKsaThresholdRule(
                                    dimension=item.dimension,
                                    topic=item.topic.strip(),
                                    min_level=item.min_level,
                                )
                                for item in node.adaptive_unlock.ksa_thresholds
                            ],
                            requires_branch_completion_ids=list(
                                dict.fromkeys(item.strip() for item in node.adaptive_unlock.requires_branch_completion_ids if item.strip())
                            ),
                            requires_checkpoint_node_ids=list(
                                dict.fromkeys(item.strip() for item in node.adaptive_unlock.requires_checkpoint_node_ids if item.strip())
                            ),
                            requires_review_recommended=node.adaptive_unlock.requires_review_recommended,
                            recommended_only=node.adaptive_unlock.recommended_only,
                        ),
                    }
                )
            )

        normalized = parsed.model_copy(
            update={
                "title": parsed.title.strip(),
                "description": parsed.description.strip(),
                "subject": parsed.subject.strip(),
                "difficulty_level": parsed.difficulty_level.strip(),
                "allowed_tags": sorted({tag.strip().lower() for tag in parsed.allowed_tags if str(tag).strip()}),
                "chapters": [
                    chapter.model_copy(
                        update={
                            "title": chapter.title.strip(),
                            "description": chapter.description.strip(),
                        }
                    )
                    for chapter in sorted(parsed.chapters, key=lambda item: (item.order_index, item.title.lower()))
                ],
                "branches": [
                    branch.model_copy(
                        update={
                            "title": branch.title.strip(),
                            "description": branch.description.strip(),
                        }
                    )
                    for branch in parsed.branches
                ],
                "nodes": normalized_nodes,
                "edges": self._merged_edges_from_nodes_and_edges(normalized_nodes, parsed.edges),
            }
        )

        if not normalized.entry_node_ids:
            incoming_targets = {edge.to_node_id for edge in normalized.edges if edge.relationship in {"requires_all", "requires_any"}}
            fallback_entries = [node.id for node in normalized.nodes if node.id not in incoming_targets]
            normalized = normalized.model_copy(update={"entry_node_ids": fallback_entries})

        return normalized

    def _merged_edges_from_nodes_and_edges(
        self,
        nodes: list[CourseNodeDefinition],
        edges: list[CourseEdgeDefinition],
    ) -> list[CourseEdgeDefinition]:
        merged: dict[tuple[str, str, str], CourseEdgeDefinition] = {}

        for edge in edges:
            merged[(edge.from_node_id, edge.to_node_id, edge.relationship)] = edge

        for node in nodes:
            for source_id in node.prerequisites.requires_all:
                merged[(source_id, node.id, "requires_all")] = CourseEdgeDefinition(
                    from_node_id=source_id,
                    to_node_id=node.id,
                    relationship="requires_all",
                )
            for source_id in node.prerequisites.requires_any:
                merged[(source_id, node.id, "requires_any")] = CourseEdgeDefinition(
                    from_node_id=source_id,
                    to_node_id=node.id,
                    relationship="requires_any",
                )
            for source_id in node.prerequisites.recommended:
                merged[(source_id, node.id, "recommended")] = CourseEdgeDefinition(
                    from_node_id=source_id,
                    to_node_id=node.id,
                    relationship="recommended",
                )

        return [
            merged[key]
            for key in sorted(merged.keys(), key=lambda item: (item[2], item[0], item[1]))
        ]
