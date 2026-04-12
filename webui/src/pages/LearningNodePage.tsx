import { useEffect, useMemo, useState, type Dispatch, type SetStateAction } from "react";
import { Icon } from "../components/common/Icons";
import type { LearningNodeExecutionAttempt, LearningNodeSession, LearningPath, SkilltreeNode } from "../types/chat";

type LearningNodePageProps = {
  loading: boolean;
  error: string | null;
  session: LearningNodeSession | null;
  learningPath: LearningPath | null;
  pathLoading: boolean;
  pathError: string | null;
  attempt: LearningNodeExecutionAttempt | null;
  attemptLoading: boolean;
  attemptError: string | null;
  onMilestoneFinish?: () => void;
  milestoneFinishing?: boolean;
};

type AnswerMap = Record<string, string>;
type MultiAnswerMap = Record<string, string[]>;
type UploadMap = Record<string, File[]>;

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function asText(value: unknown, fallback = ""): string {
  const text = String(value ?? "").trim();
  return text || fallback;
}

function normalizeQuestionId(input: unknown, fallbackPrefix: string, index: number): string {
  const raw = asText(input);
  return raw || `${fallbackPrefix}-${index + 1}`;
}

function formatKsaTag(value: unknown): string {
  const record = asRecord(value);
  const dimension = asText(record.dimension, "?").toUpperCase();
  const topic = asText(record.topic, "Unknown");
  const subtopic = asText(record.subtopic);
  return `${dimension}: ${topic}${subtopic ? `/${subtopic}` : ""}`;
}

function parseMilestoneTopic(value: unknown): { dimension: string; topic: string; subtopic: string } {
  const raw = asText(value);
  if (!raw) {
    return { dimension: "?", topic: "Unknown", subtopic: "" };
  }
  const dimensionMatch = raw.match(/^([KSA])\./i);
  const dimension = dimensionMatch ? dimensionMatch[1].toUpperCase() : "?";
  const normalized = raw.replace(/^[KSA]\./i, "");
  const [topic, ...rest] = normalized.split(".");
  return {
    dimension,
    topic: asText(topic, "Unknown"),
    subtopic: rest.join("."),
  };
}

function milestoneStatusKind(statusValue: unknown): "created" | "in_progress" | "completed" {
  const normalized = asText(statusValue).toLowerCase();
  if (normalized === "completed" || normalized === "mastered") {
    return "completed";
  }
  if (normalized === "in_progress" || normalized === "available" || normalized === "failed_needs_retry") {
    return "in_progress";
  }
  return "created";
}

function milestoneStatusLabel(status: "created" | "in_progress" | "completed"): string {
  if (status === "completed") {
    return "Completed";
  }
  if (status === "in_progress") {
    return "In Progress";
  }
  return "Created";
}

function nodeTypeIconName(typeValue: unknown): "play" | "check" | "archive" | "academic-hat" | "book" | "certificate" {
  const type = asText(typeValue);
  if (type === "practice") {
    return "play";
  }
  if (type === "quiz" || type === "checkpoint") {
    return "check";
  }
  if (type === "milestone" || type === "capstone") {
    return "academic-hat";
  }
  if (type === "unlock_gate" || type === "review" || type === "assessment_hook") {
    return "archive";
  }
  return "book";
}

function getRouteLabel(node: SkilltreeNode, learningPath: LearningPath | null): string {
  const displayRoute = asText(asRecord(node.display).route_name || asRecord(node.display).route_title);
  if (displayRoute) {
    return displayRoute;
  }
  const metadataRoute = asText(asRecord(node.metadata).route_name || asRecord(node.metadata).route_title);
  if (metadataRoute) {
    return metadataRoute;
  }
  if (node.branch_id && learningPath) {
    const branch = learningPath.branches.find((entry) => entry.id === node.branch_id);
    if (branch?.title) {
      return branch.title;
    }
  }
  return "General";
}

