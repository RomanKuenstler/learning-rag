import { useEffect, useRef } from "react";
import type { Message } from "../../types/chat";
import { MessageBubble } from "./MessageBubble";

type MessageListProps = {
  messages: Message[];
  loadingMessages: boolean;
  onFeedback?: (payload: { message_id: number | null; rating: number; feedback_text: string; re_explain_requested: boolean }) => Promise<void> | void;
};

export function MessageList({ messages, loadingMessages, onFeedback }: MessageListProps) {
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  if (loadingMessages) {
    return <div className="empty-state">Loading chat history...</div>;
  }

  if (messages.length === 0) {
    return <div className="empty-state">Ask a question to start a grounded conversation with your local knowledge base.</div>;
  }

  return (
    <div className="message-list">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} onFeedback={onFeedback} />
      ))}
      <div ref={endRef} />
    </div>
  );
}
