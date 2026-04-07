import { useEffect, useMemo, useState, type CSSProperties, type ReactNode } from "react";
import type { DiagnosticAttemptDetails, DiagnosticAttemptSummary, DiagnosticDefinition, DiagnosticQuestion, DiagnosticResult, LearningStateCheck } from "../../types/chat";
import { Dialog } from "../common/Dialog";
import { Icon } from "../common/Icons";

type DiagnosticPanelProps = {
  definitions: Record<"LAA" | "MOA" | "LTA", DiagnosticDefinition | null>;
  attempt: DiagnosticAttemptDetails | null;
  attempts: DiagnosticAttemptSummary[];
  result: DiagnosticResult | null;
  loading: boolean;
  saving: boolean;
  error: string | null;
  stateChecks: LearningStateCheck[];
  stateSaving: boolean;
  stateError: string | null;
  onLoad: () => Promise<unknown>;
  onStart: () => Promise<unknown>;
  onSaveAnswers: (attemptId: string, diagnosticType: "LAA" | "MOA" | "LTA", answers: Array<{ question_id: string; value: unknown }>) => Promise<unknown>;
  onComplete: (attemptId: string) => Promise<unknown>;
  onDeleteAttempt: (attemptId: string) => Promise<unknown>;
  onOpenAttempt: (attemptId: string) => Promise<DiagnosticAttemptDetails>;
  onCreateStateCheck: (payload: {
    mood: string;
    perceived_difficulty: string;
    needs_pause_or_input: string;
    preferred_format: string;
    notes: string;
  }) => Promise<unknown>;
  showStateCheck?: boolean;
};

const ORDER: Array<"LAA" | "MOA" | "LTA"> = ["LAA", "MOA", "LTA"];
const STEP_LABELS: Record<(typeof ORDER)[number], string> = {
  LAA: "Learning Approach",
  MOA: "Motivation",
  LTA: "Learning Type",
};
const INTRO_PREVIEW = {
  LAA: {
    user_needs: 0.86,
    learning_experience: 0.72,
    conditions: 0.58,
    objectives: 0.9,
    skills_and_interests: 0.78,
    attitude: 0.66,
    support_needs: 0.61,
    miscellaneous: 0.42,
  },
  MOA: {
    knowledge: 0.84,
    creativity: 0.72,
    influence: 0.48,
    meaning: 0.67,
    connection: 0.59,
    routine: 0.51,
    performance: 0.78,
    autonomy: 0.81,
    confirmation: 0.46,
    experimenting: 0.87,
  },
  LTA: {
    auditiv: 0.21,
    visuell: 0.32,
    kinaesthetisch: 0.29,
    lesen_schreiben: 0.18,
  },
} as const;

