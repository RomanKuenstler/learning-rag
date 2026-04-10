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
export type SkilltreeNodeType =
  | "learning_unit"
  | "practice"
  | "quiz"
  | "checkpoint"
  | "review"
  | "milestone"
  | "capstone"
  | "unlock_gate"
  | "assessment_hook";
export type SkilltreeNodeCompletionMode =
  | "lesson_complete"
  | "manual"
  | "practice_complete"
  | "quiz_pass"
  | "checkpoint_pass"
  | "review_complete"
  | "assessment_threshold"
  | "gate_unlock";
export type SkilltreeNodeProgressState =
  | "locked"
  | "available"
  | "in_progress"
  | "completed"
  | "mastered"
  | "optional_skipped"
  | "failed_needs_retry"
  | "awaiting_checkpoint";

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
  schema_version: number;
  allowed_file_ids: number[];
  allowed_tags: string[];
  chapters: SkilltreeChapter[];
  branches: SkilltreeBranch[];
  nodes: SkilltreeNode[];
  edges: SkilltreeEdge[];
  entry_node_ids: string[];
  completion_rules: Record<string, unknown>;
  visual_layout: Record<string, unknown>;
  metadata: Record<string, unknown>;
  node_progress: Record<string, SkilltreeNodeProgressState | string>;
  node_runtime: Record<string, SkilltreeNodeRuntime>;
  chapter_progress: SkilltreeChapterProgress[];
  branch_progress: SkilltreeBranchProgress[];
  completion_summary: SkilltreeCompletionSummary | null;
  recommendations: SkilltreeRecommendation | null;
  hook_summary: SkilltreeHookSummary | null;
  modules: LearningModule[];
  can_edit: boolean;
  can_delete: boolean;
  created_at: string;
  updated_at: string;
};

export type LearningPathResponse = {
  paths: LearningPath[];
};

export type CourseSort =
  | "name_asc"
  | "name_desc"
  | "updated_desc"
  | "updated_asc"
  | "modules_desc"
  | "lessons_desc"
  | "scope_global_first"
  | "scope_user_first";

export type CourseListItem = {
  id: string;
  title: string;
  description: string;
  scope: LearningPathScope | string;
  owner_user_id: number | null;
  owner_username: string | null;
  owner_displayname: string | null;
  status: LearningPathStatus | string;
  subject: string;
  difficulty_level: string;
  schema_version: number;
  chapter_count: number;
  node_count: number;
  module_count: number;
  lesson_count: number;
  updated_at: string;
  created_at: string;
};

export type SkilltreeNodePrerequisites = {
  requires_all: string[];
  requires_any: string[];
  recommended: string[];
};

export type SkilltreeNodeKsa = {
  dimension: "K" | "S" | "A";
  topic: string;
  subtopic: string | null;
  start_level: number | null;
  target_level: number | null;
  contribution_weight: number | null;
  unlocks_assessment_check: boolean;
  recommends_assessment_check: boolean;
};

export type SkilltreeNodeUnlocks = {
  node_ids: string[];
  branch_ids: string[];
  recommended_next_node_ids: string[];
};

export type SkilltreeNodeRewards = {
  estimated_ksa_gain: Record<string, number>;
  effort_score: number | null;
  reward_tags: string[];
};

export type SkilltreeNodeRetrospectiveHooks = {
  retrospective_after: boolean;
  review_recommended: boolean;
  recap_checkpoint_available: boolean;
};

export type SkilltreeNodeKsaHooks = {
  mini_assessment_available: boolean;
  recommended_reassessment_topics: string[];
  unlocks_deeper_refinement: boolean;
};

export type SkilltreeNodeRemediation = {
  is_remediation_node: boolean;
  recommended_if_failed_node_ids: string[];
  supports_review_for_node_ids: string[];
};

export type SkilltreeNodeAdaptiveUnlockRule = {
  ksa_thresholds: Array<Record<string, unknown>>;
  requires_branch_completion_ids: string[];
  requires_checkpoint_node_ids: string[];
  requires_review_recommended: boolean;
  recommended_only: boolean;
};

export type SkilltreeNodeLayout = {
  x: number;
  y: number;
};

