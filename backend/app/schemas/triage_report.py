"""Pydantic schemas for TriageReport and VLM output."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# VLM output classification labels
Classification = Literal[
    "CONFIRMED_FIRE", "PROBABLE_FIRE", "FALSE_POSITIVE", "INDUSTRIAL_SOURCE"
]

RecommendedAction = Literal[
    "MONITOR", "INVESTIGATE", "DISPATCH", "DISPATCH_LOCAL", "DISPATCH_REGIONAL", "EVACUATE"
]

TriageSource = Literal["vlm", "rule_based"]


class TriageOutput(BaseModel):
    """
    Structured output from VLM triage or rule-based fallback.
    NOTE: raw_vlm_output is intentionally excluded (ADR-014) — logged via structlog only.
    """
    classification: Classification
    confidence: float = Field(..., ge=0.0, le=1.0)
    danger_level: int = Field(..., ge=1, le=5)
    fire_area_ha: float | None = Field(None, ge=0.0)
    smoke_direction: str | None = None
    summary: str | None = None
    recommended_action: RecommendedAction = "MONITOR"
    triage_source: TriageSource = "vlm"  # "vlm" | "rule_based"


class TriageReportSchema(BaseModel):
    """Output schema for a triage report returned by the API."""
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: uuid.UUID
    event_id: uuid.UUID
    classification: str
    confidence: float | None
    fire_area_ha: float | None
    smoke_direction: str | None
    danger_level: int | None
    summary: str | None
    recommended_action: str | None
    triage_source: str      # "VLM" | "RULE_BASED_FALLBACK"
    processed_at: datetime
