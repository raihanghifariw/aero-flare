"""
Triage service orchestrator — coordinates VLM triage + rule-based fallback.
FR-04: VLM classification. FR-05: 4 labels. FR-06: structured fields. FR-07: JSON log.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import httpx
import structlog
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import TriageError
from app.models.fire_event import FireEvent
from app.models.triage_report import TriageReport
from app.schemas.common import get_trace_id
from app.schemas.triage_report import TriageOutput
from app.services.alerts.alert_service import AlertService
from app.services.triage.prompt_builder import build_triage_prompt
from app.services.triage.response_parser import parse_vlm_response
from app.services.triage.rule_based_triage import rule_based_triage
from app.services.triage.vlm_client import call_vlm, check_ollama_reachable

logger = structlog.get_logger()

# Canonical persisted values for TriageReport.triage_source.
# Must match stats.py (_source_count), the frontend TriageSource type,
# and the DB column default ("VLM").
TRIAGE_SOURCE_VLM = "VLM"
TRIAGE_SOURCE_RULE_BASED = "RULE_BASED_FALLBACK"


async def _download_tile_for_vlm(tile_url: str | None) -> str | None:
    """
    Download the tile from R2 presigned URL or GIBS URL to a local temp file.
    Returns path to temp file, or None if no tile available.
    """
    if not tile_url:
        return None
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(tile_url)
            resp.raise_for_status()
        suffix = ".jpg" if "jpg" in tile_url.lower() else ".png"
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        tmp.write(resp.content)
        tmp.close()
        return tmp.name
    except Exception as e:
        logger.warning("tile_download_failed", tile_url=tile_url, error=str(e))
        return None


async def run_triage(
    event: FireEvent,
    db: AsyncSession,
) -> TriageReport:
    """
    Run the full triage pipeline for a single fire event.

    Flow:
      1. Check Ollama reachability
      2. Download satellite tile for VLM input
      3. Build prompt
      4. Call primary VLM (qwen2-vl:7b) with tenacity retry
      5. If VLM fails → try fallback model (llava:13b)
      6. If both fail → rule-based fallback (FRP threshold)
      7. Save TriageReport to DB
      8. Update fire_events.status = 'TRIAGED'

    Returns the saved TriageReport ORM object.
    """
    settings = get_settings()
    triage_output: TriageOutput | None = None
    tmp_tile_path: str | None = None

    # --- Step 1: Check Ollama ---
    ollama_up = await check_ollama_reachable(settings.OLLAMA_BASE_URL)

    # --- Step 2: Download tile ---
    if ollama_up and event.tile_url:
        # Generate presigned URL if tile_url is an R2 key (not a full URL)
        if event.tile_url.startswith("tiles/"):
            from app.services.ingestion.gibs_tile_fetcher import get_r2_presigned_url
            presigned = get_r2_presigned_url(event.tile_url)
            tmp_tile_path = await _download_tile_for_vlm(presigned)
        else:
            tmp_tile_path = await _download_tile_for_vlm(event.tile_url)

    # --- Step 3: Build prompt ---
    prompt = build_triage_prompt(event)

    # --- Step 4 & 5: VLM triage with primary then fallback model ---
    if ollama_up and tmp_tile_path:
        for model in [settings.VLM_MODEL, settings.VLM_FALLBACK_MODEL]:
            try:
                raw = await call_vlm(
                    image_path=tmp_tile_path,
                    prompt=prompt,
                    model=model,
                    base_url=settings.OLLAMA_BASE_URL,
                )
                # Log raw output to structlog only (never stored in DB — ADR-014)
                logger.info(
                    "vlm_raw_output",
                    model=model,
                    event_id=str(event.id),
                    raw_response=raw[:500],  # truncate for log safety
                    trace_id=get_trace_id(),
                )
                triage_output = parse_vlm_response(raw)
                triage_output = triage_output.model_copy(update={"triage_source": "vlm"})
                logger.info(
                    "vlm_triage_success",
                    model=model,
                    event_id=str(event.id),
                    classification=triage_output.classification,
                    trace_id=get_trace_id(),
                )
                break  # success — stop trying models
            except Exception as e:
                logger.warning(
                    "vlm_triage_attempt_failed",
                    model=model,
                    event_id=str(event.id),
                    error=str(e),
                    trace_id=get_trace_id(),
                )

    # --- Step 6: Rule-based fallback ---
    if triage_output is None:
        triage_output = rule_based_triage(event)

    # Cleanup temp file
    if tmp_tile_path:
        Path(tmp_tile_path).unlink(missing_ok=True)

    # --- Step 7: Save TriageReport to DB ---
    report = TriageReport(
        event_id=event.id,
        classification=triage_output.classification,
        confidence=triage_output.confidence,
        fire_area_ha=triage_output.fire_area_ha,
        smoke_direction=triage_output.smoke_direction,
        danger_level=triage_output.danger_level,
        summary=triage_output.summary,
        recommended_action=triage_output.recommended_action,
        triage_source=(
            TRIAGE_SOURCE_RULE_BASED
            if triage_output.triage_source == "rule_based"
            else TRIAGE_SOURCE_VLM
        ),
    )
    db.add(report)
    await db.flush()

    # --- Step 8: Update event status ---
    await db.execute(
        update(FireEvent)
        .where(FireEvent.id == event.id)
        .values(status="TRIAGED")
    )

    logger.info(
        "triage_complete",
        event_id=str(event.id),
        classification=report.classification,
        triage_source=report.triage_source,
        danger_level=report.danger_level,
        trace_id=get_trace_id(),
    )

    # --- Step 9: Send alert for rule-based path (VLM path triggers after prediction) ---
    if report.triage_source == TRIAGE_SOURCE_RULE_BASED:
        try:
            alert_svc = AlertService(db)
            await alert_svc.send_alert(event.id)
        except Exception as alert_exc:  # noqa: BLE001
            logger.warning(
                "triage_alert_failed",
                event_id=str(event.id),
                error=str(alert_exc),
                trace_id=get_trace_id(),
            )

    return report
