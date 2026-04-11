from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from services.common.models import LearningPath, UserAccount
from services.retriever.repositories.chat_repository import ChatRepository
from services.retriever.services.course_files import CourseDefinition, CourseNodeDefinition
from services.retriever.services.course_skilltree import COMPLETED_STATES, build_skilltree_runtime
from services.retriever.services.ksa_drills import evaluate_drill_attempt, generate_round_archetypes
from services.retriever.services.node_context import DIMENSION_GROUP

QUIZ_BOUNDARY_NODE_TYPES = {"quiz", "practice", "checkpoint", "milestone", "unlock_gate"}
CHECKPOINT_BOUNDARY_NODE_TYPES = {"checkpoint", "unlock_gate", "milestone"}
REVIEW_BOUNDARY_NODE_TYPES = {"review", "checkpoint", "unlock_gate", "milestone"}
ATTEMPT_ACTIVE_STATUS = {"in_progress", "generating"}


@dataclass(slots=True)
class NodeExecutionResult:
    attempt: Any
    auto_completed: bool = False
    completion_reason: str = ""
    node_completed: bool = False
    node_status: str = "in_progress"


def _extract_json_object(text: str) -> dict[str, Any]:
    raw = str(text or "").strip()
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in LLM response")
    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("LLM response JSON is not an object")
    return parsed


def _norm_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _first_items(*values: list[str], limit: int) -> list[str]:
    seen: list[str] = []
    for value in values:
        for item in value:
            normalized = str(item).strip()
            if not normalized or normalized in seen:
                continue
            seen.append(normalized)
            if len(seen) >= limit:
                return seen
    return seen


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


