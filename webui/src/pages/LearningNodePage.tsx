import { useEffect, useMemo, useRef, useState, type Dispatch, type SetStateAction } from "react";
import { Icon } from "../components/common/Icons";
import { SourcesPanel } from "../components/sources/SourcesPanel";
import type { LearningNodeExecutionAttempt, LearningNodeSession, LearningPath, SkilltreeNode, Source } from "../types/chat";

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
  onLessonComplete?: (responses: Record<string, unknown>) => Promise<void>;
  lessonCompleting?: boolean;
  onLessonClose?: () => Promise<void> | void;
  lessonClosing?: boolean;
};

type AnswerMap = Record<string, string>;
type MultiAnswerMap = Record<string, string[]>;
type UploadMap = Record<string, File[]>;
type GuidedContentStep = "start" | "items" | "complete";
type LessonFlowStep = {
  id: string;
  title: string;
  summary: string;
  goal: string;
  topics: string[];
  mediaKind: "none" | "image" | "video";
  videoDescription?: string;
  downloadFiles: DownloadableFile[];
  imageUrl?: string;
  videoUrl?: string;
};
type DownloadableFile = {
  fileName: string;
  ext: string;
  tone: "is-red" | "is-blue" | "is-purple" | "is-gray" | "is-green";
  sizeLabel: string;
  href: string;
};

const DUMMY_DEVOPS_IMAGE = "data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1200' height='640' viewBox='0 0 1200 640'%3E%3Cdefs%3E%3ClinearGradient id='bg' x1='0%25' y1='0%25' x2='100%25' y2='100%25'%3E%3Cstop offset='0%25' stop-color='%23fff7ed'/%3E%3Cstop offset='100%25' stop-color='%23ffedd5'/%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width='1200' height='640' fill='url(%23bg)'/%3E%3Cg fill='none' stroke='%23f97316' stroke-width='5'%3E%3Crect x='110' y='135' width='980' height='370' rx='24'/%3E%3Cpath d='M180 428 C 290 300, 430 345, 520 270 C 645 160, 785 180, 915 105' stroke-linecap='round'/%3E%3C/g%3E%3Ccircle cx='915' cy='105' r='17' fill='%23f97316'/%3E%3Ctext x='180' y='215' font-family='Arial, sans-serif' font-size='46' fill='%230f172a' font-weight='700'%3EDevOps Learning Unit Preview%3C/text%3E%3Ctext x='180' y='270' font-family='Arial, sans-serif' font-size='30' fill='%23334155'%3EConcept map placeholder for runtime media rendering%3C/text%3E%3C/svg%3E";
const DUMMY_VIDEO_URL = "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4";

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

function attachmentTone(fileName: string): "is-red" | "is-blue" | "is-purple" | "is-gray" | "is-green" {
  const normalized = fileName.toLowerCase();
  if (normalized.endsWith(".pdf")) return "is-red";
  if (normalized.endsWith(".html") || normalized.endsWith(".htm")) return "is-blue";
  if (normalized.endsWith(".epub")) return "is-purple";
  if (normalized.endsWith(".md") || normalized.endsWith(".txt")) return "is-gray";
  return "is-green";
}

function fileExtension(fileName: string): string {
  const ext = fileName.split(".").pop()?.trim().toUpperCase();
  return ext || "FILE";
}

function toDataHref(fileName: string, content: string): string {
  return `data:text/plain;charset=utf-8,${encodeURIComponent(`# ${fileName}\n\n${content}\n`)}`;
}

