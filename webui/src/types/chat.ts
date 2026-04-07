export type Role = "user" | "admin" | "student";

export type CurrentUser = {
  id: number;
  username: string;
  displayname: string;
  role: Role;
  status: "active" | "inactive" | string;
  force_password_change: boolean;
};

export type AuthSession = {
  token: string;
  expires_at: string;
  max_expires_at: string;
  user: CurrentUser;
};

export type AdminUser = CurrentUser & {
  created_at: string;
  updated_at: string;
};

export type Chat = {
  id: string;
  chat_name: string;
  chat_type: "normal" | "gpt" | "learning" | string;
  learning_path_id?: string | null;
  gpt_id?: string | null;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
};

export type ChatUpdate = {
  chat_name: string;
};

export type Source = {
  chunk_id: string;
  file_name: string;
  file_path: string;
  title: string | null;
  chapter: string | null;
  section: string | null;
  page_number: number | null;
  score: number;
  tags: string[];
};

export type AttachmentMeta = {
  file_name: string;
  file_type: string;
  extraction_method: string | null;
  quality: Record<string, unknown>;
};

export type Message = {
  id: string;
  chat_id: string;
  gpt_id?: string | null;
  role: "user" | "assistant";
  content: string;
  status: "pending" | "completed" | "error" | string;
  has_attachments: boolean;
  created_at: string;
  sources: Source[];
  attachments: AttachmentMeta[];
  error?: string;
};

export type MessageResponse = {
  chat_id: string;
  gpt_id?: string | null;
  user_message: Message;
  assistant_message: Message;
  assistant_mode: AssistantMode;
  sources: Source[];
  attachments_used: AttachmentMeta[];
};

export type AssistantMode = "simple" | "refine" | "thinking";

export type Settings = {
  chat_history_messages_count: number;
  max_similarities: number;
  min_similarities: number;
  similarity_score_threshold: number;
  default_assistant_mode: AssistantMode;
  available_assistant_modes: AssistantMode[];
};

export type SettingsUpdate = {
  chat_history_messages_count: number;
  max_similarities: number;
  min_similarities: number;
  similarity_score_threshold: number;
};

export type PersonalizationBaseStyle =
  | "default"
  | "professional"
  | "friendly"
  | "direct"
  | "quirky"
  | "efficient"
  | "sceptical";

export type PersonalizationLevel = "more" | "default" | "less";

export type Personalization = {
  base_style: PersonalizationBaseStyle;
  warm: PersonalizationLevel;
  enthusiastic: PersonalizationLevel;
  headers_and_lists: PersonalizationLevel;
  custom_instructions: string;
  nickname: string;
  occupation: string;
  more_about_user: string;
};

export type PersonalizationUpdate = Personalization;

export type DownloadMessage = {
  role: "user" | "assistant" | string;
  content: string;
  created_at: string;
  sources: Source[];
  attachments: AttachmentMeta[];
};

export type ChatDownload = {
  chat_id: string;
  chat_name: string;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  messages: DownloadMessage[];
};

export type LibraryFile = {
  id: number;
  file_name: string;
  file_path: string;
  file_type: string;
  extension: string;
  size_bytes: number;
  chunk_count: number;
  tags: string[];
  is_embedded: boolean;
  is_enabled: boolean;
  is_system: boolean;
  is_global: boolean;
  source_origin: string;
  uploaded_by_user_id: number | null;
  owner_user_id: number | null;
  owner_username: string | null;
  owner_displayname: string | null;
  is_owned_by_current_user: boolean;
  can_delete: boolean;
  can_disable: boolean;
  can_toggle_enabled: boolean;
  processing_status: string;
  updated_at: string;
};

export type LibrarySummary = {
  total_files: number;
  embedded_files: number;
  total_chunks: number;
};

export type LibraryResponse = {
  files: LibraryFile[];
  summary: LibrarySummary;
  allowed_extensions: string[];
  max_upload_files: number;
  upload_max_file_size_mb: number;
  default_tag: string;
};

export type LibraryUploadResponse = {
  files: LibraryFile[];
};

export type FilterFile = {
  file_id: number;
  file_name: string;
  file_path: string;
  tags: string[];
  global_is_enabled: boolean;
  scoped_is_enabled: boolean;
  is_enabled: boolean;
  is_locked: boolean;
  updated_at: string;
};

export type FilterFileResponse = {
  files: FilterFile[];
};

export type FilterTag = {
  tag: string;
  file_count: number;
  global_is_enabled: boolean;
  scoped_is_enabled: boolean;
  is_enabled: boolean;
  is_locked: boolean;
};

export type FilterTagResponse = {
  tags: FilterTag[];
};

export type GptPersonalization = Pick<Personalization, "base_style" | "warm" | "enthusiastic" | "headers_and_lists">;

export type GptSettings = {
  chat_history_messages_count: number;
  max_similarities: number;
  min_similarities: number;
  similarity_score_threshold: number;
};

export type GptFileSetting = {
  file_id: number;
  is_enabled: boolean;
};

export type GptTagSetting = {
  tag: string;
  is_enabled: boolean;
};

export type GptConfig = {
  personalization: GptPersonalization;
  settings: GptSettings;
  files_enabled: boolean;
  tags_enabled: boolean;
  file_settings: GptFileSetting[];
  tag_settings: GptTagSetting[];
};

export type Gpt = {
  id: string;
  name: string;
  description: string;
  instructions: string;
  assistant_mode: AssistantMode;
  chat_id: string | null;
  created_at: string;
  updated_at: string;
  config: GptConfig;
};

export type GptUpsert = {
  name: string;
  description: string;
  instructions: string;
  assistant_mode: AssistantMode;
  config: GptConfig;
};

