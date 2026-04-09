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
class BranchProgressSummary:
    branch_id: str
    title: str
    required: bool
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
    required_branch_total: int
    required_branch_completed: int
    global_capstone_total: int
    global_capstone_completed: int

    @property
    def is_complete(self) -> bool:
        branches_complete = self.required_branch_total == 0 or self.required_branch_completed >= self.required_branch_total
        capstones_complete = self.global_capstone_total == 0 or self.global_capstone_completed >= self.global_capstone_total
        return branches_complete and capstones_complete


@dataclass(slots=True)
class SkilltreeRecommendations:
    next_best_node_id: str | None
    next_branch_id: str | None
    suggested_optional_node_id: str | None
    suggested_review_node_id: str | None
    suggested_ksa_assessment_node_id: str | None
    rationale: list[str]


@dataclass(slots=True)
class SkilltreeHookSummary:
    retrospective_node_ids: list[str]
    review_node_ids: list[str]
    ksa_assessment_node_ids: list[str]
    remediation_candidate_node_ids: list[str]
    adaptive_unlock_candidate_node_ids: list[str]


@dataclass(slots=True)
class SkilltreeRuntime:
    node_progress: dict[str, str]
    node_runtime: dict[str, NodeRuntimeSemantics]
    chapter_summaries: list[ChapterProgressSummary]
    branch_summaries: list[BranchProgressSummary]
    completion_summary: CourseCompletionSummary
    recommendations: SkilltreeRecommendations
    hook_summary: SkilltreeHookSummary


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


def _node_sort_key(definition: CourseDefinition, node_id: str) -> tuple[int, int, float, float, str]:
    node_by_id = {node.id: node for node in definition.nodes}
    chapter_order_by_id = {chapter.id: chapter.order_index for chapter in definition.chapters}
    node = node_by_id[node_id]
    chapter_order = chapter_order_by_id.get(node.chapter_id or "", 999)
    branch_order = 999
    if node.branch_id:
        ordered_branch_ids = [branch.id for branch in definition.branches]
        if node.branch_id in ordered_branch_ids:
            branch_order = ordered_branch_ids.index(node.branch_id)
    return (chapter_order, branch_order, float(node.layout.x), float(node.layout.y), node.id)


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


def _build_branch_summaries(
    definition: CourseDefinition,
    *,
    progress: dict[str, str],
) -> list[BranchProgressSummary]:
    branch_summaries: list[BranchProgressSummary] = []
    for branch in definition.branches:
        branch_nodes = [node for node in definition.nodes if node.branch_id == branch.id]
        required_total = sum(1 for node in branch_nodes if _is_effectively_required(definition, node.id))
        required_completed = sum(
            1
            for node in branch_nodes
            if _is_effectively_required(definition, node.id) and progress.get(node.id) in COMPLETED_STATES
        )
        optional_total = sum(1 for node in branch_nodes if not _is_effectively_required(definition, node.id))
        optional_completed = sum(
            1
            for node in branch_nodes
            if (not _is_effectively_required(definition, node.id)) and progress.get(node.id) in COMPLETED_STATES.union({"optional_skipped"})
        )
        branch_summaries.append(
            BranchProgressSummary(
                branch_id=branch.id,
                title=branch.title,
                required=branch.required,
                required_total=required_total,
                required_completed=required_completed,
                optional_total=optional_total,
                optional_completed=optional_completed,
            )
        )
    return branch_summaries


def _build_completion_summary(
    definition: CourseDefinition,
    *,
    progress: dict[str, str],
    branch_summaries: list[BranchProgressSummary],
) -> CourseCompletionSummary:
    required_total = sum(1 for node in definition.nodes if _is_effectively_required(definition, node.id))
    required_completed = sum(
        1 for node in definition.nodes if _is_effectively_required(definition, node.id) and progress.get(node.id) in COMPLETED_STATES
    )
    optional_total = sum(1 for node in definition.nodes if not _is_effectively_required(definition, node.id))
    optional_completed = sum(
        1
        for node in definition.nodes
        if (not _is_effectively_required(definition, node.id)) and progress.get(node.id) in COMPLETED_STATES.union({"optional_skipped"})
    )

    required_branch_total = sum(1 for item in branch_summaries if item.required)
    required_branch_completed = sum(1 for item in branch_summaries if item.required and item.is_complete)

    global_capstone_nodes = [
        node
        for node in definition.nodes
        if node.type == "capstone"
        and node.required
        and (node.branch_id is None or bool(node.metadata.get("global_final", False)))
    ]
    global_capstone_total = len(global_capstone_nodes)
    global_capstone_completed = sum(1 for node in global_capstone_nodes if progress.get(node.id) in COMPLETED_STATES)

    return CourseCompletionSummary(
        required_total=required_total,
        required_completed=required_completed,
        optional_total=optional_total,
        optional_completed=optional_completed,
        required_branch_total=required_branch_total,
        required_branch_completed=required_branch_completed,
        global_capstone_total=global_capstone_total,
        global_capstone_completed=global_capstone_completed,
    )