export function DiagnosticPanel({
  definitions,
  attempt,
  attempts,
  result,
  loading,
  saving,
  error,
  stateChecks,
  stateSaving,
  stateError,
  onLoad,
  onStart,
  onSaveAnswers,
  onComplete,
  onDeleteAttempt,
  onOpenAttempt,
  onCreateStateCheck,
  showStateCheck = true,
}: DiagnosticPanelProps) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [questionIndex, setQuestionIndex] = useState(0);
  const [answersByType, setAnswersByType] = useState<Record<string, Record<string, unknown>>>({ LAA: {}, MOA: {}, LTA: {} });
  const [stateDraft, setStateDraft] = useState({
    mood: "",
    perceived_difficulty: "",
    needs_pause_or_input: "",
    preferred_format: "",
    notes: "",
  });

  useEffect(() => {
    void onLoad();
    // mount only
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    setAnswersByType({
      LAA: (attempt?.answers?.LAA as Record<string, unknown>) ?? {},
      MOA: (attempt?.answers?.MOA as Record<string, unknown>) ?? {},
      LTA: (attempt?.answers?.LTA as Record<string, unknown>) ?? {},
    });
  }, [attempt]);

  const currentType = ORDER[stepIndex];
  const currentDefinition = definitions[currentType];
  const hasActiveAttempt = Boolean(attempt && attempt.attempt.status !== "completed");

  const questionItems = useMemo(() => {
    if (!currentDefinition) {
      return [];
    }
    return currentDefinition.sections.flatMap((section) => section.questions.map((question) => ({ ...question, sectionTitle: section.title })));
  }, [currentDefinition]);

  const currentQuestion = questionItems[questionIndex] ?? null;
  const currentValue = currentQuestion ? answersByType[currentType]?.[currentQuestion.id] : undefined;
  const currentAnswered = isAnswered(currentValue);

  function openDialog() {
    setDialogOpen(true);
    if (hasActiveAttempt) {
      const nextPosition = findNextQuestionPosition(definitions, answersByType);
      setStepIndex(nextPosition.stepIndex);
      setQuestionIndex(nextPosition.questionIndex);
    }
  }

  function closeDialog() {
    setDialogOpen(false);
  }

  async function handleStartAttempt() {
    await onStart();
    setStepIndex(0);
    setQuestionIndex(0);
  }

  async function saveCurrentStep(type: "LAA" | "MOA" | "LTA") {
    if (!attempt) {
      return;
    }
    const payload = Object.entries(answersByType[type] ?? {}).map(([question_id, value]) => ({ question_id, value }));
    await onSaveAnswers(attempt.attempt.attempt_id, type, payload);
  }

  async function moveToNextQuestion() {
    if (!currentQuestion) {
      return;
    }
    const nextQuestionIndex = questionIndex + 1;
    if (nextQuestionIndex < questionItems.length) {
      setQuestionIndex(nextQuestionIndex);
      return;
    }

    await saveCurrentStep(currentType);
    const nextStepIndex = stepIndex + 1;
    if (nextStepIndex < ORDER.length) {
      setStepIndex(nextStepIndex);
      setQuestionIndex(0);
      return;
    }

    if (!attempt) {
      return;
    }
    await onComplete(attempt.attempt.attempt_id);
    setDialogOpen(false);
  }

  function moveToPreviousQuestion() {
    if (questionIndex > 0) {
      setQuestionIndex((current) => current - 1);
      return;
    }
    if (stepIndex === 0) {
      return;
    }
    const previousStep = ORDER[stepIndex - 1];
    const previousQuestions = definitions[previousStep]?.sections.flatMap((section) => section.questions) ?? [];
    setStepIndex((current) => current - 1);
    setQuestionIndex(Math.max(0, previousQuestions.length - 1));
  }

  const totalQuestions = questionItems.length;
  const progress = totalQuestions > 0 ? ((questionIndex + 1) / totalQuestions) * 100 : 0;

  const laaScores = normalizeAndOrderScores(extractScores(result?.result?.LAA, "normalized"), "LAA");
  const moaScores = normalizeAndOrderScores(extractScores(result?.result?.MOA, "normalized"), "MOA");
  const ltaScores = extractScores(result?.result?.LTA, "normalized");
  const laaDominant = normalizeTraitLabels(extractTraits(result?.result?.LAA), "LAA");
  const moaDominant = normalizeTraitLabels(extractTraits(result?.result?.MOA), "MOA");
  const ltaDominant = extractTraits(result?.result?.LTA);

  return (
    <section className="info-group-card diagnostic-panel-card">
      <h4>Learning Preferences Diagnostic</h4>
      {error ? <p className="chat-error">{error}</p> : null}
      {loading ? <p>Loading diagnostic definitions...</p> : null}

      <div className="library-table diagnostic-attempts-table">
        <div className="library-table-head diagnostic-attempts-head">
          <span>Date</span>
          <span>Status</span>
          <span>Version</span>
          <span>Action</span>
        </div>
        <div className="library-table-body">
          {attempts.length === 0 ? <div className="empty-state">No diagnostic attempts yet.</div> : null}
          {attempts.map((item) => {
            const when = item.completed_at || item.started_at;
            return (
              <div key={item.attempt_id} className="library-table-row diagnostic-attempts-row">
                <span>{formatAttemptDate(when)}</span>
                <span><span className={`diagnostic-attempt-status diagnostic-attempt-status-${item.status}`}>{item.status}</span></span>
                <span>{formatAttemptVersions(item.definition_versions)}</span>
                <span className="diagnostic-attempt-actions">
                  {item.status !== "completed" ? (
                    <button
                      className="secondary-button diagnostic-attempt-continue"
                      type="button"
                      disabled={saving}
                      onClick={async () => {
                        const opened = await onOpenAttempt(item.attempt_id);
                        const nextAnswers = {
                          LAA: (opened.answers?.LAA as Record<string, unknown>) ?? {},
                          MOA: (opened.answers?.MOA as Record<string, unknown>) ?? {},
                          LTA: (opened.answers?.LTA as Record<string, unknown>) ?? {},
                        };
                        setAnswersByType(nextAnswers);
                        const nextPosition = findNextQuestionPosition(definitions, nextAnswers);
                        setStepIndex(nextPosition.stepIndex);
                        setQuestionIndex(nextPosition.questionIndex);
                        setDialogOpen(true);
                      }}
                    >
                      Continue
                    </button>
                  ) : null}
                  <button
                    className="danger-button diagnostic-attempt-delete"
                    type="button"
                    disabled={saving}
                    onClick={async () => {
                      const confirmed = window.confirm("Delete this diagnostic attempt and its results?");
                      if (!confirmed) {
                        return;
                      }
                      await onDeleteAttempt(item.attempt_id);
                    }}
                    aria-label="Delete attempt"
                  >
                    <Icon name="trash" />
                    Delete
                  </button>
                </span>
              </div>
            );
          })}
        </div>
      </div>

      <div className="library-table-footer diagnostic-start-row">
        <button className="primary-button" type="button" disabled={saving || loading} onClick={openDialog}>
          Start Diagnostic
        </button>
      </div>

      {dialogOpen ? (
        <Dialog
          title="Learning Preferences Diagnostic"
          onClose={closeDialog}
          className="diagnostic-dialog"
          contentClassName="diagnostic-dialog-content"
          bodyClassName="diagnostic-dialog-body"
          actions={null}
        >
          {!hasActiveAttempt ? (
            <div className="diagnostic-intro">
              <div className="diagnostic-stepper">
                {ORDER.map((step, index) => (
                  <div key={step} className={`diagnostic-step-pill${index === 0 ? " active" : ""}`}>
                    <strong>{index + 1} {STEP_LABELS[step]}</strong>
                  </div>
                ))}
              </div>

              <h3>Learning Preferences Diagnostic</h3>
              <p>This test guides you step by step through Learning Approach, Motivation, and Learning Type.</p>
              <div className="diagnostic-intro-cards">
                <article>
                  <h4>Learning Approach (LAA)</h4>
                  {renderLaaProfile(INTRO_PREVIEW.LAA)}
                </article>
                <article>
                  <h4>Motivation (MOA)</h4>
                  {renderMoaProfile(INTRO_PREVIEW.MOA)}
                </article>
                <article>
                  <h4>Learning Type (LTA)</h4>
                  {renderLtaProfile(INTRO_PREVIEW.LTA, ["visuell"])}
                </article>
              </div>
              <div className="diagnostic-intro-actions">
                <button className="secondary-button" type="button" onClick={closeDialog}>Later</button>
                <button className="primary-button" type="button" disabled={saving || loading} onClick={() => void handleStartAttempt()}>Start Diagnostic</button>
              </div>
            </div>
          ) : (
            <div className="diagnostic-wizard">
              <div className="diagnostic-stepper">
                {ORDER.map((step, index) => (
                  <button
                    key={step}
                    className={`diagnostic-step-pill${index === stepIndex ? " active" : ""}`}
                    type="button"
                    onClick={() => {
                      setStepIndex(index);
                      setQuestionIndex(0);
                    }}
                  >
                    <strong>{index + 1} {STEP_LABELS[step]}</strong>
                  </button>
                ))}
              </div>

              <div className="diagnostic-question-shell">
                <h3>{sanitizeDiagnosticText(currentDefinition?.title ?? STEP_LABELS[currentType])}</h3>
                <div className="diagnostic-question-progress"><span style={{ width: `${progress}%` }} /></div>

                {currentQuestion ? (
                  <>
                    <p className="diagnostic-question-meta">
                      {currentQuestion.sectionTitle ? formatDimensionLabel(currentQuestion.sectionTitle) : ""}
                    </p>
                    <p className="diagnostic-question-text">{currentQuestion.text}</p>
                    <QuestionInput
                      question={currentQuestion}
                      value={currentValue}
                      otherText={String(answersByType[currentType]?.[`${currentQuestion.id}__other_text`] ?? "")}
                      onOtherTextChange={(nextText) => setAnswersByType((current) => ({
                        ...current,
                        [currentType]: { ...(current[currentType] ?? {}), [`${currentQuestion.id}__other_text`]: nextText },
                      }))}
                      onChange={(nextValue) => setAnswersByType((current) => ({
                        ...current,
                        [currentType]: { ...(current[currentType] ?? {}), [currentQuestion.id]: nextValue },
                      }))}
                    />
                  </>
                ) : (
                  <p>No questions available for this step.</p>
                )}
              </div>

              <div className="diagnostic-wizard-actions">
                <button className="secondary-button" type="button" disabled={saving || (stepIndex === 0 && questionIndex === 0)} onClick={moveToPreviousQuestion}>Previous</button>
                <button
                  className="primary-button"
                  type="button"
                  disabled={saving || !currentAnswered}
                  onClick={() => {
                    void moveToNextQuestion();
                  }}
                >
                  {stepIndex === ORDER.length - 1 && questionIndex === totalQuestions - 1 ? "Compute Result" : "Next"}
                </button>
              </div>
            </div>
          )}
        </Dialog>
      ) : null}

      {result?.result ? (
        <section className="diagnostic-results-section">
          <h5>Latest Attempt Results</h5>
          <div className="diagnostic-results-grid">
            <ChartCard title="Learning Approach (LAA)">
              {renderLaaProfile(laaScores)}
              {laaDominant.length > 0 ? <p className="diagnostic-card-meta">Dominant: {laaDominant.map(formatDimensionLabel).join(", ")}</p> : null}
            </ChartCard>
            <ChartCard title="Motivation (MOA)">
              {renderMoaProfile(moaScores)}
              {moaDominant.length > 0 ? <p className="diagnostic-card-meta">Top drivers: {moaDominant.map(formatDimensionLabel).join(", ")}</p> : null}
            </ChartCard>
            <ChartCard title="Learning Type (LTA)">
              {renderLtaProfile(ltaScores, ltaDominant)}
            </ChartCard>
          </div>
        </section>
      ) : null}

      {showStateCheck ? (
        <section className="info-group-card">
          <h4>Learning State Check</h4>
          {stateError ? <p className="chat-error">{stateError}</p> : null}
          <div className="settings-grid">
            <label><span>Mood</span><input value={stateDraft.mood} onChange={(event) => setStateDraft((current) => ({ ...current, mood: event.target.value }))} /></label>
            <label><span>Difficulty</span><input value={stateDraft.perceived_difficulty} onChange={(event) => setStateDraft((current) => ({ ...current, perceived_difficulty: event.target.value }))} /></label>
            <label><span>Pause/Input Need</span><input value={stateDraft.needs_pause_or_input} onChange={(event) => setStateDraft((current) => ({ ...current, needs_pause_or_input: event.target.value }))} /></label>
            <label><span>Preferred Format</span><input value={stateDraft.preferred_format} onChange={(event) => setStateDraft((current) => ({ ...current, preferred_format: event.target.value }))} /></label>
            <label><span>Notes</span><textarea value={stateDraft.notes} onChange={(event) => setStateDraft((current) => ({ ...current, notes: event.target.value }))} /></label>
          </div>
          <div className="library-table-footer">
            <button className="primary-button" type="button" disabled={stateSaving} onClick={async () => {
              await onCreateStateCheck(stateDraft);
              setStateDraft({ mood: "", perceived_difficulty: "", needs_pause_or_input: "", preferred_format: "", notes: "" });
            }}>Save State Check</button>
          </div>
          <div className="archive-list">
            {stateChecks.slice(0, 5).map((item) => (
              <div key={item.id} className="archive-row"><strong>{new Date(item.created_at).toLocaleString()}</strong><span>{item.mood} | {item.perceived_difficulty} | {item.preferred_format}</span></div>
            ))}
          </div>
        </section>
      ) : null}
    </section>
  );
}

