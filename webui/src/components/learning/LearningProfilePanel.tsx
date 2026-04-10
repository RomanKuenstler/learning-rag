import { useEffect, useRef, useState } from "react";
import type { LearningGoal, LearningProfileBundle, LearningProfileContext, LearningPreferences } from "../../types/chat";
import { Icon } from "../common/Icons";
import { Dialog } from "../common/Dialog";

type LearningProfilePanelProps = {
  profile: LearningProfileBundle | null;
  currentUserDisplayName: string;
  loading: boolean;
  saving: boolean;
  error: string | null;
  success: string | null;
  onLoad: () => void;
  onSavePreferences: (payload: Partial<Omit<LearningPreferences, "updated_at">>) => Promise<unknown>;
  onSaveContext: (payload: Partial<Omit<LearningProfileContext, "updated_at">>) => Promise<unknown>;
  onCreateGoal: (payload: {
    target_topic: string;
    reason_for_learning: string;
    target_level: string;
    deadline: string | null;
    priority: "low" | "medium" | "high" | null;
    notes: string;
    is_active: boolean;
  }) => Promise<unknown>;
  onUpdateGoal: (goalId: string, payload: Partial<Omit<LearningGoal, "id" | "created_at" | "updated_at">>) => Promise<unknown>;
  onDeleteGoal: (goalId: string) => Promise<unknown>;
  showPreferences?: boolean;
  showContext?: boolean;
  showGoals?: boolean;
};

const DEFAULT_PREFERENCES: Omit<LearningPreferences, "updated_at"> = {
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
};

const DEFAULT_CONTEXT: Omit<LearningProfileContext, "updated_at"> = {
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
};

const DEFAULT_GOAL_DRAFT = {
  target_topic: "",
  reason_for_learning: "",
  target_level: "",
  deadline: "",
  priority: "medium" as "low" | "medium" | "high",
  notes: "",
  is_active: true,
};

type PairedEntry = {
  primary: string;
  secondary: string;
};

function parsePairedEntry(raw: string): PairedEntry {
  const value = String(raw ?? "").trim();
  if (!value) {
    return { primary: "", secondary: "" };
  }
  for (const separator of ["||", "::", " — ", " - "]) {
    if (value.includes(separator)) {
      const [left, ...rightParts] = value.split(separator);
      return { primary: left.trim(), secondary: rightParts.join(separator).trim() };
    }
  }
  return { primary: value, secondary: "" };
}

function parsePairedEntries(values: string[]): PairedEntry[] {
  const parsed = values.map((entry) => parsePairedEntry(entry));
  return parsed.length > 0 ? parsed : [{ primary: "", secondary: "" }];
}

function serializePairedEntries(entries: PairedEntry[]): string[] {
  return entries
    .map((entry) => {
      const primary = entry.primary.trim();
      const secondary = entry.secondary.trim();
      if (!primary && !secondary) {
        return "";
      }
      return secondary ? `${primary} || ${secondary}` : primary;
    })
    .filter(Boolean);
}

function formatDeadlineInput(raw: string): string {
  const digits = raw.replace(/\D/g, "").slice(0, 8);
  if (digits.length <= 2) return digits;
  if (digits.length <= 4) return `${digits.slice(0, 2)}.${digits.slice(2)}`;
  return `${digits.slice(0, 2)}.${digits.slice(2, 4)}.${digits.slice(4)}`;
}

function parseDeadlineInput(value: string): string | null {
  if (!value.trim()) {
    return null;
  }
  const match = value.match(/^(\d{2})\.(\d{2})\.(\d{4})$/);
  if (!match) {
    return "__invalid__";
  }
  const [, dd, mm, yyyy] = match;
  const date = new Date(Number(yyyy), Number(mm) - 1, Number(dd));
  if (
    Number.isNaN(date.getTime()) ||
    date.getFullYear() !== Number(yyyy) ||
    date.getMonth() !== Number(mm) - 1 ||
    date.getDate() !== Number(dd)
  ) {
    return "__invalid__";
  }
  return `${yyyy}-${mm}-${dd}`;
}