export type GptChat = {
  gpt: Gpt;
  messages: Message[];
};

export type GptDeleteResponse = {
  id: string;
  deleted: boolean;
};

export type GptPreviewRequest = {
  message: string;
  gpt: GptUpsert;
  preview_messages: Message[];
};

export type LearningPathScope = "global" | "user";
export type LearningPathStatus = "draft" | "published" | "archived";

export type LearningLesson = {
  id: string;
  module_id: string;
  order_index: number;
  title: string;
  description: string;
  objectives: string[];
  teaching_notes: string;
  created_at: string;
  updated_at: string;
};

export type LearningModule = {
  id: string;
  learning_path_id: string;
  order_index: number;
  title: string;
  description: string;
  learning_objectives: string[];
  lessons: LearningLesson[];
  created_at: string;
  updated_at: string;
};

export type LearningPath = {
  id: string;
  scope: LearningPathScope | string;
  owner_user_id: number | null;
  title: string;
  description: string;
  subject: string;
  difficulty_level: string;
  estimated_duration_minutes: number | null;
  status: LearningPathStatus | string;
  allowed_file_ids: number[];
  allowed_tags: string[];
  modules: LearningModule[];
  can_edit: boolean;
  can_delete: boolean;
  created_at: string;
  updated_at: string;
};

export type LearningPathResponse = {
  paths: LearningPath[];
};

export type LearningPreferencePace = "slow" | "balanced" | "fast";
export type LearningPreferenceDepth = "concise" | "balanced" | "detailed";
export type LearningPreferenceExamplesTheory = "more_examples" | "balanced" | "more_theory";
export type LearningPreferenceStructure = "more_structured" | "balanced" | "more_conversational";
export type LearningPreferenceFrequency = "low" | "medium" | "high";
export type LearningPreferenceEncouragement = "low" | "balanced" | "high";
export type LearningPreferenceGuidance = "step_by_step" | "balanced" | "more_independent";
export type LearningPreferenceFormat = "reading" | "dialogue" | "exercises" | "mixed";
export type LearningGoalPriority = "low" | "medium" | "high";

export type LearningPreferences = {
  preferred_pace: LearningPreferencePace;
  explanation_depth: LearningPreferenceDepth;
  examples_vs_theory: LearningPreferenceExamplesTheory;
  structure_preference: LearningPreferenceStructure;
  checkpoint_frequency: LearningPreferenceFrequency;
  encouragement_level: LearningPreferenceEncouragement;
  guidance_level: LearningPreferenceGuidance;
  recap_frequency: LearningPreferenceFrequency;
  preferred_learning_format: LearningPreferenceFormat;
  custom_preference_note: string;
  updated_at: string | null;
};

export type LearningProfileContext = {
  profile_display_name: string;
  about_me: string;
  contact_location: string;
  general_title: string;
  date_of_birth: string;
  current_skill_areas: string[];
  skills: string[];
  interests: string[];
  work_experience: string[];
  education_history: string[];
  current_reason_for_learning: string;
  preferred_form_of_address: string;
  learning_context_notes: string;
  updated_at: string | null;
};

export type LearningGoal = {
  id: string;
  target_topic: string;
  reason_for_learning: string;
  target_level: string;
  deadline: string | null;
  priority: LearningGoalPriority | null;
  notes: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type LearningProfileBundle = {
  preferences: LearningPreferences;
  context: LearningProfileContext;
  goals: LearningGoal[];
  diagnostics_status: "not_started" | "in_progress" | "completed";
};

export type DiagnosticQuestionType = "single_choice" | "multi_choice" | "likert" | "slider" | "text";

export type DiagnosticOption = {
  key: string;
  label: string;
  value: string | null;
  allows_text: boolean;
};

export type DiagnosticQuestion = {
  id: string;
  text: string;
  type: DiagnosticQuestionType;
  options: DiagnosticOption[];
  min_value: number | null;
  max_value: number | null;
};

export type DiagnosticSection = {
  id: string;
  title: string;
  questions: DiagnosticQuestion[];
};

export type DiagnosticDefinition = {
  id: string;
  type: "LAA" | "MOA" | "LTA";
  title: string;
  version: string;
  sections: DiagnosticSection[];
};

export type DiagnosticCatalog = {
  definitions: DiagnosticDefinition[];
};

export type DiagnosticAttemptStart = {
  attempt_id: string;
  status: string;
  definition_versions: Record<string, string>;
  started_at: string;
};

export type DiagnosticAttemptSummary = {
  attempt_id: string;
  status: string;
  definition_versions: Record<string, string>;
  started_at: string;
  completed_at: string | null;
  is_latest: boolean;
};

export type DiagnosticAttemptDetails = {
  attempt: DiagnosticAttemptSummary;
  answers: Record<string, Record<string, unknown>>;
  result: Record<string, unknown> | null;
};

export type DiagnosticResult = {
  attempt_id: string;
  result: Record<string, unknown>;
};

export type LearningStateCheck = {
  id: number;
  user_id: number;
  chat_id: string | null;
  mood: string;
  perceived_difficulty: string;
  needs_pause_or_input: string;
  preferred_format: string;
  notes: string;
  created_at: string;
};

export type ExplanationFeedback = {
  id: number;
  user_id: number;
  message_id: number | null;
  rating: number;
  feedback_text: string;
  re_explain_requested: boolean;
  created_at: string;
};

export type SystemServiceStatus = {
  key: "webui" | "retriever" | "embedder" | "knowledge_base" | "database" | string;
  label: string;
  description: string;
  status: "ok" | "warn" | "error" | string;
  detail: string;
};

export type SystemStatus = {
  checked_at: string;
  services: SystemServiceStatus[];
};
