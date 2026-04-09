from __future__ import annotations

from dataclasses import dataclass

from services.retriever.services.course_files import CourseDefinition

NODE_PROGRESS_STATES = {
    "locked",
    "available",
    "in_progress",
    "completed",
    "mastered",
    "optional_skipped",
    "failed_needs_retry",
    "awaiting_checkpoint",
}

COMPLETED_STATES = {"completed", "mastered"}
ACTIVE_STATES = {"available", "in_progress", "failed_needs_retry"}
CHECKPOINT_TYPES = {"checkpoint", "unlock_gate", "quiz"}


@dataclass(slots=True)
class ChapterProgressSummary:
    chapter_id: str
    title: str
    required_total: int
    required_completed: int
    optional_total: int
    optional_completed: int

    @property
    def is_complete(self) -> bool:
        return self.required_total == 0 or self.required_completed >= self.required_total


@dataclass(slots=True)
class CourseCompletionSummary:
    required_total: int
    required_completed: int
    optional_total: int
    optional_completed: int

    @property
    def is_complete(self) -> bool:
        return self.required_total == 0 or self.required_completed >= self.required_total


@dataclass(slots=True)
class SkilltreeRuntime:
    node_progress: dict[str, str]
    node_runtime: dict[str, NodeRuntimeSemantics]
    chapter_summaries: list[ChapterProgressSummary]
    completion_summary: CourseCompletionSummary


@dataclass(slots=True)
class NodeRuntimeSemantics:
    blocked_by_all: list[str]
    blocked_by_any: list[str]
    is_entry: bool
    is_parallel_available: bool
    awaiting_checkpoint: bool
    capstone_locked: bool
    optional_branch: bool
    completion_allowed: bool


def _dependency_sets(definition: CourseDefinition) -> dict[str, dict[str, set[str]]]:
    hard_incoming: dict[str, dict[str, set[str]]] = {
        node.id: {"requires_all": set(), "requires_any": set()} for node in definition.nodes
    }
    for edge in definition.edges:
        if edge.relationship not in {"requires_all", "requires_any"}:
            continue
        hard_incoming.setdefault(edge.to_node_id, {"requires_all": set(), "requires_any": set()})[edge.relationship].add(edge.from_node_id)

    for node in definition.nodes:
        hard_incoming[node.id]["requires_all"].update(node.prerequisites.requires_all)
        hard_incoming[node.id]["requires_any"].update(node.prerequisites.requires_any)
    return hard_incoming


def _is_effectively_required(definition: CourseDefinition, node_id: str) -> bool:
    node_by_id = {node.id: node for node in definition.nodes}
    branch_by_id = {branch.id: branch for branch in definition.branches}
    node = node_by_id[node_id]
    if not node.required:
        return False
    if not node.branch_id:
        return True
    branch = branch_by_id.get(node.branch_id)
    if branch is None:
        return True
    return bool(branch.required)


def _can_complete_node(
    definition: CourseDefinition,
    *,
    node_id: str,
    progress_state: str,
    semantics: NodeRuntimeSemantics,
) -> bool:
    if progress_state not in ACTIVE_STATES:
        return False
    if not semantics.completion_allowed:
        return False
    node_by_id = {node.id: node for node in definition.nodes}
    node = node_by_id.get(node_id)
    if node is None:
        return False
    if node.type == "assessment_hook":
        return False
    if node.completion_mode == "assessment_threshold":
        return False
    if node.completion_mode == "gate_unlock":
        return False
    return True


