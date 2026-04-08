import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import type {
  DiagnosticAttemptDetails,
  DiagnosticAttemptSummary,
  DiagnosticDefinition,
  DiagnosticResult,
  LearningGoal,
  LearningProfileBundle,
  LearningProfileContext,
  LearningPreferences,
  LearningStateCheck,
  KSAProfile,
} from "../../types/chat";
import { DiagnosticPanel } from "./DiagnosticPanel";
import { KsaPanel } from "./KsaPanel";
import { LearningProfilePanel } from "./LearningProfilePanel";

type LearningPathsPageProps = {
  error: string | null;
  onLoad: () => void;
  learningProfile: LearningProfileBundle | null;
  learningProfileLoading: boolean;
  learningProfileSaving: boolean;
  learningProfileError: string | null;
  learningProfileSuccess: string | null;
  ksaProfile: KSAProfile | null;
  ksaLoading: boolean;
  ksaError: string | null;
  currentUserDisplayName: string;
  onLoadLearningProfile: () => void;
  onLoadKsaProfile: () => void;
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
};

type LearningTab = "profile" | "preferences" | "ksa";

export function LearningPathsPage({
  error,
  learningProfile,
  learningProfileLoading,
  learningProfileSaving,
  learningProfileError,
  learningProfileSuccess,
  ksaProfile,
  ksaLoading,
  ksaError,
  currentUserDisplayName,
  onLoad,
  onLoadLearningProfile,
  onLoadKsaProfile,
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

  useEffect(() => {
    onLoad();
    // mount-scoped
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const tab = params.get("tab");
    if (tab === "profile" || tab === "preferences" || tab === "ksa") {
      setActiveTab(tab);
    }
  }, [location.search]);

  return (
    <section className="chat-column library-column">
      {error ? <p className="chat-error chat-error-banner">{error}</p> : null}

      <section className="info-group-card learning-tabs-card">
        <div className="learning-tabs" role="tablist" aria-label="Learning page tabs">
          <button className={`learning-tab${activeTab === "profile" ? " active" : ""}`} type="button" role="tab" aria-selected={activeTab === "profile"} onClick={() => setActiveTab("profile")}>Profile</button>
          <button className={`learning-tab${activeTab === "preferences" ? " active" : ""}`} type="button" role="tab" aria-selected={activeTab === "preferences"} onClick={() => setActiveTab("preferences")}>Preferences</button>
          <button className={`learning-tab${activeTab === "ksa" ? " active" : ""}`} type="button" role="tab" aria-selected={activeTab === "ksa"} onClick={() => setActiveTab("ksa")}>KSA</button>
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

      {activeTab === "ksa" ? (
        <KsaPanel
          profile={ksaProfile}
          loading={ksaLoading}
          error={ksaError}
          onReload={onLoadKsaProfile}
        />
      ) : null}
    </section>
  );
}
