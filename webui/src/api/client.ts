import type {
  AdminUser,
  AssistantMode,
  AuthSession,
  Chat,
  DiagnosticAttemptDetails,
  DiagnosticAttemptStart,
  DiagnosticAttemptSummary,
  DiagnosticCatalog,
  DiagnosticDefinition,
  DiagnosticResult,
  ExplanationFeedback,
  ChatDownload,
  ChatUpdate,
  CourseImportResponse,
  CourseListResponse,
  CourseSort,
  CourseTemplateResponse,
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
  LearningNodeSession,
  LearningNodeExecutionAttempt,
  LearningNodeExecutionStartResponse,
  LearningNodeSessionDownload,
  LearningNodeSessionListResponse,
  LearningGoal,
  LearningGoalPriority,
  LearningProfileBundle,
  KsaDrillAttempt,
  KsaDrillAttemptsResponse,
  KsaDrillTopicClassification,
  KsaDrillTopic,
  KsaAssessmentAttempt,
  KsaAssessmentDefinition,
  KSAProfile,
  LearningProfileContext,
  LearningPreferences,
  LearningPath,
  LearningPathResponse,
  LearningStateCheck,
  Message,
  MessageResponse,
  Personalization,
  PersonalizationUpdate,
  Settings,
  SettingsUpdate,
  SystemStatus,
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
  getSystemStatus() {
    return request<SystemStatus>("/api/system/status");
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
  listCourses(params?: {
    search?: string;
    scope?: "global" | "user" | "all";
    status?: "draft" | "published" | "archived" | "all";
    owner_user_id?: number;
    sort?: CourseSort;
  }) {
    const query = new URLSearchParams();
    if (params?.search?.trim()) {
      query.set("search", params.search.trim());
    }
    if (params?.scope && params.scope !== "all") {
      query.set("scope", params.scope);
    }
    if (params?.status && params.status !== "all") {
      query.set("status", params.status);
    }
    if (params?.owner_user_id) {
      query.set("owner_user_id", String(params.owner_user_id));
    }
    if (params?.sort) {
      query.set("sort", params.sort);
    }
    const queryString = query.toString();
    return request<CourseListResponse>(`/api/courses${queryString ? `?${queryString}` : ""}`);
  },
  getCourseTemplate() {
    return request<CourseTemplateResponse>("/api/courses/template");
  },
  importCourseFiles(files: File[], scopesByFile: Record<string, "global" | "user">) {
    const formData = new FormData();
    for (const file of files) {
      formData.append("files", file);
    }
    formData.append("scopes_by_file", JSON.stringify(scopesByFile));
    return request<CourseImportResponse>("/api/courses/import", {
      method: "POST",
      body: formData,
    });
  },
  getLearningProfile() {
    return request<LearningProfileBundle>("/api/learning-profile");
  },
  getKsaProfile() {
    return request<KSAProfile>("/api/learning-profile/ksa");
  },
  getKsaAssessmentDefinition() {
    return request<KsaAssessmentDefinition>("/api/ksa/assessment/definition");
  },
  startKsaAssessment() {
    return request<{ attempt_id: string; status: "in_progress" | "completed"; version: string; started_at: string }>(
      "/api/ksa/assessment/attempts",
      { method: "POST" },
    );
  },
  getLatestKsaAssessmentAttempt() {
    return request<KsaAssessmentAttempt>("/api/ksa/assessment/attempts/latest");
  },
  getKsaAssessmentAttempt(attemptId: string) {
    return request<KsaAssessmentAttempt>(`/api/ksa/assessment/attempts/${attemptId}`);
  },
  upsertKsaAssessmentAnswers(attemptId: string, answers: Record<string, unknown>) {
    return request<KsaAssessmentAttempt>(`/api/ksa/assessment/attempts/${attemptId}/answers`, {
      method: "PUT",
      body: JSON.stringify({ answers }),
    });
  },
  completeKsaAssessment(attemptId: string) {
    return request<KSAProfile>(`/api/ksa/assessment/attempts/${attemptId}/complete`, { method: "POST" });
  },
  getKsaDrillTopics() {
    return request<{ topics: KsaDrillTopic[] }>("/api/ksa/drills/topics");
  },
  classifyKsaDrillTopic(sourceTopicInput: string) {
    return request<{ source_topic_input: string; classification: KsaDrillTopicClassification }>(
      "/api/ksa/drills/classify-topic",
      {
        method: "POST",
        body: JSON.stringify({ source_topic_input: sourceTopicInput }),
      },
    );
  },
  startKsaDrillAttempt(payload: { source_topic_input: string; topic_classification: KsaDrillTopicClassification }) {
    return request<{ attempt_id: string; status: "in_progress" | "completed"; version: string; selected_topic_keys: string[]; question_set: KsaDrillAttempt["question_set"]; source_topic_input?: string | null; topic_classification?: KsaDrillTopicClassification | null; rounds?: KsaDrillAttempt["rounds"]; started_at: string }>(
      "/api/ksa/drills/attempts",
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    );
  },
  getLatestKsaDrillAttempt() {
    return request<KsaDrillAttempt>("/api/ksa/drills/attempts/latest");
  },
  getKsaDrillAttempts(limit = 25) {
    return request<KsaDrillAttemptsResponse>(`/api/ksa/drills/attempts?limit=${Math.max(1, Math.min(100, limit))}`);
  },
  getKsaDrillAttempt(attemptId: string) {
    return request<KsaDrillAttempt>(`/api/ksa/drills/attempts/${attemptId}`);
  },
  upsertKsaDrillAnswers(attemptId: string, answers: Record<string, unknown>) {
    return request<KsaDrillAttempt>(`/api/ksa/drills/attempts/${attemptId}/answers`, {
      method: "PUT",
      body: JSON.stringify({ answers }),
    });
  },
  completeKsaDrillAttempt(attemptId: string) {
    return request<KSAProfile>(`/api/ksa/drills/attempts/${attemptId}/complete`, { method: "POST" });
  },
  updateLearningPreferences(payload: Partial<Omit<LearningPreferences, "updated_at">>) {
    return request<LearningPreferences>("/api/learning-profile/preferences", {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },
  updateLearningContext(payload: Partial<Omit<LearningProfileContext, "updated_at">>) {
    return request<LearningProfileContext>("/api/learning-profile/context", {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },
  createLearningGoal(payload: {
    target_topic: string;
    reason_for_learning: string;
    target_level: string;
    deadline: string | null;
    priority: LearningGoalPriority | null;
    notes: string;
    is_active: boolean;
  }) {
    return request<LearningGoal>("/api/learning-profile/goals", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  updateLearningGoal(
    goalId: string,
    payload: Partial<{
      target_topic: string;
      reason_for_learning: string;
      target_level: string;
      deadline: string | null;
      priority: LearningGoalPriority | null;
      notes: string;
      is_active: boolean;
    }>,
  ) {
    return request<LearningGoal>(`/api/learning-profile/goals/${goalId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },
  deleteLearningGoal(goalId: string) {
    return request<LearningGoal>(`/api/learning-profile/goals/${goalId}`, {
      method: "DELETE",
    });
  },
  listDiagnosticDefinitions() {
    return request<DiagnosticCatalog>("/api/diagnostics/definitions");
  },
  getDiagnosticDefinition(diagnosticType: "LAA" | "MOA" | "LTA") {
    return request<DiagnosticDefinition>(`/api/diagnostics/definitions/${diagnosticType}`);
  },
  startDiagnosticAttempt() {
    return request<DiagnosticAttemptStart>("/api/diagnostics/attempts", { method: "POST" });
  },
  listDiagnosticAttempts() {
    return request<DiagnosticAttemptSummary[]>("/api/diagnostics/attempts");
  },
  deleteDiagnosticAttempt(attemptId: string) {
    return request<DiagnosticAttemptSummary>(`/api/diagnostics/attempts/${attemptId}`, { method: "DELETE" });
  },
  getLatestDiagnosticAttempt() {
    return request<DiagnosticAttemptDetails>("/api/diagnostics/attempts/latest");
  },
  getDiagnosticAttempt(attemptId: string) {
    return request<DiagnosticAttemptDetails>(`/api/diagnostics/attempts/${attemptId}`);
  },
  upsertDiagnosticAnswers(attemptId: string, payload: { diagnostic_type: "LAA" | "MOA" | "LTA"; answers: Array<{ question_id: string; value: unknown }> }) {
    return request<DiagnosticAttemptDetails>(`/api/diagnostics/attempts/${attemptId}/answers`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },
  completeDiagnosticAttempt(attemptId: string) {
    return request<DiagnosticResult>(`/api/diagnostics/attempts/${attemptId}/complete`, { method: "POST" });
  },
  createLearningStateCheck(payload: {
    chat_id?: string | null;
    mood: string;
    perceived_difficulty: string;
    needs_pause_or_input: string;
    preferred_format: string;
    notes: string;
  }) {
    return request<LearningStateCheck>("/api/learning-state-checks", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  listLearningStateChecks(limit = 20) {
    return request<LearningStateCheck[]>(`/api/learning-state-checks?limit=${limit}`);
  },
  createExplanationFeedback(payload: {
    message_id?: number | null;
    rating: number;
    feedback_text: string;
    re_explain_requested: boolean;
  }) {
    return request<ExplanationFeedback>("/api/explanation-feedback", {
      method: "POST",
      body: JSON.stringify(payload),
    });
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
  updateLearningNodeProgress(
    pathId: string,
    nodeId: string,
    payload: {
      status: "in_progress" | "completed" | "mastered" | "optional_skipped" | "failed_needs_retry" | "reset";
      evidence?: Record<string, unknown>;
    },
  ) {
    return request<LearningPath>(`/api/learning-paths/${pathId}/nodes/${nodeId}/progress`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },
  listLearningNodeSessions() {
    return request<LearningNodeSessionListResponse>("/api/learning-node-sessions");
  },
  listArchivedLearningNodeSessions() {
    return request<LearningNodeSessionListResponse>("/api/learning-node-sessions/archived");
  },
  ensureLearningNodeSession(pathId: string, nodeId: string) {
    return request<LearningNodeSession>(`/api/learning-paths/${pathId}/nodes/${nodeId}/session`, {
      method: "POST",
    });
  },
  startLearningNodeExecution(pathId: string, nodeId: string, forceNewAttempt = false) {
    return request<LearningNodeExecutionStartResponse>(
      `/api/learning-paths/${pathId}/nodes/${nodeId}/execution/start?force_new_attempt=${forceNewAttempt ? "true" : "false"}`,
      { method: "POST" },
    );
  },
  getLatestLearningNodeExecution(pathId: string, nodeId: string) {
    return request<LearningNodeExecutionAttempt>(`/api/learning-paths/${pathId}/nodes/${nodeId}/execution/latest`);
  },
  getLearningNodeSession(sessionId: string, markOpened = false) {
    return request<LearningNodeSession>(`/api/learning-node-sessions/${sessionId}?mark_opened=${markOpened ? "true" : "false"}`);
  },
  archiveLearningNodeSession(sessionId: string) {
    return request<LearningNodeSession>(`/api/learning-node-sessions/${sessionId}/archive`, {
      method: "PATCH",
    });
  },
  unarchiveLearningNodeSession(sessionId: string) {
    return request<LearningNodeSession>(`/api/learning-node-sessions/${sessionId}/unarchive`, {
      method: "PATCH",
    });
  },
  deleteLearningNodeSession(sessionId: string) {
    return request<LearningNodeSession>(`/api/learning-node-sessions/${sessionId}/delete`, {
      method: "PATCH",
    });
  },
  resetLearningNodeSession(sessionId: string) {
    return request<LearningNodeSession>(`/api/learning-node-sessions/${sessionId}/reset`, {
      method: "POST",
    });
  },
  downloadLearningNodeSession(sessionId: string) {
    return request<LearningNodeSessionDownload>(`/api/learning-node-sessions/${sessionId}/download`);
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
