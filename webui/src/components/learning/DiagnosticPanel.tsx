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
    purpose: 0.67,
    connection: 0.59,
    security: 0.51,
    achievement: 0.78,
    autonomy: 0.81,
    status: 0.46,
    experimentation: 0.87,
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
  const [openLaaSectionId, setOpenLaaSectionId] = useState<string | null>(null);
  const [openMoaProfile, setOpenMoaProfile] = useState(false);
  const [openLtaProfile, setOpenLtaProfile] = useState(false);

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
  const attemptId = attempt?.attempt?.attempt_id ?? "";

  const orderedQuestionsByType = useMemo(
    () => buildOrderedQuestionsByType(definitions, attemptId),
    [attemptId, definitions],
  );

  const questionItems = orderedQuestionsByType[currentType] ?? [];

  const currentQuestion = questionItems[questionIndex] ?? null;
  const currentValue = currentQuestion ? answersByType[currentType]?.[currentQuestion.id] : undefined;
  const currentAnswered = currentQuestion ? isAnswered(currentQuestion, currentValue) : false;

  function openDialog() {
    setDialogOpen(true);
    if (hasActiveAttempt) {
      const nextPosition = findNextQuestionPosition(orderedQuestionsByType, answersByType);
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
    const payload = Object.entries(answersByType[type] ?? {})
      .filter(([questionId]) => !questionId.endsWith("__other_text"))
      .map(([question_id, value]) => ({ question_id, value }));
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
    const previousQuestions = orderedQuestionsByType[previousStep] ?? [];
    setStepIndex((current) => current - 1);
    setQuestionIndex(Math.max(0, previousQuestions.length - 1));
  }

  const totalQuestions = questionItems.length;
  const progress = totalQuestions > 0 ? ((questionIndex + 1) / totalQuestions) * 100 : 0;

  const laaScores = normalizeAndOrderScores(extractScores(result?.result?.LAA, "normalized"), "LAA");
  const laaSectionProfiles = extractLaaSectionProfiles(result?.result?.LAA);
  const moaScores = normalizeAndOrderScores(extractScores(result?.result?.MOA, "normalized"), "MOA");
  const ltaProfile = extractLtaProfile(result?.result?.LTA);
  const moaDominant = normalizeTraitLabels(extractTraits(result?.result?.MOA), "MOA");
  const moaPersonalizedOutput = extractMoaOutput(result?.result?.MOA);

  useEffect(() => {
    if (laaSectionProfiles.length === 0) {
      setOpenLaaSectionId(null);
      return;
    }
    setOpenLaaSectionId((current) => {
      if (!current) {
        return null;
      }
      if (laaSectionProfiles.some((item) => item.sectionId === current)) {
        return current;
      }
      return null;
    });
  }, [laaSectionProfiles]);

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
                        const nextOrderedQuestionsByType = buildOrderedQuestionsByType(definitions, opened.attempt.attempt_id);
                        setAnswersByType(nextAnswers);
                        const nextPosition = findNextQuestionPosition(nextOrderedQuestionsByType, nextAnswers);
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
                  {renderLtaProfile({
                    scores: INTRO_PREVIEW.LTA,
                    counts: { auditiv: 4, visuell: 6, kinaesthetisch: 6, lesen_schreiben: 4 },
                    classification: "mixed",
                    profileLabel: "Visual + Kinesthetic",
                    summaryText:
                      "Your profile is mixed (Visual + Kinesthetic). You are likely to benefit from combining both channels consistently.",
                    resultTitle: "",
                    resultText: "",
                    dominantTraits: ["visuell", "kinaesthetisch"],
                  })}
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
              {laaSectionProfiles.length > 0 ? (
                <div className="diagnostic-laa-sections">
                  {renderLaaSectionProfiles(laaSectionProfiles, openLaaSectionId, (nextId) => setOpenLaaSectionId(nextId))}
                </div>
              ) : null}
            </ChartCard>
            <ChartCard title="Motivation (MOA)">
              {renderMoaProfile(moaScores)}
              {moaDominant.length > 0 ? <p className="diagnostic-card-meta">Top drivers: {moaDominant.map(formatDimensionLabel).join(", ")}</p> : null}
              {moaPersonalizedOutput ? (
                <section className="diagnostic-personalized-output diagnostic-moa-profile-accordion">
                  <button
                    type="button"
                    className={`diagnostic-laa-accordion-toggle${openMoaProfile ? " open" : ""}`}
                    onClick={() => setOpenMoaProfile((current) => !current)}
                  >
                    <strong>Personalized Motivation Profile</strong>
                    <span>{openMoaProfile ? "−" : "+"}</span>
                  </button>
                  {openMoaProfile ? (
                    <div className="diagnostic-laa-accordion-panel">
                      <p>
                        You’ve just discovered what truly motivates you to learn.
                      </p>
                      <p>
                        Unlike the Learning Type Analysis, which focuses on how you learn, the Motivation Analysis explores your internal “why”—the emotional and personal reasons that drive you to engage with new content.
                      </p>
                      <p>
                        Everyone learns differently—not only in their methods, but also in what motivates them.
                      </p>
                      <p>
                        In your case, the following motivations are particularly strong:
                      </p>
                      {moaPersonalizedOutput.title ? <p className="diagnostic-personalized-output-title">{moaPersonalizedOutput.title}</p> : null}
                      <p>{moaPersonalizedOutput.text}</p>
                    </div>
                  ) : null}
                </section>
              ) : null}
            </ChartCard>
            <ChartCard title="Learning Type (LTA)">
              {renderLtaProfile(ltaProfile)}
              {ltaProfile ? (
                (() => {
                  const narrative = resolveLtaNarrative(ltaProfile);
                  return (
                <section className="diagnostic-personalized-output diagnostic-moa-profile-accordion">
                  <button
                    type="button"
                    className={`diagnostic-laa-accordion-toggle${openLtaProfile ? " open" : ""}`}
                    onClick={() => setOpenLtaProfile((current) => !current)}
                  >
                    <strong>Personal Learning Type</strong>
                    <span>{openLtaProfile ? "−" : "+"}</span>
                  </button>
                  {openLtaProfile ? (
                    <div className="diagnostic-laa-accordion-panel">
                      {narrative.title ? <p className="diagnostic-personalized-output-title">{narrative.title}</p> : null}
                      <p>{narrative.text}</p>
                    </div>
                  ) : null}
                </section>
                  );
                })()
              ) : null}
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
  onChange,
}: {
  question: DiagnosticQuestion & { sectionTitle?: string };
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  const parsed = parseQuestionValue(value);
  const selectedSingle = typeof parsed.selected === "string" ? parsed.selected : "";
  const selectedMulti = Array.isArray(parsed.selected) ? parsed.selected : [];
  const currentOtherText = parsed.otherText;

  if (question.type === "single_choice") {
    return (
      <div className="diagnostic-options-list">
        {question.options.map((option) => {
          const resolvedValue = option.value ?? option.key;
          const selected = selectedSingle === resolvedValue;
          return (
            <label key={option.key} className={`diagnostic-option-card${selected ? " selected" : ""}`}>
              <input
                type="radio"
                checked={selected}
                onChange={() => onChange(buildQuestionValue(question, resolvedValue, currentOtherText))}
              />
              <span>{option.label}</span>
              {option.allows_text ? (
                <div className={`diagnostic-option-extra${selected ? " expanded" : ""}`}>
                  {selected ? (
                    <textarea
                      className="diagnostic-textarea diagnostic-misc-textarea"
                      placeholder="Please specify"
                      required
                      value={currentOtherText}
                      onChange={(event) => onChange(buildQuestionValue(question, resolvedValue, event.target.value))}
                    />
                  ) : null}
                </div>
              ) : null}
            </label>
          );
        })}
      </div>
    );
  }

  if (question.type === "multi_choice") {
    return (
      <div className="diagnostic-options-list">
        {question.options.map((option) => {
          const resolvedValue = option.value ?? option.key;
          const selected = selectedMulti.includes(resolvedValue);
          return (
            <label key={option.key} className={`diagnostic-option-card${selected ? " selected" : ""}`}>
              <input
                type="checkbox"
                checked={selected}
                onChange={(event) => {
                  const next = new Set(selectedMulti);
                  if (event.target.checked) {
                    next.add(resolvedValue);
                  } else {
                    next.delete(resolvedValue);
                  }
                  onChange(buildQuestionValue(question, Array.from(next), currentOtherText));
                }}
              />
              <span>{option.label}</span>
              {option.allows_text ? (
                <div className={`diagnostic-option-extra${selected ? " expanded" : ""}`}>
                  {selected ? (
                    <textarea
                      className="diagnostic-textarea diagnostic-misc-textarea"
                      placeholder="Please specify"
                      required
                      value={currentOtherText}
                      onChange={(event) => onChange(buildQuestionValue(question, selectedMulti, event.target.value))}
                    />
                  ) : null}
                </div>
              ) : null}
            </label>
          );
        })}
      </div>
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
                const selected = String(parsed.selected ?? "") === resolvedValue;
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
                  <label key={option.key} className={`diagnostic-option-card${String(parsed.selected ?? "") === resolvedValue ? " selected" : ""}`}>
                    <input type="radio" checked={String(parsed.selected ?? "") === resolvedValue} onChange={() => onChange(resolvedValue)} />
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
    const sliderSource = parsed.selected;
    const numericValue = typeof sliderSource === "number" || typeof sliderSource === "string" ? Number(sliderSource) : min;
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
      value={typeof parsed.selected === "string" ? parsed.selected : ""}
      onChange={(event) => onChange(event.target.value)}
      placeholder="Optional"
    />
  );
}

function buildOrderedQuestionsByType(
  definitions: Record<"LAA" | "MOA" | "LTA", DiagnosticDefinition | null>,
  attemptId: string,
): Record<"LAA" | "MOA" | "LTA", Array<DiagnosticQuestion & { sectionTitle?: string }>> {
  const result: Record<"LAA" | "MOA" | "LTA", Array<DiagnosticQuestion & { sectionTitle?: string }>> = {
    LAA: [],
    MOA: [],
    LTA: [],
  };
  for (const type of ORDER) {
    const definition = definitions[type];
    if (!definition) {
      continue;
    }
    const flat = definition.sections.flatMap((section) => section.questions.map((question) => ({
      ...question,
      options: [...question.options],
      sectionTitle: section.title,
    })));
    result[type] = orderQuestionsForAttempt(type, flat, attemptId);
  }
  return result;
}

function findNextQuestionPosition(
  orderedQuestionsByType: Record<"LAA" | "MOA" | "LTA", Array<DiagnosticQuestion & { sectionTitle?: string }>>,
  answersByType: Record<string, Record<string, unknown>>,
): { stepIndex: number; questionIndex: number } {
  for (let typeIndex = 0; typeIndex < ORDER.length; typeIndex += 1) {
    const type = ORDER[typeIndex];
    const questions = orderedQuestionsByType[type] ?? [];
    const answers = answersByType[type] ?? {};
    for (let idx = 0; idx < questions.length; idx += 1) {
      const question = questions[idx];
      const value = answers[question.id];
      if (!isAnswered(question, value)) {
        return { stepIndex: typeIndex, questionIndex: idx };
      }
    }
  }
  return { stepIndex: 0, questionIndex: 0 };
}

function isAnswered(question: DiagnosticQuestion, value: unknown): boolean {
  const parsed = parseQuestionValue(value);
  if (parsed.selected === undefined || parsed.selected === null || parsed.selected === "") {
    return false;
  }
  if (Array.isArray(parsed.selected) && parsed.selected.length === 0) {
    return false;
  }
  const otherOption = question.options.find((option) => option.allows_text);
  if (!otherOption) {
    return true;
  }
  const otherValue = otherOption.value ?? otherOption.key;
  if (Array.isArray(parsed.selected) && parsed.selected.includes(otherValue)) {
    return parsed.otherText.trim().length > 0;
  }
  if (typeof parsed.selected === "string" && parsed.selected === otherValue) {
    return parsed.otherText.trim().length > 0;
  }
  return true;
}

function parseQuestionValue(value: unknown): { selected: unknown; otherText: string } {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return { selected: value, otherText: "" };
  }
  const source = value as Record<string, unknown>;
  return {
    selected: source.selected,
    otherText: typeof source.other_text === "string" ? source.other_text : "",
  };
}

