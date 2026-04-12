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
  onAssessmentComplete?: (responses: Record<string, unknown>) => Promise<void>;
  assessmentFinishing?: boolean;
  onAssessmentRestart?: () => Promise<void>;
  assessmentRestarting?: boolean;
  onAssessmentStart?: () => Promise<void>;
  onGuidedComplete?: (responses: Record<string, unknown>) => Promise<void>;
  guidedCompleting?: boolean;
  onGuidedRestart?: () => Promise<void>;
  guidedRestarting?: boolean;
};

type AnswerMap = Record<string, string>;
type MultiAnswerMap = Record<string, string[]>;
type UploadMap = Record<string, File[]>;
type GuidedContentStep = "start" | "items" | "complete";

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function hasRecordFields(value: unknown): boolean {
  return Object.keys(asRecord(value)).length > 0;
}

function asText(value: unknown, fallback = ""): string {
  const text = String(value ?? "").trim();
  return text || fallback;
}

function normalizeQuestionId(input: unknown, fallbackPrefix: string, index: number): string {
  const raw = asText(input);
  return raw || `${fallbackPrefix}-${index + 1}`;
}

function dimensionFromGroup(value: unknown): string {
  const normalized = asText(value).toLowerCase();
  if (!normalized) {
    return "";
  }
  if (normalized.startsWith("knowledge")) {
    return "K";
  }
  if (normalized.startsWith("skill")) {
    return "S";
  }
  if (normalized.startsWith("abilit")) {
    return "A";
  }
  return "";
}

function parseKsaFromTopicString(value: unknown): { dimension: string; topic: string; subtopic: string } {
  const raw = asText(value);
  if (!raw) {
    return { dimension: "", topic: "", subtopic: "" };
  }
  const dotted = raw.match(/^([KSA])\.(.+)$/i);
  if (dotted) {
    const dimension = dotted[1].toUpperCase();
    const segments = dotted[2].split(".").map((item) => item.trim()).filter(Boolean);
    return {
      dimension,
      topic: asText(segments[0]),
      subtopic: segments.slice(1).join("."),
    };
  }
  return { dimension: "", topic: "", subtopic: "" };
}