export function LearningProfilePanel({
  profile,
  currentUserDisplayName,
  loading,
  saving,
  error,
  success,
  onLoad,
  onSavePreferences,
  onSaveContext,
  onCreateGoal,
  onUpdateGoal,
  onDeleteGoal,
  showPreferences = true,
  showContext = true,
  showGoals = true,
}: LearningProfilePanelProps) {
  const [preferencesDraft, setPreferencesDraft] = useState<Omit<LearningPreferences, "updated_at">>(DEFAULT_PREFERENCES);
  const [contextDraft, setContextDraft] = useState<Omit<LearningProfileContext, "updated_at">>(DEFAULT_CONTEXT);
  const [skillsInput, setSkillsInput] = useState("");
  const [interestInput, setInterestInput] = useState("");
  const [workExperienceInput, setWorkExperienceInput] = useState("");
  const [educationHistoryInput, setEducationHistoryInput] = useState("");
  const [goalDraft, setGoalDraft] = useState(DEFAULT_GOAL_DRAFT);
  const [isAddGoalDialogOpen, setIsAddGoalDialogOpen] = useState(false);
  const [isLeftProfileDialogOpen, setIsLeftProfileDialogOpen] = useState(false);
  const [isRightProfileDialogOpen, setIsRightProfileDialogOpen] = useState(false);
  const [leftProfileDraft, setLeftProfileDraft] = useState({
    profile_display_name: "",
    preferred_form_of_address: "",
    about_me: "",
    contact_location: "",
    general_title: "",
    date_of_birth: "",
  });
  const [rightProfileDraft, setRightProfileDraft] = useState({
    work_experience: [] as PairedEntry[],
    education_history: [] as PairedEntry[],
    skills: "",
    interests: "",
  });
  const [openDropdownId, setOpenDropdownId] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    void onLoad();
    // This load is mount-scoped; the parent currently passes a new callback each render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    setPreferencesDraft(profile?.preferences ? {
      preferred_pace: profile.preferences.preferred_pace,
      explanation_depth: profile.preferences.explanation_depth,
      examples_vs_theory: profile.preferences.examples_vs_theory,
      structure_preference: profile.preferences.structure_preference,
      checkpoint_frequency: profile.preferences.checkpoint_frequency,
      encouragement_level: profile.preferences.encouragement_level,
      guidance_level: profile.preferences.guidance_level,
      recap_frequency: profile.preferences.recap_frequency,
      preferred_learning_format: profile.preferences.preferred_learning_format,
      custom_preference_note: profile.preferences.custom_preference_note,
    } : DEFAULT_PREFERENCES);

    const nextContext = profile?.context
      ? {
          profile_display_name: profile.context.profile_display_name,
          about_me: profile.context.about_me,
          contact_location: profile.context.contact_location,
          general_title: profile.context.general_title,
          date_of_birth: profile.context.date_of_birth,
          current_skill_areas: profile.context.current_skill_areas,
          skills: profile.context.skills,
          interests: profile.context.interests,
          work_experience: profile.context.work_experience,
          education_history: profile.context.education_history,
          current_reason_for_learning: profile.context.current_reason_for_learning,
          preferred_form_of_address: profile.context.preferred_form_of_address,
          learning_context_notes: profile.context.learning_context_notes,
        }
      : DEFAULT_CONTEXT;
    const resolvedDisplayName = currentUserDisplayName;
    setContextDraft({ ...nextContext, profile_display_name: resolvedDisplayName });
    setSkillsInput((nextContext.skills.length > 0 ? nextContext.skills : nextContext.current_skill_areas).join(", "));
    setInterestInput(nextContext.interests.join(", "));
    setWorkExperienceInput(nextContext.work_experience.join("\n"));
    setEducationHistoryInput(nextContext.education_history.join("\n"));
    setLeftProfileDraft({
      profile_display_name: resolvedDisplayName,
      preferred_form_of_address: nextContext.preferred_form_of_address,
      about_me: nextContext.about_me,
      contact_location: nextContext.contact_location,
      general_title: nextContext.general_title,
      date_of_birth: nextContext.date_of_birth,
    });
    setRightProfileDraft({
      work_experience: parsePairedEntries(nextContext.work_experience),
      education_history: parsePairedEntries(nextContext.education_history),
      skills: (nextContext.skills.length > 0 ? nextContext.skills : nextContext.current_skill_areas).join(", "),
      interests: nextContext.interests.join(", "),
    });
  }, [profile, currentUserDisplayName]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setOpenDropdownId(null);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function renderDropdown<T extends string>(
    dropdownId: string,
    value: T,
    options: Array<{ value: T; label: string }>,
    onChange: (next: T) => void,
  ) {
    return (
      <div className={`personalization-dropdown header-mode-picker learning-pref-dropdown${openDropdownId === dropdownId ? " open" : ""}`} ref={openDropdownId === dropdownId ? dropdownRef : null}>
        <button
          className="personalization-dropdown-trigger learning-pref-trigger"
          type="button"
          aria-haspopup="menu"
          aria-expanded={openDropdownId === dropdownId}
          onClick={() => setOpenDropdownId((current) => (current === dropdownId ? null : dropdownId))}
          disabled={loading || saving}
        >
          <span className="personalization-dropdown-label">{options.find((option) => option.value === value)?.label ?? value}</span>
          <Icon name="chevron-down" className="header-mode-chevron" />
        </button>
        {openDropdownId === dropdownId ? (
          <div className="personalization-dropdown-menu header-mode-menu" role="menu">
            {options.map((option) => (
              <button
                key={option.value}
                className={`personalization-dropdown-option header-mode-option${option.value === value ? " active" : ""}`}
                type="button"
                role="menuitemradio"
                aria-checked={option.value === value}
                onClick={() => {
                  onChange(option.value);
                  setOpenDropdownId(null);
                }}
              >
                {option.label}
              </button>
            ))}
          </div>
        ) : null}
      </div>
    );
  }

  const goals = profile?.goals ?? [];
  const parsedAddGoalDeadline = parseDeadlineInput(goalDraft.deadline);
  const addGoalDeadlineInvalid = goalDraft.deadline.trim().length > 0 && parsedAddGoalDeadline === "__invalid__";

  return (
    <>
      {showPreferences ? (
      <section className="info-group-card library-table-card">
        <div className="library-table-header">
          <h4>Learning Preferences</h4>
        </div>
        <div className="learning-preferences-list">
          <div className="learning-preferences-columns">
          <div className="learning-pref-row">
            <span className="learning-pref-label">Preferred pace</span>
            {renderDropdown(
              "preferred_pace",
              preferencesDraft.preferred_pace,
              [{ value: "slow", label: "Slow" }, { value: "balanced", label: "Balanced" }, { value: "fast", label: "Fast" }],
              (next) => setPreferencesDraft((current) => ({ ...current, preferred_pace: next })),
            )}
          </div>
          <div className="learning-pref-row">
            <span className="learning-pref-label">Explanation depth</span>
            {renderDropdown(
              "explanation_depth",
              preferencesDraft.explanation_depth,
              [{ value: "concise", label: "Concise" }, { value: "balanced", label: "Balanced" }, { value: "detailed", label: "Detailed" }],
              (next) => setPreferencesDraft((current) => ({ ...current, explanation_depth: next })),
            )}
          </div>
          <div className="learning-pref-row">
            <span className="learning-pref-label">Examples vs theory</span>
            {renderDropdown(
              "examples_vs_theory",
              preferencesDraft.examples_vs_theory,
              [{ value: "more_examples", label: "More examples" }, { value: "balanced", label: "Balanced" }, { value: "more_theory", label: "More theory" }],
              (next) => setPreferencesDraft((current) => ({ ...current, examples_vs_theory: next })),
            )}
          </div>
          <div className="learning-pref-row">
            <span className="learning-pref-label">Structure preference</span>
            {renderDropdown(
              "structure_preference",
              preferencesDraft.structure_preference,
              [{ value: "more_structured", label: "More structured" }, { value: "balanced", label: "Balanced" }, { value: "more_conversational", label: "More conversational" }],
              (next) => setPreferencesDraft((current) => ({ ...current, structure_preference: next })),
            )}
          </div>
          <div className="learning-pref-row">
            <span className="learning-pref-label">Quiz/checkpoint frequency</span>
            {renderDropdown(
              "checkpoint_frequency",
              preferencesDraft.checkpoint_frequency,
              [{ value: "low", label: "Low" }, { value: "medium", label: "Medium" }, { value: "high", label: "High" }],
              (next) => setPreferencesDraft((current) => ({ ...current, checkpoint_frequency: next })),
            )}
          </div>
          <div className="learning-pref-row">
            <span className="learning-pref-label">Encouragement level</span>
            {renderDropdown(
              "encouragement_level",
              preferencesDraft.encouragement_level,
              [{ value: "low", label: "Low" }, { value: "balanced", label: "Balanced" }, { value: "high", label: "High" }],
              (next) => setPreferencesDraft((current) => ({ ...current, encouragement_level: next })),
            )}
          </div>
          <div className="learning-pref-row">
            <span className="learning-pref-label">Guidance level</span>
            {renderDropdown(
              "guidance_level",
              preferencesDraft.guidance_level,
              [{ value: "step_by_step", label: "Step by step" }, { value: "balanced", label: "Balanced" }, { value: "more_independent", label: "More independent" }],
              (next) => setPreferencesDraft((current) => ({ ...current, guidance_level: next })),
            )}
          </div>
          <div className="learning-pref-row">
            <span className="learning-pref-label">Recap frequency</span>
            {renderDropdown(
              "recap_frequency",
              preferencesDraft.recap_frequency,
              [{ value: "low", label: "Low" }, { value: "medium", label: "Medium" }, { value: "high", label: "High" }],
              (next) => setPreferencesDraft((current) => ({ ...current, recap_frequency: next })),
            )}
          </div>
          <div className="learning-pref-row">
            <span className="learning-pref-label">Preferred learning format</span>
            {renderDropdown(
              "preferred_learning_format",
              preferencesDraft.preferred_learning_format,
              [{ value: "reading", label: "Reading" }, { value: "dialogue", label: "Dialogue" }, { value: "exercises", label: "Exercises" }, { value: "mixed", label: "Mixed" }],
              (next) => setPreferencesDraft((current) => ({ ...current, preferred_learning_format: next })),
            )}
          </div>
          </div>
          <label className="learning-pref-note-row">
            <span>Custom note</span>
            <textarea className="dialog-input preferences-textarea" value={preferencesDraft.custom_preference_note} onChange={(event) => setPreferencesDraft((current) => ({ ...current, custom_preference_note: event.target.value }))} />
          </label>
        </div>
        <div className="library-table-footer">
          <button className="primary-button" disabled={loading || saving} onClick={() => void onSavePreferences(preferencesDraft)}>Save preferences</button>
        </div>
      </section>
      ) : null}

      {showContext ? (
      <section className="info-group-card library-table-card">
        <div className="profile-context-layout">
          <section className="profile-context-left">
            <div className="profile-left-name-row">
              <strong className="profile-left-name">{contextDraft.profile_display_name || "Your Profile"}</strong>
              <button className="profile-left-edit-button" type="button" disabled={loading || saving} onClick={() => setIsLeftProfileDialogOpen(true)} aria-label="Edit left profile section">
                <Icon name="pencil" className="profile-left-edit-icon" />
              </button>
            </div>
            <div className="profile-context-details">
              <p><strong>How to address</strong><span>{contextDraft.preferred_form_of_address || "-"}</span></p>
              <p><strong>Location</strong><span>{contextDraft.contact_location || "-"}</span></p>
              <p><strong>Title</strong><span>{contextDraft.general_title || "-"}</span></p>
              <p><strong>Date of birth</strong><span>{contextDraft.date_of_birth || "-"}</span></p>
            </div>
            <p className="profile-context-text"><strong>About</strong></p>
            <p className="profile-context-copy">{contextDraft.about_me || "-"}</p>
          </section>

          <section className="profile-context-right">
            <div className="profile-context-display">
              <div>
                <strong>Work Experience</strong>
                {contextDraft.work_experience.length === 0 ? <p>-</p> : (
                  <div className="profile-line-list">
                    {contextDraft.work_experience.map((item) => {
                      const parsed = parsePairedEntry(item);
                      return (
                        <article key={item} className="profile-line-item">
                          <strong>{parsed.primary || "-"}</strong>
                          {parsed.secondary ? <span>{parsed.secondary}</span> : null}
                        </article>
                      );
                    })}
                  </div>
                )}
              </div>
              <div>
                <strong>Education</strong>
                {contextDraft.education_history.length === 0 ? <p>-</p> : (
                  <div className="profile-line-list">
                    {contextDraft.education_history.map((item) => {
                      const parsed = parsePairedEntry(item);
                      return (
                        <article key={item} className="profile-line-item">
                          <strong>{parsed.primary || "-"}</strong>
                          {parsed.secondary ? <span>{parsed.secondary}</span> : null}
                        </article>
                      );
                    })}
                  </div>
                )}
              </div>
              <div>
                <strong>Skills</strong>
                {contextDraft.skills.length === 0 && contextDraft.current_skill_areas.length === 0 ? <p>-</p> : (
                  <div className="profile-chip-row">{(contextDraft.skills.length > 0 ? contextDraft.skills : contextDraft.current_skill_areas).map((item) => <span key={item} className="profile-chip">{item}</span>)}</div>
                )}
              </div>
              <div>
                <strong>Interests</strong>
                {contextDraft.interests.length === 0 ? <p>-</p> : <div className="profile-chip-row">{contextDraft.interests.map((item) => <span key={item} className="profile-chip">{item}</span>)}</div>}
              </div>
            </div>
            <div className="library-table-footer">
              <button className="primary-button" type="button" disabled={loading || saving} onClick={() => setIsRightProfileDialogOpen(true)}>
                Edit
              </button>
            </div>
          </section>
        </div>

        <div className="library-table-header profile-context-bottom-head">
          <h4>Learning Context</h4>
        </div>
        <div className="settings-grid profile-context-bottom-fields">
          <label>
            <span>Current reason for learning</span>
            <textarea className="dialog-input preferences-textarea" value={contextDraft.current_reason_for_learning} onChange={(event) => setContextDraft((current) => ({ ...current, current_reason_for_learning: event.target.value }))} />
          </label>
          <label>
            <span>Additional learning context notes</span>
            <textarea className="dialog-input preferences-textarea" value={contextDraft.learning_context_notes} onChange={(event) => setContextDraft((current) => ({ ...current, learning_context_notes: event.target.value }))} />
          </label>
        </div>
        <div className="library-table-footer">
          <button
            className="primary-button"
            disabled={loading || saving}
            onClick={() => void onSaveContext({
              ...contextDraft,
              profile_display_name: currentUserDisplayName,
              current_skill_areas: skillsInput.split(",").map((item) => item.trim()).filter(Boolean),
              skills: skillsInput.split(",").map((item) => item.trim()).filter(Boolean),
              interests: interestInput.split(",").map((item) => item.trim()).filter(Boolean),
              work_experience: workExperienceInput.split("\n").map((item) => item.trim()).filter(Boolean),
              education_history: educationHistoryInput.split("\n").map((item) => item.trim()).filter(Boolean),
            })}
          >
            Save context
          </button>
        </div>
      </section>
      ) : null}

      {isLeftProfileDialogOpen ? (
        <Dialog
          title="Edit Profile"
          onClose={() => setIsLeftProfileDialogOpen(false)}
          className="add-goal-dialog"
          actions={(
            <>
              <button className="secondary-button" type="button" onClick={() => setIsLeftProfileDialogOpen(false)}>Cancel</button>
              <button
                className="primary-button"
                type="button"
                disabled={loading || saving}
                onClick={async () => {
                  await onSaveContext({ ...leftProfileDraft, profile_display_name: currentUserDisplayName });
                  setContextDraft((current) => ({ ...current, ...leftProfileDraft, profile_display_name: currentUserDisplayName }));
                  setIsLeftProfileDialogOpen(false);
                }}
              >
                Save
              </button>
            </>
          )}
        >
          <div className="settings-grid">
            <label><span>Username</span><input className="dialog-input" value={currentUserDisplayName} disabled /></label>
            <label><span>How to address</span><input className="dialog-input" value={leftProfileDraft.preferred_form_of_address} onChange={(event) => setLeftProfileDraft((current) => ({ ...current, preferred_form_of_address: event.target.value }))} /></label>
            <label><span>Location</span><input className="dialog-input" value={leftProfileDraft.contact_location} onChange={(event) => setLeftProfileDraft((current) => ({ ...current, contact_location: event.target.value }))} /></label>
            <label><span>Title</span><input className="dialog-input" value={leftProfileDraft.general_title} onChange={(event) => setLeftProfileDraft((current) => ({ ...current, general_title: event.target.value }))} /></label>
            <label><span>Date of birth</span><input className="dialog-input" value={leftProfileDraft.date_of_birth} onChange={(event) => setLeftProfileDraft((current) => ({ ...current, date_of_birth: event.target.value }))} /></label>
            <label><span>About</span><textarea className="dialog-input preferences-textarea" value={leftProfileDraft.about_me} onChange={(event) => setLeftProfileDraft((current) => ({ ...current, about_me: event.target.value }))} /></label>
          </div>
        </Dialog>
      ) : null}

      {isRightProfileDialogOpen ? (
        <Dialog
          title="Edit Profile"
          onClose={() => setIsRightProfileDialogOpen(false)}
          className="add-goal-dialog"
          actions={(
            <>
              <button className="secondary-button" type="button" onClick={() => setIsRightProfileDialogOpen(false)}>Cancel</button>
              <button
                className="primary-button"
                type="button"
                disabled={loading || saving}
                onClick={async () => {
                  const workSerialized = serializePairedEntries(rightProfileDraft.work_experience);
                  const educationSerialized = serializePairedEntries(rightProfileDraft.education_history);
                  const payload = {
                    current_skill_areas: rightProfileDraft.skills.split(",").map((item) => item.trim()).filter(Boolean),
                    skills: rightProfileDraft.skills.split(",").map((item) => item.trim()).filter(Boolean),
                    interests: rightProfileDraft.interests.split(",").map((item) => item.trim()).filter(Boolean),
                    work_experience: workSerialized,
                    education_history: educationSerialized,
                  };
                  await onSaveContext(payload);
                  setSkillsInput(rightProfileDraft.skills);
                  setInterestInput(rightProfileDraft.interests);
                  setWorkExperienceInput(workSerialized.join("\n"));
                  setEducationHistoryInput(educationSerialized.join("\n"));
                  setContextDraft((current) => ({
                    ...current,
                    current_skill_areas: payload.current_skill_areas,
                    skills: payload.skills,
                    interests: payload.interests,
                    work_experience: payload.work_experience,
                    education_history: payload.education_history,
                  }));
                  setIsRightProfileDialogOpen(false);
                }}
              >
                Save
              </button>
            </>
          )}
        >
          <div className="settings-grid">
            <label>
              <span>Work Experience</span>
              <div className="profile-pair-editor">
                {rightProfileDraft.work_experience.map((entry, index) => (
                  <div key={`work-${index}`} className="profile-pair-row">
                    <input className="dialog-input" placeholder="Job" value={entry.primary} onChange={(event) => setRightProfileDraft((current) => ({
                      ...current,
                      work_experience: current.work_experience.map((item, itemIndex) => itemIndex === index ? { ...item, primary: event.target.value } : item),
                    }))} />
                    <input className="dialog-input" placeholder="Company" value={entry.secondary} onChange={(event) => setRightProfileDraft((current) => ({
                      ...current,
                      work_experience: current.work_experience.map((item, itemIndex) => itemIndex === index ? { ...item, secondary: event.target.value } : item),
                    }))} />
                    {index === rightProfileDraft.work_experience.length - 1 ? (
                      <button className="profile-pair-add" type="button" onClick={() => setRightProfileDraft((current) => ({
                        ...current,
                        work_experience: [...current.work_experience, { primary: "", secondary: "" }],
                      }))}>+</button>
                    ) : (
                      <button className="profile-pair-remove" type="button" onClick={() => setRightProfileDraft((current) => ({
                        ...current,
                        work_experience: current.work_experience.filter((_, itemIndex) => itemIndex !== index),
                      }))}>-</button>
                    )}
                  </div>
                ))}
              </div>
            </label>
            <label>
              <span>Education</span>
              <div className="profile-pair-editor">
                {rightProfileDraft.education_history.map((entry, index) => (
                  <div key={`education-${index}`} className="profile-pair-row">
                    <input className="dialog-input" placeholder="Degree" value={entry.primary} onChange={(event) => setRightProfileDraft((current) => ({
                      ...current,
                      education_history: current.education_history.map((item, itemIndex) => itemIndex === index ? { ...item, primary: event.target.value } : item),
                    }))} />
                    <input className="dialog-input" placeholder="Institute" value={entry.secondary} onChange={(event) => setRightProfileDraft((current) => ({
                      ...current,
                      education_history: current.education_history.map((item, itemIndex) => itemIndex === index ? { ...item, secondary: event.target.value } : item),
                    }))} />
                    {index === rightProfileDraft.education_history.length - 1 ? (
                      <button className="profile-pair-add" type="button" onClick={() => setRightProfileDraft((current) => ({
                        ...current,
                        education_history: [...current.education_history, { primary: "", secondary: "" }],
                      }))}>+</button>
                    ) : (
                      <button className="profile-pair-remove" type="button" onClick={() => setRightProfileDraft((current) => ({
                        ...current,
                        education_history: current.education_history.filter((_, itemIndex) => itemIndex !== index),
                      }))}>-</button>
                    )}
                  </div>
                ))}
              </div>
            </label>
            <label><span>Skills</span><input className="dialog-input" placeholder="e.g. App Design, UX Writing, Data Analysis" value={rightProfileDraft.skills} onChange={(event) => setRightProfileDraft((current) => ({ ...current, skills: event.target.value }))} /></label>
            <label><span>Interests</span><input className="dialog-input" placeholder="e.g. Reading, Motion Graphics, Fitness" value={rightProfileDraft.interests} onChange={(event) => setRightProfileDraft((current) => ({ ...current, interests: event.target.value }))} /></label>
          </div>
        </Dialog>
      ) : null}

      {showGoals ? (
      <section className="info-group-card library-table-card">
        <div className="library-table-header">
          <h4>Learning Goals</h4>
        </div>
        <div className="library-table learning-goals-table">
          <div className="library-table-head learning-goals-head">
            <span>Topic</span>
            <span>Target Level</span>
            <span>Deadline</span>
            <span>Priority</span>
            <span>Active</span>
            <span>Actions</span>
          </div>
          <div className="library-table-body">
            {goals.length === 0 ? <div className="empty-state">No learning goals yet.</div> : null}
            {goals.map((goal) => (
              <GoalTableRow
                key={goal.id}
                goal={goal}
                saving={saving}
                onUpdateGoal={onUpdateGoal}
                onDeleteGoal={onDeleteGoal}
              />
            ))}
          </div>
        </div>

        <div className="library-table-footer learning-goals-actions">
          <button className="primary-button" type="button" disabled={loading || saving} onClick={() => setIsAddGoalDialogOpen(true)}>
            Add Goal
          </button>
        </div>
      </section>
      ) : null}

      {isAddGoalDialogOpen ? (
        <Dialog
          title="Add Learning Goal"
          onClose={() => setIsAddGoalDialogOpen(false)}
          className="add-goal-dialog"
          actions={(
            <>
              <button className="secondary-button" type="button" onClick={() => setIsAddGoalDialogOpen(false)}>
                Cancel
              </button>
              <button
                className="primary-button"
                type="button"
                disabled={loading || saving || !goalDraft.target_topic.trim() || addGoalDeadlineInvalid}
                onClick={async () => {
                  await onCreateGoal({
                    target_topic: goalDraft.target_topic.trim(),
                    reason_for_learning: goalDraft.reason_for_learning,
                    target_level: goalDraft.target_level,
                    deadline: parsedAddGoalDeadline && parsedAddGoalDeadline !== "__invalid__" ? parsedAddGoalDeadline : null,
                    priority: goalDraft.priority,
                    notes: goalDraft.notes,
                    is_active: goalDraft.is_active,
                  });
                  setGoalDraft(DEFAULT_GOAL_DRAFT);
                  setIsAddGoalDialogOpen(false);
                }}
              >
                Add Goal
              </button>
            </>
          )}
        >
          <div className="settings-grid">
            <label>
              <span>Target topic / subject</span>
              <input className="dialog-input" value={goalDraft.target_topic} onChange={(event) => setGoalDraft((current) => ({ ...current, target_topic: event.target.value }))} />
            </label>
            <label>
              <span>Reason for learning</span>
              <textarea className="dialog-input preferences-textarea" value={goalDraft.reason_for_learning} onChange={(event) => setGoalDraft((current) => ({ ...current, reason_for_learning: event.target.value }))} />
            </label>
            <label>
              <span>Target level</span>
              <input className="dialog-input" value={goalDraft.target_level} onChange={(event) => setGoalDraft((current) => ({ ...current, target_level: event.target.value }))} />
            </label>
            <label>
              <span>Deadline</span>
              <input
                className="dialog-input"
                type="text"
                inputMode="numeric"
                placeholder="dd.mm.yyyy"
                value={goalDraft.deadline}
                onChange={(event) => setGoalDraft((current) => ({ ...current, deadline: formatDeadlineInput(event.target.value) }))}
              />
              {addGoalDeadlineInvalid ? <small className="chat-error">Please use format dd.mm.yyyy</small> : null}
            </label>
            <label className="learning-goal-priority-row">
              <span>Priority</span>
              {renderDropdown(
                "goal_priority_add_dialog",
                goalDraft.priority,
                [{ value: "low", label: "Low" }, { value: "medium", label: "Medium" }, { value: "high", label: "High" }],
                (next) => setGoalDraft((current) => ({ ...current, priority: next })),
              )}
            </label>
            <label>
              <span>Notes</span>
              <textarea className="dialog-input preferences-textarea" value={goalDraft.notes} onChange={(event) => setGoalDraft((current) => ({ ...current, notes: event.target.value }))} />
            </label>
          </div>
        </Dialog>
      ) : null}

      {error ? <p className="chat-error chat-error-banner">{error}</p> : null}
      {success ? <p className="chat-error chat-success-banner">{success}</p> : null}
    </>
  );
}

