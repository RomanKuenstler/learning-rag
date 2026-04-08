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
}

COMPLETED_STATES = {"completed", "mastered"}


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
    chapter_summaries: list[ChapterProgressSummary]
    completion_summary: CourseCompletionSummary


def build_skilltree_runtime(
    definition: CourseDefinition,
    *,
    persisted_node_progress: dict[str, str] | None = None,
) -> SkilltreeRuntime:
    progress_seed = dict(persisted_node_progress or {})

    hard_incoming: dict[str, dict[str, set[str]]] = {
        node.id: {"requires_all": set(), "requires_any": set()} for node in definition.nodes
    }
    for edge in definition.edges:
        if edge.relationship not in {"requires_all", "requires_any"}:
            continue
        hard_incoming.setdefault(edge.to_node_id, {"requires_all": set(), "requires_any": set()})[edge.relationship].add(edge.from_node_id)

    # Prerequisites on node payload are treated as hard dependencies too.
    for node in definition.nodes:
        hard_incoming[node.id]["requires_all"].update(node.prerequisites.requires_all)
        hard_incoming[node.id]["requires_any"].update(node.prerequisites.requires_any)

    entry_set = set(definition.entry_node_ids)
    computed_progress: dict[str, str] = {}

    for node in definition.nodes:
        persisted_state = progress_seed.get(node.id)
        if persisted_state in NODE_PROGRESS_STATES and persisted_state in {"in_progress", "completed", "mastered", "optional_skipped"}:
            computed_progress[node.id] = persisted_state
            continue

        requires_all = hard_incoming[node.id]["requires_all"]
        requires_any = hard_incoming[node.id]["requires_any"]

        all_ok = all(computed_progress.get(dep) in COMPLETED_STATES for dep in requires_all)
        any_ok = True if not requires_any else any(computed_progress.get(dep) in COMPLETED_STATES for dep in requires_any)

        if node.id in entry_set:
            computed_progress[node.id] = "available"
        elif all_ok and any_ok:
            computed_progress[node.id] = "available"
        else:
            computed_progress[node.id] = "locked"

    chapter_meta = {chapter.id: chapter for chapter in definition.chapters}
    chapter_summaries: list[ChapterProgressSummary] = []

    for chapter in sorted(definition.chapters, key=lambda item: (item.order_index, item.title.lower())):
        chapter_nodes = [node for node in definition.nodes if node.chapter_id == chapter.id]
        required_total = sum(1 for node in chapter_nodes if node.required)
        required_completed = sum(
            1 for node in chapter_nodes if node.required and computed_progress.get(node.id) in COMPLETED_STATES
        )
        optional_total = sum(1 for node in chapter_nodes if not node.required)
        optional_completed = sum(
            1
            for node in chapter_nodes
            if (not node.required) and computed_progress.get(node.id) in COMPLETED_STATES.union({"optional_skipped"})
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
    required_total = sum(1 for node in definition.nodes if node.required)
    required_completed = sum(
        1 for node in definition.nodes if node.required and computed_progress.get(node.id) in COMPLETED_STATES
    )
    optional_total = sum(1 for node in definition.nodes if not node.required)
    optional_completed = sum(
        1
        for node in definition.nodes
        if (not node.required) and computed_progress.get(node.id) in COMPLETED_STATES.union({"optional_skipped"})
    )

    if orphan_nodes:
        orphan_required_total = sum(1 for node in orphan_nodes if node.required)
        orphan_required_completed = sum(
            1 for node in orphan_nodes if node.required and computed_progress.get(node.id) in COMPLETED_STATES
        )
        orphan_optional_total = sum(1 for node in orphan_nodes if not node.required)
        orphan_optional_completed = sum(
            1
            for node in orphan_nodes
            if (not node.required) and computed_progress.get(node.id) in COMPLETED_STATES.union({"optional_skipped"})
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
        chapter_summaries=chapter_summaries,
        completion_summary=completion_summary,
    )
