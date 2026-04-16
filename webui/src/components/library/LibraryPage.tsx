import { useEffect, useMemo, useState } from "react";
import { Icon } from "../common/Icons";
import type { LibraryFile, LibraryResponse } from "../../types/chat";
import { Dialog } from "../common/Dialog";
import { UploadDialog } from "./UploadDialog";

type LibraryPageProps = {
  library: LibraryResponse | null;
  loading: boolean;
  error: string | null;
  showOtherUsers: boolean;
  uploading: boolean;
  busyFileIds: number[];
  onLoad: (includeOtherUsers: boolean) => void;
  onToggleShowOtherUsers: (nextValue: boolean) => void;
  onToggleFile: (file: LibraryFile) => void;
  onDeleteFile: (fileId: number) => void;
  onUploadFiles: (files: File[], tagsByFile: Record<string, string[]>) => Promise<void>;
};

function formatBytes(sizeBytes: number) {
  if (sizeBytes < 1024) {
    return `${sizeBytes} B`;
  }
  if (sizeBytes < 1024 * 1024) {
    return `${(sizeBytes / 1024).toFixed(1)} KB`;
  }
  return `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`;
}

function extensionTone(extension: string) {
  const normalized = extension.toLowerCase();
  if (normalized === ".pdf") {
    return "is-red";
  }
  if (normalized === ".html" || normalized === ".htm") {
    return "is-blue";
  }
  if (normalized === ".epub") {
    return "is-purple";
  }
  if (normalized === ".md" || normalized === ".txt") {
    return "is-gray";
  }
  return "is-green";
}

