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

# FRP threshold above which we upgrade to PROBABLE_FIRE danger level 3
FRP_HIGH_THRESHOLD = 50.0


def rule_based_triage(event: FireEvent) -> TriageOutput:
    """
    Deterministic triage when VLM is unavailable.

    Rules:
      FRP > 50 MW  → PROBABLE_FIRE, danger_level=3, DISPATCH_LOCAL
      FRP ≤ 50 MW  → PROBABLE_FIRE, danger_level=2, MONITOR
      FRP unknown  → PROBABLE_FIRE, danger_level=2, MONITOR

    Always sets triage_source='rule_based'.
    """
    frp = event.frp

    if frp is not None and frp > FRP_HIGH_THRESHOLD:
        result = TriageOutput(
            classification="PROBABLE_FIRE",
            confidence=0.5,
            danger_level=3,
            fire_area_ha=None,
            smoke_direction=None,
            recommended_action="DISPATCH_LOCAL",
            summary=(
                f"VLM unavailable — rule-based triage applied. "
                f"FRP={frp:.1f}MW exceeds {FRP_HIGH_THRESHOLD}MW threshold. "
                f"Dispatch local team for verification."
            ),
            triage_source="rule_based",
        )
    else:
        result = TriageOutput(
            classification="PROBABLE_FIRE",
            confidence=0.3,
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
