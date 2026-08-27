"""
Typed application exceptions.
All service functions raise one of these typed exceptions rather than bare Exception.
"""
from __future__ import annotations


class AeroFlareBaseError(Exception):
    """Base class for all Aero-Flare application errors."""


class IngestionError(AeroFlareBaseError):
    """Raised when FIRMS CSV parsing or API fetch fails."""


class TriageError(AeroFlareBaseError):
    """Raised when VLM triage fails after all retries and rule-based fallback."""


class PredictionError(AeroFlareBaseError):
    """Raised when XGBoost inference fails."""


class AlertError(AeroFlareBaseError):
    """Raised when alert delivery (Telegram / webhook) fails."""


class ModelNotFoundError(AeroFlareBaseError):
    """Raised when the XGBoost model artifact file is not found at configured path."""


class TileNotFoundError(AeroFlareBaseError):
    """Raised when a GIBS WMTS tile is unavailable for the given coordinates / date."""


class ValidationError(AeroFlareBaseError):
    """Raised when incoming data fails domain-level validation (beyond Pydantic)."""
