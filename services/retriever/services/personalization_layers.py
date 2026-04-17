from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from services.retriever.services.ksa_assessment import ABILITY_TOPICS, KNOWLEDGE_TOPICS, SKILL_TOPICS

GROUP_IDENTITY_CONTEXT = "identity_context"
GROUP_GOAL_INTENT = "goal_intent"
GROUP_DECLARED_PREFERENCES = "declared_preferences"
GROUP_DIAGNOSED_LEARNING = "diagnosed_learning"
GROUP_CAPABILITY_MASTERY = "capability_mastery"
GROUP_LIVE_ADAPTATION = "live_adaptation"

GROUP_ORDER = [
    GROUP_IDENTITY_CONTEXT,
    GROUP_GOAL_INTENT,
    GROUP_DECLARED_PREFERENCES,
    GROUP_DIAGNOSED_LEARNING,
    GROUP_CAPABILITY_MASTERY,
    GROUP_LIVE_ADAPTATION,
]

GROUP_COLUMNS: dict[str, tuple[str, str, str]] = {
    GROUP_IDENTITY_CONTEXT: ("identity_context_snapshot", "resolved_identity_context_rules", "identity_context_updated_at"),
    GROUP_GOAL_INTENT: ("goal_intent_snapshot", "resolved_goal_rules", "goal_intent_updated_at"),
    GROUP_DECLARED_PREFERENCES: (
        "declared_preferences_snapshot",
        "resolved_declared_tutor_rules",
        "declared_preferences_updated_at",
    ),
    GROUP_DIAGNOSED_LEARNING: ("diagnosed_learning_snapshot", "resolved_diagnostic_rules", "diagnosed_learning_updated_at"),
    GROUP_CAPABILITY_MASTERY: ("capability_mastery_snapshot", "resolved_capability_rules", "capability_mastery_updated_at"),
    GROUP_LIVE_ADAPTATION: ("live_adaptation_snapshot", "resolved_live_adaptation_rules", "live_adaptation_updated_at"),
}

GROUP_REASON_MAP: dict[str, set[str]] = {
    "learning_context_updated": {GROUP_IDENTITY_CONTEXT},
    "personalization_updated": {GROUP_IDENTITY_CONTEXT},
    "learning_goal_updated": {GROUP_GOAL_INTENT},
    "learning_preferences_updated": {GROUP_DECLARED_PREFERENCES},
    "diagnostic_completed": {GROUP_DIAGNOSED_LEARNING},
    "ksa_updated": {GROUP_CAPABILITY_MASTERY},
    "learning_state_check_created": {GROUP_LIVE_ADAPTATION},
    "explanation_feedback_created": {GROUP_LIVE_ADAPTATION},
    "learning_node_progress_updated": {GROUP_LIVE_ADAPTATION},
}

MOA_DRIVER_RULES: dict[str, dict[str, object]] = {
    "autonomy": {"offer_bounded_choices": True, "autonomy_vs_structure_balance": "autonomy_weighted"},
    "purpose": {"relevance_explanation_frequency": "high", "impact_framing": "purpose"},
    "meaning": {"relevance_explanation_frequency": "high", "impact_framing": "purpose"},
    "achievement": {"performance_feedback_visibility": "high", "milestone_framing": "achievement"},
    "status": {"performance_feedback_visibility": "high", "milestone_framing": "recognition"},
    "creativity": {"open_ended_variants": "more", "what_if_exploration": "enabled"},
    "security": {"predictability": "high", "autonomy_vs_structure_balance": "structure_weighted"},
    "connection": {"human_centered_examples": "more", "motivational_framing_type": "relational"},
    "belonging": {"human_centered_examples": "more", "motivational_framing_type": "relational"},
    "influence": {"impact_framing": "influence", "offer_bounded_choices": True},
    "knowledge": {"conceptual_richness_allowed": "high", "format_support_type": "conceptual"},
    "experimentation": {"what_if_exploration": "enabled", "open_ended_variants": "more"},
}


@dataclass(slots=True)
class GroupResolution:
    group_id: str
    snapshot: dict[str, object]
    rules: dict[str, object]
    source_hash: str