function GoalTableRow({
  goal,
  saving,
  onUpdateGoal,
  onDeleteGoal,
}: {
  goal: LearningGoal;
  saving: boolean;
  onUpdateGoal: (goalId: string, payload: Partial<Omit<LearningGoal, "id" | "created_at" | "updated_at">>) => Promise<unknown>;
  onDeleteGoal: (goalId: string) => Promise<unknown>;
}) {
  const [draft, setDraft] = useState({
    deadline: goal.deadline ?? "",
    is_active: goal.is_active,
  });

  useEffect(() => {
    setDraft({
      deadline: goal.deadline ?? "",
      is_active: goal.is_active,
    });
  }, [goal]);

  return (
    <div className="library-table-row learning-goals-row">
      <span className="learning-goal-topic">{goal.target_topic}</span>
      <span>{goal.target_level || "-"}</span>
      <span>
        <input className="dialog-input" type="date" value={draft.deadline} onChange={(event) => setDraft((current) => ({ ...current, deadline: event.target.value }))} />
      </span>
      <span>
        <span className={`learning-goal-priority-badge learning-goal-priority-${goal.priority ?? "none"}`}>
          {goal.priority ?? "-"}
        </span>
      </span>
      <span>
        <span className="learning-goal-active-cell">
          <label className="filter-switch">
            <input type="checkbox" checked={draft.is_active} onChange={(event) => setDraft((current) => ({ ...current, is_active: event.target.checked }))} />
            <span className="filter-switch-slider" />
          </label>
          <span className="learning-goal-active-text">{draft.is_active ? "Active" : "Inactive"}</span>
        </span>
      </span>
      <span className="learning-goal-actions">
        <button
          className="secondary-button"
          disabled={saving}
          onClick={() => void onUpdateGoal(goal.id, {
            deadline: draft.deadline || null,
            is_active: draft.is_active,
          })}
        >
          Save
        </button>
        <button className="danger-button" disabled={saving} onClick={() => void onDeleteGoal(goal.id)}>Delete</button>
      </span>
    </div>
  );
}