class LearningNodeExecutionService:
    def __init__(
        self,
        repository: ChatRepository,
        *,
        llm_invoke: Callable[[list[tuple[str, str]]], str],
        prompts_dir: Path | None = None,
    ) -> None:
        self.repository = repository
        self.llm_invoke = llm_invoke
        self.prompts_dir = prompts_dir

    def _load_prompt(self, file_name: str, fallback: str) -> str:
        if self.prompts_dir is not None:
            path = self.prompts_dir / file_name
            if path.exists():
                content = path.read_text(encoding="utf-8").strip()
                if content:
                    return content
        return fallback

    def start(
        self,
        *,
        user: UserAccount,
        learning_path: LearningPath,
        definition: CourseDefinition,
        node: CourseNodeDefinition,
        node_context: dict[str, Any],
        force_new_attempt: bool = False,
    ) -> NodeExecutionResult:
        progress_entries = self.repository.list_user_learning_node_progress(user_id=user.id, learning_path_id=learning_path.id)
        progress_map = {entry.node_id: entry.status for entry in progress_entries}
        runtime = build_skilltree_runtime(definition, persisted_node_progress=progress_map)
        current_state = runtime.node_progress.get(node.id, "locked")
        if current_state not in {"available", "in_progress", "failed_needs_retry"}:
            raise ValueError("Node is not startable in its current state")

        active_attempt = self._load_active_attempt(
            user_id=user.id,
            learning_path_id=learning_path.id,
            node_id=node.id,
        )
        if active_attempt is not None and not force_new_attempt:
            return NodeExecutionResult(
                attempt=active_attempt,
                auto_completed=False,
                completion_reason="resumed_active_attempt",
                node_completed=False,
                node_status="in_progress",
            )

        if active_attempt is not None and force_new_attempt:
            self._close_superseded_active_attempt(user_id=user.id, attempt=active_attempt)

        now = datetime.now(timezone.utc)
        self.repository.upsert_user_learning_node_progress(
            user_id=user.id,
            learning_path_id=learning_path.id,
            node_id=node.id,
            status="in_progress",
            started_at=now,
            completed_at=None,
        )

        package = self._build_runtime_package_for_node(
            user=user,
            learning_path=learning_path,
            definition=definition,
            node=node,
            node_context=node_context,
            progress_map=progress_map,
        )

        source_node_window = list(package.get("source_node_window") or [])
        attempt = self.repository.create_user_learning_node_execution_attempt(
            {
                "user_id": user.id,
                "learning_path_id": learning_path.id,
                "node_id": node.id,
                "node_type": node.type,
                "status": "in_progress",
                "generation_reason": "on_start_new_attempt" if force_new_attempt else "on_start",
                "package_json": package,
                "responses_json": {},
                "result_json": {},
                "context_snapshot_json": node_context,
                "source_node_window_json": source_node_window,
                "started_at": now,
            }
        )

        if node.type in {"unlock_gate", "milestone"}:
            checks = dict(package.get("requirements") or {})
            if bool(checks.get("all_requirements_met")):
                completed = self._complete_node_progress(
                    user=user,
                    learning_path=learning_path,
                    definition=definition,
                    node=node,
                    score=float(checks.get("computed_score", 1.0)),
                    gate_unlocked=True,
                )
                attempt = self.repository.update_user_learning_node_execution_attempt(
                    user_id=user.id,
                    attempt_id=attempt.id,
                    fields={
                        "status": "completed",
                        "result_json": {"requirements": checks, "auto_completed": True},
                        "completed_at": datetime.now(timezone.utc),
                    },
                ) or attempt
                return NodeExecutionResult(
                    attempt=attempt,
                    auto_completed=True,
                    completion_reason="requirements_met",
                    node_completed=completed,
                    node_status="completed" if completed else "in_progress",
                )
            return NodeExecutionResult(
                attempt=attempt,
                auto_completed=False,
                completion_reason="requirements_not_met",
                node_completed=False,
                node_status="in_progress",
            )

        return NodeExecutionResult(
            attempt=attempt,
            auto_completed=False,
            completion_reason="generated",
            node_completed=False,
            node_status="in_progress",
        )

    def start_placeholder(
        self,
        *,
        user: UserAccount,
        learning_path: LearningPath,
        definition: CourseDefinition,
        node: CourseNodeDefinition,
        node_context: dict[str, Any],
        force_new_attempt: bool = False,
    ) -> NodeExecutionResult:
        progress_entries = self.repository.list_user_learning_node_progress(user_id=user.id, learning_path_id=learning_path.id)
        progress_map = {entry.node_id: entry.status for entry in progress_entries}
        runtime = build_skilltree_runtime(definition, persisted_node_progress=progress_map)
        current_state = runtime.node_progress.get(node.id, "locked")
        if current_state not in {"available", "in_progress", "failed_needs_retry"}:
            raise ValueError("Node is not startable in its current state")

        active_attempt = self._load_active_attempt(
            user_id=user.id,
            learning_path_id=learning_path.id,
            node_id=node.id,
        )
        if active_attempt is not None and not force_new_attempt:
            status = str(active_attempt.status or "")
            reason = "resumed_active_attempt_generating" if status == "generating" else "resumed_active_attempt"
            return NodeExecutionResult(
                attempt=active_attempt,
                auto_completed=False,
                completion_reason=reason,
                node_completed=False,
                node_status="in_progress",
            )

        if active_attempt is not None and force_new_attempt:
            self._close_superseded_active_attempt(user_id=user.id, attempt=active_attempt)

        now = datetime.now(timezone.utc)
        self.repository.upsert_user_learning_node_progress(
            user_id=user.id,
            learning_path_id=learning_path.id,
            node_id=node.id,
            status="in_progress",
            started_at=now,
            completed_at=None,
        )
        attempt = self.repository.create_user_learning_node_execution_attempt(
            {
                "user_id": user.id,
                "learning_path_id": learning_path.id,
                "node_id": node.id,
                "node_type": node.type,
                "status": "generating",
                "generation_reason": "on_start_new_attempt" if force_new_attempt else "on_start",
                "package_json": {"node_type": node.type, "generation_state": "queued"},
                "responses_json": {},
                "result_json": {"generation_state": "queued"},
                "context_snapshot_json": node_context,
                "source_node_window_json": [],
                "started_at": now,
            }
        )
        return NodeExecutionResult(
            attempt=attempt,
            auto_completed=False,
            completion_reason="generation_queued",
            node_completed=False,
            node_status="in_progress",
        )

    def finalize_started_attempt_generation(
        self,
        *,
        user: UserAccount,
        attempt_id: str,
        learning_path: LearningPath,
        definition: CourseDefinition,
        node: CourseNodeDefinition,
        node_context: dict[str, Any],
    ) -> Any | None:
        attempt = self.repository.get_user_learning_node_execution_attempt(user_id=user.id, attempt_id=attempt_id)
        if attempt is None:
            return None
        if attempt.completed_at is not None:
            return attempt
        if str(attempt.status or "") not in {"generating", "in_progress"}:
            return attempt
        try:
            progress_entries = self.repository.list_user_learning_node_progress(user_id=user.id, learning_path_id=learning_path.id)
            progress_map = {entry.node_id: entry.status for entry in progress_entries}
            package = self._build_runtime_package_for_node(
                user=user,
                learning_path=learning_path,
                definition=definition,
                node=node,
                node_context=node_context,
                progress_map=progress_map,
            )
            source_node_window = list(package.get("source_node_window") or [])
            fields: dict[str, Any] = {
                "status": "in_progress",
                "package_json": package,
                "source_node_window_json": source_node_window,
                "result_json": {"generation_state": "ready"},
            }
            return self.repository.update_user_learning_node_execution_attempt(
                user_id=user.id,
                attempt_id=attempt.id,
                fields=fields,
            )
        except Exception as error:
            now = datetime.now(timezone.utc)
            self.repository.upsert_user_learning_node_progress(
                user_id=user.id,
                learning_path_id=learning_path.id,
                node_id=node.id,
                status="failed_needs_retry",
                started_at=now,
                completed_at=None,
            )
            fields = {
                "status": "failed",
                "result_json": {
                    "generation_state": "failed",
                    "generation_error": str(error),
                },
                "completed_at": now,
            }
            return self.repository.update_user_learning_node_execution_attempt(
                user_id=user.id,
                attempt_id=attempt.id,
                fields=fields,
            )

    def submit_responses(
        self,
        *,
        user: UserAccount,
        attempt_id: str,
        responses: dict[str, Any],
    ):
        attempt = self.repository.get_user_learning_node_execution_attempt(user_id=user.id, attempt_id=attempt_id)
        if attempt is None:
            return None
        merged = dict(attempt.responses_json or {})
        for key, value in dict(responses or {}).items():
            if key == "uploaded_artifacts" and isinstance(value, list):
                previous = list(merged.get("uploaded_artifacts") or [])
                previous.extend([dict(item) for item in value if isinstance(item, dict)])
                merged[key] = previous
            else:
                merged[key] = value
        return self.repository.update_user_learning_node_execution_attempt(
            user_id=user.id,
            attempt_id=attempt_id,
            fields={"responses_json": merged},
        )

    def complete(
        self,
        *,
        user: UserAccount,
        learning_path: LearningPath,
        definition: CourseDefinition,
        node: CourseNodeDefinition,
        attempt_id: str,
    ) -> NodeExecutionResult | None:
        attempt = self.repository.get_user_learning_node_execution_attempt(user_id=user.id, attempt_id=attempt_id)
        if attempt is None:
            return None
        package = dict(attempt.package_json or {})
        responses = dict(attempt.responses_json or {})
        now = datetime.now(timezone.utc)

        node_completed = False
        node_status = "in_progress"
        result_json: dict[str, Any]

        if node.type == "assessment_hook":
            result_json = self._evaluate_assessment_hook(user=user, responses=responses, package=package)
            required_rounds = int(package.get("required_round_count") or 0)
            completed_rounds = int(result_json.get("completed_round_count") or 0)
            node_completed = completed_rounds >= required_rounds and required_rounds > 0
            if node_completed:
                node_completed = self._complete_node_progress(
                    user=user,
                    learning_path=learning_path,
                    definition=definition,
                    node=node,
                    score=float(result_json.get("overall_score") or 1.0),
                    gate_unlocked=True,
                )
                node_status = "completed" if node_completed else "in_progress"
            else:
                node_status = "failed_needs_retry"
                self.repository.upsert_user_learning_node_progress(
                    user_id=user.id,
                    learning_path_id=learning_path.id,
                    node_id=node.id,
                    status="failed_needs_retry",
                    started_at=now,
                    completed_at=None,
                )
        elif node.type == "quiz":
            result_json = self._evaluate_quiz(user=user, responses=responses, package=package)
            node_completed = bool(result_json.get("passed"))
            if node_completed:
                node_completed = self._complete_node_progress(
                    user=user,
                    learning_path=learning_path,
                    definition=definition,
                    node=node,
                    score=float(result_json.get("overall_score") or 0.0),
                    gate_unlocked=True,
                )
                node_status = "completed" if node_completed else "in_progress"
            else:
                node_status = "failed_needs_retry"
                self.repository.upsert_user_learning_node_progress(
                    user_id=user.id,
                    learning_path_id=learning_path.id,
                    node_id=node.id,
                    status="failed_needs_retry",
                    started_at=now,
                    completed_at=None,
                )
        elif node.type == "practice":
            result_json = self._evaluate_practice(user=user, responses=responses, package=package)
            node_completed = bool(result_json.get("passed"))
            if node_completed:
                node_completed = self._complete_node_progress(
                    user=user,
                    learning_path=learning_path,
                    definition=definition,
                    node=node,
                    score=float(result_json.get("overall_score") or 0.0),
                    gate_unlocked=True,
                )
                node_status = "completed" if node_completed else "in_progress"
            else:
                node_status = "failed_needs_retry"
                self.repository.upsert_user_learning_node_progress(
                    user_id=user.id,
                    learning_path_id=learning_path.id,
                    node_id=node.id,
                    status="failed_needs_retry",
                    started_at=now,
                    completed_at=None,
                )
        elif node.type == "checkpoint":
            result_json = self._evaluate_checkpoint(user=user, responses=responses, package=package)
            node_completed = bool(result_json.get("passed"))
            if node_completed:
                node_completed = self._complete_node_progress(
                    user=user,
                    learning_path=learning_path,
                    definition=definition,
                    node=node,
                    score=float(result_json.get("overall_score") or 0.0),
                    gate_unlocked=True,
                )
                node_status = "completed" if node_completed else "in_progress"
            else:
                node_status = "failed_needs_retry"
                self.repository.upsert_user_learning_node_progress(
                    user_id=user.id,
                    learning_path_id=learning_path.id,
                    node_id=node.id,
                    status="failed_needs_retry",
                    started_at=now,
                    completed_at=None,
                )
        elif node.type == "capstone":
            result_json = self._evaluate_capstone(user=user, responses=responses, package=package)
            node_completed = bool(result_json.get("passed"))
            if node_completed:
                node_completed = self._complete_node_progress(
                    user=user,
                    learning_path=learning_path,
                    definition=definition,
                    node=node,
                    score=float(result_json.get("overall_score") or 0.0),
                    gate_unlocked=True,
                )
                node_status = "completed" if node_completed else "in_progress"
            else:
                node_status = "failed_needs_retry"
                self.repository.upsert_user_learning_node_progress(
                    user_id=user.id,
                    learning_path_id=learning_path.id,
                    node_id=node.id,
                    status="failed_needs_retry",
                    started_at=now,
                    completed_at=None,
                )
        elif node.type == "review":
            result_json = self._evaluate_review(user=user, responses=responses, package=package)
            node_completed = bool(result_json.get("passed"))
            if node_completed:
                node_completed = self._complete_node_progress(
                    user=user,
                    learning_path=learning_path,
                    definition=definition,
                    node=node,
                    score=float(result_json.get("overall_score") or 0.0),
                    gate_unlocked=True,
                )
                node_status = "completed" if node_completed else "in_progress"
            else:
                node_status = "failed_needs_retry"
                self.repository.upsert_user_learning_node_progress(
                    user_id=user.id,
                    learning_path_id=learning_path.id,
                    node_id=node.id,
                    status="failed_needs_retry",
                    started_at=now,
                    completed_at=None,
                )
        elif node.type == "unlock_gate":
            checks = self._check_unlock_gate_requirements(
                user=user,
                definition=definition,
                node=node,
                progress_map={
                    entry.node_id: entry.status
                    for entry in self.repository.list_user_learning_node_progress(user_id=user.id, learning_path_id=learning_path.id)
                },
                node_context=dict(attempt.context_snapshot_json or {}),
            )
            node_completed = bool(checks.get("all_requirements_met"))
            if node_completed:
                node_completed = self._complete_node_progress(
                    user=user,
                    learning_path=learning_path,
                    definition=definition,
                    node=node,
                    score=float(checks.get("computed_score") or 1.0),
                    gate_unlocked=True,
                )
                node_status = "completed" if node_completed else "in_progress"
            result_json = {"requirements": checks, "passed": node_completed}
        elif node.type == "milestone":
            checks = self._check_milestone_requirements(
                definition=definition,
                node=node,
                progress_map={
                    entry.node_id: entry.status
                    for entry in self.repository.list_user_learning_node_progress(user_id=user.id, learning_path_id=learning_path.id)
                },
            )
            node_completed = bool(checks.get("all_requirements_met"))
            if node_completed:
                node_completed = self._complete_node_progress(
                    user=user,
                    learning_path=learning_path,
                    definition=definition,
                    node=node,
                    score=1.0,
                    gate_unlocked=True,
                )
                node_status = "completed" if node_completed else "in_progress"
            result_json = {"requirements": checks, "passed": node_completed}
        else:
            raise ValueError(f"Node type '{node.type}' is not supported in this execution step")

        updated = self.repository.update_user_learning_node_execution_attempt(
            user_id=user.id,
            attempt_id=attempt.id,
            fields={
                "status": "completed" if node_completed else "failed",
                "result_json": result_json,
                "completed_at": now,
            },
        ) or attempt
        return NodeExecutionResult(
            attempt=updated,
            auto_completed=node_completed,
            completion_reason="completed" if node_completed else "not_passed",
            node_completed=node_completed,
            node_status=node_status,
        )

    def _load_active_attempt(self, *, user_id: int, learning_path_id: str, node_id: str):
        latest = self.repository.get_latest_user_learning_node_execution_attempt(
            user_id=user_id,
            learning_path_id=learning_path_id,
            node_id=node_id,
        )
        if latest is None:
            return None
        if latest.status in ATTEMPT_ACTIVE_STATUS and latest.completed_at is None:
            return latest
        return None

    def _close_superseded_active_attempt(self, *, user_id: int, attempt: Any) -> None:
        now = datetime.now(timezone.utc)
        result = dict(attempt.result_json or {})
        result["attempt_closed_reason"] = "superseded_by_new_attempt"
        self.repository.update_user_learning_node_execution_attempt(
            user_id=user_id,
            attempt_id=attempt.id,
            fields={
                "status": "superseded",
                "result_json": result,
                "completed_at": now,
            },
        )

    def _build_hard_prev_map(self, definition: CourseDefinition) -> dict[str, set[str]]:
        mapping: dict[str, set[str]] = {node.id: set() for node in definition.nodes}
        for edge in definition.edges:
            if edge.relationship in {"requires_all", "requires_any"}:
                mapping.setdefault(edge.to_node_id, set()).add(edge.from_node_id)
        for node in definition.nodes:
            mapping.setdefault(node.id, set()).update(node.prerequisites.requires_all)
            mapping.setdefault(node.id, set()).update(node.prerequisites.requires_any)
        return mapping

    def _collect_ancestors(self, *, definition: CourseDefinition, node_id: str) -> list[str]:
        parents = self._build_hard_prev_map(definition)
        seen: set[str] = set()
        stack = list(parents.get(node_id, set()))
        ordered: list[str] = []
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            ordered.append(current)
            stack.extend(list(parents.get(current, set())))
        return ordered

    def _practice_source_window(self, *, definition: CourseDefinition, node: CourseNodeDefinition) -> list[str]:
        node_by_id = {item.id: item for item in definition.nodes}
        ancestors = self._collect_ancestors(definition=definition, node_id=node.id)
        return [item for item in ancestors if node_by_id.get(item) and node_by_id[item].type in {"learning_unit", "quiz"}]

    def _checkpoint_source_window(self, *, definition: CourseDefinition, node: CourseNodeDefinition) -> list[str]:
        parents = self._build_hard_prev_map(definition)
        node_by_id = {item.id: item for item in definition.nodes}
        window: list[str] = [node.id]
        seen = {node.id}
        stack = list(parents.get(node.id, set()))
        while stack:
            parent_id = stack.pop()
            if parent_id in seen:
                continue
            seen.add(parent_id)
            window.append(parent_id)
            parent_node = node_by_id.get(parent_id)
            if parent_node and parent_node.type in CHECKPOINT_BOUNDARY_NODE_TYPES:
                continue
            stack.extend(list(parents.get(parent_id, set())))
        return window

    def _capstone_scope_window(self, *, definition: CourseDefinition, node: CourseNodeDefinition) -> list[str]:
        node_by_id = {item.id: item for item in definition.nodes}
        global_final = bool(node.metadata.get("global_final")) or not node.branch_id
        if global_final:
            return [item.id for item in definition.nodes if item.id != node.id]
        branch_nodes = [item.id for item in definition.nodes if item.branch_id == node.branch_id and item.id != node.id]
        scoped: list[str] = []
        for branch_node_id in branch_nodes:
            scoped.append(branch_node_id)
            scoped.extend(self._collect_ancestors(definition=definition, node_id=branch_node_id))
        dedup = []
        for item in scoped:
            if item in dedup:
                continue
            if item not in node_by_id:
                continue
            dedup.append(item)
        return dedup

    def _review_source_window(self, *, definition: CourseDefinition, node: CourseNodeDefinition) -> list[str]:
        parents = self._build_hard_prev_map(definition)
        window: list[str] = [node.id]
        seen = {node.id}
        stack = list(parents.get(node.id, set()))
        node_by_id = {item.id: item for item in definition.nodes}
        while stack:
            parent_id = stack.pop()
            if parent_id in seen:
                continue
            seen.add(parent_id)
            window.append(parent_id)
            parent_node = node_by_id.get(parent_id)
            if parent_node and parent_node.type in REVIEW_BOUNDARY_NODE_TYPES:
                continue
            stack.extend(list(parents.get(parent_id, set())))
        return window

    def _build_runtime_package_for_node(
        self,
        *,
        user: UserAccount,
        learning_path: LearningPath,
        definition: CourseDefinition,
        node: CourseNodeDefinition,
        node_context: dict[str, Any],
        progress_map: dict[str, str],
    ) -> dict[str, Any]:
        if node.type == "assessment_hook":
            return self._build_assessment_hook_package(
                user=user,
                learning_path=learning_path,
                definition=definition,
                node=node,
                node_context=node_context,
            )
        if node.type == "quiz":
            return self._build_quiz_package(
                user=user,
                learning_path=learning_path,
                definition=definition,
                node=node,
                node_context=node_context,
            )
        if node.type == "practice":
            return self._build_practice_package(
                user=user,
                learning_path=learning_path,
                definition=definition,
                node=node,
                node_context=node_context,
            )
        if node.type == "checkpoint":
            return self._build_checkpoint_package(
                user=user,
                learning_path=learning_path,
                definition=definition,
                node=node,
                node_context=node_context,
            )
        if node.type == "capstone":
            return self._build_capstone_package(
                user=user,
                learning_path=learning_path,
                definition=definition,
                node=node,
                node_context=node_context,
            )
        if node.type == "review":
            return self._build_review_package(
                user=user,
                learning_path=learning_path,
                definition=definition,
                node=node,
                node_context=node_context,
            )
        if node.type == "unlock_gate":
            checks = self._check_unlock_gate_requirements(
                user=user,
                definition=definition,
                node=node,
                progress_map=progress_map,
                node_context=node_context,
            )
            return {"node_type": "unlock_gate", "requirements": checks}
        if node.type == "milestone":
            checks = self._check_milestone_requirements(
                definition=definition,
                node=node,
                progress_map=progress_map,
            )
            return {"node_type": "milestone", "requirements": checks}
        raise ValueError(f"Node type '{node.type}' is not supported in this execution step")

    def _resolve_topic_group(self, dimension: str | None) -> str:
        dim = str(dimension or "").strip().upper()
        if dim == "K":
            return "Knowledge"
        if dim == "A":
            return "Abilities"
        return "Skills"

    def _topic_group_key(self, group_label: str) -> str:
        if group_label == "Knowledge":
            return "knowledge"
        if group_label == "Abilities":
            return "abilities"
        return "skills"

    def _difficulty_level_score(self, raw: object) -> float:
        value = str(raw or "").strip().lower()
        mapping = {
            "beginner": 1.0,
            "foundational": 1.0,
            "easy": 1.2,
            "intermediate": 2.0,
            "medium": 2.0,
            "advanced": 3.0,
            "hard": 3.0,
            "expert": 3.4,
        }
        return mapping.get(value, 2.0)

    def _build_difficulty_profile(
        self,
        *,
        user: UserAccount,
        node: CourseNodeDefinition,
        learning_path: LearningPath,
        node_context: dict[str, Any],
        source_node_window: list[str],
    ) -> dict[str, Any]:
        _ = source_node_window
        profile = self.repository.get_user_ksa_profile(user.id)
        profile_json = dict(profile.profile_json or {}) if profile else {}
        node_context_ksa = dict(node_context.get("ksa_context") or {})
        confidence_values = [
            _to_float(item.get("confidence"), 0.65)
            for item in list(node_context_ksa.get("topic_states") or [])
            if isinstance(item, dict)
        ]
        level_values = [
            _to_float(item.get("level"), 2.0)
            for item in list(node_context_ksa.get("topic_states") or [])
            if isinstance(item, dict)
        ]
        if not level_values:
            for section in ("knowledge", "skills", "abilities"):
                for raw in dict(profile_json.get(section) or {}).values():
                    level_values.append(_to_float(raw, 2.0))
        avg_level = sum(level_values) / float(len(level_values) or 1)
        avg_conf = sum(confidence_values) / float(len(confidence_values) or 1) if confidence_values else 0.65
        derived = dict(dict(profile_json.get("assessment_details") or {}).get("derived") or {})
        speed_multiplier = _to_float(derived.get("learning_speed_multiplier"), 1.0)
        decay_events = int(node_context_ksa.get("signals", {}).get("map_decay_events_total") or 0)

        requested_difficulty = max(
            self._difficulty_level_score(node.metadata.get("difficulty")),
            self._difficulty_level_score(learning_path.difficulty_level),
        )
        ksa_signal = min(3.5, max(1.0, avg_level))
        rigor_raw = (requested_difficulty * 0.6) + (ksa_signal * 0.4)
        if rigor_raw < 1.6:
            rigor_band = "foundational"
            target_quality = "clear_correct_application"
            expected_depth = "guided"
        elif rigor_raw < 2.6:
            rigor_band = "intermediate"
            target_quality = "consistent_independent_application"
            expected_depth = "structured"
        else:
            rigor_band = "advanced"
            target_quality = "tradeoff_reasoned_integration"
            expected_depth = "integrative"

        return {
            "rigor_band": rigor_band,
            "target_quality_level": target_quality,
            "expected_depth": expected_depth,
            "avg_ksa_level": round(avg_level, 4),
            "avg_confidence": round(avg_conf, 4),
            "learning_speed_multiplier": round(speed_multiplier, 4),
            "map_decay_events_total": decay_events,
            "complexity_guardrails": {
                "challenge_floor": max(1.0, round(rigor_raw - 0.5, 3)),
                "challenge_ceiling": min(4.0, round(rigor_raw + 0.5, 3)),
                "avoid_superficial": True,
                "avoid_unfair_overreach": avg_conf < 0.5,
            },
        }

    def _topic_candidates_from_nodes(
        self,
        *,
        definition: CourseDefinition,
        node_ids: list[str],
        node_context: dict[str, Any],
    ) -> list[str]:
        node_by_id = {item.id: item for item in definition.nodes}
        node_topics: list[str] = []
        for node_id in node_ids:
            item = node_by_id.get(node_id)
            if item is None:
                continue
            node_topics.extend(_norm_list(item.metadata.get("topics")))
            node_topics.extend(_norm_list(item.metadata.get("goals")))
            for ksa in item.ksa:
                label = f"{ksa.topic}:{ksa.subtopic}" if ksa.subtopic else str(ksa.topic)
                node_topics.append(label)
        prior = dict(node_context.get("prior_node_context") or {})
        target = dict(node_context.get("target_node_context") or {})
        return _first_items(
            node_topics,
            _norm_list(prior.get("prior_topic_summary")),
            _norm_list(prior.get("prior_concept_summary")),
            _norm_list(target.get("node_topics")),
            _norm_list(target.get("node_concepts")),
            limit=80,
        )

    def _build_assessment_hook_package(
        self,
        *,
        user: UserAccount,
        learning_path: LearningPath,
        definition: CourseDefinition,
        node: CourseNodeDefinition,
        node_context: dict[str, Any],
    ) -> dict[str, Any]:
        prior = dict(node_context.get("prior_node_context") or {})
        target = dict(node_context.get("target_node_context") or {})
        ksa_context = dict(node_context.get("ksa_context") or {})
        seed_topics = _first_items(
            _norm_list(prior.get("prior_topic_summary")),
            _norm_list(prior.get("prior_concept_summary")),
            _norm_list(target.get("node_topics")),
            _norm_list(target.get("node_concepts")),
            limit=22,
        )
        difficulty_profile = self._build_difficulty_profile(
            user=user,
            node=node,
            learning_path=learning_path,
            node_context=node_context,
            source_node_window=[node.id],
        )
        topic_prompt = self._load_prompt(
            "learning-node-assessment-hook-topic-selection.md",
            "Return strict JSON with key topics (array, length 8..16). "
            "Each topic item must include label, related_node_ids (array), related_ksa (object with dimension/topic/subtopic), why. "
            "Use complementary angles suitable for reverse definition, spot the flaw, power sprint, analogy match. "
            "Adapt complexity using difficulty_profile and KSA signals."
        )
        payload = {
            "course": {"id": learning_path.id, "title": learning_path.title, "subject": learning_path.subject},
            "node": {"id": node.id, "title": node.title, "description": node.description, "ksa": [item.model_dump() for item in node.ksa]},
            "seed_topics": seed_topics,
            "prior_completed_nodes": list(prior.get("completed_relevant_nodes") or []),
            "ksa_topic_states": list(ksa_context.get("topic_states") or []),
            "difficulty_profile": difficulty_profile,
            "rules": [
                "8 to 16 topics",
                "specific and assessment-ready",
                "avoid duplicates",
                "connected to prior nodes and KSA context",
            ],
        }
        topics: list[dict[str, Any]] = []
        try:
            raw = self.llm_invoke([("system", topic_prompt), ("user", json.dumps(payload, ensure_ascii=False))])
            parsed = _extract_json_object(raw)
            for item in list(parsed.get("topics") or []):
                if not isinstance(item, dict):
                    continue
                label = str(item.get("label") or "").strip()
                if not label:
                    continue
                topics.append(
                    {
                        "label": label,
                        "related_node_ids": [str(x).strip() for x in list(item.get("related_node_ids") or []) if str(x).strip()],
                        "related_ksa": dict(item.get("related_ksa") or {}),
                        "why": str(item.get("why") or "").strip(),
                    }
                )
        except Exception:
            topics = []
        if len(topics) < 8:
            fallback = _first_items(seed_topics, limit=12)
            while len(fallback) < 8:
                fallback.append(f"Applied {learning_path.subject or 'Topic'} angle {len(fallback)+1}")
            topics = [
                {
                    "label": label,
                    "related_node_ids": [node.id],
                    "related_ksa": {},
                    "why": "fallback",
                }
                for label in fallback[:12]
            ]
        topics = topics[:16]

        rounds: list[dict[str, Any]] = []
        for idx, topic in enumerate(topics, start=1):
            related_ksa = dict(topic.get("related_ksa") or {})
            group = self._resolve_topic_group(str(related_ksa.get("dimension") or "S"))
            subdomain = str(related_ksa.get("topic") or learning_path.subject or "Applied Topic").replace("_", " ").title()
            rounds.append(
                {
                    "round_number": idx,
                    "origin": "assessment_hook_topic",
                    "type_combo": str(related_ksa.get("dimension") or "S"),
                    "big_map_group": group,
                    "big_map_subdomain": subdomain,
                    "detailed_topic": str(topic.get("label") or ""),
                    "rationale": str(topic.get("why") or ""),
                }
            )
        generated = generate_round_archetypes(rounds=rounds, llm_invoke=self.llm_invoke)
        selected_topic_keys = sorted(
            {
                str(item.get("topic_key") or "")
                for item in list(generated.get("question_set") or [])
                if str(item.get("topic_key") or "").strip()
            }
        )
        return {
            "node_type": "assessment_hook",
            "difficulty_profile": difficulty_profile,
            "generated_topics": topics,
            "rounds": list(generated.get("rounds") or []),
            "question_set": list(generated.get("question_set") or []),
            "selected_topic_keys": selected_topic_keys,
            "required_round_count": len(rounds),
            "source_node_window": [str(node.id)],
        }

    def _quiz_source_window(self, *, definition: CourseDefinition, node: CourseNodeDefinition) -> list[str]:
        parents = self._build_hard_prev_map(definition)
        window: list[str] = [node.id]
        seen = {node.id}
        stack = list(parents.get(node.id, set()))
        node_by_id = {item.id: item for item in definition.nodes}
        while stack:
            parent_id = stack.pop()
            if parent_id in seen:
                continue
            seen.add(parent_id)
            window.append(parent_id)
            parent_node = node_by_id.get(parent_id)
            if parent_node and parent_node.type in QUIZ_BOUNDARY_NODE_TYPES:
                continue
            stack.extend(list(parents.get(parent_id, set())))
        return window

    def _build_quiz_package(
        self,
        *,
        user: UserAccount,
        learning_path: LearningPath,
        definition: CourseDefinition,
        node: CourseNodeDefinition,
        node_context: dict[str, Any],
    ) -> dict[str, Any]:
        source_window = self._quiz_source_window(definition=definition, node=node)
        node_by_id = {item.id: item for item in definition.nodes}
        window_nodes = [node_by_id[item] for item in source_window if item in node_by_id]
        topics = self._topic_candidates_from_nodes(definition=definition, node_ids=source_window, node_context=node_context)
        difficulty_profile = self._build_difficulty_profile(
            user=user,
            node=node,
            learning_path=learning_path,
            node_context=node_context,
            source_node_window=source_window,
        )
        quiz_prompt = self._load_prompt(
            "learning-node-quiz-package-generation.md",
            "Return strict JSON with mc_questions (exactly 12), free_text_questions (exactly 2), deep_dive_topics (exactly 3). "
            "Each mc question: id, type(single|multiple), question, options(>=3), correct_answers(1..n), topic, explanation. "
            "Each free text: id, question, topic, rubric(3..6 short criteria). "
            "Each deep dive topic: label, big_map_group(Knowledge|Skills|Abilities), big_map_subdomain, detailed_topic, rationale. "
            "Match difficulty_profile and avoid superficial recall."
        )
        input_payload = {
            "course": {"id": learning_path.id, "title": learning_path.title, "subject": learning_path.subject},
            "target_node": {"id": node.id, "title": node.title, "description": node.description},
            "window_node_ids": source_window,
            "window_nodes": [
                {
                    "id": item.id,
                    "title": item.title,
                    "description": item.description,
                    "type": item.type,
                    "metadata": dict(item.metadata or {}),
                }
                for item in window_nodes
            ],
            "topics": topics,
            "difficulty_profile": difficulty_profile,
            "ksa_context": dict(node_context.get("ksa_context") or {}),
        }
        mc_questions: list[dict[str, Any]] = []
        free_text: list[dict[str, Any]] = []
        deep_topics: list[dict[str, Any]] = []
        try:
            raw = self.llm_invoke([("system", quiz_prompt), ("user", json.dumps(input_payload, ensure_ascii=False))])
            parsed = _extract_json_object(raw)
            mc_questions = [dict(item) for item in list(parsed.get("mc_questions") or []) if isinstance(item, dict)]
            free_text = [dict(item) for item in list(parsed.get("free_text_questions") or []) if isinstance(item, dict)]
            deep_topics = [dict(item) for item in list(parsed.get("deep_dive_topics") or []) if isinstance(item, dict)]
        except Exception:
            mc_questions = []
            free_text = []
            deep_topics = []

        if len(mc_questions) < 12:
            topic_pool = topics or [learning_path.subject or "general"]
            for idx in range(len(mc_questions) + 1, 13):
                topic = topic_pool[(idx - 1) % len(topic_pool)]
                mc_questions.append(
                    {
                        "id": f"mc-{idx}",
                        "type": "single" if idx % 3 else "multiple",
                        "question": f"Which statement is most accurate about {topic}?",
                        "options": ["A correct-ish statement", "A partially wrong statement", "A clearly wrong statement"],
                        "correct_answers": ["A"],
                        "topic": topic,
                        "explanation": "Fallback deterministic item.",
                    }
                )
        mc_questions = mc_questions[:12]
        if len(free_text) < 2:
            ft_topics = _first_items(topics, limit=2)
            while len(ft_topics) < 2:
                ft_topics.append(learning_path.subject or "applied integration")
            free_text = [
                {
                    "id": f"ft-{idx+1}",
                    "question": f"Design and justify a robust solution strategy for {ft_topics[idx]} under realistic constraints.",
                    "topic": ft_topics[idx],
                    "rubric": ["correctness", "depth", "trade-off reasoning", "practical applicability"],
                }
                for idx in range(2)
            ]
        free_text = free_text[:2]
        if len(deep_topics) < 3:
            deep_pool = _first_items(topics, limit=3)
            while len(deep_pool) < 3:
                deep_pool.append(f"Applied {learning_path.subject or 'topic'} {len(deep_pool)+1}")
            deep_topics = [
                {
                    "label": deep_pool[idx],
                    "big_map_group": "Skills",
                    "big_map_subdomain": learning_path.subject or "Digital Craft",
                    "detailed_topic": deep_pool[idx],
                    "rationale": "fallback",
                }
                for idx in range(3)
            ]
        deep_topics = deep_topics[:3]

        rounds = []
        for idx, item in enumerate(deep_topics, start=1):
            rounds.append(
                {
                    "round_number": idx,
                    "origin": "quiz_deep_dive",
                    "type_combo": self._topic_group_key(str(item.get("big_map_group") or "Skills"))[:1].upper(),
                    "big_map_group": str(item.get("big_map_group") or "Skills"),
                    "big_map_subdomain": str(item.get("big_map_subdomain") or learning_path.subject or "Skills"),
                    "detailed_topic": str(item.get("detailed_topic") or item.get("label") or ""),
                    "rationale": str(item.get("rationale") or ""),
                }
            )
        generated = generate_round_archetypes(rounds=rounds, llm_invoke=self.llm_invoke)
        selected_topic_keys = sorted(
            {
                str(item.get("topic_key") or "")
                for item in list(generated.get("question_set") or [])
                if str(item.get("topic_key") or "").strip()
            }
        )
        return {
            "node_type": "quiz",
            "difficulty_profile": difficulty_profile,
            "source_node_window": source_window,
            "important_topics": topics[:18],
            "mc_questions": mc_questions,
            "free_text_questions": free_text,
            "deep_dive_topics": deep_topics,
            "deep_dive_rounds": list(generated.get("rounds") or []),
            "deep_dive_question_set": list(generated.get("question_set") or []),
            "selected_topic_keys": selected_topic_keys,
            "pass_threshold": float(node.metadata.get("pass_threshold") or 0.7),
        }

    def _build_practice_package(
        self,
        *,
        user: UserAccount,
        learning_path: LearningPath,
        definition: CourseDefinition,
        node: CourseNodeDefinition,
        node_context: dict[str, Any],
    ) -> dict[str, Any]:
        source_window = self._practice_source_window(definition=definition, node=node)
        topics = self._topic_candidates_from_nodes(definition=definition, node_ids=source_window, node_context=node_context)
        difficulty_profile = self._build_difficulty_profile(
            user=user,
            node=node,
            learning_path=learning_path,
            node_context=node_context,
            source_node_window=source_window,
        )
        prompt = self._load_prompt(
            "learning-node-practice-package-generation.md",
            "Return strict JSON object with tasks (array length 3..5). "
            "Each task requires id, type(scenario|artifact_upload), title, prompt, topic, rubric(array 3..6), required(bool). "
            "Mix scenario and artifact_upload tasks when suitable. "
            "Calibrate difficulty with difficulty_profile and KSA context."
        )
        payload = {
            "course": {"id": learning_path.id, "subject": learning_path.subject, "difficulty": learning_path.difficulty_level},
            "node": {"id": node.id, "title": node.title, "description": node.description, "metadata": dict(node.metadata or {})},
            "source_node_window": source_window,
            "topics": topics,
            "difficulty_profile": difficulty_profile,
            "ksa_context": dict(node_context.get("ksa_context") or {}),
        }
        tasks: list[dict[str, Any]] = []
        try:
            raw = self.llm_invoke([("system", prompt), ("user", json.dumps(payload, ensure_ascii=False))])
            parsed = _extract_json_object(raw)
            tasks = [dict(item) for item in list(parsed.get("tasks") or []) if isinstance(item, dict)]
        except Exception:
            tasks = []
        if len(tasks) < 3:
            fallback_topics = _first_items(topics, limit=4)
            while len(fallback_topics) < 4:
                fallback_topics.append(learning_path.subject or "applied practice")
            tasks = [
                {
                    "id": f"practice-task-{idx+1}",
                    "type": "scenario" if idx % 2 == 0 else "artifact_upload",
                    "title": f"Practice Task {idx+1}",
                    "prompt": f"Apply {fallback_topics[idx]} to a realistic scenario. Provide a concrete, practical output.",
                    "topic": fallback_topics[idx],
                    "rubric": ["correctness", "application", "clarity", "completeness"],
                    "required": True,
                }
                for idx in range(4)
            ]
        tasks = tasks[:5]
        if len(tasks) < 3:
            raise ValueError("Practice generation failed to produce minimum task count")

        normalized: list[dict[str, Any]] = []
        for idx, task in enumerate(tasks, start=1):
            task_type = str(task.get("type") or "scenario").strip().lower()
            if task_type not in {"scenario", "artifact_upload"}:
                task_type = "scenario"
            normalized.append(
                {
                    "id": str(task.get("id") or f"practice-task-{idx}").strip() or f"practice-task-{idx}",
                    "type": task_type,
                    "title": str(task.get("title") or f"Practice Task {idx}").strip(),
                    "prompt": str(task.get("prompt") or "").strip(),
                    "topic": str(task.get("topic") or "").strip(),
                    "rubric": _norm_list(task.get("rubric")) or ["correctness", "application", "clarity"],
                    "required": bool(task.get("required", True)),
                    "submission_mode": "upload" if task_type == "artifact_upload" else "text",
                }
            )

        return {
            "node_type": "practice",
            "difficulty_profile": difficulty_profile,
            "source_node_window": source_window,
            "important_topics": topics[:24],
            "tasks": normalized,
            "required_task_count": sum(1 for task in normalized if task.get("required", True)),
            "practice_pass_threshold": float(node.metadata.get("practice_pass_threshold") or 0.65),
        }

    def _build_checkpoint_package(
        self,
        *,
        user: UserAccount,
        learning_path: LearningPath,
        definition: CourseDefinition,
        node: CourseNodeDefinition,
        node_context: dict[str, Any],
    ) -> dict[str, Any]:
        source_window = self._checkpoint_source_window(definition=definition, node=node)
        topics = self._topic_candidates_from_nodes(definition=definition, node_ids=source_window, node_context=node_context)
        difficulty_profile = self._build_difficulty_profile(
            user=user,
            node=node,
            learning_path=learning_path,
            node_context=node_context,
            source_node_window=source_window,
        )
        prompt = self._load_prompt(
            "learning-node-checkpoint-package-generation.md",
            "Return strict JSON object with: mc_questions (exactly 10), free_text_quiz_questions (exactly 3), scenario_practice_questions (exactly 5), drill_topics (exactly 4). "
            "mc question shape: id,type(single|multiple),question,options,correct_answers,topic,explanation. "
            "free_text and scenario shape: id,question,topic,rubric(array 3..6). "
            "drill topic shape: label,big_map_group,big_map_subdomain,detailed_topic,rationale. "
            "Use difficulty_profile and KSA context."
        )
        payload = {
            "course": {"id": learning_path.id, "subject": learning_path.subject, "difficulty": learning_path.difficulty_level},
            "node": {"id": node.id, "title": node.title, "description": node.description, "metadata": dict(node.metadata or {})},
            "source_node_window": source_window,
            "topics": topics,
            "difficulty_profile": difficulty_profile,
            "ksa_context": dict(node_context.get("ksa_context") or {}),
        }
        parsed: dict[str, Any] = {}
        try:
            raw = self.llm_invoke([("system", prompt), ("user", json.dumps(payload, ensure_ascii=False))])
            parsed = _extract_json_object(raw)
        except Exception:
            parsed = {}

        mc_questions = [dict(item) for item in list(parsed.get("mc_questions") or []) if isinstance(item, dict)]
        free_text_questions = [dict(item) for item in list(parsed.get("free_text_quiz_questions") or []) if isinstance(item, dict)]
        scenario_questions = [dict(item) for item in list(parsed.get("scenario_practice_questions") or []) if isinstance(item, dict)]
        drill_topics = [dict(item) for item in list(parsed.get("drill_topics") or []) if isinstance(item, dict)]

        mc_questions = self._fill_mc_questions(mc_questions=mc_questions, topics=topics, count=10)
        free_text_questions = self._fill_text_questions(
            questions=free_text_questions,
            topics=topics,
            count=3,
            prefix="checkpoint-ft",
            stem="Explain and justify a robust approach for",
        )
        scenario_questions = self._fill_text_questions(
            questions=scenario_questions,
            topics=topics,
            count=5,
            prefix="checkpoint-scenario",
            stem="You are in a realistic situation involving",
        )
        drill_topics = self._fill_drill_topics(drill_topics=drill_topics, topics=topics, count=4, subject=learning_path.subject)

        deep_dive = self._build_drill_package(round_origin="checkpoint_deep_dive", deep_topics=drill_topics, subject=learning_path.subject)
        return {
            "node_type": "checkpoint",
            "difficulty_profile": difficulty_profile,
            "source_node_window": source_window,
            "important_topics": topics[:30],
            "mc_questions": mc_questions,
            "free_text_quiz_questions": free_text_questions,
            "scenario_practice_questions": scenario_questions,
            "drill_topics": drill_topics,
            "deep_dive_rounds": deep_dive["rounds"],
            "deep_dive_question_set": deep_dive["question_set"],
            "selected_topic_keys": deep_dive["selected_topic_keys"],
            "checkpoint_pass_threshold": float(node.metadata.get("checkpoint_pass_threshold") or 0.7),
            "component_minimum": float(node.metadata.get("component_minimum") or 0.6),
        }

    def _build_capstone_package(
        self,
        *,
        user: UserAccount,
        learning_path: LearningPath,
        definition: CourseDefinition,
        node: CourseNodeDefinition,
        node_context: dict[str, Any],
    ) -> dict[str, Any]:
        source_window = self._capstone_scope_window(definition=definition, node=node)
        topics = self._topic_candidates_from_nodes(definition=definition, node_ids=source_window, node_context=node_context)
        difficulty_profile = self._build_difficulty_profile(
            user=user,
            node=node,
            learning_path=learning_path,
            node_context=node_context,
            source_node_window=source_window,
        )
        prompt = self._load_prompt(
            "learning-node-capstone-package-generation.md",
            "Return strict JSON object with: mc_questions (exactly 24), free_text_quiz_questions (exactly 8), scenario_practice_questions (exactly 8), drill_topics (exactly 8). "
            "mc question shape: id,type(single|multiple),question,options,correct_answers,topic,explanation. "
            "free_text and scenario shape: id,question,topic,rubric(array 3..6). "
            "drill topic shape: label,big_map_group,big_map_subdomain,detailed_topic,rationale. "
            "Ensure broad representative topic coverage and high rigor."
        )
        payload = {
            "course": {"id": learning_path.id, "subject": learning_path.subject, "difficulty": learning_path.difficulty_level},
            "node": {"id": node.id, "title": node.title, "description": node.description, "metadata": dict(node.metadata or {})},
            "source_node_window": source_window,
            "topics": topics,
            "difficulty_profile": difficulty_profile,
            "ksa_context": dict(node_context.get("ksa_context") or {}),
        }
        parsed: dict[str, Any] = {}
        try:
            raw = self.llm_invoke([("system", prompt), ("user", json.dumps(payload, ensure_ascii=False))])
            parsed = _extract_json_object(raw)
        except Exception:
            parsed = {}

        mc_questions = [dict(item) for item in list(parsed.get("mc_questions") or []) if isinstance(item, dict)]
        free_text_questions = [dict(item) for item in list(parsed.get("free_text_quiz_questions") or []) if isinstance(item, dict)]
        scenario_questions = [dict(item) for item in list(parsed.get("scenario_practice_questions") or []) if isinstance(item, dict)]
        drill_topics = [dict(item) for item in list(parsed.get("drill_topics") or []) if isinstance(item, dict)]

        mc_questions = self._fill_mc_questions(mc_questions=mc_questions, topics=topics, count=24)
        free_text_questions = self._fill_text_questions(
            questions=free_text_questions,
            topics=topics,
            count=8,
            prefix="capstone-ft",
            stem="Integrate and justify an end-to-end strategy for",
        )
        scenario_questions = self._fill_text_questions(
            questions=scenario_questions,
            topics=topics,
            count=8,
            prefix="capstone-scenario",
            stem="Solve a realistic cross-functional challenge involving",
        )
        drill_topics = self._fill_drill_topics(drill_topics=drill_topics, topics=topics, count=8, subject=learning_path.subject)

        deep_dive = self._build_drill_package(round_origin="capstone_deep_dive", deep_topics=drill_topics, subject=learning_path.subject)
        return {
            "node_type": "capstone",
            "difficulty_profile": difficulty_profile,
            "source_node_window": source_window,
            "important_topics": topics[:60],
            "mc_questions": mc_questions,
            "free_text_quiz_questions": free_text_questions,
            "scenario_practice_questions": scenario_questions,
            "drill_topics": drill_topics,
            "deep_dive_rounds": deep_dive["rounds"],
            "deep_dive_question_set": deep_dive["question_set"],
            "selected_topic_keys": deep_dive["selected_topic_keys"],
            "capstone_pass_threshold": float(node.metadata.get("capstone_pass_threshold") or 0.75),
            "component_minimum": float(node.metadata.get("component_minimum") or 0.65),
        }

    def _build_review_package(
        self,
        *,
        user: UserAccount,
        learning_path: LearningPath,
        definition: CourseDefinition,
        node: CourseNodeDefinition,
        node_context: dict[str, Any],
    ) -> dict[str, Any]:
        source_window = self._review_source_window(definition=definition, node=node)
        topics = self._topic_candidates_from_nodes(definition=definition, node_ids=source_window, node_context=node_context)
        difficulty_profile = self._build_difficulty_profile(
            user=user,
            node=node,
            learning_path=learning_path,
            node_context=node_context,
            source_node_window=source_window,
        )
        prompt = self._load_prompt(
            "learning-node-review-package-generation.md",
            "Return strict JSON object with mc_questions (exactly 6) and review_prompts (exactly 4). "
            "mc question shape: id,type(single|multiple),question,options,correct_answers,topic,explanation. "
            "review prompt shape: id,question,topic,rubric(array 3..6). "
            "Keep this focused on consolidation and transfer with KSA-aware difficulty."
        )
        payload = {
            "course": {"id": learning_path.id, "subject": learning_path.subject, "difficulty": learning_path.difficulty_level},
            "node": {"id": node.id, "title": node.title, "description": node.description, "metadata": dict(node.metadata or {})},
            "source_node_window": source_window,
            "topics": topics,
            "difficulty_profile": difficulty_profile,
            "ksa_context": dict(node_context.get("ksa_context") or {}),
        }
        parsed: dict[str, Any] = {}
        try:
            raw = self.llm_invoke([("system", prompt), ("user", json.dumps(payload, ensure_ascii=False))])
            parsed = _extract_json_object(raw)
        except Exception:
            parsed = {}

        mc_questions = [dict(item) for item in list(parsed.get("mc_questions") or []) if isinstance(item, dict)]
        review_prompts = [dict(item) for item in list(parsed.get("review_prompts") or []) if isinstance(item, dict)]
        mc_questions = self._fill_mc_questions(mc_questions=mc_questions, topics=topics, count=6)
        review_prompts = self._fill_text_questions(
            questions=review_prompts,
            topics=topics,
            count=4,
            prefix="review-ft",
            stem="Reflect on and improve your approach for",
        )
        return {
            "node_type": "review",
            "difficulty_profile": difficulty_profile,
            "source_node_window": source_window,
            "important_topics": topics[:24],
            "mc_questions": mc_questions,
            "review_prompts": review_prompts,
            "review_pass_threshold": float(node.metadata.get("review_pass_threshold") or 0.6),
        }

    def _fill_mc_questions(self, *, mc_questions: list[dict[str, Any]], topics: list[str], count: int) -> list[dict[str, Any]]:
        if len(mc_questions) < count:
            topic_pool = topics or ["general"]
            for idx in range(len(mc_questions) + 1, count + 1):
                topic = topic_pool[(idx - 1) % len(topic_pool)]
                mc_questions.append(
                    {
                        "id": f"mc-{idx}",
                        "type": "single" if idx % 4 else "multiple",
                        "question": f"Which option best reflects sound practice for {topic}?",
                        "options": ["A", "B", "C", "D"],
                        "correct_answers": ["A"],
                        "topic": topic,
                        "explanation": "Fallback deterministic item.",
                    }
                )
        return mc_questions[:count]

    def _fill_text_questions(
        self,
        *,
        questions: list[dict[str, Any]],
        topics: list[str],
        count: int,
        prefix: str,
        stem: str,
    ) -> list[dict[str, Any]]:
        if len(questions) < count:
            topic_pool = _first_items(topics, limit=max(count, 1))
            while len(topic_pool) < count:
                topic_pool.append(f"Applied topic {len(topic_pool)+1}")
            for idx in range(len(questions), count):
                topic = topic_pool[idx]
                questions.append(
                    {
                        "id": f"{prefix}-{idx+1}",
                        "question": f"{stem} {topic}. Address constraints, trade-offs, and expected outcomes.",
                        "topic": topic,
                        "rubric": ["correctness", "depth", "reasoning", "applicability"],
                    }
                )
        return questions[:count]

    def _fill_drill_topics(
        self,
        *,
        drill_topics: list[dict[str, Any]],
        topics: list[str],
        count: int,
        subject: str,
    ) -> list[dict[str, Any]]:
        if len(drill_topics) < count:
            topic_pool = _first_items(topics, limit=count)
            while len(topic_pool) < count:
                topic_pool.append(f"Applied {subject or 'topic'} {len(topic_pool)+1}")
            for idx in range(len(drill_topics), count):
                topic = topic_pool[idx]
                drill_topics.append(
                    {
                        "label": topic,
                        "big_map_group": "Skills",
                        "big_map_subdomain": subject or "Digital Craft",
                        "detailed_topic": topic,
                        "rationale": "fallback",
                    }
                )
        return drill_topics[:count]

    def _build_drill_package(self, *, round_origin: str, deep_topics: list[dict[str, Any]], subject: str) -> dict[str, Any]:
        rounds = []
        for idx, item in enumerate(deep_topics, start=1):
            rounds.append(
                {
                    "round_number": idx,
                    "origin": round_origin,
                    "type_combo": self._topic_group_key(str(item.get("big_map_group") or "Skills"))[:1].upper(),
                    "big_map_group": str(item.get("big_map_group") or "Skills"),
                    "big_map_subdomain": str(item.get("big_map_subdomain") or subject or "Skills"),
                    "detailed_topic": str(item.get("detailed_topic") or item.get("label") or ""),
                    "rationale": str(item.get("rationale") or ""),
                }
            )
        generated = generate_round_archetypes(rounds=rounds, llm_invoke=self.llm_invoke)
        selected_topic_keys = sorted(
            {
                str(item.get("topic_key") or "")
                for item in list(generated.get("question_set") or [])
                if str(item.get("topic_key") or "").strip()
            }
        )
        return {
            "rounds": list(generated.get("rounds") or []),
            "question_set": list(generated.get("question_set") or []),
            "selected_topic_keys": selected_topic_keys,
        }

    def _check_unlock_gate_requirements(
        self,
        *,
        user: UserAccount,
        definition: CourseDefinition,
        node: CourseNodeDefinition,
        progress_map: dict[str, str],
        node_context: dict[str, Any],
    ) -> dict[str, Any]:
        _ = definition
        prereq = list(node.prerequisites.requires_all) + list(node.prerequisites.requires_any)
        prereq_completed = all(progress_map.get(item) in COMPLETED_STATES for item in prereq) if prereq else True
        profile = self.repository.get_user_ksa_profile(user.id)
        ksa_profile = dict(profile.profile_json or {}) if profile else {}
        requirements: list[dict[str, Any]] = []
        all_ok = prereq_completed
        for rule in list(node.adaptive_unlock.ksa_thresholds or []):
            section = DIMENSION_GROUP.get(rule.dimension, "skills")
            level = int(dict(ksa_profile.get(section) or {}).get(rule.topic, 1))
            ok = level >= int(rule.min_level)
            requirements.append(
                {
                    "type": "ksa_threshold",
                    "dimension": rule.dimension,
                    "topic": rule.topic,
                    "min_level": rule.min_level,
                    "current_level": level,
                    "met": ok,
                }
            )
            all_ok = all_ok and ok
        for checkpoint_id in list(node.adaptive_unlock.requires_checkpoint_node_ids or []):
            ok = progress_map.get(checkpoint_id) in COMPLETED_STATES
            requirements.append({"type": "checkpoint_node", "node_id": checkpoint_id, "met": ok})
            all_ok = all_ok and ok
        return {
            "all_requirements_met": all_ok,
            "prerequisites_completed": prereq_completed,
            "requirements": requirements,
            "computed_score": 1.0 if all_ok else 0.0,
            "context_snapshot_keys": sorted(list(dict(node_context or {}).keys())),
        }

    def _check_milestone_requirements(
        self,
        *,
        definition: CourseDefinition,
        node: CourseNodeDefinition,
        progress_map: dict[str, str],
    ) -> dict[str, Any]:
        _ = definition
        required_nodes = list(node.prerequisites.requires_all)
        any_nodes = list(node.prerequisites.requires_any)
        required_ok = all(progress_map.get(item) in COMPLETED_STATES for item in required_nodes)
        any_ok = True if not any_nodes else any(progress_map.get(item) in COMPLETED_STATES for item in any_nodes)
        checks = [
            {"type": "requires_all", "node_id": item, "met": progress_map.get(item) in COMPLETED_STATES}
            for item in required_nodes
        ]
        checks.extend(
            {"type": "requires_any", "node_id": item, "met": progress_map.get(item) in COMPLETED_STATES}
            for item in any_nodes
        )
        all_ok = required_ok and any_ok
        return {
            "all_requirements_met": all_ok,
            "requirements": checks,
            "computed_score": 1.0 if all_ok else 0.0,
        }

    def _evaluate_assessment_hook(self, *, user: UserAccount, responses: dict[str, Any], package: dict[str, Any]) -> dict[str, Any]:
        question_set = list(package.get("question_set") or [])
        selected_topic_keys = list(package.get("selected_topic_keys") or [])
        answer_map = dict(responses.get("answers") or responses.get("deep_dive_answers") or {})
        profile = self.repository.get_user_ksa_profile(user.id)
        base_profile = dict(profile.profile_json or {}) if profile else {
            "knowledge": {},
            "skills": {},
            "abilities": {},
            "assessment_details": {"derived": {}},
        }
        drill_outcome = evaluate_drill_attempt(
            user_id=user.id,
            selected_topic_keys=selected_topic_keys,
            question_set=question_set,
            answers=answer_map,
            base_profile_json=base_profile,
            ai_validation_overrides={},
        )
        updated_profile_json = dict(drill_outcome.get("updated_profile_json") or {})
        self.repository.upsert_user_ksa_profile(
            user_id=user.id,
            has_assessment=True,
            assessment_version="ksa-drill-v1",
            profile_json=updated_profile_json,
        )
        completed_rounds = len({int(item.get("block_index") or 0) for item in question_set if str(item.get("id")) in answer_map})
        required_round_count = int(package.get("required_round_count") or 0)
        overall_score = min(1.0, float(completed_rounds) / float(required_round_count or 1))
        return {
            "evaluation_type": "assessment_hook",
            "completed_round_count": completed_rounds,
            "required_round_count": required_round_count,
            "overall_score": round(overall_score, 4),
            "drill_result": dict(drill_outcome.get("result_json") or {}),
        }

    def _score_mc_questions(self, *, mc_questions: list[dict[str, Any]], responses: dict[str, Any]) -> dict[str, Any]:
        answer_map = dict(responses.get("mc_answers") or {})
        total = len(mc_questions)
        correct = 0.0
        details = []
        for question in mc_questions:
            qid = str(question.get("id") or "")
            expected = [str(item).strip() for item in list(question.get("correct_answers") or []) if str(item).strip()]
            actual_raw = answer_map.get(qid)
            if isinstance(actual_raw, list):
                actual = [str(item).strip() for item in actual_raw if str(item).strip()]
            elif isinstance(actual_raw, str):
                actual = [actual_raw.strip()] if actual_raw.strip() else []
            else:
                actual = []
            is_correct = sorted(expected) == sorted(actual)
            if is_correct:
                correct += 1.0
            details.append({"question_id": qid, "expected": expected, "actual": actual, "correct": is_correct})
        return {
            "total": total,
            "correct": int(correct),
            "score": round(float(correct) / float(total or 1), 4),
            "details": details,
        }

    def _evaluate_free_text(
        self,
        *,
        questions: list[dict[str, Any]],
        responses: dict[str, Any],
        answer_key: str,
    ) -> dict[str, Any]:
        answer_map = dict(responses.get(answer_key) or {})
        items = []
        scores = []
        for question in questions:
            qid = str(question.get("id") or "")
            answer = str(answer_map.get(qid) or "").strip()
            rubric = [str(item).strip() for item in list(question.get("rubric") or []) if str(item).strip()]
            prompt = self._load_prompt(
                "learning-node-free-text-evaluation.md",
                "Return strict JSON with score_0_1, depth_0_1, relevance_0_1, feedback, rubric_hits(array), strengths(array), gaps(array). "
                "Evaluate this learner response against the rubric."
            )
            payload = {
                "question": str(question.get("question") or ""),
                "topic": str(question.get("topic") or ""),
                "rubric": rubric,
                "answer": answer,
            }
            try:
                raw = self.llm_invoke([("system", prompt), ("user", json.dumps(payload, ensure_ascii=False))])
                parsed = _extract_json_object(raw)
                score = float(parsed.get("score_0_1") or 0.0)
                depth = float(parsed.get("depth_0_1") or 0.0)
                relevance = float(parsed.get("relevance_0_1") or 0.0)
                final_score = max(0.0, min(1.0, (score * 0.5) + (depth * 0.25) + (relevance * 0.25)))
                feedback = str(parsed.get("feedback") or "").strip()
                rubric_hits = [str(item).strip() for item in list(parsed.get("rubric_hits") or []) if str(item).strip()]
                strengths = [str(item).strip() for item in list(parsed.get("strengths") or []) if str(item).strip()]
                gaps = [str(item).strip() for item in list(parsed.get("gaps") or []) if str(item).strip()]
            except Exception:
                final_score = 0.0 if not answer else 0.4
                feedback = "Fallback evaluation used."
                rubric_hits = []
                strengths = []
                gaps = []
            scores.append(final_score)
            items.append(
                {
                    "question_id": qid,
                    "score_0_1": round(final_score, 4),
                    "feedback": feedback,
                    "rubric_hits": rubric_hits,
                    "strengths": strengths,
                    "gaps": gaps,
                }
            )
        return {
            "score": round(sum(scores) / float(len(scores) or 1), 4),
            "items": items,
        }

    def _evaluate_upload_tasks(self, *, tasks: list[dict[str, Any]], responses: dict[str, Any]) -> dict[str, Any]:
        uploaded_artifacts = [dict(item) for item in list(responses.get("uploaded_artifacts") or []) if isinstance(item, dict)]
        by_task: dict[str, list[dict[str, Any]]] = {}
        for artifact in uploaded_artifacts:
            task_id = str(artifact.get("task_id") or "").strip()
            if task_id:
                by_task.setdefault(task_id, []).append(artifact)
        items: list[dict[str, Any]] = []
        scores: list[float] = []
        for task in tasks:
            task_id = str(task.get("id") or "")
            artifacts = by_task.get(task_id, [])
            if not artifacts:
                items.append(
                    {
                        "task_id": task_id,
                        "score_0_1": 0.0,
                        "feedback": "No uploaded artifact found for required upload task.",
                        "artifacts_count": 0,
                    }
                )
                scores.append(0.0)
                continue
            combined_context = "\n\n".join(str(item.get("extracted_content") or item.get("content") or "") for item in artifacts)
            prompt = self._load_prompt(
                "learning-node-upload-evaluation.md",
                "Return strict JSON with score_0_1, feedback, strengths(array), gaps(array). "
                "Evaluate whether uploaded artifacts satisfy the task and rubric."
            )
            payload = {
                "task": task,
                "artifact_summaries": artifacts,
                "combined_context": combined_context[:12000],
            }
            try:
                raw = self.llm_invoke([("system", prompt), ("user", json.dumps(payload, ensure_ascii=False))])
                parsed = _extract_json_object(raw)
                score = max(0.0, min(1.0, float(parsed.get("score_0_1") or 0.0)))
                feedback = str(parsed.get("feedback") or "").strip()
                strengths = _norm_list(parsed.get("strengths"))
                gaps = _norm_list(parsed.get("gaps"))
            except Exception:
                score = 0.5
                feedback = "Fallback upload evaluation used."
                strengths = []
                gaps = []
            items.append(
                {
                    "task_id": task_id,
                    "score_0_1": round(score, 4),
                    "feedback": feedback,
                    "strengths": strengths,
                    "gaps": gaps,
                    "artifacts_count": len(artifacts),
                }
            )
            scores.append(score)
        return {
            "score": round(sum(scores) / float(len(scores) or 1), 4),
            "items": items,
        }

    def _required_task_completion(self, *, tasks: list[dict[str, Any]], responses: dict[str, Any]) -> tuple[bool, list[str]]:
        scenario_answers = dict(responses.get("scenario_answers") or responses.get("task_answers") or {})
        uploaded_artifacts = [dict(item) for item in list(responses.get("uploaded_artifacts") or []) if isinstance(item, dict)]
        task_ids_with_upload = {str(item.get("task_id") or "").strip() for item in uploaded_artifacts if str(item.get("task_id") or "").strip()}
        missing: list[str] = []
        for task in tasks:
            if not bool(task.get("required", True)):
                continue
            task_id = str(task.get("id") or "")
            task_type = str(task.get("type") or "scenario")
            if task_type == "artifact_upload":
                if task_id not in task_ids_with_upload:
                    missing.append(task_id)
                continue
            answer = str(scenario_answers.get(task_id) or "").strip()
            if not answer:
                missing.append(task_id)
        return len(missing) == 0, missing

    def _evaluate_practice(self, *, user: UserAccount, responses: dict[str, Any], package: dict[str, Any]) -> dict[str, Any]:
        tasks = [dict(item) for item in list(package.get("tasks") or []) if isinstance(item, dict)]
        scenario_tasks = [task for task in tasks if str(task.get("type") or "") != "artifact_upload"]
        upload_tasks = [task for task in tasks if str(task.get("type") or "") == "artifact_upload"]

        scenario_eval = self._evaluate_free_text(
            questions=[
                {
                    "id": str(task.get("id") or ""),
                    "question": str(task.get("prompt") or ""),
                    "topic": str(task.get("topic") or ""),
                    "rubric": list(task.get("rubric") or []),
                }
                for task in scenario_tasks
            ],
            responses=responses,
            answer_key="scenario_answers",
        )
        upload_eval = self._evaluate_upload_tasks(tasks=upload_tasks, responses=responses)

        all_required_completed, missing_required = self._required_task_completion(tasks=tasks, responses=responses)
        scenario_weight = 0.65 if scenario_tasks else 0.0
        upload_weight = 0.35 if upload_tasks else 0.0
        if scenario_weight + upload_weight == 0.0:
            overall_score = 0.0
        else:
            overall_score = (float(scenario_eval.get("score") or 0.0) * scenario_weight) + (
                float(upload_eval.get("score") or 0.0) * upload_weight
            )
            overall_score = overall_score / (scenario_weight + upload_weight)

        pass_threshold = float(package.get("practice_pass_threshold") or 0.65)
        passed = all_required_completed and overall_score >= pass_threshold
        return {
            "evaluation_type": "practice",
            "scenario_evaluation": scenario_eval,
            "upload_evaluation": upload_eval,
            "all_required_completed": all_required_completed,
            "missing_required_task_ids": missing_required,
            "overall_score": round(overall_score, 4),
            "pass_threshold": pass_threshold,
            "passed": passed,
        }

    def _evaluate_drill_section(self, *, user: UserAccount, package: dict[str, Any], responses: dict[str, Any]) -> dict[str, Any]:
        deep_answers = dict(responses.get("deep_dive_answers") or {})
        profile = self.repository.get_user_ksa_profile(user.id)
        base_profile = dict(profile.profile_json or {}) if profile else {
            "knowledge": {},
            "skills": {},
            "abilities": {},
            "assessment_details": {"derived": {}},
        }
        drill_outcome = evaluate_drill_attempt(
            user_id=user.id,
            selected_topic_keys=list(package.get("selected_topic_keys") or []),
            question_set=list(package.get("deep_dive_question_set") or []),
            answers=deep_answers,
            base_profile_json=base_profile,
            ai_validation_overrides={},
        )
        updated_profile_json = dict(drill_outcome.get("updated_profile_json") or {})
        self.repository.upsert_user_ksa_profile(
            user_id=user.id,
            has_assessment=True,
            assessment_version="ksa-drill-v1",
            profile_json=updated_profile_json,
        )
        required = len(list(package.get("deep_dive_rounds") or []))
        completed = len(
            {
                int(item.get("block_index") or 0)
                for item in list(package.get("deep_dive_question_set") or [])
                if str(item.get("id") or "") in deep_answers
            }
        )
        score = min(1.0, float(completed) / float(required or 1))
        return {
            "score": round(score, 4),
            "required_rounds": required,
            "completed_rounds": completed,
            "drill_result": dict(drill_outcome.get("result_json") or {}),
        }

    def _evaluate_quiz(self, *, user: UserAccount, responses: dict[str, Any], package: dict[str, Any]) -> dict[str, Any]:
        mc_questions = [dict(item) for item in list(package.get("mc_questions") or [])]
        mc_eval = self._score_mc_questions(mc_questions=mc_questions, responses=responses)
        drill_section = self._evaluate_drill_section(user=user, package=package, responses=responses)
        free_text_eval = self._evaluate_free_text(
            questions=[dict(item) for item in list(package.get("free_text_questions") or [])],
            responses=responses,
            answer_key="free_text_answers",
        )
        overall_score = (mc_eval["score"] * 0.5) + (float(drill_section["score"]) * 0.3) + (float(free_text_eval["score"]) * 0.2)
        pass_threshold = float(package.get("pass_threshold") or 0.7)
        return {
            "evaluation_type": "quiz",
            "mc_evaluation": mc_eval,
            "deep_dive_score": round(float(drill_section["score"]), 4),
            "deep_dive_required_rounds": int(drill_section["required_rounds"]),
            "deep_dive_completed_rounds": int(drill_section["completed_rounds"]),
            "free_text_evaluation": free_text_eval,
            "overall_score": round(overall_score, 4),
            "pass_threshold": pass_threshold,
            "passed": bool(overall_score >= pass_threshold),
            "drill_result": dict(drill_section.get("drill_result") or {}),
        }

    def _evaluate_checkpoint(self, *, user: UserAccount, responses: dict[str, Any], package: dict[str, Any]) -> dict[str, Any]:
        mc_eval = self._score_mc_questions(
            mc_questions=[dict(item) for item in list(package.get("mc_questions") or [])],
            responses=responses,
        )
        free_text_eval = self._evaluate_free_text(
            questions=[dict(item) for item in list(package.get("free_text_quiz_questions") or [])],
            responses=responses,
            answer_key="free_text_answers",
        )
        scenario_eval = self._evaluate_free_text(
            questions=[dict(item) for item in list(package.get("scenario_practice_questions") or [])],
            responses=responses,
            answer_key="scenario_answers",
        )
        drill_section = self._evaluate_drill_section(user=user, package=package, responses=responses)

        mc_score = float(mc_eval.get("score") or 0.0)
        free_score = float(free_text_eval.get("score") or 0.0)
        scenario_score = float(scenario_eval.get("score") or 0.0)
        drill_score = float(drill_section.get("score") or 0.0)

        overall_score = (mc_score * 0.35) + (free_score * 0.25) + (scenario_score * 0.25) + (drill_score * 0.15)
        pass_threshold = float(package.get("checkpoint_pass_threshold") or 0.7)
        component_minimum = float(package.get("component_minimum") or 0.6)

        required_complete = (
            len(dict(responses.get("mc_answers") or {})) >= len(list(package.get("mc_questions") or []))
            and len(dict(responses.get("free_text_answers") or {})) >= len(list(package.get("free_text_quiz_questions") or []))
            and len(dict(responses.get("scenario_answers") or {})) >= len(list(package.get("scenario_practice_questions") or []))
            and int(drill_section.get("completed_rounds") or 0) >= int(drill_section.get("required_rounds") or 0)
        )

        passed = (
            required_complete
            and overall_score >= pass_threshold
            and mc_score >= component_minimum
            and free_score >= component_minimum
            and scenario_score >= component_minimum
            and drill_score >= component_minimum
        )
        return {
            "evaluation_type": "checkpoint",
            "mc_evaluation": mc_eval,
            "free_text_quiz_evaluation": free_text_eval,
            "scenario_practice_evaluation": scenario_eval,
            "drill_evaluation": drill_section,
            "required_complete": required_complete,
            "overall_score": round(overall_score, 4),
            "pass_threshold": pass_threshold,
            "component_minimum": component_minimum,
            "passed": passed,
            "drill_result": dict(drill_section.get("drill_result") or {}),
        }

    def _evaluate_capstone(self, *, user: UserAccount, responses: dict[str, Any], package: dict[str, Any]) -> dict[str, Any]:
        mc_eval = self._score_mc_questions(
            mc_questions=[dict(item) for item in list(package.get("mc_questions") or [])],
            responses=responses,
        )
        free_text_eval = self._evaluate_free_text(
            questions=[dict(item) for item in list(package.get("free_text_quiz_questions") or [])],
            responses=responses,
            answer_key="free_text_answers",
        )
        scenario_eval = self._evaluate_free_text(
            questions=[dict(item) for item in list(package.get("scenario_practice_questions") or [])],
            responses=responses,
            answer_key="scenario_answers",
        )
        drill_section = self._evaluate_drill_section(user=user, package=package, responses=responses)

        mc_score = float(mc_eval.get("score") or 0.0)
        free_score = float(free_text_eval.get("score") or 0.0)
        scenario_score = float(scenario_eval.get("score") or 0.0)
        drill_score = float(drill_section.get("score") or 0.0)

        overall_score = (mc_score * 0.30) + (free_score * 0.25) + (scenario_score * 0.25) + (drill_score * 0.20)
        pass_threshold = float(package.get("capstone_pass_threshold") or 0.75)
        component_minimum = float(package.get("component_minimum") or 0.65)

        required_complete = (
            len(dict(responses.get("mc_answers") or {})) >= len(list(package.get("mc_questions") or []))
            and len(dict(responses.get("free_text_answers") or {})) >= len(list(package.get("free_text_quiz_questions") or []))
            and len(dict(responses.get("scenario_answers") or {})) >= len(list(package.get("scenario_practice_questions") or []))
            and int(drill_section.get("completed_rounds") or 0) >= int(drill_section.get("required_rounds") or 0)
        )

        passed = (
            required_complete
            and overall_score >= pass_threshold
            and mc_score >= component_minimum
            and free_score >= component_minimum
            and scenario_score >= component_minimum
            and drill_score >= component_minimum
        )
        return {
            "evaluation_type": "capstone",
            "mc_evaluation": mc_eval,
            "free_text_quiz_evaluation": free_text_eval,
            "scenario_practice_evaluation": scenario_eval,
            "drill_evaluation": drill_section,
            "required_complete": required_complete,
            "overall_score": round(overall_score, 4),
            "pass_threshold": pass_threshold,
            "component_minimum": component_minimum,
            "passed": passed,
            "drill_result": dict(drill_section.get("drill_result") or {}),
        }

    def _evaluate_review(self, *, user: UserAccount, responses: dict[str, Any], package: dict[str, Any]) -> dict[str, Any]:
        mc_eval = self._score_mc_questions(
            mc_questions=[dict(item) for item in list(package.get("mc_questions") or [])],
            responses=responses,
        )
        review_eval = self._evaluate_free_text(
            questions=[dict(item) for item in list(package.get("review_prompts") or [])],
            responses=responses,
            answer_key="free_text_answers",
        )
        mc_score = float(mc_eval.get("score") or 0.0)
        review_score = float(review_eval.get("score") or 0.0)
        threshold = float(package.get("review_pass_threshold") or 0.6)
        required_complete = (
            len(dict(responses.get("mc_answers") or {})) >= len(list(package.get("mc_questions") or []))
            and len(dict(responses.get("free_text_answers") or {})) >= len(list(package.get("review_prompts") or []))
        )
        overall_score = (mc_score * 0.45) + (review_score * 0.55)
        passed = required_complete and overall_score >= threshold
        return {
            "evaluation_type": "review",
            "mc_evaluation": mc_eval,
            "review_prompt_evaluation": review_eval,
            "required_complete": required_complete,
            "overall_score": round(overall_score, 4),
            "pass_threshold": threshold,
            "passed": passed,
        }

    def _complete_node_progress(
        self,
        *,
        user: UserAccount,
        learning_path: LearningPath,
        definition: CourseDefinition,
        node: CourseNodeDefinition,
        score: float,
        gate_unlocked: bool,
    ) -> bool:
        _ = definition
        if node.completion_mode == "quiz_pass":
            threshold = float(node.metadata.get("pass_threshold") or 0.7)
            if score < threshold:
                return False
        if node.completion_mode == "checkpoint_pass":
            threshold = float(node.metadata.get("checkpoint_pass_threshold") or 0.7)
            if score < threshold:
                return False
        if node.completion_mode == "assessment_threshold":
            threshold = float(node.metadata.get("assessment_threshold") or 0.7)
            if score < threshold:
                return False
        if node.completion_mode == "gate_unlock":
            expected_gate_key = str(node.metadata.get("gate_key") or "").strip()
            if expected_gate_key and not gate_unlocked:
                return False

        now = datetime.now(timezone.utc)
        self.repository.upsert_user_learning_node_progress(
            user_id=user.id,
            learning_path_id=learning_path.id,
            node_id=node.id,
            status="completed",
            started_at=now,
            completed_at=now,
        )
        return True