class LearningPersonalizationLayerEngine:
    def __init__(self, repository, *, available_assistant_modes: list[str], default_assistant_mode: str) -> None:
        self.repository = repository
        self.available_assistant_modes = list(available_assistant_modes)
        self.default_assistant_mode = default_assistant_mode

    def recompute_for_reasons(
        self,
        *,
        user,
        reasons: list[str] | None = None,
        force_all: bool = False,
    ):
        reasons = [str(item).strip() for item in (reasons or []) if str(item).strip()]
        affected_groups = self._resolve_affected_groups(reasons=reasons, force_all=force_all)
        source = self._collect_source_data(user=user)
        existing = self.repository.get_user_learning_personalization_layers(user_id=user.id)

        source_hashes = dict(getattr(existing, "last_source_hashes_json", {}) or {}) if existing else {}
        trace_map = dict(getattr(existing, "source_to_group_trace_json", {}) or {}) if existing else {}
        change_log = list(getattr(existing, "change_log_json", []) or []) if existing else []

        now = datetime.now(timezone.utc)
        updates: dict[str, object] = {
            "rule_engine_version": "v1",
        }

        for group_id in GROUP_ORDER:
            if group_id not in affected_groups and not force_all:
                continue
            resolution = self._resolve_group(group_id=group_id, source=source, user=user)
            snapshot_col, rules_col, updated_at_col = GROUP_COLUMNS[group_id]
            updates[snapshot_col] = resolution.snapshot
            updates[rules_col] = resolution.rules
            updates[updated_at_col] = now
            source_hashes[group_id] = resolution.source_hash
            trace_map[group_id] = {
                "last_reasons": reasons,
                "updated_at": now.isoformat(),
                "source_sections": sorted(list(resolution.snapshot.keys())),
            }
            change_log.append(
                {
                    "group": group_id,
                    "reasons": reasons,
                    "source_hash": resolution.source_hash,
                    "updated_at": now.isoformat(),
                }
            )

        updates["last_source_hashes_json"] = source_hashes
        updates["source_to_group_trace_json"] = trace_map
        updates["change_log_json"] = change_log[-120:]

        return self.repository.upsert_user_learning_personalization_layers(user_id=user.id, fields=updates)

    def _resolve_affected_groups(self, *, reasons: list[str], force_all: bool) -> set[str]:
        if force_all or not reasons:
            return set(GROUP_ORDER)
        resolved: set[str] = set()
        for reason in reasons:
            resolved.update(GROUP_REASON_MAP.get(reason, set(GROUP_ORDER)))
        if not resolved:
            return set(GROUP_ORDER)
        return resolved

    def _collect_source_data(self, *, user) -> dict[str, object]:
        profile = self.repository.get_user_learning_profile(user.id)
        preferences = self.repository.get_user_learning_preference(user.id)
        goals = self.repository.list_user_learning_goals(user.id)
        settings_map = self._load_settings(user_id=user.id)

        latest_diagnostic_attempt = self.repository.get_latest_user_diagnostic_attempt(user_id=user.id)
        latest_diagnostic_result = (
            self.repository.get_user_diagnostic_result(attempt_id=latest_diagnostic_attempt.id)
            if latest_diagnostic_attempt is not None
            else None
        )
        diagnostic_attempts = self.repository.list_user_diagnostic_attempts(user_id=user.id)

        ksa_profile = self.repository.get_user_ksa_profile(user.id)
        latest_drill_attempt = self.repository.get_latest_user_ksa_drill_attempt(user_id=user.id)
        recent_drill_attempts = self.repository.list_user_ksa_drill_attempts(user_id=user.id, limit=10)

        state_checks = self.repository.list_learning_state_checks(user_id=user.id, limit=20)
        explanation_feedback = self.repository.list_explanation_feedback(user_id=user.id, limit=30)

        return {
            "user": user,
            "profile": profile,
            "preferences": preferences,
            "goals": goals,
            "settings": settings_map,
            "latest_diagnostic_attempt": latest_diagnostic_attempt,
            "latest_diagnostic_result": latest_diagnostic_result,
            "diagnostic_attempts": diagnostic_attempts,
            "ksa_profile": ksa_profile,
            "latest_drill_attempt": latest_drill_attempt,
            "recent_drill_attempts": recent_drill_attempts,
            "learning_state_checks": state_checks,
            "explanation_feedback": explanation_feedback,
        }

    def _load_settings(self, *, user_id: int) -> dict[str, object]:
        values: dict[str, object] = {}
        for record in self.repository.list_settings(user_id):
            try:
                values[record.key] = json.loads(record.value)
            except Exception:
                continue
        return values

    def _resolve_group(self, *, group_id: str, source: dict[str, object], user) -> GroupResolution:
        if group_id == GROUP_IDENTITY_CONTEXT:
            snapshot, rules = self._resolve_identity_context(source=source, user=user)
        elif group_id == GROUP_GOAL_INTENT:
            snapshot, rules = self._resolve_goal_intent(source=source)
        elif group_id == GROUP_DECLARED_PREFERENCES:
            snapshot, rules = self._resolve_declared_preferences(source=source)
        elif group_id == GROUP_DIAGNOSED_LEARNING:
            snapshot, rules = self._resolve_diagnosed_learning(source=source)
        elif group_id == GROUP_CAPABILITY_MASTERY:
            snapshot, rules = self._resolve_capability_mastery(source=source)
        elif group_id == GROUP_LIVE_ADAPTATION:
            snapshot, rules = self._resolve_live_adaptation(source=source)
        else:
            snapshot = {}
            rules = {}
        return GroupResolution(
            group_id=group_id,
            snapshot=snapshot,
            rules=rules,
            source_hash=_source_hash({"snapshot": snapshot, "rules": rules}),
        )

    def _resolve_identity_context(self, *, source: dict[str, object], user) -> tuple[dict[str, object], dict[str, object]]:
        profile = source.get("profile")
        settings = dict(source.get("settings") or {})

        preferred_form = str(getattr(profile, "preferred_form_of_address", "") or "").strip().lower()
        display_name = str(getattr(profile, "profile_display_name", "") or "").strip()
        nickname = str(settings.get("nickname") or "").strip()
        chosen_name = display_name or nickname or str(getattr(user, "displayname", "") or "").strip() or str(getattr(user, "username", "") or "")

        if any(token in preferred_form for token in ["formal", "mr", "mrs", "ms", "sir", "madam"]) or str(getattr(profile, "general_title", "") or "").strip():
            address_mode = "formal"
            name_frequency = "low"
        elif any(token in preferred_form for token in ["informal", "nickname", "casual", "first name"]):
            address_mode = "informal"
            name_frequency = "high"
        else:
            address_mode = "neutral"
            name_frequency = "medium"

        skills = _to_string_list(getattr(profile, "skills", []))
        interests = _to_string_list(getattr(profile, "interests", []))
        work_experience = _to_string_list(getattr(profile, "work_experience", []))
        education_history = _to_string_list(getattr(profile, "education_history", []))
        current_skill_areas = _to_string_list(getattr(profile, "current_skill_areas", []))

        occupation = str(source.get("settings", {}).get("occupation") or "").strip()
        location = str(getattr(profile, "contact_location", "") or "").strip()
        about_text = " ".join(
            [
                str(getattr(profile, "about_me", "") or "").strip(),
                str(getattr(profile, "learning_context_notes", "") or "").strip(),
                str(source.get("settings", {}).get("more_about_user") or "").strip(),
            ]
        ).strip()

        example_domains = [item for item in [occupation, *current_skill_areas, *skills, *interests] if item]
        if not example_domains:
            example_domains = ["general"]

        education_text = " ".join(education_history).lower()
        assumed_theoretical_tolerance = "high" if any(token in education_text for token in ["master", "phd", "bachelor", "university"]) else "medium"
        assumed_academic_jargon_tolerance = "medium" if education_history else "low"

        technical_vocab_ceiling = "high" if len(skills) >= 5 else "medium"
        if any("beginner" in item.lower() for item in skills):
            technical_vocab_ceiling = "low"

        snapshot = {
            "identity_profile": {
                "chosen_name": chosen_name,
                "preferred_form_of_address": str(getattr(profile, "preferred_form_of_address", "") or "").strip(),
                "general_title": str(getattr(profile, "general_title", "") or "").strip(),
                "date_of_birth": str(getattr(profile, "date_of_birth", "") or "").strip(),
                "about_me": str(getattr(profile, "about_me", "") or "").strip(),
            },
            "context_profile": {
                "location": location,
                "occupation": occupation,
                "work_experience": work_experience,
                "education_history": education_history,
                "skills": skills,
                "interests": interests,
                "reason_for_learning": str(getattr(profile, "current_reason_for_learning", "") or "").strip(),
                "learning_context_notes": str(getattr(profile, "learning_context_notes", "") or "").strip(),
            },
            "example_relevance_profile": {
                "preferred_example_domains": example_domains[:12],
                "motivation_context_pool": interests[:10],
                "example_personalization_pool": list(dict.fromkeys((interests + skills + current_skill_areas)))[:14],
                "story_context_pool": work_experience[:10],
            },
            "constraints_profile": {
                "identity_sensitive_framing": bool(about_text),
                "constraint_flags": _extract_flags(about_text, ["accessibility", "disability", "time", "family", "stress"]),
                "avoidance_flags": _extract_flags(about_text, ["avoid", "no ", "sensitive", "trigger"]),
                "relevance_notes": about_text,
            },
        }

        rules = {
            "addressing_rules": {
                "address_mode": address_mode,
                "name_token": chosen_name,
                "use_direct_name_frequency": name_frequency,
                "pronoun_or_salutation_behavior": "title_and_surname" if address_mode == "formal" else "friendly_name",
            },
            "contextualization_rules": {
                "response_language": "en",
                "cultural_example_filter": location or "global",
                "idiom_usage": "low" if technical_vocab_ceiling == "low" else "medium",
                "technical_vocabulary_ceiling": technical_vocab_ceiling,
                "preferred_case_types": _guess_case_types(example_domains=example_domains),
                "baseline_domain_familiarity": "high" if len(work_experience) >= 2 else "medium",
            },
            "relevance_framing_rules": {
                "professional_relevance_weight": 0.8 if occupation else 0.55,
                "connect_to_job_hobby_project_frequency": "high" if occupation or interests else "medium",
                "motivation_context_pool": interests[:8],
            },
            "background_assumption_rules": {
                "assumed_theoretical_tolerance": assumed_theoretical_tolerance,
                "assumed_academic_jargon_tolerance": assumed_academic_jargon_tolerance,
                "need_for_concept_unpacking": "high" if assumed_academic_jargon_tolerance == "low" else "medium",
                "skip_known_basics": len(skills) >= 4,
                "bridge_from_prior_knowledge": skills[:6],
                "estimated_transfer_capacity": "high" if len(skills) + len(work_experience) >= 6 else "medium",
            },
        }
        return snapshot, rules

    def _resolve_goal_intent(self, *, source: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
        goals = list(source.get("goals") or [])
        goal_items = []
        active_goal = None
        for goal in goals:
            item = {
                "id": str(goal.id),
                "target_topic": str(goal.target_topic or "").strip(),
                "target_level": str(goal.target_level or "").strip(),
                "reason_for_learning": str(goal.reason_for_learning or "").strip(),
                "deadline": goal.deadline.isoformat() if isinstance(goal.deadline, date) else None,
                "priority": str(goal.priority or ""),
                "notes": str(goal.notes or "").strip(),
                "is_active": bool(goal.is_active),
            }
            goal_items.append(item)
            if item["is_active"] and active_goal is None:
                active_goal = item
        if active_goal is None and goal_items:
            active_goal = goal_items[0]

        days_to_deadline = _days_to_deadline(active_goal.get("deadline") if active_goal else None)
        urgency = "low"
        if days_to_deadline is not None and days_to_deadline <= 14:
            urgency = "high"
        elif days_to_deadline is not None and days_to_deadline <= 45:
            urgency = "medium"

        reason_text = str((active_goal or {}).get("reason_for_learning") or "")
        utility_frame = _detect_utility_frame(reason_text=reason_text)

        target_level = str((active_goal or {}).get("target_level") or "").lower()
        abstraction_map = {
            "beginner": ("concrete", "guided", "deep"),
            "intermediate": ("mixed", "shared", "medium"),
            "advanced": ("abstract", "independent", "light"),
        }
        abstraction, independence, scaffolding = abstraction_map.get(target_level, ("mixed", "shared", "medium"))

        snapshot = {
            "learning_goals": goal_items,
            "active_goal_id": (active_goal or {}).get("id"),
            "goal_rule_snapshot": {
                "active_topic": (active_goal or {}).get("target_topic", ""),
                "active_target_level": (active_goal or {}).get("target_level", ""),
                "urgency": urgency,
                "utility_frame": utility_frame,
                "days_to_deadline": days_to_deadline,
            },
        }

        rules = {
            "scope_rules": {
                "topic_scope": (active_goal or {}).get("target_topic", ""),
                "allowed_example_space": [
                    (active_goal or {}).get("target_topic", ""),
                    utility_frame,
                ],
                "concept_dependency_map": "strict" if urgency == "high" else "balanced",
                "breadth_vs_focus": "focus" if urgency in {"medium", "high"} else "balanced",
                "essentials_first": urgency in {"medium", "high"},
            },
            "difficulty_target_rules": {
                "target_abstraction_level": abstraction,
                "target_independence_level": independence,
                "acceptable_scaffolding_depth": scaffolding,
                "mastery_threshold_profile": target_level or "intermediate",
            },
            "urgency_rules": {
                "pace_pressure": urgency,
                "focus_narrowing": urgency == "high",
                "remediation_tolerance": "low" if urgency == "high" else "medium",
                "enrichment_suppression": urgency == "high",
                "checkpoint_density": "high" if urgency == "high" else "medium",
                "recap_compression": "high" if urgency == "high" else "low",
            },
            "utility_framing_rules": {
                "utility_frame": utility_frame,
                "example_selection_priority": utility_frame,
                "assessment_style_bias": _assessment_style_for_utility_frame(utility_frame),
                "goal_attention_weight": _goal_weight_from_priority(str((active_goal or {}).get("priority") or "")),
                "review_frequency_weight": 0.8 if urgency == "high" else 0.6,
                "session_success_check_type": "progress_to_goal",
                "end_of_node_reflection_prompt_type": utility_frame,
            },
        }
        return snapshot, rules

    def _resolve_declared_preferences(self, *, source: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
        preference = source.get("preferences")
        if preference is None:
            pref = {
                "preferred_pace": "balanced",
                "explanation_depth": "balanced",
                "examples_vs_theory": "balanced",
                "structure_preference": "balanced",
                "checkpoint_frequency": "medium",
                "encouragement_level": "balanced",
                "guidance_level": "balanced",
                "recap_frequency": "medium",
                "preferred_learning_format": "mixed",
                "custom_preference_note": "",
            }
        else:
            pref = {
                "preferred_pace": str(preference.preferred_pace),
                "explanation_depth": str(preference.explanation_depth),
                "examples_vs_theory": str(preference.examples_vs_theory),
                "structure_preference": str(preference.structure_preference),
                "checkpoint_frequency": str(preference.checkpoint_frequency),
                "encouragement_level": str(preference.encouragement_level),
                "guidance_level": str(preference.guidance_level),
                "recap_frequency": str(preference.recap_frequency),
                "preferred_learning_format": str(preference.preferred_learning_format),
                "custom_preference_note": str(preference.custom_preference_note or "").strip(),
            }

        custom_flags = _extract_custom_preference_flags(pref["custom_preference_note"])
        snapshot = {
            "declared_preferences": pref,
            "declared_preference_flags": custom_flags,
        }

        pace_map = {
            "slow": ("small", 1, 0),
            "balanced": ("medium", 2, 1),
            "fast": ("large", 3, 2),
        }
        step_size, concepts_per_turn, advance_threshold = pace_map.get(pref["preferred_pace"], pace_map["balanced"])

        depth_map = {
            "concise": ("light", "low", False),
            "balanced": ("medium", "medium", False),
            "detailed": ("deep", "high", True),
        }
        explanation_depth, definition_density, secondary_detail = depth_map.get(pref["explanation_depth"], depth_map["balanced"])

        order_map = {
            "more_examples": ("example_first", "high", "long"),
            "balanced": ("mixed", "medium", "medium"),
            "more_theory": ("concept_first", "low", "short"),
        }
        explanation_order, example_density, abstraction_delay = order_map.get(pref["examples_vs_theory"], order_map["balanced"])

        structure_map = {
            "more_structured": ("high", True, True, "short"),
            "balanced": ("medium", True, True, "medium"),
            "more_conversational": ("low", False, False, "long"),
        }
        structure_level, uses_lists, uses_signposting, paragraph_target = structure_map.get(
            pref["structure_preference"],
            structure_map["balanced"],
        )

        frequency_map = {"low": "low", "medium": "medium", "high": "high"}

        guidance_map = {
            "step_by_step": ("high", True, "low"),
            "balanced": ("medium", True, "medium"),
            "more_independent": ("low", False, "high"),
        }
        scaffolding_strength, hint_before_answer, independence_expectation = guidance_map.get(
            pref["guidance_level"],
            guidance_map["balanced"],
        )

        rules = {
            "response_length": "concise" if pref["explanation_depth"] == "concise" else "standard",
            "explanation_granularity": explanation_depth,
            "explanation_order": explanation_order,
            "structure_density": structure_level,
            "check_frequency": frequency_map.get(pref["checkpoint_frequency"], "medium"),
            "scaffolding_strength": scaffolding_strength,
            "recap_interval": frequency_map.get(pref["recap_frequency"], "medium"),
            "exercise_ratio": "high" if pref["preferred_learning_format"] == "exercises" else "medium",
            "tone_warmth": "high" if pref["encouragement_level"] == "high" else "medium",
            "resolved_declared_tutor_rules": {
                "step_size": step_size,
                "concepts_per_turn": concepts_per_turn,
                "advance_without_confirmation_threshold": advance_threshold,
                "default_explanation_depth": explanation_depth,
                "definition_density": definition_density,
                "include_secondary_detail": secondary_detail,
                "example_density": example_density,
                "abstraction_delay": abstraction_delay,
                "format_structure_level": structure_level,
                "uses_lists": uses_lists,
                "uses_signposting": uses_signposting,
                "paragraph_length_target": paragraph_target,
                "micro_check_interval": frequency_map.get(pref["checkpoint_frequency"], "medium"),
                "retrieval_prompt_frequency": frequency_map.get(pref["checkpoint_frequency"], "medium"),
                "encouragement_frequency": frequency_map.get(pref["encouragement_level"], "medium"),
                "affirmation_style": "energetic" if pref["encouragement_level"] == "high" else "calm",
                "hint_before_answer": hint_before_answer,
                "independence_expectation": independence_expectation,
                "mini_summary_frequency": frequency_map.get(pref["recap_frequency"], "medium"),
                "response_mode_bias": pref["preferred_learning_format"],
                "custom_preference_flags": custom_flags,
            },
        }
        return snapshot, rules

    def _resolve_diagnosed_learning(self, *, source: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
        latest_attempt = source.get("latest_diagnostic_attempt")
        latest_result_row = source.get("latest_diagnostic_result")
        result_json = dict(getattr(latest_result_row, "result_json", {}) or {})

        laa = dict(result_json.get("LAA") or {})
        moa = dict(result_json.get("MOA") or {})
        lta = dict(result_json.get("LTA") or {})
        laa_dimensions = _flatten_laa_dimensions(laa)

        goal_clarity = _pick_dimension(laa_dimensions, ["zielklarheit", "goal clarity"], default=55.0)
        sustainability = _pick_dimension(laa_dimensions, ["nachhaltigkeit", "retention"], default=55.0)
        self_efficacy = _pick_dimension(laa_dimensions, ["selbstwirksamkeit", "selbstvertrauen"], default=55.0)
        personalization_need = _pick_dimension(laa_dimensions, ["individualisierungswunsch", "selbststeuerung"], default=55.0)
        frustration = _pick_dimension(laa_dimensions, ["frustrationsanfaelligkeit", "frustration"], default=50.0)
        technical_affinity = _pick_dimension(laa_dimensions, ["technikaffinitaet", "technical"], default=50.0)
        time_pressure = _pick_dimension(laa_dimensions, ["zeitdruck", "time pressure"], default=50.0)
        emotional_safety = _pick_dimension(laa_dimensions, ["emotionale_sicherheit", "emotional"], default=55.0)

        moa_traits = [str(item).strip() for item in list(moa.get("dominant_traits") or []) if str(item).strip()][:2]
        moa_rules: dict[str, object] = {}
        for trait in moa_traits:
            moa_rules.update(MOA_DRIVER_RULES.get(_normalize_driver_key(trait), {}))

        lta_classification = str(lta.get("classification") or "balanced")
        lta_dominant = [str(item) for item in list(lta.get("dominant_traits") or [])]
        format_support = "neutral"
        if lta_classification == "dominant" and lta_dominant:
            channel = lta_dominant[0]
            if channel == "auditiv":
                format_support = "dialogic_explanation_bias"
            elif channel == "visuell":
                format_support = "spatial_structural_wording"
            elif channel == "kinaesthetisch":
                format_support = "practice_first_bias"
            elif channel == "lesen_schreiben":
                format_support = "text_clarity"
        elif lta_classification == "mixed":
            format_support = "rotate_modes"

        snapshot = {
            "diagnostic_attempts": [
                {
                    "attempt_id": str(item.id),
                    "status": str(item.status),
                    "is_latest": bool(item.is_latest),
                    "completed_at": item.completed_at.isoformat() if getattr(item, "completed_at", None) else None,
                }
                for item in list(source.get("diagnostic_attempts") or [])[:20]
            ],
            "active_diagnostic_profile": {
                "attempt_id": str(getattr(latest_attempt, "id", "") or ""),
                "status": str(getattr(latest_attempt, "status", "") or ""),
                "definition_versions": dict(getattr(latest_attempt, "definition_versions", {}) or {}) if latest_attempt else {},
                "laa_dimensions": laa_dimensions,
                "moa_dominant_drivers": moa_traits,
                "lta_classification": lta_classification,
                "lta_dominant": lta_dominant,
            },
            "resolved_diagnostic_rules": {},
            "diagnostic_change_log": [
                {
                    "attempt_id": str(getattr(latest_attempt, "id", "") or ""),
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                }
            ] if latest_attempt else [],
        }

        support_intensity = "high" if self_efficacy < 45 or frustration > 70 else "medium"
        if goal_clarity > 70 and self_efficacy > 70 and frustration < 40:
            support_intensity = "low"

        rules = {
            "support_intensity": support_intensity,
            "motivational_framing_type": "achievement" if "achievement" in [_normalize_driver_key(item) for item in moa_traits] else "relevance",
            "format_support_type": format_support,
            "self_regulation_support": "high" if goal_clarity < 45 else "medium",
            "emotional_safety_level": "high" if emotional_safety < 45 or frustration > 70 else "medium",
            "feedback_density": "high" if frustration > 65 else "medium",
            "autonomy_vs_structure_balance": "structure_weighted" if personalization_need < 45 else "balanced",
            "goal_restatement_frequency": "high" if goal_clarity < 45 else "low",
            "retention_support_level": "high" if sustainability < 50 else "medium",
            "difficulty_jump_policy": "small" if self_efficacy < 50 else "balanced",
            "progress_evidence_frequency": "high" if self_efficacy < 50 else "medium",
            "visible_personalization_level": "high" if personalization_need > 70 else "medium",
            "frustration_protection": "strong" if frustration > 65 else "medium",
            "technical_jargon_tolerance": "high" if technical_affinity > 70 else "medium",
            "time_pressure_compaction": "high" if time_pressure > 70 else "medium",
            "moa_directives": moa_rules,
            "lta_directives": {
                "classification": lta_classification,
                "dominant": lta_dominant,
            },
        }

        snapshot["resolved_diagnostic_rules"] = rules
        return snapshot, rules

    def _resolve_capability_mastery(self, *, source: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
        ksa_profile = source.get("ksa_profile")
        profile_json = dict(getattr(ksa_profile, "profile_json", {}) or {})
        knowledge = dict(profile_json.get("knowledge") or {})
        skills = dict(profile_json.get("skills") or {})
        abilities = dict(profile_json.get("abilities") or {})
        drill_state = dict(profile_json.get("drill_state") or {})
        topic_nodes = dict(drill_state.get("topic_nodes") or {})

        latest_drill = source.get("latest_drill_attempt")
        latest_drill_result = dict(getattr(latest_drill, "result_json", {}) or {}) if latest_drill else {}
        latest_topic_updates = dict(latest_drill_result.get("topic_updates") or {})

        topic_state: dict[str, dict[str, object]] = {}
        for topic_key in list(KNOWLEDGE_TOPICS) + list(SKILL_TOPICS) + list(ABILITY_TOPICS):
            group = "knowledge" if topic_key in KNOWLEDGE_TOPICS else ("skills" if topic_key in SKILL_TOPICS else "abilities")
            baseline = _read_level(group=group, key=topic_key, knowledge=knowledge, skills=skills, abilities=abilities)
            node = dict(topic_nodes.get(topic_key) or {})
            final_level = float(node.get("level") or baseline)
            competence_level = max(1.0, min(5.0, final_level))
            confidence = float(node.get("confidence") or 0.7)
            map_decay = int(node.get("map_decay_events_total") or 0)
            delta = float(dict(latest_topic_updates.get(topic_key) or {}).get("delta") or 0.0)
            topic_state[topic_key] = {
                "group": group,
                "competence_level": round(competence_level, 3),
                "confidence_level": round(max(0.0, min(1.0, confidence)), 3),
                "chart_level": int(round(competence_level)),
                "delta_recent": round(delta, 3),
                "map_decay_events_total": map_decay,
                "latest_status": str(node.get("status") or "baseline"),
            }

        levels = [float(item["competence_level"]) for item in topic_state.values()] or [2.0]
        confidence_values = [float(item["confidence_level"]) for item in topic_state.values()] or [0.7]
        avg_level = sum(levels) / len(levels)
        avg_confidence = sum(confidence_values) / len(confidence_values)

        weak_topics = [key for key, value in topic_state.items() if float(value["competence_level"]) <= 2.4]
        strong_topics = [key for key, value in topic_state.items() if float(value["competence_level"]) >= 3.8]
        remediation_topics = [
            key
            for key, value in topic_state.items()
            if int(value["map_decay_events_total"]) > 0 or float(value["competence_level"]) <= 2.2
        ]

        derived = dict(dict(profile_json.get("assessment_details") or {}).get("derived") or {})
        speed_multiplier = float(derived.get("learning_speed_multiplier") or 1.0)

        snapshot = {
            "ksa_topic_state": topic_state,
            "topic_mastery_estimates": {key: value["competence_level"] for key, value in topic_state.items()},
            "topic_confidence_estimates": {key: value["confidence_level"] for key, value in topic_state.items()},
            "review_decay_state": {key: value["map_decay_events_total"] for key, value in topic_state.items()},
            "recent_assessment_history": [
                {
                    "attempt_id": str(item.id),
                    "status": str(item.status),
                    "completed_at": item.completed_at.isoformat() if getattr(item, "completed_at", None) else None,
                }
                for item in list(source.get("recent_drill_attempts") or [])[:10]
            ],
        }

        confidence_support = "balanced"
        if avg_level < 2.6 and avg_confidence > 0.75:
            confidence_support = "more_checking"
        elif avg_level > 3.4 and avg_confidence < 0.55:
            confidence_support = "encourage_and_demonstrate"
        elif avg_level < 2.6 and avg_confidence < 0.55:
            confidence_support = "heavy_scaffolding"

        rules = {
            "starting_difficulty": "low" if avg_level < 2.5 else ("medium" if avg_level < 3.6 else "high"),
            "allowed_concept_jump_size": "small" if avg_level < 2.8 else "medium",
            "skip_basics": avg_level >= 3.7,
            "use_remediation": bool(remediation_topics),
            "hint_density": "high" if avg_level < 2.6 else "medium",
            "ask_vs_tell": "ask_first" if avg_level >= 3.4 else "tell_then_ask",
            "node_readiness": "needs_review" if bool(remediation_topics) else "ready",
            "mastery_confidence": "high" if avg_level >= 3.7 and avg_confidence >= 0.7 else "medium",
            "topic_difficulty_band": {key: _difficulty_band(float(value["competence_level"])) for key, value in topic_state.items()},
            "entry_point_depth": "intermediate" if avg_level >= 3.0 else "intro",
            "skip_intro_basics": avg_level >= 3.8,
            "challenge_ramp_rate": "fast" if speed_multiplier > 1.2 else "normal",
            "confidence_sensitive_support": confidence_support,
            "response_compaction": "high" if speed_multiplier > 1.2 else "normal",
            "practice_count_before_advance": 2 if speed_multiplier > 1.2 else 4,
            "required_remediation_topics": remediation_topics,
            "cannot_advance_flags": {key: True for key in remediation_topics},
            "review_priority": sorted(remediation_topics + weak_topics),
            "recall_check_bias": "high" if any(int(value["map_decay_events_total"]) > 0 for value in topic_state.values()) else "medium",
            "bridge_from_strengths": strong_topics[:4],
            "protect_against_overchallenge_in_weak_topics": weak_topics[:6],
        }
        return snapshot, rules

    def _resolve_live_adaptation(self, *, source: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
        state_checks = list(source.get("learning_state_checks") or [])
        feedback_rows = list(source.get("explanation_feedback") or [])

        latest_state = state_checks[0] if state_checks else None
        current_session_state = {
            "mood": str(getattr(latest_state, "mood", "") or "").strip(),
            "perceived_difficulty": str(getattr(latest_state, "perceived_difficulty", "") or "").strip(),
            "needs_pause_or_input": str(getattr(latest_state, "needs_pause_or_input", "") or "").strip(),
            "preferred_format": str(getattr(latest_state, "preferred_format", "") or "").strip(),
            "notes": str(getattr(latest_state, "notes", "") or "").strip(),
        }

        notes_text = " ".join(str(getattr(item, "notes", "") or "") for item in state_checks[:8]).lower()
        feedback_text = " ".join(str(getattr(item, "feedback_text", "") or "") for item in feedback_rows[:20]).lower()

        ratings = [int(getattr(item, "rating", 3) or 3) for item in feedback_rows[:20]]
        avg_rating = (sum(ratings) / len(ratings)) if ratings else 3.0
        re_explain_count = sum(1 for item in feedback_rows[:20] if bool(getattr(item, "re_explain_requested", False)))
        struggle_streak = sum(1 for item in feedback_rows[:6] if int(getattr(item, "rating", 3) or 3) <= 2)
        success_streak = sum(1 for item in feedback_rows[:6] if int(getattr(item, "rating", 3) or 3) >= 4)

        observed = {
            "explanation_length_preference_observed": "shorter" if "too long" in feedback_text else "neutral",
            "example_bias_observed": "example_first" if "abstract" in feedback_text else "neutral",
            "structure_need_observed": "high" if "step by step" in feedback_text or "step-by-step" in feedback_text else "medium",
            "language_simplicity_need_observed": "high" if "too complicated" in feedback_text else "medium",
        }

        drop_off_risk = "low"
        if avg_rating <= 2.5 or re_explain_count >= 3 or "pause" in notes_text:
            drop_off_risk = "high"
        elif avg_rating <= 3.2 or re_explain_count >= 2:
            drop_off_risk = "medium"

        snapshot = {
            "current_session_state": current_session_state,
            "node_session_state": {
                "struggle_streak": struggle_streak,
                "success_streak": success_streak,
                "drop_off_risk": drop_off_risk,
                "average_explanation_rating": round(avg_rating, 3),
                "re_explain_count": re_explain_count,
            },
            "observed_preference_patterns": observed,
            "effective_strategy_patterns": {
                "high_rating_count": sum(1 for value in ratings if value >= 4),
            },
            "ineffective_strategy_patterns": {
                "low_rating_count": sum(1 for value in ratings if value <= 2),
            },
        }

        perceived_difficulty = current_session_state["perceived_difficulty"].lower()
        mood = current_session_state["mood"].lower()
        needs_pause = "pause" in current_session_state["needs_pause_or_input"].lower() or "pause" in current_session_state["notes"].lower()
        needs_more_explanation = any(token in feedback_text for token in ["more explanation", "unclear", "confusing", "too short"])
        needs_more_challenge = any(token in feedback_text for token in ["too easy", "more challenge", "harder"])
        needs_different_format = bool(current_session_state["preferred_format"]) and current_session_state["preferred_format"].lower() not in {"", "none"}

        rules = {
            "turn_length": "short" if drop_off_risk == "high" else "medium",
            "turn_complexity": "low" if perceived_difficulty in {"hard", "high"} else "medium",
            "next_teaching_move": _next_teaching_move(
                needs_pause=needs_pause,
                needs_more_explanation=needs_more_explanation,
                needs_more_challenge=needs_more_challenge,
                drop_off_risk=drop_off_risk,
            ),
            "offer_pause_or_micro_stop": needs_pause,
            "expand_current_concept": needs_more_explanation,
            "increase_independence": needs_more_challenge,
            "format_override": current_session_state["preferred_format"] if needs_different_format else "",
            "supportive_tone_adjustment": "high" if mood in {"tired", "frustrated", "stressed"} else "medium",
            "challenge_suppression_if_needed": perceived_difficulty in {"hard", "high"} or drop_off_risk == "high",
            "response_energy_budget": "low" if mood in {"tired", "low"} else "normal",
            "task_size": "small" if mood in {"tired", "low"} else "medium",
            "complexity_adjustment": "down" if perceived_difficulty in {"hard", "high"} else "neutral",
            "worked_example_bias": "high" if perceived_difficulty in {"hard", "high"} else "medium",
            "must_change_strategy": struggle_streak >= 3,
            "reduce_turn_burden": drop_off_risk == "high",
            "increase_relevance_visibility": drop_off_risk in {"medium", "high"},
            "avoid_multi_part_tasks": drop_off_risk == "high",
            "observed_updates": observed,
        }
        return snapshot, rules


def _extract_flags(text: str, keywords: list[str]) -> list[str]:
    lowered = str(text or "").lower()
    flags: list[str] = []
    for token in keywords:
        if token in lowered and token not in flags:
            flags.append(token)
    return flags


def _to_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            result.append(text)
    return result


def _source_hash(payload: dict[str, object]) -> str:
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _guess_case_types(*, example_domains: list[str]) -> list[str]:
    combined = " ".join(example_domains).lower()
    candidates = []
    if any(token in combined for token in ["engineer", "dev", "ops", "software", "it", "cloud"]):
        candidates.append("technical")
    if any(token in combined for token in ["manager", "lead", "business", "sales", "finance"]):
        candidates.append("business")
    if any(token in combined for token in ["teacher", "learn", "student", "education"]):
        candidates.append("education")
    return candidates or ["general"]


def _days_to_deadline(deadline_iso: str | None) -> int | None:
    if not deadline_iso:
        return None
    try:
        deadline = date.fromisoformat(deadline_iso)
    except Exception:
        return None
    return (deadline - datetime.now(timezone.utc).date()).days


def _detect_utility_frame(*, reason_text: str) -> str:
    text = reason_text.lower()
    if any(token in text for token in ["exam", "test", "certificate", "certification"]):
        return "exam"
    if any(token in text for token in ["project", "build", "portfolio"]):
        return "project"
    if any(token in text for token in ["job", "work", "career", "promotion"]):
        return "work"
    if any(token in text for token in ["transition", "switch", "change field"]):
        return "transition"
    return "hobby" if any(token in text for token in ["curious", "hobby", "interest", "fun"]) else "project"


def _assessment_style_for_utility_frame(utility_frame: str) -> str:
    if utility_frame == "exam":
        return "checkpoint_heavy"
    if utility_frame == "work":
        return "scenario_based"
    if utility_frame == "project":
        return "deliverable_based"
    return "mixed"


def _goal_weight_from_priority(priority: str) -> float:
    normalized = priority.lower().strip()
    if normalized == "high":
        return 1.0
    if normalized == "low":
        return 0.4
    return 0.7


def _extract_custom_preference_flags(note: str) -> list[str]:
    lowered = str(note or "").lower()
    flags: list[str] = []
    checks = {
        "explain_slowly": ["explain slowly", "slowly", "slower"],
        "avoid_theory": ["avoid theory", "less theory", "too much theory"],
        "practical_examples": ["practical", "real world", "examples"],
        "step_by_step": ["step by step", "step-by-step"],
        "short_answers": ["short", "concise", "brief"],
        "simple_language": ["simple language", "simpler", "easy words"],
    }
    for key, tokens in checks.items():
        if any(token in lowered for token in tokens):
            flags.append(key)
    if not flags and lowered:
        words = [item for item in re.split(r"[^a-z0-9]+", lowered) if item]
        flags.extend([f"custom:{item}" for item in words[:4]])
    return flags


def _flatten_laa_dimensions(laa_payload: dict[str, Any]) -> dict[str, float]:
    result: dict[str, float] = {}
    section_profiles = dict(laa_payload.get("section_profiles") or {})
    for section in section_profiles.values():
        dims = dict(section.get("dimensions_normalized_0_100") or {})
        for key, value in dims.items():
            try:
                parsed = float(value)
            except Exception:
                continue
            current = result.get(str(key))
            if current is None:
                result[str(key)] = parsed
            else:
                result[str(key)] = (current + parsed) / 2.0
    return result


def _pick_dimension(dimensions: dict[str, float], aliases: list[str], *, default: float) -> float:
    normalized = {str(key).lower(): float(value) for key, value in dimensions.items()}
    for alias in aliases:
        for key, value in normalized.items():
            if alias in key:
                return value
    return default


def _normalize_driver_key(value: str) -> str:
    return re.sub(r"\s+", "_", str(value or "").strip().lower())


def _read_level(*, group: str, key: str, knowledge: dict[str, Any], skills: dict[str, Any], abilities: dict[str, Any]) -> float:
    source = knowledge if group == "knowledge" else (skills if group == "skills" else abilities)
    try:
        return max(1.0, min(5.0, float(source.get(key) or 2.0)))
    except Exception:
        return 2.0


def _difficulty_band(level: float) -> str:
    if level <= 2.0:
        return "foundational"
    if level <= 3.2:
        return "intermediate"
    if level <= 4.2:
        return "advanced"
    return "expert"


def _next_teaching_move(*, needs_pause: bool, needs_more_explanation: bool, needs_more_challenge: bool, drop_off_risk: str) -> str:
    if needs_pause:
        return "offer_pause"
    if drop_off_risk == "high":
        return "reduce_burden_and_relevance"
    if needs_more_explanation:
        return "re_explain_with_examples"
    if needs_more_challenge:
        return "increase_independence"
    return "continue_balanced"
