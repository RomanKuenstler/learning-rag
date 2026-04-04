import { useEffect, useMemo, useState } from "react";
import { apiClient, clearStoredAuthSession, getStoredAuthSession, setStoredAuthSession, subscribeAuthSession } from "../api/client";
import type {
  AdminUser,
  AssistantMode,
  AttachmentMeta,
  AuthSession,
  Chat,
  FilterFile,
  FilterTag,
  Gpt,
  GptChat,
  GptPreviewRequest,
  GptUpsert,
  LibraryFile,
  LibraryResponse,
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
  anchor.click();
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
      const [chatList, archivedList, runtimeSettings, personalizationSettings, gptList] = await Promise.all([
        apiClient.listChats(),
        apiClient.listArchivedChats(),
        apiClient.getSettings(),
        apiClient.getPersonalization(),
        apiClient.listGpts(),
      ]);
      setChats(sortChats(chatList));
      setGpts(gptList);
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

      if (chatList.length === 0) {
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

  async function createAdminUser(payload: { username: string; displayname: string; role: "user" | "admin" }) {
    setAdminError(null);
    const created = await apiClient.createAdminUser(payload);
    setAdminUsers((current) => [...current, created].sort((left, right) => left.username.localeCompare(right.username)));
    return created;
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