def build_skilltree_runtime(
    definition: CourseDefinition,
    *,
    persisted_node_progress: dict[str, str] | None = None,
) -> SkilltreeRuntime:
    progress_seed = dict(persisted_node_progress or {})
    node_by_id = {node.id: node for node in definition.nodes}
    hard_incoming = _dependency_sets(definition)

    entry_set = set(definition.entry_node_ids)
    computed_progress: dict[str, str] = {}
    node_runtime: dict[str, NodeRuntimeSemantics] = {}

    for node in definition.nodes:
        persisted_state = progress_seed.get(node.id)
        if persisted_state in NODE_PROGRESS_STATES and persisted_state in {"in_progress", "completed", "mastered", "optional_skipped", "failed_needs_retry"}:
            computed_progress[node.id] = persisted_state
        requires_all = hard_incoming[node.id]["requires_all"]
        requires_any = hard_incoming[node.id]["requires_any"]
        blocked_by_all = sorted(dep for dep in requires_all if computed_progress.get(dep) not in COMPLETED_STATES)
        blocked_by_any = []
        if requires_any:
            if not any(computed_progress.get(dep) in COMPLETED_STATES for dep in requires_any):
                blocked_by_any = sorted(requires_any)

        all_ok = not blocked_by_all
        any_ok = not blocked_by_any

        if node.id not in computed_progress:
            if node.id in entry_set:
                computed_progress[node.id] = "available"
            elif all_ok and any_ok:
                computed_progress[node.id] = "available"
            else:
                awaiting_checkpoint = False
                if blocked_by_all:
                    non_checkpoint_blockers = [dep for dep in blocked_by_all if node_by_id.get(dep) and node_by_id[dep].type not in CHECKPOINT_TYPES]
                    awaiting_checkpoint = len(non_checkpoint_blockers) == 0
                elif blocked_by_any:
                    any_non_checkpoint = any(node_by_id.get(dep) and node_by_id[dep].type not in CHECKPOINT_TYPES for dep in blocked_by_any)
                    awaiting_checkpoint = not any_non_checkpoint
                computed_progress[node.id] = "awaiting_checkpoint" if awaiting_checkpoint else "locked"

        node_runtime[node.id] = NodeRuntimeSemantics(
            blocked_by_all=blocked_by_all,
            blocked_by_any=blocked_by_any,
            is_entry=node.id in entry_set,
            is_parallel_available=False,
            awaiting_checkpoint=computed_progress.get(node.id) == "awaiting_checkpoint",
            capstone_locked=node.type == "capstone" and computed_progress.get(node.id) in {"locked", "awaiting_checkpoint"},
            optional_branch=bool(node.branch_id) and not _is_effectively_required(definition, node.id),
            completion_allowed=False,
        )

    available_nodes = [node_id for node_id, state in computed_progress.items() if state == "available"]
    parallel_available = len(available_nodes) > 1
    for node_id in available_nodes:
        if node_id in node_runtime:
            node_runtime[node_id].is_parallel_available = parallel_available
    for node_id, semantics in node_runtime.items():
        semantics.completion_allowed = _can_complete_node(
            definition,
            node_id=node_id,
            progress_state=computed_progress.get(node_id, "locked"),
            semantics=semantics,
        )

    chapter_meta = {chapter.id: chapter for chapter in definition.chapters}
    chapter_summaries: list[ChapterProgressSummary] = []

    for chapter in sorted(definition.chapters, key=lambda item: (item.order_index, item.title.lower())):
        chapter_nodes = [node for node in definition.nodes if node.chapter_id == chapter.id]
        required_total = sum(1 for node in chapter_nodes if _is_effectively_required(definition, node.id))
        required_completed = sum(
            1 for node in chapter_nodes if _is_effectively_required(definition, node.id) and computed_progress.get(node.id) in COMPLETED_STATES
        )
        optional_total = sum(1 for node in chapter_nodes if not _is_effectively_required(definition, node.id))
        optional_completed = sum(
            1
            for node in chapter_nodes
            if (not _is_effectively_required(definition, node.id)) and computed_progress.get(node.id) in COMPLETED_STATES.union({"optional_skipped"})
        )
        chapter_summaries.append(
            ChapterProgressSummary(
                chapter_id=chapter.id,
                title=chapter.title,
                required_total=required_total,
                required_completed=required_completed,
                optional_total=optional_total,
                optional_completed=optional_completed,
            )
        )

    # Ensure nodes without chapter assignment are still counted in totals.
    orphan_nodes = [node for node in definition.nodes if not node.chapter_id or node.chapter_id not in chapter_meta]
    required_total = sum(1 for node in definition.nodes if _is_effectively_required(definition, node.id))
    required_completed = sum(
        1 for node in definition.nodes if _is_effectively_required(definition, node.id) and computed_progress.get(node.id) in COMPLETED_STATES
    )
    optional_total = sum(1 for node in definition.nodes if not _is_effectively_required(definition, node.id))
    optional_completed = sum(
        1
        for node in definition.nodes
        if (not _is_effectively_required(definition, node.id)) and computed_progress.get(node.id) in COMPLETED_STATES.union({"optional_skipped"})
    )

    if orphan_nodes:
        orphan_required_total = sum(1 for node in orphan_nodes if _is_effectively_required(definition, node.id))
        orphan_required_completed = sum(
            1 for node in orphan_nodes if _is_effectively_required(definition, node.id) and computed_progress.get(node.id) in COMPLETED_STATES
        )
        orphan_optional_total = sum(1 for node in orphan_nodes if not _is_effectively_required(definition, node.id))
        orphan_optional_completed = sum(
            1
            for node in orphan_nodes
            if (not _is_effectively_required(definition, node.id)) and computed_progress.get(node.id) in COMPLETED_STATES.union({"optional_skipped"})
        )
        chapter_summaries.append(
            ChapterProgressSummary(
                chapter_id="_ungrouped",
                title="Ungrouped",
                required_total=orphan_required_total,
                required_completed=orphan_required_completed,
                optional_total=orphan_optional_total,
                optional_completed=orphan_optional_completed,
            )
        )

    completion_summary = CourseCompletionSummary(
        required_total=required_total,
        required_completed=required_completed,
        optional_total=optional_total,
        optional_completed=optional_completed,
    )

    return SkilltreeRuntime(
        node_progress=computed_progress,
        node_runtime=node_runtime,
        chapter_summaries=chapter_summaries,
        completion_summary=completion_summary,
    )