export function LibraryPage({
  library,
  loading,
  error,
  showOtherUsers,
  uploading,
  busyFileIds,
  onLoad,
  onToggleShowOtherUsers,
  onToggleFile,
  onDeleteFile,
  onUploadFiles,
}: LibraryPageProps) {
  const [uploadOpen, setUploadOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<LibraryFile | null>(null);
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (library === null) {
      onLoad(showOtherUsers);
    }
  }, [library, onLoad, showOtherUsers]);

  const busySet = useMemo(() => new Set(busyFileIds), [busyFileIds]);
  const filteredFiles = useMemo(() => {
    if (!library) {
      return [];
    }
    const needle = search.trim().toLowerCase();
    if (!needle) {
      return library.files;
    }
    return library.files.filter((file) => {
      const inName = file.file_name.toLowerCase().includes(needle);
      const inTags = file.tags.some((tag) => tag.toLowerCase().includes(needle));
      return inName || inTags;
    });
  }, [library, search]);

  return (
    <section className="chat-column library-column">
      {error ? <p className="chat-error chat-error-banner">{error}</p> : null}

      <section className="info-group-card library-summary-card">
        <h4>Knowledge Base</h4>
        <div className="library-summary-table">
          <div className="library-summary-head">
            <span>Total files</span>
            <span>Embedded files</span>
            <span>Total chunks</span>
          </div>
          <div className="library-summary-row">
            <strong>{library?.summary.total_files ?? 0}</strong>
            <strong>{library?.summary.embedded_files ?? 0}</strong>
            <strong>{library?.summary.total_chunks ?? 0}</strong>
          </div>
        </div>
      </section>

      <section className="info-group-card library-table-card">
        <div className="library-table-header">
          <h4>Files</h4>
          <div className="table-search-input library-search-input">
            <Icon name="search" className="table-search-input-icon" />
            <input
              className="dialog-input table-search-input-control"
              type="search"
              placeholder="Search files or tags"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
        </div>

        <div className="library-table">
          {loading ? <div className="empty-state">Loading library...</div> : null}

          {!loading && library && filteredFiles.length === 0 ? (
            <div className="empty-state">
              <div>
                <p>{library.files.length > 0 ? "No files match your search." : "No files are embedded yet."}</p>
                <p>{library.files.length > 0 ? "Try a different file or tag keyword." : "Upload supported knowledge files to start grounding answers."}</p>
              </div>
            </div>
          ) : null}

          {!loading && library && filteredFiles.length > 0 ? (
            <>
              <div className="library-table-head">
                <span>Name</span>
                <span>Status</span>
                <span>Tags</span>
                <span>Size</span>
                <span>Chunks</span>
                <span>Type</span>
                <span>Embedded</span>
                <span>Updated</span>
                <span>Actions</span>
              </div>
              <div className="library-table-body">
                {filteredFiles.map((file) => (
                  <div key={file.id} className="library-table-row">
                    <div className="library-path">
                      <strong>{file.file_name}</strong>
                      <div className="library-owner-cell">
                        {file.is_global ? <span className="library-tag-line">global</span> : null}
                        {file.is_owned_by_current_user ? <span className="library-tag-line">owned by you</span> : null}
                        {!file.is_global && !file.is_owned_by_current_user ? (
                          <span className="library-tag-line muted">
                            owner: {file.owner_displayname || file.owner_username || "unknown"}
                          </span>
                        ) : null}
                      </div>
                    </div>
                    <div className="library-status-cell">
                      <span className={`status-icon-pill ${file.is_enabled ? "enabled" : "disabled"}`}>
                        <Icon name={file.is_enabled ? "check" : "ban"} />
                      </span>
                    </div>
                    <div className="library-tags-cell">
                      {file.tags.length > 0 ? (
                        file.tags.map((tag) => (
                          <span key={`${file.id}-${tag}`} className="library-tag-line">
                            {tag}
                          </span>
                        ))
                      ) : (
                        <span className="library-tag-line muted">No tags</span>
                      )}
                    </div>
                    <div>{formatBytes(file.size_bytes)}</div>
                    <div>{file.chunk_count}</div>
                    <div>
                      <span className={`library-extension-chip ${extensionTone(file.extension || file.file_type)}`}>
                        {file.extension || file.file_type}
                      </span>
                      {file.is_system ? <span className="library-tag-line">system</span> : null}
                      {file.source_origin === "admin_upload" ? <span className="library-tag-line">admin upload</span> : null}
                    </div>
                    <div className="library-status-cell">
                      <span className={`status-icon-pill ${file.is_embedded ? "enabled" : "disabled"}`}>
                        {file.is_embedded ? <Icon name="check" /> : <span className="status-empty">-</span>}
                      </span>
                    </div>
                    <div className="library-updated-cell">
                      <strong>{new Date(file.updated_at).toLocaleDateString()}</strong>
                      <span>{new Date(file.updated_at).toLocaleTimeString()}</span>
                    </div>
                    <div className="library-row-actions">
                      <button
                        className="library-toggle-button"
                        type="button"
                        disabled={busySet.has(file.id) || !file.can_disable}
                        onClick={() => onToggleFile(file)}
                        aria-label={file.is_enabled ? `Disable ${file.file_name}` : `Enable ${file.file_name}`}
                      >
                        <Icon name={file.is_enabled ? "ban" : "check"} />
                      </button>
                      <button
                        className="library-delete-button"
                        type="button"
                        disabled={busySet.has(file.id) || !file.can_delete}
                        onClick={() => setDeleteTarget(file)}
                        aria-label={`Delete ${file.file_name}`}
                      >
                        <Icon name="trash" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : null}
        </div>
        <div className="library-table-footer">
          <label className="library-switch-label" title="Show files uploaded by other users">
            <span className="filter-switch">
              <input
                type="checkbox"
                checked={showOtherUsers}
                onChange={(event) => onToggleShowOtherUsers(event.target.checked)}
              />
              <span className="filter-switch-slider" />
            </span>
            <span>Show other users' files</span>
          </label>
          <button className="restart-button library-upload-button" type="button" onClick={() => setUploadOpen(true)}>
            Upload
          </button>
        </div>
      </section>

      {uploadOpen && library ? (
        <UploadDialog
          allowedExtensions={library.allowed_extensions}
          defaultTag={library.default_tag}
          maxFiles={library.max_upload_files}
          uploading={uploading}
          onClose={() => setUploadOpen(false)}
          onSubmit={onUploadFiles}
        />
      ) : null}

      {deleteTarget ? (
        <Dialog
          title="Delete File"
          onClose={() => setDeleteTarget(null)}
          className="dialog-compact"
          actions={
            <>
              <button className="secondary-button library-delete-cancel" type="button" onClick={() => setDeleteTarget(null)}>
                Keep
              </button>
              <button
                className="danger-button library-delete-confirm"
                type="button"
                onClick={() => {
                  onDeleteFile(deleteTarget.id);
                  setDeleteTarget(null);
                }}
              >
                Delete
              </button>
            </>
          }
        >
          <p>
            Delete <strong>{deleteTarget.file_name}</strong> from the library, vector index, database, and local data folder?
          </p>
        </Dialog>
      ) : null}
    </section>
  );
}
