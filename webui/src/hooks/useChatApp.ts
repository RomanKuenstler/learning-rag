import { useEffect, useMemo, useState } from "react";
import { apiClient, clearStoredAuthSession, getStoredAuthSession, setStoredAuthSession, subscribeAuthSession } from "../api/client";
import type {
  AdminUser,
  AssistantMode,
  AttachmentMeta,
  AuthSession,
  Chat,
  CourseImportResponse,
  CourseListItem,
  CourseSort,
  DiagnosticAttemptDetails,
  DiagnosticAttemptSummary,
  DiagnosticCatalog,
  DiagnosticDefinition,
  DiagnosticResult,
  ExplanationFeedback,
  FilterFile,
  FilterTag,
  Gpt,
  GptChat,
  GptPreviewRequest,
  GptUpsert,
  LibraryFile,
  LibraryResponse,
  LearningLesson,
  LearningGoal,
  KSAProfile,
  LearningProfileBundle,
  LearningProfileContext,
  LearningPreferences,
  LearningModule,
  LearningPath,
  LearningStateCheck,
  Message,
  Personalization,
  PersonalizationUpdate,
  Settings,
  SettingsUpdate,
} from "../types/chat";

const ACTIVE_CHAT_STORAGE_KEY = "local-rag-active-chat";
const DEFAULT_PERSONALIZATION: Personalization = {
  base_style: "default",
  warm: "default",
  enthusiastic: "default",
  headers_and_lists: "default",
  custom_instructions: "",
  nickname: "",
  occupation: "",
  more_about_user: "",
};

export const DEFAULT_GPT: GptUpsert = {
  name: "",
  description: "",
  instructions: "",
  assistant_mode: "simple",
  config: {
    personalization: {
      base_style: "default",
      warm: "default",
      enthusiastic: "default",
      headers_and_lists: "default",
    },
    settings: {
      chat_history_messages_count: 5,
      max_similarities: 8,
      min_similarities: 2,
      similarity_score_threshold: 0.7,
    },
    files_enabled: true,
    tags_enabled: true,
    file_settings: [],
    tag_settings: [],
  },
};

export const ATTACHMENT_MAX_FILES = 3;
export const ATTACHMENT_ALLOWED_EXTENSIONS = [".txt", ".md", ".html", ".htm", ".pdf", ".epub", ".csv", ".png", ".jpg", ".jpeg", ".webp"];

function createOptimisticMessage(
  chatId: string,
  role: "user" | "assistant",
  content: string,
  status: Message["status"],
  attachments: AttachmentMeta[] = [],
): Message {
  return {
    id: `temp-${role}-${crypto.randomUUID()}`,
    chat_id: chatId,
    role,
    content,
    status,
    has_attachments: attachments.length > 0,
    created_at: new Date().toISOString(),
    sources: [],
    attachments,
  };
}

function sortChats(chats: Chat[]) {
  return [...chats].sort((left, right) => right.updated_at.localeCompare(left.updated_at));
}

function sortGpts(gpts: Gpt[]) {
  return [...gpts].sort((left, right) => right.updated_at.localeCompare(left.updated_at));
}

