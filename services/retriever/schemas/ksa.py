from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


KSAValue = Literal[1, 2, 3, 4, 5]


class KSAKnowledgeRead(BaseModel):
    stem_fundamentals: KSAValue
    information_technology: KSAValue
    humanities_social_sciences: KSAValue
    languages_linguistics: KSAValue
    business_commerce: KSAValue
    legal_ethics: KSAValue
    health_wellness: KSAValue


class KSASkillsRead(BaseModel):
    literacy_numeracy: KSAValue
    digital_craft: KSAValue
    strategic_execution: KSAValue
    operational_skills: KSAValue
    relational_skills: KSAValue
    research_inquiry: KSAValue


class KSAAbilitiesRead(BaseModel):
    quantitative_reasoning: KSAValue
    verbal_comprehension: KSAValue
    spatial_visualization: KSAValue
    executive_function: KSAValue
    sensory_perceptual: KSAValue
    social_emotional_capacity: KSAValue
    divergent_thinking: KSAValue


class KSAProfileRead(BaseModel):
    user_id: int
    has_assessment: bool = False
    profile_source: Literal["student_default_baseline", "placeholder_baseline", "assessment"] = "placeholder_baseline"
    scale_min: Literal[1] = 1
    scale_max: Literal[5] = 5
    dreyfus_levels: list[str] = Field(
        default_factory=lambda: ["Novice", "Advanced", "Competent", "Proficient", "Expert"]
    )
    knowledge: KSAKnowledgeRead
    skills: KSASkillsRead
    abilities: KSAAbilitiesRead
    assessment_details: dict[str, object] | None = None
    drill_state: dict[str, object] | None = None
    learning_speed_multiplier: float | None = None
    updated_at: datetime | None = None
