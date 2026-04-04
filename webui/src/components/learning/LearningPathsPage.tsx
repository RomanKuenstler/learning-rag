import { useEffect, useMemo, useState } from "react";
import type { LearningLesson, LearningModule, LearningPath, LibraryFile, Role } from "../../types/chat";
import { Icon } from "../common/Icons";

type LearningPathDraft = {
  scope: "global" | "user";
  title: string;
  description: string;
  subject: string;
  difficulty_level: string;
  estimated_duration_minutes: string;
  status: "draft" | "published" | "archived";
  allowed_file_ids: number[];
  allowed_tags: string;
};

type LearningPathsPageProps = {
  role: Role;
  paths: LearningPath[];
  libraryFiles: LibraryFile[];
  loading: boolean;
  saving: boolean;
  error: string | null;
  canAuthor: boolean;
  onLoad: () => void;
  onCreatePath: (payload: {
    scope: "global" | "user";
    title: string;
    description: string;
    subject: string;
    difficulty_level: string;
    estimated_duration_minutes: number | null;
    status: "draft" | "published" | "archived";
    allowed_file_ids: number[];
    allowed_tags: string[];
  }) => Promise<unknown>;
  onUpdatePath: (
    pathId: string,
    payload: Partial<{
      title: string;
      description: string;
      subject: string;
      difficulty_level: string;
      estimated_duration_minutes: number | null;
      status: "draft" | "published" | "archived";
      allowed_file_ids: number[];
      allowed_tags: string[];
    }>,
  ) => Promise<unknown>;
  onDeletePath: (pathId: string) => Promise<unknown>;
  onCreateModule: (pathId: string, payload: { title: string; description: string; learning_objectives: string[] }) => Promise<unknown>;
  onUpdateModule: (
    pathId: string,
    moduleId: string,
    payload: Partial<{ title: string; description: string; learning_objectives: string[] }>,
  ) => Promise<unknown>;
  onDeleteModule: (pathId: string, moduleId: string) => Promise<unknown>;
  onReorderModules: (pathId: string, modules: LearningModule[]) => Promise<unknown>;
  onCreateLesson: (
    pathId: string,
    moduleId: string,
    payload: { title: string; description: string; objectives: string[]; teaching_notes: string },
  ) => Promise<unknown>;
  onUpdateLesson: (
    pathId: string,
    moduleId: string,
    lessonId: string,
    payload: Partial<{ title: string; description: string; objectives: string[]; teaching_notes: string }>,
  ) => Promise<unknown>;
  onDeleteLesson: (pathId: string, moduleId: string, lessonId: string) => Promise<unknown>;
  onReorderLessons: (pathId: string, moduleId: string, lessons: LearningLesson[]) => Promise<unknown>;
};

const EMPTY_DRAFT: LearningPathDraft = {
  scope: "user",
  title: "",
  description: "",
  subject: "",
  difficulty_level: "",
  estimated_duration_minutes: "",
  status: "draft",
  allowed_file_ids: [],
  allowed_tags: "",
};