export type SkilltreeNode = {
  id: string;
  title: string;
  description: string;
  type: SkilltreeNodeType;
  chapter_id: string | null;
  branch_id: string | null;
  required: boolean;
  prerequisites: SkilltreeNodePrerequisites;
  completion_mode: SkilltreeNodeCompletionMode;
  estimated_duration_minutes: number | null;
  layout: SkilltreeNodeLayout;
  metadata: Record<string, unknown>;
  display: Record<string, unknown>;
  ksa: SkilltreeNodeKsa[];
  unlocks: SkilltreeNodeUnlocks;
  rewards: SkilltreeNodeRewards;
  retrospective_hooks: SkilltreeNodeRetrospectiveHooks;
  ksa_hooks: SkilltreeNodeKsaHooks;
  remediation: SkilltreeNodeRemediation;
  adaptive_unlock: SkilltreeNodeAdaptiveUnlockRule;
};

export type SkilltreeEdge = {
  from_node_id: string;
  to_node_id: string;
  relationship: "requires_all" | "requires_any" | "recommended" | "optional";
};

export type SkilltreeChapter = {
  id: string;
  title: string;
  description: string;
  order_index: number;
  metadata: Record<string, unknown>;
};

export type SkilltreeBranch = {
  id: string;
  title: string;
  description: string;
  required: boolean;
  metadata: Record<string, unknown>;
};

export type SkilltreeChapterProgress = {
  chapter_id: string;
  title: string;
  required_total: number;
  required_completed: number;
  optional_total: number;
  optional_completed: number;
  is_complete: boolean;
};

export type SkilltreeCompletionSummary = {
  required_total: number;
  required_completed: number;
  optional_total: number;
  optional_completed: number;
  required_branch_total: number;
  required_branch_completed: number;
  global_capstone_total: number;
  global_capstone_completed: number;
  is_complete: boolean;
};

export type SkilltreeBranchProgress = {
  branch_id: string;
  title: string;
  required: boolean;
  required_total: number;
  required_completed: number;
  optional_total: number;
  optional_completed: number;
  is_complete: boolean;
};

export type SkilltreeRecommendation = {
  next_best_node_id: string | null;
  next_branch_id: string | null;
  suggested_optional_node_id: string | null;
  suggested_review_node_id: string | null;
  suggested_ksa_assessment_node_id: string | null;
  rationale: string[];
};

export type SkilltreeHookSummary = {
  retrospective_node_ids: string[];
  review_node_ids: string[];
  ksa_assessment_node_ids: string[];
  remediation_candidate_node_ids: string[];
  adaptive_unlock_candidate_node_ids: string[];
};

export type SkilltreeNodeRuntime = {
  blocked_by_all: string[];
  blocked_by_any: string[];
  is_entry: boolean;
  is_parallel_available: boolean;
  awaiting_checkpoint: boolean;
  capstone_locked: boolean;
  optional_branch: boolean;
  completion_allowed: boolean;
};

export type CourseListResponse = {
  courses: CourseListItem[];
  total: number;
};

export type CourseImportFileResult = {
  file_name: string;
  scope: LearningPathScope | string;
  success: boolean;
  course_id: string | null;
  title: string | null;
  error: string | null;
};

export type CourseImportResponse = {
  imported_count: number;
  failed_count: number;
  results: CourseImportFileResult[];
};