function renderMetadataTags(node: SkilltreeNode, learningPath: LearningPath | null) {
  const chapterTitle = node.chapter_id && learningPath
    ? learningPath.chapters.find((entry) => entry.id === node.chapter_id)?.title ?? node.chapter_id
    : "General";
  const branchTitle = node.branch_id && learningPath
    ? learningPath.branches.find((entry) => entry.id === node.branch_id)?.title ?? node.branch_id
    : "Default";
  const routeLabel = getRouteLabel(node, learningPath);
  return (
    <div className="learning-node-page-tag-row">
      <span className="tag-pill">Type: {node.type}</span>
      <span className="tag-pill">Chapter: {chapterTitle}</span>
      <span className="tag-pill">Branch: {branchTitle}</span>
      <span className="tag-pill">Route: {routeLabel}</span>
      <span className="tag-pill">{node.required ? "Required" : "Optional"}</span>
      {node.ksa.map((item, index) => (
        <span key={`${node.id}-ksa-${index}`} className="tag-pill">
          {`${item.dimension}: ${item.topic}${item.subtopic ? `/${item.subtopic}` : ""}`}
        </span>
      ))}
    </div>
  );
}

function MultipleChoiceQuestion({
  question,
  index,
  singleAnswers,
  multiAnswers,
  setSingleAnswers,
  setMultiAnswers,
}: {
  question: Record<string, unknown>;
  index: number;
  singleAnswers: AnswerMap;
  multiAnswers: MultiAnswerMap;
  setSingleAnswers: Dispatch<SetStateAction<AnswerMap>>;
  setMultiAnswers: Dispatch<SetStateAction<MultiAnswerMap>>;
}) {
  const questionId = normalizeQuestionId(question.id, "mc", index);
  const questionType = asText(question.type, "single").toLowerCase();
  const isMultiple = questionType === "multiple" || questionType === "multi";
  const options = asArray(question.options).map((item) => asText(item)).filter(Boolean);

  return (
    <article className="ksa-question-card learning-node-question-card">
      <h4>Question {index + 1}</h4>
      <p>{asText(question.question, "Question prompt missing.")}</p>
      <p className="ksa-drill-topic-meta">{asText(question.topic, "General topic")}</p>
      <div className="diagnostic-options-list">
        {options.map((option) => (
          <label
            key={`${questionId}-${option}`}
            className={`diagnostic-option-card${
              isMultiple
                ? (multiAnswers[questionId] ?? []).includes(option)
                  ? " selected"
                  : ""
                : singleAnswers[questionId] === option
                  ? " selected"
                  : ""
            }`}
          >
            <input
              type={isMultiple ? "checkbox" : "radio"}
              name={questionId}
              checked={isMultiple ? (multiAnswers[questionId] ?? []).includes(option) : singleAnswers[questionId] === option}
              onChange={(event) => {
                if (isMultiple) {
                  setMultiAnswers((current) => {
                    const currentValues = current[questionId] ?? [];
                    const nextValues = event.target.checked
                      ? [...currentValues, option]
                      : currentValues.filter((value) => value !== option);
                    return { ...current, [questionId]: nextValues };
                  });
                  return;
                }
                setSingleAnswers((current) => ({ ...current, [questionId]: option }));
              }}
            />
            <span>{option}</span>
          </label>
        ))}
      </div>
    </article>
  );
}

function FreeTextQuestion({
  question,
  index,
  answers,
  setAnswers,
  answerKeyPrefix,
}: {
  question: Record<string, unknown>;
  index: number;
  answers: AnswerMap;
  setAnswers: Dispatch<SetStateAction<AnswerMap>>;
  answerKeyPrefix: string;
}) {
  const questionId = normalizeQuestionId(question.id, answerKeyPrefix, index);
  const rubric = asArray(question.rubric).map((item) => asText(item)).filter(Boolean);

  return (
    <article className="ksa-question-card learning-node-question-card">
      <h4>Prompt {index + 1}</h4>
      <p>{asText(question.question || question.prompt, "Prompt missing.")}</p>
      <p className="ksa-drill-topic-meta">{asText(question.topic, "General topic")}</p>
      {rubric.length > 0 ? (
        <div className="learning-node-rubric-row">
          {rubric.map((item) => (
            <span key={`${questionId}-${item}`} className="tag-pill">
              {item}
            </span>
          ))}
        </div>
      ) : null}
      <textarea
        className="dialog-input diagnostic-textarea"
        rows={4}
        placeholder="Write your answer here..."
        value={answers[questionId] ?? ""}
        onChange={(event) => setAnswers((current) => ({ ...current, [questionId]: event.target.value }))}
      />
    </article>
  );
}

