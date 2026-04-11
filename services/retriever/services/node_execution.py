from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from services.common.models import LearningPath, UserAccount
from services.retriever.repositories.chat_repository import ChatRepository
from services.retriever.services.course_files import CourseDefinition, CourseNodeDefinition
from services.retriever.services.course_skilltree import COMPLETED_STATES, build_skilltree_runtime
from services.retriever.services.ksa_drills import evaluate_drill_attempt, generate_round_archetypes
from services.retriever.services.node_context import DIMENSION_GROUP


BOUNDARY_NODE_TYPES = {"quiz", "practice", "checkpoint", "milestone", "unlock_gate"}


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


class LearningNodeExecutionService:
    def __init__(
        self,
        repository: ChatRepository,
        *,
        llm_invoke: Callable[[list[tuple[str, str]]], str],
    ) -> None:
        self.repository = repository
        self.llm_invoke = llm_invoke

    def start(
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
        if current_state not in {"available", "in_progress", "failed_needs_retry"}:
            raise ValueError("Node is not startable in its current state")

        now = datetime.now(timezone.utc)
        self.repository.upsert_user_learning_node_progress(
            user_id=user.id,
            learning_path_id=learning_path.id,
            node_id=node.id,
            status="in_progress",
            started_at=now,
            completed_at=None,
        )

        if node.type == "assessment_hook":
            package = self._build_assessment_hook_package(
                user=user,
                learning_path=learning_path,
                definition=definition,
                node=node,
                node_context=node_context,
            )
        elif node.type == "quiz":
            package = self._build_quiz_package(
                user=user,
                learning_path=learning_path,
                definition=definition,
                node=node,
                node_context=node_context,
            )
        elif node.type == "unlock_gate":
            checks = self._check_unlock_gate_requirements(
                user=user,
                definition=definition,
                node=node,
                progress_map=progress_map,
                node_context=node_context,
            )
            package = {"node_type": "unlock_gate", "requirements": checks}
        elif node.type == "milestone":
            checks = self._check_milestone_requirements(
                definition=definition,
                node=node,
                progress_map=progress_map,
            )
            package = {"node_type": "milestone", "requirements": checks}
        else:
            raise ValueError(f"Node type '{node.type}' is not supported in this execution step")

        source_node_window = list(package.get("source_node_window") or [])
        attempt = self.repository.create_user_learning_node_execution_attempt(
            {
                "user_id": user.id,
                "learning_path_id": learning_path.id,
                "node_id": node.id,
                "node_type": node.type,
                "status": "in_progress",
                "generation_reason": "on_start",
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
        merged.update(dict(responses or {}))
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
            result_json = self._evaluate_assessment_hook(
                user=user,
                responses=responses,
                package=package,
            )
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
            result_json = self._evaluate_quiz(
                user=user,
                responses=responses,
                package=package,
            )
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
                progress_map={entry.node_id: entry.status for entry in self.repository.list_user_learning_node_progress(user_id=user.id, learning_path_id=learning_path.id)},
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
                progress_map={entry.node_id: entry.status for entry in self.repository.list_user_learning_node_progress(user_id=user.id, learning_path_id=learning_path.id)},
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
        topic_prompt = (
            "Return strict JSON with key topics (array, length 8..16). "
            "Each topic item must include label, related_node_ids (array), related_ksa (object with dimension/topic/subtopic), why. "
            "Use complementary angles suitable for reverse definition, spot the flaw, power sprint, analogy match."
        )
        payload = {
            "course": {"id": learning_path.id, "title": learning_path.title, "subject": learning_path.subject},
            "node": {"id": node.id, "title": node.title, "description": node.description, "ksa": [item.model_dump() for item in node.ksa]},
            "seed_topics": seed_topics,
            "prior_completed_nodes": list(prior.get("completed_relevant_nodes") or []),
            "ksa_topic_states": list(ksa_context.get("topic_states") or []),
            "rules": [
                "8 to 16 topics",
                "specific and assessment-ready",
                "avoid duplicates",
                "connected to prior nodes and KSA context",
            ],
        }
        topics: list[dict[str, Any]] = []
        try:
            raw = self.llm_invoke(
                [("system", topic_prompt), ("user", json.dumps(payload, ensure_ascii=False))]
            )
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
        selected_topic_keys = sorted({str(item.get("topic_key") or "") for item in list(generated.get("question_set") or []) if str(item.get("topic_key") or "").strip()})
        return {
            "node_type": "assessment_hook",
            "generated_topics": topics,
            "rounds": list(generated.get("rounds") or []),
            "question_set": list(generated.get("question_set") or []),
            "selected_topic_keys": selected_topic_keys,
            "required_round_count": len(rounds),
            "source_node_window": [str(node.id)],
        }

    def _build_hard_prev_map(self, definition: CourseDefinition) -> dict[str, set[str]]:
        mapping: dict[str, set[str]] = {node.id: set() for node in definition.nodes}
        for edge in definition.edges:
            if edge.relationship in {"requires_all", "requires_any"}:
                mapping.setdefault(edge.to_node_id, set()).add(edge.from_node_id)
        for node in definition.nodes:
            mapping.setdefault(node.id, set()).update(node.prerequisites.requires_all)
            mapping.setdefault(node.id, set()).update(node.prerequisites.requires_any)
        return mapping

    def _quiz_source_window(self, *, definition: CourseDefinition, node: CourseNodeDefinition) -> list[str]:
        parents = self._build_hard_prev_map(definition)
        window: list[str] = [node.id]
        seen = {node.id}
        stack = list(parents.get(node.id, set()))
        while stack:
            parent_id = stack.pop()
            if parent_id in seen:
                continue
            seen.add(parent_id)
            window.append(parent_id)
            parent_node = next((item for item in definition.nodes if item.id == parent_id), None)
            if parent_node and parent_node.type in BOUNDARY_NODE_TYPES:
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
        topics = []
        for item in window_nodes:
            topics.extend(_norm_list(item.metadata.get("topics")))
            for ksa_item in item.ksa:
                topics.append(f"{ksa_item.topic}:{ksa_item.subtopic or ''}".strip(":"))
        topics = _first_items(topics, _norm_list(dict(node_context.get("prior_node_context") or {}).get("prior_topic_summary")), limit=30)
        quiz_prompt = (
            "Return strict JSON with mc_questions (exactly 12), free_text_questions (exactly 2), deep_dive_topics (exactly 3). "
            "Each mc question: id, type(single|multiple), question, options(>=3), correct_answers(1..n), topic, explanation. "
            "Each free text: id, question, topic, rubric(3..6 short criteria). "
            "Each deep dive topic: label, big_map_group(Knowledge|Skills|Abilities), big_map_subdomain, detailed_topic, rationale."
        )
        input_payload = {
            "course": {"id": learning_path.id, "title": learning_path.title, "subject": learning_path.subject},
            "target_node": {"id": node.id, "title": node.title, "description": node.description},
            "window_node_ids": source_window,
            "window_nodes": [
                {"id": item.id, "title": item.title, "description": item.description, "type": item.type, "metadata": dict(item.metadata or {})}
                for item in window_nodes
            ],
            "topics": topics,
            "ksa_context": dict(node_context.get("ksa_context") or {}),
            "difficulty": node.metadata.get("difficulty_level") or learning_path.difficulty_level,
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
        selected_topic_keys = sorted({str(item.get("topic_key") or "") for item in list(generated.get("question_set") or []) if str(item.get("topic_key") or "").strip()})
        return {
            "node_type": "quiz",
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

    def _check_unlock_gate_requirements(
        self,
        *,
        user: UserAccount,
        definition: CourseDefinition,
        node: CourseNodeDefinition,
        progress_map: dict[str, str],
        node_context: dict[str, Any],
    ) -> dict[str, Any]:
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

    def _evaluate_free_text(self, *, questions: list[dict[str, Any]], responses: dict[str, Any]) -> dict[str, Any]:
        answer_map = dict(responses.get("free_text_answers") or {})
        items = []
        scores = []
        for question in questions:
            qid = str(question.get("id") or "")
            answer = str(answer_map.get(qid) or "").strip()
            rubric = [str(item).strip() for item in list(question.get("rubric") or []) if str(item).strip()]
            prompt = (
                "Return strict JSON with score_0_1, depth_0_1, relevance_0_1, feedback, rubric_hits(array). "
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
            except Exception:
                final_score = 0.0 if not answer else 0.4
                feedback = "Fallback evaluation used."
                rubric_hits = []
            scores.append(final_score)
            items.append(
                {
                    "question_id": qid,
                    "score_0_1": round(final_score, 4),
                    "feedback": feedback,
                    "rubric_hits": rubric_hits,
                }
            )
        return {
            "score": round(sum(scores) / float(len(scores) or 1), 4),
            "items": items,
        }

    def _evaluate_quiz(self, *, user: UserAccount, responses: dict[str, Any], package: dict[str, Any]) -> dict[str, Any]:
        mc_questions = [dict(item) for item in list(package.get("mc_questions") or [])]
        mc_eval = self._score_mc_questions(mc_questions=mc_questions, responses=responses)
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
        deep_rounds_required = len(list(package.get("deep_dive_rounds") or []))
        deep_rounds_completed = len(
            {
                int(item.get("block_index") or 0)
                for item in list(package.get("deep_dive_question_set") or [])
                if str(item.get("id") or "") in deep_answers
            }
        )
        deep_score = min(1.0, float(deep_rounds_completed) / float(deep_rounds_required or 1))
        free_text_eval = self._evaluate_free_text(
            questions=[dict(item) for item in list(package.get("free_text_questions") or [])],
            responses=responses,
        )
        overall_score = (mc_eval["score"] * 0.5) + (deep_score * 0.3) + (float(free_text_eval["score"]) * 0.2)
        pass_threshold = float(package.get("pass_threshold") or 0.7)
        return {
            "evaluation_type": "quiz",
            "mc_evaluation": mc_eval,
            "deep_dive_score": round(deep_score, 4),
            "deep_dive_required_rounds": deep_rounds_required,
            "deep_dive_completed_rounds": deep_rounds_completed,
            "free_text_evaluation": free_text_eval,
            "overall_score": round(overall_score, 4),
            "pass_threshold": pass_threshold,
            "passed": bool(overall_score >= pass_threshold),
            "drill_result": dict(drill_outcome.get("result_json") or {}),
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
        progress_entries = self.repository.list_user_learning_node_progress(user_id=user.id, learning_path_id=learning_path.id)
        progress_map = {entry.node_id: entry.status for entry in progress_entries}
        if node.completion_mode == "quiz_pass":
            threshold = float(node.metadata.get("pass_threshold") or 0.7)
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
