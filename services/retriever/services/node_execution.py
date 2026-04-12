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
from services.retriever.services.ksa_drills import TOPIC_BY_KEY, evaluate_drill_attempt, generate_round_archetypes
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
        allowed_states = {"available", "in_progress", "failed_needs_retry"}
        if node.type == "assessment_hook":
            allowed_states.add("completed")
            allowed_states.add("mastered")
        if current_state not in allowed_states:
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
        if not (node.type == "assessment_hook" and current_state in {"completed", "mastered"}):
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

    def restart_with_existing_package(
        self,
        *,
        user: UserAccount,
        learning_path: LearningPath,
        definition: CourseDefinition,
        node: CourseNodeDefinition,
        node_context: dict[str, Any],
    ) -> NodeExecutionResult:
        progress_entries = self.repository.list_user_learning_node_progress(user_id=user.id, learning_path_id=learning_path.id)
        progress_map = {entry.node_id: entry.status for entry in progress_entries}
        runtime = build_skilltree_runtime(definition, persisted_node_progress=progress_map)
        current_state = runtime.node_progress.get(node.id, "locked")
        allowed_states = {"available", "in_progress", "failed_needs_retry", "completed", "mastered"}
        if current_state not in allowed_states:
            raise ValueError("Node is not startable in its current state")

        active_attempt = self._load_active_attempt(
            user_id=user.id,
            learning_path_id=learning_path.id,
            node_id=node.id,
        )
        if active_attempt is not None:
            self._close_superseded_active_attempt(user_id=user.id, attempt=active_attempt)

        attempts = self.repository.list_user_learning_node_execution_attempts(
            user_id=user.id,
            learning_path_id=learning_path.id,
            node_id=node.id,
            limit=30,
        )
        reusable_package: dict[str, Any] | None = None
        for item in attempts:
            status = str(getattr(item, "status", "") or "")
            if status == "generating":
                continue
            package_json = dict(getattr(item, "package_json", {}) or {})
            if not package_json:
                continue
            generation_state = str(dict(getattr(item, "result_json", {}) or {}).get("generation_state") or "").strip().lower()
            if generation_state == "queued":
                continue
            reusable_package = package_json
            break
        if reusable_package is None:
            raise ValueError("No reusable assessment package found for restart")

        now = datetime.now(timezone.utc)
        if current_state not in {"completed", "mastered"}:
            self.repository.upsert_user_learning_node_progress(
                user_id=user.id,
                learning_path_id=learning_path.id,
                node_id=node.id,
                status="in_progress",
                started_at=now,
                completed_at=None,
            )

        source_node_window = list(reusable_package.get("source_node_window") or [])
        attempt = self.repository.create_user_learning_node_execution_attempt(
            {
                "user_id": user.id,
                "learning_path_id": learning_path.id,
                "node_id": node.id,
                "node_type": node.type,
                "status": "in_progress",
                "generation_reason": "on_restart_reuse_package",
                "package_json": reusable_package,
                "responses_json": {},
                "result_json": {},
                "context_snapshot_json": node_context,
                "source_node_window_json": source_node_window,
                "started_at": now,
            }
        )
        return NodeExecutionResult(
            attempt=attempt,
            auto_completed=False,
            completion_reason="restarted_reused_package",
            node_completed=False,
            node_status="completed" if current_state in {"completed", "mastered"} else "in_progress",
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
        allowed_states = {"available", "in_progress", "failed_needs_retry"}
        if node.type == "assessment_hook":
            allowed_states.add("completed")
            allowed_states.add("mastered")
        if current_state not in allowed_states:
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
        if not (node.type == "assessment_hook" and current_state in {"completed", "mastered"}):
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
                previous_mirror_id = self._get_previous_mirrored_drill_attempt_id(
                    user_id=user.id,
                    learning_path_id=learning_path.id,
                    node_id=node.id,
                    current_attempt_id=str(attempt.id),
                )
                if previous_mirror_id:
                    self._remove_mirrored_drill_attempt_impact(
                        user_id=user.id,
                        drill_attempt_id=previous_mirror_id,
                    )
                mirrored_drill_attempt_id = self._mirror_assessment_hook_as_drill_attempt(
                    user=user,
                    learning_path=learning_path,
                    node=node,
                    package=package,
                    responses=responses,
                    drill_result=dict(result_json.get("drill_result") or {}),
                )
                if mirrored_drill_attempt_id:
                    result_json["mirrored_drill_attempt_id"] = mirrored_drill_attempt_id
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
        elif node.type == "learning_unit":
            result_json = self._evaluate_learning_unit(responses=responses, package=package)
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

    def _mirror_assessment_hook_as_drill_attempt(
        self,
        *,
        user: UserAccount,
        learning_path: LearningPath,
        node: CourseNodeDefinition,
        package: dict[str, Any],
        responses: dict[str, Any],
        drill_result: dict[str, Any],
    ) -> str:
        selected_topic_keys = [str(item).strip() for item in list(package.get("selected_topic_keys") or []) if str(item).strip()]
        question_set = [dict(item) for item in list(package.get("question_set") or []) if isinstance(item, dict)]
        answer_map = dict(responses.get("answers") or responses.get("deep_dive_answers") or {})
        source_topic_input = f"Course Node: {learning_path.title} / {node.title}"

        drill_attempt = self.repository.create_user_ksa_drill_attempt(
            user_id=user.id,
            assessment_version="ksa-drill-v1",
            selected_topic_keys=selected_topic_keys,
            question_set_json=question_set,
            source_topic_input=source_topic_input,
            topic_classification_json={},
            rounds_json=[
                {
                    **dict(item),
                    # Keep KSA drill history schema-compatible for KsaPanel rendering.
                    "origin": str(dict(item).get("origin") or "") in {"user_core", "user_variant", "llm_stretch", "llm_growth"}
                    and str(dict(item).get("origin"))
                    or "user_core",
                }
                for item in list(package.get("rounds") or [])
                if isinstance(item, dict)
            ],
        )
        self.repository.upsert_user_ksa_drill_answers(
            user_id=user.id,
            attempt_id=drill_attempt.id,
            answers_json=answer_map,
        )
        result_payload = dict(drill_result or {})
        result_payload["source"] = "course_node_assessment_hook"
        result_payload["source_label"] = "Course Node"
        result_payload["course_node"] = {
            "learning_path_id": learning_path.id,
            "learning_path_title": learning_path.title,
            "node_id": node.id,
            "node_title": node.title,
            "node_type": node.type,
        }
        self.repository.complete_user_ksa_drill_attempt(
            user_id=user.id,
            attempt_id=drill_attempt.id,
            result_json=result_payload,
        )
        return str(drill_attempt.id)

    def _get_previous_mirrored_drill_attempt_id(
        self,
        *,
        user_id: int,
        learning_path_id: str,
        node_id: str,
        current_attempt_id: str,
    ) -> str:
        attempts = self.repository.list_user_learning_node_execution_attempts(
            user_id=user_id,
            learning_path_id=learning_path_id,
            node_id=node_id,
            limit=25,
        )
        for record in attempts:
            if str(record.id) == current_attempt_id:
                continue
            result_json = dict(record.result_json or {})
            mirrored_id = str(result_json.get("mirrored_drill_attempt_id") or "").strip()
            if mirrored_id:
                return mirrored_id
        return ""

    def _remove_mirrored_drill_attempt_impact(self, *, user_id: int, drill_attempt_id: str) -> None:
        attempt = self.repository.get_user_ksa_drill_attempt(user_id=user_id, attempt_id=drill_attempt_id)
        if attempt is None:
            return
        result_json = dict(attempt.result_json or {})
        topic_updates = dict(result_json.get("topic_updates") or {})
        profile = self.repository.get_user_ksa_profile(user_id)
        profile_json = dict(profile.profile_json or {}) if profile else {}
        knowledge = dict(profile_json.get("knowledge") or {})
        skills = dict(profile_json.get("skills") or {})
        abilities = dict(profile_json.get("abilities") or {})
        drill_state = dict(profile_json.get("drill_state") or {})
        topic_nodes = dict(drill_state.get("topic_nodes") or {})

        for topic_key, update in topic_updates.items():
            topic = TOPIC_BY_KEY.get(str(topic_key))
            if topic is None:
                continue
            group = str(topic.get("group") or "")
            delta = float(dict(update or {}).get("delta") or 0.0)
            if group == "knowledge":
                current = float(knowledge.get(topic_key) or 2.0)
                knowledge[topic_key] = max(1, min(5, int(round(current - delta))))
            elif group == "skills":
                current = float(skills.get(topic_key) or 2.0)
                skills[topic_key] = max(1, min(5, int(round(current - delta))))
            elif group == "abilities":
                current = float(abilities.get(topic_key) or 2.0)
                abilities[topic_key] = max(1, min(5, int(round(current - delta))))
            node_payload = dict(topic_nodes.get(topic_key) or {})
            if node_payload:
                level = float(node_payload.get("level") or 2.0)
                next_level = max(1.0, min(5.0, level - delta))
                node_payload["level"] = round(next_level, 3)
                node_payload["chart_level"] = max(1, min(5, int(round(next_level))))
                topic_nodes[topic_key] = node_payload

        drill_state["topic_nodes"] = topic_nodes
        drill_state["attempt_count"] = max(0, int(drill_state.get("attempt_count") or 0) - 1)
        profile_json["knowledge"] = knowledge
        profile_json["skills"] = skills
        profile_json["abilities"] = abilities
        profile_json["drill_state"] = drill_state

        assessment_details = dict(profile_json.get("assessment_details") or {})
        derived = dict(assessment_details.get("derived") or {})
        logic = float(abilities.get("executive_function") or 2)
        quant = float(abilities.get("quantitative_reasoning") or 2)
        logic_quant_index = (logic / 5.0) + (quant / 5.0)
        derived["logic_quantitative_index"] = round(logic_quant_index, 4)
        derived["learning_speed_multiplier"] = 1.5 if logic_quant_index > 1.6 else 1.0
        assessment_details["derived"] = derived
        profile_json["assessment_details"] = assessment_details

        self.repository.upsert_user_ksa_profile(
            user_id=user_id,
            has_assessment=True,
            assessment_version="ksa-drill-v1",
            profile_json=profile_json,
        )
        self.repository.delete_user_ksa_drill_attempt(
            user_id=user_id,
            attempt_id=drill_attempt_id,
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

    def _build_outgoing_map(self, definition: CourseDefinition) -> dict[str, list[str]]:
        mapping: dict[str, list[str]] = {node.id: [] for node in definition.nodes}
        for edge in definition.edges:
            mapping.setdefault(edge.from_node_id, []).append(edge.to_node_id)
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

    def _collect_boundary_window(
        self,
        *,
        definition: CourseDefinition,
        node: CourseNodeDefinition,
        boundary_types: set[str],
        include_current: bool = True,
    ) -> tuple[list[str], list[str]]:
        parents = self._build_hard_prev_map(definition)
        node_by_id = {item.id: item for item in definition.nodes}
        window: list[str] = [node.id] if include_current else []
        boundaries: list[str] = []
        seen = {node.id}
        stack = list(parents.get(node.id, set()))
        while stack:
            parent_id = stack.pop()
            if parent_id in seen:
                continue
            seen.add(parent_id)
            parent_node = node_by_id.get(parent_id)
            if parent_node and parent_node.type in boundary_types:
                boundaries.append(parent_id)
                continue
            window.append(parent_id)
            stack.extend(list(parents.get(parent_id, set())))
        return window, sorted(set(boundaries))

    def _practice_source_window(self, *, definition: CourseDefinition, node: CourseNodeDefinition) -> list[str]:
        node_by_id = {item.id: item for item in definition.nodes}
        ancestors = self._collect_ancestors(definition=definition, node_id=node.id)
        return [item for item in ancestors if node_by_id.get(item) and node_by_id[item].type in {"learning_unit", "quiz"}]

    def _checkpoint_source_window(self, *, definition: CourseDefinition, node: CourseNodeDefinition) -> list[str]:
        window, _ = self._collect_boundary_window(
            definition=definition,
            node=node,
            boundary_types=CHECKPOINT_BOUNDARY_NODE_TYPES,
            include_current=True,
        )
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
        window, _ = self._collect_boundary_window(
            definition=definition,
            node=node,
            boundary_types=REVIEW_BOUNDARY_NODE_TYPES,
            include_current=False,
        )
        return window

    def _direct_neighbor_nodes(
        self,
        *,
        definition: CourseDefinition,
        node: CourseNodeDefinition,
    ) -> tuple[list[CourseNodeDefinition], list[CourseNodeDefinition]]:
        hard_prev = self._build_hard_prev_map(definition)
        outgoing = self._build_outgoing_map(definition)
        node_by_id = {item.id: item for item in definition.nodes}
        previous = [node_by_id[item_id] for item_id in sorted(hard_prev.get(node.id, set())) if item_id in node_by_id]
        nxt = [node_by_id[item_id] for item_id in sorted(set(outgoing.get(node.id, []))) if item_id in node_by_id]
        return previous, nxt

    def _node_topic_snapshot(self, node: CourseNodeDefinition) -> dict[str, Any]:
        topics = _norm_list(node.metadata.get("topics"))
        goals = _norm_list(node.metadata.get("goals"))
        concepts = _norm_list(node.metadata.get("concepts"))
        ksa_links = [item.model_dump() for item in node.ksa]
        return {
            "node_id": node.id,
            "node_title": node.title,
            "node_type": node.type,
            "topics": topics,
            "goals": goals,
            "concepts": concepts,
            "ksa_links": ksa_links,
            "difficulty": str(node.metadata.get("difficulty") or node.metadata.get("difficulty_level") or ""),
            "description": str(node.description or ""),
        }

    def _topic_tokenize(self, values: list[str]) -> set[str]:
        out: set[str] = set()
        for raw in values:
            text = str(raw or "").strip().lower().replace("/", " ").replace("_", " ")
            for token in re.split(r"[^a-z0-9]+", text):
                token = token.strip()
                if len(token) >= 3:
                    out.add(token)
        return out

    def _extract_drill_signals(self, *, user: UserAccount, topic_tokens: set[str], limit: int = 40) -> dict[str, Any]:
        attempts = list(self.repository.list_user_ksa_drill_attempts(user_id=user.id, limit=limit) or [])
        related: list[dict[str, Any]] = []
        for item in attempts:
            result_json = dict(getattr(item, "result_json", {}) or {})
            score = _to_float(result_json.get("overall_score"), -1.0)
            topic_keys = [str(x).strip().lower() for x in list(result_json.get("selected_topic_keys") or []) if str(x).strip()]
            topic_blob = " ".join(topic_keys)
            if topic_tokens and not any(token in topic_blob for token in topic_tokens):
                continue
            related.append(
                {
                    "attempt_id": str(getattr(item, "id", "")),
                    "status": str(getattr(item, "status", "")),
                    "selected_topic_keys": topic_keys[:20],
                    "overall_score": None if score < 0 else round(score, 4),
                    "completed_at": str(getattr(item, "completed_at", "") or ""),
                }
            )
        scores = [float(x["overall_score"]) for x in related if x.get("overall_score") is not None]
        return {
            "related_attempts_count": len(related),
            "average_related_score": round(sum(scores) / float(len(scores) or 1), 4) if scores else None,
            "recent_related_attempts": related[:8],
        }

    def _collect_ksa_levels(self, *, profile_json: dict[str, Any], topics: list[str]) -> list[dict[str, Any]]:
        tokens = self._topic_tokenize(topics)
        levels: list[dict[str, Any]] = []
        for section in ("knowledge", "skills", "abilities"):
            source = dict(profile_json.get(section) or {})
            for key, value in source.items():
                text = str(key).replace("_", " ").lower()
                if tokens and not any(token in text for token in tokens):
                    continue
                levels.append(
                    {
                        "group": section,
                        "topic": str(key),
                        "level": round(_to_float(value, 0.0), 4),
                    }
                )
        return levels

    def _derive_topic_strengths(
        self,
        *,
        levels: list[dict[str, Any]],
        target_topics: list[str],
        previous_topics: list[str],
    ) -> dict[str, Any]:
        sorted_levels = sorted(levels, key=lambda item: float(item.get("level") or 0.0), reverse=True)
        strong = sorted_levels[:6]
        weak = sorted(sorted_levels, key=lambda item: float(item.get("level") or 0.0))[:6]
        bridge = [
            str(item.get("topic") or "").replace("_", " ")
            for item in strong
            if str(item.get("topic") or "").strip()
        ][:5]
        risk = [
            str(item.get("topic") or "").replace("_", " ")
            for item in weak
            if str(item.get("topic") or "").strip()
        ][:5]
        if not bridge:
            bridge = _first_items(previous_topics, target_topics, limit=5)
        if not risk:
            risk = _first_items(target_topics, limit=5)
        return {
            "strong_topics_for_bridging": bridge,
            "weak_topics_for_scaffolding": risk,
            "topic_level_snapshot": sorted_levels[:20],
        }

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
        if node.type == "learning_unit":
            return self._build_learning_unit_package(
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
        _, boundary_nodes = self._collect_boundary_window(
            definition=definition,
            node=node,
            boundary_types=REVIEW_BOUNDARY_NODE_TYPES,
            include_current=False,
        )
        topics = self._topic_candidates_from_nodes(definition=definition, node_ids=source_window, node_context=node_context)
        node_by_id = {item.id: item for item in definition.nodes}
        scope_nodes = [node_by_id[item_id] for item_id in source_window if item_id in node_by_id]
        learning_unit_nodes = [item for item in scope_nodes if item.type == "learning_unit"]
        difficulty_profile = self._build_difficulty_profile(
            user=user,
            node=node,
            learning_path=learning_path,
            node_context=node_context,
            source_node_window=source_window,
        )
        profile = self.repository.get_user_ksa_profile(user.id)
        profile_json = dict(profile.profile_json or {}) if profile else {}
        topic_tokens = self._topic_tokenize(topics)
        drill_signals = self._extract_drill_signals(user=user, topic_tokens=topic_tokens)
        level_snapshot = self._collect_ksa_levels(profile_json=profile_json, topics=topics)
        strengths = self._derive_topic_strengths(levels=level_snapshot, target_topics=topics, previous_topics=topics)
        topic_agg_prompt = self._load_prompt(
            "learning-node-review-topic-aggregation.md",
            "Return strict JSON object with grouped_topics (array) and key_themes (array). "
            "Each grouped_topics item must include topic, importance(high|medium|low), source_node_ids(array), related_ksa(array), reinforcement_priority(0..1)."
        )
        topic_payload = {
            "course": {"id": learning_path.id, "subject": learning_path.subject, "difficulty": learning_path.difficulty_level},
            "node": {"id": node.id, "title": node.title, "description": node.description, "metadata": dict(node.metadata or {})},
            "source_node_window": source_window,
            "boundary_nodes": boundary_nodes,
            "scope_nodes": [self._node_topic_snapshot(item) for item in scope_nodes],
            "learning_unit_scope_nodes": [self._node_topic_snapshot(item) for item in learning_unit_nodes],
            "topics": topics,
            "difficulty_profile": difficulty_profile,
            "ksa_context": dict(node_context.get("ksa_context") or {}),
            "drill_signals": drill_signals,
            "topic_strengths": strengths,
        }
        topic_aggregation: dict[str, Any] = {}
        try:
            raw = self.llm_invoke([("system", topic_agg_prompt), ("user", json.dumps(topic_payload, ensure_ascii=False))])
            topic_aggregation = _extract_json_object(raw)
        except Exception:
            grouped = []
            for idx, topic in enumerate(_first_items(topics, limit=18), start=1):
                grouped.append(
                    {
                        "topic": topic,
                        "importance": "high" if idx <= 6 else ("medium" if idx <= 12 else "low"),
                        "source_node_ids": source_window[:4],
                        "related_ksa": [],
                        "reinforcement_priority": 0.8 if idx <= 6 else 0.5,
                    }
                )
            topic_aggregation = {
                "grouped_topics": grouped,
                "key_themes": _first_items(topics, limit=8),
            }

        recap_prompt = self._load_prompt(
            "learning-node-review-recap-plan-generation.md",
            "Return strict JSON object with recap_goal, content_aware_recap_summary, recap_steps(array), key_takeaways(array), likely_questions(array). "
            "Each recap_steps item includes step_id,title,focus_topics(array),brief,goal,interaction_hooks(array)."
        )
        recap_payload = {
            "course": {"id": learning_path.id, "title": learning_path.title, "subject": learning_path.subject},
            "node": {"id": node.id, "title": node.title, "description": node.description},
            "topic_aggregation": topic_aggregation,
            "difficulty_profile": difficulty_profile,
            "strengths": strengths,
            "drill_signals": drill_signals,
        }
        recap_plan: dict[str, Any] = {}
        try:
            raw = self.llm_invoke([("system", recap_prompt), ("user", json.dumps(recap_payload, ensure_ascii=False))])
            recap_plan = _extract_json_object(raw)
        except Exception:
            grouped_topics = [dict(item) for item in list(topic_aggregation.get("grouped_topics") or []) if isinstance(item, dict)]
            focus_topics = [str(item.get("topic") or "").strip() for item in grouped_topics if str(item.get("topic") or "").strip()]
            recap_plan = {
                "recap_goal": "Consolidate core topics and prepare for upcoming validations.",
                "content_aware_recap_summary": {
                    "what_was_learned": _first_items(focus_topics, limit=8),
                    "what_to_reinforce": _first_items(strengths.get("weak_topics_for_scaffolding") or [], focus_topics, limit=6),
                    "upcoming_validation_preparation": list(node_context.get("next_node_context", {}).get("upcoming_validation_node_ids") or []),
                },
                "recap_steps": [
                    {
                        "step_id": "review-intro",
                        "title": "Review Introduction",
                        "focus_topics": _first_items(focus_topics, limit=4),
                        "brief": "Reconnect major concepts and establish recap objectives.",
                        "goal": "Orientation",
                        "interaction_hooks": ["questions", "reclarification_request"],
                    },
                    {
                        "step_id": "review-reinforcement",
                        "title": "Targeted Reinforcement",
                        "focus_topics": _first_items(strengths.get("weak_topics_for_scaffolding") or [], focus_topics, limit=6),
                        "brief": "Reinforce weak points and connect them to stronger known areas.",
                        "goal": "Remediation",
                        "interaction_hooks": ["questions", "feedback_rating"],
                    },
                    {
                        "step_id": "review-close",
                        "title": "Review Summary",
                        "focus_topics": _first_items(focus_topics, limit=5),
                        "brief": "Summarize and prepare for next assessment-oriented nodes.",
                        "goal": "Readiness",
                        "interaction_hooks": ["questions", "feedback_rating", "reclarification_request"],
                    },
                ],
                "key_takeaways": _first_items(focus_topics, limit=7),
                "likely_questions": _first_items(focus_topics, limit=4),
            }

        grouped_topics = [dict(item) for item in list(topic_aggregation.get("grouped_topics") or []) if isinstance(item, dict)]
        review_scope_summary = {
            "included_node_ids": source_window,
            "boundary_node_ids": boundary_nodes,
            "included_learning_unit_node_ids": [item.id for item in learning_unit_nodes],
            "why_included": "Backward hard-dependency traversal until last review/checkpoint/milestone/unlock_gate boundaries.",
            "key_themes": list(topic_aggregation.get("key_themes") or []),
        }
        interaction_hooks = {
            "supports_questions": True,
            "supports_recap_feedback_rating": True,
            "supports_reclarification_requests": True,
        }
        return {
            "node_type": "review",
            "difficulty_profile": difficulty_profile,
            "source_node_window": source_window,
            "important_topics": topics[:32],
            "review_scope_summary": review_scope_summary,
            "topic_aggregation": {
                "grouped_topics": grouped_topics,
                "learning_unit_emphasis_topics": _first_items(
                    [str(item.get("topic") or "") for item in grouped_topics if isinstance(item, dict)],
                    limit=12,
                ),
            },
            "content_aware_recap_summary": dict(recap_plan.get("content_aware_recap_summary") or {}),
            "recap_goal": str(recap_plan.get("recap_goal") or "").strip(),
            "recap_structure": {
                "introduction": {
                    "title": "Review Introduction",
                    "brief": "Set review scope and expected outcomes.",
                },
                "mini_recaps": [dict(item) for item in list(recap_plan.get("recap_steps") or []) if isinstance(item, dict)],
                "summary": {
                    "key_takeaways": list(recap_plan.get("key_takeaways") or []),
                    "likely_questions": list(recap_plan.get("likely_questions") or []),
                },
            },
            "interaction_hooks": interaction_hooks,
            "drill_signals": drill_signals,
            "topic_strengths": strengths,
            "review_pass_threshold": float(node.metadata.get("review_pass_threshold") or 0.6),
            "review_mode": "structured_recap_plan",
        }

    def _build_learning_unit_package(
        self,
        *,
        user: UserAccount,
        learning_path: LearningPath,
        definition: CourseDefinition,
        node: CourseNodeDefinition,
        node_context: dict[str, Any],
    ) -> dict[str, Any]:
        previous_nodes, next_nodes = self._direct_neighbor_nodes(definition=definition, node=node)
        target_snapshot = self._node_topic_snapshot(node)
        previous_snapshots = [self._node_topic_snapshot(item) for item in previous_nodes]
        next_snapshots = [self._node_topic_snapshot(item) for item in next_nodes]

        previous_topics = _first_items(*[list(item.get("topics") or []) for item in previous_snapshots], limit=20)
        target_topics = _first_items(
            list(target_snapshot.get("topics") or []),
            list(target_snapshot.get("goals") or []),
            list(target_snapshot.get("concepts") or []),
            limit=24,
        )
        next_topics = _first_items(*[list(item.get("topics") or []) for item in next_snapshots], limit=20)

        source_window = _first_items(
            [item.id for item in previous_nodes],
            [node.id],
            [item.id for item in next_nodes],
            limit=24,
        )
        difficulty_profile = self._build_difficulty_profile(
            user=user,
            node=node,
            learning_path=learning_path,
            node_context=node_context,
            source_node_window=source_window,
        )
        profile = self.repository.get_user_ksa_profile(user.id)
        profile_json = dict(profile.profile_json or {}) if profile else {}
        topic_tokens = self._topic_tokenize(previous_topics + target_topics + next_topics)
        drill_signals = self._extract_drill_signals(user=user, topic_tokens=topic_tokens)
        level_snapshot = self._collect_ksa_levels(profile_json=profile_json, topics=target_topics + previous_topics + next_topics)
        strengths = self._derive_topic_strengths(
            levels=level_snapshot,
            target_topics=target_topics,
            previous_topics=previous_topics,
        )
        personalization = self.repository.get_user_learning_personalization_layers(user_id=user.id)
        personalization_snapshot = {
            "resolved_declared_tutor_rules": dict(getattr(personalization, "resolved_declared_tutor_rules", {}) or {}),
            "resolved_diagnostic_rules": dict(getattr(personalization, "resolved_diagnostic_rules", {}) or {}),
            "resolved_live_adaptation_rules": dict(getattr(personalization, "resolved_live_adaptation_rules", {}) or {}),
        }

        topic_prompt = self._load_prompt(
            "learning-node-learning-unit-topic-extraction.md",
            "Return strict JSON object with mini_topics(array). Each item includes title, focus, objective, related_target_topics(array), estimated_complexity(low|medium|high), ksa_links(array), likely_difficulty_points(array)."
        )
        topic_payload = {
            "course": {"id": learning_path.id, "title": learning_path.title, "subject": learning_path.subject},
            "node": target_snapshot,
            "previous_nodes": previous_snapshots,
            "next_nodes": next_snapshots,
            "target_topics": target_topics,
            "difficulty_profile": difficulty_profile,
            "topic_strengths": strengths,
            "drill_signals": drill_signals,
        }
        mini_topic_plan: dict[str, Any] = {}
        try:
            raw = self.llm_invoke([("system", topic_prompt), ("user", json.dumps(topic_payload, ensure_ascii=False))])
            mini_topic_plan = _extract_json_object(raw)
        except Exception:
            mini_topics = []
            for idx, topic in enumerate(_first_items(target_topics, limit=6), start=1):
                mini_topics.append(
                    {
                        "title": f"Mini Topic {idx}: {topic}",
                        "focus": topic,
                        "objective": f"Understand and apply {topic} confidently.",
                        "related_target_topics": [topic],
                        "estimated_complexity": "medium",
                        "ksa_links": list(target_snapshot.get("ksa_links") or [])[:3],
                        "likely_difficulty_points": _first_items(strengths.get("weak_topics_for_scaffolding") or [], [topic], limit=3),
                    }
                )
            mini_topic_plan = {"mini_topics": mini_topics}

        niveau_prompt = self._load_prompt(
            "learning-node-learning-unit-niveau-estimation.md",
            "Return strict JSON object with estimated_level, confidence_0_1, rationale, assumed_known_topics(array), likely_gaps(array), support_intensity(low|medium|high), abstraction_level(concrete|balanced|abstract)."
        )
        niveau_payload = {
            "difficulty_profile": difficulty_profile,
            "target_topics": target_topics,
            "topic_strengths": strengths,
            "drill_signals": drill_signals,
            "personalization_snapshot": personalization_snapshot,
            "prior_completion_ratio": dict(node_context.get("prior_node_context") or {}).get("prior_required_completion_ratio"),
        }
        niveau: dict[str, Any] = {}
        try:
            raw = self.llm_invoke([("system", niveau_prompt), ("user", json.dumps(niveau_payload, ensure_ascii=False))])
            niveau = _extract_json_object(raw)
        except Exception:
            niveau = {
                "estimated_level": "intermediate",
                "confidence_0_1": 0.68,
                "rationale": "Derived from KSA profile, related drill outcomes, and node difficulty.",
                "assumed_known_topics": _first_items(previous_topics, strengths.get("strong_topics_for_bridging") or [], limit=6),
                "likely_gaps": _first_items(strengths.get("weak_topics_for_scaffolding") or [], target_topics, limit=6),
                "support_intensity": "medium",
                "abstraction_level": "balanced",
            }

        lesson_prompt = self._load_prompt(
            "learning-node-learning-unit-lesson-plan-generation.md",
            "Return strict JSON object with node_structure_preview, lesson_steps(array), recap_plan, and interaction_hooks. "
            "lesson_steps items include mini_topic_title, intro_brief, lesson_goal, explanation_requirements(array), explanation_constraints(array), teaching_brief, prior_assumptions(array), expected_difficulty_points(array), ksa_links(array), style_hints(array)."
        )
        lesson_payload = {
            "course": {"id": learning_path.id, "title": learning_path.title, "subject": learning_path.subject},
            "node": target_snapshot,
            "mini_topics": list(mini_topic_plan.get("mini_topics") or []),
            "niveau": niveau,
            "difficulty_profile": difficulty_profile,
            "topic_strengths": strengths,
            "previous_topics": previous_topics,
            "target_topics": target_topics,
            "next_topics": next_topics,
            "personalization_snapshot": personalization_snapshot,
        }
        lesson_plan: dict[str, Any] = {}
        try:
            raw = self.llm_invoke([("system", lesson_prompt), ("user", json.dumps(lesson_payload, ensure_ascii=False))])
            lesson_plan = _extract_json_object(raw)
        except Exception:
            mini_topics = [dict(item) for item in list(mini_topic_plan.get("mini_topics") or []) if isinstance(item, dict)]
            lessons = []
            for idx, mini in enumerate(mini_topics, start=1):
                title = str(mini.get("title") or f"Mini Topic {idx}").strip()
                lessons.append(
                    {
                        "step_id": f"mini-topic-{idx}",
                        "mini_topic_title": title,
                        "intro_brief": str(mini.get("focus") or ""),
                        "lesson_goal": str(mini.get("objective") or ""),
                        "explanation_requirements": ["clear_definition", "practical_example", "bridge_to_known_topic"],
                        "explanation_constraints": ["avoid_full-depth-dump", "keep_focus_on_target_topic"],
                        "teaching_brief": f"Teach {title} using concise, scaffolded explanation with bridge analogies.",
                        "prior_assumptions": _first_items(previous_topics, limit=3),
                        "expected_difficulty_points": _first_items(
                            list(mini.get("likely_difficulty_points") or []),
                            strengths.get("weak_topics_for_scaffolding") or [],
                            limit=4,
                        ),
                        "ksa_links": list(mini.get("ksa_links") or [])[:4],
                        "style_hints": ["stepwise", "example-driven", "confirm-understanding"],
                    }
                )
            lesson_plan = {
                "node_structure_preview": {
                    "phases": [
                        "phase_1_intro",
                        "phase_2_niveau_confirmation",
                        "phase_3_self_explanation",
                        "phase_4_structure_preview",
                        "phase_5_mini_topic_lessons",
                        "phase_6_node_recap",
                    ]
                },
                "lesson_steps": lessons,
                "recap_plan": {
                    "recap_goals": ["consolidate_core_topics", "prepare_for_next_topics"],
                    "key_topics_to_summarize": _first_items(target_topics, limit=8),
                    "most_important_takeaways": _first_items(target_topics, strengths.get("strong_topics_for_bridging") or [], limit=6),
                    "likely_questions": _first_items(target_topics, next_topics, limit=4),
                },
                "interaction_hooks": {
                    "supports_questions_per_lesson": True,
                    "supports_explanation_rating": True,
                    "supports_reexplanation_request": True,
                    "supports_node_feedback": True,
                },
            }

        lesson_steps = [dict(item) for item in list(lesson_plan.get("lesson_steps") or []) if isinstance(item, dict)]
        if not lesson_steps:
            mini_topics = [dict(item) for item in list(mini_topic_plan.get("mini_topics") or []) if isinstance(item, dict)]
            for idx, mini in enumerate(mini_topics, start=1):
                lesson_steps.append(
                    {
                        "step_id": f"mini-topic-{idx}",
                        "mini_topic_title": str(mini.get("title") or f"Mini Topic {idx}").strip(),
                        "intro_brief": str(mini.get("focus") or "").strip(),
                        "lesson_goal": str(mini.get("objective") or "").strip(),
                        "explanation_requirements": ["clear_definition", "practical_example", "check_understanding"],
                        "explanation_constraints": ["avoid_overload", "stay_topic_scoped"],
                        "teaching_brief": f"Teach {str(mini.get('title') or f'Mini Topic {idx}')}.",
                        "prior_assumptions": _first_items(previous_topics, limit=3),
                        "expected_difficulty_points": _first_items(
                            list(mini.get("likely_difficulty_points") or []),
                            strengths.get("weak_topics_for_scaffolding") or [],
                            limit=4,
                        ),
                        "ksa_links": list(mini.get("ksa_links") or [])[:4],
                        "style_hints": ["stepwise", "example-driven"],
                    }
                )
            lesson_plan["lesson_steps"] = lesson_steps

        context_summary = {
            "course_summary": {
                "course_id": learning_path.id,
                "course_title": learning_path.title,
                "course_subject": learning_path.subject,
                "course_goal_hint": str(learning_path.description or ""),
                "branch_context": dict(node_context.get("chapter_branch_context") or {}),
            },
            "previous_node_topics": previous_snapshots,
            "target_node_topics": target_snapshot,
            "next_node_topics": next_snapshots,
            "relevant_ksa_state": {
                "topic_level_snapshot": strengths.get("topic_level_snapshot") or [],
                "drill_signals": drill_signals,
            },
            "related_strong_topics": list(strengths.get("strong_topics_for_bridging") or []),
            "related_weak_topics": list(strengths.get("weak_topics_for_scaffolding") or []),
        }
        learner_niveau_hypothesis = {
            "estimated_level": str(niveau.get("estimated_level") or "intermediate"),
            "confidence_0_1": _to_float(niveau.get("confidence_0_1"), 0.65),
            "rationale": str(niveau.get("rationale") or ""),
            "assumed_known_topics": _norm_list(niveau.get("assumed_known_topics")),
            "likely_gaps": _norm_list(niveau.get("likely_gaps")),
            "support_intensity": str(niveau.get("support_intensity") or "medium"),
            "abstraction_level": str(niveau.get("abstraction_level") or "balanced"),
        }

        phase_flow = {
            "phase_1_introduction": {
                "title": "Introduction to node and topics",
                "tasks": [
                    "introduce_node_scope",
                    "frame_course_relevance",
                    "list_target_topics",
                ],
            },
            "phase_2_niveau_estimation": {
                "title": "Show estimated learner niveau",
                "tasks": ["show_estimated_level", "allow_confirm_or_edit"],
                "user_confirmable_self_positioning_step": {
                    "prompt": "Does this estimated level match your current comfort? You can confirm or adjust.",
                    "response_key": "niveau_self_positioning",
                },
            },
            "phase_3_user_self_explanation": {
                "title": "Ask user for high-level explanation",
                "tasks": ["high_level_topic_explanation", "why_topic_matters_explanation"],
                "response_keys": ["user_high_level_explanation", "user_importance_explanation"],
            },
            "phase_4_structure_preview": {
                "title": "Show planned structure",
                "tasks": ["display_node_structure_preview", "preview_mini_topic_lesson_steps"],
                "node_structure_preview": dict(lesson_plan.get("node_structure_preview") or {}),
            },
            "phase_5_mini_topic_lessons": {
                "title": "Mini-topic lessons",
                "lessons": lesson_steps,
            },
            "phase_6_node_recap": {
                "title": "Node recap",
                "recap_plan": dict(lesson_plan.get("recap_plan") or {}),
                "tasks": ["summarize_core_topics", "open_questions", "collect_node_feedback"],
            },
        }

        interaction_hooks = dict(lesson_plan.get("interaction_hooks") or {})
        if not interaction_hooks:
            interaction_hooks = {
                "supports_questions_per_lesson": True,
                "supports_explanation_rating": True,
                "supports_reexplanation_request": True,
                "supports_node_feedback": True,
            }
        return {
            "node_type": "learning_unit",
            "difficulty_profile": difficulty_profile,
            "source_node_window": source_window,
            "context_summary": context_summary,
            "learner_niveau_hypothesis": learner_niveau_hypothesis,
            "user_confirmable_self_positioning_step": phase_flow["phase_2_niveau_estimation"]["user_confirmable_self_positioning_step"],
            "topic_self_explanation_step": {
                "prompt_high_level": "Please explain this topic in your own words at a high level.",
                "prompt_why_it_matters": "Why does this topic matter in real usage?",
            },
            "node_structure_preview": dict(lesson_plan.get("node_structure_preview") or {}),
            "mini_topic_lessons": lesson_steps,
            "recap_plan": dict(lesson_plan.get("recap_plan") or {}),
            "interaction_hooks": interaction_hooks,
            "phase_flow": phase_flow,
            "drill_signals": drill_signals,
            "topic_strengths": strengths,
            "personalization_snapshot": personalization_snapshot,
            "runtime_plan_mode": "structured_plan_only",
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
        review_mode = str(package.get("review_mode") or "")
        if review_mode == "structured_recap_plan":
            recap_feedback = str(dict(responses.get("node_feedback") or {}).get("text") or responses.get("recap_feedback") or "").strip()
            rating_raw = dict(responses.get("node_feedback") or {}).get("rating") or responses.get("recap_rating")
            rating = _to_float(rating_raw, 0.0)
            asked_questions = list(responses.get("questions") or [])
            viewed_steps = list(dict(responses.get("phase_progress") or {}).keys())
            required_steps = [
                "phase_1_introduction",
                "phase_2_grouped_recaps",
                "phase_3_summary_and_feedback",
            ]
            completion_ratio = float(len([step for step in viewed_steps if step in required_steps])) / float(len(required_steps) or 1)
            engagement_score = min(
                1.0,
                (completion_ratio * 0.55)
                + (0.25 if recap_feedback else 0.0)
                + (0.10 if asked_questions else 0.0)
                + (min(5.0, max(0.0, rating)) / 5.0 * 0.10),
            )
            threshold = float(package.get("review_pass_threshold") or 0.6)
            passed = engagement_score >= threshold
            return {
                "evaluation_type": "review",
                "review_mode": review_mode,
                "required_steps": required_steps,
                "viewed_steps": viewed_steps,
                "questions_count": len(asked_questions),
                "feedback_present": bool(recap_feedback),
                "rating": rating if rating > 0 else None,
                "overall_score": round(engagement_score, 4),
                "pass_threshold": threshold,
                "passed": passed,
            }

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

    def _evaluate_learning_unit(self, *, responses: dict[str, Any], package: dict[str, Any]) -> dict[str, Any]:
        phase_flow = dict(package.get("phase_flow") or {})
        phase_progress = dict(responses.get("phase_progress") or {})
        completed_steps = [key for key in phase_progress.keys() if key in phase_flow]
        required_phases = [
            "phase_1_introduction",
            "phase_2_niveau_estimation",
            "phase_3_user_self_explanation",
            "phase_4_structure_preview",
            "phase_5_mini_topic_lessons",
            "phase_6_node_recap",
        ]
        completed_required = [step for step in required_phases if step in completed_steps]
        ratio = float(len(completed_required)) / float(len(required_phases) or 1)
        niveau_response = dict(responses.get("niveau_self_positioning") or {})
        self_expl = str(responses.get("user_high_level_explanation") or "").strip()
        importance = str(responses.get("user_importance_explanation") or "").strip()
        hooks = dict(responses.get("interaction_feedback") or {})

        signal_bonus = 0.0
        if niveau_response:
            signal_bonus += 0.1
        if self_expl:
            signal_bonus += 0.1
        if importance:
            signal_bonus += 0.1
        if hooks:
            signal_bonus += 0.05
        overall = min(1.0, ratio * 0.65 + signal_bonus)
        threshold = float(package.get("learning_unit_complete_threshold") or 0.6)
        passed = overall >= threshold
        return {
            "evaluation_type": "learning_unit",
            "required_phases": required_phases,
            "completed_phases": completed_required,
            "phase_completion_ratio": round(ratio, 4),
            "niveau_self_positioning_present": bool(niveau_response),
            "self_explanation_present": bool(self_expl),
            "importance_explanation_present": bool(importance),
            "interaction_feedback_present": bool(hooks),
            "overall_score": round(overall, 4),
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