export type CourseTemplateResponse = {
  file_name: string;
  template: Record<string, unknown>;
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

export type KSAValue = 1 | 2 | 3 | 4 | 5;

export type KSAKnowledge = {
  stem_fundamentals: KSAValue;
  information_technology: KSAValue;
  humanities_social_sciences: KSAValue;
  languages_linguistics: KSAValue;
  business_commerce: KSAValue;
  legal_ethics: KSAValue;
  health_wellness: KSAValue;
};

export type KSASkills = {
  literacy_numeracy: KSAValue;
  digital_craft: KSAValue;
  strategic_execution: KSAValue;
  operational_skills: KSAValue;
  relational_skills: KSAValue;
  research_inquiry: KSAValue;
};

export type KSAAbilities = {
  quantitative_reasoning: KSAValue;
  verbal_comprehension: KSAValue;
  spatial_visualization: KSAValue;
  executive_function: KSAValue;
  sensory_perceptual: KSAValue;
  social_emotional_capacity: KSAValue;
  divergent_thinking: KSAValue;
};

export type KSAProfile = {
  user_id: number;
  has_assessment: boolean;
  profile_source: "student_default_baseline" | "placeholder_baseline" | "assessment";
  scale_min: 1;
  scale_max: 5;
  dreyfus_levels: string[];
  knowledge: KSAKnowledge;
  skills: KSASkills;
  abilities: KSAAbilities;
  assessment_details?: Record<string, unknown> | null;
  drill_state?: Record<string, unknown> | null;
  learning_speed_multiplier?: number | null;
  updated_at: string | null;
};

export type KsaAssessmentDefinition = {
  version: string;
  time_limit_seconds: number;
  phase1_sliders: Array<{
    id: string;
    key: string;
    topic: string;
    prompt: string;
    min: number;
    max: number;
    triggers: string[];
  }>;
  knowledge_questions: Array<{
    id: string;
    topic: string;
    difficulty: "easy" | "hard" | string;
    question: string;
    options: string[];
  }>;
  skill_questions: Array<{
    id: string;
    topic: string;
    scenario: string;
    choice_a: string;
    choice_b: string;
  }>;
  ability_questions: Array<{
    id: string;
    topic: string;
    task: string;
    expected: string;
    open_ended: boolean;
  }>;
};

export type KsaAssessmentAttempt = {
  attempt_id: string;
  status: "in_progress" | "completed";
  version: string;
  started_at: string;
  completed_at: string | null;
  answers: Record<string, unknown>;
  result: Record<string, unknown> | null;
};

export type KsaDrillTopic = {
  key: string;
  group: "knowledge" | "skills" | "abilities";
  name: string;
  subtopics: string[];
  archetype_subtopics: string[];
};

export type KsaDrillQuestion = {
  id: string;
  topic_key: string;
  topic_name: string;
  topic_group: "knowledge" | "skills" | "abilities";
  block_index: number;
  block_label: string;
  question_index: number;
  kind: "recalibration" | "threshold" | "sidestep" | "stress_test";
  archetype: "reverse_definition" | "spot_the_flaw" | "analogy_match" | "power_sprint";
  focus_subtopic: string;
  related_subtopic?: string | null;
  prompt: string;
  time_limit_seconds?: number | null;
  topic_source?: "manual" | "auto_good" | "auto_bad" | "user_core" | "user_variant" | "llm_stretch" | "llm_growth" | null;
  choices?: string[];
  correct_answer?: string | null;
  distractors?: string[];
};

export type KsaDrillTopicClassification = {
  primary_type: "K" | "S" | "A";
  secondary_type?: "K" | "S" | "A" | null;
  type_combo: "K" | "S" | "A" | "K+S" | "K+A" | "S+A" | "K+S+A";
  big_map_group: "Knowledge" | "Skills" | "Abilities";
  big_map_subdomain: string;
  detailed_topic: string;
  user_explanation: string;
};

export type KsaDrillRound = {
  round_number: 1 | 2 | 3 | 4;
  origin: "user_core" | "user_variant" | "llm_stretch" | "llm_growth";
  type_combo: string;
  big_map_group: "Knowledge" | "Skills" | "Abilities";
  big_map_subdomain: string;
  detailed_topic: string;
  rationale?: string;
  questions: KsaDrillQuestion[];
};

export type KsaDrillAttempt = {
  attempt_id: string;
  status: "in_progress" | "completed";
  version: string;
  selected_topic_keys: string[];
  question_set: KsaDrillQuestion[];
  source_topic_input?: string | null;
  topic_classification?: KsaDrillTopicClassification | null;
  rounds?: KsaDrillRound[];
  started_at: string;
  completed_at: string | null;
  answers: Record<string, unknown>;
  result: Record<string, unknown> | null;
};

export type KsaDrillAttemptsResponse = {
  attempts: KsaDrillAttempt[];
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
