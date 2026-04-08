import { useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";
import type { CourseImportResponse, CourseListItem, CourseSort, LearningPath } from "../../types/chat";
import { Dialog } from "../common/Dialog";
import { Icon } from "../common/Icons";

type CourseScopeFilter = "all" | "global" | "user";
type CourseStatusFilter = "all" | "draft" | "published" | "archived";

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
  onImport: (files: File[], scopesByFile: Record<string, "global" | "user">) => Promise<CourseImportResponse>;
  onDownloadTemplate: () => Promise<unknown>;
  onStartContinue: (course: CourseListItem) => void;
  onToggleArchived: (courseId: string, nextArchived: boolean) => Promise<unknown>;
};

type ScopeMenuProps = {
  value: "global" | "user";
  canCreateGlobal: boolean;
  disabled: boolean;
  onChange: (value: "global" | "user") => void;
};

function ScopeMenu({ value, canCreateGlobal, disabled, onChange }: ScopeMenuProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className={`gpt-editor-select${open ? " open" : ""}`}>
      <button
        type="button"
        className="gpt-editor-select-trigger"
        aria-expanded={open}
        onClick={() => {
          if (!disabled) {
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
  onImport,
  onDownloadTemplate,
  onStartContinue,
  onToggleArchived,
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
    if (!selectedCourseId || detailsByCourseId[selectedCourseId]) {
      return;
    }
    void onLoadDetails(selectedCourseId)
      .then((payload) => {
        setDetailsByCourseId((current) => ({ ...current, [selectedCourseId]: payload }));
      })
      .catch(() => undefined);
  }, [detailsByCourseId, onLoadDetails, selectedCourseId]);

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
                          void onStartContinue(course);
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
                              <button className="chat-item-actions-option delete" type="button" onClick={() => setMenuCourseId(null)}>
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
              <strong>{selectedCourse.module_count}</strong>
              <small>Modules</small>
            </span>
            <span className="learning-path-stat-card">
              <strong>{selectedCourse.lesson_count}</strong>
              <small>Lessons</small>
            </span>
            <span className="learning-path-stat-card">
              <strong>{selectedCourse.owner_displayname || selectedCourse.owner_username || (selectedCourse.scope === "global" ? "System" : "-")}</strong>
              <small>Owner</small>
            </span>
            <span className="learning-path-stat-card">
              <strong>{new Date(selectedCourse.updated_at).toLocaleDateString()}</strong>
              <small>Updated</small>
            </span>
          </div>
          <div className="library-table learning-path-structure-table">
            {selectedDetails ? (
              <div className="library-table-body">
                {selectedDetails.modules.length === 0 ? (
                  <div className="empty-state">No modules configured yet.</div>
                ) : (
                  selectedDetails.modules
                    .slice()
                    .sort((left, right) => left.order_index - right.order_index)
                    .map((module, moduleIndex) => (
                      <div key={module.id} className="learning-path-module-block">
                        <div className="library-table-row learning-path-module-row">
                          <span className="learning-path-module-title-cell">
                            <strong>{moduleIndex + 1}. {module.title}</strong>
                            <small>{module.description || "No module description."}</small>
                          </span>
                          <span>{module.lessons.length} lessons</span>
                        </div>
                        {module.lessons
                          .slice()
                          .sort((left, right) => left.order_index - right.order_index)
                          .map((lesson) => (
                            <div key={lesson.id} className="library-table-row learning-path-lesson-row">
                              <span className="learning-path-lesson-title-cell">
                                <Icon name="book" className="learning-path-lesson-icon" />
                                <span className="learning-path-lesson-type">Lesson</span>
                                <span className="learning-path-lesson-title">{lesson.title}</span>
                              </span>
                              <span>{lesson.order_index + 1}</span>
                            </div>
                          ))}
                      </div>
                    ))
                )}
              </div>
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
          <div className="upload-file-list library-upload-list">
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