function QuestionInput({
  question,
  value,
  otherText,
  onChange,
  onOtherTextChange,
}: {
  question: DiagnosticQuestion & { sectionTitle?: string };
  value: unknown;
  otherText: string;
  onChange: (value: unknown) => void;
  onOtherTextChange: (value: string) => void;
}) {
  if (question.type === "single_choice") {
    const miscOption = question.options.find((option) => option.allows_text);
    const miscValue = miscOption ? (miscOption.value ?? miscOption.key) : "";
    const isMiscSelected = miscValue && String(value ?? "") === miscValue;
    return (
      <>
        <div className="diagnostic-options-list">
          {question.options.map((option) => {
            const resolvedValue = option.value ?? option.key;
            return (
              <label key={option.key} className={`diagnostic-option-card${String(value ?? "") === resolvedValue ? " selected" : ""}`}>
                <input type="radio" checked={String(value ?? "") === resolvedValue} onChange={() => onChange(resolvedValue)} />
                <span>{option.label}</span>
              </label>
            );
          })}
        </div>
        {isMiscSelected ? (
          <textarea
            className="diagnostic-textarea diagnostic-misc-textarea"
            placeholder="Please specify"
            value={otherText}
            onChange={(event) => onOtherTextChange(event.target.value)}
          />
        ) : null}
      </>
    );
  }

  if (question.type === "multi_choice") {
    const selected = Array.isArray(value) ? value.map(String) : [];
    const miscOption = question.options.find((option) => option.allows_text);
    const miscValue = miscOption ? (miscOption.value ?? miscOption.key) : "";
    const isMiscSelected = miscValue && selected.includes(miscValue);
    return (
      <>
        <div className="diagnostic-options-list">
          {question.options.map((option) => {
            const resolvedValue = option.value ?? option.key;
            return (
              <label key={option.key} className={`diagnostic-option-card${selected.includes(resolvedValue) ? " selected" : ""}`}>
                <input
                  type="checkbox"
                  checked={selected.includes(resolvedValue)}
                  onChange={(event) => {
                    const next = new Set(selected);
                    if (event.target.checked) {
                      next.add(resolvedValue);
                    } else {
                      next.delete(resolvedValue);
                    }
                    onChange(Array.from(next));
                  }}
                />
                <span>{option.label}</span>
              </label>
            );
          })}
        </div>
        {isMiscSelected ? (
          <textarea
            className="diagnostic-textarea diagnostic-misc-textarea"
            placeholder="Please specify"
            value={otherText}
            onChange={(event) => onOtherTextChange(event.target.value)}
          />
        ) : null}
      </>
    );
  }

  if (question.type === "likert" || question.type === "slider") {
    if (question.options.length > 0) {
      const isFivePointScale =
        question.options.length === 5 &&
        question.options.every((option, index) => Number(option.value ?? option.key) === index + 1);
      return (
        <>
          {isFivePointScale ? (
            <div className="diagnostic-likert-inline" role="radiogroup" aria-label={question.text}>
              {question.options.map((option) => {
                const resolvedValue = option.value ?? option.key;
                const selected = String(value ?? "") === resolvedValue;
                return (
                  <label key={option.key} className={`diagnostic-likert-point${selected ? " selected" : ""}`}>
                    <input type="radio" checked={selected} onChange={() => onChange(resolvedValue)} />
                    <span>{option.label}</span>
                  </label>
                );
              })}
            </div>
          ) : (
            <div className="diagnostic-options-list">
              {question.options.map((option) => {
                const resolvedValue = option.value ?? option.key;
                return (
                  <label key={option.key} className={`diagnostic-option-card${String(value ?? "") === resolvedValue ? " selected" : ""}`}>
                    <input type="radio" checked={String(value ?? "") === resolvedValue} onChange={() => onChange(resolvedValue)} />
                    <span>{option.label}</span>
                  </label>
                );
              })}
            </div>
          )}
          {isFivePointScale ? <p className="diagnostic-scale-hint">1 = Strongly disagree, 5 = Strongly agree</p> : null}
        </>
      );
    }

    const min = Number(question.min_value ?? 1);
    const max = Number(question.max_value ?? 10);
    const numericValue = typeof value === "number" || typeof value === "string" ? Number(value) : min;
    const clamped = Math.max(min, Math.min(max, numericValue));
    const fillPercent = ((clamped - min) / Math.max(max - min, 1)) * 100;
    const marks = Array.from({ length: Math.max(0, max - min + 1) }, (_, index) => min + index);
    return (
      <div className="diagnostic-range-wrap">
        <input
          type="range"
          min={min}
          max={max}
          value={clamped}
          style={{ "--range-fill": `${fillPercent}%` } as CSSProperties}
          onChange={(event) => onChange(Number(event.target.value))}
        />
        <div className="diagnostic-range-marks" aria-hidden="true">
          {marks.map((mark) => <span key={mark}>{mark}</span>)}
        </div>
        <small>Value: {clamped}</small>
      </div>
    );
  }

  return (
    <textarea
      className="diagnostic-textarea"
      value={typeof value === "string" ? value : ""}
      onChange={(event) => onChange(event.target.value)}
      placeholder="Optional"
    />
  );
}

