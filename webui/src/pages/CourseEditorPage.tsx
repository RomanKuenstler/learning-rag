import { useEffect, useMemo, useRef, useState, type ChangeEvent, type UIEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Icon } from "../components/common/Icons";
import type { ContentAsset, CourseAttachmentReferenceIssue, CourseEditorData } from "../types/chat";

type CourseEditorPageProps = {
  courseId: string;
  saving: boolean;
  onLoadEditor: (courseId: string) => Promise<CourseEditorData>;
  onSaveEditor: (courseId: string, rawJson: string) => Promise<CourseEditorData>;
  onUploadAttachments: (courseId: string, files: File[]) => Promise<{ assets: ContentAsset[] }>;
};

function formatBytes(size: number): string {
  if (!Number.isFinite(size) || size <= 0) {
    return "0 B";
  }
  const units = ["B", "KB", "MB", "GB"];
  let value = size;
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }
  return `${value.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function issueLabel(issue: CourseAttachmentReferenceIssue): string {
  return issue.issue === "missing" ? "Missing" : "Ambiguous";
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function isFileReferenceString(valueToken: string): boolean {
  try {
    const parsed = JSON.parse(valueToken);
    if (typeof parsed !== "string") {
      return false;
    }
    if (parsed.includes("/") || parsed.includes("\\")) {
      return false;
    }
    return /^[A-Za-z0-9._ -]+\.[A-Za-z0-9]{2,8}$/.test(parsed);
  } catch {
    return false;
  }
}

function highlightJson(raw: string): string {
  let index = 0;
  let output = "";
  const length = raw.length;

  const push = (text: string, className?: string) => {
    const escaped = escapeHtml(text);
    output += className ? `<span class="${className}">${escaped}</span>` : escaped;
  };

  const isWhitespace = (char: string | undefined) => char === " " || char === "\n" || char === "\r" || char === "\t";

  while (index < length) {
    const char = raw[index];

    if (char === "\"") {
      let end = index + 1;
      let escaped = false;
      while (end < length) {
        const next = raw[end];
        if (!escaped && next === "\"") {
          end += 1;
          break;
        }
        if (!escaped && next === "\\") {
          escaped = true;
        } else {
          escaped = false;
        }
        end += 1;
      }
      const token = raw.slice(index, end);
      let lookahead = end;
      while (lookahead < length && isWhitespace(raw[lookahead])) {
        lookahead += 1;
      }
      if (lookahead < length && raw[lookahead] === ":") {
        push(token, "course-editor-token-key");
      } else if (isFileReferenceString(token)) {
        push(token, "course-editor-token-file-ref");
      } else {
        push(token, "course-editor-token-value");
      }
      index = end;
      continue;
    }

    if (char === "{" || char === "}") {
      push(char, "course-editor-token-brace");
      index += 1;
      continue;
    }
    if (char === "[" || char === "]") {
      push(char, "course-editor-token-bracket");
      index += 1;
      continue;
    }
    if (char === ",") {
      push(char, "course-editor-token-comma");
      index += 1;
      continue;
    }

    if (char === "-" || (char >= "0" && char <= "9")) {
      let end = index + 1;
      while (end < length && /[0-9eE.+-]/.test(raw[end])) {
        end += 1;
      }
      const token = raw.slice(index, end);
      if (/^-?\d+(\.\d+)?([eE][+-]?\d+)?$/.test(token)) {
        push(token, "course-editor-token-value");
        index = end;
        continue;
      }
    }

    if (raw.startsWith("true", index) || raw.startsWith("false", index) || raw.startsWith("null", index)) {
      const literal = raw.startsWith("true", index)
        ? "true"
        : raw.startsWith("false", index)
          ? "false"
          : "null";
      push(literal, "course-editor-token-value");
      index += literal.length;
      continue;
    }

    push(char);
    index += 1;
  }

  return output;
}

export function CourseEditorPage({
  courseId,
  saving,
  onLoadEditor,
  onSaveEditor,
  onUploadAttachments,
}: CourseEditorPageProps) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);
  const [course, setCourse] = useState<CourseEditorData | null>(null);
  const [rawJson, setRawJson] = useState("");
  const [copied, setCopied] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const lineNumberRef = useRef<HTMLDivElement | null>(null);
  const highlightRef = useRef<HTMLPreElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setSaveError(null);
    setSaveSuccess(null);
    void onLoadEditor(courseId)
      .then((payload) => {
        if (cancelled) {
          return;
        }
        setCourse(payload);
        setRawJson(payload.raw_json);
      })
      .catch((nextError: unknown) => {
        if (!cancelled) {
          setError(nextError instanceof Error ? nextError.message : "Failed to load course editor");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [courseId, onLoadEditor]);

  const parsedJsonError = useMemo(() => {
    try {
      JSON.parse(rawJson);
      return null;
    } catch (nextError: unknown) {
      return nextError instanceof Error ? nextError.message : "Invalid JSON";
    }
  }, [rawJson]);
  const lineCount = useMemo(() => Math.max(1, rawJson.split("\n").length), [rawJson]);
  const highlightedJson = useMemo(() => highlightJson(rawJson), [rawJson]);
  const isReadOnly = Boolean(course && !course.can_edit);

  const handleSave = async () => {
    setSaveError(null);
    setSaveSuccess(null);
    if (parsedJsonError) {
      setSaveError(`JSON is invalid: ${parsedJsonError}`);
      return;
    }
    try {
      const saved = await onSaveEditor(courseId, rawJson);
      setCourse(saved);
      setRawJson(saved.raw_json);
      setSaveSuccess("Course saved.");
    } catch (nextError: unknown) {
      setSaveError(nextError instanceof Error ? nextError.message : "Failed to save course");
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleUploadFiles = async (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    event.target.value = "";
    if (files.length === 0) {
      return;
    }
    setUploading(true);
    setSaveError(null);
    setSaveSuccess(null);
    try {
      await onUploadAttachments(courseId, files);
      const refreshed = await onLoadEditor(courseId);
      setCourse(refreshed);
      setRawJson(refreshed.raw_json);
      setSaveSuccess(`${files.length} attachment${files.length === 1 ? "" : "s"} uploaded.`);
    } catch (nextError: unknown) {
      setSaveError(nextError instanceof Error ? nextError.message : "Failed to upload attachments");
    } finally {
      setUploading(false);
    }
  };

  const handleCopyJson = async () => {
    try {
      await navigator.clipboard.writeText(rawJson);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      setSaveError("Failed to copy JSON to clipboard.");
    }
  };

  const handleJsonScroll = (event: UIEvent<HTMLTextAreaElement>) => {
    const target = event.currentTarget;
    if (lineNumberRef.current) {
      lineNumberRef.current.scrollTop = target.scrollTop;
    }
    if (highlightRef.current) {
      highlightRef.current.scrollTop = target.scrollTop;
      highlightRef.current.scrollLeft = target.scrollLeft;
    }
  };

  return (
    <section className="gpt-editor-page course-editor-page">
      <header className="gpt-editor-header">
        <button className="gpt-editor-back" type="button" onClick={() => navigate(-1)}>
          <Icon name="chevron-left" />
          Back
        </button>
        <h1 className="gpt-editor-title">Edit Course</h1>
        <button className="primary-button gpt-editor-save" type="button" disabled={loading || saving || uploading || isReadOnly} onClick={() => void handleSave()}>
          {saving ? "Saving..." : "Save"}
        </button>
      </header>

      <div className="gpt-editor-layout course-editor-layout">
        <div className="gpt-editor-panel gpt-editor-config course-editor-panel">
          {loading ? <div className="empty-state">Loading course editor...</div> : null}
          {error ? <div className="empty-state">{error}</div> : null}
          {!loading && !error && course ? (
            <>
              <section className="gpt-editor-section">
                <div className="course-editor-section-header">
                  <h4 className="gpt-editor-section-title">Course JSON</h4>
                  <button className="secondary-button course-editor-copy-button" type="button" onClick={() => void handleCopyJson()}>
                    <Icon name="files" />
                    {copied ? "Copied" : "Copy"}
                  </button>
                </div>
                <div className="course-editor-json-shell">
                  <div ref={lineNumberRef} className="course-editor-line-numbers" aria-hidden="true">
                    {Array.from({ length: lineCount }, (_, lineIndex) => (
                      <span key={lineIndex}>{lineIndex + 1}</span>
                    ))}
                  </div>
                  <div className="course-editor-code-wrap">
                    <pre ref={highlightRef} className="course-editor-json-highlight" dangerouslySetInnerHTML={{ __html: highlightedJson }} />
                    <textarea
                      className="dialog-input preferences-textarea gpt-editor-textarea gpt-editor-textarea-lg course-editor-json course-editor-json-input"
                      rows={28}
                      value={rawJson}
                      onChange={(event) => setRawJson(event.target.value)}
                      spellCheck={false}
                      disabled={isReadOnly}
                      onScroll={handleJsonScroll}
                    />
                  </div>
                </div>
                <p className={`course-editor-lint ${parsedJsonError ? "invalid" : "valid"}`}>
                  {parsedJsonError ? `Lint: invalid JSON (${parsedJsonError})` : "Lint: valid JSON format"}
                </p>
              </section>

              <section className="gpt-editor-section">
                <h4 className="gpt-editor-section-title">Attached Media</h4>
                <div className="course-editor-attachment-table">
                  <div className="course-editor-attachment-head">
                    <span>Filename</span>
                    <span>Type</span>
                    <span>Size</span>
                    <span>Status</span>
                    <span>Uploaded</span>
                    <span>Preview</span>
                  </div>
                  <div className="course-editor-attachment-body">
                    {course.attachments.length === 0 ? (
                      <div className="course-editor-attachment-empty">No course attachments yet.</div>
                    ) : course.attachments.map((asset) => (
                      <div key={asset.asset_id} className="course-editor-attachment-row">
                        <span className="course-editor-attachment-file">{asset.file_name}</span>
                        <span>{asset.asset_kind}</span>
                        <span>{formatBytes(asset.size_bytes)}</span>
                        <span>{asset.asset_status}</span>
                        <span>{new Date(asset.created_at).toLocaleString()}</span>
                        <span>
                          {asset.url ? (
                            <a href={asset.url} target="_blank" rel="noreferrer" className="course-editor-attachment-link">
                              Open
                            </a>
                          ) : (
                            "-"
                          )}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="course-editor-attachment-actions">
                  <button className="primary-button course-editor-attachment-button" type="button" disabled={uploading || saving || isReadOnly} onClick={handleUploadClick}>
                    <Icon name="files" />
                    {uploading ? "Uploading..." : "Add Attachments"}
                  </button>
                  <input
                    ref={fileInputRef}
                    className="course-editor-hidden-input"
                    type="file"
                    multiple
                    onChange={handleUploadFiles}
                  />
                </div>
              </section>

              <section className="gpt-editor-section">
                <h4 className="gpt-editor-section-title">Attachment Reference Check</h4>
                {course.attachment_reference_issues.length === 0 ? (
                  <p className="course-editor-ok">All filename-based attachment references are resolvable.</p>
                ) : (
                  <div className="course-editor-issues">
                    {course.attachment_reference_issues.map((issue) => (
                      <div key={`${issue.file_name}-${issue.issue}`} className="course-editor-issue">
                        <strong>{issueLabel(issue)}:</strong> <span>{issue.file_name}</span>
                        {issue.details ? <small>{issue.details}</small> : null}
                      </div>
                    ))}
                  </div>
                )}
              </section>

              {saveError ? <div className="course-editor-error-banner">{saveError}</div> : null}
              {saveSuccess ? <div className="course-editor-success-banner">{saveSuccess}</div> : null}
              {isReadOnly ? <div className="course-editor-error-banner">You do not have edit permission for this course.</div> : null}
            </>
          ) : null}
        </div>
      </div>
    </section>
  );
}