function DrillQuestion({
  question,
  singleAnswers,
  setSingleAnswers,
  textAnswers,
  setTextAnswers,
  index,
}: {
  question: Record<string, unknown>;
  singleAnswers: AnswerMap;
  setSingleAnswers: Dispatch<SetStateAction<AnswerMap>>;
  textAnswers: AnswerMap;
  setTextAnswers: Dispatch<SetStateAction<AnswerMap>>;
  index: number;
}) {
  const questionId = normalizeQuestionId(question.id, "drill", index);
  const choices = asArray(question.choices).map((item) => asText(item)).filter(Boolean);

  return (
    <article className="ksa-question-card learning-node-question-card">
      <div className="ksa-drill-question-meta">
        <span>{asText(question.topic_name, "Topic")}</span>
        <span>{asText(question.block_label, "Round")}</span>
        <span>{asText(question.kind, "Question").replace(/_/g, " ")}</span>
      </div>
      <p>{asText(question.prompt, "Question prompt missing.")}</p>
      {choices.length > 0 ? (
        <div className="diagnostic-options-list">
          {choices.map((choice) => (
            <label key={`${questionId}-${choice}`} className={`diagnostic-option-card${singleAnswers[questionId] === choice ? " selected" : ""}`}>
              <input
                type="radio"
                name={questionId}
                checked={singleAnswers[questionId] === choice}
                onChange={() => setSingleAnswers((current) => ({ ...current, [questionId]: choice }))}
              />
              <span>{choice}</span>
            </label>
          ))}
        </div>
      ) : (
        <textarea
          className="dialog-input diagnostic-textarea"
          rows={4}
          placeholder="Write your answer here..."
          value={textAnswers[questionId] ?? ""}
          onChange={(event) => setTextAnswers((current) => ({ ...current, [questionId]: event.target.value }))}
        />
      )}
    </article>
  );
}