function triggerJsonDownload(fileName: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  anchor.rel = "noopener";
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

function clearAppSessionState() {
  window.localStorage.removeItem(ACTIVE_CHAT_STORAGE_KEY);
}

function getPendingAssistantText(mode: AssistantMode) {
  if (mode === "refine") {
    return "Refining answer...";
  }
  if (mode === "thinking") {
    return "Planning, drafting, and refining...";
  }
  return "Thinking...";
}

export function useChatApp() {
  const [authReady, setAuthReady] = useState(false);
  const [authLoading, setAuthLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);
  const [authSession, setAuthSession] = useState<AuthSession | null>(getStoredAuthSession());
  const [passwordChanging, setPasswordChanging] = useState(false);
  const [adminUsers, setAdminUsers] = useState<AdminUser[]>([]);
  const [adminLoading, setAdminLoading] = useState(false);
  const [adminError, setAdminError] = useState<string | null>(null);
  const [adminBusyUserIds, setAdminBusyUserIds] = useState<number[]>([]);

  const [bootstrapping, setBootstrapping] = useState(false);
  const [chats, setChats] = useState<Chat[]>([]);
  const [gpts, setGpts] = useState<Gpt[]>([]);
  const [learningPaths, setLearningPaths] = useState<LearningPath[]>([]);
  const [learningLoading, setLearningLoading] = useState(false);
  const [learningError, setLearningError] = useState<string | null>(null);
  const [learningSaving, setLearningSaving] = useState(false);
  const [courses, setCourses] = useState<CourseListItem[]>([]);
  const [coursesLoading, setCoursesLoading] = useState(false);
  const [coursesError, setCoursesError] = useState<string | null>(null);
  const [coursesImporting, setCoursesImporting] = useState(false);
  const [learningProfile, setLearningProfile] = useState<LearningProfileBundle | null>(null);
  const [ksaProfile, setKsaProfile] = useState<KSAProfile | null>(null);
  const [ksaLoading, setKsaLoading] = useState(false);
  const [ksaError, setKsaError] = useState<string | null>(null);
  const [learningProfileLoading, setLearningProfileLoading] = useState(false);
  const [learningProfileSaving, setLearningProfileSaving] = useState(false);
  const [learningProfileError, setLearningProfileError] = useState<string | null>(null);
  const [learningProfileSuccess, setLearningProfileSuccess] = useState<string | null>(null);
  const [diagnosticCatalog, setDiagnosticCatalog] = useState<DiagnosticCatalog | null>(null);
  const [diagnosticDefinitions, setDiagnosticDefinitions] = useState<Record<"LAA" | "MOA" | "LTA", DiagnosticDefinition | null>>({ LAA: null, MOA: null, LTA: null });
  const [diagnosticAttempt, setDiagnosticAttempt] = useState<DiagnosticAttemptDetails | null>(null);
  const [diagnosticAttempts, setDiagnosticAttempts] = useState<DiagnosticAttemptSummary[]>([]);
  const [diagnosticResult, setDiagnosticResult] = useState<DiagnosticResult | null>(null);
  const [diagnosticLoading, setDiagnosticLoading] = useState(false);
  const [diagnosticSaving, setDiagnosticSaving] = useState(false);
  const [diagnosticError, setDiagnosticError] = useState<string | null>(null);
  const [learningStateChecks, setLearningStateChecks] = useState<LearningStateCheck[]>([]);
  const [learningStateSaving, setLearningStateSaving] = useState(false);
  const [learningStateError, setLearningStateError] = useState<string | null>(null);
  const [feedbackSaving, setFeedbackSaving] = useState(false);
  const [feedbackError, setFeedbackError] = useState<string | null>(null);
  const [archivedChats, setArchivedChats] = useState<Chat[]>([]);
  const [messagesByChat, setMessagesByChat] = useState<Record<string, Message[]>>({});
  const [gptChatsById, setGptChatsById] = useState<Record<string, GptChat>>({});
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);
  const [appError, setAppError] = useState<string | null>(null);
  const [library, setLibrary] = useState<LibraryResponse | null>(null);
  const [libraryLoading, setLibraryLoading] = useState(false);
  const [libraryError, setLibraryError] = useState<string | null>(null);
  const [libraryIncludeOtherUsers, setLibraryIncludeOtherUsers] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [busyFileIds, setBusyFileIds] = useState<number[]>([]);
  const [assistantMode, setAssistantMode] = useState<AssistantMode>("simple");
  const [settings, setSettings] = useState<Settings | null>(null);
  const [settingsDraft, setSettingsDraft] = useState<SettingsUpdate | null>(null);
  const [settingsLoading, setSettingsLoading] = useState(false);
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [settingsError, setSettingsError] = useState<string | null>(null);
  const [settingsSuccess, setSettingsSuccess] = useState<string | null>(null);
  const [personalization, setPersonalization] = useState<Personalization | null>(null);
  const [personalizationDraft, setPersonalizationDraft] = useState<PersonalizationUpdate | null>(null);
  const [personalizationLoading, setPersonalizationLoading] = useState(false);
  const [personalizationSaving, setPersonalizationSaving] = useState(false);
  const [personalizationError, setPersonalizationError] = useState<string | null>(null);
  const [personalizationSuccess, setPersonalizationSuccess] = useState<string | null>(null);
  const [globalFileFilters, setGlobalFileFilters] = useState<FilterFile[]>([]);
  const [globalTagFilters, setGlobalTagFilters] = useState<FilterTag[]>([]);
  const [chatFileFiltersByChat, setChatFileFiltersByChat] = useState<Record<string, FilterFile[]>>({});
  const [chatTagFiltersByChat, setChatTagFiltersByChat] = useState<Record<string, FilterTag[]>>({});
  const [filterLoading, setFilterLoading] = useState(false);
  const [filterError, setFilterError] = useState<string | null>(null);
  const [filterBusyKeys, setFilterBusyKeys] = useState<string[]>([]);

  useEffect(() => subscribeAuthSession(setAuthSession), []);

  useEffect(() => {
    void restoreSession();
  }, []);

  useEffect(() => {
    if (!authSession?.expires_at) {
      return undefined;
    }
    const expiresAt = new Date(authSession.expires_at).getTime();
    const remaining = expiresAt - Date.now();
    if (remaining <= 0) {
      void logout();
      return undefined;
    }
    const timeout = window.setTimeout(() => {
      void logout();
    }, remaining);
    return () => window.clearTimeout(timeout);
  }, [authSession?.expires_at]);

  async function restoreSession() {
    setAuthLoading(true);
    setAuthError(null);
    try {
      const stored = getStoredAuthSession();
      if (!stored?.token) {
        clearClientState();
        return;
      }
      const me = await apiClient.getMe();
      const nextSession: AuthSession = {
        token: stored.token,
        user: me.user,
        expires_at: me.expires_at,
        max_expires_at: me.max_expires_at,
      };
      setStoredAuthSession(nextSession);
      if (!me.user.force_password_change) {
        await bootstrap(nextSession);
      } else {
        clearAppState();
      }
    } catch (error) {
      clearStoredAuthSession();
      clearClientState(error instanceof Error ? error.message : null);
    } finally {
      setAuthReady(true);
      setAuthLoading(false);
    }
  }

  async function bootstrap(session = authSession) {
    if (!session?.token || session.user.force_password_change) {
      setBootstrapping(false);
      return;
    }
    setBootstrapping(true);
    setAppError(null);
    try {
      const isStudent = session.user.role === "student";
      const [chatList, archivedList, runtimeSettings, personalizationSettings, gptList, learning, declaredLearningProfile, ksa, diagnostics, attempts, stateChecks] = await Promise.all([
        isStudent ? Promise.resolve([]) : apiClient.listChats(),
        isStudent ? Promise.resolve([]) : apiClient.listArchivedChats(),
        apiClient.getSettings(),
        apiClient.getPersonalization(),
        isStudent ? Promise.resolve([]) : apiClient.listGpts(),
        apiClient.listLearningPaths(),
        apiClient.getLearningProfile(),
        apiClient.getKsaProfile(),
        apiClient.listDiagnosticDefinitions(),
        apiClient.listDiagnosticAttempts(),
        apiClient.listLearningStateChecks(),
      ]);
      setChats(sortChats(chatList));
      setGpts(gptList);
      setLearningPaths(learning.paths);
      setLearningProfile(declaredLearningProfile);
      setKsaProfile(ksa);
      setDiagnosticCatalog(diagnostics);
      setDiagnosticDefinitions({
        LAA: diagnostics.definitions.find((item) => item.type === "LAA") ?? null,
        MOA: diagnostics.definitions.find((item) => item.type === "MOA") ?? null,
        LTA: diagnostics.definitions.find((item) => item.type === "LTA") ?? null,
      });
      setDiagnosticAttempts(attempts);
      setLearningStateChecks(stateChecks);
      if (attempts.length > 0) {
        const latest = await apiClient.getDiagnosticAttempt(attempts[0].attempt_id);
        setDiagnosticAttempt(latest);
        setDiagnosticResult(latest.result ? { attempt_id: latest.attempt.attempt_id, result: latest.result } : null);
      } else {
        setDiagnosticAttempt(null);
        setDiagnosticResult(null);
      }
      setArchivedChats(sortChats(archivedList));
      setSettings(runtimeSettings);
      setSettingsDraft({
        chat_history_messages_count: runtimeSettings.chat_history_messages_count,
        max_similarities: runtimeSettings.max_similarities,
        min_similarities: runtimeSettings.min_similarities,
        similarity_score_threshold: runtimeSettings.similarity_score_threshold,
      });
      setPersonalization(personalizationSettings);
      setPersonalizationDraft(personalizationSettings);
      setAssistantMode(runtimeSettings.default_assistant_mode);

      if (isStudent) {
        setActiveChatInternal(null);
      } else if (chatList.length === 0) {
        const created = await apiClient.createChat();
        setChats([created]);
        setActiveChatInternal(created.id);
        setMessagesByChat({ [created.id]: [] });
      } else {
        const persistedChatId = window.localStorage.getItem(ACTIVE_CHAT_STORAGE_KEY);
        const nextChatId = chatList.some((chat) => chat.id === persistedChatId) ? persistedChatId : chatList[0].id;
        setActiveChatInternal(nextChatId);
      }
    } catch (error) {
      setAppError(error instanceof Error ? error.message : "Failed to load chats");
    } finally {
      setBootstrapping(false);
    }
  }

  function clearAppState() {
    setChats([]);
    setGpts([]);
    setLearningPaths([]);
    setCourses([]);
    setCoursesError(null);
    setCoursesLoading(false);
    setCoursesImporting(false);
    setLearningProfile(null);
    setKsaProfile(null);
    setKsaLoading(false);
    setKsaError(null);
    setLearningProfileLoading(false);
    setLearningProfileSaving(false);
    setLearningProfileError(null);
    setLearningProfileSuccess(null);
    setDiagnosticCatalog(null);
    setDiagnosticDefinitions({ LAA: null, MOA: null, LTA: null });
    setDiagnosticAttempt(null);
    setDiagnosticAttempts([]);
    setDiagnosticResult(null);
    setDiagnosticLoading(false);
    setDiagnosticSaving(false);
    setDiagnosticError(null);
    setLearningStateChecks([]);
    setLearningStateSaving(false);
    setLearningStateError(null);
    setFeedbackSaving(false);
    setFeedbackError(null);
    setArchivedChats([]);
    setMessagesByChat({});
    setGptChatsById({});
    setActiveChatId(null);
    setLibrary(null);
    setLibraryError(null);
    setLibraryIncludeOtherUsers(false);
    setSettings(null);
    setSettingsDraft(null);
    setPersonalization(null);
    setPersonalizationDraft(null);
    setPersonalizationError(null);
    setPersonalizationSuccess(null);
    setGlobalFileFilters([]);
    setGlobalTagFilters([]);
    setChatFileFiltersByChat({});
    setChatTagFiltersByChat({});
    setFilterError(null);
    setAdminUsers([]);
    setAdminError(null);
    clearAppSessionState();
  }

  function clearClientState(message: string | null = null) {
    clearAppState();
    setAuthSession(null);
    setAuthError(message);
  }

  async function login(username: string, password: string) {
    setAuthLoading(true);
    setAuthError(null);
    try {
      const session = await apiClient.login(username, password);
      setStoredAuthSession(session);
      if (!session.user.force_password_change) {
        await bootstrap(session);
      } else {
        clearAppState();
      }
      return session;
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Login failed");
      throw error;
    } finally {
      setAuthReady(true);
      setAuthLoading(false);
    }
  }

  async function logout() {
    try {
      if (getStoredAuthSession()?.token) {
        await apiClient.logout();
      }
    } catch {
      // ignore logout failures while clearing the client session
    }
    clearStoredAuthSession();
    clearClientState();
  }

  async function changePassword(currentPassword: string | null, newPassword: string, confirmPassword: string) {
    setPasswordChanging(true);
    setAuthError(null);
    try {
      const session = await apiClient.changePassword(currentPassword, newPassword, confirmPassword);
      setStoredAuthSession(session);
      await bootstrap(session);
      return session;
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Password change failed");
      throw error;
    } finally {
      setPasswordChanging(false);
    }
  }

  function setActiveChatInternal(chatId: string | null) {
    setActiveChatId(chatId);
    if (chatId) {
      window.localStorage.setItem(ACTIVE_CHAT_STORAGE_KEY, chatId);
      return;
    }
    window.localStorage.removeItem(ACTIVE_CHAT_STORAGE_KEY);
  }

  async function ensureChatLoaded(chatId: string) {
    setActiveChatInternal(chatId);
    if (messagesByChat[chatId] !== undefined) {
      return;
    }

    setLoadingMessages(true);
    setAppError(null);
    try {
      const messages = await apiClient.getMessages(chatId);
      setMessagesByChat((current) => ({ ...current, [chatId]: messages }));
    } catch (error) {
      setAppError(error instanceof Error ? error.message : "Failed to load messages");
    } finally {
      setLoadingMessages(false);
    }
  }

  async function createChat() {
    if (authSession?.user.role === "student") {
      throw new Error("Students can only use learning mode");
    }
    setAppError(null);
    const chat = await apiClient.createChat();
    setChats((current) => sortChats([chat, ...current]));
    setMessagesByChat((current) => ({ ...current, [chat.id]: [] }));
    setActiveChatInternal(chat.id);
    return chat;
  }

  async function renameChat(chatId: string, chatName: string) {
    const updated = await apiClient.renameChat(chatId, { chat_name: chatName });
    setChats((current) => sortChats(current.map((chat) => (chat.id === chatId ? updated : chat))));
    setArchivedChats((current) => sortChats(current.map((chat) => (chat.id === chatId ? updated : chat))));
    return updated;
  }

  async function archiveChat(chatId: string) {
    const archived = await apiClient.archiveChat(chatId);
    setChats((current) => current.filter((chat) => chat.id !== chatId));
    setArchivedChats((current) => sortChats([archived, ...current.filter((chat) => chat.id !== chatId)]));

    const remaining = chats.filter((chat) => chat.id !== chatId);
    if (activeChatId === chatId) {
      if (remaining.length > 0) {
        setActiveChatInternal(remaining[0].id);
        return remaining[0].id;
      }
      const created = await apiClient.createChat();
      setChats([created]);
      setMessagesByChat((current) => ({ ...current, [created.id]: [] }));
      setActiveChatInternal(created.id);
      return created.id;
    }
    return activeChatId;
  }

  async function unarchiveChat(chatId: string) {
    const restored = await apiClient.unarchiveChat(chatId);
    setArchivedChats((current) => current.filter((chat) => chat.id !== chatId));
    setChats((current) => sortChats([restored, ...current.filter((chat) => chat.id !== chatId)]));
    return restored;
  }

  async function deleteChat(chatId: string) {
    await apiClient.deleteChat(chatId);
    setChats((current) => current.filter((chat) => chat.id !== chatId));
    setArchivedChats((current) => current.filter((chat) => chat.id !== chatId));
    setMessagesByChat((current) => {
      const next = { ...current };
      delete next[chatId];
      return next;
    });

    const remaining = chats.filter((chat) => chat.id !== chatId);
    if (activeChatId === chatId) {
      if (remaining.length > 0) {
        const nextActive = remaining[0].id;
        setActiveChatInternal(nextActive);
        return nextActive;
      }

      const created = await apiClient.createChat();
      setChats([created]);
      setMessagesByChat({ [created.id]: [] });
      setActiveChatInternal(created.id);
      return created.id;
    }

    return activeChatId ?? remaining[0]?.id ?? null;
  }

  async function downloadChat(chatId: string) {
    const payload = await apiClient.downloadChat(chatId);
    const safeName = payload.chat_name.replace(/[^a-z0-9-_]+/gi, "_").replace(/^_+|_+$/g, "") || "chat";
    triggerJsonDownload(`${safeName}-${payload.chat_id}.json`, payload);
  }

  async function loadGpts() {
    if (authSession?.user.role === "student") {
      setGpts([]);
      return [];
    }
    const payload = await apiClient.listGpts();
    setGpts(payload);
    return payload;
  }

  async function ensureGptChatLoaded(gptId: string) {
    if (gptChatsById[gptId] !== undefined) {
      return gptChatsById[gptId];
    }
    setLoadingMessages(true);
    setAppError(null);
    try {
      const payload = await apiClient.getGptChat(gptId);
      setGptChatsById((current) => ({ ...current, [gptId]: payload }));
      setGpts((current) => current.map((entry) => (entry.id === gptId ? payload.gpt : entry)));
      return payload;
    } catch (error) {
      setAppError(error instanceof Error ? error.message : "Failed to load GPT chat");
      throw error;
    } finally {
      setLoadingMessages(false);
    }
  }

  async function createGpt(payload: GptUpsert) {
    if (authSession?.user.role === "student") {
      throw new Error("Students cannot create GPTs");
    }
    setAppError(null);
    const created = await apiClient.createGpt(payload);
    setGpts((current) => sortGpts([created, ...current]));
    return created;
  }

  async function updateGpt(gptId: string, payload: Partial<GptUpsert>) {
    const updated = await apiClient.updateGpt(gptId, payload);
    setGpts((current) => current.map((entry) => (entry.id === gptId ? updated : entry)));
    setGptChatsById((current) =>
      current[gptId]
        ? {
            ...current,
            [gptId]: {
              ...current[gptId],
              gpt: updated,
            },
          }
        : current,
    );
    return updated;
  }

  async function deleteGpt(gptId: string) {
    await apiClient.deleteGpt(gptId);
    setGpts((current) => current.filter((entry) => entry.id !== gptId));
    setGptChatsById((current) => {
      const next = { ...current };
      delete next[gptId];
      return next;
    });
  }

  async function clearGptChat(gptId: string) {
    const payload = await apiClient.clearGptChat(gptId);
    setGptChatsById((current) => ({ ...current, [gptId]: payload }));
    return payload;
  }

  async function downloadGptChat(gptId: string) {
    const payload = await apiClient.downloadGptChat(gptId);
    const safeName = payload.chat_name.replace(/[^a-z0-9-_]+/gi, "_").replace(/^_+|_+$/g, "") || "gpt";
    triggerJsonDownload(`${safeName}-${payload.chat_id}.json`, payload);
  }

  async function sendGptMessage(gptId: string, content: string, attachments: File[] = []) {
    if (!content.trim() || sending) {
      return;
    }
    const currentGpt = gptChatsById[gptId]?.gpt ?? gpts.find((entry) => entry.id === gptId);
    if (!currentGpt) {
      return;
    }

    const optimisticAttachments = attachments.map<AttachmentMeta>((file) => ({
      file_name: file.name,
      file_type: file.name.split(".").pop()?.toLowerCase() ?? "unknown",
      extraction_method: null,
      quality: {},
    }));
    const optimisticUser = createOptimisticMessage(gptId, "user", content, "completed", optimisticAttachments);
    const optimisticAssistant = createOptimisticMessage(
      gptId,
      "assistant",
      getPendingAssistantText(currentGpt.assistant_mode),
      "pending",
    );

    setSending(true);
    setAppError(null);
    setGptChatsById((current) => ({
      ...current,
      [gptId]: {
        ...(current[gptId] ?? { gpt: currentGpt, messages: [] }),
        messages: [...(current[gptId]?.messages ?? []), optimisticUser, optimisticAssistant],
      },
    }));

    try {
      const response = await apiClient.sendGptMessage(gptId, content, attachments);
      setGptChatsById((current) => ({
        ...current,
        [gptId]: {
          ...(current[gptId] ?? { gpt: currentGpt, messages: [] }),
          messages: [
            ...(current[gptId]?.messages ?? []).filter((message) => message.id !== optimisticUser.id && message.id !== optimisticAssistant.id),
            response.user_message,
            { ...response.assistant_message, sources: response.sources },
          ],
        },
      }));
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to send message";
      setGptChatsById((current) => ({
        ...current,
        [gptId]: {
          ...(current[gptId] ?? { gpt: currentGpt, messages: [] }),
          messages: [
            ...(current[gptId]?.messages ?? []).filter((message) => message.id !== optimisticAssistant.id),
            {
              ...optimisticAssistant,
              content: errorMessage,
              status: "error",
              error: errorMessage,
            },
          ],
        },
      }));
      setAppError(errorMessage);
    } finally {
      setSending(false);
    }
  }

  async function previewGptMessage(payload: GptPreviewRequest) {
    return apiClient.previewGptMessage(payload);
  }

  async function sendMessage(content: string, attachments: File[] = [], mode: AssistantMode = assistantMode) {
    if (!activeChatId || !content.trim() || sending) {
      return;
    }

    const chatId = activeChatId;
    const optimisticAttachments = attachments.map<AttachmentMeta>((file) => ({
      file_name: file.name,
      file_type: file.name.split(".").pop()?.toLowerCase() ?? "unknown",
      extraction_method: null,
      quality: {},
    }));
    const optimisticUser = createOptimisticMessage(chatId, "user", content, "completed", optimisticAttachments);
    const optimisticAssistant = createOptimisticMessage(chatId, "assistant", getPendingAssistantText(mode), "pending");

    setSending(true);
    setAppError(null);
    setMessagesByChat((current) => ({
      ...current,
      [chatId]: [...(current[chatId] ?? []), optimisticUser, optimisticAssistant],
    }));

    try {
      const response = await apiClient.sendMessage(chatId, content, attachments, mode);
      setMessagesByChat((current) => ({
        ...current,
        [chatId]: [
          ...(current[chatId] ?? []).filter((message) => message.id !== optimisticUser.id && message.id !== optimisticAssistant.id),
          response.user_message,
          {
            ...response.assistant_message,
            sources: response.sources,
          },
        ],
      }));
      setChats((current) =>
        sortChats(current.map((chat) => (chat.id === chatId ? { ...chat, updated_at: new Date().toISOString() } : chat))),
      );
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to send message";
      setMessagesByChat((current) => ({
        ...current,
        [chatId]: [
          ...(current[chatId] ?? []).filter((message) => message.id !== optimisticAssistant.id),
          {
            ...optimisticAssistant,
            content: errorMessage,
            status: "error",
            error: errorMessage,
          },
        ],
      }));
      setAppError(errorMessage);
    } finally {
      setSending(false);
    }
  }

  async function loadSettings() {
    setSettingsLoading(true);
    setSettingsError(null);
    try {
      const runtimeSettings = await apiClient.getSettings();
      setSettings(runtimeSettings);
      setSettingsDraft({
        chat_history_messages_count: runtimeSettings.chat_history_messages_count,
        max_similarities: runtimeSettings.max_similarities,
        min_similarities: runtimeSettings.min_similarities,
        similarity_score_threshold: runtimeSettings.similarity_score_threshold,
      });
      setAssistantMode((current) => (runtimeSettings.available_assistant_modes.includes(current) ? current : runtimeSettings.default_assistant_mode));
    } catch (error) {
      setSettingsError(error instanceof Error ? error.message : "Failed to load settings");
    } finally {
      setSettingsLoading(false);
    }
  }

  async function loadPersonalization() {
    setPersonalizationLoading(true);
    setPersonalizationError(null);
    try {
      const payload = await apiClient.getPersonalization();
      setPersonalization(payload);
      setPersonalizationDraft(payload);
    } catch (error) {
      setPersonalizationError(error instanceof Error ? error.message : "Failed to load personalization");
    } finally {
      setPersonalizationLoading(false);
    }
  }

  function updateSettingsDraft(patch: Partial<SettingsUpdate>) {
    setSettingsDraft((current) => (current ? { ...current, ...patch } : current));
    setSettingsSuccess(null);
  }

  function updatePersonalizationDraft(patch: Partial<PersonalizationUpdate>) {
    setPersonalizationDraft((current) => ({ ...(current ?? DEFAULT_PERSONALIZATION), ...patch }));
    setPersonalizationSuccess(null);
  }

  async function saveSettings() {
    if (!settingsDraft) {
      return null;
    }

    setSettingsSaving(true);
    setSettingsError(null);
    setSettingsSuccess(null);
    try {
      const updated = await apiClient.updateSettings(settingsDraft);
      setSettings(updated);
      setSettingsDraft({
        chat_history_messages_count: updated.chat_history_messages_count,
        max_similarities: updated.max_similarities,
        min_similarities: updated.min_similarities,
        similarity_score_threshold: updated.similarity_score_threshold,
      });
      setSettingsSuccess("Settings saved and applied live.");
      return updated;
    } catch (error) {
      setSettingsError(error instanceof Error ? error.message : "Failed to save settings");
      return null;
    } finally {
      setSettingsSaving(false);
    }
  }

  async function savePersonalization() {
    if (!personalizationDraft) {
      return null;
    }

    setPersonalizationSaving(true);
    setPersonalizationError(null);
    setPersonalizationSuccess(null);
    try {
      const updated = await apiClient.updatePersonalization(personalizationDraft);
      setPersonalization(updated);
      setPersonalizationDraft(updated);
      setPersonalizationSuccess("Personalization saved and applied to all chats.");
      return updated;
    } catch (error) {
      setPersonalizationError(error instanceof Error ? error.message : "Failed to save personalization");
      return null;
    } finally {
      setPersonalizationSaving(false);
    }
  }

  async function loadLibrary(includeOtherUsers = libraryIncludeOtherUsers) {
    setLibraryLoading(true);
    setLibraryError(null);
    setLibraryIncludeOtherUsers(includeOtherUsers);
    try {
      const payload = await apiClient.listLibraryFiles({ includeOtherUsers });
      setLibrary(payload);
      const userFiles = await apiClient.listUserFiles();
      setGlobalFileFilters(userFiles.files);
    } catch (error) {
      setLibraryError(error instanceof Error ? error.message : "Failed to load library");
    } finally {
      setLibraryLoading(false);
    }
  }

  async function toggleLibraryFile(file: LibraryFile) {
    if (!file.can_disable) {
      return;
    }
    setBusyFileIds((current) => [...current, file.id]);
    setLibraryError(null);
    try {
      const updated = await apiClient.updateLibraryFile(file.id, { is_enabled: !file.is_enabled });
      setLibrary((current) =>
        current
          ? {
              ...current,
              files: current.files.map((entry) => (entry.id === file.id ? updated : entry)),
            }
          : current,
      );
      const globalUpdated = await apiClient.updateUserFile(file.id, { is_enabled: !file.is_enabled });
      setGlobalFileFilters((current) => current.map((entry) => (entry.file_id === file.id ? globalUpdated : entry)));
      setChatFileFiltersByChat((current) =>
        Object.fromEntries(
          Object.entries(current).map(([chatId, entries]) => [
            chatId,
            entries.map((entry) =>
              entry.file_id === file.id
                ? {
                    ...entry,
                    global_is_enabled: globalUpdated.global_is_enabled,
                    is_enabled: globalUpdated.global_is_enabled && entry.scoped_is_enabled,
                    is_locked: !globalUpdated.global_is_enabled,
                  }
                : entry,
            ),
          ]),
        ),
      );
    } catch (error) {
      setLibraryError(error instanceof Error ? error.message : "Failed to update file");
    } finally {
      setBusyFileIds((current) => current.filter((value) => value !== file.id));
    }
  }

  async function deleteLibraryFile(fileId: number) {
    setBusyFileIds((current) => [...current, fileId]);
    setLibraryError(null);
    try {
      await apiClient.deleteLibraryFile(fileId);
      await loadLibrary(libraryIncludeOtherUsers);
    } catch (error) {
      setLibraryError(error instanceof Error ? error.message : "Failed to delete file");
    } finally {
      setBusyFileIds((current) => current.filter((value) => value !== fileId));
    }
  }

  async function uploadLibraryFiles(files: File[], tagsByFile: Record<string, string[]>) {
    setUploading(true);
    setLibraryError(null);
    try {
      await apiClient.uploadLibraryFiles(files, tagsByFile);
      await loadLibrary(libraryIncludeOtherUsers);
    } catch (error) {
      setLibraryError(error instanceof Error ? error.message : "Failed to upload files");
      throw error;
    } finally {
      setUploading(false);
    }
  }

  async function loadAdminUsers() {
    if (authSession?.user.role !== "admin") {
      return;
    }
    setAdminLoading(true);
    setAdminError(null);
    try {
      setAdminUsers(await apiClient.listAdminUsers());
    } catch (error) {
      setAdminError(error instanceof Error ? error.message : "Failed to load users");
    } finally {
      setAdminLoading(false);
    }
  }

  async function createAdminUser(payload: { username: string; displayname: string; role: "user" | "admin" | "student" }) {
    setAdminError(null);
    const created = await apiClient.createAdminUser(payload);
    setAdminUsers((current) => [...current, created].sort((left, right) => left.username.localeCompare(right.username)));
    return created;
  }

  async function loadLearningPaths() {
    setLearningLoading(true);
    setLearningError(null);
    try {
      const payload = await apiClient.listLearningPaths();
      setLearningPaths(payload.paths);
      return payload.paths;
    } catch (error) {
      setLearningError(error instanceof Error ? error.message : "Failed to load learning paths");
      return [];
    } finally {
      setLearningLoading(false);
    }
  }

  async function loadCourses(params?: {
    search?: string;
    scope?: "global" | "user" | "all";
    status?: "draft" | "published" | "archived" | "all";
    owner_user_id?: number;
    sort?: CourseSort;
  }) {
    setCoursesLoading(true);
    setCoursesError(null);
    try {
      const payload = await apiClient.listCourses(params);
      setCourses(payload.courses);
      return payload.courses;
    } catch (error) {
      setCoursesError(error instanceof Error ? error.message : "Failed to load courses");
      return [];
    } finally {
      setCoursesLoading(false);
    }
  }

  async function importCourseFiles(files: File[], scopesByFile: Record<string, "global" | "user">) {
    setCoursesImporting(true);
    setCoursesError(null);
    try {
      const payload: CourseImportResponse = await apiClient.importCourseFiles(files, scopesByFile);
      await loadCourses();
      return payload;
    } catch (error) {
      setCoursesError(error instanceof Error ? error.message : "Failed to import course files");
      throw error;
    } finally {
      setCoursesImporting(false);
    }
  }

  async function downloadCourseTemplate() {
    setCoursesError(null);
    try {
      const payload = await apiClient.getCourseTemplate();
      triggerJsonDownload(payload.file_name, payload.template);
    } catch (error) {
      setCoursesError(error instanceof Error ? error.message : "Failed to download course template");
      throw error;
    }
  }

  async function loadLearningProfile() {
    setLearningProfileLoading(true);
    setLearningProfileError(null);
    try {
      const payload = await apiClient.getLearningProfile();
      setLearningProfile(payload);
      setLearningProfileSuccess(null);
      return payload;
    } catch (error) {
      setLearningProfileError(error instanceof Error ? error.message : "Failed to load learning profile");
      return null;
    } finally {
      setLearningProfileLoading(false);
    }
  }

  async function loadKsaProfile() {
    setKsaLoading(true);
    setKsaError(null);
    try {
      const payload = await apiClient.getKsaProfile();
      setKsaProfile(payload);
      return payload;
    } catch (error) {
      setKsaError(error instanceof Error ? error.message : "Failed to load KSA profile");
      return null;
    } finally {
      setKsaLoading(false);
    }
  }

  async function saveLearningPreferences(payload: Partial<Omit<LearningPreferences, "updated_at">>) {
    setLearningProfileSaving(true);
    setLearningProfileError(null);
    setLearningProfileSuccess(null);
    try {
      const updated = await apiClient.updateLearningPreferences(payload);
      setLearningProfile((current) => {
        if (!current) {
          return {
            preferences: updated,
            context: {
              profile_display_name: "",
              about_me: "",
              contact_location: "",
              general_title: "",
              date_of_birth: "",
              current_skill_areas: [],
              skills: [],
              interests: [],
              work_experience: [],
              education_history: [],
              current_reason_for_learning: "",
              preferred_form_of_address: "",
              learning_context_notes: "",
              updated_at: null,
            },
            goals: [],
            diagnostics_status: "not_started",
          };
        }
        return { ...current, preferences: updated };
      });
      setLearningProfileSuccess("Learning preferences saved.");
      return updated;
    } catch (error) {
      setLearningProfileError(error instanceof Error ? error.message : "Failed to save learning preferences");
      throw error;
    } finally {
      setLearningProfileSaving(false);
    }
  }

  async function saveLearningContext(payload: Partial<Omit<LearningProfileContext, "updated_at">>) {
    setLearningProfileSaving(true);
    setLearningProfileError(null);
    setLearningProfileSuccess(null);
    try {
      const updated = await apiClient.updateLearningContext(payload);
      setLearningProfile((current) => {
        if (!current) {
          return {
            preferences: {
              preferred_pace: "balanced",
              explanation_depth: "balanced",
              examples_vs_theory: "balanced",
              structure_preference: "balanced",
              checkpoint_frequency: "medium",
              encouragement_level: "balanced",
              guidance_level: "balanced",
              recap_frequency: "medium",
              preferred_learning_format: "mixed",
              custom_preference_note: "",
              updated_at: null,
            },
            context: updated,
            goals: [],
            diagnostics_status: "not_started",
          };
        }
        return { ...current, context: updated };
      });
      setLearningProfileSuccess("Learning context saved.");
      return updated;
    } catch (error) {
      setLearningProfileError(error instanceof Error ? error.message : "Failed to save learning context");
      throw error;
    } finally {
      setLearningProfileSaving(false);
    }
  }

  async function createLearningGoal(payload: {
    target_topic: string;
    reason_for_learning: string;
    target_level: string;
    deadline: string | null;
    priority: "low" | "medium" | "high" | null;
    notes: string;
    is_active: boolean;
  }) {
    setLearningProfileSaving(true);
    setLearningProfileError(null);
    setLearningProfileSuccess(null);
    try {
      const created = await apiClient.createLearningGoal(payload);
      setLearningProfile((current) => {
        if (!current) {
          return {
            preferences: {
              preferred_pace: "balanced",
              explanation_depth: "balanced",
              examples_vs_theory: "balanced",
              structure_preference: "balanced",
              checkpoint_frequency: "medium",
              encouragement_level: "balanced",
              guidance_level: "balanced",
              recap_frequency: "medium",
              preferred_learning_format: "mixed",
              custom_preference_note: "",
              updated_at: null,
            },
            context: {
              profile_display_name: "",
              about_me: "",
              contact_location: "",
              general_title: "",
              date_of_birth: "",
              current_skill_areas: [],
              skills: [],
              interests: [],
              work_experience: [],
              education_history: [],
              current_reason_for_learning: "",
              preferred_form_of_address: "",
              learning_context_notes: "",
              updated_at: null,
            },
            goals: [created],
            diagnostics_status: "not_started",
          };
        }
        return { ...current, goals: [created, ...current.goals.filter((goal) => goal.id !== created.id)] };
      });
      setLearningProfileSuccess("Learning goal saved.");
      return created;
    } catch (error) {
      setLearningProfileError(error instanceof Error ? error.message : "Failed to save learning goal");
      throw error;
    } finally {
      setLearningProfileSaving(false);
    }
  }

  async function updateLearningGoal(goalId: string, payload: Partial<Omit<LearningGoal, "id" | "created_at" | "updated_at">>) {
    setLearningProfileSaving(true);
    setLearningProfileError(null);
    setLearningProfileSuccess(null);
    try {
      const updated = await apiClient.updateLearningGoal(goalId, payload);
      setLearningProfile((current) => (current ? { ...current, goals: current.goals.map((goal) => (goal.id === goalId ? updated : goal)) } : current));
      setLearningProfileSuccess("Learning goal updated.");
      return updated;
    } catch (error) {
      setLearningProfileError(error instanceof Error ? error.message : "Failed to update learning goal");
      throw error;
    } finally {
      setLearningProfileSaving(false);
    }
  }

  async function deleteLearningGoal(goalId: string) {
    setLearningProfileSaving(true);
    setLearningProfileError(null);
    setLearningProfileSuccess(null);
    try {
      await apiClient.deleteLearningGoal(goalId);
      setLearningProfile((current) => (current ? { ...current, goals: current.goals.filter((goal) => goal.id !== goalId) } : current));
      setLearningProfileSuccess("Learning goal deleted.");
    } catch (error) {
      setLearningProfileError(error instanceof Error ? error.message : "Failed to delete learning goal");
      throw error;
    } finally {
      setLearningProfileSaving(false);
    }
  }

  async function loadDiagnosticCatalog() {
    setDiagnosticLoading(true);
    setDiagnosticError(null);
    try {
      const catalog = await apiClient.listDiagnosticDefinitions();
      setDiagnosticCatalog(catalog);
      setDiagnosticDefinitions({
        LAA: catalog.definitions.find((item) => item.type === "LAA") ?? null,
        MOA: catalog.definitions.find((item) => item.type === "MOA") ?? null,
        LTA: catalog.definitions.find((item) => item.type === "LTA") ?? null,
      });
      return catalog;
    } catch (error) {
      setDiagnosticError(error instanceof Error ? error.message : "Failed to load diagnostics");
      throw error;
    } finally {
      setDiagnosticLoading(false);
    }
  }

  async function loadDiagnosticAttempts() {
    setDiagnosticLoading(true);
    setDiagnosticError(null);
    try {
      const attempts = await apiClient.listDiagnosticAttempts();
      setDiagnosticAttempts(attempts);
      if (attempts.length === 0) {
        setDiagnosticAttempt(null);
        setDiagnosticResult(null);
        return attempts;
      }

      const inProgress = attempts.find((item) => item.status !== "completed");
      const activeAttemptId = inProgress?.attempt_id ?? attempts[0].attempt_id;
      const activeAttempt = await apiClient.getDiagnosticAttempt(activeAttemptId);
      setDiagnosticAttempt(activeAttempt);

      const latestCompleted = attempts.find((item) => item.status === "completed");
      if (latestCompleted) {
        const completedDetails = await apiClient.getDiagnosticAttempt(latestCompleted.attempt_id);
        setDiagnosticResult(completedDetails.result ? { attempt_id: completedDetails.attempt.attempt_id, result: completedDetails.result } : null);
      } else {
        setDiagnosticResult(null);
      }
      return attempts;
    } catch (error) {
      setDiagnosticError(error instanceof Error ? error.message : "Failed to load attempts");
      throw error;
    } finally {
      setDiagnosticLoading(false);
    }
  }

  async function startDiagnosticAttempt() {
    setDiagnosticSaving(true);
    setDiagnosticError(null);
    try {
      const started = await apiClient.startDiagnosticAttempt();
      const details = await apiClient.getDiagnosticAttempt(started.attempt_id);
      setDiagnosticAttempt(details);
      setDiagnosticResult(null);
      await loadDiagnosticAttempts();
      await loadLearningProfile();
      return details;
    } catch (error) {
      setDiagnosticError(error instanceof Error ? error.message : "Failed to start diagnostic attempt");
      throw error;
    } finally {
      setDiagnosticSaving(false);
    }
  }

  async function saveDiagnosticAnswers(
    attemptId: string,
    diagnosticType: "LAA" | "MOA" | "LTA",
    answers: Array<{ question_id: string; value: unknown }>,
  ) {
    setDiagnosticSaving(true);
    setDiagnosticError(null);
    try {
      const updated = await apiClient.upsertDiagnosticAnswers(attemptId, { diagnostic_type: diagnosticType, answers });
      setDiagnosticAttempt(updated);
      return updated;
    } catch (error) {
      setDiagnosticError(error instanceof Error ? error.message : "Failed to save diagnostic answers");
      throw error;
    } finally {
      setDiagnosticSaving(false);
    }
  }

  async function completeDiagnosticAttempt(attemptId: string) {
    setDiagnosticSaving(true);
    setDiagnosticError(null);
    try {
      const result = await apiClient.completeDiagnosticAttempt(attemptId);
      setDiagnosticResult(result);
      await loadDiagnosticAttempts();
      await loadLearningProfile();
      return result;
    } catch (error) {
      setDiagnosticError(error instanceof Error ? error.message : "Failed to complete diagnostic");
      throw error;
    } finally {
      setDiagnosticSaving(false);
    }
  }

  async function deleteDiagnosticAttempt(attemptId: string) {
    setDiagnosticSaving(true);
    setDiagnosticError(null);
    try {
      await apiClient.deleteDiagnosticAttempt(attemptId);
      await loadDiagnosticAttempts();
      await loadLearningProfile();
    } catch (error) {
      setDiagnosticError(error instanceof Error ? error.message : "Failed to delete diagnostic attempt");
      throw error;
    } finally {
      setDiagnosticSaving(false);
    }
  }

  async function openDiagnosticAttempt(attemptId: string) {
    setDiagnosticSaving(true);
    setDiagnosticError(null);
    try {
      const details = await apiClient.getDiagnosticAttempt(attemptId);
      setDiagnosticAttempt(details);
      return details;
    } catch (error) {
      setDiagnosticError(error instanceof Error ? error.message : "Failed to open diagnostic attempt");
      throw error;
    } finally {
      setDiagnosticSaving(false);
    }
  }

  async function createLearningStateCheck(payload: {
    chat_id?: string | null;
    mood: string;
    perceived_difficulty: string;
    needs_pause_or_input: string;
    preferred_format: string;
    notes: string;
  }) {
    setLearningStateSaving(true);
    setLearningStateError(null);
    try {
      const created = await apiClient.createLearningStateCheck(payload);
      setLearningStateChecks((current) => [created, ...current]);
      return created;
    } catch (error) {
      setLearningStateError(error instanceof Error ? error.message : "Failed to save learning state");
      throw error;
    } finally {
      setLearningStateSaving(false);
    }
  }

  async function loadLearningStateChecks(limit = 20) {
    setLearningStateError(null);
    const checks = await apiClient.listLearningStateChecks(limit);
    setLearningStateChecks(checks);
    return checks;
  }

  async function submitExplanationFeedback(payload: {
    message_id?: number | null;
    rating: number;
    feedback_text: string;
    re_explain_requested: boolean;
  }) {
    setFeedbackSaving(true);
    setFeedbackError(null);
    try {
      return await apiClient.createExplanationFeedback(payload);
    } catch (error) {
      setFeedbackError(error instanceof Error ? error.message : "Failed to save feedback");
      throw error;
    } finally {
      setFeedbackSaving(false);
    }
  }

  async function createLearningPath(payload: {
    scope: "global" | "user";
    title: string;
    description: string;
    subject: string;
    difficulty_level: string;
    estimated_duration_minutes: number | null;
    status: "draft" | "published" | "archived";
    allowed_file_ids: number[];
    allowed_tags: string[];
  }) {
    setLearningSaving(true);
    setLearningError(null);
    try {
      const created = await apiClient.createLearningPath(payload);
      setLearningPaths((current) => [created, ...current.filter((entry) => entry.id !== created.id)]);
      return created;
    } catch (error) {
      setLearningError(error instanceof Error ? error.message : "Failed to create learning path");
      throw error;
    } finally {
      setLearningSaving(false);
    }
  }

  async function updateLearningPath(
    pathId: string,
    payload: Partial<{
      title: string;
      description: string;
      subject: string;
      difficulty_level: string;
      estimated_duration_minutes: number | null;
      status: "draft" | "published" | "archived";
      allowed_file_ids: number[];
      allowed_tags: string[];
    }>,
  ) {
    setLearningSaving(true);
    setLearningError(null);
    try {
      const updated = await apiClient.updateLearningPath(pathId, payload);
      setLearningPaths((current) => current.map((entry) => (entry.id === pathId ? updated : entry)));
      return updated;
    } catch (error) {
      setLearningError(error instanceof Error ? error.message : "Failed to update learning path");
      throw error;
    } finally {
      setLearningSaving(false);
    }
  }

  async function getLearningPathDetails(pathId: string) {
    return await apiClient.getLearningPath(pathId);
  }

  async function deleteLearningPath(pathId: string) {
    setLearningSaving(true);
    setLearningError(null);
    try {
      await apiClient.deleteLearningPath(pathId);
      setLearningPaths((current) => current.filter((entry) => entry.id !== pathId));
    } catch (error) {
      setLearningError(error instanceof Error ? error.message : "Failed to delete learning path");
      throw error;
    } finally {
      setLearningSaving(false);
    }
  }

  async function createLearningModule(pathId: string, payload: { title: string; description: string; learning_objectives: string[] }) {
    setLearningSaving(true);
    setLearningError(null);
    try {
      const module = await apiClient.createLearningModule(pathId, payload);
      setLearningPaths((current) =>
        current.map((entry) =>
          entry.id === pathId
            ? { ...entry, modules: [...entry.modules, module].sort((a, b) => a.order_index - b.order_index) }
            : entry,
        ),
      );
      return module;
    } catch (error) {
      setLearningError(error instanceof Error ? error.message : "Failed to create module");
      throw error;
    } finally {
      setLearningSaving(false);
    }
  }

  async function updateLearningModule(
    pathId: string,
    moduleId: string,
    payload: Partial<{ title: string; description: string; learning_objectives: string[] }>,
  ) {
    setLearningSaving(true);
    setLearningError(null);
    try {
      const updated = await apiClient.updateLearningModule(moduleId, payload);
      setLearningPaths((current) =>
        current.map((entry) =>
          entry.id === pathId
            ? { ...entry, modules: entry.modules.map((module) => (module.id === moduleId ? updated : module)) }
            : entry,
        ),
      );
      return updated;
    } catch (error) {
      setLearningError(error instanceof Error ? error.message : "Failed to update module");
      throw error;
    } finally {
      setLearningSaving(false);
    }
  }

  async function deleteLearningModule(pathId: string, moduleId: string) {
    setLearningSaving(true);
    setLearningError(null);
    try {
      await apiClient.deleteLearningModule(moduleId);
      setLearningPaths((current) =>
        current.map((entry) =>
          entry.id === pathId ? { ...entry, modules: entry.modules.filter((module) => module.id !== moduleId) } : entry,
        ),
      );
    } catch (error) {
      setLearningError(error instanceof Error ? error.message : "Failed to delete module");
      throw error;
    } finally {
      setLearningSaving(false);
    }
  }

  async function reorderLearningModules(pathId: string, modules: LearningModule[]) {
    setLearningSaving(true);
    setLearningError(null);
    try {
      const reordered = await apiClient.reorderLearningModules(
        pathId,
        modules.map((module, index) => ({ id: module.id, order_index: index })),
      );
      setLearningPaths((current) =>
        current.map((entry) => (entry.id === pathId ? { ...entry, modules: reordered } : entry)),
      );
      return reordered;
    } catch (error) {
      setLearningError(error instanceof Error ? error.message : "Failed to reorder modules");
      throw error;
    } finally {
      setLearningSaving(false);
    }
  }

  async function createLearningLesson(
    pathId: string,
    moduleId: string,
    payload: { title: string; description: string; objectives: string[]; teaching_notes: string },
  ) {
    setLearningSaving(true);
    setLearningError(null);
    try {
      const lesson = await apiClient.createLearningLesson(moduleId, payload);
      setLearningPaths((current) =>
        current.map((entry) =>
          entry.id === pathId
            ? {
                ...entry,
                modules: entry.modules.map((module) =>
                  module.id === moduleId
                    ? { ...module, lessons: [...module.lessons, lesson].sort((a, b) => a.order_index - b.order_index) }
                    : module,
                ),
              }
            : entry,
        ),
      );
      return lesson;
    } catch (error) {
      setLearningError(error instanceof Error ? error.message : "Failed to create lesson");
      throw error;
    } finally {
      setLearningSaving(false);
    }
  }

  async function updateLearningLesson(
    pathId: string,
    moduleId: string,
    lessonId: string,
    payload: Partial<{ title: string; description: string; objectives: string[]; teaching_notes: string }>,
  ) {
    setLearningSaving(true);
    setLearningError(null);
    try {
      const updated = await apiClient.updateLearningLesson(lessonId, payload);
      setLearningPaths((current) =>
        current.map((entry) =>
          entry.id === pathId
            ? {
                ...entry,
                modules: entry.modules.map((module) =>
                  module.id === moduleId
                    ? { ...module, lessons: module.lessons.map((lesson) => (lesson.id === lessonId ? updated : lesson)) }
                    : module,
                ),
              }
            : entry,
        ),
      );
      return updated;
    } catch (error) {
      setLearningError(error instanceof Error ? error.message : "Failed to update lesson");
      throw error;
    } finally {
      setLearningSaving(false);
    }
  }

  async function deleteLearningLesson(pathId: string, moduleId: string, lessonId: string) {
    setLearningSaving(true);
    setLearningError(null);
    try {
      await apiClient.deleteLearningLesson(lessonId);
      setLearningPaths((current) =>
        current.map((entry) =>
          entry.id === pathId
            ? {
                ...entry,
                modules: entry.modules.map((module) =>
                  module.id === moduleId
                    ? { ...module, lessons: module.lessons.filter((lesson) => lesson.id !== lessonId) }
                    : module,
                ),
              }
            : entry,
        ),
      );
    } catch (error) {
      setLearningError(error instanceof Error ? error.message : "Failed to delete lesson");
      throw error;
    } finally {
      setLearningSaving(false);
    }
  }

  async function reorderLearningLessons(pathId: string, moduleId: string, lessons: LearningLesson[]) {
    setLearningSaving(true);
    setLearningError(null);
    try {
      const reordered = await apiClient.reorderLearningLessons(
        moduleId,
        lessons.map((lesson, index) => ({ id: lesson.id, order_index: index })),
      );
      setLearningPaths((current) =>
        current.map((entry) =>
          entry.id === pathId
            ? {
                ...entry,
                modules: entry.modules.map((module) =>
                  module.id === moduleId ? { ...module, lessons: reordered } : module,
                ),
              }
            : entry,
        ),
      );
      return reordered;
    } catch (error) {
      setLearningError(error instanceof Error ? error.message : "Failed to reorder lessons");
      throw error;
    } finally {
      setLearningSaving(false);
    }
  }

  async function updateAdminUser(userId: number, payload: Partial<Pick<AdminUser, "displayname" | "role" | "status" | "force_password_change">>) {
    setAdminBusyUserIds((current) => [...current, userId]);
    setAdminError(null);
    try {
      const updated = await apiClient.updateAdminUser(userId, payload);
      setAdminUsers((current) => current.map((user) => (user.id === userId ? updated : user)));
      if (authSession?.user.id === userId) {
        setStoredAuthSession({ ...authSession, user: updated });
      }
      return updated;
    } catch (error) {
      setAdminError(error instanceof Error ? error.message : "Failed to update user");
      throw error;
    } finally {
      setAdminBusyUserIds((current) => current.filter((value) => value !== userId));
    }
  }

  async function deleteAdminUser(userId: number) {
    setAdminBusyUserIds((current) => [...current, userId]);
    setAdminError(null);
    try {
      await apiClient.deleteAdminUser(userId);
      setAdminUsers((current) => current.filter((user) => user.id !== userId));
    } catch (error) {
      setAdminError(error instanceof Error ? error.message : "Failed to delete user");
      throw error;
    } finally {
      setAdminBusyUserIds((current) => current.filter((value) => value !== userId));
    }
  }

  async function loadGlobalFilters() {
    setFilterLoading(true);
    setFilterError(null);
    try {
      const [files, tags] = await Promise.all([apiClient.listUserFiles(), apiClient.listUserTags()]);
      setGlobalFileFilters(files.files);
      setGlobalTagFilters(tags.tags);
    } catch (error) {
      setFilterError(error instanceof Error ? error.message : "Failed to load filters");
    } finally {
      setFilterLoading(false);
    }
  }

  async function loadChatFilters(chatId: string) {
    setFilterLoading(true);
    setFilterError(null);
    try {
      const [files, tags] = await Promise.all([apiClient.listChatFiles(chatId), apiClient.listChatTags(chatId)]);
      setChatFileFiltersByChat((current) => ({ ...current, [chatId]: files.files }));
      setChatTagFiltersByChat((current) => ({ ...current, [chatId]: tags.tags }));
    } catch (error) {
      setFilterError(error instanceof Error ? error.message : "Failed to load chat filters");
    } finally {
      setFilterLoading(false);
    }
  }

  async function toggleGlobalFileFilter(fileId: number, isEnabled: boolean) {
    const busyKey = `global-file:${fileId}`;
    setFilterBusyKeys((current) => [...current, busyKey]);
    setFilterError(null);
    try {
      const updated = await apiClient.updateUserFile(fileId, { is_enabled: isEnabled });
      setGlobalFileFilters((current) => current.map((entry) => (entry.file_id === fileId ? updated : entry)));
      setLibrary((current) =>
        current
          ? {
              ...current,
              files: current.files.map((entry) => (entry.id === fileId ? { ...entry, is_enabled: updated.is_enabled } : entry)),
            }
          : current,
      );
      setChatFileFiltersByChat((current) =>
        Object.fromEntries(
          Object.entries(current).map(([chatId, entries]) => [
            chatId,
            entries.map((entry) =>
              entry.file_id === fileId
                ? {
                    ...entry,
                    global_is_enabled: updated.global_is_enabled,
                    is_enabled: updated.global_is_enabled && entry.scoped_is_enabled,
                    is_locked: !updated.global_is_enabled,
                  }
                : entry,
            ),
          ]),
        ),
      );
    } catch (error) {
      setFilterError(error instanceof Error ? error.message : "Failed to update global file filter");
    } finally {
      setFilterBusyKeys((current) => current.filter((value) => value !== busyKey));
    }
  }

  async function toggleChatFileFilter(chatId: string, fileId: number, isEnabled: boolean) {
    const busyKey = `chat-file:${chatId}:${fileId}`;
    setFilterBusyKeys((current) => [...current, busyKey]);
    setFilterError(null);
    try {
      const updated = await apiClient.updateChatFile(chatId, fileId, { is_enabled: isEnabled });
      setChatFileFiltersByChat((current) => ({
        ...current,
        [chatId]: (current[chatId] ?? []).map((entry) => (entry.file_id === fileId ? updated : entry)),
      }));
    } catch (error) {
      setFilterError(error instanceof Error ? error.message : "Failed to update chat file filter");
    } finally {
      setFilterBusyKeys((current) => current.filter((value) => value !== busyKey));
    }
  }

  async function toggleGlobalTagFilter(tag: string, isEnabled: boolean) {
    const busyKey = `global-tag:${tag}`;
    setFilterBusyKeys((current) => [...current, busyKey]);
    setFilterError(null);
    try {
      const updated = await apiClient.updateUserTag(tag, { is_enabled: isEnabled });
      setGlobalTagFilters((current) => current.map((entry) => (entry.tag === tag ? updated : entry)));
      setChatTagFiltersByChat((current) =>
        Object.fromEntries(
          Object.entries(current).map(([chatId, entries]) => [
            chatId,
            entries.map((entry) =>
              entry.tag === tag
                ? {
                    ...entry,
                    global_is_enabled: updated.global_is_enabled,
                    is_enabled: updated.global_is_enabled && entry.scoped_is_enabled,
                    is_locked: !updated.global_is_enabled,
                  }
                : entry,
            ),
          ]),
        ),
      );
    } catch (error) {
      setFilterError(error instanceof Error ? error.message : "Failed to update global tag filter");
    } finally {
      setFilterBusyKeys((current) => current.filter((value) => value !== busyKey));
    }
  }

  async function toggleChatTagFilter(chatId: string, tag: string, isEnabled: boolean) {
    const busyKey = `chat-tag:${chatId}:${tag}`;
    setFilterBusyKeys((current) => [...current, busyKey]);
    setFilterError(null);
    try {
      const updated = await apiClient.updateChatTag(chatId, tag, { is_enabled: isEnabled });
      setChatTagFiltersByChat((current) => ({
        ...current,
        [chatId]: (current[chatId] ?? []).map((entry) => (entry.tag === tag ? updated : entry)),
      }));
    } catch (error) {
      setFilterError(error instanceof Error ? error.message : "Failed to update chat tag filter");
    } finally {
      setFilterBusyKeys((current) => current.filter((value) => value !== busyKey));
    }
  }

  const activeMessages = useMemo(() => (activeChatId ? messagesByChat[activeChatId] ?? [] : []), [activeChatId, messagesByChat]);
  const isStudent = authSession?.user.role === "student";
  const canUseStandardChat = !isStudent;
  const canUseGpts = !isStudent;
  const canAuthorLearningPaths = authSession?.user.role === "admin" || authSession?.user.role === "user";

  return {
    authReady,
    authLoading,
    authError,
    authSession,
    currentUser: authSession?.user ?? null,
    isAuthenticated: Boolean(authSession?.token),
    requiresPasswordChange: Boolean(authSession?.user.force_password_change),
    passwordChanging,
    login,
    logout,
    changePassword,
    adminUsers,
    adminLoading,
    adminError,
    adminBusyUserIds,
    loadAdminUsers,
    createAdminUser,
    updateAdminUser,
    deleteAdminUser,
    bootstrapping,
    chats,
    gpts,
    learningPaths,
    courses,
    learningLoading,
    learningError,
    learningSaving,
    coursesLoading,
    coursesError,
    coursesImporting,
    learningProfile,
    ksaProfile,
    learningProfileLoading,
    ksaLoading,
    ksaError,
    learningProfileSaving,
    learningProfileError,
    learningProfileSuccess,
    diagnosticCatalog,
    diagnosticDefinitions,
    diagnosticAttempt,
    diagnosticAttempts,
    diagnosticResult,
    diagnosticLoading,
    diagnosticSaving,
    diagnosticError,
    learningStateChecks,
    learningStateSaving,
    learningStateError,
    feedbackSaving,
    feedbackError,
    archivedChats,
    gptChatsById,
    activeChatId,
    activeMessages,
    loadingMessages,
    sending,
    appError,
    library,
    libraryLoading,
    libraryError,
    libraryIncludeOtherUsers,
    uploading,
    busyFileIds,
    assistantMode,
    settings,
    settingsDraft,
    settingsLoading,
    settingsSaving,
    settingsError,
    settingsSuccess,
    personalization,
    personalizationDraft,
    personalizationLoading,
    personalizationSaving,
    personalizationError,
    personalizationSuccess,
    globalFileFilters,
    globalTagFilters,
    chatFileFiltersByChat,
    chatTagFiltersByChat,
    filterLoading,
    filterError,
    filterBusyKeys,
    isStudent,
    canUseStandardChat,
    canUseGpts,
    canAuthorLearningPaths,
    canCreateGlobalCourses: authSession?.user.role === "admin",
    setAssistantMode,
    ensureChatLoaded,
    createChat,
    renameChat,
    archiveChat,
    unarchiveChat,
    deleteChat,
    downloadChat,
    loadGpts,
    ensureGptChatLoaded,
    createGpt,
    updateGpt,
    deleteGpt,
    clearGptChat,
    downloadGptChat,
    sendGptMessage,
    previewGptMessage,
    sendMessage,
    loadSettings,
    loadPersonalization,
    updateSettingsDraft,
    updatePersonalizationDraft,
    saveSettings,
    savePersonalization,
    loadGlobalFilters,
    loadChatFilters,
    toggleGlobalFileFilter,
    toggleChatFileFilter,
    toggleGlobalTagFilter,
    toggleChatTagFilter,
    loadLearningPaths,
    loadCourses,
    importCourseFiles,
    downloadCourseTemplate,
    loadLearningProfile,
    loadKsaProfile,
    saveLearningPreferences,
    saveLearningContext,
    createLearningGoal,
    updateLearningGoal,
    deleteLearningGoal,
    loadDiagnosticCatalog,
    loadDiagnosticAttempts,
    startDiagnosticAttempt,
    saveDiagnosticAnswers,
    completeDiagnosticAttempt,
    deleteDiagnosticAttempt,
    openDiagnosticAttempt,
    createLearningStateCheck,
    loadLearningStateChecks,
    submitExplanationFeedback,
    createLearningPath,
    getLearningPathDetails,
    updateLearningPath,
    deleteLearningPath,
    createLearningModule,
    updateLearningModule,
    deleteLearningModule,
    reorderLearningModules,
    createLearningLesson,
    updateLearningLesson,
    deleteLearningLesson,
    reorderLearningLessons,
    loadLibrary,
    setLibraryIncludeOtherUsers,
    toggleLibraryFile,
    deleteLibraryFile,
    uploadLibraryFiles,
    attachmentRules: {
      maxFiles: ATTACHMENT_MAX_FILES,
      allowedExtensions: ATTACHMENT_ALLOWED_EXTENSIONS,
    },
  };
}
