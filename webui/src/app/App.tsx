import { useEffect, useState, type ComponentProps } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import { AdminPage } from "../components/admin/AdminPage";
import { ChatView } from "../components/chat/ChatView";
import { Dialog } from "../components/common/Dialog";
import { Icon } from "../components/common/Icons";
import { ChatFilterDialog } from "../components/filters/ChatFilterDialog";
import { AppShell } from "../components/layout/AppShell";
import { LibraryPage } from "../components/library/LibraryPage";
import { LearningPathsPage } from "../components/learning/LearningPathsPage";
import { PreferencesDialog } from "../components/preferences/PreferencesDialog";
import { Sidebar } from "../components/sidebar/Sidebar";
import { useChatApp } from "../hooks/useChatApp";
import { LoginPage } from "../pages/LoginPage";
import { PasswordChangePage } from "../pages/PasswordChangePage";
import { GptEditorPage } from "../pages/GptEditorPage";

type PreferencesTab = "general" | "personalization" | "settings" | "filter" | "archive";

function AppRoutes() {
  const app = useChatApp();
  const navigate = useNavigate();
  const location = useLocation();
  const currentChatId = location.pathname.startsWith("/chats/") ? location.pathname.split("/")[2] ?? null : null;
  const currentGptId = location.pathname.startsWith("/gpts/") && location.pathname.endsWith("/chat") ? location.pathname.split("/")[2] ?? null : null;
  const activeView = location.pathname.startsWith("/learning")
    ? "learning"
    : location.pathname.startsWith("/library")
      ? "library"
      : location.pathname.startsWith("/admin")
        ? "admin"
        : currentGptId
          ? "gpt"
          : "chat";
  const activeGptChat = currentGptId ? app.gptChatsById[currentGptId] ?? null : null;
  const [preferencesTab, setPreferencesTab] = useState<PreferencesTab | null>(null);
  const [infoOpen, setInfoOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false);
  const [chatFilterChatId, setChatFilterChatId] = useState<string | null>(null);
  const isGptEditorRoute = location.pathname === "/gpts/new" || /^\/gpts\/[^/]+\/edit$/.test(location.pathname);

  useEffect(() => {
    if (!app.isAuthenticated || app.requiresPasswordChange || app.bootstrapping || app.chats.length === 0) {
      return;
    }

    if (app.isStudent) {
      if (!location.pathname.startsWith("/learning") && !location.pathname.startsWith("/library")) {
        navigate("/learning", { replace: true });
      }
      return;
    }

    const fallbackChatId = app.activeChatId ?? app.chats[0]?.id;
    if (!fallbackChatId) {
      return;
    }

    if (location.pathname === "/" || location.pathname === "/login") {
      navigate(`/chats/${fallbackChatId}`, { replace: true });
      return;
    }

    if (currentChatId && !app.chats.some((chat) => chat.id === currentChatId)) {
      navigate(`/chats/${fallbackChatId}`, { replace: true });
    }
  }, [app.activeChatId, app.bootstrapping, app.chats, app.isAuthenticated, app.requiresPasswordChange, location.pathname, navigate]);

  if (!app.authReady || app.authLoading) {
    return <div className="auth-screen"><div className="auth-card"><p>Loading session...</p></div></div>;
  }

  if (!app.isAuthenticated) {
    return <LoginPage loading={app.authLoading} error={app.authError} onSubmit={(username, password) => app.login(username, password).then(() => undefined)} />;
  }

  if (!app.currentUser) {
    return null;
  }

  if (app.requiresPasswordChange) {
    return (
      <PasswordChangePage
        user={app.currentUser}
        loading={app.passwordChanging}
        error={app.authError}
        onSubmit={(currentPassword, newPassword, confirmPassword) => app.changePassword(currentPassword, newPassword, confirmPassword).then(() => undefined)}
        onLogout={app.logout}
      />
    );
  }

  async function openPreferences(tab: PreferencesTab = "general") {
    setPreferencesTab(tab);
    await Promise.all([app.loadSettings(), app.loadPersonalization()]);
    if (tab === "filter") {
      await app.loadGlobalFilters();
    }
  }

  async function handleCreateChat() {
    const chat = await app.createChat();
    navigate(`/chats/${chat.id}`);
  }

  function handleCreateGpt() {
    navigate("/gpts/new");
  }

  async function handleSelectChat(chatId: string) {
    await app.ensureChatLoaded(chatId);
    navigate(`/chats/${chatId}`);
  }

  async function handleSelectGpt(gptId: string) {
    await app.ensureGptChatLoaded(gptId);
    navigate(`/gpts/${gptId}/chat`);
  }

  async function handleRenameChat(chatId: string, chatName: string) {
    await app.renameChat(chatId, chatName);
  }

  async function handleArchiveChat(chatId: string) {
    const fallbackChatId = await app.archiveChat(chatId);
    if (fallbackChatId) {
      navigate(`/chats/${fallbackChatId}`);
      return;
    }
    navigate("/");
  }

  async function handleDeleteChat(chatId: string) {
    const fallbackChatId = await app.deleteChat(chatId);
    if (fallbackChatId) {
      navigate(`/chats/${fallbackChatId}`);
      return;
    }
    navigate("/");
  }

  async function handleDeleteGpt(gptId: string) {
    await app.deleteGpt(gptId);
    if (currentGptId === gptId) {
      navigate(app.activeChatId ? `/chats/${app.activeChatId}` : "/");
    }
  }

  const sidebar = (
    <Sidebar
      chats={app.chats}
      gpts={app.gpts}
      activeChatId={currentGptId ?? app.activeChatId}
      activeView={activeView}
      currentUser={app.currentUser}
      canUseStandardChat={app.canUseStandardChat}
      canUseGpts={app.canUseGpts}
      canUseLibrary
      onCreateGpt={handleCreateGpt}
      onCreateChat={() => void handleCreateChat()}
      onOpenLearning={() => navigate("/learning")}
      onOpenLibrary={() => navigate("/library")}
      onOpenAdmin={() => navigate("/admin")}
      onOpenArchive={() => void openPreferences("archive")}
      onOpenInfo={() => setInfoOpen(true)}
      onOpenHelp={() => setHelpOpen(true)}
      onOpenPreferences={(tab) => void openPreferences(tab ?? "settings")}
      onOpenChangePassword={() => setPasswordDialogOpen(true)}
      onLogout={() => void app.logout()}
      onSelectChat={(chatId) => void handleSelectChat(chatId)}
      onSelectGpt={(gptId) => void handleSelectGpt(gptId)}
      onRenameChat={(chatId, chatName) => void handleRenameChat(chatId, chatName)}
      onArchiveChat={(chatId) => void handleArchiveChat(chatId)}
      onOpenChatFilter={(chat) => {
        setChatFilterChatId(chat.id);
        void app.loadChatFilters(chat.id);
      }}
      onDownloadChat={(chatId) => void app.downloadChat(chatId)}
      onDeleteChat={(chatId) => void handleDeleteChat(chatId)}
      onEditGpt={(gptId) => navigate(`/gpts/${gptId}/edit`)}
      onClearGpt={(gptId) => void app.clearGptChat(gptId)}
      onDownloadGpt={(gptId) => void app.downloadGptChat(gptId)}
      onDeleteGpt={(gptId) => void handleDeleteGpt(gptId)}
    />
  );

  const gptEditorRoutes = (
    <Routes>
      <Route
        path="/gpts/new"
        element={
          <GptEditorPage
            settings={app.settings}
            libraryFiles={app.library?.files ?? []}
            attachmentRules={app.attachmentRules}
            onEnsureLibrary={() => app.loadLibrary().then(() => undefined)}
            onCreate={app.createGpt}
            onUpdate={app.updateGpt}
            onPreview={app.previewGptMessage}
          />
        }
      />
      <Route
        path="/gpts/:gptId/edit"
        element={
          <GptEditorRoute
            settings={app.settings}
            libraryFiles={app.library?.files ?? []}
            attachmentRules={app.attachmentRules}
            onEnsureLibrary={() => app.loadLibrary().then(() => undefined)}
            onCreate={app.createGpt}
            onUpdate={app.updateGpt}
            onPreview={app.previewGptMessage}
          />
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );

  if (isGptEditorRoute) {
    if (!app.canUseGpts) {
      return <Navigate to="/learning" replace />;
    }
    return gptEditorRoutes;
  }

  return (
    <>
      <AppShell
        sidebar={sidebar}
        assistantMode={activeGptChat?.gpt.assistant_mode ?? app.assistantMode}
        availableModes={
          currentGptId
            ? [activeGptChat?.gpt.assistant_mode ?? "simple"]
            : app.isStudent
              ? ["simple"]
              : (app.settings?.available_assistant_modes ?? ["simple", "refine", "thinking"])
        }
        onAssistantModeChange={currentGptId || app.isStudent ? (() => undefined) : app.setAssistantMode}
        assistantModeLocked={Boolean(currentGptId) || app.isStudent}
        headerRight={
          currentGptId ? (
            <div className="header-gpt-badge" aria-label="Active GPT">
              <span className="header-gpt-badge-icon-shell" aria-hidden="true">
                <Icon name="sparkles" className="header-gpt-badge-icon" />
              </span>
              <span className="header-gpt-badge-copy">
                <span className="header-gpt-badge-label">GPT Mode</span>
                <strong className="header-gpt-badge-name">{activeGptChat?.gpt.name ?? "Untitled GPT"}</strong>
              </span>
            </div>
          ) : undefined
        }
        content={
          <Routes>
            <Route
              path="/gpts/:gptId/chat"
              element={
                app.canUseGpts ? <GptChatRoute app={app} /> : <Navigate to="/learning" replace />
              }
            />
            <Route
              path="/learning"
              element={
                <LearningPathsPage
                  role={app.currentUser.role}
                  paths={app.learningPaths}
                  libraryFiles={app.library?.files ?? []}
                  loading={app.learningLoading}
                  saving={app.learningSaving}
                  error={app.learningError}
                  canAuthor={app.canAuthorLearningPaths}
                  onLoad={async () => {
                    if (!app.library) {
                      await app.loadLibrary(false);
                    }
                    await app.loadLearningPaths();
                  }}
                  learningProfile={app.learningProfile}
                  learningProfileLoading={app.learningProfileLoading}
                  learningProfileSaving={app.learningProfileSaving}
                  learningProfileError={app.learningProfileError}
                  learningProfileSuccess={app.learningProfileSuccess}
                  onLoadLearningProfile={() => void app.loadLearningProfile()}
                  onSaveLearningPreferences={(payload) => app.saveLearningPreferences(payload).then(() => undefined)}
                  onSaveLearningContext={(payload) => app.saveLearningContext(payload).then(() => undefined)}
                  onCreateLearningGoal={(payload) => app.createLearningGoal(payload).then(() => undefined)}
                  onUpdateLearningGoal={(goalId, payload) => app.updateLearningGoal(goalId, payload).then(() => undefined)}
                  onDeleteLearningGoal={(goalId) => app.deleteLearningGoal(goalId).then(() => undefined)}
                  onCreatePath={app.createLearningPath}
                  onUpdatePath={app.updateLearningPath}
                  onDeletePath={app.deleteLearningPath}
                  onCreateModule={app.createLearningModule}
                  onUpdateModule={app.updateLearningModule}
                  onDeleteModule={app.deleteLearningModule}
                  onReorderModules={app.reorderLearningModules}
                  onCreateLesson={app.createLearningLesson}
                  onUpdateLesson={app.updateLearningLesson}
                  onDeleteLesson={app.deleteLearningLesson}
                  onReorderLessons={app.reorderLearningLessons}
                />
              }
            />
            <Route
              path="/library"
              element={
                <LibraryPage
                  library={app.library}
                  loading={app.libraryLoading}
                  error={app.libraryError}
                  showOtherUsers={app.libraryIncludeOtherUsers}
                  uploading={app.uploading}
                  busyFileIds={app.busyFileIds}
                  onLoad={(includeOtherUsers) => void app.loadLibrary(includeOtherUsers)}
                  onToggleShowOtherUsers={(nextValue) => void app.loadLibrary(nextValue)}
                  onToggleFile={(file) => void app.toggleLibraryFile(file)}
                  onDeleteFile={(fileId) => void app.deleteLibraryFile(fileId)}
                  onUploadFiles={(files, tagsByFile) => app.uploadLibraryFiles(files, tagsByFile)}
                />
              }
            />
            <Route
              path="/admin"
              element={
                app.currentUser.role === "admin" ? (
                  <AdminPage
                    currentUser={app.currentUser}
                    users={app.adminUsers}
                    loading={app.adminLoading}
                    error={app.adminError}
                    busyUserIds={app.adminBusyUserIds}
                    onLoad={() => void app.loadAdminUsers()}
                    onCreateUser={(payload) => app.createAdminUser(payload).then(() => undefined)}
                    onUpdateUser={(userId, payload) => app.updateAdminUser(userId, payload).then(() => undefined)}
                    onDeleteUser={(userId) => app.deleteAdminUser(userId).then(() => undefined)}
                  />
                ) : (
                  <Navigate to="/" replace />
                )
              }
            />
            <Route
              path="/chats/:chatId"
              element={
                app.canUseStandardChat ? (
                  <ChatRoute
                    loading={app.loadingMessages}
                    error={app.appError}
                    messages={app.activeMessages}
                    sending={app.sending}
                    assistantMode={app.assistantMode}
                    attachmentRules={app.attachmentRules}
                    onOpenChat={(chatId) => void app.ensureChatLoaded(chatId)}
                    onSend={app.sendMessage}
                  />
                ) : (
                  <Navigate to="/learning" replace />
                )
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        }
      />

      {preferencesTab ? (
        <PreferencesDialog
          initialTab={preferencesTab}
          archivedChats={app.archivedChats}
          settingsDraft={app.settingsDraft}
          personalizationDraft={app.personalizationDraft}
          availableModes={app.settings?.available_assistant_modes ?? ["simple", "refine", "thinking"]}
          globalFilterTags={app.globalTagFilters}
          loading={app.settingsLoading}
          saving={app.settingsSaving}
          personalizationLoading={app.personalizationLoading}
          personalizationSaving={app.personalizationSaving}
          filterLoading={app.filterLoading}
          filterError={app.filterError}
          filterBusyKeys={app.filterBusyKeys}
          error={app.settingsError}
          success={app.settingsSuccess}
          personalizationError={app.personalizationError}
          personalizationSuccess={app.personalizationSuccess}
          onClose={() => setPreferencesTab(null)}
          onDownloadChat={(chatId) => void app.downloadChat(chatId)}
          onUnarchiveChat={(chatId) => void app.unarchiveChat(chatId)}
          onDeleteChat={(chatId) => void handleDeleteChat(chatId)}
          onFieldChange={app.updateSettingsDraft}
          onPersonalizationFieldChange={app.updatePersonalizationDraft}
          onSaveSettings={() => void app.saveSettings()}
          onSavePersonalization={() => void app.savePersonalization()}
          onOpenFilterTab={() => void app.loadGlobalFilters()}
          onToggleGlobalTag={(tag, isEnabled) => void app.toggleGlobalTagFilter(tag.tag, isEnabled)}
        />
      ) : null}

      {chatFilterChatId ? (
        <ChatFilterDialog
          chatName={app.chats.find((chat) => chat.id === chatFilterChatId)?.chat_name ?? "Chat"}
          files={app.chatFileFiltersByChat[chatFilterChatId] ?? []}
          tags={app.chatTagFiltersByChat[chatFilterChatId] ?? []}
          loading={app.filterLoading && !(app.chatFileFiltersByChat[chatFilterChatId] && app.chatTagFiltersByChat[chatFilterChatId])}
          error={app.filterError}
          busyKeys={app.filterBusyKeys}
          onClose={() => setChatFilterChatId(null)}
          onToggleTag={(tag, isEnabled) => void app.toggleChatTagFilter(chatFilterChatId, tag.tag, isEnabled)}
          onToggleFile={(file, isEnabled) => void app.toggleChatFileFilter(chatFilterChatId, file.file_id, isEnabled)}
        />
      ) : null}

      {passwordDialogOpen ? (
        <Dialog
          title="Change Password"
          onClose={() => setPasswordDialogOpen(false)}
          className="dialog-wide"
          actions={null}
        >
          <PasswordChangePage
            user={app.currentUser}
            loading={app.passwordChanging}
            error={app.authError}
            requiresCurrentPassword
            compact
            showLogout={false}
            onSubmit={async (currentPassword, newPassword, confirmPassword) => {
              await app.changePassword(currentPassword, newPassword, confirmPassword);
              setPasswordDialogOpen(false);
            }}
            onLogout={app.logout}
          />
        </Dialog>
      ) : null}

      {infoOpen ? (
        <Dialog
          title="Info"
          onClose={() => setInfoOpen(false)}
          className="dialog-wide info-dialog"
          actions={null}
        >
          <div className="info-panel">
            <section className="info-panel-section">
              <h4>Status</h4>
              <div className="info-table">
                {[
                  ["Backend", "Web API orchestration, auth, and chat handling."],
                  ["Retriever", "Retrieval, prompt assembly, and answer generation."],
                  ["Embedder", "Processes library files and maintains embeddings."],
                  ["OCR Scanner", "Extracts text from supported images when needed."],
                  ["Vector Db", "Stores nearest-neighbor retrieval vectors."],
                  ["Postgres", "Stores users, chats, file metadata, and settings."],
                ].map(([label, description]) => (
                  <div className="info-row" key={label}>
                    <div className="info-copy">
                      <strong>{label}</strong>
                      <span>{description}</span>
                    </div>
                    <span className="status-pill enabled">Active</span>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </Dialog>
      ) : null}

      {helpOpen ? (
        <Dialog title="Help" onClose={() => setHelpOpen(false)} className="dialog-wide help-dialog" actions={null}>
          <div className="info-panel">
            <section className="info-panel-section">
              <h4>Authentication</h4>
              <p>Sign in with a provisioned user. New or reset users must change the default password before entering the app.</p>
            </section>
            <section className="info-panel-section">
              <h4>Chat Usage</h4>
              <p>Create chats from the sidebar, use one chat per topic when helpful, and open the chat menu to rename, download, archive, or delete a chat.</p>
              <p>Type in the bottom composer and press Enter to send or Shift+Enter for a new line.</p>
            </section>
          </div>
        </Dialog>
      ) : null}
    </>
  );
}

type ChatRouteProps = {
  messages: ReturnType<typeof useChatApp>["activeMessages"];
  loading: boolean;
  sending: boolean;
  error: string | null;
  assistantMode: ReturnType<typeof useChatApp>["assistantMode"];
  attachmentRules: ReturnType<typeof useChatApp>["attachmentRules"];
  onOpenChat: (chatId: string) => void;
  onSend: ReturnType<typeof useChatApp>["sendMessage"];
};

function ChatRoute({
  messages,
  loading,
  sending,
  error,
  assistantMode,
  attachmentRules,
  onOpenChat,
  onSend,
}: ChatRouteProps) {
  const { chatId } = useParams();

  useEffect(() => {
    if (chatId) {
      onOpenChat(chatId);
    }
  }, [chatId, onOpenChat]);

  return (
    <ChatView
      messages={messages}
      sending={sending}
      loadingMessages={loading}
      error={error}
      assistantMode={assistantMode}
      attachmentRules={attachmentRules}
      onSend={onSend}
    />
  );
}

function GptEditorRoute(props: ComponentProps<typeof GptEditorPage>) {
  const params = useParams<{ gptId: string }>();
  return <GptEditorPage {...props} gptId={params.gptId} />;
}

function GptChatRoute({
  app,
}: {
  app: ReturnType<typeof useChatApp>;
}) {
  const params = useParams<{ gptId: string }>();
  const gptId = params.gptId ?? "";

  useEffect(() => {
    if (gptId) {
      void app.ensureGptChatLoaded(gptId);
    }
  }, [app, gptId]);

  const gptChat = app.gptChatsById[gptId];

  if (!gptId) {
    return <Navigate to="/" replace />;
  }

  return (
    <ChatView
      messages={gptChat?.messages ?? []}
      sending={app.sending}
      loadingMessages={app.loadingMessages}
      error={app.appError}
      assistantMode={gptChat?.gpt.assistant_mode ?? "simple"}
      attachmentRules={app.attachmentRules}
      onSend={(value, attachments) => app.sendGptMessage(gptId, value, attachments)}
    />
  );
}

export function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}
