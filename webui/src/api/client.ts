import type {
  AdminUser,
  AssistantMode,
  AuthSession,
  Chat,
  ChatDownload,
  ChatUpdate,
  CurrentUser,
  FilterFile,
  FilterFileResponse,
  FilterTag,
  FilterTagResponse,
  Gpt,
  GptChat,
  GptDeleteResponse,
  GptPreviewRequest,
  GptUpsert,
  LibraryFile,
  LibraryResponse,
  LibraryUploadResponse,
  LearningModule,
  LearningLesson,
  LearningPath,
  LearningPathResponse,
  Message,
  MessageResponse,
  Personalization,
  PersonalizationUpdate,
  Settings,
  SettingsUpdate,
} from "../types/chat";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ?? "http://localhost:8000";
const AUTH_STORAGE_KEY = "local-rag-auth-session";

type AuthListener = (session: AuthSession | null) => void;

const authListeners = new Set<AuthListener>();

function readStoredAuthSession(): AuthSession | null {
  const raw = window.localStorage.getItem(AUTH_STORAGE_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as AuthSession;
  } catch {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
    return null;
  }
}

function emitAuthSession(session: AuthSession | null) {
  authListeners.forEach((listener) => listener(session));
}

export function getStoredAuthSession() {
  return readStoredAuthSession();
}

export function setStoredAuthSession(session: AuthSession) {
  window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
  emitAuthSession(session);
}

export function clearStoredAuthSession() {
  window.localStorage.removeItem(AUTH_STORAGE_KEY);
  emitAuthSession(null);
}