function findNextQuestionPosition(
  definitions: Record<"LAA" | "MOA" | "LTA", DiagnosticDefinition | null>,
  answersByType: Record<string, Record<string, unknown>>,
): { stepIndex: number; questionIndex: number } {
  for (let typeIndex = 0; typeIndex < ORDER.length; typeIndex += 1) {
    const type = ORDER[typeIndex];
    const questions = definitions[type]?.sections.flatMap((section) => section.questions) ?? [];
    const answers = answersByType[type] ?? {};
    for (let idx = 0; idx < questions.length; idx += 1) {
      const value = answers[questions[idx].id];
      const isEmptyArray = Array.isArray(value) && value.length === 0;
      if (value === undefined || value === null || value === "" || isEmptyArray) {
        return { stepIndex: typeIndex, questionIndex: idx };
      }
    }
  }
  return { stepIndex: 0, questionIndex: 0 };
}

function isAnswered(value: unknown): boolean {
  if (value === undefined || value === null || value === "") {
    return false;
  }
  if (Array.isArray(value)) {
    return value.length > 0;
  }
  return true;
}

function extractScores(section: unknown, key: "raw_scores" | "normalized"): Record<string, number> {
  if (!section || typeof section !== "object") {
    return {};
  }
  const raw = (section as Record<string, unknown>)[key];
  if (!raw || typeof raw !== "object") {
    return {};
  }
  return Object.fromEntries(
    Object.entries(raw as Record<string, unknown>).map(([entryKey, value]) => [entryKey, Number(value)]),
  );
}

