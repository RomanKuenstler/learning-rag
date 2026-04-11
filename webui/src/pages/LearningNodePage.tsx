import type { LearningNodeSession } from "../types/chat";

type LearningNodePageProps = {
  loading: boolean;
  error: string | null;
  session: LearningNodeSession | null;
};

function statusLabel(status: LearningNodeSession["status"]) {
  if (status === "completed") {
    return "Completed";
  }
  if (status === "in_progress") {
    return "In Progress";
  }
  return "Created";
}

export function LearningNodePage({ loading, error, session }: LearningNodePageProps) {
  return (
    <section className="learning-node-page-shell">
      <header className="learning-node-page-header">
        <h2>Learning Node</h2>
        <p>This page is the dedicated route shell for node-specific learning sessions.</p>
      </header>

      {loading ? <div className="empty-state">Loading learning node session...</div> : null}
      {error ? <div className="error-banner">{error}</div> : null}

      {!loading && !error && session ? (
        <div className="learning-node-page-card">
          <div className="learning-node-page-grid">
            <span>
              <strong>Course</strong>
              <small>{session.course_title}</small>
            </span>
            <span>
              <strong>Node</strong>
              <small>{session.node_title}</small>
            </span>
            <span>
              <strong>Node Type</strong>
              <small>{session.node_type}</small>
            </span>
            <span>
              <strong>Status</strong>
              <small>{statusLabel(session.status)}</small>
            </span>
            <span>
              <strong>Session</strong>
              <small>{session.id}</small>
            </span>
            <span>
              <strong>Last Opened</strong>
              <small>{session.last_opened_at ? new Date(session.last_opened_at).toLocaleString() : "Never"}</small>
            </span>
          </div>
          <div className="learning-node-page-placeholder">
            Learning node content UI is intentionally out of scope for this step. This shell confirms session routing, loading, and lifecycle wiring.
          </div>
        </div>
      ) : null}
    </section>
  );
}
