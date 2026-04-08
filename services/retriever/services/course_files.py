from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, model_validator

COURSE_NODE_TYPES = {"learning_unit", "practice", "checkpoint", "review", "milestone"}
EDGE_RELATIONSHIPS = {"requires_all", "requires_any", "recommended"}
COMPLETION_MODES = {"lesson_complete", "manual", "practice_complete", "checkpoint_pass"}


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


class CourseNodePrerequisites(BaseModel):
    requires_all: list[str] = Field(default_factory=list)
    requires_any: list[str] = Field(default_factory=list)
    recommended: list[str] = Field(default_factory=list)


class CourseNodeKsaMetadata(BaseModel):
    dimension: Literal["K", "S", "A"]
    topic: str = Field(min_length=1, max_length=255)
    subtopic: str | None = Field(default=None, max_length=255)
    target_level: int | None = Field(default=None, ge=1, le=5)
    contribution_weight: float | None = Field(default=None, gt=0, le=1)


class CourseNodeLayout(BaseModel):
    x: float = 0
    y: float = 0


class CourseNodeDefinition(BaseModel):
    id: str
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=12000)
    type: Literal["learning_unit", "practice", "checkpoint", "review", "milestone"] = "learning_unit"
    chapter_id: str | None = Field(default=None)
    required: bool = True
    prerequisites: CourseNodePrerequisites = Field(default_factory=CourseNodePrerequisites)
    completion_mode: Literal["lesson_complete", "manual", "practice_complete", "checkpoint_pass"] = "lesson_complete"
    estimated_duration_minutes: int | None = Field(default=None, ge=1, le=100000)
    layout: CourseNodeLayout = Field(default_factory=CourseNodeLayout)
    metadata: dict[str, object] = Field(default_factory=dict)
    display: dict[str, object] = Field(default_factory=dict)
    ksa: list[CourseNodeKsaMetadata] = Field(default_factory=list)


class CourseEdgeDefinition(BaseModel):
    from_node_id: str
    to_node_id: str
    relationship: Literal["requires_all", "requires_any", "recommended"] = "requires_all"


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

        node_id_set = set(node_ids)
        chapter_id_set = set(chapter_ids)
        for node in self.nodes:
            if node.chapter_id and node.chapter_id not in chapter_id_set:
                raise ValueError(f"node '{node.id}' references unknown chapter_id '{node.chapter_id}'")
            for required_id in node.prerequisites.requires_all + node.prerequisites.requires_any + node.prerequisites.recommended:
                if required_id not in node_id_set:
                    raise ValueError(f"node '{node.id}' references unknown prerequisite node '{required_id}'")
                if required_id == node.id:
                    raise ValueError(f"node '{node.id}' cannot depend on itself")

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
            "title": "Docker Fundamentals Skilltree",
            "description": "Starter skilltree course with checkpoints and optional practice nodes.",
            "scope": "user",
            "owner_user_id": 1,
            "subject": "Docker",
            "difficulty_level": "beginner",
            "estimated_duration_minutes": 120,
            "status": "draft",
            "allowed_file_ids": [1, 2],
            "allowed_tags": ["docker", "containers"],
            "chapters": [
                {
                    "id": "chapter-foundations",
                    "order_index": 0,
                    "title": "Foundations",
                    "description": "Core concepts and first runs.",
                },
                {
                    "id": "chapter-compose",
                    "order_index": 1,
                    "title": "Compose",
                    "description": "Multi-service local environments.",
                },
            ],
            "nodes": [
                {
                    "id": "node-images-containers",
                    "title": "Images vs Containers",
                    "description": "Build a strong mental model.",
                    "type": "learning_unit",
                    "chapter_id": "chapter-foundations",
                    "required": True,
                    "completion_mode": "lesson_complete",
                    "estimated_duration_minutes": 20,
                    "layout": {"x": 80, "y": 120},
                    "prerequisites": {"requires_all": [], "requires_any": [], "recommended": []},
                    "ksa": [
                        {
                            "dimension": "K",
                            "topic": "information_technology",
                            "target_level": 2,
                            "contribution_weight": 0.5,
                        }
                    ],
                },
                {
                    "id": "node-first-container",
                    "title": "Run First Container",
                    "description": "Use run, ps, logs, stop, rm.",
                    "type": "practice",
                    "chapter_id": "chapter-foundations",
                    "required": True,
                    "completion_mode": "practice_complete",
                    "estimated_duration_minutes": 30,
                    "layout": {"x": 300, "y": 120},
                    "prerequisites": {"requires_all": ["node-images-containers"], "requires_any": [], "recommended": []},
                    "ksa": [
                        {
                            "dimension": "S",
                            "topic": "digital_craft",
                            "subtopic": "Full-Stack Development",
                            "target_level": 2,
                            "contribution_weight": 0.6,
                        }
                    ],
                },
                {
                    "id": "node-compose-basics",
                    "title": "Compose Basics",
                    "description": "Read and run compose files.",
                    "type": "checkpoint",
                    "chapter_id": "chapter-compose",
                    "required": True,
                    "completion_mode": "checkpoint_pass",
                    "estimated_duration_minutes": 30,
                    "layout": {"x": 520, "y": 120},
                    "prerequisites": {"requires_all": ["node-first-container"], "requires_any": [], "recommended": []},
                    "ksa": [],
                },
                {
                    "id": "node-review-cleanup",
                    "title": "Cleanup Review",
                    "description": "Optional consolidation and review.",
                    "type": "review",
                    "chapter_id": "chapter-compose",
                    "required": False,
                    "completion_mode": "manual",
                    "estimated_duration_minutes": 15,
                    "layout": {"x": 520, "y": 260},
                    "prerequisites": {"requires_all": ["node-first-container"], "requires_any": [], "recommended": []},
                    "ksa": [],
                },
            ],
            "edges": [
                {"from_node_id": "node-images-containers", "to_node_id": "node-first-container", "relationship": "requires_all"},
                {"from_node_id": "node-first-container", "to_node_id": "node-compose-basics", "relationship": "requires_all"},
                {"from_node_id": "node-first-container", "to_node_id": "node-review-cleanup", "relationship": "recommended"},
            ],
            "entry_node_ids": ["node-images-containers"],
            "completion_rules": {"required_completion": "all_required_nodes"},
            "visual_layout": {"layout_engine": "manual", "canvas_width": 900, "canvas_height": 460},
            "metadata": {"domain": "docker"},
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
                    "required": True,
                    "completion_mode": "manual",
                    "estimated_duration_minutes": legacy.estimated_duration_minutes,
                    "layout": {"x": 120, "y": 120},
                    "prerequisites": {"requires_all": [], "requires_any": [], "recommended": []},
                    "metadata": {"generated": True},
                    "ksa": [],
                    "display": {},
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