export function LearningPathsPage({
  role,
  paths,
  libraryFiles,
  loading,
  saving,
  error,
  canAuthor,
  onLoad,
  onCreatePath,
  onUpdatePath,
  onDeletePath,
  onCreateModule,
  onUpdateModule,
  onDeleteModule,
  onReorderModules,
  onCreateLesson,
  onUpdateLesson,
  onDeleteLesson,
  onReorderLessons,
}: LearningPathsPageProps) {
  const [draft, setDraft] = useState<LearningPathDraft>(EMPTY_DRAFT);
  const [selectedPathId, setSelectedPathId] = useState<string | null>(null);

  useEffect(() => {
    void onLoad();
  }, [onLoad]);

  const selectedPath = useMemo(() => paths.find((item) => item.id === selectedPathId) ?? null, [paths, selectedPathId]);

  useEffect(() => {
    if (!selectedPathId && paths.length > 0) {
      setSelectedPathId(paths[0].id);
    }
  }, [paths, selectedPathId]);

  return (
    <section className="chat-column library-column">
      {error ? <p className="chat-error chat-error-banner">{error}</p> : null}
      <section className="info-group-card library-table-card">
        <div className="library-table-header">
          <h4>Learning paths</h4>
        </div>
        <div className="library-table">
          {loading ? <div className="empty-state">Loading learning paths...</div> : null}
          {!loading ? (
            <div className="library-table-body">
              {paths.length === 0 ? <div className="empty-state">No learning paths yet.</div> : null}
              {paths.map((path) => (
                <button
                  key={path.id}
                  type="button"
                  className={`side-nav-chat-item${selectedPathId === path.id ? " active" : ""}`}
                  onClick={() => setSelectedPathId(path.id)}
                >
                  <span>{path.title}</span>
                  <small>{path.scope === "global" ? "Global" : "User"}</small>
                </button>
              ))}
            </div>
          ) : null}
        </div>
      </section>

      {canAuthor ? (
        <section className="info-group-card">
          <h4>Create learning path</h4>
          <div className="settings-grid">
            <label>
              <span>Title</span>
              <input value={draft.title} onChange={(event) => setDraft((current) => ({ ...current, title: event.target.value }))} />
            </label>
            <label>
              <span>Description</span>
              <textarea value={draft.description} onChange={(event) => setDraft((current) => ({ ...current, description: event.target.value }))} />
            </label>
            <label>
              <span>Subject</span>
              <input value={draft.subject} onChange={(event) => setDraft((current) => ({ ...current, subject: event.target.value }))} />
            </label>
            <label>
              <span>Difficulty</span>
              <input value={draft.difficulty_level} onChange={(event) => setDraft((current) => ({ ...current, difficulty_level: event.target.value }))} />
            </label>
            <label>
              <span>Duration minutes</span>
              <input
                type="number"
                min={1}
                value={draft.estimated_duration_minutes}
                onChange={(event) => setDraft((current) => ({ ...current, estimated_duration_minutes: event.target.value }))}
              />
            </label>
            <label>
              <span>Status</span>
              <select value={draft.status} onChange={(event) => setDraft((current) => ({ ...current, status: event.target.value as LearningPathDraft["status"] }))}>
                <option value="draft">Draft</option>
                <option value="published">Published</option>
                <option value="archived">Archived</option>
              </select>
            </label>
            {role === "admin" ? (
              <label>
                <span>Scope</span>
                <select value={draft.scope} onChange={(event) => setDraft((current) => ({ ...current, scope: event.target.value as LearningPathDraft["scope"] }))}>
                  <option value="user">User</option>
                  <option value="global">Global</option>
                </select>
              </label>
            ) : null}
            <label>
              <span>Allowed tags (comma-separated)</span>
              <input value={draft.allowed_tags} onChange={(event) => setDraft((current) => ({ ...current, allowed_tags: event.target.value }))} />
            </label>
            <div>
              <span>Allowed files</span>
              <div className="archive-list">
                {libraryFiles.map((file) => {
                  const checked = draft.allowed_file_ids.includes(file.id);
                  return (
                    <label key={file.id} className="archive-row">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={(event) => {
                          setDraft((current) => ({
                            ...current,
                            allowed_file_ids: event.target.checked
                              ? [...current.allowed_file_ids, file.id]
                              : current.allowed_file_ids.filter((item) => item !== file.id),
                          }));
                        }}
                      />
                      <span>{file.file_name}</span>
                    </label>
                  );
                })}
              </div>
            </div>
          </div>
          <div className="library-table-footer">
            <button
              className="primary-button"
              disabled={saving || !draft.title.trim()}
              onClick={async () => {
                await onCreatePath({
                  scope: draft.scope,
                  title: draft.title.trim(),
                  description: draft.description.trim(),
                  subject: draft.subject.trim(),
                  difficulty_level: draft.difficulty_level.trim(),
                  estimated_duration_minutes: draft.estimated_duration_minutes ? Number(draft.estimated_duration_minutes) : null,
                  status: draft.status,
                  allowed_file_ids: draft.allowed_file_ids,
                  allowed_tags: draft.allowed_tags.split(",").map((item) => item.trim()).filter(Boolean),
                });
                setDraft(EMPTY_DRAFT);
              }}
            >
              Create
            </button>
          </div>
        </section>
      ) : null}

      {selectedPath ? (
        <LearningPathEditor
          path={selectedPath}
          libraryFiles={libraryFiles}
          saving={saving}
          onUpdatePath={onUpdatePath}
          onDeletePath={onDeletePath}
          onCreateModule={onCreateModule}
          onUpdateModule={onUpdateModule}
          onDeleteModule={onDeleteModule}
          onReorderModules={onReorderModules}
          onCreateLesson={onCreateLesson}
          onUpdateLesson={onUpdateLesson}
          onDeleteLesson={onDeleteLesson}
          onReorderLessons={onReorderLessons}
        />
      ) : null}
    </section>
  );
}

