"""
Fire spread prediction service — builds feature vector, runs XGBoost, saves Prediction.
FR-08: Feature engineering. FR-09: 4 spread targets. FR-10: Store predictions.
"""
from __future__ import annotations

import structlog
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PredictionError
from app.models.fire_event import FireEvent
from app.models.prediction import Prediction
from app.models.triage_report import TriageReport
from app.schemas.common import get_trace_id
from app.services.alerts.alert_service import AlertService
from app.services.prediction.feature_builder import build_feature_vector
from app.services.prediction.model_loader import load_model

logger = structlog.get_logger()

MODEL_VERSION = "1.0.0"
# Target column order — must match training script output order
TARGET_COLUMNS = [
    "spread_direction_deg",
    "radius_6h_km",
    "radius_12h_km",
    "radius_24h_km",
]


async def run_prediction(
    event: FireEvent,
    triage: TriageReport,
    db: AsyncSession,
) -> Prediction:
    """
    Run XGBoost fire spread prediction for a triaged event.

    Steps:
      1. Build feature vector (weather + terrain + triage data)
      2. Load model from disk (cached)
      3. Run inference → 4 spread targets
      4. Save Prediction row to DB
      5. Update fire_events.status = 'PREDICTED'

    Returns:
        Saved Prediction ORM object.
    Raises:
        PredictionError: if feature build or inference fails.
    """
    # Step 1: Feature vector
    features_df = await build_feature_vector(event, triage)

    # Step 2: Load model (may raise ModelNotFoundError)
    model = load_model()

    # Step 3: Inference
    try:
        raw_preds = model.predict(features_df)
    except Exception as e:
        logger.error(
            "xgboost_inference_failed",
            event_id=str(event.id),
            error=str(e),
            trace_id=get_trace_id(),
        )
        raise PredictionError(f"XGBoost inference failed: {e}") from e

    # raw_preds shape: (1, 4) for multi-output or (1,) for single output
    preds = raw_preds[0] if raw_preds.ndim > 1 else raw_preds
    spread_dir = float(preds[0]) % 360  # normalize to 0-360
    radius_6h = max(0.0, float(preds[1]))
    radius_12h = max(0.0, float(preds[2]))
    radius_24h = max(0.0, float(preds[3]))

    # Step 4: Save to DB
    prediction = Prediction(
        event_id=event.id,
        spread_direction_deg=spread_dir,
        radius_6h_km=radius_6h,
        radius_12h_km=radius_12h,
        radius_24h_km=radius_24h,
        wind_speed=float(features_df["wind_speed"].iloc[0]),
        wind_direction=float(features_df["wind_direction"].iloc[0]),
        humidity=float(features_df["humidity"].iloc[0]),
        model_version=MODEL_VERSION,
    )
    db.add(prediction)
    await db.flush()

    # Step 5: Update event status
    await db.execute(
        update(FireEvent)
        .where(FireEvent.id == event.id)
        .values(status="PREDICTED")
    )

    logger.info(
        "prediction_complete",
        event_id=str(event.id),
        spread_direction_deg=spread_dir,
        radius_6h_km=radius_6h,
        model_version=MODEL_VERSION,
        trace_id=get_trace_id(),
    )

    # Step 6: Send alert (fire spread prediction complete → notify)
    try:
        alert_svc = AlertService(db)
        await alert_svc.send_alert(event.id)
    except Exception as alert_exc:  # noqa: BLE001
        logger.warning(
            "prediction_alert_failed",
            event_id=str(event.id),
            error=str(alert_exc),
            trace_id=get_trace_id(),
        )

    return prediction