function formatKsaTag(value: unknown): string {
  const root = asRecord(value);
  const record = asRecord(Object.keys(asRecord(root.related_ksa)).length > 0 ? root.related_ksa : root);
  const parsedTopicString = parseKsaFromTopicString(record.topic || root.topic || record.big_map_subdomain || root.big_map_subdomain);
  const parsedDetailedString = parseKsaFromTopicString(record.detailed_topic || root.detailed_topic || root.label);
  const dimension = (
    asText(record.dimension || root.dimension).toUpperCase()
    || asText(record.primary_type || root.primary_type).toUpperCase()
    || asText(record.type_combo || root.type_combo).split("+").map((item) => item.trim()).find(Boolean)?.toUpperCase()
    || dimensionFromGroup(record.big_map_group || root.big_map_group)
    || parsedTopicString.dimension
    || parsedDetailedString.dimension
    || "?"
  );
  const topic = (
    asText(record.topic || root.topic)
    || asText(record.big_map_subdomain || root.big_map_subdomain)
    || parsedTopicString.topic
    || parsedDetailedString.topic
    || "Unknown"
  );
  const subtopic = (
    asText(record.subtopic || root.subtopic)
    || asText(record.detailed_topic || root.detailed_topic)
    || parsedTopicString.subtopic
    || parsedDetailedString.subtopic
  );
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
  showMeta = true,
}: {
  question: Record<string, unknown>;
  singleAnswers: AnswerMap;
  setSingleAnswers: Dispatch<SetStateAction<AnswerMap>>;
  textAnswers: AnswerMap;
  setTextAnswers: Dispatch<SetStateAction<AnswerMap>>;
  index: number;
  showMeta?: boolean;
}) {
  const questionId = normalizeQuestionId(question.id, "drill", index);
  const choices = asArray(question.choices).map((item) => asText(item)).filter(Boolean);

  return (
    <article className="ksa-question-card learning-node-question-card">
      {showMeta ? (
        <div className="ksa-drill-question-meta">
          <span>{asText(question.topic_name, "Topic")}</span>
          <span>{asText(question.block_label, "Round")}</span>
          <span>{asText(question.kind, "Question").replace(/_/g, " ")}</span>
        </div>
      ) : null}
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
  const isUploadTask = asText(task.type) === "artifact_upload";
  const uploadFiles = uploads[taskId] ?? [];

  return (
    <article className="ksa-question-card learning-node-question-card">
      <h4>{asText(task.title, `Practice Task ${index + 1}`)}</h4>
      <p>{asText(task.prompt, "Task prompt missing.")}</p>
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
  onAssessmentComplete,
  assessmentFinishing = false,
  onAssessmentRestart,
  assessmentRestarting = false,
  onAssessmentStart,
  onGuidedComplete,
  guidedCompleting = false,
  onGuidedRestart,
  guidedRestarting = false,
}: LearningNodePageProps) {
  const [singleAnswers, setSingleAnswers] = useState<AnswerMap>({});
  const [multiAnswers, setMultiAnswers] = useState<MultiAnswerMap>({});
  const [textAnswers, setTextAnswers] = useState<AnswerMap>({});
  const [uploads, setUploads] = useState<UploadMap>({});
  const [assessmentStep, setAssessmentStep] = useState<"topics" | "questions" | "complete">("topics");
  const [assessmentQuestionIndex, setAssessmentQuestionIndex] = useState(0);
  const [guidedStep, setGuidedStep] = useState<GuidedContentStep>("start");
  const [guidedItemIndex, setGuidedItemIndex] = useState(0);

  useEffect(() => {
    setSingleAnswers({});
    setMultiAnswers({});
    setTextAnswers({});
    setUploads({});
    setAssessmentStep("topics");
    setAssessmentQuestionIndex(0);
    setGuidedStep("start");
    setGuidedItemIndex(0);
  }, [session?.id, attempt?.attempt_id]);

  const node = useMemo(() => {
    if (!session || !learningPath) {
      return null;
    }
    return learningPath.nodes.find((item) => item.id === session.node_id) ?? null;
  }, [learningPath, session]);

  useEffect(() => {
    if (node?.type !== "assessment_hook") {
      return;
    }
    const isCompleted = Boolean(attempt?.completed_at)
      || asText(asRecord(attempt?.result).evaluation_type) === "assessment_hook";
    if (isCompleted) {
      setAssessmentStep("complete");
      return;
    }
    setAssessmentStep("topics");
    setAssessmentQuestionIndex(0);
  }, [attempt?.completed_at, attempt?.result, node?.type]);

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
  const assessmentRounds = asArray(packageData.rounds).map((item) => asRecord(item));
  const assessmentTopicCards = useMemo(
    () =>
      (generatedTopics.length > 0 ? generatedTopics : assessmentRounds).map((topic, index) => {
        const round = assessmentRounds[index];
        const relatedKsa = asRecord(topic.related_ksa);
        const ksaSource = hasRecordFields(relatedKsa)
          ? relatedKsa
          : hasRecordFields(round)
            ? round
            : topic;
        return {
          label: asText(topic.label || topic.detailed_topic || round?.detailed_topic, `Topic ${index + 1}`),
          ksaSource,
        };
      }),
    [assessmentRounds, generatedTopics],
  );
  const generationState = asText(asRecord(attempt?.result).generation_state).toLowerCase();
  const showInitialGenerationLoader = Boolean(
    node && ((attemptLoading && !attempt) || attempt?.status === "generating" || generationState === "queued"),
  );
  const showMilestoneFooterActions = Boolean(!showInitialGenerationLoader && node?.type === "milestone");
  const showAssessmentFooterActions = Boolean(!showInitialGenerationLoader && node?.type === "assessment_hook");
  const isGuidedNodeType = Boolean(node && ["quiz", "practice", "checkpoint", "capstone"].includes(node.type));
  const guidedItems = useMemo(() => {
    if (!node) {
      return [] as Array<{ kind: "mc" | "ft" | "practice" | "drill"; payload: Record<string, unknown>; index: number; prefix: string }>;
    }
    if (node.type === "quiz") {
      return [
        ...quizMcQuestions.map((payload, index) => ({ kind: "mc" as const, payload, index, prefix: "quiz-mc" })),
        ...quizFreeTextQuestions.map((payload, index) => ({ kind: "ft" as const, payload, index, prefix: "quiz-ft" })),
      ];
    }
    if (node.type === "practice") {
      return practiceTasks.map((payload, index) => ({ kind: "practice" as const, payload, index, prefix: "practice" }));
    }
    if (node.type === "checkpoint" || node.type === "capstone") {
      return [
        ...quizMcQuestions.map((payload, index) => ({ kind: "mc" as const, payload, index, prefix: "combined-mc" })),
        ...quizFreeTextQuestions.map((payload, index) => ({ kind: "ft" as const, payload, index, prefix: "combined-ft" })),
        ...practiceTasks.map((payload, index) => ({ kind: "practice" as const, payload, index, prefix: "combined-practice" })),
        ...drillQuestions.map((payload, index) => ({ kind: "drill" as const, payload, index, prefix: "combined-drill" })),
      ];
    }
    return [];
  }, [drillQuestions, node, practiceTasks, quizFreeTextQuestions, quizMcQuestions]);
  const showGuidedFooterActions = Boolean(!showInitialGenerationLoader && isGuidedNodeType);
  const guidedStartItems = useMemo(() => {
    if (!node) {
      return [] as string[];
    }
    if (node.type === "quiz") {
      const items: string[] = [];
      if (quizMcQuestions.length > 0) {
        items.push("Quiz questions");
      }
      if (quizFreeTextQuestions.length > 0) {
        items.push("Free-text prompts");
      }
      return items.length > 0 ? items : ["Quiz questions"];
    }
    if (node.type === "practice") {
      const items: string[] = [];
      if (practiceTasks.length > 0) {
        items.push("Practice exercises");
      }
      const hasUploadTasks = practiceTasks.some((task) => asText(task.type).toLowerCase() === "scenario");
      if (hasUploadTasks) {
        items.push("External-solving tasks with file uploads");
      }
      return items.length > 0 ? items : ["Practice exercises"];
    }
    if (node.type === "checkpoint" || node.type === "capstone") {
      return [
        "Quiz questions",
        "Practice exercises",
        "KSA assessment drills",
      ];
    }
    return [];
  }, [drillQuestions.length, node, practiceTasks, quizFreeTextQuestions.length, quizMcQuestions.length]);
  const collectedGuidedResponses = useMemo(() => {
    const mcAnswers: Record<string, unknown> = {};
    const freeTextAnswers: Record<string, string> = {};
    const scenarioAnswers: Record<string, string> = {};
    const deepDiveAnswers: Record<string, { answer: string }> = {};
    const uploadedArtifacts: Array<Record<string, unknown>> = [];

    guidedItems.forEach((item) => {
      if (item.kind === "mc") {
        const questionId = normalizeQuestionId(item.payload.id, "mc", item.index);
        const questionType = asText(item.payload.type, "single").toLowerCase();
        const isMultiple = questionType === "multiple" || questionType === "multi";
        if (isMultiple) {
          const values = multiAnswers[questionId] ?? [];
          if (values.length > 0) {
            mcAnswers[questionId] = values;
          }
          return;
        }
        const value = asText(singleAnswers[questionId]);
        if (value) {
          mcAnswers[questionId] = value;
        }
        return;
      }
      if (item.kind === "ft") {
        const questionId = normalizeQuestionId(item.payload.id, item.prefix, item.index);
        const value = asText(textAnswers[questionId]);
        if (value) {
          freeTextAnswers[questionId] = value;
        }
        return;
      }
      if (item.kind === "practice") {
        const taskId = normalizeQuestionId(item.payload.id, "task", item.index);
        const textValue = asText(textAnswers[taskId]);
        if (textValue) {
          scenarioAnswers[taskId] = textValue;
        }
        const files = uploads[taskId] ?? [];
        files.forEach((file) => {
          uploadedArtifacts.push({
            task_id: taskId,
            file_name: file.name,
            content: file.name,
          });
        });
        return;
      }
      if (item.kind === "drill") {
        const questionId = normalizeQuestionId(item.payload.id, "drill", item.index);
        const answer = asText(singleAnswers[questionId]) || asText(textAnswers[questionId]);
        if (answer) {
          deepDiveAnswers[questionId] = { answer };
        }
      }
    });

    return {
      mc_answers: mcAnswers,
      free_text_answers: freeTextAnswers,
      scenario_answers: scenarioAnswers,
      deep_dive_answers: deepDiveAnswers,
      uploaded_artifacts: uploadedArtifacts,
    };
  }, [guidedItems, multiAnswers, singleAnswers, textAnswers, uploads]);
  const guidedResult = asRecord(attempt?.result);
  const guidedOverallScore = Number(guidedResult.overall_score ?? 0);
  const guidedPassedByThreshold = Number.isFinite(guidedOverallScore) && guidedOverallScore >= 0.6;
  const guidedCompletionLabel = node?.type === "capstone" ? "Course" : "Checkpoint";
  const guidedResultRows = useMemo(() => {
    const mcScore = Number(asRecord(guidedResult.mc_evaluation).score);
    const freeScore = Number(asRecord(guidedResult.free_text_quiz_evaluation).score || asRecord(guidedResult.free_text_evaluation).score);
    const practiceScore = Number(
      asRecord(guidedResult.scenario_practice_evaluation).score
      || asRecord(guidedResult.scenario_evaluation).score
      || asRecord(guidedResult.upload_evaluation).score,
    );
    const drillScore = Number(asRecord(guidedResult.drill_evaluation).score || guidedResult.deep_dive_score);
    const quizComponents = [mcScore, freeScore].filter((value) => Number.isFinite(value) && value >= 0);
    const quizScore = quizComponents.length > 0
      ? quizComponents.reduce((sum, value) => sum + value, 0) / quizComponents.length
      : NaN;
    return [
      { label: "Quiz", score: quizScore },
      { label: "Practice", score: practiceScore },
      { label: "KSA drill", score: drillScore },
    ].map((item) => ({
      ...item,
      scoreText: Number.isFinite(item.score) ? `${Math.round(item.score * 100)}%` : "—",
      scoreClass: Number.isFinite(item.score)
        ? item.score >= 0.6
          ? "trend-up"
          : "trend-down"
        : "",
    }));
  }, [guidedResult]);
  const currentGuidedItem = guidedItems[guidedItemIndex] ?? null;
  const isLastGuidedItem = guidedItemIndex >= guidedItems.length - 1;
  const showGuidedProgress = showGuidedFooterActions && guidedStep === "items" && guidedItems.length > 0;
  const guidedProgressPercent = showGuidedProgress
    ? Math.round(((guidedItemIndex + 1) / guidedItems.length) * 100)
    : 0;
  const currentDrillQuestion = drillQuestions[assessmentQuestionIndex] ?? null;
  const isLastAssessmentQuestion = assessmentQuestionIndex >= drillQuestions.length - 1;
  const showAssessmentProgress = showAssessmentFooterActions && assessmentStep === "questions" && drillQuestions.length > 0;
  const assessmentProgressPercent = showAssessmentProgress
    ? Math.round(((assessmentQuestionIndex + 1) / drillQuestions.length) * 100)
    : 0;
  const currentAssessmentQuestionId = currentDrillQuestion ? normalizeQuestionId(currentDrillQuestion.id, "drill", assessmentQuestionIndex) : "";
  const currentAssessmentHasAnswer = Boolean(
    asText(singleAnswers[currentAssessmentQuestionId]) || asText(textAnswers[currentAssessmentQuestionId]),
  );
  const collectedAssessmentAnswers = useMemo(() => {
    const answerMap: Record<string, unknown> = {};
    drillQuestions.forEach((question, index) => {
      const questionId = normalizeQuestionId(question.id, "drill", index);
      const singleChoice = asText(singleAnswers[questionId]);
      const textValue = asText(textAnswers[questionId]);
      const answer = singleChoice || textValue;
      if (!answer) {
        return;
      }
      answerMap[questionId] = { answer };
    });
    return answerMap;
  }, [drillQuestions, singleAnswers, textAnswers]);
  const assessmentResult = asRecord(attempt?.result);
  const assessmentDrillResult = asRecord(assessmentResult.drill_result);
  const topicUpdates = asRecord(assessmentDrillResult.topic_updates);
  const assessmentRoundRows = useMemo(() => {
    const roundIndexes = assessmentRounds.length > 0
      ? assessmentRounds.map((round) => Number(round.round_number || 0)).filter((value) => Number.isFinite(value) && value > 0)
      : Array.from(new Set(drillQuestions.map((question) => Number(question.block_index || 0)).filter((value) => Number.isFinite(value) && value > 0))).sort((a, b) => a - b);
    const deltaByRound = new Map<number, number>();
    Object.values(topicUpdates).forEach((item) => {
      const updateRecord = asRecord(item);
      asArray(updateRecord.blocks).forEach((block) => {
        const blockRecord = asRecord(block);
        const roundNumber = Number(blockRecord.block_index || 0);
        if (!Number.isFinite(roundNumber) || roundNumber <= 0) {
          return;
        }
        const q1Pass = Boolean(blockRecord.q1_pass);
        const q2Pass = Boolean(blockRecord.q2_pass);
        const blockDelta = q1Pass && q2Pass ? 0.2 : !q1Pass ? -0.1 : 0;
        deltaByRound.set(roundNumber, (deltaByRound.get(roundNumber) ?? 0) + blockDelta);
      });
    });
    return roundIndexes.map((roundNumber) => {
      const round = assessmentRounds.find((item) => Number(item.round_number || 0) === roundNumber);
      const questions = drillQuestions.filter((question) => Number(question.block_index || 0) === roundNumber);
      return {
        title: asText(round?.detailed_topic || questions[0]?.topic_name, `Round ${roundNumber}`),
        ksa: formatKsaTag(round || questions[0] || {}),
        delta: Number((deltaByRound.get(roundNumber) ?? 0).toFixed(3)),
      };
    });
  }, [assessmentRounds, drillQuestions, topicUpdates]);

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
              {assessmentStep === "topics" ? (
                <>
                  <h3>Generated Assessment Topics</h3>
                  <div className="ksa-drill-topic-grid">
                    {assessmentTopicCards.map((topic, index) => (
                      <article key={`topic-${index}`} className="ksa-drill-topic-card">
                        <strong>{topic.label}</strong>
                        <small>{formatKsaTag(topic.ksaSource)}</small>
                      </article>
                    ))}
                  </div>
                  {assessmentTopicCards.length === 0 ? (
                    <div className="learning-node-page-placeholder">
                      No generated assessment topics are available yet.
                    </div>
                  ) : null}
                </>
              ) : null}
              {assessmentStep === "questions" ? (
                <>
                  <div className="learning-node-stack">
                    {currentDrillQuestion ? (
                      <DrillQuestion
                        key={`${asText(currentDrillQuestion.id, `drill-${assessmentQuestionIndex}`)}-${assessmentQuestionIndex}`}
                        question={currentDrillQuestion}
                        index={assessmentQuestionIndex}
                        singleAnswers={singleAnswers}
                        setSingleAnswers={setSingleAnswers}
                        textAnswers={textAnswers}
                        setTextAnswers={setTextAnswers}
                        showMeta={false}
                      />
                    ) : (
                      <div className="learning-node-page-placeholder">
                        No assessment questions are available for this node yet.
                      </div>
                    )}
                  </div>
                </>
              ) : null}
              {assessmentStep === "complete" ? (
                <section className="learning-node-section">
                  <h3>Assessment Hook Results</h3>
                  {assessmentRoundRows.length > 0 ? (
                    <div className="learning-node-milestone-topic-table learning-node-assessment-results-table">
                      <div className="learning-node-milestone-topic-head">
                        <span>Topic</span>
                        <span>KSA</span>
                        <span>Delta</span>
                      </div>
                      <div className="learning-node-milestone-topic-body">
                        {assessmentRoundRows.map((row, index) => (
                          <div key={`assessment-round-${index}`} className="learning-node-milestone-topic-line">
                            <span>{row.title}</span>
                            <small>{row.ksa}</small>
                            <span className={row.delta > 0 ? "trend-up" : row.delta < 0 ? "trend-down" : ""}>
                              {row.delta > 0 ? "+" : ""}
                              {row.delta.toFixed(2)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="learning-node-page-placeholder">
                      No assessment round results are available yet.
                    </div>
                  )}
                </section>
              ) : null}
            </section>
          ) : null}

          {!showInitialGenerationLoader && isGuidedNodeType ? (
            <section className="learning-node-section">
              {guidedStep === "start" ? (
                <div className="learning-node-guided-start">
                  <div className="learning-node-guided-start-icon">
                    <Icon name={nodeTypeIconName(node?.type)} />
                  </div>
                  <strong>Ready to start</strong>
                  <small>This learning node will guide you through:</small>
                  <ul className="learning-node-guided-start-list">
                    {guidedStartItems.map((item, index) => (
                      <li key={`guided-start-${index}`}>
                        <Icon name="check" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {guidedStep === "items" ? (
                <div className="learning-node-stack">
                  {currentGuidedItem?.kind === "mc" ? (
                    <MultipleChoiceQuestion
                      key={`${normalizeQuestionId(currentGuidedItem.payload.id, currentGuidedItem.prefix, currentGuidedItem.index)}-${guidedItemIndex}`}
                      question={currentGuidedItem.payload}
                      index={currentGuidedItem.index}
                      singleAnswers={singleAnswers}
                      multiAnswers={multiAnswers}
                      setSingleAnswers={setSingleAnswers}
                      setMultiAnswers={setMultiAnswers}
                    />
                  ) : null}
                  {currentGuidedItem?.kind === "ft" ? (
                    <FreeTextQuestion
                      key={`${normalizeQuestionId(currentGuidedItem.payload.id, currentGuidedItem.prefix, currentGuidedItem.index)}-${guidedItemIndex}`}
                      question={currentGuidedItem.payload}
                      index={currentGuidedItem.index}
                      answers={textAnswers}
                      setAnswers={setTextAnswers}
                      answerKeyPrefix={currentGuidedItem.prefix}
                    />
                  ) : null}
                  {currentGuidedItem?.kind === "practice" ? (
                    <PracticeTask
                      key={`${normalizeQuestionId(currentGuidedItem.payload.id, currentGuidedItem.prefix, currentGuidedItem.index)}-${guidedItemIndex}`}
                      task={currentGuidedItem.payload}
                      index={currentGuidedItem.index}
                      textAnswers={textAnswers}
                      setTextAnswers={setTextAnswers}
                      uploads={uploads}
                      setUploads={setUploads}
                    />
                  ) : null}
                  {currentGuidedItem?.kind === "drill" ? (
                    <DrillQuestion
                      key={`${asText(currentGuidedItem.payload.id, `${currentGuidedItem.prefix}-${currentGuidedItem.index}`)}-${guidedItemIndex}`}
                      question={currentGuidedItem.payload}
                      index={currentGuidedItem.index}
                      singleAnswers={singleAnswers}
                      setSingleAnswers={setSingleAnswers}
                      textAnswers={textAnswers}
                      setTextAnswers={setTextAnswers}
                      showMeta={false}
                    />
                  ) : null}
                  {!currentGuidedItem ? (
                    <div className="learning-node-page-placeholder">
                      No content steps are available for this node yet.
                    </div>
                  ) : null}
                </div>
              ) : null}
              {guidedStep === "complete" ? (
                <section className="learning-node-section">
                  <div className="learning-node-guided-result-hero">
                    <div className={`learning-node-guided-result-badge ${guidedPassedByThreshold ? "success" : "failed"}`}>
                      <Icon name={guidedPassedByThreshold ? "certificate" : "ban"} />
                      <strong>{guidedPassedByThreshold ? `${guidedCompletionLabel} completed` : `${guidedCompletionLabel} not completed`}</strong>
                    </div>
                  </div>
                  {guidedResultRows.length > 0 ? (
                    <div className="learning-node-milestone-topic-table learning-node-guided-results-table">
                      <div className="learning-node-milestone-topic-head">
                        <span>Section</span>
                        <span>Result</span>
                      </div>
                      <div className="learning-node-milestone-topic-body">
                        {guidedResultRows.map((row, index) => {
                          return (
                            <div key={`guided-result-${index}`} className="learning-node-milestone-topic-line">
                              <span>{row.label}</span>
                              <span className={row.scoreClass}>{row.scoreText}</span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ) : (
                    <div className="learning-node-page-placeholder">
                      No result metrics are available yet.
                    </div>
                  )}
                </section>
              ) : null}
            </section>
          ) : null}

          {!showInitialGenerationLoader && node && !["unlock_gate", "milestone", "assessment_hook", "quiz", "practice", "checkpoint", "capstone"].includes(node.type) ? (
            <div className="learning-node-page-placeholder">
              Node type <strong>{node.type}</strong> is intentionally not rendered in this step.
            </div>
          ) : null}
        </div>
      ) : null}

      {showAssessmentProgress || showGuidedProgress ? (
        <div className="learning-node-progress-floating" aria-label="Assessment progress">
          <div
            className="learning-node-progress-track"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={showAssessmentProgress ? assessmentProgressPercent : guidedProgressPercent}
          >
            <div className="learning-node-progress-fill" style={{ width: `${showAssessmentProgress ? assessmentProgressPercent : guidedProgressPercent}%` }} />
          </div>
          <small>
            {showAssessmentProgress
              ? `${assessmentQuestionIndex + 1} / ${drillQuestions.length}`
              : `${guidedItemIndex + 1} / ${guidedItems.length}`}
          </small>
        </div>
      ) : null}

      {showMilestoneFooterActions || showAssessmentFooterActions || showGuidedFooterActions ? (
        <div className="learning-node-fixed-footer">
          <div className="learning-node-fixed-footer-inner">
            <div className="learning-node-footer-actions">
              {showMilestoneFooterActions ? (
                <>
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
                </>
              ) : null}
              {showAssessmentFooterActions ? (
                <button
                  className="primary-button"
                  type="button"
                  disabled={
                    assessmentFinishing
                    || assessmentRestarting
                    || (assessmentStep === "questions" && !currentAssessmentHasAnswer)
                  }
                  onClick={() => {
                    if (assessmentStep === "complete") {
                      void onAssessmentRestart?.();
                      return;
                    }
                    if (assessmentStep === "topics") {
                      void (async () => {
                        try {
                          await onAssessmentStart?.();
                        } catch {
                          // Error banner is handled at route level.
                        }
                        if (drillQuestions.length > 0) {
                          setAssessmentStep("questions");
                          setAssessmentQuestionIndex(0);
                        } else {
                          setAssessmentStep("complete");
                        }
                      })();
                      return;
                    }
                    if (assessmentStep === "questions") {
                      if (isLastAssessmentQuestion) {
                        void (async () => {
                          try {
                            if (onAssessmentComplete) {
                              await onAssessmentComplete({ answers: collectedAssessmentAnswers });
                            }
                            setAssessmentStep("complete");
                          } catch {
                            // Error banner is handled at route level.
                          }
                        })();
                        return;
                      }
                      setAssessmentQuestionIndex((value) => value + 1);
                    }
                  }}
                >
                  {assessmentFinishing
                    ? "Finishing..."
                    : assessmentRestarting
                      ? "Restarting..."
                    : assessmentStep === "topics"
                      ? "Start"
                      : assessmentStep === "questions"
                        ? (isLastAssessmentQuestion ? "Finish" : "Next")
                        : "Restart"}
                </button>
              ) : null}
              {showGuidedFooterActions ? (
                <>
                  {guidedStep === "complete" && guidedPassedByThreshold && node?.type === "capstone" ? (
                    <button className="secondary-button" type="button" disabled>
                      <Icon name="download" />
                      Download Certificate
                    </button>
                  ) : null}
                  <button
                    className="primary-button"
                    type="button"
                    disabled={guidedCompleting || guidedRestarting}
                    onClick={() => {
                      if (guidedStep === "complete") {
                        if (guidedPassedByThreshold) {
                          return;
                        }
                        void (async () => {
                          try {
                            await onGuidedRestart?.();
                            setGuidedStep("start");
                            setGuidedItemIndex(0);
                          } catch {
                            // Error banner is handled at route level.
                          }
                        })();
                        return;
                      }
                      if (guidedStep === "start") {
                        void (async () => {
                          try {
                            await onAssessmentStart?.();
                          } catch {
                            // Error banner is handled at route level.
                          }
                          if (guidedItems.length > 0) {
                            setGuidedStep("items");
                            setGuidedItemIndex(0);
                          } else {
                            setGuidedStep("complete");
                          }
                        })();
                        return;
                      }
                      if (guidedStep === "items") {
                        if (isLastGuidedItem) {
                          void (async () => {
                            try {
                              await onGuidedComplete?.(collectedGuidedResponses);
                              setGuidedStep("complete");
                            } catch {
                              // Error banner is handled at route level.
                            }
                          })();
                          return;
                        }
                        setGuidedItemIndex((value) => value + 1);
                      }
                    }}
                  >
                    {guidedCompleting
                      ? "Finishing..."
                      : guidedRestarting
                        ? "Restarting..."
                      : guidedStep === "start"
                        ? "Start"
                      : guidedStep === "items"
                        ? (isLastGuidedItem ? "Finish" : "Next")
                        : guidedPassedByThreshold
                          ? "Finish"
                          : "Restart"}
                  </button>
                </>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
