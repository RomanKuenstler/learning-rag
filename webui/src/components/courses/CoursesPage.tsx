import { useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";
import type { CourseImportResponse, CourseListItem, CourseSort, LearningPath } from "../../types/chat";
import { Dialog } from "../common/Dialog";
import { Icon } from "../common/Icons";

type CourseScopeFilter = "all" | "global" | "user";
type CourseStatusFilter = "all" | "draft" | "published" | "archived";
const CHAPTER_COLORS = ["#0ea5e9", "#f97316", "#22c55e", "#a855f7", "#ef4444", "#14b8a6", "#eab308"];
const NODE_ICON_SIZE = 52;
const NODE_CENTER_X = NODE_ICON_SIZE / 2;
const NODE_CENTER_Y = NODE_ICON_SIZE / 2;
const H_SPACING = 210;
const V_SPACING = 130;
const LEFT_PADDING = 90;
const TOP_PADDING = 90;

type CoursesPageProps = {
  courses: CourseListItem[];
  loading: boolean;
  error: string | null;
  importing: boolean;
  canCreateGlobal: boolean;
  canUploadPaths: boolean;
  currentUserId: number;
  onLoad: (params: {
    search?: string;
    scope?: CourseScopeFilter;
    status?: CourseStatusFilter;
    sort?: CourseSort;
  }) => Promise<unknown>;
  onLoadDetails: (courseId: string) => Promise<LearningPath>;
  onUpdateNodeProgress: (
    courseId: string,
    nodeId: string,
    payload: {
      status: "in_progress" | "completed" | "mastered" | "optional_skipped" | "failed_needs_retry" | "reset";
      evidence?: Record<string, unknown>;
    },
  ) => Promise<LearningPath>;
  onImport: (files: File[], scopesByFile: Record<string, "global" | "user">) => Promise<CourseImportResponse>;
  onDownloadTemplate: () => Promise<unknown>;
  onStartContinue: (courseId: string, nodeId: string) => Promise<unknown> | unknown;
  onToggleArchived: (courseId: string, nextArchived: boolean) => Promise<unknown>;
  onDeleteCourse: (courseId: string) => Promise<unknown>;
};

type ScopeMenuProps = {
  value: "global" | "user";
  canCreateGlobal: boolean;
  disabled: boolean;
  onChange: (value: "global" | "user") => void;
};

function ScopeMenu({ value, canCreateGlobal, disabled, onChange }: ScopeMenuProps) {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const [open, setOpen] = useState(false);
  const [openUpward, setOpenUpward] = useState(false);

  const MENU_ESTIMATED_HEIGHT = 140;

  return (
    <div ref={rootRef} className={`gpt-editor-select${open ? " open" : ""}${openUpward ? " open-upward" : ""}`}>
      <button
        type="button"
        className="gpt-editor-select-trigger"
        aria-expanded={open}
        onClick={() => {
          if (!disabled) {
            if (!open && rootRef.current) {
              const rect = rootRef.current.getBoundingClientRect();
              const roomBelow = window.innerHeight - rect.bottom;
              const roomAbove = rect.top;
              setOpenUpward(roomBelow < MENU_ESTIMATED_HEIGHT && roomAbove > roomBelow);
            }
            setOpen((current) => !current);
          }
        }}
        disabled={disabled}
      >
        <span className="gpt-editor-select-label">{value === "global" ? "Global" : "User"}</span>
        <Icon name="chevron-down" className="header-mode-chevron" />
      </button>
      {open ? (
        <div className="header-mode-menu gpt-editor-select-menu" role="menu">
          <button
            type="button"
            className={`header-mode-option gpt-editor-select-option${value === "user" ? " active" : ""}`}
            onClick={() => {
              onChange("user");
              setOpen(false);
            }}
          >
            <span className="gpt-editor-select-option-label">User</span>
            {value === "user" ? <Icon name="check" className="header-mode-option-check" /> : null}
          </button>
          <button
            type="button"
            className={`header-mode-option gpt-editor-select-option${value === "global" ? " active" : ""}`}
            onClick={() => {
              onChange("global");
              setOpen(false);
            }}
            disabled={!canCreateGlobal}
            title={!canCreateGlobal ? "Only admins can create global courses" : undefined}
          >
            <span className="gpt-editor-select-option-label">Global</span>
            {value === "global" ? <Icon name="check" className="header-mode-option-check" /> : null}
          </button>
        </div>
      ) : null}
    </div>
  );
}

function SortMenu({
  value,
  onChange,
}: {
  value: CourseSort;
  onChange: (next: CourseSort) => void;
}) {
  const [open, setOpen] = useState(false);
  const options: Array<{ value: CourseSort; label: string }> = [
    { value: "updated_desc", label: "Newest Updated" },
    { value: "updated_asc", label: "Oldest Updated" },
    { value: "name_asc", label: "Name A-Z" },
    { value: "name_desc", label: "Name Z-A" },
    { value: "modules_desc", label: "Most Modules" },
    { value: "lessons_desc", label: "Most Lessons" },
    { value: "scope_global_first", label: "Global First" },
    { value: "scope_user_first", label: "User First" },
  ];

  return (
    <div className={`gpt-editor-select${open ? " open" : ""}`}>
      <button type="button" className="gpt-editor-select-trigger" aria-expanded={open} onClick={() => setOpen((current) => !current)}>
        <span className="gpt-editor-select-label">{options.find((item) => item.value === value)?.label ?? "Sort"}</span>
        <Icon name="chevron-down" className="header-mode-chevron" />
      </button>
      {open ? (
        <div className="header-mode-menu gpt-editor-select-menu" role="menu">
          {options.map((option) => (
            <button
              key={option.value}
              type="button"
              className={`header-mode-option gpt-editor-select-option${value === option.value ? " active" : ""}`}
              onClick={() => {
                onChange(option.value);
                setOpen(false);
              }}
            >
              <span className="gpt-editor-select-option-label">{option.label}</span>
              {value === option.value ? <Icon name="check" className="header-mode-option-check" /> : null}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function ScopeFilterMenu({
  value,
  onChange,
}: {
  value: CourseScopeFilter;
  onChange: (next: CourseScopeFilter) => void;
}) {
  const [open, setOpen] = useState(false);
  const options: Array<{ value: CourseScopeFilter; label: string }> = [
    { value: "all", label: "All scopes" },
    { value: "global", label: "Global" },
    { value: "user", label: "User" },
  ];

  return (
    <div className={`gpt-editor-select${open ? " open" : ""}`}>
      <button type="button" className="gpt-editor-select-trigger" aria-expanded={open} onClick={() => setOpen((current) => !current)}>
        <span className="gpt-editor-select-label">{options.find((item) => item.value === value)?.label ?? "Scope"}</span>
        <Icon name="chevron-down" className="header-mode-chevron" />
      </button>
      {open ? (
        <div className="header-mode-menu gpt-editor-select-menu" role="menu">
          {options.map((option) => (
            <button
              key={option.value}
              type="button"
              className={`header-mode-option gpt-editor-select-option${value === option.value ? " active" : ""}`}
              onClick={() => {
                onChange(option.value);
                setOpen(false);
              }}
            >
              <span className="gpt-editor-select-option-label">{option.label}</span>
              {value === option.value ? <Icon name="check" className="header-mode-option-check" /> : null}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function StatusFilterMenu({
  value,
  onChange,
  includeArchived,
}: {
  value: CourseStatusFilter;
  onChange: (next: CourseStatusFilter) => void;
  includeArchived: boolean;
}) {
  const [open, setOpen] = useState(false);
  const options: Array<{ value: CourseStatusFilter; label: string }> = [
    { value: "all", label: "All status" },
    { value: "draft", label: "Draft" },
    { value: "published", label: "Published" },
  ];
  if (includeArchived) {
    options.push({ value: "archived", label: "Archived" });
  }

  return (
    <div className={`gpt-editor-select${open ? " open" : ""}`}>
      <button type="button" className="gpt-editor-select-trigger" aria-expanded={open} onClick={() => setOpen((current) => !current)}>
        <span className="gpt-editor-select-label">{options.find((item) => item.value === value)?.label ?? "Status"}</span>
        <Icon name="chevron-down" className="header-mode-chevron" />
      </button>
      {open ? (
        <div className="header-mode-menu gpt-editor-select-menu" role="menu">
          {options.map((option) => (
            <button
              key={option.value}
              type="button"
              className={`header-mode-option gpt-editor-select-option${value === option.value ? " active" : ""}`}
              onClick={() => {
                onChange(option.value);
                setOpen(false);
              }}
            >
              <span className="gpt-editor-select-option-label">{option.label}</span>
              {value === option.value ? <Icon name="check" className="header-mode-option-check" /> : null}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function CoursesPage({
  courses,
  loading,
  error,
  importing,
  canCreateGlobal,
  canUploadPaths,
  currentUserId,
  onLoad,
  onLoadDetails,
  onUpdateNodeProgress,
  onImport,
  onDownloadTemplate,
  onStartContinue,
  onToggleArchived,
  onDeleteCourse,
}: CoursesPageProps) {
  const [search, setSearch] = useState("");
  const [scope, setScope] = useState<CourseScopeFilter>("all");
  const [status, setStatus] = useState<CourseStatusFilter>("all");
  const [sort, setSort] = useState<CourseSort>("updated_desc");
  const [importOpen, setImportOpen] = useState(false);
  const [selectedCourseId, setSelectedCourseId] = useState<string | null>(null);
  const [menuCourseId, setMenuCourseId] = useState<string | null>(null);
  const [menuCoursePosition, setMenuCoursePosition] = useState<{ top: number; left: number } | null>(null);
  const [detailsByCourseId, setDetailsByCourseId] = useState<Record<string, LearningPath>>({});
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);

  useEffect(() => {
    void onLoad({ search, scope, status, sort });
    // Intentionally exclude onLoad to avoid request loops from changing function identity.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, scope, status, sort]);

  useEffect(() => {
    if (!canCreateGlobal && status === "archived") {
      setStatus("all");
    }
  }, [canCreateGlobal, status]);

  const selectedCourse = useMemo(() => {
    if (!selectedCourseId) {
      return null;
    }
    return courses.find((course) => course.id === selectedCourseId) ?? null;
  }, [courses, selectedCourseId]);

  const selectedDetails = selectedCourseId ? detailsByCourseId[selectedCourseId] ?? null : null;
  const chapterColorById = useMemo(() => {
    if (!selectedDetails) {
      return {};
    }
    const map: Record<string, string> = {};
    selectedDetails.chapters
      .slice()
      .sort((left, right) => left.order_index - right.order_index)
      .forEach((chapter, index) => {
        map[chapter.id] = CHAPTER_COLORS[index % CHAPTER_COLORS.length];
      });
    return map;
  }, [selectedDetails]);
  const branchById = useMemo(() => {
    if (!selectedDetails) {
      return {} as Record<string, { title: string; required: boolean }>;
    }
    return Object.fromEntries(selectedDetails.branches.map((branch) => [branch.id, { title: branch.title, required: branch.required }]));
  }, [selectedDetails]);
  const selectedNode = useMemo(() => {
    if (!selectedDetails || selectedDetails.nodes.length === 0) {
      return null;
    }
    if (!selectedNodeId) {
      return selectedDetails.nodes[0];
    }
    return selectedDetails.nodes.find((node) => node.id === selectedNodeId) ?? selectedDetails.nodes[0];
  }, [selectedDetails, selectedNodeId]);
  const autoNodePositions = useMemo(() => {
    if (!selectedDetails || selectedDetails.nodes.length === 0) {
      return {} as Record<string, { x: number; y: number }>;
    }

    const chapterOrder = selectedDetails.chapters
      .slice()
      .sort((left, right) => left.order_index - right.order_index)
      .map((chapter) => chapter.id);
    const chapterIndex = new Map<string, number>(chapterOrder.map((id, index) => [id, index]));

    const nodesById = new Map(selectedDetails.nodes.map((node) => [node.id, node]));
    const hardIncoming = new Map<string, Set<string>>();
    const hardOutgoing = new Map<string, Set<string>>();
    const ensureMaps = (id: string) => {
      if (!hardIncoming.has(id)) {
        hardIncoming.set(id, new Set());
      }
      if (!hardOutgoing.has(id)) {
        hardOutgoing.set(id, new Set());
      }
    };
    selectedDetails.nodes.forEach((node) => ensureMaps(node.id));

    const addHardDependency = (fromId: string, toId: string) => {
      if (!nodesById.has(fromId) || !nodesById.has(toId) || fromId === toId) {
        return;
      }
      ensureMaps(fromId);
      ensureMaps(toId);
      hardIncoming.get(toId)?.add(fromId);
      hardOutgoing.get(fromId)?.add(toId);
    };

    selectedDetails.edges.forEach((edge) => {
      if (edge.relationship === "requires_all" || edge.relationship === "requires_any") {
        addHardDependency(edge.from_node_id, edge.to_node_id);
      }
    });

    selectedDetails.nodes.forEach((node) => {
      node.prerequisites.requires_all.forEach((depId) => addHardDependency(depId, node.id));
      node.prerequisites.requires_any.forEach((depId) => addHardDependency(depId, node.id));
    });

    const indegree = new Map<string, number>();
    selectedDetails.nodes.forEach((node) => indegree.set(node.id, hardIncoming.get(node.id)?.size ?? 0));
    const queue: string[] = selectedDetails.nodes
      .filter((node) => (indegree.get(node.id) ?? 0) === 0)
      .sort((left, right) => left.title.localeCompare(right.title))
      .map((node) => node.id);

    const level = new Map<string, number>();
    selectedDetails.nodes.forEach((node) => level.set(node.id, 0));

    while (queue.length > 0) {
      const current = queue.shift()!;
      const currentLevel = level.get(current) ?? 0;
      (hardOutgoing.get(current) ?? new Set()).forEach((target) => {
        level.set(target, Math.max(level.get(target) ?? 0, currentLevel + 1));
        const nextIndegree = (indegree.get(target) ?? 0) - 1;
        indegree.set(target, nextIndegree);
        if (nextIndegree === 0) {
          queue.push(target);
        }
      });
    }

    const byLevel = new Map<number, string[]>();
    selectedDetails.nodes.forEach((node) => {
      const lane = level.get(node.id) ?? 0;
      if (!byLevel.has(lane)) {
        byLevel.set(lane, []);
      }
      byLevel.get(lane)!.push(node.id);
    });

    const positions: Record<string, { x: number; y: number }> = {};
    const sortedLevels = Array.from(byLevel.entries()).sort((left, right) => left[0] - right[0]);
    const maxNodesPerLevel = Math.max(1, ...sortedLevels.map(([, ids]) => ids.length));

    sortedLevels.forEach(([lane, ids]) => {
      const sortedIds = ids.slice().sort((leftId, rightId) => {
        const leftNode = nodesById.get(leftId)!;
        const rightNode = nodesById.get(rightId)!;
        const leftChapter = chapterIndex.get(leftNode.chapter_id ?? "") ?? chapterOrder.length;
        const rightChapter = chapterIndex.get(rightNode.chapter_id ?? "") ?? chapterOrder.length;
        if (leftChapter !== rightChapter) {
          return leftChapter - rightChapter;
        }
        return leftNode.title.localeCompare(rightNode.title);
      });

      const topOffset = TOP_PADDING + ((maxNodesPerLevel - sortedIds.length) * V_SPACING) / 2;
      sortedIds.forEach((id, rowIndex) => {
        positions[id] = {
          x: LEFT_PADDING + lane * H_SPACING,
          y: topOffset + rowIndex * V_SPACING,
        };
      });
    });

    return positions;
  }, [selectedDetails]);
  const positionedNodes = useMemo(() => {
    if (!selectedDetails) {
      return [];
    }
    return selectedDetails.nodes.map((node) => ({
      node,
      position: autoNodePositions[node.id] ?? { x: LEFT_PADDING, y: TOP_PADDING },
    }));
  }, [autoNodePositions, selectedDetails]);
  const positionedNodeById = useMemo(() => {
    const map = new Map<string, { x: number; y: number }>();
    for (const item of positionedNodes) {
      map.set(item.node.id, item.position);
    }
    return map;
  }, [positionedNodes]);
  const skilltreeBoardSize = useMemo(() => {
    if (positionedNodes.length === 0) {
      return { width: 960, height: 520 };
    }
    const maxX = Math.max(...positionedNodes.map((item) => item.position.x + NODE_ICON_SIZE + LEFT_PADDING));
    const maxY = Math.max(...positionedNodes.map((item) => item.position.y + NODE_ICON_SIZE + TOP_PADDING));
    return {
      width: Math.max(960, maxX),
      height: Math.max(520, maxY),
    };
  }, [positionedNodes]);

  useEffect(() => {
    if (!selectedCourseId) {
      return;
    }
    if (!courses.some((course) => course.id === selectedCourseId)) {
      setSelectedCourseId(null);
    }
  }, [courses, selectedCourseId]);

  useEffect(() => {
    if (!menuCourseId) {
      return;
    }
    const onDocumentClick = () => {
      setMenuCourseId(null);
      setMenuCoursePosition(null);
    };
    const closeOnResize = () => {
      setMenuCourseId(null);
      setMenuCoursePosition(null);
    };
    window.addEventListener("click", onDocumentClick);
    window.addEventListener("resize", closeOnResize);
    window.addEventListener("scroll", closeOnResize, true);
    return () => {
      window.removeEventListener("click", onDocumentClick);
      window.removeEventListener("resize", closeOnResize);
      window.removeEventListener("scroll", closeOnResize, true);
    };
  }, [menuCourseId]);

  useEffect(() => {
    if (!selectedCourseId) {
      return;
    }
    void onLoadDetails(selectedCourseId)
      .then((payload) => {
        setDetailsByCourseId((current) => ({ ...current, [selectedCourseId]: payload }));
      })
      .catch(() => undefined);
  }, [onLoadDetails, selectedCourse?.updated_at, selectedCourseId]);

  useEffect(() => {
    if (!selectedDetails || selectedDetails.nodes.length === 0) {
      setSelectedNodeId(null);
      return;
    }
    if (!selectedNodeId || !selectedDetails.nodes.some((node) => node.id === selectedNodeId)) {
      setSelectedNodeId(selectedDetails.nodes[0].id);
    }
  }, [selectedDetails, selectedNodeId]);

  useEffect(() => {
    setZoom(1);
  }, [selectedCourseId]);

  return (
    <section className="chat-column library-column">
      {error ? <p className="chat-error chat-error-banner">{error}</p> : null}
      <section className="info-group-card library-table-card">
        <div className="library-table-header">
          <h4>Courses</h4>
        </div>

        <div className="courses-toolbar">
          <input
            className="dialog-input"
            type="search"
            placeholder="Search title or description"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          <ScopeFilterMenu value={scope} onChange={setScope} />
          <StatusFilterMenu value={status} onChange={setStatus} includeArchived={canCreateGlobal} />
          <SortMenu value={sort} onChange={setSort} />
        </div>

        <div className="library-table courses-table">
          {loading ? <div className="empty-state">Loading courses...</div> : null}
          {!loading ? (
            <>
              <div className="library-table-head courses-head">
                <span>Name</span>
                <span>Scope</span>
                <span>Owner</span>
                <span>Status</span>
                <span>Nodes</span>
                <span>Modules</span>
                <span>Lessons</span>
                <span>Updated</span>
                <span>Actions</span>
              </div>
              <div className="library-table-body">
                {courses.length === 0 ? <div className="empty-state">No courses found.</div> : null}
                {courses.map((course) => (
                  <div
                    key={course.id}
                    className={`library-table-row courses-row${selectedCourseId === course.id ? " active" : ""}`}
                    role="button"
                    tabIndex={0}
                    onClick={() => setSelectedCourseId(course.id)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        setSelectedCourseId(course.id);
                      }
                    }}
                  >
                    <span className="courses-title-cell">
                      <strong>{course.title}</strong>
                      <small>{course.description || "No description"}</small>
                    </span>
                    <span>{course.scope === "global" ? "Global" : "User"}</span>
                    <span>{course.owner_displayname || course.owner_username || (course.scope === "global" ? "System" : "-")}</span>
                    <span className={`learning-path-status learning-path-status-${course.status}`}>{course.status}</span>
                    <span>{course.node_count}</span>
                    <span>{course.module_count}</span>
                    <span>{course.lesson_count}</span>
                    <span className="library-updated-cell">
                      <strong>{new Date(course.updated_at).toLocaleDateString()}</strong>
                      <span>{new Date(course.updated_at).toLocaleTimeString()}</span>
                    </span>
                    <span className="courses-row-actions">
                      <button
                        className="course-icon-button play"
                        type="button"
                        title={course.status === "draft" ? "Start" : "Continue"}
                        aria-label={course.status === "draft" ? "Start course" : "Continue course"}
                        onClick={(event) => {
                          event.stopPropagation();
                          setSelectedCourseId(course.id);
                          if (!detailsByCourseId[course.id]) {
                            void onLoadDetails(course.id)
                              .then((payload) => setDetailsByCourseId((current) => ({ ...current, [course.id]: payload })));
                          }
                        }}
                      >
                        <Icon name="play" className="course-play-icon" />
                      </button>
                      {canCreateGlobal || course.owner_user_id === currentUserId ? (
                        <div className="courses-row-menu">
                          <button
                            className="course-icon-button"
                            type="button"
                            aria-label="Course menu"
                            aria-expanded={menuCourseId === course.id}
                            onClick={(event) => {
                              event.stopPropagation();
                              const triggerRect = (event.currentTarget as HTMLButtonElement).getBoundingClientRect();
                              const menuWidth = 184;
                              const estimatedMenuHeight = 150;
                              const spaceBelow = window.innerHeight - triggerRect.bottom;
                              const openUp = spaceBelow < estimatedMenuHeight;
                              const top = openUp ? triggerRect.top - estimatedMenuHeight - 6 : triggerRect.bottom + 6;
                              const left = Math.max(8, Math.min(window.innerWidth - menuWidth - 8, triggerRect.right - menuWidth));
                              setMenuCoursePosition({ top: Math.max(8, top), left });
                              setMenuCourseId((current) => (current === course.id ? null : course.id));
                            }}
                          >
                            <Icon name="dots" className="chat-menu-dots" />
                          </button>
                          {menuCourseId === course.id && menuCoursePosition ? (
                            <div
                              className="chat-item-actions-menu floating-menu"
                              role="menu"
                              onClick={(event) => event.stopPropagation()}
                              style={{ top: `${menuCoursePosition.top}px`, left: `${menuCoursePosition.left}px` }}
                            >
                              <button
                                className="chat-item-actions-option"
                                type="button"
                                onClick={() => {
                                  void onToggleArchived(course.id, course.status !== "archived");
                                  setMenuCourseId(null);
                                  setMenuCoursePosition(null);
                                }}
                              >
                                <Icon name="archive" />
                                {course.status === "archived" ? "Unarchive" : "Archive"}
                              </button>
                              <button className="chat-item-actions-option" type="button" onClick={() => setMenuCourseId(null)}>
                                <Icon name="edit" />
                                Edit
                              </button>
                              <button
                                className="chat-item-actions-option delete"
                                type="button"
                                onClick={() => {
                                  void onDeleteCourse(course.id);
                                  setMenuCourseId(null);
                                  setMenuCoursePosition(null);
                                }}
                              >
                                <Icon name="trash" />
                                Delete
                              </button>
                            </div>
                          ) : null}
                        </div>
                      ) : null}
                    </span>
                  </div>
                ))}
              </div>
            </>
          ) : null}
        </div>

        {canUploadPaths ? (
          <div className="library-table-footer courses-footer-actions">
            <button className="secondary-button" type="button" onClick={() => void onDownloadTemplate()}>
              Download Template
            </button>
            <button className="restart-button library-upload-button" type="button" onClick={() => setImportOpen(true)}>
              Add Paths
            </button>
          </div>
        ) : null}
      </section>

      {selectedCourse ? (
        <section className="info-group-card learning-path-details-card courses-details-card">
          <div className="learning-path-details-header">
            <h4>{selectedCourse.title}</h4>
            <p>{selectedCourse.description || "No description provided for this course."}</p>
            <div className="learning-path-details-meta">
              <span>{selectedCourse.scope === "global" ? "Global scope" : "User scope"}</span>
              <span>{selectedCourse.status}</span>
              <span>{selectedCourse.subject || "General"}</span>
              <span>{selectedCourse.difficulty_level || "n/a"}</span>
            </div>
          </div>
          <div className="learning-path-details-stats">
            <span className="learning-path-stat-card">
              <strong>{selectedCourse.node_count}</strong>
              <small>Nodes</small>
            </span>
            <span className="learning-path-stat-card">
              <strong>{selectedCourse.chapter_count}</strong>
              <small>Chapters</small>
            </span>
            <span className="learning-path-stat-card">
              <strong>{selectedCourse.module_count}</strong>
              <small>Modules</small>
            </span>
            <span className="learning-path-stat-card">
              <strong>{selectedCourse.lesson_count}</strong>
              <small>Lessons</small>
            </span>
          </div>
          <div className="skilltree-shell">
            {selectedDetails ? (
              selectedDetails.nodes.length === 0 ? (
                <div className="empty-state">No skilltree nodes configured yet.</div>
              ) : (
                <>
                  <div className="skilltree-main-column">
                    <div className="skilltree-board">
                      <div className="skilltree-zoom-controls">
                        <button className="secondary-button skilltree-zoom-button" type="button" onClick={() => setZoom((current) => Math.max(0.6, Number((current - 0.1).toFixed(2))))}>
                          -
                        </button>
                        <span className="skilltree-zoom-value">{Math.round(zoom * 100)}%</span>
                        <button className="secondary-button skilltree-zoom-button" type="button" onClick={() => setZoom((current) => Math.min(1.8, Number((current + 0.1).toFixed(2))))}>
                          +
                        </button>
                        <button className="secondary-button skilltree-zoom-reset" type="button" onClick={() => setZoom(1)}>
                          Reset
                        </button>
                      </div>
                      <div className="skilltree-canvas-viewport" style={{ width: `${skilltreeBoardSize.width}px`, height: `${skilltreeBoardSize.height}px` }}>
                        <div className="skilltree-canvas-scroll-space" style={{ width: `${skilltreeBoardSize.width * zoom}px`, height: `${skilltreeBoardSize.height * zoom}px` }}>
                          <div className="skilltree-canvas" style={{ width: `${skilltreeBoardSize.width}px`, height: `${skilltreeBoardSize.height}px`, transform: `scale(${zoom})`, transformOrigin: "top left" }}>
                          <svg className="skilltree-lines" viewBox={`0 0 ${skilltreeBoardSize.width} ${skilltreeBoardSize.height}`}>
                            {selectedDetails.edges.map((edge, index) => {
                              const fromPosition = positionedNodeById.get(edge.from_node_id);
                              const toPosition = positionedNodeById.get(edge.to_node_id);
                              const toNode = selectedDetails.nodes.find((node) => node.id === edge.to_node_id);
                              if (!fromPosition || !toPosition || !toNode) {
                                return null;
                              }
                              const isRecommended = edge.relationship === "recommended";
                              const edgeColor = chapterColorById[toNode.chapter_id ?? ""] ?? "#94a3b8";
                              return (
                                <line
                                  key={`${edge.from_node_id}-${edge.to_node_id}-${edge.relationship}-${index}`}
                                  x1={fromPosition.x + NODE_CENTER_X}
                                  y1={fromPosition.y + NODE_CENTER_Y}
                                  x2={toPosition.x + NODE_CENTER_X}
                                  y2={toPosition.y + NODE_CENTER_Y}
                                  className={`skilltree-edge${isRecommended ? " recommended" : ""}`}
                                  style={{ stroke: edgeColor }}
                                />
                              );
                            })}
                          </svg>
                          {positionedNodes.map(({ node, position }) => {
                            const state = selectedDetails.node_progress[node.id] ?? "locked";
                            const isSelected = selectedNode?.id === node.id;
                            const chapterColor = chapterColorById[node.chapter_id ?? ""] ?? "#94a3b8";
                            const nodeIcon: "play" | "check" | "archive" | "academic-hat" | "book" =
                              node.type === "practice"
                                ? "play"
                                : node.type === "quiz"
                                  ? "check"
                                  : node.type === "checkpoint"
                                    ? "check"
                                    : node.type === "unlock_gate"
                                      ? "archive"
                                      : node.type === "review"
                                        ? "archive"
                                        : node.type === "milestone"
                                          ? "academic-hat"
                                          : node.type === "capstone"
                                            ? "academic-hat"
                                            : node.type === "assessment_hook"
                                              ? "archive"
                                              : "book";
                            return (
                              <button
                                key={node.id}
                                type="button"
                                data-node-type={node.type}
                                data-node-mode={node.completion_mode}
                                className={`skilltree-node skilltree-node-${state} skilltree-node-type-${node.type}${node.required ? "" : " optional"}${isSelected ? " selected" : ""}`}
                                style={{ left: `${position.x}px`, top: `${position.y}px` }}
                                onClick={() => setSelectedNodeId(node.id)}
                                title={`${node.title} (${state.replace("_", " ")})`}
                                aria-label={`${node.title} (${state.replace("_", " ")})`}
                              >
                                <span className="skilltree-node-icon-shell" style={{ borderColor: chapterColor, color: chapterColor }}>
                                  <Icon name={nodeIcon} className="skilltree-node-icon" />
                                </span>
                              </button>
                            );
                          })}
                          </div>
                        </div>
                      </div>
                  </div>
                  <div className="skilltree-completion-block">
                    {selectedDetails.chapter_progress.length > 0 ? (
                      <div className="skilltree-chapter-progress-strip">
                        {selectedDetails.chapter_progress.map((chapter) => (
                          <span key={chapter.chapter_id} className="skilltree-chapter-progress-item">
                            <span className="skilltree-chapter-progress-value" style={{ color: chapterColorById[chapter.chapter_id] ?? "#94a3b8" }}>
                              {chapter.required_completed}/{chapter.required_total}
                            </span>
                            <span className="skilltree-chapter-progress-label">{chapter.title}</span>
                          </span>
                        ))}
                      </div>
                    ) : null}
                  </div>
                </div>
                <aside className="skilltree-sidepanel">
                    {selectedNode ? (
                      <>
                        <h5>{selectedNode.title}</h5>
                        <p>{selectedNode.description || "No description provided for this node."}</p>
                        <div className="skilltree-sidepanel-meta">
                          <span>{selectedNode.type.replace("_", " ")}</span>
                          <span>{selectedNode.completion_mode.replace("_", " ")}</span>
                          <span>{selectedNode.required ? "Required" : "Optional"}</span>
                          <span>{selectedDetails.node_progress[selectedNode.id] ?? "locked"}</span>
                          {selectedDetails.node_runtime[selectedNode.id]?.is_parallel_available ? <span>Parallel available</span> : null}
                          {selectedDetails.node_runtime[selectedNode.id]?.awaiting_checkpoint ? <span>Checkpoint pending</span> : null}
                          {selectedDetails.node_runtime[selectedNode.id]?.capstone_locked ? <span>Capstone locked</span> : null}
                          <span>{selectedNode.estimated_duration_minutes ? `${selectedNode.estimated_duration_minutes} min` : "Duration n/a"}</span>
                        </div>
                        <div className="skilltree-sidepanel-list">
                          <strong>Branch & Role</strong>
                          <p>
                            Branch: {selectedNode.branch_id ? branchById[selectedNode.branch_id]?.title ?? selectedNode.branch_id : "none"}
                            <br />
                            Completion role: {selectedNode.type === "capstone" ? "capstone" : selectedNode.required ? "required" : "optional"}
                          </p>
                        </div>
                        <div className="skilltree-sidepanel-list">
                          <strong>Prerequisites</strong>
                          <p>
                            All: {selectedNode.prerequisites.requires_all.join(", ") || "none"}
                            <br />
                            Any: {selectedNode.prerequisites.requires_any.join(", ") || "none"}
                            <br />
                            Recommended: {selectedNode.prerequisites.recommended.join(", ") || "none"}
                          </p>
                        </div>
                        <div className="skilltree-sidepanel-list">
                          <strong>KSA Links</strong>
                          {selectedNode.ksa.length === 0 ? (
                            <p>None mapped.</p>
                          ) : (
                            selectedNode.ksa.map((item, index) => (
                              <p key={`${selectedNode.id}-ksa-${index}`}>
                                {item.dimension} · {item.topic}
                                {item.subtopic ? ` · ${item.subtopic}` : ""}
                                {item.start_level ? ` · start ${item.start_level}` : ""}
                                {item.target_level ? ` · target ${item.target_level}` : ""}
                                {item.contribution_weight ? ` · weight ${item.contribution_weight}` : ""}
                                {item.unlocks_assessment_check ? " · unlocks KSA check" : ""}
                                {item.recommends_assessment_check ? " · recommends KSA check" : ""}
                              </p>
                            ))
                          )}
                        </div>
                        <div className="skilltree-sidepanel-list">
                          <strong>Unlocks & Rewards</strong>
                          <p>none</p>
                        </div>
                        <div className="skilltree-sidepanel-list">
                          <strong>Hooks & Adaptation</strong>
                          <p>
                            Retrospective: {selectedNode.retrospective_hooks.retrospective_after ? "after node" : "none"}
                            <br />
                            Review signal: {selectedNode.retrospective_hooks.review_recommended ? "recommended" : "none"}
                            <br />
                            KSA mini-check: {selectedNode.ksa_hooks.mini_assessment_available ? "available" : "none"}
                            <br />
                            Remediation: {selectedNode.remediation.is_remediation_node ? "yes" : "no"}
                            <br />
                            Adaptive unlock prep: {selectedNode.adaptive_unlock.recommended_only ? "recommended only" : "gated/required ready"}
                          </p>
                        </div>
                        {selectedDetails.completion_summary ? (
                          <div className="skilltree-sidepanel-list">
                            <strong>Course Progress</strong>
                            <p>
                              Required branches: {selectedDetails.completion_summary.required_branch_completed}/{selectedDetails.completion_summary.required_branch_total}
                              <br />
                              Global capstones: {selectedDetails.completion_summary.global_capstone_completed}/{selectedDetails.completion_summary.global_capstone_total}
                              <br />
                              Required nodes: {selectedDetails.completion_summary.required_completed}/{selectedDetails.completion_summary.required_total}
                            </p>
                          </div>
                        ) : null}
                        <div className="skilltree-sidepanel-list">
                          <strong>Course Hooks</strong>
                          <p>none</p>
                        </div>
                        {(() => {
                          const runtime = selectedDetails.node_runtime[selectedNode.id];
                          const state = selectedDetails.node_progress[selectedNode.id] ?? "locked";
                          const prereqsSatisfied = runtime ? runtime.blocked_by_all.length === 0 && runtime.blocked_by_any.length === 0 : false;
                          const showActions = prereqsSatisfied && state !== "locked" && state !== "awaiting_checkpoint";
                          const canReset = state === "in_progress" || state === "completed";
                          const actionLabel = state === "in_progress" ? "Continue" : "Start";
                          if (!showActions) {
                            return null;
                          }
                          return (
                            <div className="skilltree-sidepanel-actions-row">
                              {canReset ? (
                                <button
                                  className="skilltree-icon-action"
                                  type="button"
                                  title="Reset"
                                  aria-label="Reset node progress"
                                  onClick={() => {
                                    void onUpdateNodeProgress(selectedCourse.id, selectedNode.id, { status: "reset" })
                                      .then((payload) => setDetailsByCourseId((current) => ({ ...current, [selectedCourse.id]: payload })));
                                  }}
                                >
                                  <Icon name="reset" />
                                </button>
                              ) : null}
                              {!selectedNode.required ? (
                                <button
                                  className="skilltree-icon-action"
                                  type="button"
                                  title="Skip"
                                  aria-label="Skip optional node"
                                  onClick={() => {
                                    void onUpdateNodeProgress(selectedCourse.id, selectedNode.id, { status: "optional_skipped" })
                                      .then((payload) => setDetailsByCourseId((current) => ({ ...current, [selectedCourse.id]: payload })));
                                  }}
                                >
                                  <Icon name="archive" />
                                </button>
                              ) : null}
                              <button
                                className="skilltree-icon-action primary"
                                type="button"
                                title={actionLabel}
                                aria-label={`${actionLabel} node`}
                                onClick={() => {
                                  void onUpdateNodeProgress(selectedCourse.id, selectedNode.id, { status: "in_progress" })
                                    .then((payload) => setDetailsByCourseId((current) => ({ ...current, [selectedCourse.id]: payload })))
                                    .then(() => onStartContinue(selectedCourse.id, selectedNode.id));
                                }}
                              >
                                <Icon name="play" />
                                <span>{actionLabel}</span>
                              </button>
                            </div>
                          );
                        })()}
                      </>
                    ) : (
                      <p>Select a node to inspect details.</p>
                    )}
                  </aside>
                </>
              )
            ) : (
              <div className="empty-state">Loading course details...</div>
            )}
          </div>
        </section>
      ) : null}

      {importOpen ? (
        <CourseImportDialog
          importing={importing}
          canCreateGlobal={canCreateGlobal}
          onClose={() => setImportOpen(false)}
          onImport={onImport}
        />
      ) : null}
    </section>
  );
}

function CourseImportDialog({
  importing,
  canCreateGlobal,
  onClose,
  onImport,
}: {
  importing: boolean;
  canCreateGlobal: boolean;
  onClose: () => void;
  onImport: (files: File[], scopesByFile: Record<string, "global" | "user">) => Promise<CourseImportResponse>;
}) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [scopesByFile, setScopesByFile] = useState<Record<string, "global" | "user">>({});
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CourseImportResponse | null>(null);

  const failedByName = useMemo(() => {
    const map = new Map<string, string>();
    for (const entry of result?.results ?? []) {
      if (!entry.success && entry.error) {
        map.set(entry.file_name, entry.error);
      }
    }
    return map;
  }, [result]);

  function handleSelectFiles(event: ChangeEvent<HTMLInputElement>) {
    const selected = Array.from(event.target.files ?? []);
    if (selected.length === 0) {
      return;
    }
    if (selected.length > 5) {
      setError("You can upload up to 5 JSON files at a time.");
      return;
    }
    const unique = new Set<string>();
    for (const file of selected) {
      if (!file.name.toLowerCase().endsWith(".json")) {
        setError(`Unsupported file type: ${file.name}`);
        return;
      }
      if (unique.has(file.name)) {
        setError(`Duplicate file selected: ${file.name}`);
        return;
      }
      unique.add(file.name);
    }
    setFiles(selected);
    setError(null);
    setResult(null);
    setScopesByFile((current) => {
      const next: Record<string, "global" | "user"> = {};
      for (const file of selected) {
        next[file.name] = current[file.name] ?? "user";
      }
      return next;
    });
  }

  async function handleImport() {
    setError(null);
    try {
      const payload = await onImport(files, scopesByFile);
      setResult(payload);
      if (payload.failed_count === 0) {
        onClose();
      }
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Import failed");
    }
  }

  return (
    <Dialog
      title="Add Paths"
      onClose={importing ? () => undefined : onClose}
      className="dialog-compact upload-dialog-compact"
      actions={
        <>
          <button className="secondary-button" type="button" disabled={importing} onClick={onClose}>
            Cancel
          </button>
          <button className="primary-button" type="button" disabled={files.length === 0 || importing} onClick={() => void handleImport()}>
            {importing ? "Adding..." : "Add"}
          </button>
        </>
      }
    >
      <div className="upload-dialog-body library-upload-modal">
        {files.length === 0 ? (
          <button className="upload-picker-button library-upload-add" type="button" disabled={importing} onClick={() => inputRef.current?.click()}>
            + Add Files
          </button>
        ) : (
          <div className="upload-file-list library-upload-list courses-upload-list">
            {files.map((file) => (
              <div key={file.name} className="upload-file-row library-upload-row courses-upload-row">
                <div>
                  <strong className="library-upload-name">{file.name}</strong>
                  <p>{file.size.toLocaleString()} bytes</p>
                  {failedByName.has(file.name) ? <p className="inline-error">{failedByName.get(file.name)}</p> : null}
                </div>
                <ScopeMenu
                  value={scopesByFile[file.name] ?? "user"}
                  canCreateGlobal={canCreateGlobal}
                  disabled={importing}
                  onChange={(value) => setScopesByFile((current) => ({ ...current, [file.name]: value }))}
                />
              </div>
            ))}
            <button className="secondary-button library-upload-add" type="button" disabled={importing} onClick={() => inputRef.current?.click()}>
              + Add Files
            </button>
          </div>
        )}
        <input ref={inputRef} type="file" hidden accept=".json,application/json" multiple onChange={handleSelectFiles} />
        {error ? <p className="inline-error">{error}</p> : null}
        {result?.failed_count ? <p className="inline-error">{result.imported_count} imported, {result.failed_count} failed.</p> : null}
      </div>
    </Dialog>
  );
}