function extractTraits(section: unknown): string[] {
  if (!section || typeof section !== "object") {
    return [];
  }
  const traits = (section as Record<string, unknown>).dominant_traits;
  if (!Array.isArray(traits)) {
    return [];
  }
  return traits.map((item) => String(item));
}

function normalizePercent(value: number): number {
  const normalized = value > 1 ? value / 100 : value;
  return Math.max(0, Math.min(1, normalized));
}

function formatPercent(value: number): string {
  return `${Math.round(normalizePercent(value) * 100)}%`;
}

function ChartCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <article className="info-group-card diagnostic-result-card">
      <h6>{title}</h6>
      {children}
    </article>
  );
}

function renderLaaProfile(scores: Record<string, number>) {
  const entries = Object.entries(scores);
  if (entries.length === 0) {
    return <p className="diagnostic-card-empty">No data yet.</p>;
  }
  const colors = ["#f59e0b", "#fb923c", "#f97316", "#38bdf8", "#6366f1", "#10b981"];
  return (
    <div className="diagnostic-laa-bars">
      {entries.map(([key, value], index) => (
        <div key={key} className="diagnostic-laa-row">
          <span>{formatDimensionLabel(key)}</span>
          <div className="diagnostic-moa-track">
            <div
              style={{
                width: `${normalizePercent(value) * 100}%`,
                background: colors[index % colors.length],
              }}
            />
          </div>
          <strong>{formatPercent(value)}</strong>
        </div>
      ))}
    </div>
  );
}

