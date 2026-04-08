import { useEffect, useRef } from "react";
import type { Source } from "../../types/chat";

type SourcesPanelProps = {
  open: boolean;
  onClose: () => void;
  sources: Source[];
};

export function SourcesPanel({ open, onClose, sources }: SourcesPanelProps) {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }

    function handlePointerDown(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        onClose();
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  return (
    <section className="sources-panel assistant-evidence-menu down" ref={ref} role="menu" aria-label="Sources">
      <h4 className="sources-panel-header assistant-evidence-heading">Sources</h4>
      <p className="assistant-evidence-summary">{sources.length} retrieved matches</p>
      <div className="sources-list assistant-evidence-list">
        {sources.length === 0 ? <p className="assistant-evidence-summary">No evidence returned for this answer.</p> : null}
        {sources.map((source) => (
          <article className="source-card" key={`${source.chunk_id}-${source.file_name}`}>
            <div className="source-row assistant-evidence-meta">
              <strong className="assistant-evidence-file-name">{source.file_name}</strong>
              <span className="assistant-evidence-score">{source.score.toFixed(3)}</span>
            </div>
            <div className="source-meta">
              {source.tags.map((tag) => (
                <span className="tag-pill" key={tag}>
                  {tag}
                </span>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