function LearningPathEditor({
  path,
  libraryFiles,
  saving,
  onUpdatePath,
  onDeletePath,
  onCreateModule,
  onUpdateModule,
  onDeleteModule,
  onReorderModules,
  onCreateLesson,
  onUpdateLesson,
  onDeleteLesson,
  onReorderLessons,
}: {
  path: LearningPath;
  libraryFiles: LibraryFile[];
  saving: boolean;
  onUpdatePath: LearningPathsPageProps["onUpdatePath"];
  onDeletePath: LearningPathsPageProps["onDeletePath"];
  onCreateModule: LearningPathsPageProps["onCreateModule"];
  onUpdateModule: LearningPathsPageProps["onUpdateModule"];
  onDeleteModule: LearningPathsPageProps["onDeleteModule"];
  onReorderModules: LearningPathsPageProps["onReorderModules"];
  onCreateLesson: LearningPathsPageProps["onCreateLesson"];
  onUpdateLesson: LearningPathsPageProps["onUpdateLesson"];
  onDeleteLesson: LearningPathsPageProps["onDeleteLesson"];
  onReorderLessons: LearningPathsPageProps["onReorderLessons"];
}) {
  const [title, setTitle] = useState(path.title);
  const [description, setDescription] = useState(path.description);
  const [subject, setSubject] = useState(path.subject);
  const [difficulty, setDifficulty] = useState(path.difficulty_level);
  const [duration, setDuration] = useState(path.estimated_duration_minutes?.toString() ?? "");
  const [status, setStatus] = useState(path.status as "draft" | "published" | "archived");
  const [allowedTags, setAllowedTags] = useState(path.allowed_tags.join(", "));
  const [allowedFiles, setAllowedFiles] = useState<number[]>(path.allowed_file_ids);
  const [newModuleTitle, setNewModuleTitle] = useState("");

  useEffect(() => {
    setTitle(path.title);
    setDescription(path.description);
    setSubject(path.subject);
    setDifficulty(path.difficulty_level);
    setDuration(path.estimated_duration_minutes?.toString() ?? "");
    setStatus(path.status as "draft" | "published" | "archived");
    setAllowedTags(path.allowed_tags.join(", "));
    setAllowedFiles(path.allowed_file_ids);
  }, [path]);

  return (
    <section className="info-group-card">
      <h4>{path.title}</h4>
      <div className="settings-grid">
        <label>
          <span>Title</span>
          <input value={title} disabled={!path.can_edit} onChange={(event) => setTitle(event.target.value)} />
        </label>
        <label>
          <span>Description</span>
          <textarea value={description} disabled={!path.can_edit} onChange={(event) => setDescription(event.target.value)} />
        </label>
        <label>
          <span>Subject</span>
          <input value={subject} disabled={!path.can_edit} onChange={(event) => setSubject(event.target.value)} />
        </label>
        <label>
          <span>Difficulty</span>
          <input value={difficulty} disabled={!path.can_edit} onChange={(event) => setDifficulty(event.target.value)} />
        </label>
        <label>
          <span>Duration minutes</span>
          <input type="number" min={1} value={duration} disabled={!path.can_edit} onChange={(event) => setDuration(event.target.value)} />
        </label>
        <label>
          <span>Status</span>
          <select value={status} disabled={!path.can_edit} onChange={(event) => setStatus(event.target.value as "draft" | "published" | "archived")}>
            <option value="draft">Draft</option>
            <option value="published">Published</option>
            <option value="archived">Archived</option>
          </select>
        </label>
        <label>
          <span>Allowed tags</span>
          <input value={allowedTags} disabled={!path.can_edit} onChange={(event) => setAllowedTags(event.target.value)} />
        </label>
        <div>
          <span>Allowed files</span>
          <div className="archive-list">
            {libraryFiles.map((file) => (
              <label key={file.id} className="archive-row">
                <input
                  type="checkbox"
                  checked={allowedFiles.includes(file.id)}
                  disabled={!path.can_edit}
                  onChange={(event) => {
                    if (!path.can_edit) {
                      return;
                    }
                    setAllowedFiles((current) =>
                      event.target.checked ? [...current, file.id] : current.filter((item) => item !== file.id),
                    );
                  }}
                />
                <span>{file.file_name}</span>
              </label>
            ))}
          </div>
        </div>
      </div>
      {path.can_edit ? (
        <div className="library-table-footer">
          <button
            className="primary-button"
            disabled={saving}
            onClick={() =>
              void onUpdatePath(path.id, {
                title: title.trim(),
                description: description.trim(),
                subject: subject.trim(),
                difficulty_level: difficulty.trim(),
                estimated_duration_minutes: duration ? Number(duration) : null,
                status,
                allowed_file_ids: allowedFiles,
                allowed_tags: allowedTags.split(",").map((item) => item.trim()).filter(Boolean),
              })
            }
          >
            Save path
          </button>
          {path.can_delete ? (
            <button className="danger-button" disabled={saving} onClick={() => void onDeletePath(path.id)}>
              Delete path
            </button>
          ) : null}
        </div>
      ) : null}

      <div className="library-table-header">
        <h4>Modules</h4>
      </div>
      <div className="library-table-body">
        {path.modules.map((module, moduleIndex) => (
          <LearningModuleEditor
            key={module.id}
            pathId={path.id}
            module={module}
            moduleIndex={moduleIndex}
            moduleCount={path.modules.length}
            canEdit={path.can_edit}
            saving={saving}
            onUpdateModule={onUpdateModule}
            onDeleteModule={onDeleteModule}
            onReorderModules={() => onReorderModules(path.id, path.modules)}
            onCreateLesson={onCreateLesson}
            onUpdateLesson={onUpdateLesson}
            onDeleteLesson={onDeleteLesson}
            onReorderLessons={onReorderLessons}
            onMoveUp={() => {
              const next = [...path.modules];
              [next[moduleIndex - 1], next[moduleIndex]] = [next[moduleIndex], next[moduleIndex - 1]];
              void onReorderModules(path.id, next);
            }}
            onMoveDown={() => {
              const next = [...path.modules];
              [next[moduleIndex + 1], next[moduleIndex]] = [next[moduleIndex], next[moduleIndex + 1]];
              void onReorderModules(path.id, next);
            }}
          />
        ))}
      </div>
      {path.can_edit ? (
        <div className="library-table-footer">
          <input value={newModuleTitle} placeholder="New module title" onChange={(event) => setNewModuleTitle(event.target.value)} />
          <button
            className="secondary-button"
            disabled={saving || !newModuleTitle.trim()}
            onClick={async () => {
              await onCreateModule(path.id, { title: newModuleTitle.trim(), description: "", learning_objectives: [] });
              setNewModuleTitle("");
            }}
          >
            Add module
          </button>
        </div>
      ) : null}
    </section>
  );
}

