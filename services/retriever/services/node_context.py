from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from services.common.models import LearningPath, UserLearningNodeContext
from services.retriever.repositories.chat_repository import ChatRepository
from services.retriever.services.course_files import CourseDefinition, CourseNodeDefinition
from services.retriever.services.course_skilltree import COMPLETED_STATES, SkilltreeRuntime, build_skilltree_runtime


SUPPORTED_NODE_CONTEXT_TYPES = {
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

CHECK_NODE_TYPES = {"quiz", "checkpoint", "unlock_gate", "assessment_hook"}
ACTIVE_OR_COMPLETED_STATES = {"available", "in_progress", "failed_needs_retry", "completed", "mastered"}
DIMENSION_GROUP = {"K": "knowledge", "S": "skills", "A": "abilities"}


def _norm_text(value: object) -> str:
    return str(value or "").strip()


def _as_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [_norm_text(item) for item in value if _norm_text(item)]
    if isinstance(value, str):
        parts = [item.strip() for item in value.replace("\n", ",").split(",")]
        return [item for item in parts if item]
    return []


def _is_effectively_required(definition: CourseDefinition, node: CourseNodeDefinition) -> bool:
    if not node.required:
        return False
    if not node.branch_id:
        return True
    branch = next((item for item in definition.branches if item.id == node.branch_id), None)
    if branch is None:
        return True
    return bool(branch.required)


@dataclass(slots=True)
class _GraphData:
    hard_prev: dict[str, set[str]]
    recommended_prev: dict[str, set[str]]
    optional_prev: dict[str, set[str]]
    outgoing: dict[str, list[tuple[str, str]]]


class LearningNodeContextEngine:
    def __init__(self, repository: ChatRepository) -> None:
        self.repository = repository

    def recompute_for_node(
        self,
        *,
        user_id: int,
        learning_path: LearningPath,
        definition: CourseDefinition,
        node_id: str,
        generation_reason: str,
    ) -> UserLearningNodeContext:
        node_by_id = {node.id: node for node in definition.nodes}
        if node_id not in node_by_id:
            raise ValueError(f"Unknown node_id '{node_id}'")
        node = node_by_id[node_id]
        if node.type not in SUPPORTED_NODE_CONTEXT_TYPES:
            raise ValueError(f"Unsupported node type '{node.type}'")

        progress_entries = self.repository.list_user_learning_node_progress(user_id=user_id, learning_path_id=learning_path.id)
        progress_map = {entry.node_id: entry.status for entry in progress_entries}
        runtime = build_skilltree_runtime(definition, persisted_node_progress=progress_map)
        graph = self._build_graph(definition)

        course_context = self._build_course_context(
            learning_path=learning_path,
            definition=definition,
            runtime=runtime,
            node=node,
        )
        chapter_branch_context = self._build_chapter_branch_context(definition=definition, graph=graph, node=node)
        prior_node_context = self._build_prior_node_context(
            definition=definition,
            graph=graph,
            runtime=runtime,
            node=node,
            progress_map=progress_map,
        )
        target_node_context = self._build_target_node_context(definition=definition, node=node)
        next_node_context = self._build_next_node_context(definition=definition, graph=graph, node=node)
        ksa_context = self._build_ksa_context(
            user_id=user_id,
            learning_path=learning_path,
            definition=definition,
            node=node,
            prior_node_context=prior_node_context,
        )
        readiness_context = self._build_readiness_context(
            learning_path=learning_path,
            node=node,
            prior_node_context=prior_node_context,
            ksa_context=ksa_context,
        )
        derived_assumptions = self._build_derived_assumptions(
            prior_node_context=prior_node_context,
            next_node_context=next_node_context,
            ksa_context=ksa_context,
            readiness_context=readiness_context,
        )

        context_payload = {
            "course_context": course_context,
            "chapter_branch_context": chapter_branch_context,
            "prior_node_context": prior_node_context,
            "target_node_context": target_node_context,
            "next_node_context": next_node_context,
            "ksa_context": ksa_context,
            "readiness_context": readiness_context,
            "derived_assumptions": derived_assumptions,
        }
        source_hash = self._source_hash(
            definition=definition,
            node_id=node_id,
            progress_map=progress_map,
            ksa_context=ksa_context,
            readiness_context=readiness_context,
        )
        now = datetime.now(timezone.utc)
        return self.repository.upsert_user_learning_node_context(
            user_id=user_id,
            learning_path_id=learning_path.id,
            node_id=node_id,
            fields={
                "node_type": node.type,
                "generation_reason": generation_reason,
                "source_hash": source_hash,
                "generated_at": now,
                "context_json": context_payload,
                "course_context_json": course_context,
                "chapter_branch_context_json": chapter_branch_context,
                "prior_node_context_json": prior_node_context,
                "target_node_context_json": target_node_context,
                "next_node_context_json": next_node_context,
                "ksa_context_json": ksa_context,
                "readiness_context_json": readiness_context,
                "derived_assumptions_json": derived_assumptions,
            },
        )

    def recompute_for_available_nodes(
        self,
        *,
        user_id: int,
        learning_path: LearningPath,
        definition: CourseDefinition,
        generation_reason: str,
    ) -> list[UserLearningNodeContext]:
        progress_entries = self.repository.list_user_learning_node_progress(user_id=user_id, learning_path_id=learning_path.id)
        progress_map = {entry.node_id: entry.status for entry in progress_entries}
        runtime = build_skilltree_runtime(definition, persisted_node_progress=progress_map)
        candidate_node_ids = sorted(
            node_id for node_id, state in runtime.node_progress.items() if state in ACTIVE_OR_COMPLETED_STATES
        )
        result: list[UserLearningNodeContext] = []
        for node_id in candidate_node_ids:
            result.append(
                self.recompute_for_node(
                    user_id=user_id,
                    learning_path=learning_path,
                    definition=definition,
                    node_id=node_id,
                    generation_reason=generation_reason,
                )
            )
        return result

    def _build_graph(self, definition: CourseDefinition) -> _GraphData:
        hard_prev: dict[str, set[str]] = {node.id: set() for node in definition.nodes}
        recommended_prev: dict[str, set[str]] = {node.id: set() for node in definition.nodes}
        optional_prev: dict[str, set[str]] = {node.id: set() for node in definition.nodes}
        outgoing: dict[str, list[tuple[str, str]]] = {node.id: [] for node in definition.nodes}

        for edge in definition.edges:
            if edge.relationship in {"requires_all", "requires_any"}:
                hard_prev.setdefault(edge.to_node_id, set()).add(edge.from_node_id)
            elif edge.relationship == "recommended":
                recommended_prev.setdefault(edge.to_node_id, set()).add(edge.from_node_id)
            elif edge.relationship == "optional":
                optional_prev.setdefault(edge.to_node_id, set()).add(edge.from_node_id)
            outgoing.setdefault(edge.from_node_id, []).append((edge.to_node_id, edge.relationship))

        for node in definition.nodes:
            hard_prev.setdefault(node.id, set()).update(node.prerequisites.requires_all)
            hard_prev.setdefault(node.id, set()).update(node.prerequisites.requires_any)
            recommended_prev.setdefault(node.id, set()).update(node.prerequisites.recommended)
            for source in node.prerequisites.requires_all:
                outgoing.setdefault(source, []).append((node.id, "requires_all"))
            for source in node.prerequisites.requires_any:
                outgoing.setdefault(source, []).append((node.id, "requires_any"))
            for source in node.prerequisites.recommended:
                outgoing.setdefault(source, []).append((node.id, "recommended"))
        return _GraphData(
            hard_prev=hard_prev,
            recommended_prev=recommended_prev,
            optional_prev=optional_prev,
            outgoing=outgoing,
        )

    def _ancestors(self, parents_map: dict[str, set[str]], node_id: str) -> set[str]:
        seen: set[str] = set()
        stack = list(parents_map.get(node_id, set()))
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            stack.extend(list(parents_map.get(current, set())))
        return seen

    def _build_course_context(
        self,
        *,
        learning_path: LearningPath,
        definition: CourseDefinition,
        runtime: SkilltreeRuntime,
        node: CourseNodeDefinition,
    ) -> dict[str, Any]:
        structure_summary = {
            "chapter_count": len(definition.chapters),
            "branch_count": len(definition.branches),
            "node_count": len(definition.nodes),
            "edge_count": len(definition.edges),
            "entry_node_ids": list(definition.entry_node_ids),
            "required_node_count": sum(1 for item in definition.nodes if _is_effectively_required(definition, item)),
            "optional_node_count": sum(1 for item in definition.nodes if not _is_effectively_required(definition, item)),
        }
        branch = next((item for item in definition.branches if item.id == node.branch_id), None)
        node_state = runtime.node_progress.get(node.id, "locked")
        return {
            "course_id": learning_path.id,
            "course_title": learning_path.title,
            "course_description": learning_path.description or "",
            "course_difficulty": learning_path.difficulty_level or "",
            "course_subject": learning_path.subject or "",
            "course_goals": _as_list(definition.metadata.get("goals")) or _as_list(definition.metadata.get("learning_goals")),
            "overall_course_structure_summary": structure_summary,
            "entry_node_relationship": {
                "is_entry_node": node.id in set(definition.entry_node_ids),
                "entry_node_ids": list(definition.entry_node_ids),
            },
            "branch_requirement": {
                "branch_id": node.branch_id,
                "is_required_branch": True if branch is None else bool(branch.required),
                "is_optional_branch": False if branch is None else (not bool(branch.required)),
            },
            "overall_course_completion_state": {
                "user_node_state": node_state,
                "completion_summary": {
                    "required_total": runtime.completion_summary.required_total,
                    "required_completed": runtime.completion_summary.required_completed,
                    "optional_total": runtime.completion_summary.optional_total,
                    "optional_completed": runtime.completion_summary.optional_completed,
                    "required_branch_total": runtime.completion_summary.required_branch_total,
                    "required_branch_completed": runtime.completion_summary.required_branch_completed,
                    "global_capstone_total": runtime.completion_summary.global_capstone_total,
                    "global_capstone_completed": runtime.completion_summary.global_capstone_completed,
                    "is_complete": runtime.completion_summary.is_complete,
                },
            },
        }

    def _build_chapter_branch_context(
        self,
        *,
        definition: CourseDefinition,
        graph: _GraphData,
        node: CourseNodeDefinition,
    ) -> dict[str, Any]:
        chapter = next((item for item in definition.chapters if item.id == node.chapter_id), None)
        branch = next((item for item in definition.branches if item.id == node.branch_id), None)
        sibling_nodes = [item for item in definition.nodes if item.branch_id == node.branch_id] if node.branch_id else []
        sibling_ids = [item.id for item in sibling_nodes if item.id != node.id]
        hard_prev = graph.hard_prev.get(node.id, set())
        outgoing = graph.outgoing.get(node.id, [])
        near_merge = any(len(graph.hard_prev.get(next_node_id, set())) > 1 for next_node_id, _ in outgoing)
        near_capstone = any(
            next((n for n in definition.nodes if n.id == next_node_id), None) and
            next((n for n in definition.nodes if n.id == next_node_id), None).type in {"milestone", "capstone"}
            for next_node_id, _ in outgoing
        )
        if node.branch_id and all(
            next((n for n in definition.nodes if n.id == parent_id), None) and
            next((n for n in definition.nodes if n.id == parent_id), None).branch_id != node.branch_id
            for parent_id in hard_prev
        ):
            branch_position = "branch_start"
        elif near_merge:
            branch_position = "merge_point_adjacent"
        elif near_capstone or node.type in {"milestone", "capstone"}:
            branch_position = "late_stage_integration"
        else:
            branch_position = "mid_branch"

        return {
            "chapter": {
                "id": chapter.id if chapter else "",
                "title": chapter.title if chapter else "",
                "description": chapter.description if chapter else "",
                "order_index": chapter.order_index if chapter else 0,
            },
            "branch": {
                "id": branch.id if branch else "",
                "title": branch.title if branch else "",
                "description": branch.description if branch else "",
                "required": True if branch is None else bool(branch.required),
                "type": "required" if (branch is None or branch.required) else "optional",
            },
            "sibling_nodes": sibling_ids,
            "branch_topology": {
                "is_near_merge_point": near_merge,
                "is_near_milestone_or_capstone": near_capstone,
                "position_class": branch_position,
            },
        }

    def _node_topics(self, node: CourseNodeDefinition) -> tuple[list[str], list[str], list[str], list[dict[str, Any]]]:
        topic_set = set()
        goal_set = set()
        concept_set = set()
        ksa_links: list[dict[str, Any]] = []
        for item in node.ksa:
            topic_key = f"{item.dimension}.{item.topic}{('.' + item.subtopic) if item.subtopic else ''}"
            topic_set.add(topic_key)
            ksa_links.append(
                {
                    "dimension": item.dimension,
                    "topic": item.topic,
                    "subtopic": item.subtopic,
                    "start_level": item.start_level,
                    "target_level": item.target_level,
                }
            )
        for key in ("topics", "topic_tags"):
            topic_set.update(_as_list(node.metadata.get(key)))
        for key in ("goals", "learning_goals", "objectives"):
            goal_set.update(_as_list(node.metadata.get(key)))
        for key in ("concepts", "covered_concepts", "key_concepts"):
            concept_set.update(_as_list(node.metadata.get(key)))
        if not concept_set:
            concept_set.update(goal_set)
        return sorted(topic_set), sorted(goal_set), sorted(concept_set), ksa_links

    def _build_prior_node_context(
        self,
        *,
        definition: CourseDefinition,
        graph: _GraphData,
        runtime: SkilltreeRuntime,
        node: CourseNodeDefinition,
        progress_map: dict[str, str],
    ) -> dict[str, Any]:
        node_by_id = {item.id: item for item in definition.nodes}
        hard_ancestors = self._ancestors(graph.hard_prev, node.id)
        recommended_ancestors = self._ancestors(graph.recommended_prev, node.id)
        optional_ancestors = self._ancestors(graph.optional_prev, node.id)
        is_start_node = node.id in set(definition.entry_node_ids) or len(hard_ancestors) == 0

        completed_hard = sorted([node_id for node_id in hard_ancestors if progress_map.get(node_id) in COMPLETED_STATES])
        completed_recommended = sorted(
            [node_id for node_id in recommended_ancestors if progress_map.get(node_id) in COMPLETED_STATES]
        )
        completed_parallel = sorted(
            [
                node_id
                for node_id, status in runtime.node_progress.items()
                if status in COMPLETED_STATES
                and node_id not in hard_ancestors
                and node_id not in recommended_ancestors
                and node_id != node.id
                and node_by_id.get(node_id)
                and node_by_id[node_id].branch_id != node.branch_id
            ]
        )

        completed_nodes: list[dict[str, Any]] = []
        aggregate_topics: list[str] = []
        aggregate_goals: list[str] = []
        aggregate_concepts: list[str] = []
        aggregate_ksa: list[dict[str, Any]] = []
        for prior_id in sorted(set(completed_hard + completed_recommended + completed_parallel)):
            prior = node_by_id.get(prior_id)
            if prior is None:
                continue
            topics, goals, concepts, ksa_links = self._node_topics(prior)
            completed_nodes.append(
                {
                    "node_id": prior.id,
                    "title": prior.title,
                    "type": prior.type,
                    "status": progress_map.get(prior.id, ""),
                    "topics": topics,
                    "goals": goals,
                    "concepts": concepts,
                    "ksa_links": ksa_links,
                    "branch_id": prior.branch_id,
                }
            )
            aggregate_topics.extend(topics)
            aggregate_goals.extend(goals)
            aggregate_concepts.extend(concepts)
            aggregate_ksa.extend(ksa_links)

        prior_required_total = len(hard_ancestors)
        prior_required_completed = len(completed_hard)
        return {
            "is_start_node": is_start_node,
            "prior_required_node_ids": sorted(hard_ancestors),
            "prior_recommended_node_ids": sorted(recommended_ancestors),
            "prior_optional_related_node_ids": sorted(optional_ancestors),
            "completed_prior_required_node_ids": completed_hard,
            "completed_prior_recommended_node_ids": completed_recommended,
            "completed_parallel_branch_node_ids": completed_parallel,
            "completed_relevant_nodes": completed_nodes,
            "prior_topic_summary": sorted(set(aggregate_topics)),
            "prior_goal_summary": sorted(set(aggregate_goals)),
            "prior_concept_summary": sorted(set(aggregate_concepts)),
            "prior_ksa_link_summary": aggregate_ksa,
            "prior_required_completion_ratio": round(
                float(prior_required_completed) / float(prior_required_total),
                3,
            )
            if prior_required_total > 0
            else 1.0,
            "prior_assessment_passed_node_ids": [
                item["node_id"]
                for item in completed_nodes
                if item["type"] in CHECK_NODE_TYPES
            ],
        }

    def _build_target_node_context(self, *, definition: CourseDefinition, node: CourseNodeDefinition) -> dict[str, Any]:
        topics, goals, concepts, ksa_links = self._node_topics(node)
        branch = next((item for item in definition.branches if item.id == node.branch_id), None)
        return {
            "node_id": node.id,
            "node_title": node.title,
            "node_type": node.type,
            "node_description": node.description,
            "node_difficulty_level": _norm_text(node.metadata.get("difficulty_level") or node.metadata.get("difficulty")),
            "node_completion_mode": node.completion_mode,
            "node_required": _is_effectively_required(definition, node),
            "node_estimated_duration_minutes": node.estimated_duration_minutes,
            "node_chapter_id": node.chapter_id,
            "node_branch_id": node.branch_id,
            "node_branch_required": True if branch is None else bool(branch.required),
            "node_prerequisites": {
                "requires_all": list(node.prerequisites.requires_all),
                "requires_any": list(node.prerequisites.requires_any),
                "recommended": list(node.prerequisites.recommended),
            },
            "node_ksa_links": ksa_links,
            "node_topics": topics,
            "node_goals": goals,
            "node_concepts": concepts,
            "node_unlocks": {
                "node_ids": list(node.unlocks.node_ids),
                "branch_ids": list(node.unlocks.branch_ids),
                "recommended_next_node_ids": list(node.unlocks.recommended_next_node_ids),
            },
            "node_rewards": {
                "estimated_ksa_gain": dict(node.rewards.estimated_ksa_gain or {}),
                "effort_score": node.rewards.effort_score,
                "reward_tags": list(node.rewards.reward_tags),
            },
            "node_hooks": {
                "retrospective_hooks": {
                    "retrospective_after": node.retrospective_hooks.retrospective_after,
                    "review_recommended": node.retrospective_hooks.review_recommended,
                    "recap_checkpoint_available": node.retrospective_hooks.recap_checkpoint_available,
                },
                "ksa_hooks": {
                    "mini_assessment_available": node.ksa_hooks.mini_assessment_available,
                    "recommended_reassessment_topics": list(node.ksa_hooks.recommended_reassessment_topics),
                    "unlocks_deeper_refinement": node.ksa_hooks.unlocks_deeper_refinement,
                },
                "remediation": {
                    "is_remediation_node": node.remediation.is_remediation_node,
                    "recommended_if_failed_node_ids": list(node.remediation.recommended_if_failed_node_ids),
                    "supports_review_for_node_ids": list(node.remediation.supports_review_for_node_ids),
                },
            },
            "node_metadata": dict(node.metadata or {}),
        }

    def _build_next_node_context(
        self,
        *,
        definition: CourseDefinition,
        graph: _GraphData,
        node: CourseNodeDefinition,
    ) -> dict[str, Any]:
        node_by_id = {item.id: item for item in definition.nodes}
        direct = graph.outgoing.get(node.id, [])
        direct_successors: list[dict[str, Any]] = []
        upcoming_validation: list[str] = []
        second_hop: list[dict[str, Any]] = []
        fork_targets = set()
        merge_targets = []
        for to_node_id, relationship in direct:
            successor = node_by_id.get(to_node_id)
            if successor is None:
                continue
            fork_targets.add(to_node_id)
            direct_successors.append(
                {
                    "node_id": successor.id,
                    "title": successor.title,
                    "type": successor.type,
                    "relationship": relationship,
                    "branch_id": successor.branch_id,
                    "required": _is_effectively_required(definition, successor),
                }
            )
            if successor.type in CHECK_NODE_TYPES:
                upcoming_validation.append(successor.id)
            if len(graph.hard_prev.get(successor.id, set())) > 1:
                merge_targets.append(successor.id)
            for hop_node_id, hop_rel in graph.outgoing.get(successor.id, []):
                hop_node = node_by_id.get(hop_node_id)
                if hop_node is None:
                    continue
                second_hop.append(
                    {
                        "via_node_id": successor.id,
                        "node_id": hop_node.id,
                        "type": hop_node.type,
                        "relationship": hop_rel,
                    }
                )
                if hop_node.type in CHECK_NODE_TYPES:
                    upcoming_validation.append(hop_node.id)
        return {
            "direct_successors": direct_successors,
            "branch_forks_after_node": max(0, len(fork_targets) - 1),
            "merge_points_after_node": sorted(set(merge_targets)),
            "upcoming_validation_node_ids": sorted(set(upcoming_validation)),
            "second_hop_preview": second_hop[:8],
            "prepares_for": [
                {"node_id": item["node_id"], "type": item["type"]}
                for item in direct_successors[:5]
            ],
        }

    def _build_ksa_context(
        self,
        *,
        user_id: int,
        learning_path: LearningPath,
        definition: CourseDefinition,
        node: CourseNodeDefinition,
        prior_node_context: dict[str, Any],
    ) -> dict[str, Any]:
        persisted = self.repository.get_user_ksa_profile(user_id)
        if persisted is None:
            return {
                "has_ksa_profile": False,
                "relevant_topics": [],
                "topic_states": [],
                "related_drill_attempts": [],
                "signals": {"readiness_signal": "unknown"},
            }
        profile_json = dict(persisted.profile_json or {})
        knowledge = dict(profile_json.get("knowledge") or {})
        skills = dict(profile_json.get("skills") or {})
        abilities = dict(profile_json.get("abilities") or {})
        drill_state = dict(profile_json.get("drill_state") or {})
        topic_nodes = dict(drill_state.get("topic_nodes") or {})

        relevant_topics: list[dict[str, str]] = []
        for item in node.ksa:
            relevant_topics.append(
                {
                    "dimension": item.dimension,
                    "group": DIMENSION_GROUP.get(item.dimension, ""),
                    "topic": item.topic,
                    "subtopic": item.subtopic or "",
                }
            )
        if not relevant_topics:
            for entry in list(prior_node_context.get("prior_ksa_link_summary") or [])[:8]:
                dim = _norm_text(entry.get("dimension"))
                topic = _norm_text(entry.get("topic"))
                if dim and topic:
                    relevant_topics.append(
                        {
                            "dimension": dim,
                            "group": DIMENSION_GROUP.get(dim, ""),
                            "topic": topic,
                            "subtopic": _norm_text(entry.get("subtopic")),
                        }
                    )
        dedup = {(item["dimension"], item["topic"], item.get("subtopic", "")): item for item in relevant_topics}
        relevant_topics = list(dedup.values())

        topic_states: list[dict[str, Any]] = []
        decay_count = 0
        for item in relevant_topics:
            group = item["group"]
            topic = item["topic"]
            base_level = 1
            if group == "knowledge":
                base_level = int(knowledge.get(topic, 1))
            elif group == "skills":
                base_level = int(skills.get(topic, 1))
            elif group == "abilities":
                base_level = int(abilities.get(topic, 1))
            drill_topic = dict(topic_nodes.get(topic) or {})
            confidence = drill_topic.get("confidence")
            map_decay = int(drill_topic.get("map_decay_events_total") or 0)
            decay_count += map_decay
            topic_states.append(
                {
                    "dimension": item["dimension"],
                    "group": group,
                    "topic": topic,
                    "subtopic": item.get("subtopic", ""),
                    "level": base_level,
                    "drill_level": drill_topic.get("level"),
                    "chart_level": drill_topic.get("chart_level"),
                    "confidence": confidence,
                    "map_decay_events_total": map_decay,
                    "status": drill_topic.get("status"),
                }
            )

        attempts = self.repository.list_user_ksa_drill_attempts(user_id=user_id, limit=50)
        related_attempts: list[dict[str, Any]] = []
        relevant_topic_keys = {item["topic"] for item in relevant_topics}
        for attempt in attempts:
            selected = [str(item) for item in list(attempt.selected_topic_keys_json or [])]
            if not set(selected) & relevant_topic_keys:
                continue
            related_attempts.append(
                {
                    "attempt_id": attempt.id,
                    "completed_at": attempt.completed_at.isoformat() if attempt.completed_at else None,
                    "selected_topic_keys": selected,
                    "status": attempt.status,
                }
            )
        learning_speed = (
            dict(profile_json.get("assessment_details") or {}).get("derived", {}).get("learning_speed_multiplier")
        )
        avg_level = round(sum(float(item["level"]) for item in topic_states) / max(len(topic_states), 1), 3) if topic_states else 0.0
        avg_confidence = round(
            sum(float(item["confidence"] or 0.65) for item in topic_states) / max(len(topic_states), 1),
            3,
        ) if topic_states else 0.65
        readiness_signal = "strong" if avg_level >= 3.5 else ("risky" if avg_level <= 2.0 else "mixed")

        return {
            "has_ksa_profile": True,
            "profile_updated_at": persisted.updated_at.isoformat() if persisted.updated_at else None,
            "learning_speed_multiplier": float(learning_speed) if learning_speed is not None else None,
            "relevant_topics": relevant_topics,
            "topic_states": topic_states,
            "related_drill_attempts": related_attempts[:10],
            "signals": {
                "average_level": avg_level,
                "average_confidence": avg_confidence,
                "map_decay_events_total": decay_count,
                "readiness_signal": readiness_signal,
                "course_subject": learning_path.subject or "",
                "course_domain": _norm_text(definition.metadata.get("domain")),
            },
        }

    def _difficulty_score(self, *, node: CourseNodeDefinition, learning_path: LearningPath) -> float:
        raw = node.metadata.get("difficulty_score")
        if raw is not None:
            try:
                parsed = float(raw)
                return max(1.0, min(5.0, parsed))
            except Exception:
                pass
        level_text = _norm_text(node.metadata.get("difficulty_level") or node.metadata.get("difficulty") or learning_path.difficulty_level).lower()
        if level_text in {"beginner", "intro", "easy"}:
            return 2.0
        if level_text in {"intermediate", "medium"}:
            return 3.0
        if level_text in {"advanced", "hard"}:
            return 4.0
        if level_text in {"expert"}:
            return 5.0
        return 3.0

    def _build_readiness_context(
        self,
        *,
        learning_path: LearningPath,
        node: CourseNodeDefinition,
        prior_node_context: dict[str, Any],
        ksa_context: dict[str, Any],
    ) -> dict[str, Any]:
        prior_completion = float(prior_node_context.get("prior_required_completion_ratio") or 0.0)
        topic_states = list(ksa_context.get("topic_states") or [])
        if topic_states:
            competence = sum(float(item.get("level") or 1) for item in topic_states) / (5.0 * len(topic_states))
            confidence = sum(float(item.get("confidence") or 0.65) for item in topic_states) / len(topic_states)
        else:
            competence = 0.5
            confidence = 0.65
        difficulty = self._difficulty_score(node=node, learning_path=learning_path)
        speed = ksa_context.get("learning_speed_multiplier")
        speed_multiplier = float(speed) if speed is not None else 1.0
        adjusted_competence = max(0.0, min(1.0, competence + ((speed_multiplier - 1.0) * 0.1)))
        likely_ready = prior_completion >= 0.8 and adjusted_competence >= (difficulty / 6.0)
        likely_needs_review = bool(ksa_context.get("signals", {}).get("map_decay_events_total", 0)) or prior_completion < 0.5
        likely_needs_scaffold = adjusted_competence < 0.45 or confidence < 0.45 or prior_completion < 0.6
        weak_alignment = sorted({item.get("topic") for item in topic_states if float(item.get("level") or 1) <= 2.0})
        strong_alignment = sorted({item.get("topic") for item in topic_states if float(item.get("level") or 1) >= 4.0})
        if likely_needs_scaffold:
            support_intensity = "high"
        elif likely_ready:
            support_intensity = "low"
        else:
            support_intensity = "medium"
        return {
            "difficulty_score": round(difficulty, 3),
            "prior_completion_ratio": round(prior_completion, 3),
            "competence_estimate": round(adjusted_competence, 3),
            "confidence_estimate": round(confidence, 3),
            "competence_confidence_gap": round(adjusted_competence - confidence, 3),
            "likely_ready": likely_ready,
            "likely_needs_scaffold": likely_needs_scaffold,
            "likely_needs_review": likely_needs_review,
            "strong_topic_alignment": strong_alignment,
            "weak_topic_alignment": weak_alignment,
            "estimated_support_intensity": support_intensity,
            "confidence_sensitive_support": {
                "low_competence_high_confidence": adjusted_competence < 0.45 and confidence >= 0.7,
                "high_competence_low_confidence": adjusted_competence >= 0.65 and confidence < 0.5,
                "low_competence_low_confidence": adjusted_competence < 0.45 and confidence < 0.5,
            },
        }

    def _build_derived_assumptions(
        self,
        *,
        prior_node_context: dict[str, Any],
        next_node_context: dict[str, Any],
        ksa_context: dict[str, Any],
        readiness_context: dict[str, Any],
    ) -> dict[str, Any]:
        already_understands = list(prior_node_context.get("prior_concept_summary") or [])[:15]
        skip_reexplain = list(readiness_context.get("strong_topic_alignment") or [])[:8]
        support_focus = list(readiness_context.get("weak_topic_alignment") or [])[:8]
        if not support_focus and readiness_context.get("likely_needs_scaffold"):
            support_focus = list(prior_node_context.get("prior_topic_summary") or [])[:5]
        return {
            "probably_understands": already_understands,
            "skip_or_compress_reexplain_for": skip_reexplain,
            "support_focus_areas": support_focus,
            "next_node_dependency_focus": list(next_node_context.get("upcoming_validation_node_ids") or [])[:6],
            "preferred_ksa_topics_for_examples": [
                item.get("topic")
                for item in list(ksa_context.get("topic_states") or [])
                if float(item.get("level") or 1) >= 3.0
            ][:6],
        }

    def _source_hash(
        self,
        *,
        definition: CourseDefinition,
        node_id: str,
        progress_map: dict[str, str],
        ksa_context: dict[str, Any],
        readiness_context: dict[str, Any],
    ) -> str:
        payload = {
            "definition": definition.model_dump(),
            "node_id": node_id,
            "progress_map": progress_map,
            "ksa_context": ksa_context,
            "readiness_context": readiness_context,
        }
        raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