function normalizeDownloadableFiles(
  source: Record<string, unknown>,
  fallbackPrefix: string,
  fallbackContent: string,
  includeFallback = false,
  assetCatalog?: Record<string, Record<string, unknown>>,
): DownloadableFile[] {
  const keys = [
    "download_files",
    "files",
    "attachments",
    "resources",
    "supporting_files",
    "step_files",
    "reference_files",
    "materials",
  ];
  const raw = keys.flatMap((key) => asArray(source[key]));
  const assetRefs = asRecord(source.asset_refs);
  const rawAssetDownloads = [
    ...asArray(assetRefs.downloads),
    ...asArray(source.download_assets),
  ];
  const fromAssets = rawAssetDownloads
    .map((entry) => asRecord(entry))
    .map((record) => {
      const assetId = asText(record.asset_id);
      const catalogEntry = assetCatalog ? asRecord(assetCatalog[assetId]) : {};
      const fileName = asText(
        record.file_name || record.filename || catalogEntry.file_name || catalogEntry.filename,
        "",
      );
      if (!assetId || !fileName) {
        return null;
      }
      const href = asText(record.url || record.download_url || catalogEntry.url || catalogEntry.download_url);
      if (!href) {
        return null;
      }
      return {
        fileName,
        href,
        sizeLabel: asText(catalogEntry.size_label || record.size_label || catalogEntry.size_bytes || record.size_bytes, "File"),
      };
    })
    .filter(Boolean) as Array<{ fileName: string; href: string; sizeLabel: string }>;
  const mapped = raw
    .map((entry, index) => {
      if (typeof entry === "string") {
        const fileName = entry.includes(".") ? entry : `${entry}.md`;
        return {
          fileName,
          href: toDataHref(fileName, fallbackContent),
          sizeLabel: "Template",
        };
      }
      const record = asRecord(entry);
      const fileName = asText(
        record.file_name || record.filename || record.name || record.title || record.label,
        `${fallbackPrefix}-${index + 1}.md`,
      );
      const href = asText(record.download_url || record.url || record.href || record.path || record.file_path);
      const rawSize = record.size_label ?? record.size ?? record.bytes;
      const sizeLabel = typeof rawSize === "number"
        ? `${Math.max(1, Math.round(rawSize / 1024))} KB`
        : asText(rawSize, "Template");
      return {
        fileName,
        href: href || toDataHref(fileName, fallbackContent),
        sizeLabel,
      };
    })
    .filter((item) => item.fileName);

  const merged = [...fromAssets, ...mapped];
  const withFallback = merged.length > 0
    ? merged
    : includeFallback
      ? [
        {
          fileName: `${fallbackPrefix}.md`,
          href: toDataHref(`${fallbackPrefix}.md`, fallbackContent),
          sizeLabel: "Template",
        },
      ]
      : [];

  return withFallback.slice(0, 4).map((item) => ({
    ...item,
    ext: fileExtension(item.fileName),
    tone: attachmentTone(item.fileName),
  }));
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

function nodeTypeHeaderIconName(typeValue: unknown): "play" | "check" | "archive" | "academic-hat" | "book" | "certificate" {
  return nodeTypeIconName(typeValue);
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

function detectMediaKind(step: Record<string, unknown>, index: number, nodeType: string, courseTitle: string): "none" | "image" | "video" {
  const hints = asArray(step.style_hints).map((item) => asText(item).toLowerCase());
  const textBlob = `${asText(step.title)} ${asText(step.mini_topic_title)} ${asText(step.brief)} ${asText(step.intro_brief)} ${asText(step.teaching_brief)}`.toLowerCase();
  if (nodeType === "review") {
    if (hints.some((hint) => hint.includes("image")) || textBlob.includes("diagram") || textBlob.includes("graphic") || index === 0) {
      return "image";
    }
    return "none";
  }
  if (nodeType === "learning_unit" && (textBlob.includes("linux fundamentals") || textBlob.includes("linux filesystem") || textBlob.includes("linux")) && index === 1) {
    return "video";
  }
  if (hints.some((hint) => hint.includes("video")) || textBlob.includes("video")) {
    return "video";
  }
  if (hints.some((hint) => hint.includes("image")) || textBlob.includes("diagram") || textBlob.includes("graphic")) {
    return "image";
  }
  if (nodeType === "review" && index === 0) {
    return "video";
  }
  if (courseTitle.toLowerCase().includes("devops roadmap") && index === 0) {
    return "image";
  }
  return "none";
}

function dummyLessonSources(learningPath: LearningPath | null, sourceNodeIds: string[]): Source[] {
  return sourceNodeIds.slice(0, 8).map((nodeId, index) => {
    const nodeTitle = learningPath?.nodes.find((item) => item.id === nodeId)?.title ?? nodeId;
    return {
      chunk_id: `node-${nodeId}-${index + 1}`,
      file_name: `${nodeTitle}.md`,
      file_path: `/courses/${learningPath?.id ?? "course"}/nodes/${nodeId}`,
      title: nodeTitle,
      chapter: null,
      section: `Runtime package excerpt ${index + 1}`,
      page_number: null,
      score: Number(Math.max(0.65, 0.98 - index * 0.05).toFixed(3)),
      tags: ["learning-node", "runtime-package"],
    };
  });
}

function MultipleChoiceQuestion({
  question,
  index,
  singleAnswers,
  multiAnswers,
  setSingleAnswers,
  setMultiAnswers,
  assetCatalog,
  showHeading = true,
}: {
  question: Record<string, unknown>;
  index: number;
  singleAnswers: AnswerMap;
  multiAnswers: MultiAnswerMap;
  setSingleAnswers: Dispatch<SetStateAction<AnswerMap>>;
  setMultiAnswers: Dispatch<SetStateAction<MultiAnswerMap>>;
  assetCatalog?: Record<string, Record<string, unknown>>;
  showHeading?: boolean;
}) {
  const questionId = normalizeQuestionId(question.id, "mc", index);
  const questionType = asText(question.type, "single").toLowerCase();
  const isMultiple = questionType === "multiple" || questionType === "multi";
  const options = asArray(question.options).map((item) => asText(item)).filter(Boolean);
  const downloadFiles = useMemo(
    () => normalizeDownloadableFiles(question, `question-${index + 1}-resources`, "Reference files for this question step.", false, assetCatalog),
    [assetCatalog, index, question],
  );

  return (
    <article className="ksa-question-card learning-node-question-card">
      {showHeading ? <h4>Question {index + 1}</h4> : null}
      <p>{asText(question.question, "Question prompt missing.")}</p>
      <DownloadableFiles files={downloadFiles} />
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
  uploads,
  setUploads,
  assetCatalog,
  showHeading = true,
}: {
  question: Record<string, unknown>;
  index: number;
  answers: AnswerMap;
  setAnswers: Dispatch<SetStateAction<AnswerMap>>;
  answerKeyPrefix: string;
  uploads: UploadMap;
  setUploads: Dispatch<SetStateAction<UploadMap>>;
  assetCatalog?: Record<string, Record<string, unknown>>;
  showHeading?: boolean;
}) {
  const questionId = normalizeQuestionId(question.id, answerKeyPrefix, index);
  const uploadFiles = uploads[questionId] ?? [];
  const downloadFiles = useMemo(
    () => normalizeDownloadableFiles(question, `prompt-${index + 1}-resources`, "Starter reference files for this prompt.", false, assetCatalog),
    [assetCatalog, index, question],
  );

  return (
    <article className="ksa-question-card learning-node-question-card">
      {showHeading ? <h4>Prompt {index + 1}</h4> : null}
      <p>{asText(question.question || question.prompt, "Prompt missing.")}</p>
      <DownloadableFiles files={downloadFiles} />
      <div className="learning-node-practice-split">
        <textarea
          className="dialog-input diagnostic-textarea"
          rows={6}
          placeholder="Write your answer here..."
          value={answers[questionId] ?? ""}
          onChange={(event) => setAnswers((current) => ({ ...current, [questionId]: event.target.value }))}
        />
        <UploadPanel
          uploadKey={questionId}
          uploads={uploadFiles}
          setUploads={setUploads}
          helperText="Upload optional files (parts or full solution)."
        />
      </div>
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
  assetCatalog,
}: {
  task: Record<string, unknown>;
  index: number;
  textAnswers: AnswerMap;
  setTextAnswers: Dispatch<SetStateAction<AnswerMap>>;
  uploads: UploadMap;
  setUploads: Dispatch<SetStateAction<UploadMap>>;
  assetCatalog?: Record<string, Record<string, unknown>>;
}) {
  const taskId = normalizeQuestionId(task.id, "task", index);
  const uploadFiles = uploads[taskId] ?? [];
  const downloadFiles = useMemo(
    () => normalizeDownloadableFiles(task, `practice-${index + 1}-resources`, "Practice materials and starter assets.", false, assetCatalog),
    [assetCatalog, index, task],
  );

  return (
    <article className="ksa-question-card learning-node-question-card">
      <h4>{asText(task.title, `Practice Task ${index + 1}`)}</h4>
      <p>{asText(task.prompt, "Task prompt missing.")}</p>
      <DownloadableFiles files={downloadFiles} />
      <div className="learning-node-practice-split">
        <textarea
          className="dialog-input diagnostic-textarea"
          rows={6}
          placeholder="Describe your approach, notes, and solution summary..."
          value={textAnswers[taskId] ?? ""}
          onChange={(event) => setTextAnswers((current) => ({ ...current, [taskId]: event.target.value }))}
        />
        <UploadPanel
          uploadKey={taskId}
          uploads={uploadFiles}
          setUploads={setUploads}
          helperText="Upload optional artifacts for this exercise."
        />
      </div>
    </article>
  );
}

function UploadPanel({
  uploadKey,
  uploads,
  setUploads,
  helperText,
}: {
  uploadKey: string;
  uploads: File[];
  setUploads: Dispatch<SetStateAction<UploadMap>>;
  helperText: string;
}) {
  return (
    <div className="learning-node-upload-box">
      <label className="learning-node-upload-dropzone">
        <Icon name="arrow-up" />
        <strong>Click to upload or drag and drop</strong>
        <small>{helperText}</small>
        <input
          type="file"
          multiple
          onChange={(event) => {
            const selected = Array.from(event.target.files ?? []);
            if (selected.length === 0) {
              return;
            }
            setUploads((current) => ({ ...current, [uploadKey]: [...(current[uploadKey] ?? []), ...selected] }));
          }}
        />
      </label>
      <div className="composer-attachment-chip-list">
        {uploads.length === 0 ? <small>No files selected yet.</small> : null}
        {uploads.map((file, index) => (
          <div key={`${uploadKey}-${file.name}-${file.size}-${index}`} className="composer-attachment-chip learning-node-upload-file-row">
            <span className={`library-extension-chip ${attachmentTone(file.name)}`}>{fileExtension(file.name)}</span>
            <span className="composer-attachment-meta">
              <span className="composer-attachment-name">{file.name}</span>
              <span className="composer-attachment-ext">{`${Math.max(1, Math.round(file.size / 1024))} KB`}</span>
            </span>
            <button
              className="composer-attachment-remove"
              type="button"
              aria-label={`Remove ${file.name}`}
              onClick={() => {
                setUploads((current) => ({
                  ...current,
                  [uploadKey]: (current[uploadKey] ?? []).filter((_, i) => i !== index),
                }));
              }}
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

function DownloadableFiles({ files }: { files: DownloadableFile[] }) {
  if (files.length === 0) {
    return null;
  }
  return (
    <div className="learning-node-download-files">
      {files.map((file, index) => (
        <a
          key={`${file.fileName}-${index}`}
          className="learning-node-download-chip"
          href={file.href}
          download={file.fileName}
          target={file.href.startsWith("data:") ? undefined : "_blank"}
          rel={file.href.startsWith("data:") ? undefined : "noreferrer"}
        >
          <span className={`library-extension-chip ${file.tone}`}>{file.ext}</span>
          <span className="learning-node-download-meta">
            <strong>{file.fileName}</strong>
            <small>{file.sizeLabel}</small>
          </span>
          <Icon name="download" />
        </a>
      ))}
    </div>
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
  onLessonComplete,
  lessonCompleting = false,
  onLessonClose,
  lessonClosing = false,
}: LearningNodePageProps) {
  const [singleAnswers, setSingleAnswers] = useState<AnswerMap>({});
  const [multiAnswers, setMultiAnswers] = useState<MultiAnswerMap>({});
  const [textAnswers, setTextAnswers] = useState<AnswerMap>({});
  const [uploads, setUploads] = useState<UploadMap>({});
  const [assessmentStep, setAssessmentStep] = useState<"topics" | "questions" | "complete">("topics");
  const [assessmentQuestionIndex, setAssessmentQuestionIndex] = useState(0);
  const [guidedStep, setGuidedStep] = useState<GuidedContentStep>("start");
  const [guidedItemIndex, setGuidedItemIndex] = useState(0);
  const [lessonFlowStepIndex, setLessonFlowStepIndex] = useState(0);
  const [lessonSourcesOpen, setLessonSourcesOpen] = useState(false);
  const [lessonTranscriptOpen, setLessonTranscriptOpen] = useState(false);
  const [lessonVideoHeight, setLessonVideoHeight] = useState<number>(0);
  const [lessonCompleted, setLessonCompleted] = useState(false);
  const lessonVideoWrapRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setSingleAnswers({});
    setMultiAnswers({});
    setTextAnswers({});
    setUploads({});
    setAssessmentStep("topics");
    setAssessmentQuestionIndex(0);
    setGuidedStep("start");
    setGuidedItemIndex(0);
    setLessonSourcesOpen(false);
    setLessonTranscriptOpen(false);
    setLessonVideoHeight(0);
    setLessonFlowStepIndex(0);
    setLessonCompleted(false);
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
  const assetCatalog = asRecord(packageData.asset_catalog);
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
  const isLessonNodeType = Boolean(node && (node.type === "learning_unit" || node.type === "review"));
  const lessonSteps = useMemo(() => {
    if (!node || !attempt) {
      return [] as LessonFlowStep[];
    }
    const courseTitle = asText(learningPath?.title);
    if (node.type === "learning_unit") {
      return asArray(packageData.mini_topic_lessons).map((item, index) => {
        const step = asRecord(item);
        const refs = asRecord(step.asset_refs);
        const imageAsset = asRecord(asArray(refs.images)[0]);
        const videoAsset = asRecord(asArray(refs.videos)[0]);
        const imageUrl = asText(asRecord(assetCatalog[asText(imageAsset.asset_id)]).url);
        const videoUrl = asText(asRecord(assetCatalog[asText(videoAsset.asset_id)]).url);
        const explicitMediaKind: "none" | "image" | "video" = videoUrl ? "video" : imageUrl ? "image" : "none";
        return {
          id: asText(step.step_id, `lesson-${index + 1}`),
          title: asText(step.mini_topic_title || step.title, `Mini lesson ${index + 1}`),
          summary: asText(step.intro_brief || step.teaching_brief, "This lesson introduces a focused concept for this learning node."),
          goal: asText(step.lesson_goal, "Understand and apply the mini topic in practical context."),
          topics: asArray(step.expected_difficulty_points).map((value) => asText(value)).filter(Boolean).slice(0, 4),
          mediaKind: explicitMediaKind !== "none" ? explicitMediaKind : detectMediaKind(step, index, node.type, courseTitle),
          videoDescription: "Watch this short clip before continuing to the next step.",
          downloadFiles: normalizeDownloadableFiles(
            step,
            `lesson-step-${index + 1}-resources`,
            `Learning unit support files for step "${asText(step.mini_topic_title || step.title, `Step ${index + 1}`)}".`,
            false,
            assetCatalog as Record<string, Record<string, unknown>>,
          ),
          imageUrl,
          videoUrl,
        };
      });
    }
    if (node.type === "review") {
      const recap = asRecord(packageData.recap_structure);
      const miniRecaps = asArray(recap.mini_recaps).length > 0
        ? asArray(recap.mini_recaps)
        : asArray(packageData.mini_topic_lessons);
      return miniRecaps.map((item, index) => {
        const step = asRecord(item);
        const refs = asRecord(step.asset_refs);
        const imageAsset = asRecord(asArray(refs.images)[0]);
        const videoAsset = asRecord(asArray(refs.videos)[0]);
        const imageUrl = asText(asRecord(assetCatalog[asText(imageAsset.asset_id)]).url);
        const videoUrl = asText(asRecord(assetCatalog[asText(videoAsset.asset_id)]).url);
        const explicitMediaKind: "none" | "image" | "video" = videoUrl ? "video" : imageUrl ? "image" : "none";
        return {
          id: asText(step.step_id, `recap-${index + 1}`),
          title: asText(step.title || step.mini_topic_title, `Review step ${index + 1}`),
          summary: asText(step.brief || step.intro_brief, "This review step reinforces important concepts from previous nodes."),
          goal: asText(step.goal || step.lesson_goal, "Consolidate understanding and prepare for upcoming checkpoints."),
          topics: asArray(step.focus_topics).map((value) => asText(value)).filter(Boolean).slice(0, 4),
          mediaKind: explicitMediaKind !== "none" ? explicitMediaKind : detectMediaKind(step, index, node.type, courseTitle),
          videoDescription: "Recap video: review this short summary before moving on.",
          downloadFiles: normalizeDownloadableFiles(
            step,
            `review-step-${index + 1}-resources`,
            `Review support files for step "${asText(step.title || step.mini_topic_title, `Review ${index + 1}`)}".`,
            false,
            assetCatalog as Record<string, Record<string, unknown>>,
          ),
          imageUrl,
          videoUrl,
        };
      });
    }
    return [] as LessonFlowStep[];
  }, [assetCatalog, attempt, learningPath?.title, node, packageData.mini_topic_lessons, packageData.recap_structure]);
  const lessonStartTopics = useMemo(() => {
    return (asArray(packageData.important_topics).map((item) => asText(item)).filter(Boolean).slice(0, 8));
  }, [packageData.important_topics]);
  const lessonSources = useMemo(
    () => dummyLessonSources(learningPath, asArray(attempt?.source_node_window).map((item) => asText(item)).filter(Boolean)),
    [attempt?.source_node_window, learningPath],
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
        const files = uploads[questionId] ?? [];
        files.forEach((file) => {
          uploadedArtifacts.push({
            task_id: questionId,
            file_name: file.name,
            content: file.name,
          });
        });
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
  const lessonFlowTotalSteps = lessonSteps.length + 2;
  const boundedLessonStep = Math.min(Math.max(lessonFlowStepIndex, 0), Math.max(lessonFlowTotalSteps - 1, 0));
  const lessonCurrentStep = lessonSteps[Math.max(0, Math.min(lessonSteps.length - 1, boundedLessonStep - 1))] ?? null;
  const isLessonStartStep = boundedLessonStep === 0;
  const isLessonResultStep = boundedLessonStep === lessonFlowTotalSteps - 1;
  const isLessonContentStep = !isLessonStartStep && !isLessonResultStep;
  const isLessonFirstContentStep = boundedLessonStep === 1;
  const isLessonLastContentStep = boundedLessonStep >= lessonSteps.length;
  const showLessonFooterActions = Boolean(!showInitialGenerationLoader && isLessonNodeType);
  const showLessonProgress = showLessonFooterActions && lessonFlowTotalSteps > 1 && !lessonCompleted;
  const showLessonContentActions = Boolean(!showInitialGenerationLoader && isLessonContentStep);
  const lessonProgressPercent = showLessonProgress
    ? Math.round((boundedLessonStep / Math.max(lessonFlowTotalSteps - 1, 1)) * 100)
    : 0;
  const lessonCompletionPayload = useMemo(() => {
    const lessonStepIds = lessonSteps.map((item) => item.id);
    if (node?.type === "review") {
      return {
        phase_progress: {
          phase_1_introduction: true,
          phase_2_grouped_recaps: true,
          phase_3_summary_and_feedback: true,
          ...Object.fromEntries(lessonStepIds.map((stepId) => [stepId, true])),
        },
        node_feedback: {
          text: "Completed review flow in learning node chat.",
          rating: 4,
        },
        questions: [],
      } as Record<string, unknown>;
    }
    return {
      phase_progress: {
        phase_1_introduction: true,
        phase_2_niveau_estimation: true,
        phase_3_user_self_explanation: true,
        phase_4_structure_preview: true,
        phase_5_mini_topic_lessons: true,
        phase_6_node_recap: true,
        ...Object.fromEntries(lessonStepIds.map((stepId) => [stepId, true])),
      },
      niveau_self_positioning: {
        confidence: "intermediate",
      },
      user_high_level_explanation: "Completed all mini-topic steps in this learning node.",
      user_importance_explanation: "The node content connects to practical execution and reinforces the core goals.",
      interaction_feedback: {
        explain_again_used: false,
      },
    } as Record<string, unknown>;
  }, [lessonSteps, node?.type]);
  const lessonBootstrapRef = useRef<string>("");
  useEffect(() => {
    if (!isLessonNodeType) {
      return;
    }
    const bootKey = `${session?.id ?? "none"}:${attempt?.attempt_id ?? "none"}`;
    if (lessonBootstrapRef.current === bootKey) {
      return;
    }
    lessonBootstrapRef.current = bootKey;
    const result = asRecord(attempt?.result);
    const alreadyCompleted = Boolean(attempt?.completed_at)
      || session?.status === "completed"
      || Boolean(result.passed);
    setLessonCompleted(alreadyCompleted);
    setLessonFlowStepIndex(alreadyCompleted ? Math.max(lessonFlowTotalSteps - 1, 0) : 0);
  }, [
    attempt?.attempt_id,
    attempt?.completed_at,
    attempt?.result,
    isLessonNodeType,
    lessonFlowTotalSteps,
    session?.id,
    session?.status,
  ]);
  useEffect(() => {
    const target = lessonVideoWrapRef.current;
    if (!target || typeof ResizeObserver === "undefined") {
      return;
    }
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) {
        return;
      }
      const nextHeight = Math.round(entry.contentRect.height);
      if (nextHeight > 0) {
        setLessonVideoHeight(nextHeight);
      }
    });
    observer.observe(target);
    return () => observer.disconnect();
  }, [boundedLessonStep, lessonTranscriptOpen, lessonCurrentStep?.mediaKind]);
  const showGuidedResultLoading = guidedStep === "complete" && guidedCompleting;
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
        <div className="learning-node-page-heading">
          <span className="learning-node-header-icon-wrap" aria-hidden="true">
            <Icon name={nodeTypeHeaderIconName(node?.type)} className="learning-node-header-icon" />
          </span>
          <div className="learning-node-page-heading-copy">
            <h2>{node?.title ?? session?.node_title ?? "Learning Node"}</h2>
            <p>{asText(node?.description, "This node currently has no description.")}</p>
          </div>
        </div>
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

          {!showInitialGenerationLoader && isLessonNodeType ? (
            <section className="learning-node-section learning-node-lesson-shell">
              {isLessonStartStep ? (
                <div className="learning-node-guided-start learning-node-lesson-start">
                  <div className="learning-node-guided-start-icon">
                    <Icon name={node?.type === "review" ? "archive" : "book"} />
                  </div>
                  <strong>{node?.type === "review" ? "Review flow overview" : "Learning unit overview"}</strong>
                  <small>{node?.type === "review" ? "This node will recap and reinforce your previous progress." : "This node will guide you through mini-topic lessons."}</small>
                  {node?.type !== "review" && lessonStartTopics.length > 0 ? (
                    <div className="learning-node-lesson-meta-block">
                      <h4>Topics</h4>
                      <ul className="learning-node-lesson-plain-list">
                        {lessonStartTopics.map((topic, index) => (
                          <li key={`lesson-topic-${index}`}>{topic}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  {node?.type === "review" ? (
                    <ul className="learning-node-guided-start-list">
                      {lessonStartTopics.length === 0 ? (
                        <li>
                          <span>No generated review topics available yet.</span>
                        </li>
                      ) : (
                        lessonStartTopics.map((topic, index) => (
                          <li key={`review-start-topic-${index}`}>
                            <Icon name="check" />
                            <span>{topic}</span>
                          </li>
                        ))
                      )}
                    </ul>
                  ) : (
                    <div className="learning-node-lesson-meta-block planned">
                      <h4>Planned steps</h4>
                      <ul className="learning-node-lesson-plain-list">
                        {lessonSteps.length === 0 ? (
                          <li>No generated mini-topic lessons available yet.</li>
                        ) : (
                          lessonSteps.map((step, index) => (
                            <li key={step.id}>{`${index + 1}. ${step.title}`}</li>
                          ))
                        )}
                      </ul>
                    </div>
                  )}
                </div>
              ) : null}
              {isLessonContentStep ? (
                <>
                  <article className="learning-node-lesson-content-card">
                    <header className="learning-node-lesson-step-head">
                      <h3>{lessonCurrentStep?.title ?? "Lesson step"}</h3>
                      {lessonCurrentStep?.goal ? <p>{lessonCurrentStep.goal}</p> : null}
                    </header>
                    <DownloadableFiles files={lessonCurrentStep?.downloadFiles ?? []} />
                    {lessonCurrentStep?.mediaKind === "video" ? (
                      <div className="learning-node-video-shell">
                        <div className="learning-node-video-wrap" ref={lessonVideoWrapRef}>
                          <button
                            className="learning-node-video-transcript-toggle"
                            type="button"
                            aria-label={lessonTranscriptOpen ? "Collapse transcript" : "Expand transcript"}
                            onClick={() => setLessonTranscriptOpen((current) => !current)}
                          >
                            <Icon name="transcript" />
                          </button>
                          <video controls preload="metadata">
                            <source src={lessonCurrentStep?.videoUrl || DUMMY_VIDEO_URL} type="video/mp4" />
                          </video>
                        </div>
                        {lessonTranscriptOpen ? (
                          <aside className="learning-node-video-transcript" aria-label="Video transcript" style={lessonVideoHeight > 0 ? { height: `${lessonVideoHeight}px` } : undefined}>
                            <h4>Transcript</h4>
                            <div className="learning-node-video-transcript-scroll">
                              {[
                                "00:00 - Introduction to this learning step and expected outcome.",
                                "00:12 - Key concept walkthrough with a practical context example.",
                                "00:38 - Why this concept matters in day-to-day operations.",
                                "01:04 - Common mistakes and quick correction strategies.",
                                "01:31 - Recap and what to pay attention to in the next step.",
                                "02:00 - Additional transcript placeholder line for scroll testing.",
                              ].map((line, index) => (
                                <p key={`transcript-line-${index}`}>{line}</p>
                              ))}
                            </div>
                          </aside>
                        ) : null}
                      </div>
                    ) : (
                      <div className="learning-node-lesson-content-scroll">
                        <p>
                          This lesson section uses generated runtime structure and currently renders styled placeholder teaching text.
                          Pay special attention to <span className="learning-node-term" title="A deployment strategy that shifts user traffic from old to new environments in controlled phases." data-definition="A deployment strategy that shifts user traffic from old to new environments in controlled phases.">blue-green deployment</span> and how it connects to your node goal.
                        </p>
                        {lessonCurrentStep?.summary ? <p>{lessonCurrentStep.summary}</p> : null}
                        {lessonCurrentStep?.topics.length ? (
                          <ul>
                            {lessonCurrentStep.topics.map((topic, index) => <li key={`lesson-topic-point-${index}`}>{topic}</li>)}
                          </ul>
                        ) : null}
                        {lessonCurrentStep?.mediaKind === "image" ? (
                          <figure className="learning-node-media-block">
                            <img src={lessonCurrentStep?.imageUrl || DUMMY_DEVOPS_IMAGE} alt="Dummy lesson diagram preview" />
                            <figcaption>Dummy media block: example visual placeholder for this generated lesson step.</figcaption>
                          </figure>
                        ) : null}
                        <p>
                          More runtime-powered text content will be introduced in the next step. For now this shell verifies layout, navigation,
                          scroll behavior, sources placement, media rendering, and technical-term tooltips.
                        </p>
                      </div>
                    )}
                    {lessonCurrentStep?.mediaKind === "video" ? (
                      <p className="learning-node-video-description">
                        Dummy video description: this short clip introduces the main concept of this learning step.
                      </p>
                    ) : null}
                  </article>
                </>
              ) : null}
              {isLessonResultStep ? (
                <section className="learning-node-section learning-node-lesson-result">
                  <div className="learning-node-milestone-hero">
                    <div className="learning-node-milestone-badge">
                      <Icon name="certificate" />
                      <strong>{node?.type === "review" ? "Review Completed" : "Learning Unit Completed"}</strong>
                      <small>Result preview</small>
                    </div>
                  </div>
                  <div className="learning-node-page-placeholder">
                    Summary preview:
                    <ul>
                      <li>You progressed through the planned learning flow.</li>
                      <li>Runtime package steps were rendered successfully.</li>
                      <li>Interactive evaluation details will be added in the next step.</li>
                    </ul>
                  </div>
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
                      assetCatalog={assetCatalog as Record<string, Record<string, unknown>>}
                      showHeading={node?.type !== "quiz"}
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
                      uploads={uploads}
                      setUploads={setUploads}
                      assetCatalog={assetCatalog as Record<string, Record<string, unknown>>}
                      showHeading={node?.type !== "quiz"}
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
                      assetCatalog={assetCatalog as Record<string, Record<string, unknown>>}
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
                  {showGuidedResultLoading ? (
                    <div className="learning-node-initial-loading learning-node-result-loading">
                      <span className="learning-node-loading-circle" aria-hidden="true" />
                      <strong>Please wait while your results are being verified.</strong>
                      <small>This may take a few seconds.</small>
                    </div>
                  ) : (
                    <>
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
                    </>
                  )}
                </section>
              ) : null}
            </section>
          ) : null}

          {!showInitialGenerationLoader && node && !["unlock_gate", "milestone", "assessment_hook", "quiz", "practice", "checkpoint", "capstone", "learning_unit", "review"].includes(node.type) ? (
            <div className="learning-node-page-placeholder">
              Node type <strong>{node.type}</strong> is intentionally not rendered in this step.
            </div>
          ) : null}
        </div>
      ) : null}

      {!error && session && showLessonContentActions ? (
        <div className="learning-node-page-actions-outside-card">
          <div className="learning-node-lesson-feedback-row">
            <div className="sources-wrap assistant-evidence-wrap learning-node-inline-sources">
              <button
                className={`sources-button assistant-evidence-trigger${lessonSourcesOpen ? " active" : ""}`}
                type="button"
                aria-expanded={lessonSourcesOpen}
                onClick={() => setLessonSourcesOpen((current) => !current)}
              >
                <span className="assistant-evidence-trigger-icon" aria-hidden="true">
                  <Icon name="files" />
                </span>
                <small>Sources ({lessonSources.length})</small>
              </button>
              <SourcesPanel open={lessonSourcesOpen} onClose={() => setLessonSourcesOpen(false)} sources={lessonSources} direction="up" />
            </div>
            <button className="icon-button" type="button" aria-label="Like this explanation" title="Like (coming soon)">
              <Icon name="thumb-up" />
            </button>
            <button className="icon-button" type="button" aria-label="Dislike this explanation" title="Dislike (coming soon)">
              <Icon name="thumb-down" />
            </button>
          </div>
        </div>
      ) : null}

      {showAssessmentProgress || showGuidedProgress || showLessonProgress ? (
        <div className="learning-node-progress-floating" aria-label="Learning node progress">
          <div
            className="learning-node-progress-track"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={showAssessmentProgress ? assessmentProgressPercent : showGuidedProgress ? guidedProgressPercent : lessonProgressPercent}
          >
            <div className="learning-node-progress-fill" style={{ width: `${showAssessmentProgress ? assessmentProgressPercent : showGuidedProgress ? guidedProgressPercent : lessonProgressPercent}%` }} />
          </div>
        </div>
      ) : null}

      {showMilestoneFooterActions || showAssessmentFooterActions || showGuidedFooterActions || showLessonFooterActions ? (
        <div className="learning-node-fixed-footer">
          <div className="learning-node-fixed-footer-inner">
            <div className={`learning-node-footer-actions${showLessonFooterActions ? " lesson-mode" : ""}`}>
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
                  {guidedStep === "items" && (node?.type === "quiz" || node?.type === "practice") && guidedItemIndex > 0 ? (
                    <button
                      className="secondary-button"
                      type="button"
                      disabled={guidedCompleting || guidedRestarting}
                      onClick={() => setGuidedItemIndex((value) => Math.max(0, value - 1))}
                    >
                      Back
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
                          setGuidedStep("complete");
                          void (async () => {
                            try {
                              await onGuidedComplete?.(collectedGuidedResponses);
                            } catch {
                              setGuidedStep("items");
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
              {showLessonFooterActions ? (
                <>
                  {isLessonContentStep && !lessonCompleted ? (
                    <div className="learning-node-footer-left-actions">
                      <button className="secondary-button" type="button" disabled>
                        <Icon name="chalkboard" />
                        Audio
                      </button>
                      <button className="secondary-button" type="button">
                        <Icon name="reset" />
                        Explain again
                      </button>
                    </div>
                  ) : <div />}
                  <div className="learning-node-footer-right-actions">
                    {(isLessonContentStep && !isLessonFirstContentStep) || isLessonResultStep ? (
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => setLessonFlowStepIndex((value) => Math.max(0, value - 1))}
                      >
                        Back
                      </button>
                    ) : null}
                    <button
                      className="primary-button"
                      type="button"
                      disabled={lessonFlowTotalSteps === 0 || lessonClosing || lessonCompleting}
                      onClick={() => {
                        if (isLessonStartStep) {
                          void onAssessmentStart?.();
                        }
                        if (isLessonResultStep) {
                          void onLessonClose?.();
                          return;
                        }
                        if (isLessonLastContentStep) {
                          setLessonCompleted(true);
                          setLessonFlowStepIndex(Math.min(boundedLessonStep + 1, Math.max(lessonFlowTotalSteps - 1, 0)));
                          void (async () => {
                            try {
                              await onLessonComplete?.(lessonCompletionPayload);
                            } catch {
                              setLessonCompleted(false);
                              setLessonFlowStepIndex(Math.max(1, Math.max(lessonFlowTotalSteps - 2, 0)));
                            }
                          })();
                          return;
                        }
                        setLessonFlowStepIndex((value) => Math.min(value + 1, Math.max(lessonFlowTotalSteps - 1, 0)));
                      }}
                    >
                      {lessonClosing
                        ? "Closing..."
                        : lessonCompleting
                          ? "Finishing..."
                          : isLessonStartStep
                            ? "Start"
                            : isLessonLastContentStep
                              ? "Finish"
                              : isLessonResultStep
                                ? "Close"
                                : "Next"}
                    </button>
                  </div>
                </>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