function LearningModuleEditor({
  pathId,
  module,
  moduleIndex,
  moduleCount,
  canEdit,
  saving,
  onUpdateModule,
  onDeleteModule,
  onCreateLesson,
  onUpdateLesson,
  onDeleteLesson,
  onReorderLessons,
  onMoveUp,
  onMoveDown,
}: {
  pathId: string;
  module: LearningModule;
  moduleIndex: number;
  moduleCount: number;
  canEdit: boolean;
  saving: boolean;
  onUpdateModule: LearningPathsPageProps["onUpdateModule"];
  onDeleteModule: LearningPathsPageProps["onDeleteModule"];
  onReorderModules: () => Promise<unknown>;
  onCreateLesson: LearningPathsPageProps["onCreateLesson"];
  onUpdateLesson: LearningPathsPageProps["onUpdateLesson"];
  onDeleteLesson: LearningPathsPageProps["onDeleteLesson"];
  onReorderLessons: LearningPathsPageProps["onReorderLessons"];
  onMoveUp: () => void;
  onMoveDown: () => void;
}) {
  const [title, setTitle] = useState(module.title);
  const [description, setDescription] = useState(module.description);
  const [objectives, setObjectives] = useState(module.learning_objectives.join(", "));
  const [newLessonTitle, setNewLessonTitle] = useState("");

  useEffect(() => {
    setTitle(module.title);
    setDescription(module.description);
    setObjectives(module.learning_objectives.join(", "));
  }, [module]);

  return (
    <div className="archive-row">
      <div className="archive-row-main">
        <strong>Module {moduleIndex + 1}: {module.title}</strong>
        <div className="archive-row-actions">
          {canEdit ? (
            <>
              <button className="secondary-button" disabled={saving || moduleIndex === 0} onClick={onMoveUp}>
                <Icon name="arrow-up" />
              </button>
              <button className="secondary-button" disabled={saving || moduleIndex >= moduleCount - 1} onClick={onMoveDown}>
                <Icon name="arrow-up" className="rotate-180" />
              </button>
            </>
          ) : null}
        </div>
      </div>
      <div className="settings-grid">
        <input value={title} disabled={!canEdit} onChange={(event) => setTitle(event.target.value)} />
        <textarea value={description} disabled={!canEdit} onChange={(event) => setDescription(event.target.value)} />
        <input value={objectives} disabled={!canEdit} onChange={(event) => setObjectives(event.target.value)} placeholder="Objectives comma-separated" />
      </div>
      {canEdit ? (
        <div className="archive-row-actions">
          <button
            className="secondary-button"
            disabled={saving}
            onClick={() =>
              void onUpdateModule(pathId, module.id, {
                title: title.trim(),
                description: description.trim(),
                learning_objectives: objectives.split(",").map((item) => item.trim()).filter(Boolean),
              })
            }
          >
            Save module
          </button>
          <button className="danger-button" disabled={saving} onClick={() => void onDeleteModule(pathId, module.id)}>
            Delete module
          </button>
        </div>
      ) : null}

      <div className="archive-list">
        {module.lessons.map((lesson, lessonIndex) => (
          <LearningLessonEditor
            key={lesson.id}
            pathId={pathId}
            moduleId={module.id}
            lesson={lesson}
            lessonIndex={lessonIndex}
            lessonCount={module.lessons.length}
            canEdit={canEdit}
            saving={saving}
            onUpdateLesson={onUpdateLesson}
            onDeleteLesson={onDeleteLesson}
            onMoveUp={() => {
              const next = [...module.lessons];
              [next[lessonIndex - 1], next[lessonIndex]] = [next[lessonIndex], next[lessonIndex - 1]];
              void onReorderLessons(pathId, module.id, next);
            }}
            onMoveDown={() => {
              const next = [...module.lessons];
              [next[lessonIndex + 1], next[lessonIndex]] = [next[lessonIndex], next[lessonIndex + 1]];
              void onReorderLessons(pathId, module.id, next);
            }}
          />
        ))}
      </div>
      {canEdit ? (
        <div className="archive-row-actions">
          <input value={newLessonTitle} placeholder="New lesson title" onChange={(event) => setNewLessonTitle(event.target.value)} />
          <button
            className="secondary-button"
            disabled={saving || !newLessonTitle.trim()}
            onClick={async () => {
              await onCreateLesson(pathId, module.id, {
                title: newLessonTitle.trim(),
                description: "",
                objectives: [],
                teaching_notes: "",
              });
              setNewLessonTitle("");
            }}
          >
            Add lesson
          </button>
        </div>
      ) : null}
    </div>
  );
}

