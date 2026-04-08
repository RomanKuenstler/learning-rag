import { useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import type { Message } from "../../types/chat";
import { Icon } from "../common/Icons";
import { SourcesPanel } from "../sources/SourcesPanel";

type MessageBubbleProps = {
  message: Message;
  onFeedback?: (payload: { message_id: number | null; rating: number; feedback_text: string; re_explain_requested: boolean }) => Promise<void> | void;
};

function attachmentTone(fileName: string) {
  const normalized = fileName.toLowerCase();
  if (normalized.endsWith(".pdf")) return "is-red";
  if (normalized.endsWith(".html") || normalized.endsWith(".htm")) return "is-blue";
  if (normalized.endsWith(".epub")) return "is-purple";
  if (normalized.endsWith(".md") || normalized.endsWith(".txt")) return "is-gray";
  return "is-green";
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const isAssistant = message.role === "assistant";
  const attachments = message.attachments.length > 0 ? (
    <div className={`message-attachments composer-attachment-chip-list${isAssistant ? "" : " user-message-attachment-chip-list"}`}>
      {message.attachments.map((attachment) => (
        <span
          key={`${message.id}-${attachment.file_name}`}
          className={`message-attachment-pill composer-attachment-chip${isAssistant ? "" : " user-message-attachment-chip user-message-attachment-card"}`}
        >
          <span className={`composer-attachment-icon ${attachmentTone(attachment.file_name)}`}>
            <span className="composer-attachment-icon-label">
              {attachment.file_name.split(".").pop()?.slice(0, 3).toUpperCase() ?? "FILE"}
            </span>
          </span>
          <span className="composer-attachment-meta">
            <span className="composer-attachment-name">{attachment.file_name}</span>
            <span className="composer-attachment-ext">{attachment.file_name.split(".").pop()?.toUpperCase() ?? "FILE"}</span>
          </span>
        </span>
      ))}
    </div>
  ) : null;

  return (
    <article className={`message-bubble msg ${message.role}${message.status === "pending" ? " pending" : ""}`}>
      <div className="message-meta msg-header">
        <span>{isAssistant ? "Assistant" : "You"}</span>
        {message.status === "pending" ? <span className="message-status">Working...</span> : null}
        {message.status === "error" ? <span className="message-status error">Error</span> : null}
      </div>
      {!isAssistant ? attachments : null}
      <div className={`message-content ${isAssistant ? "assistant-markdown" : "user-message-content"}`}>
        {isAssistant ? (
          <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
            {message.content}
          </ReactMarkdown>
        ) : (
          message.content
        )}
      </div>
      {isAssistant ? attachments : null}
      {isAssistant ? (
        <div className="sources-wrap assistant-evidence-wrap">
          <button
            className={`sources-button assistant-evidence-trigger${sourcesOpen ? " active" : ""}`}
            type="button"
            aria-expanded={sourcesOpen}
            onClick={() => setSourcesOpen((current) => !current)}
          >
            <span className="assistant-evidence-trigger-icon" aria-hidden="true">
              <Icon name="files" />
            </span>
            <small>Sources ({message.sources.length})</small>
          </button>
          <SourcesPanel open={sourcesOpen} onClose={() => setSourcesOpen(false)} sources={message.sources} />
        </div>
      ) : null}
    </article>
  );
}
