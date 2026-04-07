import { ChatInput } from "../input/ChatInput";
import { MessageList } from "../messages/MessageList";
import type { AssistantMode, Message } from "../../types/chat";

type ChatViewProps = {
  messages: Message[];
  sending: boolean;
  loadingMessages: boolean;
  error: string | null;
  assistantMode: AssistantMode;
  attachmentRules: {
    maxFiles: number;
    allowedExtensions: string[];
  };
  onSend: (value: string, attachments: File[], mode: AssistantMode) => Promise<void>;
  onFeedback?: (payload: { message_id: number | null; rating: number; feedback_text: string; re_explain_requested: boolean }) => Promise<void> | void;
  variant?: "default" | "embedded";
};

export function ChatView({
  messages,
  sending,
  loadingMessages,
  error,
  assistantMode,
  attachmentRules,
  onSend,
  onFeedback,
  variant = "default",
}: ChatViewProps) {
  return (
    <section className={`chat-column${variant === "embedded" ? " chat-column-embedded" : ""}`}>
      {error ? <p className="chat-error chat-error-banner">{error}</p> : null}
      <div className={`chat-thread-card chat${variant === "embedded" ? " chat-embedded-thread" : ""}`} aria-label="Conversation">
        <MessageList messages={messages} loadingMessages={loadingMessages} onFeedback={onFeedback} />
      </div>
      <ChatInput
        disabled={sending}
        assistantMode={assistantMode}
        attachmentRules={attachmentRules}
        onSend={onSend}
        variant={variant}
      />
    </section>
  );
}