function LearningLessonEditor({
  pathId,
  moduleId,
  lesson,
  lessonIndex,
  lessonCount,
  canEdit,
  saving,
  onUpdateLesson,
  onDeleteLesson,
  onMoveUp,
  onMoveDown,
}: {
  pathId: string;
  moduleId: string;
  lesson: LearningLesson;
  lessonIndex: number;
  lessonCount: number;
  canEdit: boolean;
  saving: boolean;
  onUpdateLesson: LearningPathsPageProps["onUpdateLesson"];
  onDeleteLesson: LearningPathsPageProps["onDeleteLesson"];
  onMoveUp: () => void;
  onMoveDown: () => void;
}) {
  const [title, setTitle] = useState(lesson.title);
  const [description, setDescription] = useState(lesson.description);
  const [objectives, setObjectives] = useState(lesson.objectives.join(", "));
  const [notes, setNotes] = useState(lesson.teaching_notes);

  useEffect(() => {
    setTitle(lesson.title);
    setDescription(lesson.description);
    setObjectives(lesson.objectives.join(", "));
    setNotes(lesson.teaching_notes);
  }, [lesson]);

  return (
    <div className="archive-row">
      <strong>Lesson {lessonIndex + 1}: {lesson.title}</strong>
      <div className="settings-grid">
        <input value={title} disabled={!canEdit} onChange={(event) => setTitle(event.target.value)} />
        <textarea value={description} disabled={!canEdit} onChange={(event) => setDescription(event.target.value)} />
        <input value={objectives} disabled={!canEdit} onChange={(event) => setObjectives(event.target.value)} placeholder="Objectives comma-separated" />
        <textarea value={notes} disabled={!canEdit} onChange={(event) => setNotes(event.target.value)} placeholder="Teaching notes" />
      </div>
      {canEdit ? (
        <div className="archive-row-actions">
          <button className="secondary-button" disabled={saving || lessonIndex === 0} onClick={onMoveUp}>
            <Icon name="arrow-up" />
          </button>
          <button className="secondary-button" disabled={saving || lessonIndex >= lessonCount - 1} onClick={onMoveDown}>
            <Icon name="arrow-up" className="rotate-180" />
          </button>
          <button
            className="secondary-button"
            disabled={saving}
            onClick={() =>
              void onUpdateLesson(pathId, moduleId, lesson.id, {
                title: title.trim(),
                description: description.trim(),
                objectives: objectives.split(",").map((item) => item.trim()).filter(Boolean),
                teaching_notes: notes.trim(),
              })
            }
          >
            Save lesson
          </button>
          <button className="danger-button" disabled={saving} onClick={() => void onDeleteLesson(pathId, moduleId, lesson.id)}>
            Delete lesson
          </button>
        </div>
      ) : null}
    </div>
  );
}
