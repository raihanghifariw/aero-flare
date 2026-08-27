"""Pydantic schemas for fire spread Prediction."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PredictionCreate(BaseModel):
    """Input schema for creating a prediction (internal use by prediction service)."""
    # `model_version` is a legitimate domain field; disable pydantic's reserved
    # "model_" namespace check so it does not emit a UserWarning on import.
    model_config = ConfigDict(protected_namespaces=())

    event_id: uuid.UUID
    spread_direction_deg: float | None = None
    radius_6h_km: float | None = None
    radius_12h_km: float | None = None
    radius_24h_km: float | None = None
    wind_speed: float | None = None
    wind_direction: float | None = None
    humidity: float | None = None
    model_version: str | None = None


class PredictionSchema(BaseModel):
    """Output schema for a prediction returned by the API."""
    model_config = ConfigDict(
        frozen=True, from_attributes=True, protected_namespaces=()
    )

    id: uuid.UUID
    event_id: uuid.UUID
    spread_direction_deg: float | None
    radius_6h_km: float | None
    radius_12h_km: float | None
    radius_24h_km: float | None
    wind_speed: float | None
    wind_direction: float | None
    humidity: float | None
    model_version: str | None
    predicted_at: datetime