function PracticeTask({
  task,
  index,
  textAnswers,
  setTextAnswers,
  uploads,
  setUploads,
}: {
  task: Record<string, unknown>;
  index: number;
  textAnswers: AnswerMap;
  setTextAnswers: Dispatch<SetStateAction<AnswerMap>>;
  uploads: UploadMap;
  setUploads: Dispatch<SetStateAction<UploadMap>>;
}) {
  const taskId = normalizeQuestionId(task.id, "task", index);
  const rubric = asArray(task.rubric).map((item) => asText(item)).filter(Boolean);
  const isUploadTask = asText(task.type) === "artifact_upload";
  const uploadFiles = uploads[taskId] ?? [];

  return (
    <article className="ksa-question-card learning-node-question-card">
      <h4>{asText(task.title, `Practice Task ${index + 1}`)}</h4>
      <p>{asText(task.prompt, "Task prompt missing.")}</p>
      <p className="ksa-drill-topic-meta">
        {asText(task.topic, "General topic")}
        {task.required ? " · required" : " · optional"}
      </p>
      {rubric.length > 0 ? (
        <div className="learning-node-rubric-row">
          {rubric.map((item) => (
            <span key={`${taskId}-${item}`} className="tag-pill">
              {item}
            </span>
          ))}
        </div>
      ) : null}
      {isUploadTask ? (
        <div className="learning-node-practice-split">
          <textarea
            className="dialog-input diagnostic-textarea"
            rows={6}
            placeholder="Describe your approach, notes, and solution summary..."
            value={textAnswers[taskId] ?? ""}
            onChange={(event) => setTextAnswers((current) => ({ ...current, [taskId]: event.target.value }))}
          />
          <div className="learning-node-upload-box">
            <label className="secondary-button learning-node-upload-trigger">
              Select files
              <input
                type="file"
                multiple
                onChange={(event) => {
                  const selected = Array.from(event.target.files ?? []);
                  setUploads((current) => ({ ...current, [taskId]: selected }));
                }}
              />
            </label>
            <div className="composer-attachment-chip-list">
              {uploadFiles.length === 0 ? <small>No files selected yet.</small> : null}
              {uploadFiles.map((file) => (
                <div key={`${taskId}-${file.name}-${file.size}`} className="composer-attachment-chip">
                  <span className="composer-attachment-meta">
                    <span className="composer-attachment-name">{file.name}</span>
                    <span className="composer-attachment-ext">{file.name.split(".").pop()?.toUpperCase() ?? "FILE"}</span>
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <textarea
          className="dialog-input diagnostic-textarea"
          rows={5}
          placeholder="Write your response..."
          value={textAnswers[taskId] ?? ""}
          onChange={(event) => setTextAnswers((current) => ({ ...current, [taskId]: event.target.value }))}
        />
      )}
    </article>
  );
}

export function LearningNodePage({
  loading,
  error,
  session,
  learningPath,
  pathLoading,
  pathError,
  attempt,
  attemptLoading,
  attemptError,
  onMilestoneFinish,
  milestoneFinishing = false,
}: LearningNodePageProps) {
  const [singleAnswers, setSingleAnswers] = useState<AnswerMap>({});
  const [multiAnswers, setMultiAnswers] = useState<MultiAnswerMap>({});
  const [textAnswers, setTextAnswers] = useState<AnswerMap>({});
  const [uploads, setUploads] = useState<UploadMap>({});

  useEffect(() => {
    setSingleAnswers({});
    setMultiAnswers({});
    setTextAnswers({});
    setUploads({});
  }, [session?.id]);

  const node = useMemo(() => {
    if (!session || !learningPath) {
      return null;
    }
    return learningPath.nodes.find((item) => item.id === session.node_id) ?? null;
  }, [learningPath, session]);

  const packageData = asRecord(attempt?.package);
  const milestoneRelevantNodes = useMemo(() => {
    const packageNodes = asArray(packageData.completed_relevant_nodes).map((item) => asRecord(item));
    if (packageNodes.length > 0) {
      return packageNodes;
    }
    const snapshot = asRecord(attempt?.context_snapshot);
    const prior = asRecord(snapshot.prior_node_context);
    return asArray(prior.completed_relevant_nodes).map((item) => asRecord(item));
  }, [attempt?.context_snapshot, packageData.completed_relevant_nodes]);
  const milestoneTopicRows = useMemo(
    () =>
      milestoneRelevantNodes.flatMap((item) =>
        asArray(item.topics)
          .map((topic) => parseMilestoneTopic(topic))
          .map((topic) => ({
            nodeTitle: asText(item.title, "Completed Node"),
            nodeType: asText(item.type, "learning_unit"),
            status: milestoneStatusKind(item.status),
            dimension: topic.dimension,
            topic: topic.topic,
            subtopic: topic.subtopic,
          })),
      ),
    [milestoneRelevantNodes],
  );

  const drillQuestions = useMemo(() => {
    if (node?.type === "assessment_hook") {
      return asArray(packageData.question_set).map((item) => asRecord(item));
    }
    const rounds = asArray(packageData.deep_dive_rounds).map((item) => asRecord(item));
    return rounds.flatMap((round) => asArray(round.questions).map((question) => asRecord(question)));
  }, [node?.type, packageData.deep_dive_rounds, packageData.question_set]);

  const quizMcQuestions = asArray(packageData.mc_questions).map((item) => asRecord(item));
  const quizFreeTextQuestions = (asArray(packageData.free_text_questions).length > 0
    ? asArray(packageData.free_text_questions)
    : asArray(packageData.free_text_quiz_questions)
  ).map((item) => asRecord(item));
  const practiceTasks = (asArray(packageData.tasks).length > 0
    ? asArray(packageData.tasks)
    : asArray(packageData.scenario_practice_questions).map((item) => ({
        ...asRecord(item),
        type: "scenario",
        title: asText(asRecord(item).question, "Scenario Practice"),
        prompt: asText(asRecord(item).question, "Scenario prompt missing."),
        required: true,
      }))
  ).map((item) => asRecord(item));

  const generatedTopics = (asArray(packageData.generated_topics).length > 0
    ? asArray(packageData.generated_topics)
    : asArray(packageData.drill_topics)
  ).map((item) => asRecord(item));
  const generationState = asText(asRecord(attempt?.result).generation_state).toLowerCase();
  const showInitialGenerationLoader = Boolean(
    node && ((attemptLoading && !attempt) || attempt?.status === "generating" || generationState === "queued"),
  );
  const showMilestoneFooterActions = Boolean(!showInitialGenerationLoader && node?.type === "milestone");

  return (
    <section className="learning-node-page-shell">
      <header className="learning-node-page-header">
        <h2>{node?.title ?? session?.node_title ?? "Learning Node"}</h2>
        <p>{asText(node?.description, "This node currently has no description.")}</p>
        {node ? renderMetadataTags(node, learningPath) : null}
      </header>

      {loading && !session ? <div className="empty-state">Loading learning node session...</div> : null}
      {error ? <div className="error-banner">{error}</div> : null}
      {pathError ? <div className="error-banner">{pathError}</div> : null}

      {!error && session ? (
        <div className="learning-node-page-card">
          {pathLoading && !node ? (
            <div className="learning-node-page-placeholder">
              Loading node metadata...
            </div>
          ) : null}

          {!pathLoading && !node ? (
            <div className="learning-node-page-placeholder">
              Node details are not available yet for this session.
            </div>
          ) : null}

          {!showInitialGenerationLoader && !attemptLoading && !attemptError && !attempt && node ? (
            <div className="learning-node-page-placeholder">
              Learning content is not ready yet for this node.
            </div>
          ) : null}

          {showInitialGenerationLoader ? (
            <div className="learning-node-initial-loading">
              <span className="learning-node-loading-circle" aria-hidden="true" />
              <strong>Please wait while we create your personal learning experience for this learning node.</strong>
              <small>This can take a little while on first start.</small>
            </div>
          ) : null}

          {!showInitialGenerationLoader && node?.type === "unlock_gate" ? (
            <div className="learning-node-page-placeholder">unlock_gate nodes do not render a dedicated learning page.</div>
          ) : null}

          {!showInitialGenerationLoader && node?.type === "milestone" ? (
            <section className="learning-node-section milestone">
              <div className="learning-node-milestone-hero">
                <div className="learning-node-milestone-badge">
                  <Icon name="certificate" />
                  <strong>Milestone Reached</strong>
                  <small>Badge preview</small>
                </div>
              </div>
              <div className="learning-node-milestone-list">
                {milestoneTopicRows.length > 0 ? (
                  <div className="learning-node-milestone-topic-table">
                    <div className="learning-node-milestone-topic-head">
                      <span>Node</span>
                      <span>KSA</span>
                      <span>Topic</span>
                      <span>Subtopic</span>
                      <span>Status</span>
                    </div>
                    <div className="learning-node-milestone-topic-body">
                      {milestoneTopicRows.map((row, index) => (
                        <div key={`${row.topic}-${row.subtopic}-${index}`} className="learning-node-milestone-topic-line">
                          <span className="learning-node-milestone-node-cell">
                            <Icon name={nodeTypeIconName(row.nodeType)} />
                            <strong>{row.nodeTitle}</strong>
                          </span>
                          <span className="learning-node-milestone-ksa-cell">{`+${row.dimension}`}</span>
                          <span>{row.topic}</span>
                          <small>{row.subtopic || "—"}</small>
                          <span className="learning-node-milestone-status-cell">
                            <span className={`learning-session-status-dot ${row.status === "in_progress" ? "in-progress" : row.status}`} aria-hidden="true">
                              {row.status === "completed" ? <Icon name="check" className="learning-session-status-icon completed" /> : null}
                            </span>
                            <small>{milestoneStatusLabel(row.status)}</small>
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="learning-node-page-placeholder">
                    No completed relevant-node topics are available yet for this milestone package.
                  </div>
                )}
              </div>
            </section>
          ) : null}

          {!showInitialGenerationLoader && node?.type === "assessment_hook" ? (
            <section className="learning-node-section">
              <h3>Generated Assessment Topics</h3>
              <div className="ksa-drill-topic-grid">
                {generatedTopics.map((topic, index) => (
                  <article key={`topic-${index}`} className="ksa-drill-topic-card">
                    <strong>{asText(topic.label || topic.detailed_topic, `Topic ${index + 1}`)}</strong>
                    <small>{formatKsaTag(topic.related_ksa)}</small>
                  </article>
                ))}
              </div>
              <h3>Assessment Questions</h3>
              <div className="learning-node-stack">
                {drillQuestions.map((question, index) => (
                  <DrillQuestion
                    key={`${asText(question.id, `drill-${index}`)}-${index}`}
                    question={question}
                    index={index}
                    singleAnswers={singleAnswers}
                    setSingleAnswers={setSingleAnswers}
                    textAnswers={textAnswers}
                    setTextAnswers={setTextAnswers}
                  />
                ))}
              </div>
            </section>
          ) : null}

          {!showInitialGenerationLoader && node?.type === "quiz" ? (
            <section className="learning-node-section">
              <h3>Quiz Questions</h3>
              <div className="learning-node-stack">
                {quizMcQuestions.map((question, index) => (
                  <MultipleChoiceQuestion
                    key={`${normalizeQuestionId(question.id, "quiz-mc", index)}-${index}`}
                    question={question}
                    index={index}
                    singleAnswers={singleAnswers}
                    multiAnswers={multiAnswers}
                    setSingleAnswers={setSingleAnswers}
                    setMultiAnswers={setMultiAnswers}
                  />
                ))}
                {quizFreeTextQuestions.map((question, index) => (
                  <FreeTextQuestion
                    key={`${normalizeQuestionId(question.id, "quiz-ft", index)}-${index}`}
                    question={question}
                    index={index}
                    answers={textAnswers}
                    setAnswers={setTextAnswers}
                    answerKeyPrefix="quiz-ft"
                  />
                ))}
              </div>
            </section>
          ) : null}

          {!showInitialGenerationLoader && node?.type === "practice" ? (
            <section className="learning-node-section">
              <h3>Practice Exercises</h3>
              <div className="learning-node-stack">
                {practiceTasks.map((task, index) => (
                  <PracticeTask
                    key={`${normalizeQuestionId(task.id, "practice", index)}-${index}`}
                    task={task}
                    index={index}
                    textAnswers={textAnswers}
                    setTextAnswers={setTextAnswers}
                    uploads={uploads}
                    setUploads={setUploads}
                  />
                ))}
              </div>
            </section>
          ) : null}

          {!showInitialGenerationLoader && (node?.type === "checkpoint" || node?.type === "capstone") ? (
            <section className="learning-node-section">
              <h3>{node.type === "capstone" ? "Capstone Assessment Bundle" : "Checkpoint Assessment Bundle"}</h3>
              <div className="learning-node-combined-grid">
                <section>
                  <h4>Quiz</h4>
                  <div className="learning-node-stack">
                    {quizMcQuestions.map((question, index) => (
                      <MultipleChoiceQuestion
                        key={`${normalizeQuestionId(question.id, "combined-mc", index)}-${index}`}
                        question={question}
                        index={index}
                        singleAnswers={singleAnswers}
                        multiAnswers={multiAnswers}
                        setSingleAnswers={setSingleAnswers}
                        setMultiAnswers={setMultiAnswers}
                      />
                    ))}
                    {quizFreeTextQuestions.map((question, index) => (
                      <FreeTextQuestion
                        key={`${normalizeQuestionId(question.id, "combined-ft", index)}-${index}`}
                        question={question}
                        index={index}
                        answers={textAnswers}
                        setAnswers={setTextAnswers}
                        answerKeyPrefix="combined-ft"
                      />
                    ))}
                  </div>
                </section>
                <section>
                  <h4>Practice</h4>
                  <div className="learning-node-stack">
                    {practiceTasks.map((task, index) => (
                      <PracticeTask
                        key={`${normalizeQuestionId(task.id, "combined-practice", index)}-${index}`}
                        task={task}
                        index={index}
                        textAnswers={textAnswers}
                        setTextAnswers={setTextAnswers}
                        uploads={uploads}
                        setUploads={setUploads}
                      />
                    ))}
                  </div>
                </section>
                <section>
                  <h4>Assessment Hook</h4>
                  <div className="ksa-drill-topic-grid">
                    {generatedTopics.map((topic, index) => (
                      <article key={`combined-topic-${index}`} className="ksa-drill-topic-card">
                        <strong>{asText(topic.label || topic.detailed_topic, `Topic ${index + 1}`)}</strong>
                        <small>{formatKsaTag(topic.related_ksa || topic)}</small>
                      </article>
                    ))}
                  </div>
                  <div className="learning-node-stack">
                    {drillQuestions.map((question, index) => (
                      <DrillQuestion
                        key={`${asText(question.id, `combined-drill-${index}`)}-${index}`}
                        question={question}
                        index={index}
                        singleAnswers={singleAnswers}
                        setSingleAnswers={setSingleAnswers}
                        textAnswers={textAnswers}
                        setTextAnswers={setTextAnswers}
                      />
                    ))}
                  </div>
                </section>
              </div>
            </section>
          ) : null}

          {!showInitialGenerationLoader && node && !["unlock_gate", "milestone", "assessment_hook", "quiz", "practice", "checkpoint", "capstone"].includes(node.type) ? (
            <div className="learning-node-page-placeholder">
              Node type <strong>{node.type}</strong> is intentionally not rendered in this step.
            </div>
          ) : null}
        </div>
      ) : null}

      {showMilestoneFooterActions ? (
        <div className="learning-node-fixed-footer">
          <div className="learning-node-fixed-footer-inner">
            <div className="learning-node-footer-actions">
              <button className="secondary-button" type="button" disabled>
                <Icon name="download" />
                Download Badge
              </button>
              <button
                className="primary-button"
                type="button"
                disabled={milestoneFinishing}
                onClick={() => {
                  onMilestoneFinish?.();
                }}
              >
                {milestoneFinishing ? "Finishing..." : "Finish"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
