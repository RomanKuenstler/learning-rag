import { useEffect, useMemo, useState } from "react";
import type { AdminUser, CurrentUser } from "../../types/chat";
import { Dialog } from "../common/Dialog";
import { Icon } from "../common/Icons";

type AdminPageProps = {
  currentUser: CurrentUser;
  users: AdminUser[];
  loading: boolean;
  error: string | null;
  busyUserIds: number[];
  onLoad: () => void;
  onCreateUser: (payload: { username: string; displayname: string; role: "user" | "admin" | "student" }) => Promise<void>;
  onUpdateUser: (userId: number, payload: Partial<Pick<AdminUser, "status" | "force_password_change" | "role" | "displayname">>) => Promise<void>;
  onDeleteUser: (userId: number) => Promise<void>;
};

export function AdminPage({
  currentUser,
  users,
  loading,
  error,
  busyUserIds,
  onLoad,
  onCreateUser,
  onUpdateUser,
  onDeleteUser,
}: AdminPageProps) {
  const [addOpen, setAddOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<AdminUser | null>(null);
  const [form, setForm] = useState({ username: "", displayname: "", role: "user" as "user" | "admin" | "student" });
  const [roleMenuOpen, setRoleMenuOpen] = useState(false);
  const [rowRoleMenuUserId, setRowRoleMenuUserId] = useState<number | null>(null);
  const [rowRoleMenuPosition, setRowRoleMenuPosition] = useState<{ top: number; left: number } | null>(null);
  const busy = useMemo(() => new Set(busyUserIds), [busyUserIds]);

  useEffect(() => {
    void onLoad();
  }, []);

  useEffect(() => {
    if (rowRoleMenuUserId === null) {
      return;
    }
    const close = () => setRowRoleMenuUserId(null);
    const closeOnResize = () => {
      setRowRoleMenuUserId(null);
      setRowRoleMenuPosition(null);
    };
    window.addEventListener("click", close);
    window.addEventListener("resize", closeOnResize);
    window.addEventListener("scroll", closeOnResize, true);
    return () => {
      window.removeEventListener("click", close);
      window.removeEventListener("resize", closeOnResize);
      window.removeEventListener("scroll", closeOnResize, true);
    };
  }, [rowRoleMenuUserId]);

  return (
    <section className="chat-column library-column">
      {error ? <p className="chat-error chat-error-banner">{error}</p> : null}
      <section className="info-group-card library-table-card">
        <div className="library-table-header">
          <h4>Users</h4>
        </div>
        <div className="library-table admin-users-table">
          {loading ? <div className="empty-state">Loading users...</div> : null}
          {!loading ? (
            <>
              <div className="library-table-head admin-table-head">
                <span>Username</span>
                <span>Display name</span>
                <span>Role</span>
                <span>Status</span>
                <span>Force password change</span>
                <span>Actions</span>
              </div>
              <div className="library-table-body">
                {users.map((user) => (
                  <div key={user.id} className="library-table-row admin-table-row">
                    <div className="admin-cell admin-cell-text">{user.username}</div>
                    <div className="admin-cell admin-cell-text">{user.displayname}</div>
                    <div className="admin-cell admin-cell-center">
                      {user.id !== currentUser.id && user.role !== "admin" ? (
                        <div className={`header-mode-picker dialog-role-picker admin-role-picker${rowRoleMenuUserId === user.id ? " open" : ""}`}>
                          <button
                            type="button"
                            className="header-mode-trigger dialog-role-trigger admin-role-trigger"
                            aria-expanded={rowRoleMenuUserId === user.id}
                            disabled={busy.has(user.id)}
                            onClick={(event) => {
                              event.stopPropagation();
                              const triggerRect = (event.currentTarget as HTMLButtonElement).getBoundingClientRect();
                              const menuWidth = 130;
                              const estimatedMenuHeight = 112;
                              const spaceBelow = window.innerHeight - triggerRect.bottom;
                              const openUp = spaceBelow < estimatedMenuHeight;
                              const top = openUp ? triggerRect.top - estimatedMenuHeight - 6 : triggerRect.bottom + 6;
                              const left = Math.max(8, Math.min(window.innerWidth - menuWidth - 8, triggerRect.left));
                              setRowRoleMenuPosition({ top: Math.max(8, top), left });
                              setRowRoleMenuUserId((current) => (current === user.id ? null : user.id));
                            }}
                          >
                            <span className="dialog-role-trigger-label">{user.role[0].toUpperCase() + user.role.slice(1)}</span>
                            <Icon name="chevron-down" className="header-mode-chevron" />
                          </button>
                          {rowRoleMenuUserId === user.id && rowRoleMenuPosition ? (
                            <div
                              className="header-mode-menu dialog-role-menu floating-menu"
                              role="menu"
                              onClick={(event) => event.stopPropagation()}
                              style={{ top: `${rowRoleMenuPosition.top}px`, left: `${rowRoleMenuPosition.left}px` }}
                            >
                              {(["user", "student"] as const).map((role) => (
                                <button
                                  key={role}
                                  type="button"
                                  className={`header-mode-option dialog-role-option${user.role === role ? " active" : ""}`}
                                  onClick={() => {
                                    void onUpdateUser(user.id, { role });
                                    setRowRoleMenuUserId(null);
                                    setRowRoleMenuPosition(null);
                                  }}
                                >
                                  <span className="dialog-role-option-label">{role[0].toUpperCase() + role.slice(1)}</span>
                                  {user.role === role ? <Icon name="check" className="header-mode-option-check" /> : null}
                                </button>
                              ))}
                            </div>
                          ) : null}
                        </div>
                      ) : (
                        <span className="admin-role-badge">{user.role}</span>
                      )}
                    </div>
                    <div className="admin-cell admin-cell-center">
                      <label className="filter-switch" title={user.status === "active" ? "Deactivate user" : "Activate user"}>
                        <input
                          type="checkbox"
                          checked={user.status === "active"}
                          disabled={busy.has(user.id) || user.id === currentUser.id}
                          onChange={(event) => void onUpdateUser(user.id, { status: event.target.checked ? "active" : "inactive" })}
                        />
                        <span className="filter-switch-slider" aria-hidden="true" />
                      </label>
                    </div>
                    <div className="admin-cell admin-cell-center">
                      <label className="filter-switch" title={user.force_password_change ? "Disable required password change" : "Require password change"}>
                        <input
                          type="checkbox"
                          checked={user.force_password_change}
                          disabled={busy.has(user.id)}
                          onChange={(event) => void onUpdateUser(user.id, { force_password_change: event.target.checked })}
                        />
                        <span className="filter-switch-slider" aria-hidden="true" />
                      </label>
                    </div>
                    <div className="admin-cell admin-cell-center">
                      <button
                        className="library-delete-button"
                        type="button"
                        disabled={busy.has(user.id) || user.id === currentUser.id}
                        onClick={() => setDeleteTarget(user)}
                        aria-label={`Delete ${user.username}`}
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
          <button className="restart-button library-upload-button" type="button" onClick={() => setAddOpen(true)}>
            Add user
          </button>
        </div>
      </section>

      {addOpen ? (
        <Dialog
          title="Add User"
          onClose={() => setAddOpen(false)}
          className="dialog-compact add-user-dialog"
          actions={
            <>
              <button className="secondary-button" type="button" onClick={() => setAddOpen(false)}>
                Cancel
              </button>
              <button
                className="primary-button"
                type="button"
                disabled={!form.username.trim() || !form.displayname.trim()}
                onClick={async () => {
                  await onCreateUser({
                    username: form.username.trim(),
                    displayname: form.displayname.trim(),
                    role: form.role,
                  });
                  setForm({ username: "", displayname: "", role: "user" });
                  setAddOpen(false);
                }}
              >
                Create
              </button>
            </>
          }
        >
          <div className="auth-form">
            <label className="dialog-role-field">
              <span className="dialog-field-label">Username</span>
              <input className="dialog-input" placeholder="Username" value={form.username} onChange={(event) => setForm((current) => ({ ...current, username: event.target.value }))} />
            </label>
            <label className="dialog-role-field">
              <span className="dialog-field-label">Display name</span>
              <input className="dialog-input" placeholder="Display name" value={form.displayname} onChange={(event) => setForm((current) => ({ ...current, displayname: event.target.value }))} />
            </label>
            <label className="dialog-role-field">
              <span className="dialog-field-label">Role</span>
              <div className={`header-mode-picker dialog-role-picker${roleMenuOpen ? " open" : ""}`}>
                <button type="button" className="header-mode-trigger dialog-role-trigger" aria-expanded={roleMenuOpen} onClick={() => setRoleMenuOpen((current) => !current)}>
                  <span className="dialog-role-trigger-label">{form.role[0].toUpperCase() + form.role.slice(1)}</span>
                  <Icon name="chevron-down" className="header-mode-chevron" />
                </button>
                {roleMenuOpen ? (
                  <div className="header-mode-menu dialog-role-menu" role="menu">
                    {(["user", "student", "admin"] as const).map((role) => (
                        <button
                          key={role}
                          type="button"
                          className={`header-mode-option dialog-role-option${form.role === role ? " active" : ""}`}
                          onClick={() => {
                            setForm((current) => ({ ...current, role }));
                            setRoleMenuOpen(false);
                          }}
                        >
                          <span className="dialog-role-option-label">{role[0].toUpperCase() + role.slice(1)}</span>
                          {form.role === role ? <Icon name="check" className="header-mode-option-check" /> : null}
                        </button>
                      ))}
                  </div>
                ) : null}
              </div>
            </label>
          </div>
        </Dialog>
      ) : null}

      {deleteTarget ? (
        <Dialog
          title="Delete User"
          onClose={() => setDeleteTarget(null)}
          className="dialog-compact"
          actions={
            <>
              <button className="secondary-button" type="button" onClick={() => setDeleteTarget(null)}>
                Cancel
              </button>
              <button
                className="danger-button"
                type="button"
                onClick={async () => {
                  await onDeleteUser(deleteTarget.id);
                  setDeleteTarget(null);
                }}
              >
                Delete
              </button>
            </>
          }
        >
          <p>Delete user <strong>{deleteTarget.username}</strong>? This removes their access and scoped chat data.</p>
        </Dialog>
      ) : null}
    </section>
  );
}
