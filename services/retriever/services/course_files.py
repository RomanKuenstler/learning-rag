from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError, model_validator


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


class CourseDefinition(BaseModel):
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
    def validate_scope_owner(self) -> "CourseDefinition":
        if self.scope == "user" and self.owner_user_id is None:
            raise ValueError("owner_user_id is required for user-scoped courses")
        return self


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
        try:
            parsed = CourseDefinition.model_validate(payload)
        except ValidationError as error:
            first = error.errors()[0]
            location = ".".join(str(item) for item in first.get("loc", []))
            msg = str(first.get("msg", "invalid payload"))
            where = f" ({location})" if location else ""
            raise ValueError(f"{file_name}: {msg}{where}") from error

        normalized = parsed.model_copy(
            update={
                "title": parsed.title.strip(),
                "description": parsed.description.strip(),
                "subject": parsed.subject.strip(),
                "difficulty_level": parsed.difficulty_level.strip(),
                "allowed_tags": sorted({tag.strip().lower() for tag in parsed.allowed_tags if str(tag).strip()}),
                "modules": [
                    module.model_copy(
                        update={
                            "title": module.title.strip(),
                            "description": module.description.strip(),
                            "learning_objectives": [item.strip() for item in module.learning_objectives if str(item).strip()],
                            "lessons": [
                                lesson.model_copy(
                                    update={
                                        "title": lesson.title.strip(),
                                        "description": lesson.description.strip(),
                                        "objectives": [item.strip() for item in lesson.objectives if str(item).strip()],
                                        "teaching_notes": lesson.teaching_notes.strip(),
                                    }
                                )
                                for lesson in module.lessons
                            ],
                        }
                    )
                    for module in parsed.modules
                ],
            }
        )
        return normalized

    def safe_file_name(self, course_id: str, title: str) -> str:
        _ = title
        return f"{course_id}.json"

    def template_payload(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "title": "Docker Basics",
            "description": "Starter course with two modules and practical lessons.",
            "scope": "user",
            "owner_user_id": 1,
            "subject": "Docker",
            "difficulty_level": "beginner",
            "estimated_duration_minutes": 120,
            "status": "draft",
            "allowed_file_ids": [1, 2],
            "allowed_tags": ["docker", "containers"],
            "modules": [
                {
                    "order_index": 0,
                    "title": "Getting Started",
                    "description": "Foundational Docker concepts and commands.",
                    "learning_objectives": ["Understand images vs containers", "Run and inspect containers"],
                    "lessons": [
                        {
                            "order_index": 0,
                            "title": "What Docker Is",
                            "description": "Core concepts and terminology.",
                            "objectives": ["Explain images and containers"],
                            "teaching_notes": "Use a local demo with docker run and docker ps.",
                        },
                        {
                            "order_index": 1,
                            "title": "First Container",
                            "description": "Run and stop a sample container.",
                            "objectives": ["Use run, logs, stop, rm"],
                            "teaching_notes": "Pair with cleanup commands.",
                        },
                    ],
                },
                {
                    "order_index": 1,
                    "title": "Compose Basics",
                    "description": "Working with multi-service local stacks.",
                    "learning_objectives": ["Read compose files", "Start and inspect services"],
                    "lessons": [
                        {
                            "order_index": 0,
                            "title": "Compose File Structure",
                            "description": "Services, ports, and volumes.",
                            "objectives": ["Understand core compose keys"],
                            "teaching_notes": "Walk line-by-line through an example compose file.",
                        }
                    ],
                },
            ],
        }
