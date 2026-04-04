import { useEffect, useRef, useState } from "react";
import type { LearningGoal, LearningProfileBundle, LearningProfileContext, LearningPreferences } from "../../types/chat";
import { Icon } from "../common/Icons";

type LearningProfilePanelProps = {
  profile: LearningProfileBundle | null;
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
  education_background: "",
  current_skill_areas: [],
  interests: [],
  professional_context: "",
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

export function LearningProfilePanel({
  profile,
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
}: LearningProfilePanelProps) {
  const [preferencesDraft, setPreferencesDraft] = useState<Omit<LearningPreferences, "updated_at">>(DEFAULT_PREFERENCES);
  const [contextDraft, setContextDraft] = useState<Omit<LearningProfileContext, "updated_at">>(DEFAULT_CONTEXT);
  const [skillInput, setSkillInput] = useState("");
  const [interestInput, setInterestInput] = useState("");
  const [goalDraft, setGoalDraft] = useState(DEFAULT_GOAL_DRAFT);
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
          education_background: profile.context.education_background,
          current_skill_areas: profile.context.current_skill_areas,
          interests: profile.context.interests,
          professional_context: profile.context.professional_context,
          current_reason_for_learning: profile.context.current_reason_for_learning,
          preferred_form_of_address: profile.context.preferred_form_of_address,
          learning_context_notes: profile.context.learning_context_notes,
        }
      : DEFAULT_CONTEXT;
    setContextDraft(nextContext);
    setSkillInput(nextContext.current_skill_areas.join(", "));
    setInterestInput(nextContext.interests.join(", "));
  }, [profile]);

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

  return (
    <>
      <section className="info-group-card library-table-card">
        <div className="library-table-header">
          <h4>Learning Preferences</h4>
        </div>
        <div className="learning-preferences-list">
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
          <label className="learning-pref-note-row">
            <span>Custom note</span>
            <textarea className="dialog-input preferences-textarea" value={preferencesDraft.custom_preference_note} onChange={(event) => setPreferencesDraft((current) => ({ ...current, custom_preference_note: event.target.value }))} />
          </label>
        </div>
        <div className="library-table-footer">
          <button className="primary-button" disabled={loading || saving} onClick={() => void onSavePreferences(preferencesDraft)}>Save preferences</button>
        </div>
      </section>

      <section className="info-group-card library-table-card">
        <div className="library-table-header">
          <h4>Learning Context / Background</h4>
        </div>
        <div className="settings-grid">
          <label>
            <span>Education background</span>
            <textarea className="dialog-input preferences-textarea" value={contextDraft.education_background} onChange={(event) => setContextDraft((current) => ({ ...current, education_background: event.target.value }))} />
          </label>
          <label>
            <span>Current skill areas (comma-separated)</span>
            <input className="dialog-input" value={skillInput} onChange={(event) => setSkillInput(event.target.value)} />
          </label>
          <label>
            <span>Interests (comma-separated)</span>
            <input className="dialog-input" value={interestInput} onChange={(event) => setInterestInput(event.target.value)} />
          </label>
          <label>
            <span>Professional context</span>
            <textarea className="dialog-input preferences-textarea" value={contextDraft.professional_context} onChange={(event) => setContextDraft((current) => ({ ...current, professional_context: event.target.value }))} />
          </label>
          <label>
            <span>Current reason for learning</span>
            <textarea className="dialog-input preferences-textarea" value={contextDraft.current_reason_for_learning} onChange={(event) => setContextDraft((current) => ({ ...current, current_reason_for_learning: event.target.value }))} />
          </label>
          <label>
            <span>Preferred form of address</span>
            <input className="dialog-input" value={contextDraft.preferred_form_of_address} onChange={(event) => setContextDraft((current) => ({ ...current, preferred_form_of_address: event.target.value }))} />
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
              current_skill_areas: skillInput.split(",").map((item) => item.trim()).filter(Boolean),
              interests: interestInput.split(",").map((item) => item.trim()).filter(Boolean),
            })}
          >
            Save context
          </button>
        </div>
      </section>

      <section className="info-group-card library-table-card">
        <div className="library-table-header">
          <h4>Learning Goals</h4>
        </div>
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
            <input className="dialog-input" type="date" value={goalDraft.deadline} onChange={(event) => setGoalDraft((current) => ({ ...current, deadline: event.target.value }))} />
          </label>
          <label className="learning-goal-priority-row">
            <span className="learning-pref-label">Priority</span>
            {renderDropdown(
              "goal_priority",
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
        <div className="library-table-footer">
          <button
            className="primary-button"
            disabled={loading || saving || !goalDraft.target_topic.trim()}
            onClick={async () => {
              await onCreateGoal({
                target_topic: goalDraft.target_topic.trim(),
                reason_for_learning: goalDraft.reason_for_learning,
                target_level: goalDraft.target_level,
                deadline: goalDraft.deadline || null,
                priority: goalDraft.priority,
                notes: goalDraft.notes,
                is_active: goalDraft.is_active,
              });
              setGoalDraft(DEFAULT_GOAL_DRAFT);
            }}
          >
            Add goal
          </button>
        </div>

        <div className="library-table learning-goals-table">
          <div className="library-table-head learning-goals-head">
            <span>Topic</span>
            <span>Target Level</span>
            <span>Deadline</span>
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
      </section>

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
