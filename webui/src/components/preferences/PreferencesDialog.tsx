import { useEffect, useMemo, useRef, useState } from "react";
import type {
  AssistantMode,
  Chat,
  FilterTag,
  PersonalizationBaseStyle,
  PersonalizationLevel,
  PersonalizationUpdate,
  SettingsUpdate,
} from "../../types/chat";
import { Icon } from "../common/Icons";
import { Dialog } from "../common/Dialog";
import { FilterTables } from "../filters/FilterTables";

function describeAssistantMode(mode: AssistantMode) {
  if (mode === "simple") {
    return "Single-step retrieval and answer generation.";
  }
  if (mode === "refine") {
    return "Two-stage draft and refinement pipeline.";
  }
  return "Three-stage planning, drafting, and refinement pipeline.";
}

type PreferencesDialogProps = {
  initialTab?: "general" | "personalization" | "settings" | "filter" | "archive";
  archivedChats: Chat[];
  settingsDraft: SettingsUpdate | null;
  personalizationDraft: PersonalizationUpdate | null;
  availableModes: AssistantMode[];
  globalFilterTags: FilterTag[];
  loading: boolean;
  saving: boolean;
  personalizationLoading: boolean;
  personalizationSaving: boolean;
  filterLoading: boolean;
  filterError: string | null;
  filterBusyKeys: string[];
  error: string | null;
  success: string | null;
  personalizationError: string | null;
  personalizationSuccess: string | null;
  onClose: () => void;
  onDownloadChat: (chatId: string) => void;
  onUnarchiveChat: (chatId: string) => void;
  onDeleteChat: (chatId: string) => void;
  onFieldChange: (patch: Partial<SettingsUpdate>) => void;
  onPersonalizationFieldChange: (patch: Partial<PersonalizationUpdate>) => void;
  onSaveSettings: () => void;
  onSavePersonalization: () => void;
  onOpenFilterTab: () => void;
  onToggleGlobalTag: (tag: FilterTag, isEnabled: boolean) => void;
  isStudent?: boolean;
  onOpenLearningProfile?: () => void;
};

const BASE_STYLE_OPTIONS: Array<{ value: PersonalizationBaseStyle; label: string }> = [
  { value: "default", label: "Default" },
  { value: "professional", label: "Professional" },
  { value: "friendly", label: "Friendly" },
  { value: "direct", label: "Direct" },
  { value: "quirky", label: "Quirky" },
  { value: "efficient", label: "Efficient" },
  { value: "sceptical", label: "Sceptical" },
];

const LEVEL_OPTIONS: Array<{ value: PersonalizationLevel; label: string }> = [
  { value: "more", label: "More" },
  { value: "default", label: "Default" },
  { value: "less", label: "Less" },
];

const TABS = [
  { id: "general", label: "General", icon: "settings" },
  { id: "personalization", label: "Personalization", icon: "sparkles" },
  { id: "settings", label: "Settings", icon: "settings" },
  { id: "filter", label: "Filter", icon: "filter" },
  { id: "archive", label: "Archive", icon: "archive" },
] as const;