function buildQuestionValue(question: DiagnosticQuestion, selected: unknown, otherText: string): unknown {
  const otherOption = question.options.find((option) => option.allows_text);
  if (!otherOption) {
    return selected;
  }
  const otherValue = otherOption.value ?? otherOption.key;
  const isOtherSelected = Array.isArray(selected)
    ? selected.includes(otherValue)
    : String(selected ?? "") === otherValue;
  return {
    selected,
    other_text: isOtherSelected ? otherText : "",
  };
}

function orderQuestionsForAttempt(
  type: "LAA" | "MOA" | "LTA",
  questions: Array<DiagnosticQuestion & { sectionTitle?: string }>,
  attemptId: string,
): Array<DiagnosticQuestion & { sectionTitle?: string }> {
  if (!attemptId || questions.length <= 1) {
    return questions;
  }

  if (type === "MOA") {
    return shuffleDeterministic(questions, `${attemptId}:${type}:questions`);
  }

  if (type === "LTA") {
    const shuffledQuestions = shuffleDeterministic(questions, `${attemptId}:${type}:questions`);
    return shuffledQuestions.map((question) => ({
      ...question,
      options: shuffleDeterministic(question.options ?? [], `${attemptId}:${type}:${question.id}:options`),
    }));
  }

  return questions;
}