function renderMoaProfile(scores: Record<string, number>) {
  const entries = Object.entries(scores);
  if (entries.length === 0) {
    return <p className="diagnostic-card-empty">No data yet.</p>;
  }
  return (
    <div className="diagnostic-moa-bars">
      {entries.map(([key, value]) => (
        <div key={key} className="diagnostic-moa-row">
          <span>{formatDimensionLabel(key)}</span>
          <div className="diagnostic-moa-track"><div style={{ width: `${normalizePercent(value) * 100}%` }} /></div>
          <strong>{formatPercent(value)}</strong>
        </div>
      ))}
    </div>
  );
}

function renderLtaProfile(scores: Record<string, number>, dominantTraits: string[]) {
  const entries = Object.entries(scores);
  if (entries.length === 0) {
    return <p className="diagnostic-card-empty">No data yet.</p>;
  }
  const total = entries.reduce((sum, [, value]) => sum + normalizePercent(value), 0);
  if (total <= 0) {
    return <p className="diagnostic-card-empty">No data yet.</p>;
  }
  let offset = 0;
  const colors = ["#f59e0b", "#10b981", "#3b82f6", "#8b5cf6", "#ef4444"];
  return (
    <div className="diagnostic-lta-wrap">
      <svg width="180" height="180" viewBox="0 0 220 220" role="img" aria-label="LTA donut chart" className="diagnostic-lta-donut">
        {entries.map(([key, value], index) => {
          const ratio = normalizePercent(value) / total;
          const dash = `${ratio * 502} 502`;
          const node = (
            <circle
              key={key}
              cx="110"
              cy="110"
              r="80"
              fill="none"
              stroke={colors[index % colors.length]}
              strokeWidth="28"
              strokeDasharray={dash}
              strokeDashoffset={-offset}
              transform="rotate(-90 110 110)"
            />
          );
          offset += ratio * 502;
          return node;
        })}
        <circle cx="110" cy="110" r="56" fill="#fff" />
      </svg>
      <div className="diagnostic-legend-list">
        {entries.map(([key, value], index) => (
          <div key={key} className="diagnostic-legend-row">
            <span className="diagnostic-legend-key"><i style={{ background: colors[index % colors.length] }} />{formatDimensionLabel(key)}</span>
            <strong>{formatPercent(value)}</strong>
          </div>
        ))}
      </div>
      {dominantTraits.length > 0 ? (
        <p className="diagnostic-card-meta">Dominant learning type: {dominantTraits.map(formatDimensionLabel).join(" / ")}</p>
      ) : null}
    </div>
  );
}