export function subscribeAuthSession(listener: AuthListener) {
  authListeners.add(listener);
  return () => {
    authListeners.delete(listener);
  };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers ?? {});
  const isFormData = init?.body instanceof FormData;
  if (!isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const authSession = readStoredAuthSession();
  if (authSession?.token) {
    headers.set("Authorization", `Bearer ${authSession.token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  });

  const refreshedToken = response.headers.get("X-Auth-Token");
  if (refreshedToken && authSession) {
    setStoredAuthSession({
      ...authSession,
      token: refreshedToken,
      expires_at: response.headers.get("X-Auth-Expires-At") ?? authSession.expires_at,
      max_expires_at: response.headers.get("X-Auth-Max-Expires-At") ?? authSession.max_expires_at,
    });
  }

  if (!response.ok) {
    if (response.status === 401) {
      clearStoredAuthSession();
    }
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? `Request failed with status ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const apiClient = {
  login(username: string, password: string) {
    return request<AuthSession>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  },
  logout() {
    return request<void>("/api/auth/logout", { method: "POST" });
  },
  getMe() {
    return request<{ user: CurrentUser; expires_at: string; max_expires_at: string }>("/api/auth/me");
  },
  changePassword(currentPassword: string | null, newPassword: string, confirmPassword: string) {
    return request<AuthSession>("/api/auth/change-password", {
      method: "POST",
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      }),
    });
  },
  listAdminUsers() {
    return request<AdminUser[]>("/api/admin/users");
  },
  createAdminUser(payload: { username: string; displayname: string; role: "user" | "admin" | "student" }) {
    return request<AdminUser>("/api/admin/users", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  updateAdminUser(userId: number, payload: Partial<Pick<AdminUser, "displayname" | "role" | "status" | "force_password_change">>) {
    return request<AdminUser>(`/api/admin/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },
  listLearningPaths() {
    return request<LearningPathResponse>("/api/learning-paths");
  },
  createLearningPath(payload: {
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
    return request<LearningPath>("/api/learning-paths", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  getLearningPath(pathId: string) {
    return request<LearningPath>(`/api/learning-paths/${pathId}`);
  },
  updateLearningPath(
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
    return request<LearningPath>(`/api/learning-paths/${pathId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },
  deleteLearningPath(pathId: string) {
    return request<LearningPath>(`/api/learning-paths/${pathId}`, { method: "DELETE" });
  },
  createLearningModule(
    pathId: string,
    payload: { title: string; description: string; learning_objectives: string[] },
  ) {
    return request<LearningModule>(`/api/learning-paths/${pathId}/modules`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  reorderLearningModules(pathId: string, modules: Array<{ id: string; order_index: number }>) {
    return request<LearningModule[]>(`/api/learning-paths/${pathId}/modules/reorder`, {
      method: "PATCH",
      body: JSON.stringify({ modules }),
    });
  },
  updateLearningModule(
    moduleId: string,
    payload: Partial<{ title: string; description: string; learning_objectives: string[] }>,
  ) {
    return request<LearningModule>(`/api/learning-modules/${moduleId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },
  deleteLearningModule(moduleId: string) {
    return request<LearningModule>(`/api/learning-modules/${moduleId}`, { method: "DELETE" });
  },
  createLearningLesson(
    moduleId: string,
    payload: { title: string; description: string; objectives: string[]; teaching_notes: string },
  ) {
    return request<LearningLesson>(`/api/learning-modules/${moduleId}/lessons`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  reorderLearningLessons(moduleId: string, lessons: Array<{ id: string; order_index: number }>) {
    return request<LearningLesson[]>(`/api/learning-modules/${moduleId}/lessons/reorder`, {
      method: "PATCH",
      body: JSON.stringify({ lessons }),
    });
  },
  updateLearningLesson(
    lessonId: string,
    payload: Partial<{ title: string; description: string; objectives: string[]; teaching_notes: string }>,
  ) {
    return request<LearningLesson>(`/api/learning-lessons/${lessonId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },
  deleteLearningLesson(lessonId: string) {
    return request<LearningLesson>(`/api/learning-lessons/${lessonId}`, {
      method: "DELETE",
    });
  },
  deleteAdminUser(userId: number) {
    return request<AdminUser>(`/api/admin/users/${userId}`, { method: "DELETE" });
  },
  createChat() {
    return request<Chat>("/api/chats", { method: "POST" });
  },
  listChats() {
    return request<Chat[]>("/api/chats");
  },
  listArchivedChats() {
    return request<Chat[]>("/api/chats/archived");
  },
  renameChat(chatId: string, payload: ChatUpdate) {
    return request<Chat>(`/api/chats/${chatId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },
  archiveChat(chatId: string) {
    return request<Chat>(`/api/chats/${chatId}/archive`, { method: "PATCH" });
  },
  unarchiveChat(chatId: string) {
    return request<Chat>(`/api/chats/${chatId}/unarchive`, { method: "PATCH" });
  },
  deleteChat(chatId: string) {
    return request<Chat>(`/api/chats/${chatId}`, { method: "DELETE" });
  },
  listGpts() {
    return request<Gpt[]>("/api/gpts");
  },
  createGpt(payload: GptUpsert) {
    return request<Gpt>("/api/gpts", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  getGpt(gptId: string) {
    return request<Gpt>(`/api/gpts/${gptId}`);
  },
  updateGpt(gptId: string, payload: Partial<GptUpsert>) {
    return request<Gpt>(`/api/gpts/${gptId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },
  deleteGpt(gptId: string) {
    return request<GptDeleteResponse>(`/api/gpts/${gptId}`, { method: "DELETE" });
  },
  getGptChat(gptId: string) {
    return request<GptChat>(`/api/gpts/${gptId}/chat`);
  },
  clearGptChat(gptId: string) {
    return request<GptChat>(`/api/gpts/${gptId}/chat`, { method: "DELETE" });
  },
  sendGptMessage(gptId: string, message: string, attachments: File[]) {
    if (attachments.length === 0) {
      return request<MessageResponse>(`/api/gpts/${gptId}/messages`, {
        method: "POST",
        body: JSON.stringify({ message }),
      });
    }

    const formData = new FormData();
    formData.append("message", message);
    attachments.forEach((file) => formData.append("files", file));
    return request<MessageResponse>(`/api/gpts/${gptId}/messages`, {
      method: "POST",
      body: formData,
    });
  },
  previewGptMessage(payload: GptPreviewRequest) {
    return request<MessageResponse>("/api/gpts/preview/messages", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  downloadGptChat(gptId: string) {
    return request<ChatDownload>(`/api/gpts/${gptId}/download`);
  },
  downloadChat(chatId: string) {
    return request<ChatDownload>(`/api/chats/${chatId}/download`);
  },
  getMessages(chatId: string) {
    return request<Message[]>(`/api/chats/${chatId}/messages`);
  },
  sendMessage(chatId: string, message: string, attachments: File[], assistantMode: AssistantMode) {
    if (attachments.length === 0) {
      return request<MessageResponse>(`/api/chats/${chatId}/messages`, {
        method: "POST",
        body: JSON.stringify({ message, assistant_mode: assistantMode }),
      });
    }

    const formData = new FormData();
    formData.append("message", message);
    formData.append("assistant_mode", assistantMode);
    attachments.forEach((file) => formData.append("files", file));
    return request<MessageResponse>(`/api/chats/${chatId}/messages`, {
      method: "POST",
      body: formData,
    });
  },
  getSettings() {
    return request<Settings>("/api/settings");
  },
  updateSettings(payload: SettingsUpdate) {
    return request<Settings>("/api/settings", {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },
  getPersonalization() {
    return request<Personalization>("/api/personalization");
  },
  updatePersonalization(payload: PersonalizationUpdate) {
    return request<Personalization>("/api/personalization", {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },
  listLibraryFiles(options?: { includeOtherUsers?: boolean }) {
    const includeOtherUsers = options?.includeOtherUsers ?? false;
    return request<LibraryResponse>(`/api/library/files?include_other_users=${includeOtherUsers ? "true" : "false"}`);
  },
  updateLibraryFile(fileId: number, payload: { is_enabled: boolean }) {
    return request<LibraryFile>(`/api/library/files/${fileId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },
  deleteLibraryFile(fileId: number) {
    return request<LibraryFile>(`/api/library/files/${fileId}`, { method: "DELETE" });
  },
  uploadLibraryFiles(files: File[], tagsByFile: Record<string, string[]>) {
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));
    formData.append("tags_by_file", JSON.stringify(tagsByFile));
    return request<LibraryUploadResponse>("/api/library/files/upload", {
      method: "POST",
      body: formData,
    });
  },
  listUserFiles() {
    return request<FilterFileResponse>("/api/user/files");
  },
  updateUserFile(fileId: number, payload: { is_enabled: boolean }) {
    return request<FilterFile>(`/api/user/files/${fileId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },
  listChatFiles(chatId: string) {
    return request<FilterFileResponse>(`/api/chats/${chatId}/files`);
  },
  updateChatFile(chatId: string, fileId: number, payload: { is_enabled: boolean }) {
    return request<FilterFile>(`/api/chats/${chatId}/files/${fileId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },
  listUserTags() {
    return request<FilterTagResponse>("/api/user/tags");
  },
  updateUserTag(tag: string, payload: { is_enabled: boolean }) {
    return request<FilterTag>(`/api/user/tags/${encodeURIComponent(tag)}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },
  listChatTags(chatId: string) {
    return request<FilterTagResponse>(`/api/chats/${chatId}/tags`);
  },
  updateChatTag(chatId: string, tag: string, payload: { is_enabled: boolean }) {
    return request<FilterTag>(`/api/chats/${chatId}/tags/${encodeURIComponent(tag)}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },
};
