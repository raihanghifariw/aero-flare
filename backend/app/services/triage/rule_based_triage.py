"""
Rule-based fallback triage — activates when all VLM models are unavailable.
Safety-critical: ensures no high-FRP event goes unalerted. (ADR-011, project_rules §8)
"""
from __future__ import annotations

import structlog

from app.models.fire_event import FireEvent
from app.schemas.common import get_trace_id
from app.schemas.triage_report import TriageOutput

logger = structlog.get_logger()

# FRP thresholds for rule-based classification
FRP_CONFIRMED_THRESHOLD = 100.0   # > 100 MW → CONFIRMED_FIRE (major active fire)
FRP_HIGH_THRESHOLD = 50.0          # > 50 MW  → PROBABLE_FIRE, danger 3
FRP_MODERATE_THRESHOLD = 15.0      # > 15 MW  → PROBABLE_FIRE, danger 2


def rule_based_triage(event: FireEvent) -> TriageOutput:
    """
    Deterministic triage when VLM is unavailable.

    Rules (based on FIRMS FRP — Fire Radiative Power in MW):
      FRP > 100 MW → CONFIRMED_FIRE,  danger_level=4, DISPATCH
      FRP >  50 MW → PROBABLE_FIRE,   danger_level=3, DISPATCH
      FRP >  15 MW → PROBABLE_FIRE,   danger_level=2, MONITOR
      FRP ≤  15 MW → PROBABLE_FIRE,   danger_level=1, MONITOR
      FRP unknown  → PROBABLE_FIRE,   danger_level=2, MONITOR

    Always sets triage_source='rule_based'.
    """
    frp = event.frp

    if frp is not None and frp > FRP_CONFIRMED_THRESHOLD:
        result = TriageOutput(
            classification="CONFIRMED_FIRE",
            confidence=0.65,
            danger_level=4,
            fire_area_ha=None,
            smoke_direction=None,
            recommended_action="DISPATCH",
            summary=(
                f"VLM unavailable — rule-based triage applied. "
                f"FRP={frp:.1f}MW exceeds {FRP_CONFIRMED_THRESHOLD}MW threshold. "
                f"High-confidence active fire. Dispatch units immediately."
            ),
            triage_source="rule_based",
        )
    elif frp is not None and frp > FRP_HIGH_THRESHOLD:
        result = TriageOutput(
            classification="PROBABLE_FIRE",
            confidence=0.55,
            danger_level=3,
            fire_area_ha=None,
            smoke_direction=None,
            recommended_action="DISPATCH_LOCAL",
            summary=(
                f"VLM unavailable — rule-based triage applied. "
                f"FRP={frp:.1f}MW exceeds {FRP_HIGH_THRESHOLD}MW threshold. "
                f"Probable active fire. Dispatch local team for verification."
            ),
            triage_source="rule_based",
        )
    elif frp is not None and frp > FRP_MODERATE_THRESHOLD:
        result = TriageOutput(
            classification="PROBABLE_FIRE",
            confidence=0.40,
            danger_level=2,
            fire_area_ha=None,
            smoke_direction=None,
            recommended_action="MONITOR",
            summary=(
                f"VLM unavailable — rule-based triage applied. "
                f"FRP={frp:.1f}MW. Moderate heat signature. Monitor closely."
            ),
            triage_source="rule_based",
        )
    else:
        result = TriageOutput(
            classification="PROBABLE_FIRE",
            confidence=0.30,
            danger_level=2,
            fire_area_ha=None,
            smoke_direction=None,
            recommended_action="MONITOR",
            summary=(
                f"VLM unavailable — rule-based triage applied. "
                f"FRP={frp:.1f}MW (below threshold). Monitor only."
                if frp is not None
                else "VLM unavailable — rule-based triage applied. FRP unknown. Monitor only."
            ),
            triage_source="rule_based",
        )

    logger.warning(
        "rule_based_triage_applied",
        event_id=str(event.id),
        frp=frp,
        classification=result.classification,
        danger_level=result.danger_level,
        trace_id=get_trace_id(),
    )
    return result