function formatDimensionLabel(rawKey: string): string {
  const raw = String(rawKey || "").trim();
  const key = raw.toLowerCase();
  const normalizedKey = normalizeDimensionKey(raw);
  const laaMatch = mapLaaLabel(normalizedKey);
  if (laaMatch) {
    return laaMatch;
  }
  const dictionary: Record<string, string> = {
    [normalizeDimensionKey("Nutherbedürfnisse")]: "User needs",
    [normalizeDimensionKey("Lernerfahrung und Selbstbild")]: "Learning experience",
    [normalizeDimensionKey("Zeit und Rahmenbedingungen")]: "Conditions",
    [normalizeDimensionKey("Lernziele & Motivation")]: "Objectives",
    [normalizeDimensionKey("Skills & Interessen")]: "Skills and Interests",
    [normalizeDimensionKey("Emotionale Haltung zum Lernen")]: "Attitude",
    [normalizeDimensionKey("Lernblockaden & Unterstützungsbedarfe")]: "Support needs",
    [normalizeDimensionKey("Sonstiges zur Personalisierung")]: "Miscellaneous",
    [normalizeDimensionKey("User needs")]: "User needs",
    [normalizeDimensionKey("Learning experience")]: "Learning experience",
    [normalizeDimensionKey("Conditions")]: "Conditions",
    [normalizeDimensionKey("Objectives")]: "Objectives",
    [normalizeDimensionKey("Skills and Interests")]: "Skills and Interests",
    [normalizeDimensionKey("Attitude")]: "Attitude",
    [normalizeDimensionKey("Support needs")]: "Support needs",
    [normalizeDimensionKey("Miscellaneous")]: "Miscellaneous",
    [normalizeDimensionKey("Erkenntnis/Wissen")]: "Knowledge",
    [normalizeDimensionKey("Gestaltung/Kreativität")]: "Creativity",
    [normalizeDimensionKey("Einfluss/Wirksamkeit")]: "Influence",
    [normalizeDimensionKey("Sinn/Beitrag")]: "Meaning",
    [normalizeDimensionKey("Beziehung/Verbundenheit")]: "Connection",
    [normalizeDimensionKey("Ordnung/Sicherheit")]: "Routine",
    [normalizeDimensionKey("Leistung/Kompetenzaufbau")]: "Performance",
    [normalizeDimensionKey("Autonomie/Selbstbestimmung")]: "Autonomy",
    [normalizeDimensionKey("Status/Bestätigung")]: "Confirmation",
    [normalizeDimensionKey("Experimentieren/Handlungsorientierung")]: "Experimenting",
    [normalizeDimensionKey("Insight/Knowledge")]: "Knowledge",
    [normalizeDimensionKey("Design/Creativity")]: "Creativity",
    [normalizeDimensionKey("Influence/Effectiveness")]: "Influence",
    [normalizeDimensionKey("Meaning/Contribution")]: "Meaning",
    [normalizeDimensionKey("Relationship/Connection")]: "Connection",
    [normalizeDimensionKey("Order/Security")]: "Routine",
    [normalizeDimensionKey("Performance/Competence Development")]: "Performance",
    [normalizeDimensionKey("Autonomy/Self-determination")]: "Autonomy",
    [normalizeDimensionKey("Status/Approval")]: "Confirmation",
    [normalizeDimensionKey("Experimentation/Freedom of action")]: "Experimenting",
    auditiv: "Auditory",
    auditory: "Auditory",
    auditic: "Auditory",
    visuell: "Visual",
    visual: "Visual",
    kinaesthetisch: "Kinesthetic",
    kinasthetisch: "Kinesthetic",
    kinesthetic: "Kinesthetic",
    lesen_schreiben: "Cognitive",
    kognitive: "Cognitive",
    cognitive: "Cognitive",
  };
  if (dictionary[key]) {
    return dictionary[key];
  }
  if (dictionary[normalizedKey]) {
    return dictionary[normalizedKey];
  }
  if (normalizedKey.includes("insight") && normalizedKey.includes("knowledge")) {
    return "Knowledge";
  }
  if (normalizedKey.includes("design") && normalizedKey.includes("creativity")) {
    return "Creativity";
  }
  if (normalizedKey.includes("influence") && (normalizedKey.includes("effectiveness") || normalizedKey.includes("wirksamkeit"))) {
    return "Influence";
  }
  if (normalizedKey.includes("meaning") && normalizedKey.includes("contribution")) {
    return "Meaning";
  }
  if (normalizedKey.includes("relationship") && normalizedKey.includes("connection")) {
    return "Connection";
  }
  if (normalizedKey.includes("order") && normalizedKey.includes("security")) {
    return "Routine";
  }
  if (normalizedKey.includes("performance") && normalizedKey.includes("competence")) {
    return "Performance";
  }
  if (normalizedKey.includes("autonomy") && normalizedKey.includes("self")) {
    return "Autonomy";
  }
  if (normalizedKey.includes("status") && (normalizedKey.includes("approval") || normalizedKey.includes("bestatigung"))) {
    return "Confirmation";
  }
  if (
    (normalizedKey.includes("experiment") || normalizedKey.includes("experiement"))
    && (normalizedKey.includes("freedom") || normalizedKey.includes("handlungs"))
  ) {
    return "Experimenting";
  }
  return key
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function normalizeDimensionKey(value: string): string {
  return String(value || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function sanitizeDiagnosticText(value: string): string {
  return String(value || "")
    .replace(/\bmythriq\b/gi, "")
    .replace(/\baember\b/gi, "")
    .replace(/\s{2,}/g, " ")
    .replace(/\s+\-/g, " -")
    .trim();
}

function formatAttemptDate(rawIso: string): string {
  const date = new Date(rawIso);
  if (Number.isNaN(date.getTime())) {
    return rawIso;
  }
  const dd = String(date.getDate()).padStart(2, "0");
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const yyyy = date.getFullYear();
  const hh = String(date.getHours()).padStart(2, "0");
  const min = String(date.getMinutes()).padStart(2, "0");
  return `${dd}.${mm}.${yyyy} - ${hh}:${min}`;
}

function formatVersionLabel(rawVersion: string, diagnosticType?: "LAA" | "MOA" | "LTA"): string {
  const value = String(rawVersion || "").trim();
  if (!value) {
    return "-";
  }
  if (value.startsWith("v")) {
    return value;
  }
  if (/^\d{8}[a-z]?$/i.test(value) && diagnosticType) {
    const mapped = { LAA: "1.1", MOA: "1.0", LTA: "1.0" }[diagnosticType];
    return `v${mapped}`;
  }
  const compact = value.match(/^(\d{4})(\d{2})(\d{2})([a-z])?$/i);
  if (compact) {
    const [_, yyyy, mm, dd] = compact;
    return `v${dd}.${mm}.${yyyy.slice(2)}`;
  }
  return `v${value}`;
}

function formatAttemptVersions(definitionVersions: Record<string, string>): string {
  const parts: string[] = [];
  for (const key of ["LAA", "MOA", "LTA"]) {
    const version = definitionVersions[key];
    if (!version) {
      continue;
    }
    parts.push(`${key} ${formatVersionLabel(version, key as "LAA" | "MOA" | "LTA")}`);
  }
  return parts.length > 0 ? parts.join(" - ") : "-";
}

function normalizeAndOrderScores(
  scores: Record<string, number>,
  type: "LAA" | "MOA",
): Record<string, number> {
  const canonicalOrder = type === "LAA"
    ? ["User needs", "Learning experience", "Conditions", "Objectives", "Skills and Interests", "Attitude", "Support needs", "Miscellaneous"]
    : ["Knowledge", "Creativity", "Influence", "Meaning", "Connection", "Routine", "Performance", "Autonomy", "Confirmation", "Experimenting"];

  const grouped = new Map<string, number[]>();
  for (const [rawKey, rawValue] of Object.entries(scores)) {
    const label = canonicalLabel(rawKey);
    const current = grouped.get(label) ?? [];
    current.push(rawValue);
    grouped.set(label, current);
  }

  const orderedEntries: Array<[string, number]> = [];
  for (const label of canonicalOrder) {
    const values = grouped.get(label);
    if (!values || values.length === 0) {
      continue;
    }
    const avg = values.reduce((sum, value) => sum + value, 0) / values.length;
    orderedEntries.push([label, avg]);
  }

  for (const [label, values] of grouped.entries()) {
    if (canonicalOrder.includes(label)) {
      continue;
    }
    const avg = values.reduce((sum, value) => sum + value, 0) / values.length;
    orderedEntries.push([label, avg]);
  }

  return Object.fromEntries(orderedEntries);
}

function normalizeTraitLabels(
  traits: string[],
  type: "LAA" | "MOA",
): string[] {
  const canonicalOrder = type === "LAA"
    ? ["User needs", "Learning experience", "Conditions", "Objectives", "Skills and Interests", "Attitude", "Support needs", "Miscellaneous"]
    : ["Knowledge", "Creativity", "Influence", "Meaning", "Connection", "Routine", "Performance", "Autonomy", "Confirmation", "Experimenting"];
  const set = new Set(traits.map((item) => canonicalLabel(item)));
  return canonicalOrder.filter((label) => set.has(label));
}

function canonicalLabel(value: string): string {
  return formatDimensionLabel(value);
}

function mapLaaLabel(normalizedKey: string): string | null {
  if (!normalizedKey) {
    return null;
  }
  const key = ` ${normalizedKey} `;

  // LAA aliases from doc/source variants and parser outputs.
  if (
    key.includes(" nutzerbedurf") ||
    key.includes(" nutzerbeduerf") ||
    key.includes(" nutherbedurf") ||
    key.includes(" nutzer bedurf") ||
    key.includes(" user needs ")
  ) {
    return "User needs";
  }
  if (
    key.includes(" lernerfahrung ") ||
    key.includes(" selbstbild ") ||
    key.includes(" learning experience ")
  ) {
    return "Learning experience";
  }
  if (
    (key.includes(" zeit ") && key.includes(" rahmen")) ||
    key.includes(" conditions ")
  ) {
    return "Conditions";
  }
  if (
    key.includes(" lernziele ") ||
    (key.includes(" lernziele") && key.includes(" motivation")) ||
    key.includes(" objectives ")
  ) {
    return "Objectives";
  }
  if (
    key.includes(" skills interessen ") ||
    key.includes(" skills und interessen ") ||
    key.includes(" interessen ") ||
    key.includes(" kompetenzen ") ||
    key.includes(" soft skills ") ||
    key.includes(" skills and interests ")
  ) {
    return "Skills and Interests";
  }
  if (
    key.includes(" emotionale haltung ") ||
    (key.includes(" haltung ") && key.includes(" lernen")) ||
    key.includes(" attitude ")
  ) {
    return "Attitude";
  }
  if (
    key.includes(" lernblockaden ") ||
    key.includes(" unterstutzungsbedar") ||
    key.includes(" support need ") ||
    key.includes(" support needs ")
  ) {
    return "Support needs";
  }
  if (
    key.includes(" sonstiges ") ||
    key.includes(" personalisierung ") ||
    key.includes(" miscellaneous ")
  ) {
    return "Miscellaneous";
  }
  return null;
}