export function PreferencesDialog({
  initialTab = "general",
  archivedChats,
  settingsDraft,
  personalizationDraft,
  availableModes,
  globalFilterTags,
  loading,
  saving,
  personalizationLoading,
  personalizationSaving,
  filterLoading,
  filterError,
  filterBusyKeys,
  error,
  success,
  personalizationError,
  personalizationSuccess,
  onClose,
  onDownloadChat,
  onUnarchiveChat,
  onDeleteChat,
  onFieldChange,
  onPersonalizationFieldChange,
  onSaveSettings,
  onSavePersonalization,
  onOpenFilterTab,
  onToggleGlobalTag,
  isStudent = false,
  onOpenLearningProfile,
}: PreferencesDialogProps) {
  const visibleTabs = useMemo(
    () => (isStudent ? TABS.filter((tab) => tab.id !== "filter" && tab.id !== "settings") : TABS),
    [isStudent],
  );
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]["id"]>(() => (
    visibleTabs.some((tab) => tab.id === initialTab) ? initialTab : "general"
  ));
  const [openPersonalizationDropdown, setOpenPersonalizationDropdown] = useState<string | null>(null);
  const personalizationDropdownRef = useRef<HTMLDivElement | null>(null);
  const settingsValidation = useMemo(() => {
    if (!settingsDraft) {
      return null;
    }
    if (settingsDraft.min_similarities > settingsDraft.max_similarities) {
      return "Min similarities cannot be greater than max similarities.";
    }
    return null;
  }, [settingsDraft]);
  const personalizationSaveDisabled = personalizationLoading || personalizationSaving || !personalizationDraft;

  useEffect(() => {
    function handlePointerDown(event: MouseEvent) {
      if (personalizationDropdownRef.current && !personalizationDropdownRef.current.contains(event.target as Node)) {
        setOpenPersonalizationDropdown(null);
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpenPersonalizationDropdown(null);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleEscape);
    };
  }, []);

  useEffect(() => {
    if (!visibleTabs.some((tab) => tab.id === activeTab)) {
      setActiveTab("general");
    }
  }, [activeTab, visibleTabs]);

  const renderPersonalizationSelectRow = (
    dropdownId: string,
    label: string,
    value: string,
    onChange: (nextValue: string) => void,
    options: Array<{ value: string; label: string; description?: string }>,
    description?: string,
  ) => (
    <div className="personalization-setting-row">
      <div className="personalization-setting-copy">
        <strong className="personalization-setting-label">{label}</strong>
        {description ? <span className="personalization-setting-description">{description}</span> : null}
      </div>
      <div
        className={`personalization-dropdown header-mode-picker${openPersonalizationDropdown === dropdownId ? " open" : ""}`}
        ref={openPersonalizationDropdown === dropdownId ? personalizationDropdownRef : null}
      >
        <button
          type="button"
          className="personalization-dropdown-trigger"
          aria-expanded={openPersonalizationDropdown === dropdownId}
          disabled={personalizationLoading || personalizationSaving}
          onClick={() => setOpenPersonalizationDropdown((current) => (current === dropdownId ? null : dropdownId))}
        >
          <span className="personalization-dropdown-label">{value}</span>
          <Icon name="chevron-down" className="header-mode-chevron" />
        </button>
        {openPersonalizationDropdown === dropdownId ? (
          <div className="personalization-dropdown-menu header-mode-menu" role="menu">
            {options.map((option) => (
              <button
                key={option.value}
                type="button"
                className={`personalization-dropdown-option header-mode-option${option.value === value ? " active" : ""}`}
                onClick={() => {
                  onChange(option.value);
                  setOpenPersonalizationDropdown(null);
                }}
              >
                <span className="header-mode-option-copy">
                  <strong>{option.label.toLowerCase()}</strong>
                  {option.description ? <small>{option.description}</small> : null}
                </span>
                {option.value === value ? <Icon name="check" className="header-mode-option-check" /> : null}
              </button>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );

  return (
    <Dialog
      title="Preferences"
      onClose={onClose}
      actions={null}
      hideHeader
      className="dialog-wide panel-modal-with-tabs"
      contentClassName="preferences-dialog-content"
      bodyClassName="preferences-dialog panel-modal-tab-layout"
    >
      <div className="preferences-tabs panel-tab-nav" role="tablist" aria-label="Preferences tabs">
          <div className="panel-tab-nav-top">
            <button className="ghost-button panel-close panel-close-sidebar" type="button" onClick={onClose} aria-label="Close preferences dialog">
              x
            </button>
          </div>
          {visibleTabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              className={`preferences-tab panel-tab-button${tab.id === activeTab ? " active" : ""}`}
              aria-selected={tab.id === activeTab}
              onClick={() => {
                setActiveTab(tab.id);
                if (tab.id === "filter") {
                  onOpenFilterTab();
                }
              }}
            >
              <span className="panel-tab-button-icon" aria-hidden="true">
                <Icon name={tab.icon} />
              </span>
              <span>{tab.label}</span>
            </button>
          ))}
      </div>

      <div className="preferences-panel">
          {activeTab === "general" ? (
            <div className="preferences-section info-groups">
              <section className="info-group-card">
                <h4>{isStudent ? "Learning Mode" : "Assistant Modes"}</h4>
                <p className="preferences-copy">
                  {isStudent ? "Your account uses Learning mode." : "Available assistant modes for this system."}
                </p>
              </section>
              <div className="preferences-mode-list assistant-mode-grid">
                {isStudent ? (
                  <div className="preferences-mode-card assistant-mode-card">
                    <strong>Learning</strong>
                    <span>Adaptive learning guidance based on your profile and diagnostic context.</span>
                  </div>
                ) : (
                  availableModes.map((mode) => (
                    <div key={mode} className="preferences-mode-card assistant-mode-card">
                      <strong>{mode}</strong>
                      <span>{describeAssistantMode(mode)}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          ) : null}

          {activeTab === "personalization" ? (
            <div className="preferences-section config-sections">
              <section className="info-group-card personalization-section-card personalization-settings-shell">
                <h4 className="personalization-title">Personalization</h4>
                <div className="personalization-section-divider" aria-hidden="true" />

                {renderPersonalizationSelectRow(
                  "base-style",
                  "Base style and tone",
                  personalizationDraft?.base_style ?? "default",
                  (nextValue) => onPersonalizationFieldChange({ base_style: nextValue as PersonalizationBaseStyle }),
                  BASE_STYLE_OPTIONS.map((option) => ({
                    ...option,
                    description:
                      option.value === "default"
                        ? "default response style."
                        : option.value === "professional"
                          ? "polished and precise."
                          : option.value === "friendly"
                            ? "warm and chatty."
                            : option.value === "direct"
                              ? "direct and encouraging."
                              : option.value === "quirky"
                                ? "playful and imaginative."
                                : option.value === "efficient"
                                  ? "concise and plain."
                                  : "sceptical and critical.",
                  })),
                  "Set the style and tone of how the assistant responds to you.",
                )}

                <div className="personalization-subheadline-block">
                  <h5 className="personalization-subheadline">Characteristics</h5>
                  <p className="personalization-subheadline-description">
                    Choose additional customizations on top of your base style and tone.
                  </p>
                </div>

                {renderPersonalizationSelectRow(
                  "warm",
                  "Warm",
                  personalizationDraft?.warm ?? "default",
                  (nextValue) => onPersonalizationFieldChange({ warm: nextValue as PersonalizationLevel }),
                  LEVEL_OPTIONS.map((option) => ({ ...option })),
                )}
                {renderPersonalizationSelectRow(
                  "enthusiastic",
                  "Enthusiastic",
                  personalizationDraft?.enthusiastic ?? "default",
                  (nextValue) => onPersonalizationFieldChange({ enthusiastic: nextValue as PersonalizationLevel }),
                  LEVEL_OPTIONS.map((option) => ({ ...option })),
                )}
                {renderPersonalizationSelectRow(
                  "headers-and-lists",
                  "Headers and Lists",
                  personalizationDraft?.headers_and_lists ?? "default",
                  (nextValue) => onPersonalizationFieldChange({ headers_and_lists: nextValue as PersonalizationLevel }),
                  LEVEL_OPTIONS.map((option) => ({ ...option })),
                )}

                {isStudent ? (
                  <section className="personalization-about-you-block">
                    <h5 className="personalization-about-title">Learning Profile</h5>
                    <div className="personalization-section-divider" aria-hidden="true" />
                    <p className="preferences-copy">Manage profile details in the Learning page.</p>
                    <div className="library-table-footer">
                      <button
                        className="primary-button"
                        type="button"
                        onClick={() => {
                          onOpenLearningProfile?.();
                          onClose();
                        }}
                      >
                        Open Learning Profile
                      </button>
                    </div>
                  </section>
                ) : (
                  <>
                    <div className="personalization-custom-instructions-row">
                      <label className="personalization-field-label" htmlFor="personalization-custom-instructions">
                        Custom Instructions
                      </label>
                      <div className="personalization-custom-instructions-input-shell">
                        <textarea
                          id="personalization-custom-instructions"
                          className="dialog-input personalization-custom-instructions-input preferences-textarea is-single-line"
                          rows={1}
                          placeholder="Additional behavior, style, and tone preferences"
                          value={personalizationDraft?.custom_instructions ?? ""}
                          onChange={(event) => onPersonalizationFieldChange({ custom_instructions: event.target.value })}
                          disabled={personalizationLoading || personalizationSaving}
                        />
                        <button
                          className={`personalization-custom-save-button${personalizationSaveDisabled ? "" : " active"}`}
                          type="button"
                          onClick={onSavePersonalization}
                          disabled={personalizationSaveDisabled}
                          aria-label="Save personalization"
                        >
                          <Icon name="check" />
                        </button>
                      </div>
                    </div>

                    <section className="personalization-about-you-block">
                      <h5 className="personalization-about-title">About You</h5>
                      <div className="personalization-section-divider" aria-hidden="true" />

                      <div className="personalization-custom-instructions-row personalization-about-you-row">
                        <label className="personalization-field-label" htmlFor="personalization-nickname">
                          Nickname
                        </label>
                        <div className="personalization-custom-instructions-input-shell">
                          <input
                            id="personalization-nickname"
                            className="dialog-input personalization-custom-instructions-input"
                            type="text"
                            placeholder="What should the assistant call you?"
                            value={personalizationDraft?.nickname ?? ""}
                            onChange={(event) => onPersonalizationFieldChange({ nickname: event.target.value })}
                            disabled={personalizationLoading || personalizationSaving}
                          />
                          <button
                            className={`personalization-custom-save-button${personalizationSaveDisabled ? "" : " active"}`}
                            type="button"
                            onClick={onSavePersonalization}
                            disabled={personalizationSaveDisabled}
                            aria-label="Save personalization"
                          >
                            <Icon name="check" />
                          </button>
                        </div>
                      </div>

                      <div className="personalization-custom-instructions-row personalization-about-you-row">
                        <label className="personalization-field-label" htmlFor="personalization-occupation">
                          Occupation
                        </label>
                        <div className="personalization-custom-instructions-input-shell">
                          <input
                            id="personalization-occupation"
                            className="dialog-input personalization-custom-instructions-input"
                            type="text"
                            placeholder="What do you do?"
                            value={personalizationDraft?.occupation ?? ""}
                            onChange={(event) => onPersonalizationFieldChange({ occupation: event.target.value })}
                            disabled={personalizationLoading || personalizationSaving}
                          />
                          <button
                            className={`personalization-custom-save-button${personalizationSaveDisabled ? "" : " active"}`}
                            type="button"
                            onClick={onSavePersonalization}
                            disabled={personalizationSaveDisabled}
                            aria-label="Save personalization"
                          >
                            <Icon name="check" />
                          </button>
                        </div>
                      </div>

                      <div className="personalization-custom-instructions-row personalization-about-you-row">
                        <label className="personalization-field-label" htmlFor="personalization-more-about-you">
                          More about you
                        </label>
                        <div className="personalization-custom-instructions-input-shell">
                          <textarea
                            id="personalization-more-about-you"
                            className="dialog-input personalization-custom-instructions-input preferences-textarea is-single-line"
                            rows={1}
                            placeholder="Anything else that helps personalize responses"
                            value={personalizationDraft?.more_about_user ?? ""}
                            onChange={(event) => onPersonalizationFieldChange({ more_about_user: event.target.value })}
                            disabled={personalizationLoading || personalizationSaving}
                          />
                          <button
                            className={`personalization-custom-save-button${personalizationSaveDisabled ? "" : " active"}`}
                            type="button"
                            onClick={onSavePersonalization}
                            disabled={personalizationSaveDisabled}
                            aria-label="Save personalization"
                          >
                            <Icon name="check" />
                          </button>
                        </div>
                      </div>
                    </section>
                  </>
                )}
              </section>

              {personalizationError ? <p className="inline-error config-settings-error">{personalizationError}</p> : null}
              {personalizationSuccess ? <p className="inline-success preferences-inline-success">{personalizationSuccess}</p> : null}
              {personalizationLoading && !personalizationDraft ? (
                <section className="info-group-card">
                  <div className="preferences-placeholder">Loading personalization...</div>
                </section>
              ) : null}
            </div>
          ) : null}

          {activeTab === "settings" ? (
            <div className="preferences-section config-sections">
              <section className="settings-grid info-group-card general-settings-card config-live-table-card">
                <div className="settings-grid-head config-live-table-head" role="row">
                  <span>Setting</span>
                  <span>Value</span>
                </div>
                <div className="settings-grid-row config-live-table-row" role="row">
                  <div className="config-setting-cell">
                    <strong>History Messages</strong>
                    <small>Retrieval</small>
                  </div>
                  <div className="config-edit-form">
                    <input
                      id="history-limit"
                      className="dialog-input config-input"
                      type="number"
                      min={1}
                      max={50}
                      value={settingsDraft?.chat_history_messages_count ?? ""}
                      onChange={(event) => onFieldChange({ chat_history_messages_count: Number(event.target.value) })}
                      disabled={loading || saving}
                    />
                    <button
                      className="primary-button config-apply-save-button"
                      type="button"
                      onClick={onSaveSettings}
                      disabled={saving || loading || !!settingsValidation || !settingsDraft}
                      aria-label="Save History Messages"
                      title="Save History Messages"
                    >
                      {saving ? "..." : "Save"}
                    </button>
                  </div>
                </div>
                <div className="settings-grid-row config-live-table-row" role="row">
                  <div className="config-setting-cell">
                    <strong>Max Similarities</strong>
                    <small>Retrieval</small>
                  </div>
                  <div className="config-edit-form">
                    <input
                      id="max-similarities"
                      className="dialog-input config-input"
                      type="number"
                      min={1}
                      max={50}
                      value={settingsDraft?.max_similarities ?? ""}
                      onChange={(event) => onFieldChange({ max_similarities: Number(event.target.value) })}
                      disabled={loading || saving}
                    />
                    <button
                      className="primary-button config-apply-save-button"
                      type="button"
                      onClick={onSaveSettings}
                      disabled={saving || loading || !!settingsValidation || !settingsDraft}
                      aria-label="Save Max Similarities"
                      title="Save Max Similarities"
                    >
                      {saving ? "..." : "Save"}
                    </button>
                  </div>
                </div>
                <div className="settings-grid-row config-live-table-row" role="row">
                  <div className="config-setting-cell">
                    <strong>Min Similarities</strong>
                    <small>Retrieval</small>
                  </div>
                  <div className="config-edit-form">
                    <input
                      id="min-similarities"
                      className="dialog-input config-input"
                      type="number"
                      min={1}
                      max={50}
                      value={settingsDraft?.min_similarities ?? ""}
                      onChange={(event) => onFieldChange({ min_similarities: Number(event.target.value) })}
                      disabled={loading || saving}
                    />
                    <button
                      className="primary-button config-apply-save-button"
                      type="button"
                      onClick={onSaveSettings}
                      disabled={saving || loading || !!settingsValidation || !settingsDraft}
                      aria-label="Save Min Similarities"
                      title="Save Min Similarities"
                    >
                      {saving ? "..." : "Save"}
                    </button>
                  </div>
                </div>
                <div className="settings-grid-row config-live-table-row" role="row">
                  <div className="config-setting-cell">
                    <strong>Cosine Limit</strong>
                    <small>Retrieval</small>
                  </div>
                  <div className="config-edit-form">
                    <input
                      id="score-threshold"
                      className="dialog-input config-input"
                      type="number"
                      min={0}
                      max={1}
                      step={0.01}
                      value={settingsDraft?.similarity_score_threshold ?? ""}
                      onChange={(event) => onFieldChange({ similarity_score_threshold: Number(event.target.value) })}
                      disabled={loading || saving}
                    />
                    <button
                      className="primary-button config-apply-save-button"
                      type="button"
                      onClick={onSaveSettings}
                      disabled={saving || loading || !!settingsValidation || !settingsDraft}
                      aria-label="Save Cosine Limit"
                      title="Save Cosine Limit"
                    >
                      {saving ? "..." : "Save"}
                    </button>
                  </div>
                </div>
              </section>

              {settingsValidation ? <p className="inline-error config-settings-error">{settingsValidation}</p> : null}
              {error ? <p className="inline-error config-settings-error">{error}</p> : null}
              {success ? <p className="inline-success preferences-inline-success">{success}</p> : null}
            </div>
          ) : null}

          {activeTab === "filter" ? (
            <div className="preferences-section info-groups">
              {filterError ? <p className="inline-error">{filterError}</p> : null}
              {filterLoading ? (
                <section className="info-group-card">
                  <div className="preferences-placeholder">Loading global filters...</div>
                </section>
              ) : (
                <FilterTables
                  mode="global"
                  tags={globalFilterTags}
                  files={[]}
                  busyKeys={filterBusyKeys}
                  showFiles={false}
                  onToggleTag={onToggleGlobalTag}
                  onToggleFile={() => undefined}
                />
              )}
            </div>
          ) : null}

          {activeTab === "archive" ? (
            <div className="preferences-section">
              {archivedChats.length === 0 ? (
                <div className="preferences-placeholder">No archived chats yet.</div>
              ) : (
                <div className="archive-list archive-table-wrapper">
                  {archivedChats.map((chat) => (
                    <div key={chat.id} className="archive-row archive-table-row">
                      <div className="archive-meta">
                        <strong className="archive-chat-name">{chat.chat_name}</strong>
                        <span className="archive-chat-date">Updated {new Date(chat.updated_at).toLocaleString()}</span>
                      </div>
                      <div className="archive-actions archive-row-actions">
                        <button className="secondary-button" type="button" onClick={() => onDownloadChat(chat.id)}>
                          Download
                        </button>
                        <button className="secondary-button" type="button" onClick={() => onUnarchiveChat(chat.id)}>
                          Unarchive
                        </button>
                        <button className="danger-button" type="button" onClick={() => onDeleteChat(chat.id)}>
                          Delete
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : null}
      </div>
    </Dialog>
  );
}
