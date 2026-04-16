import { useEffect, useState, type ComponentProps } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import { apiClient } from "../api/client";
import { AdminPage } from "../components/admin/AdminPage";
import { ChatView } from "../components/chat/ChatView";
import { Dialog } from "../components/common/Dialog";
import { Icon } from "../components/common/Icons";
import { ChatFilterDialog } from "../components/filters/ChatFilterDialog";
import { AppShell } from "../components/layout/AppShell";
import { LibraryPage } from "../components/library/LibraryPage";
import { CoursesPage } from "../components/courses/CoursesPage";
import { LearningPathsPage } from "../components/learning/LearningPathsPage";
import { PreferencesDialog } from "../components/preferences/PreferencesDialog";
import { Sidebar } from "../components/sidebar/Sidebar";
import { useChatApp } from "../hooks/useChatApp";
import { LoginPage } from "../pages/LoginPage";
import { LearningNodePage } from "../pages/LearningNodePage";
import { PasswordChangePage } from "../pages/PasswordChangePage";
import { GptEditorPage } from "../pages/GptEditorPage";

type PreferencesTab = "general" | "personalization" | "settings" | "filter" | "archive";

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

function AppRoutes() {
  const app = useChatApp();
  const navigate = useNavigate();
  const location = useLocation();
  const currentChatId = location.pathname.startsWith("/chats/") ? location.pathname.split("/")[2] ?? null : null;
  const currentGptId = location.pathname.startsWith("/gpts/") && location.pathname.endsWith("/chat") ? location.pathname.split("/")[2] ?? null : null;
  const currentLearningNodeSessionId = location.pathname.startsWith("/learning/nodes/") ? location.pathname.split("/")[3] ?? null : null;
  const activeView = location.pathname.startsWith("/learning/nodes/")
    ? "learning-node"
    : location.pathname.startsWith("/learning")
      ? "learning"
    : location.pathname.startsWith("/courses")
      ? "courses"
    : location.pathname.startsWith("/library")
      ? "library"
      : location.pathname.startsWith("/admin")
        ? "admin"
        : currentGptId
          ? "gpt"
          : "chat";
  const activeGptChat = currentGptId ? app.gptChatsById[currentGptId] ?? null : null;
  const showAssistantModeDropdown = activeView === "chat";
  const [preferencesTab, setPreferencesTab] = useState<PreferencesTab | null>(null);
  const [infoOpen, setInfoOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false);
  const [chatFilterChatId, setChatFilterChatId] = useState<string | null>(null);
  const [systemStatusLoading, setSystemStatusLoading] = useState(false);
  const [systemStatusError, setSystemStatusError] = useState<string | null>(null);
  const [systemStatus, setSystemStatus] = useState<Array<{ label: string; description: string; status: string; detail: string }>>([]);
  const isGptEditorRoute = location.pathname === "/gpts/new" || /^\/gpts\/[^/]+\/edit$/.test(location.pathname);

  useEffect(() => {
    if (!app.isAuthenticated || app.requiresPasswordChange || app.bootstrapping || app.chats.length === 0) {
      return;
    }

    if (app.isStudent) {
      if (!location.pathname.startsWith("/learning") && !location.pathname.startsWith("/library") && !location.pathname.startsWith("/courses")) {
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

  useEffect(() => {
    if (!infoOpen) {
      return;
    }
    let cancelled = false;
    setSystemStatusLoading(true);
    setSystemStatusError(null);
    void apiClient.getSystemStatus()
      .then((payload) => {
        if (cancelled) {
          return;
        }
        setSystemStatus(
          payload.services.map((service) => ({
            label: service.label,
            description: service.description,
            status: service.status,
            detail: service.detail,
          })),
        );
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        setSystemStatusError(error instanceof Error ? error.message : "Failed to load system status");
        setSystemStatus([]);
      })
      .finally(() => {
        if (!cancelled) {
          setSystemStatusLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [infoOpen]);

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

  async function handleSelectLearningNodeSession(sessionId: string) {
    navigate(`/learning/nodes/${sessionId}`);
  }

  async function handleArchiveLearningNodeSession(sessionId: string) {
    await app.archiveLearningNodeSession(sessionId);
    if (currentLearningNodeSessionId === sessionId) {
      navigate("/courses");
    }
  }

  async function handleDeleteLearningNodeSession(sessionId: string) {
    await app.deleteLearningNodeSession(sessionId);
    if (currentLearningNodeSessionId === sessionId) {
      navigate("/courses");
    }
  }

  const sidebar = (
    <Sidebar
      chats={app.chats}
      gpts={app.gpts}
      learningNodeSessions={app.learningNodeSessions}
      activeChatId={currentGptId ?? app.activeChatId}
      activeLearningNodeSessionId={currentLearningNodeSessionId}
      activeView={activeView}
      currentUser={app.currentUser}
      canUseStandardChat={app.canUseStandardChat}
      canUseGpts={app.canUseGpts}
      canUseLibrary
      onCreateGpt={handleCreateGpt}
      onCreateChat={() => void handleCreateChat()}
      onOpenLearning={() => navigate("/learning")}
      onOpenCourses={() => navigate("/courses")}
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
      onSelectLearningNodeSession={(sessionId) => void handleSelectLearningNodeSession(sessionId)}
      onArchiveLearningNodeSession={(sessionId) => void handleArchiveLearningNodeSession(sessionId)}
      onResetLearningNodeSession={(sessionId) => void app.resetLearningNodeSession(sessionId)}
      onDownloadLearningNodeSession={(sessionId) => void app.downloadLearningNodeSession(sessionId)}
      onDeleteLearningNodeSession={(sessionId) => void handleDeleteLearningNodeSession(sessionId)}
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
          showAssistantModeDropdown ? undefined : activeView === "learning-node" ? (
            <div />
          ) : app.isStudent ? (
            <div className="header-learning-badge" aria-label="Learning mode">
              <span className="header-learning-badge-icon-shell" aria-hidden="true">
                <Icon name="academic-hat" className="header-learning-badge-icon" />
              </span>
              <span className="header-learning-badge-copy">
                <span className="header-learning-badge-label">Mode</span>
                <strong className="header-learning-badge-name">Learning</strong>
              </span>
            </div>
          ) : currentGptId ? (
            <div className="header-gpt-badge" aria-label="Active GPT">
              <span className="header-gpt-badge-icon-shell" aria-hidden="true">
                <Icon name="sparkles" className="header-gpt-badge-icon" />
              </span>
              <span className="header-gpt-badge-copy">
                <span className="header-gpt-badge-label">GPT Mode</span>
                <strong className="header-gpt-badge-name">{activeGptChat?.gpt.name ?? "Untitled GPT"}</strong>
              </span>
            </div>
          ) : (
            <div />
          )
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
                  error={app.learningError}
                  onLoad={async () => {
                    await Promise.all([
                      app.loadLearningProfile(),
                      app.loadKsaProfile(),
                      app.loadKsaDrillAttempts(),
                      app.loadDiagnosticCatalog(),
                      app.loadDiagnosticAttempts(),
                      app.loadLearningStateChecks(),
                    ]);
                  }}
                  learningProfile={app.learningProfile}
                  learningProfileLoading={app.learningProfileLoading}
                  learningProfileSaving={app.learningProfileSaving}
                  learningProfileError={app.learningProfileError}
                  learningProfileSuccess={app.learningProfileSuccess}
                  ksaProfile={app.ksaProfile}
                  ksaLoading={app.ksaLoading}
                  ksaError={app.ksaError}
                  ksaAssessmentDefinition={app.ksaAssessmentDefinition}
                  ksaAssessmentAttempt={app.ksaAssessmentAttempt}
                  ksaDrillAttempt={app.ksaDrillAttempt}
                  ksaDrillAttempts={app.ksaDrillAttempts}
                  ksaAssessmentSaving={app.ksaAssessmentSaving}
                  currentUserDisplayName={app.currentUser.displayname}
                  onLoadLearningProfile={() => void app.loadLearningProfile()}
                  onLoadKsaProfile={() => app.loadKsaProfile()}
                  onLoadKsaAssessmentDefinition={() => app.loadKsaAssessmentDefinition()}
                  onLoadLatestKsaAssessmentAttempt={() => app.loadLatestKsaAssessmentAttempt()}
                  onStartKsaAssessment={() => app.startKsaAssessment()}
                  onSaveKsaAssessmentAnswers={(attemptId, answers) => app.saveKsaAssessmentAnswers(attemptId, answers)}
                  onCompleteKsaAssessment={(attemptId) => app.completeKsaAssessment(attemptId)}
                  onClassifyKsaDrillTopic={(sourceTopicInput) => app.classifyKsaDrillTopic(sourceTopicInput)}
                  onLoadLatestKsaDrillAttempt={() => app.loadLatestKsaDrillAttempt()}
                  onLoadKsaDrillAttempts={() => app.loadKsaDrillAttempts()}
                  onStartKsaDrillAttempt={(payload) => app.startKsaDrillAttempt(payload)}
                  onSaveKsaDrillAnswers={(attemptId, answers) => app.saveKsaDrillAnswers(attemptId, answers)}
                  onCompleteKsaDrillAttempt={(attemptId) => app.completeKsaDrillAttempt(attemptId)}
                  onSaveLearningPreferences={(payload) => app.saveLearningPreferences(payload).then(() => undefined)}
                  onSaveLearningContext={(payload) => app.saveLearningContext(payload).then(() => undefined)}
                  onCreateLearningGoal={(payload) => app.createLearningGoal(payload).then(() => undefined)}
                  onUpdateLearningGoal={(goalId, payload) => app.updateLearningGoal(goalId, payload).then(() => undefined)}
                  onDeleteLearningGoal={(goalId) => app.deleteLearningGoal(goalId).then(() => undefined)}
                  diagnosticDefinitions={app.diagnosticDefinitions}
                  diagnosticAttempt={app.diagnosticAttempt}
                  diagnosticAttempts={app.diagnosticAttempts}
                  diagnosticResult={app.diagnosticResult}
                  diagnosticLoading={app.diagnosticLoading}
                  diagnosticSaving={app.diagnosticSaving}
                  diagnosticError={app.diagnosticError}
                  learningStateChecks={app.learningStateChecks}
                  learningStateSaving={app.learningStateSaving}
                  learningStateError={app.learningStateError}
                  onLoadDiagnostics={() => Promise.all([app.loadDiagnosticCatalog(), app.loadDiagnosticAttempts()])}
                  onStartDiagnosticAttempt={() => app.startDiagnosticAttempt().then(() => undefined)}
                  onSaveDiagnosticAnswers={(attemptId, diagnosticType, answers) => app.saveDiagnosticAnswers(attemptId, diagnosticType, answers).then(() => undefined)}
                  onCompleteDiagnosticAttempt={(attemptId) => app.completeDiagnosticAttempt(attemptId).then(() => undefined)}
                  onDeleteDiagnosticAttempt={(attemptId) => app.deleteDiagnosticAttempt(attemptId).then(() => undefined)}
                  onOpenDiagnosticAttempt={app.openDiagnosticAttempt}
                  onCreateLearningStateCheck={(payload) => app.createLearningStateCheck(payload).then(() => undefined)}
                />
              }
            />
            <Route
              path="/learning/nodes/:sessionId"
              element={
                <LearningNodeRoute
                  app={app}
                />
              }
            />
            <Route
              path="/courses"
              element={
                <CoursesPage
                  courses={app.courses}
                  learningNodeSessions={app.learningNodeSessions}
                  loading={app.coursesLoading}
                  error={app.coursesError}
                  importing={app.coursesImporting}
                  canCreateGlobal={app.canCreateGlobalCourses}
                  canUploadPaths={app.canAuthorLearningPaths}
                  currentUserId={app.currentUser.id}
                  onLoad={app.loadCourses}
                  onLoadDetails={(courseId) => app.getLearningPathDetails(courseId)}
                  onUpdateNodeProgress={(courseId, nodeId, payload) => app.updateLearningNodeProgress(courseId, nodeId, payload)}
                  onImport={app.importCourseFiles}
                  onDownloadTemplate={app.downloadCourseTemplate}
                  onStartContinue={async (courseId, nodeId) => {
                    const session = await app.ensureLearningNodeSession(courseId, nodeId);
                    if (!session) {
                      return;
                    }
                    navigate(`/learning/nodes/${session.id}`);
                  }}
                  onToggleArchived={(courseId, nextArchived) =>
                    app
                      .updateLearningPath(courseId, { status: nextArchived ? "archived" : "published" })
                      .then(() => app.loadCourses())
                      .then(() => undefined)
                  }
                  onDeleteCourse={(courseId) =>
                    app
                      .deleteLearningPath(courseId)
                      .then(() => app.loadCourses())
                      .then(() => undefined)
                  }
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
                    onFeedback={(payload) => app.submitExplanationFeedback(payload).then(() => undefined)}
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
          archivedLearningNodeSessions={app.archivedLearningNodeSessions}
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
          onDownloadLearningNodeSession={(sessionId) => void app.downloadLearningNodeSession(sessionId)}
          onUnarchiveChat={(chatId) => void app.unarchiveChat(chatId)}
          onUnarchiveLearningNodeSession={(sessionId) => void app.unarchiveLearningNodeSession(sessionId)}
          onDeleteChat={(chatId) => void handleDeleteChat(chatId)}
          onDeleteLearningNodeSession={(sessionId) => void app.deleteLearningNodeSession(sessionId)}
          onFieldChange={app.updateSettingsDraft}
          onPersonalizationFieldChange={app.updatePersonalizationDraft}
          onSaveSettings={() => void app.saveSettings()}
          onSavePersonalization={() => void app.savePersonalization()}
          onOpenFilterTab={() => void app.loadGlobalFilters()}
          onToggleGlobalTag={(tag, isEnabled) => void app.toggleGlobalTagFilter(tag.tag, isEnabled)}
          isStudent={app.isStudent}
          onOpenLearningProfile={() => navigate("/learning?tab=profile")}
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
                {systemStatusLoading ? <div className="info-row"><div className="info-copy"><strong>Loading status...</strong></div></div> : null}
                {systemStatusError ? <div className="info-row"><div className="info-copy"><strong>Error</strong><span>{systemStatusError}</span></div><span className="status-pill disabled">Unavailable</span></div> : null}
                {systemStatus.map((item) => (
                  <div className="info-row" key={item.label}>
                    <div className="info-copy">
                      <strong>{item.label}</strong>
                      <span>{item.description}</span>
                      <span>{item.detail}</span>
                    </div>
                    <span className={`status-pill ${item.status === "ok" ? "enabled" : item.status === "warn" ? "warn" : "error"}`}>
                      {item.status === "ok" ? "Active" : item.status === "warn" ? "Warning" : "Error"}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </Dialog>
      ) : null}

      {helpOpen ? (
        <Dialog title="Help" onClose={() => setHelpOpen(false)} className="dialog-wide help-dialog" actions={null}>
          <div className="help-panel">
            <section className="help-card">
              <div className="help-card-head">
                <h4>Quick Start</h4>
                <span className="status-pill enabled">{app.currentUser.role.toUpperCase()}</span>
              </div>
              <ol className="help-list">
                <li>Use the left navigation to open Learning, Library, and role-specific areas.</li>
                {app.canUseStandardChat ? <li>Create a chat with `+ New chat` and keep one topic per chat for cleaner results.</li> : null}
                <li>Use the bottom input to send: `Enter` sends, `Shift+Enter` adds a new line.</li>
                <li>Use the chat menu (`...`) to rename, download, archive, or delete chats.</li>
              </ol>
            </section>

            {app.canUseStandardChat ? (
              <section className="help-card">
                <h4>Chat & Responses</h4>
                <ul className="help-list">
                  <li>Ask clear questions and include context for best grounded answers.</li>
                  <li>Upload up to {app.attachmentRules.maxFiles} files per message when needed.</li>
                  <li>Supported attachments:</li>
                </ul>
                <div className="chip-row">
                  {app.attachmentRules.allowedExtensions.map((extension) => (
                    <span key={extension} className={`library-extension-chip ${extensionTone(extension)}`}>{extension.toUpperCase()}</span>
                  ))}
                </div>
              </section>
            ) : null}

            <section className="help-card">
              <h4>Learning Page</h4>
              <ul className="help-list">
                <li>`Profile` tab: maintain learning context and goals.</li>
                <li>`Preferences` tab: set learning preferences and run diagnostics (LAA/MOA/LTA).</li>
                <li>`KSA` tab: review the big-map and run the full initial KSA assessment flow.</li>
              </ul>
            </section>

            <section className="help-card">
              <h4>Courses</h4>
              <ul className="help-list">
                <li>Use Courses to filter, sort, and review all learning paths.</li>
                <li>Import up to 5 course JSON files from the Add Paths dialog.</li>
                <li>Download the course JSON template to bootstrap new definitions.</li>
              </ul>
            </section>

            <section className="help-card">
              <h4>Library</h4>
              <ul className="help-list">
                <li>Use Library to manage files used for grounded retrieval.</li>
                <li>Toggle files to enable/disable retrieval without deleting them.</li>
                <li>Delete removes a file from storage and retrieval index.</li>
                <li>Common file types:</li>
              </ul>
              <div className="chip-row">
                {[".md", ".txt", ".html", ".htm", ".pdf", ".csv", ".png", ".jpg", ".jpeg", ".webp"].map((extension) => (
                  <span key={`library-${extension}`} className={`library-extension-chip ${extensionTone(extension)}`}>{extension.toUpperCase()}</span>
                ))}
              </div>
            </section>

            {app.isStudent ? (
              <section className="help-card">
                <h4>Student Scope</h4>
                <ul className="help-list">
                  <li>Students can use Learning and Library features.</li>
                  <li>Students do not access chat mode switching, admin user management, or global system settings.</li>
                </ul>
              </section>
            ) : null}

            {app.canUseGpts ? (
              <section className="help-card">
                <h4>GPTs</h4>
                <ul className="help-list">
                  <li>Create/edit GPTs to define custom instructions, settings, files, and tags.</li>
                  <li>Run GPT chats from the GPT list in the sidebar.</li>
                </ul>
              </section>
            ) : null}

            {app.canAuthorLearningPaths ? (
              <section className="help-card">
                <h4>Path Authoring</h4>
                <ul className="help-list">
                  <li>Create learning paths and organize modules/lessons in sequence.</li>
                  <li>Set status (`draft`, `published`, `archived`) to control visibility.</li>
                </ul>
              </section>
            ) : null}

            {app.currentUser.role === "admin" ? (
              <section className="help-card">
                <h4>Admin Features</h4>
                <ul className="help-list">
                  <li>Manage users (role, activation, password reset enforcement) in Admin.</li>
                  <li>Use Preferences to adjust global settings and global retrieval filters.</li>
                  <li>Review Info dialog for live service health (WebUI, Retriever, Embedder, Knowledge Base, Database).</li>
                </ul>
              </section>
            ) : null}
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
  onFeedback: (payload: { message_id?: number | null; rating: number; feedback_text: string; re_explain_requested: boolean }) => Promise<void>;
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
  onFeedback,
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
      onFeedback={onFeedback}
    />
  );
}

function LearningNodeRoute({
  app,
}: {
  app: ReturnType<typeof useChatApp>;
}) {
  const navigate = useNavigate();
  const params = useParams<{ sessionId: string }>();
  const sessionId = params.sessionId ?? "";
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [session, setSession] = useState<Awaited<ReturnType<typeof app.getLearningNodeSession>> | null>(null);
  const [learningPath, setLearningPath] = useState<Awaited<ReturnType<typeof app.getLearningPathDetails>> | null>(null);
  const [attempt, setAttempt] = useState<Awaited<ReturnType<typeof app.getLatestLearningNodeExecution>> | null>(null);
  const [pathLoading, setPathLoading] = useState(false);
  const [pathError, setPathError] = useState<string | null>(null);
  const [attemptLoading, setAttemptLoading] = useState(false);
  const [attemptError, setAttemptError] = useState<string | null>(null);
  const [milestoneFinishing, setMilestoneFinishing] = useState(false);
  const [assessmentFinishing, setAssessmentFinishing] = useState(false);
  const [assessmentRestarting, setAssessmentRestarting] = useState(false);
  const [guidedCompleting, setGuidedCompleting] = useState(false);
  const [guidedRestarting, setGuidedRestarting] = useState(false);
  const [lessonCompleting, setLessonCompleting] = useState(false);
  const [lessonClosing, setLessonClosing] = useState(false);

  const isStaleGeneratingAttempt = (attemptRecord: Awaited<ReturnType<typeof app.getLatestLearningNodeExecution>>) => {
    if (String(attemptRecord.status ?? "") !== "generating") {
      return false;
    }
    const startedAt = Date.parse(String(attemptRecord.started_at ?? ""));
    if (Number.isNaN(startedAt)) {
      return false;
    }
    return Date.now() - startedAt > 90_000;
  };

  const tryFallbackToCompletedAttempt = async (pathId: string, nodeId: string) => {
    try {
      const attempts = await app.listLearningNodeExecutionAttempts(pathId, nodeId, 20);
      const completed = attempts.find((item) => String(item.status) === "completed");
      if (completed) {
        setAttempt(completed);
        setAttemptError("Latest generation attempt is stalled. Showing the latest completed attempt.");
        return true;
      }
    } catch {
      // keep polling fallback silent
    }
    return false;
  };

  const pollAttemptUntilReady = async (pathId: string, nodeId: string, isCancelled?: () => boolean) => {
    const maxPollCycles = 120;
    for (let cycle = 0; cycle < maxPollCycles; cycle += 1) {
      if (isCancelled?.()) {
        return;
      }
      await new Promise((resolve) => window.setTimeout(resolve, 2500));
      if (isCancelled?.()) {
        return;
      }
      try {
        const latest = await app.getLatestLearningNodeExecution(pathId, nodeId);
        if (isCancelled?.()) {
          return;
        }
        setAttempt(latest);
        setAttemptError(null);
        if (isStaleGeneratingAttempt(latest)) {
          const switched = await tryFallbackToCompletedAttempt(pathId, nodeId);
          if (switched) {
            return;
          }
        }
        if (String(latest.status ?? "") !== "generating") {
          return;
        }
      } catch (pollError: unknown) {
        if (isCancelled?.()) {
          return;
        }
        setAttemptError(pollError instanceof Error ? pollError.message : "Failed to refresh learning node package");
        return;
      }
    }
    if (isCancelled?.()) {
      return;
    }
    setAttemptError("Package generation is taking longer than expected. Please keep this page open.");
  };

  useEffect(() => {
    if (!sessionId) {
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    setPathLoading(false);
    setPathError(null);
    setLearningPath(null);
    setAttemptLoading(false);
    setAttemptError(null);
    setAttempt(null);
    setMilestoneFinishing(false);
    setAssessmentFinishing(false);
    setAssessmentRestarting(false);
    setGuidedCompleting(false);
    setGuidedRestarting(false);
    setLessonCompleting(false);
    setLessonClosing(false);
    void (async () => {
      try {
        const payload = await app.getLearningNodeSession(sessionId, false);
        if (cancelled) {
          return;
        }
        setSession(payload);
        setLoading(false);
        setPathLoading(true);
        let details: Awaited<ReturnType<typeof app.getLearningPathDetails>> | null = null;
        try {
          details = await app.getLearningPathDetails(payload.learning_path_id);
        } catch (pathLoadError: unknown) {
          if (!cancelled) {
            setPathError(pathLoadError instanceof Error ? pathLoadError.message : "Failed to load learning node details");
          }
          return;
        } finally {
          if (!cancelled) {
            setPathLoading(false);
          }
        }
        if (cancelled || !details) {
          return;
        }
        setLearningPath(details);
        const node = details.nodes.find((item) => item.id === payload.node_id);
        if (!node) {
          setPathError("Node definition is missing for this learning session.");
          return;
        }
        if (node.type === "unlock_gate") {
          navigate("/courses", { replace: true });
          return;
        }
        setAttemptLoading(true);
        try {
          const latestAttempt = await app.getLatestLearningNodeExecution(payload.learning_path_id, payload.node_id);
          if (!cancelled) {
            setAttempt(latestAttempt);
            if (isStaleGeneratingAttempt(latestAttempt)) {
              void tryFallbackToCompletedAttempt(payload.learning_path_id, payload.node_id);
              return;
            }
            if (String(latestAttempt.status ?? "") === "generating") {
              void pollAttemptUntilReady(payload.learning_path_id, payload.node_id, () => cancelled);
            }
          }
        } catch {
          try {
            const started = await app.startLearningNodeExecution(payload.learning_path_id, payload.node_id, false);
            if (cancelled) {
              return;
            }
            setAttempt(started.attempt);
            if (String(started.attempt.status ?? "") === "generating") {
              void pollAttemptUntilReady(payload.learning_path_id, payload.node_id, () => cancelled);
            }
            if (started.auto_completed) {
              void app.loadLearningNodeSessions();
              const refreshedDetails = await app.getLearningPathDetails(payload.learning_path_id);
              if (!cancelled) {
                setLearningPath(refreshedDetails);
              }
            }
          } catch (attemptLoadError: unknown) {
            if (!cancelled) {
              setAttemptError(attemptLoadError instanceof Error ? attemptLoadError.message : "Failed to load learning node package");
            }
          }
        } finally {
          if (!cancelled) {
            setAttemptLoading(false);
          }
        }
      } catch (nextError: unknown) {
        if (!cancelled) {
          setError(nextError instanceof Error ? nextError.message : "Failed to load learning node session");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [navigate, sessionId]);

  if (!sessionId) {
    return <Navigate to="/courses" replace />;
  }

  const handleMilestoneFinish = async () => {
    if (!session) {
      return;
    }
    setMilestoneFinishing(true);
    try {
      await app.archiveLearningNodeSession(session.id);
      navigate(`/courses?course=${encodeURIComponent(session.learning_path_id)}`, { replace: true });
    } finally {
      setMilestoneFinishing(false);
    }
  };

  const handleAssessmentComplete = async (responses: Record<string, unknown>) => {
    if (!session || !attempt) {
      return;
    }
    setAssessmentFinishing(true);
    setAttemptError(null);
    try {
      const savedAttempt = await app.submitLearningNodeExecutionResponses(
        session.learning_path_id,
        session.node_id,
        attempt.attempt_id,
        responses,
      );
      setAttempt(savedAttempt);
      const completed = await app.completeLearningNodeExecution(
        session.learning_path_id,
        session.node_id,
        attempt.attempt_id,
      );
      setAttempt(completed.attempt);
      await app.loadLearningNodeSessions();
      const refreshedDetails = await app.getLearningPathDetails(session.learning_path_id);
      setLearningPath(refreshedDetails);
    } catch (nextError: unknown) {
      setAttemptError(nextError instanceof Error ? nextError.message : "Failed to complete assessment hook");
      throw nextError;
    } finally {
      setAssessmentFinishing(false);
    }
  };

  const handleAssessmentRestart = async () => {
    if (!session) {
      return;
    }
    setAssessmentRestarting(true);
    setAttemptError(null);
    try {
      const restarted = await app.startLearningNodeExecution(session.learning_path_id, session.node_id, true);
      setAttempt(restarted.attempt);
      if (String(restarted.attempt.status ?? "") === "generating") {
        void pollAttemptUntilReady(session.learning_path_id, session.node_id);
      }
    } catch (nextError: unknown) {
      setAttemptError(nextError instanceof Error ? nextError.message : "Failed to restart assessment hook");
      throw nextError;
    } finally {
      setAssessmentRestarting(false);
    }
  };

  const handleAssessmentStart = async () => {
    if (!session) {
      return;
    }
    if (session.status !== "created") {
      return;
    }
    try {
      const opened = await app.getLearningNodeSession(session.id, true);
      setSession(opened);
    } catch (nextError: unknown) {
      setAttemptError(nextError instanceof Error ? nextError.message : "Failed to set assessment in progress");
      throw nextError;
    }
  };

  const handleGuidedComplete = async (responses: Record<string, unknown>) => {
    if (!session || !attempt) {
      return;
    }
    setGuidedCompleting(true);
    setAttemptError(null);
    try {
      const savedAttempt = await app.submitLearningNodeExecutionResponses(
        session.learning_path_id,
        session.node_id,
        attempt.attempt_id,
        responses,
      );
      setAttempt(savedAttempt);
      const completed = await app.completeLearningNodeExecution(
        session.learning_path_id,
        session.node_id,
        attempt.attempt_id,
      );
      setAttempt(completed.attempt);
      await app.loadLearningNodeSessions();
      const refreshedDetails = await app.getLearningPathDetails(session.learning_path_id);
      setLearningPath(refreshedDetails);
    } catch (nextError: unknown) {
      setAttemptError(nextError instanceof Error ? nextError.message : "Failed to complete learning node");
      throw nextError;
    } finally {
      setGuidedCompleting(false);
    }
  };

  const handleGuidedRestart = async () => {
    if (!session) {
      return;
    }
    setGuidedRestarting(true);
    setAttemptError(null);
    try {
      const restarted = await app.startLearningNodeExecution(session.learning_path_id, session.node_id, true);
      setAttempt(restarted.attempt);
      if (String(restarted.attempt.status ?? "") === "generating") {
        void pollAttemptUntilReady(session.learning_path_id, session.node_id);
      }
      await app.loadLearningNodeSessions();
    } catch (nextError: unknown) {
      setAttemptError(nextError instanceof Error ? nextError.message : "Failed to restart learning node");
      throw nextError;
    } finally {
      setGuidedRestarting(false);
    }
  };

  const handleLessonClose = async () => {
    if (!session) {
      return;
    }
    setLessonClosing(true);
    try {
      await app.archiveLearningNodeSession(session.id);
      await app.loadLearningNodeSessions();
      navigate("/courses", { replace: true });
    } finally {
      setLessonClosing(false);
    }
  };

  const handleLessonComplete = async (responses: Record<string, unknown>) => {
    if (!session || !attempt) {
      return;
    }
    setLessonCompleting(true);
    setAttemptError(null);
    try {
      const savedAttempt = await app.submitLearningNodeExecutionResponses(
        session.learning_path_id,
        session.node_id,
        attempt.attempt_id,
        responses,
      );
      setAttempt(savedAttempt);
      const completed = await app.completeLearningNodeExecution(
        session.learning_path_id,
        session.node_id,
        attempt.attempt_id,
      );
      setAttempt(completed.attempt);
      const opened = await app.getLearningNodeSession(session.id, false);
      setSession(opened);
      await app.loadLearningNodeSessions();
      const refreshedDetails = await app.getLearningPathDetails(session.learning_path_id);
      setLearningPath(refreshedDetails);
    } catch (nextError: unknown) {
      setAttemptError(nextError instanceof Error ? nextError.message : "Failed to complete learning node");
      throw nextError;
    } finally {
      setLessonCompleting(false);
    }
  };

  return (
    <LearningNodePage
      loading={loading}
      error={error}
      session={session}
      learningPath={learningPath}
      pathLoading={pathLoading}
      pathError={pathError}
      attempt={attempt}
      attemptLoading={attemptLoading}
      attemptError={attemptError}
      onMilestoneFinish={() => {
        void handleMilestoneFinish();
      }}
      milestoneFinishing={milestoneFinishing}
      onAssessmentComplete={handleAssessmentComplete}
      assessmentFinishing={assessmentFinishing}
      onAssessmentRestart={handleAssessmentRestart}
      assessmentRestarting={assessmentRestarting}
      onAssessmentStart={handleAssessmentStart}
      onGuidedComplete={handleGuidedComplete}
      guidedCompleting={guidedCompleting}
      onGuidedRestart={handleGuidedRestart}
      guidedRestarting={guidedRestarting}
      onLessonComplete={handleLessonComplete}
      lessonCompleting={lessonCompleting}
      onLessonClose={handleLessonClose}
      lessonClosing={lessonClosing}
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
      onFeedback={(payload) => app.submitExplanationFeedback(payload).then(() => undefined)}
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