def _build_recommendations(
    definition: CourseDefinition,
    *,
    progress: dict[str, str],
    branch_summaries: list[BranchProgressSummary],
) -> SkilltreeRecommendations:
    node_by_id = {node.id: node for node in definition.nodes}
    available_ids = [node_id for node_id, state in progress.items() if state == "available"]

    available_required = [node_id for node_id in available_ids if _is_effectively_required(definition, node_id)]
    available_optional = [node_id for node_id in available_ids if not _is_effectively_required(definition, node_id)]

    next_best_node_id = sorted(available_required, key=lambda node_id: _node_sort_key(definition, node_id))[0] if available_required else (
        sorted(available_ids, key=lambda node_id: _node_sort_key(definition, node_id))[0] if available_ids else None
    )

    incomplete_required_branches = [item for item in branch_summaries if item.required and not item.is_complete]
    next_branch_id = None
    if incomplete_required_branches:
        next_branch = sorted(
            incomplete_required_branches,
            key=lambda item: (
                0 if item.required_total == 0 else (item.required_completed / item.required_total),
                item.title.lower(),
            ),
        )[0]
        next_branch_id = next_branch.branch_id

    suggested_optional_node_id = sorted(available_optional, key=lambda node_id: _node_sort_key(definition, node_id))[0] if available_optional else None

    failed_ids = {node_id for node_id, state in progress.items() if state == "failed_needs_retry"}
    review_candidate_ids = [
        node.id
        for node in definition.nodes
        if progress.get(node.id) == "available"
        and (
            node.type == "review"
            or node.retrospective_hooks.review_recommended
            or node.remediation.is_remediation_node
            or any(dep in failed_ids for dep in node.remediation.recommended_if_failed_node_ids)
        )
    ]
    suggested_review_node_id = sorted(review_candidate_ids, key=lambda node_id: _node_sort_key(definition, node_id))[0] if review_candidate_ids else None

    ksa_candidate_ids = [
        node.id
        for node in definition.nodes
        if progress.get(node.id) == "available"
        and (
            node.type == "assessment_hook"
            or node.ksa_hooks.mini_assessment_available
            or any(item.unlocks_assessment_check or item.recommends_assessment_check for item in node.ksa)
        )
    ]
    suggested_ksa_assessment_node_id = sorted(ksa_candidate_ids, key=lambda node_id: _node_sort_key(definition, node_id))[0] if ksa_candidate_ids else None

    rationale: list[str] = []
    if next_best_node_id:
        rationale.append("Prioritize required available nodes first.")
    if next_branch_id:
        rationale.append("Continue the next incomplete required branch.")
    if suggested_optional_node_id:
        rationale.append("Optional enrichment is available without blocking core progression.")
    if suggested_review_node_id:
        rationale.append("A review/remediation node is available based on current state.")
    if suggested_ksa_assessment_node_id:
        rationale.append("A KSA mini-assessment hook is available.")

    if next_best_node_id:
        explicit_recommended = [
            node.id
            for node in definition.nodes
            if node.id in available_ids and next_best_node_id in node.unlocks.recommended_next_node_ids
        ]
        if explicit_recommended:
            rationale.append("Recommendation aligns with course-defined recommended-next hints.")

    return SkilltreeRecommendations(
        next_best_node_id=next_best_node_id,
        next_branch_id=next_branch_id,
        suggested_optional_node_id=suggested_optional_node_id,
        suggested_review_node_id=suggested_review_node_id,
        suggested_ksa_assessment_node_id=suggested_ksa_assessment_node_id,
        rationale=rationale,
    )


def _build_hook_summary(definition: CourseDefinition, *, progress: dict[str, str]) -> SkilltreeHookSummary:
    retrospective_node_ids = sorted(
        [
            node.id
            for node in definition.nodes
            if node.retrospective_hooks.retrospective_after or node.retrospective_hooks.recap_checkpoint_available
        ]
    )
    review_node_ids = sorted(
        [
            node.id
            for node in definition.nodes
            if node.type == "review" or node.retrospective_hooks.review_recommended
        ]
    )
    ksa_assessment_node_ids = sorted(
        [
            node.id
            for node in definition.nodes
            if node.type == "assessment_hook"
            or node.ksa_hooks.mini_assessment_available
            or any(item.unlocks_assessment_check or item.recommends_assessment_check for item in node.ksa)
        ]
    )

    failed_ids = {node_id for node_id, state in progress.items() if state == "failed_needs_retry"}
    remediation_candidate_node_ids = sorted(
        [
            node.id
            for node in definition.nodes
            if node.remediation.is_remediation_node
            or bool(set(node.remediation.recommended_if_failed_node_ids).intersection(failed_ids))
        ]
    )

    adaptive_unlock_candidate_node_ids = sorted(
        [
            node.id
            for node in definition.nodes
            if node.adaptive_unlock.ksa_thresholds
            or node.adaptive_unlock.requires_branch_completion_ids
            or node.adaptive_unlock.requires_checkpoint_node_ids
            or node.adaptive_unlock.requires_review_recommended
            or node.adaptive_unlock.recommended_only
        ]
    )

    return SkilltreeHookSummary(
        retrospective_node_ids=retrospective_node_ids,
        review_node_ids=review_node_ids,
        ksa_assessment_node_ids=ksa_assessment_node_ids,
        remediation_candidate_node_ids=remediation_candidate_node_ids,
        adaptive_unlock_candidate_node_ids=adaptive_unlock_candidate_node_ids,
    )


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

    orphan_nodes = [node for node in definition.nodes if not node.chapter_id or node.chapter_id not in chapter_meta]
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

    branch_summaries = _build_branch_summaries(definition, progress=computed_progress)
    completion_summary = _build_completion_summary(definition, progress=computed_progress, branch_summaries=branch_summaries)
    recommendations = _build_recommendations(definition, progress=computed_progress, branch_summaries=branch_summaries)
    hook_summary = _build_hook_summary(definition, progress=computed_progress)

    return SkilltreeRuntime(
        node_progress=computed_progress,
        node_runtime=node_runtime,
        chapter_summaries=chapter_summaries,
        branch_summaries=branch_summaries,
        completion_summary=completion_summary,
        recommendations=recommendations,
        hook_summary=hook_summary,
    )
