import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import type {
  DiagnosticAttemptDetails,
  DiagnosticAttemptSummary,
  DiagnosticDefinition,
  DiagnosticResult,
  LearningGoal,
  LearningLesson,
  LearningModule,
  LearningPath,
  LearningProfileBundle,
  LearningProfileContext,
  LearningPreferences,
  LearningStateCheck,
  LibraryFile,
  Role,
} from "../../types/chat";
import { DiagnosticPanel } from "./DiagnosticPanel";
import { LearningProfilePanel } from "./LearningProfilePanel";
import { Icon } from "../common/Icons";

type LearningPathsPageProps = {
  role: Role;
  paths: LearningPath[];
  libraryFiles: LibraryFile[];
  loading: boolean;
  saving: boolean;
  error: string | null;
  canAuthor: boolean;
  onLoad: () => void;
  learningProfile: LearningProfileBundle | null;
  learningProfileLoading: boolean;
  learningProfileSaving: boolean;
  learningProfileError: string | null;
  learningProfileSuccess: string | null;
  currentUserDisplayName: string;
  onLoadLearningProfile: () => void;
  onSaveLearningPreferences: (payload: Partial<Omit<LearningPreferences, "updated_at">>) => Promise<unknown>;
  onSaveLearningContext: (payload: Partial<Omit<LearningProfileContext, "updated_at">>) => Promise<unknown>;
  onCreateLearningGoal: (payload: {
    target_topic: string;
    reason_for_learning: string;
    target_level: string;
    deadline: string | null;
    priority: "low" | "medium" | "high" | null;
    notes: string;
    is_active: boolean;
  }) => Promise<unknown>;
  onUpdateLearningGoal: (goalId: string, payload: Partial<Omit<LearningGoal, "id" | "created_at" | "updated_at">>) => Promise<unknown>;
  onDeleteLearningGoal: (goalId: string) => Promise<unknown>;
  diagnosticDefinitions: Record<"LAA" | "MOA" | "LTA", DiagnosticDefinition | null>;
  diagnosticAttempt: DiagnosticAttemptDetails | null;
  diagnosticAttempts: DiagnosticAttemptSummary[];
  diagnosticResult: DiagnosticResult | null;
  diagnosticLoading: boolean;
  diagnosticSaving: boolean;
  diagnosticError: string | null;
  learningStateChecks: LearningStateCheck[];
  learningStateSaving: boolean;
  learningStateError: string | null;
  onLoadDiagnostics: () => Promise<unknown>;
  onStartDiagnosticAttempt: () => Promise<unknown>;
  onSaveDiagnosticAnswers: (attemptId: string, diagnosticType: "LAA" | "MOA" | "LTA", answers: Array<{ question_id: string; value: unknown }>) => Promise<unknown>;
  onCompleteDiagnosticAttempt: (attemptId: string) => Promise<unknown>;
  onDeleteDiagnosticAttempt: (attemptId: string) => Promise<unknown>;
  onOpenDiagnosticAttempt: (attemptId: string) => Promise<DiagnosticAttemptDetails>;
  onCreateLearningStateCheck: (payload: {
    mood: string;
    perceived_difficulty: string;
    needs_pause_or_input: string;
    preferred_format: string;
    notes: string;
  }) => Promise<unknown>;
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

type LearningTab = "profile" | "preferences" | "paths";

export function LearningPathsPage({
  paths,
  loading,
  error,
  learningProfile,
  learningProfileLoading,
  learningProfileSaving,
  learningProfileError,
  learningProfileSuccess,
  currentUserDisplayName,
  onLoad,
  onLoadLearningProfile,
  onSaveLearningPreferences,
  onSaveLearningContext,
  onCreateLearningGoal,
  onUpdateLearningGoal,
  onDeleteLearningGoal,
  diagnosticDefinitions,
  diagnosticAttempt,
  diagnosticAttempts,
  diagnosticResult,
  diagnosticLoading,
  diagnosticSaving,
  diagnosticError,
  learningStateChecks,
  learningStateSaving,
  learningStateError,
  onLoadDiagnostics,
  onStartDiagnosticAttempt,
  onSaveDiagnosticAnswers,
  onCompleteDiagnosticAttempt,
  onDeleteDiagnosticAttempt,
  onOpenDiagnosticAttempt,
  onCreateLearningStateCheck,
}: LearningPathsPageProps) {
  const location = useLocation();
  const [activeTab, setActiveTab] = useState<LearningTab>("profile");
  const [selectedPathId, setSelectedPathId] = useState<string | null>(null);
  const [showScrollTop, setShowScrollTop] = useState(false);
  const detailsRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    onLoad();
    // mount-scoped
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const tab = params.get("tab");
    if (tab === "profile" || tab === "preferences" || tab === "paths") {
      setActiveTab(tab);
    }
  }, [location.search]);

  useEffect(() => {
    if (activeTab !== "paths") {
      setShowScrollTop(false);
      return;
    }
    function handleScroll() {
      setShowScrollTop(window.scrollY > 180);
    }
    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, [activeTab]);

  const selectedPath = useMemo(
    () => paths.find((path) => path.id === selectedPathId) ?? null,
    [paths, selectedPathId],
  );

  function openPathDetails(pathId: string) {
    setSelectedPathId(pathId);
    window.requestAnimationFrame(() => {
      window.setTimeout(() => {
        detailsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 30);
    });
  }

  return (
    <section className="chat-column library-column">
      {error ? <p className="chat-error chat-error-banner">{error}</p> : null}

      <section className="info-group-card learning-tabs-card">
        <div className="learning-tabs" role="tablist" aria-label="Learning page tabs">
          <button className={`learning-tab${activeTab === "profile" ? " active" : ""}`} type="button" role="tab" aria-selected={activeTab === "profile"} onClick={() => setActiveTab("profile")}>Profile</button>
          <button className={`learning-tab${activeTab === "preferences" ? " active" : ""}`} type="button" role="tab" aria-selected={activeTab === "preferences"} onClick={() => setActiveTab("preferences")}>Preferences</button>
          <button className={`learning-tab${activeTab === "paths" ? " active" : ""}`} type="button" role="tab" aria-selected={activeTab === "paths"} onClick={() => setActiveTab("paths")}>Paths</button>
        </div>
      </section>

      {activeTab === "profile" ? (
        <>
          <LearningProfilePanel
            profile={learningProfile}
            loading={learningProfileLoading}
            saving={learningProfileSaving}
            error={learningProfileError}
            success={learningProfileSuccess}
            currentUserDisplayName={currentUserDisplayName}
            onLoad={onLoadLearningProfile}
            onSavePreferences={onSaveLearningPreferences}
            onSaveContext={onSaveLearningContext}
            onCreateGoal={onCreateLearningGoal}
            onUpdateGoal={onUpdateLearningGoal}
            onDeleteGoal={onDeleteLearningGoal}
            showPreferences={false}
            showContext
            showGoals
          />
        </>
      ) : null}

      {activeTab === "preferences" ? (
        <>
          <LearningProfilePanel
            profile={learningProfile}
            loading={learningProfileLoading}
            saving={learningProfileSaving}
            error={learningProfileError}
            success={learningProfileSuccess}
            currentUserDisplayName={currentUserDisplayName}
            onLoad={onLoadLearningProfile}
            onSavePreferences={onSaveLearningPreferences}
            onSaveContext={onSaveLearningContext}
            onCreateGoal={onCreateLearningGoal}
            onUpdateGoal={onUpdateLearningGoal}
            onDeleteGoal={onDeleteLearningGoal}
            showPreferences
            showContext={false}
            showGoals={false}
          />
          <DiagnosticPanel
            definitions={diagnosticDefinitions}
            attempt={diagnosticAttempt}
            attempts={diagnosticAttempts}
            result={diagnosticResult}
            loading={diagnosticLoading}
            saving={diagnosticSaving}
            error={diagnosticError}
            stateChecks={learningStateChecks}
            stateSaving={learningStateSaving}
            stateError={learningStateError}
            onLoad={onLoadDiagnostics}
            onStart={onStartDiagnosticAttempt}
            onSaveAnswers={onSaveDiagnosticAnswers}
            onComplete={onCompleteDiagnosticAttempt}
            onDeleteAttempt={onDeleteDiagnosticAttempt}
            onOpenAttempt={onOpenDiagnosticAttempt}
            onCreateStateCheck={onCreateLearningStateCheck}
            showStateCheck={false}
          />
        </>
      ) : null}

      {activeTab === "paths" ? (
        <>
          <section className="info-group-card library-table-card">
            <div className="library-table-header">
              <h4>Learning paths</h4>
            </div>
            <div className="library-table learning-paths-table">
              {loading ? <div className="empty-state">Loading learning paths...</div> : null}
              {!loading ? (
                <>
                  <div className="library-table-head learning-paths-head">
                    <span>Title</span>
                    <span>Scope</span>
                    <span>Subject</span>
                    <span>Status</span>
                    <span>Modules</span>
                    <span>Actions</span>
                  </div>
                  <div className="library-table-body">
                    {paths.length === 0 ? <div className="empty-state">No learning paths yet.</div> : null}
                    {paths.map((path) => {
                      const isSelected = selectedPathId === path.id;
                      return (
                        <div key={path.id} className={`library-table-row learning-paths-row${isSelected ? " active" : ""}`}>
                          <span className="learning-paths-title">
                            <strong>{path.title}</strong>
                            <small>{path.description || "No description yet."}</small>
                          </span>
                          <span>{path.scope === "global" ? "Global" : "User"}</span>
                          <span>{path.subject || "-"}</span>
                          <span className={`learning-path-status learning-path-status-${path.status}`}>{path.status}</span>
                          <span>{path.modules.length}</span>
                          <span className="learning-path-actions">
                            <button className="learning-path-action-button" type="button" onClick={() => openPathDetails(path.id)} title="Details" aria-label="Show details">
                              <Icon name="info" />
                            </button>
                            <button className="learning-path-action-button primary" type="button" onClick={() => openPathDetails(path.id)} title={isSelected ? "Continue learning" : "Start learning"} aria-label={isSelected ? "Continue learning" : "Start learning"}>
                              <Icon name="play" />
                            </button>
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </>
              ) : null}
            </div>
          </section>

          {selectedPath ? (
            <section ref={detailsRef} className="info-group-card learning-path-details-card">
              <div className="learning-path-details-header">
                <h4>{selectedPath.title}</h4>
                <p>{selectedPath.description || "No description available."}</p>
                <div className="learning-path-details-meta">
                  <span>{selectedPath.subject || "General"}</span>
                  <span>{selectedPath.difficulty_level || "Mixed level"}</span>
                </div>
                <div className="learning-path-details-stats">
                  <div className="learning-path-stat-card">
                    <strong>{selectedPath.modules.length}</strong>
                    <small>Modules</small>
                  </div>
                  <div className="learning-path-stat-card">
                    <strong>{selectedPath.modules.reduce((count, module) => count + module.lessons.length, 0)}</strong>
                    <small>Lessons</small>
                  </div>
                </div>
              </div>

              <div className="library-table learning-path-structure-table">
                <div className="library-table-body">
                {selectedPath.modules
                  .slice()
                  .sort((left, right) => left.order_index - right.order_index)
                  .map((module) => (
                    <article key={module.id} className="learning-path-module-block">
                      <div className="library-table-row learning-path-module-row">
                        <span className="learning-path-module-title-cell">
                          <strong>{module.title}</strong>
                          {module.description ? <small>{module.description}</small> : null}
                        </span>
                        <span>{module.lessons.length} Lessons</span>
                      </div>
                      {module.lessons
                        .slice()
                        .sort((left, right) => left.order_index - right.order_index)
                        .map((lesson) => (
                          <div key={lesson.id} className="library-table-row learning-path-lesson-row">
                            <span className="learning-path-lesson-title-cell">
                              <Icon name="chalkboard" className="learning-path-lesson-icon" />
                              <span className="learning-path-lesson-title">{lesson.title}</span>
                            </span>
                            <span className="learning-path-lesson-type" aria-hidden="true">&nbsp;</span>
                          </div>
                        ))}
                    </article>
                  ))}
                </div>
              </div>
            </section>
          ) : null}

          {showScrollTop ? (
            <button
              type="button"
              className="learning-path-scroll-top"
              onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
              aria-label="Scroll to top"
              title="Scroll to top"
            >
              <Icon name="arrow-up" />
            </button>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