function shuffleDeterministic<T>(items: T[], seedKey: string): T[] {
  const values = [...items];
  if (values.length <= 1) {
    return values;
  }
  const random = createSeededRandom(hashString(seedKey));
  for (let index = values.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(random() * (index + 1));
    [values[index], values[swapIndex]] = [values[swapIndex], values[index]];
  }
  return values;
}

function hashString(value: string): number {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function createSeededRandom(seedValue: number): () => number {
  let seed = seedValue >>> 0;
  return () => {
    seed = (seed + 0x6d2b79f5) >>> 0;
    let value = seed;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
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

function extractMoaOutput(section: unknown): { title: string; text: string } | null {
  if (!section || typeof section !== "object") {
    return null;
  }
  const source = section as Record<string, unknown>;
  const text = String(source.result_text ?? "").trim();
  if (!text) {
    return null;
  }
  return {
    title: String(source.selected_result_block_title ?? "").trim(),
    text,
  };
}

const LTA_CHANNEL_ORDER = ["auditiv", "visuell", "kinaesthetisch", "lesen_schreiben"] as const;

type LtaProfile = {
  scores: Record<string, number>;
  counts: Record<string, number>;
  classification: string;
  profileLabel: string;
  summaryText: string;
  resultTitle: string;
  resultText: string;
  dominantTraits: string[];
};

function extractLtaProfile(section: unknown): LtaProfile | null {
  if (!section || typeof section !== "object") {
    return null;
  }
  const source = section as Record<string, unknown>;
  const scoreSource = (source.channel_percentages_0_100 && typeof source.channel_percentages_0_100 === "object")
    ? (source.channel_percentages_0_100 as Record<string, unknown>)
    : (source.normalized && typeof source.normalized === "object")
      ? (source.normalized as Record<string, unknown>)
      : (source.raw_scores && typeof source.raw_scores === "object")
        ? (source.raw_scores as Record<string, unknown>)
        : {};
  const countSource = (source.channel_counts && typeof source.channel_counts === "object")
    ? (source.channel_counts as Record<string, unknown>)
    : {};
  return {
    scores: Object.fromEntries(Object.entries(scoreSource).map(([key, value]) => [key, Number(value)])),
    counts: Object.fromEntries(Object.entries(countSource).map(([key, value]) => [key, Number(value)])),
    classification: String(source.classification ?? "").trim(),
    profileLabel: String(source.profile_label ?? "").trim(),
    summaryText: String(source.summary_text ?? "").trim(),
    resultTitle: String(source.selected_result_block_title ?? "").trim(),
    resultText: String(source.result_text ?? "").trim(),
    dominantTraits: Array.isArray(source.dominant_traits) ? source.dominant_traits.map((item) => String(item)) : [],
  };
}

function resolveLtaNarrative(profile: LtaProfile): { title: string; text: string } {
  if (profile.resultText.trim()) {
    return {
      title: profile.resultTitle || "",
      text: profile.resultText,
    };
  }
  const dominantTexts: Record<string, { title: string; text: string }> = {
    auditiv: {
      title: "Auditory (A)",
      text: "You learn especially well through listening and speaking. Explanations, conversations, or thinking things through out loud help you understand and retain information more effectively.",
    },
    visuell: {
      title: "Visual (V)",
      text: "You understand content best through images, structure, and visual representation. Diagrams, overviews, and clear organization help you quickly grasp relationships and concepts.",
    },
    kinaesthetisch: {
      title: "Kinesthetic (K)",
      text: "You learn most effectively through hands-on experience and active engagement. Practice, exercises, and personal experience help you internalize knowledge in a lasting way.",
    },
    lesen_schreiben: {
      title: "Reading/Writing (L)",
      text: "You learn particularly well through reading, writing, and reflection. Texts, notes, and summaries help you structure and deepen your understanding.",
    },
  };
  const mixedTexts: Record<string, { title: string; text: string }> = {
    "auditiv__visuell": {
      title: "Auditory–Visual",
      text: "You combine listening and seeing when learning. Explanations become especially clear to you when they are supported by visual structure or representation.",
    },
    "auditiv__kinaesthetisch": {
      title: "Auditory–Kinesthetic",
      text: "You benefit from hearing information while actively trying things out. Conversations combined with practical application are especially effective for your learning.",
    },
    "auditiv__lesen_schreiben": {
      title: "Auditory–Reading/Writing",
      text: "You understand content well through explanations and reinforce it through writing and note-taking. The combination of listening and written processing works particularly well for you.",
    },
    "visuell__kinaesthetisch": {
      title: "Visual–Kinesthetic",
      text: "You learn best when you can both see and actively apply what you’re learning. Visual guidance combined with hands-on practice helps you internalize content effectively.",
    },
    "visuell__lesen_schreiben": {
      title: "Visual–Reading/Writing",
      text: "You benefit greatly from structured visual representations and written processing. Overviews, notes, and clear organization support your learning optimally.",
    },
    "kinaesthetisch__lesen_schreiben": {
      title: "Kinesthetic–Reading/Writing",
      text: "You combine hands-on learning with reflective writing. Learning becomes especially effective when you apply concepts and then document or structure them afterward.",
    },
  };
  const balanced = {
    title: "Balanced",
    text: "You use different learning approaches in a relatively balanced way. Depending on the situation, you can flexibly switch between listening, observing, doing, and writing-allowing for versatile and adaptable learning.",
  };

  const normalizedTraits = (profile.dominantTraits ?? [])
    .map(normalizeLtaChannelKey)
    .filter(Boolean);
  const derived = deriveLtaClassificationFromScores(profile.scores);
  const normalizedClassification = normalizeLtaClassification(profile.classification);
  const effectiveClassification = normalizedClassification || derived.classification;
  const effectiveTraits = normalizedTraits.length > 0 ? normalizedTraits : derived.topChannels;

  if (effectiveClassification === "dominant") {
    const key = effectiveTraits[0] || normalizeLtaChannelKey(profile.profileLabel);
    if (key && dominantTexts[key]) {
      return dominantTexts[key];
    }
  }
  if (effectiveClassification === "mixed") {
    const fromLabel = profile.profileLabel.split("+").map((item) => normalizeLtaChannelKey(item)).filter(Boolean);
    const pair = (effectiveTraits.length >= 2 ? effectiveTraits.slice(0, 2) : fromLabel.slice(0, 2)).sort();
    const pairKey = pair.join("__");
    if (pairKey && mixedTexts[pairKey]) {
      return mixedTexts[pairKey];
    }
  }
  if (effectiveClassification === "balanced") {
    return balanced;
  }
  return {
    title: profile.resultTitle || "Personal Learning Type",
    text: profile.summaryText || "Your learning type profile will appear here after completing the diagnostic.",
  };
}

function normalizeLtaClassification(raw: string): "" | "dominant" | "mixed" | "balanced" {
  const value = String(raw || "").trim().toLowerCase();
  if (value === "dominant" || value === "mixed" || value === "balanced") {
    return value;
  }
  return "";
}

function deriveLtaClassificationFromScores(scores: Record<string, number>): { classification: string; topChannels: string[] } {
  const entries = LTA_CHANNEL_ORDER
    .map((channel) => [channel, normalizePercent(Number(scores[channel] ?? 0))] as const)
    .sort((a, b) => b[1] - a[1]);
  if (entries.length === 0 || entries[0][1] <= 0) {
    return { classification: "", topChannels: [] };
  }
  const top = entries[0][1];
  const second = entries[1]?.[1] ?? 0;
  const min = entries[entries.length - 1]?.[1] ?? 0;
  const max = top;
  const isBalanced = (max - min) <= 0.05;
  const isDominant = (top - second) >= 0.10;
  if (isBalanced) {
    return { classification: "balanced", topChannels: [] };
  }
  if (isDominant) {
    return { classification: "dominant", topChannels: [entries[0][0]] };
  }
  return { classification: "mixed", topChannels: [entries[0][0], entries[1]?.[0] ?? ""] .filter(Boolean) };
}

function normalizeLtaChannelKey(raw: string): string {
  const value = String(raw || "").trim().toLowerCase();
  if (!value) {
    return "";
  }
  if (value.includes("auditiv") || value.includes("auditory")) {
    return "auditiv";
  }
  if (value.includes("visuell") || value.includes("visual")) {
    return "visuell";
  }
  if (value.includes("kinaesthetisch") || value.includes("kinasthetisch") || value.includes("kinesthetic")) {
    return "kinaesthetisch";
  }
  if (value.includes("lesen") || value.includes("reading") || value.includes("writing")) {
    return "lesen_schreiben";
  }
  return "";
}

type LaaSectionProfile = {
  sectionId: string;
  sectionTitle: string;
  dimensions: Array<{ key: string; value: number }>;
  insights: string[];
  tags: Array<{ group: string; values: string[] }>;
  emotionalItems: Array<{ key: string; label: string; value: number; normalized: number }>;
  summaryIndices: Array<{ key: string; value: number }>;
};

function extractLaaSectionProfiles(section: unknown): LaaSectionProfile[] {
  if (!section || typeof section !== "object") {
    return [];
  }
  const source = section as Record<string, unknown>;
  const rawProfiles = source.section_profiles;
  if (!rawProfiles || typeof rawProfiles !== "object") {
    return [];
  }
  const profiles = rawProfiles as Record<string, unknown>;
  return Object.values(profiles)
    .filter((value): value is Record<string, unknown> => Boolean(value) && typeof value === "object")
    .map((entry) => {
      const rawDims = (entry.dimensions_normalized_0_100 && typeof entry.dimensions_normalized_0_100 === "object")
        ? (entry.dimensions_normalized_0_100 as Record<string, unknown>)
        : {};
      const dimensions = Object.entries(rawDims)
        .map(([key, value]) => ({ key, value: Number(value) }))
        .filter((item) => Number.isFinite(item.value))
        .sort((a, b) => b.value - a.value);

      const rawTags = (entry.profile_tags && typeof entry.profile_tags === "object")
        ? (entry.profile_tags as Record<string, unknown>)
        : {};
      const tags = Object.entries(rawTags)
        .filter(([, values]) => Array.isArray(values) && values.length > 0)
        .map(([group, values]) => ({ group, values: (values as unknown[]).map(String) }));

      const rawEmotional = (entry.emotional_items && typeof entry.emotional_items === "object")
        ? (entry.emotional_items as Record<string, unknown>)
        : {};
      const emotionalItems = Object.entries(rawEmotional)
        .map(([key, item]) => {
          const sourceItem = (item && typeof item === "object") ? (item as Record<string, unknown>) : {};
          return {
            key,
            label: String(sourceItem.label ?? key),
            value: Number(sourceItem.value ?? 0),
            normalized: Number(sourceItem.normalized_0_100 ?? 0),
          };
        })
        .filter((item) => Number.isFinite(item.value));

      const rawIndices = (entry.summary_indices_0_100 && typeof entry.summary_indices_0_100 === "object")
        ? (entry.summary_indices_0_100 as Record<string, unknown>)
        : {};
      const summaryIndices = Object.entries(rawIndices)
        .map(([key, value]) => ({ key, value: Number(value) }))
        .filter((item) => Number.isFinite(item.value))
        .sort((a, b) => b.value - a.value);

      const insights = Array.isArray(entry.insights) ? entry.insights.map(String).filter(Boolean) : [];

      return {
        sectionId: String(entry.section_id ?? ""),
        sectionTitle: String(entry.section_title ?? ""),
        dimensions,
        insights,
        tags,
        emotionalItems,
        summaryIndices,
      };
    })
    .sort((a, b) => a.sectionTitle.localeCompare(b.sectionTitle));
}

function renderLaaSectionProfiles(
  profiles: LaaSectionProfile[],
  openSectionId: string | null,
  onToggle: (sectionId: string | null) => void,
) {
  return profiles.map((profile) => (
    <article key={profile.sectionId} className="diagnostic-laa-section-card">
      <button
        type="button"
        className={`diagnostic-laa-accordion-toggle${openSectionId === profile.sectionId ? " open" : ""}`}
        onClick={() => onToggle(openSectionId === profile.sectionId ? null : profile.sectionId)}
      >
        <strong>{profile.sectionTitle || formatDimensionLabel(profile.sectionId)}</strong>
        <span>{openSectionId === profile.sectionId ? "−" : "+"}</span>
      </button>
      {openSectionId === profile.sectionId ? (
        <div className="diagnostic-laa-accordion-panel">
          {profile.insights.length > 0 ? (
            <ul className="diagnostic-laa-insights">
              {profile.insights.slice(0, 4).map((item) => <li key={item}>{item}</li>)}
            </ul>
          ) : null}

          {profile.dimensions.length > 0 ? (
            <div className="diagnostic-laa-dimensions">
              {profile.dimensions.slice(0, 5).map((item) => (
                <div key={item.key} className="diagnostic-laa-dimension-row">
                  <span>{formatDimensionLabel(item.key)}</span>
                  <div className="diagnostic-moa-track"><div style={{ width: `${Math.max(0, Math.min(100, item.value))}%` }} /></div>
                  <strong>{Math.round(item.value)}%</strong>
                </div>
              ))}
            </div>
          ) : null}

          {profile.summaryIndices.length > 0 ? (
            <div className="diagnostic-laa-indices">
              {profile.summaryIndices.map((item) => (
                <span key={item.key} className="diagnostic-laa-chip">{formatDimensionLabel(item.key)}: {Math.round(item.value)}%</span>
              ))}
            </div>
          ) : null}

          {profile.tags.length > 0 ? (
            <div className="diagnostic-laa-tags">
              {profile.tags.map((tagGroup) => (
                <div key={tagGroup.group}>
                  <strong>{formatDimensionLabel(tagGroup.group)}:</strong> {tagGroup.values.map(formatDimensionLabel).join(", ")}
                </div>
              ))}
            </div>
          ) : null}

          {profile.emotionalItems.length > 0 ? (
            <div className="diagnostic-laa-emotional">
              {profile.emotionalItems.map((item) => (
                <div key={item.key} className="diagnostic-laa-emotional-row">
                  <span>{item.label}</span>
                  <strong>{item.value.toFixed(1)} / 5</strong>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </article>
  ));
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

function renderLtaProfile(profile: LtaProfile | null) {
  const scores = profile?.scores ?? {};
  const counts = profile?.counts ?? {};
  const entries = LTA_CHANNEL_ORDER
    .map((channel) => [channel, Number(scores[channel] ?? 0)] as const)
    .filter(([, value]) => Number.isFinite(value));
  if (entries.length === 0) {
    return <p className="diagnostic-card-empty">No data yet.</p>;
  }
  const profileType = profile?.classification
    ? `${profile.classification.charAt(0).toUpperCase()}${profile.classification.slice(1)}`
    : "";
  const profileLabel = profile?.profileLabel ? profile.profileLabel.split("+").map((item) => formatDimensionLabel(item.trim())).join(" + ") : "";
  const hasCounts = Object.values(counts).some((value) => Number(value) > 0);
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
            {hasCounts ? <small>{Math.round(Number(counts[key] ?? 0))}</small> : null}
          </div>
        ))}
      </div>
      {profileType ? <p className="diagnostic-card-meta">Profile type: {profileType}{profileLabel ? ` (${profileLabel})` : ""}</p> : null}
      {profile?.summaryText ? <p className="diagnostic-lta-summary">{profile.summaryText}</p> : null}
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
    [normalizeDimensionKey("zielklarheit")]: "Goal clarity",
    [normalizeDimensionKey("zeitdruck")]: "Time pressure",
    [normalizeDimensionKey("strukturbedarf")]: "Need for structure",
    [normalizeDimensionKey("feedbackbedarf")]: "Need for feedback",
    [normalizeDimensionKey("selbststeuerung")]: "Self-direction",
    [normalizeDimensionKey("soziale_lernorientierung")]: "Social learning orientation",
    [normalizeDimensionKey("emotionale_sicherheit")]: "Emotional safety",
    [normalizeDimensionKey("frustrationsanfaelligkeit")]: "Frustration sensitivity",
    [normalizeDimensionKey("technikaffinitaet")]: "Technical affinity",
    [normalizeDimensionKey("praxisorientierung")]: "Practical orientation",
    [normalizeDimensionKey("sichtbarkeitsmotivation")]: "Progress visibility motivation",
    [normalizeDimensionKey("interests")]: "Interests",
    [normalizeDimensionKey("competencies")]: "Competencies",
    [normalizeDimensionKey("everyday_strengths")]: "Everyday strengths",
    [normalizeDimensionKey("digital_tools")]: "Digital tools",
    [normalizeDimensionKey("custom_inputs")]: "Custom inputs",
    [normalizeDimensionKey("lernsicherheit")]: "Learning stability",
    [normalizeDimensionKey("selbstvertrauen")]: "Self-confidence",
    [normalizeDimensionKey("aeusserer_aktivierungsbedarf")]: "External activation need",
    [normalizeDimensionKey("Erkenntnis/Wissen")]: "Knowledge",
    [normalizeDimensionKey("Gestaltung/Kreativität")]: "Creativity",
    [normalizeDimensionKey("Einfluss/Wirksamkeit")]: "Influence",
    [normalizeDimensionKey("Sinn/Beitrag")]: "Purpose",
    [normalizeDimensionKey("Beziehung/Verbundenheit")]: "Connection",
    [normalizeDimensionKey("Ordnung/Sicherheit")]: "Security",
    [normalizeDimensionKey("Leistung/Kompetenzaufbau")]: "Achievement",
    [normalizeDimensionKey("Autonomie/Selbstbestimmung")]: "Autonomy",
    [normalizeDimensionKey("Status/Bestätigung")]: "Status",
    [normalizeDimensionKey("Experimentieren/Handlungsorientierung")]: "Experimentation",
    [normalizeDimensionKey("Insight/Knowledge")]: "Knowledge",
    [normalizeDimensionKey("Design/Creativity")]: "Creativity",
    [normalizeDimensionKey("Influence/Effectiveness")]: "Influence",
    [normalizeDimensionKey("Meaning/Contribution")]: "Purpose",
    [normalizeDimensionKey("Relationship/Connection")]: "Connection",
    [normalizeDimensionKey("Order/Security")]: "Security",
    [normalizeDimensionKey("Performance/Competence Development")]: "Achievement",
    [normalizeDimensionKey("Autonomy/Self-determination")]: "Autonomy",
    [normalizeDimensionKey("Status/Approval")]: "Status",
    [normalizeDimensionKey("Experimentation/Freedom of action")]: "Experimentation",
    auditiv: "Auditory",
    auditory: "Auditory",
    auditic: "Auditory",
    visuell: "Visual",
    visual: "Visual",
    kinaesthetisch: "Kinesthetic",
    kinasthetisch: "Kinesthetic",
    kinesthetic: "Kinesthetic",
    lesen_schreiben: "Reading/Writing",
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
    return "Purpose";
  }
  if (normalizedKey.includes("relationship") && normalizedKey.includes("connection")) {
    return "Connection";
  }
  if (normalizedKey.includes("order") && normalizedKey.includes("security")) {
    return "Security";
  }
  if (normalizedKey.includes("performance") && normalizedKey.includes("competence")) {
    return "Achievement";
  }
  if (normalizedKey.includes("autonomy") && normalizedKey.includes("self")) {
    return "Autonomy";
  }
  if (normalizedKey.includes("status") && (normalizedKey.includes("approval") || normalizedKey.includes("bestatigung"))) {
    return "Status";
  }
  if (
    (normalizedKey.includes("experiment") || normalizedKey.includes("experiement"))
    && (normalizedKey.includes("freedom") || normalizedKey.includes("handlungs"))
  ) {
    return "Experimentation";
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
    : ["Knowledge", "Creativity", "Influence", "Purpose", "Connection", "Security", "Achievement", "Autonomy", "Status", "Experimentation"];

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
    : ["Knowledge", "Creativity", "Influence", "Purpose", "Connection", "Security", "Achievement", "Autonomy", "Status", "Experimentation"];
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
