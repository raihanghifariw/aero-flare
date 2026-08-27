"""
XGBoost model loader with in-memory singleton cache.
Raises ModelNotFoundError if the .ubj artifact is missing.
"""
from __future__ import annotations

import structlog
from xgboost import XGBRegressor

from app.core.exceptions import ModelNotFoundError

logger = structlog.get_logger()

# Module-level singleton — loaded once, reused across requests
_model_cache: dict[str, XGBRegressor] = {}


def load_model(model_path: str | None = None) -> XGBRegressor:
    """
    Load the XGBoost multi-output spread prediction model from disk.
    Cached in memory after first load — no re-read on subsequent calls.

    Args:
        model_path: Path to the .ubj model file. Defaults to XGBOOST_MODEL_PATH env var.

    Returns:
        Loaded XGBRegressor.

    Raises:
        ModelNotFoundError: if the file does not exist.
    """
    from app.core.config import get_settings

    if model_path is None:
        model_path = get_settings().XGBOOST_MODEL_PATH

    if model_path in _model_cache:
        return _model_cache[model_path]

    from pathlib import Path

    resolved = Path(model_path)
    if not resolved.is_absolute() and not resolved.exists():
        # Relative paths (e.g. "ml/models/....ubj") are defined relative to the
        # repo root — resolve against it so loading works from any CWD
        # (backend/, repo root, Docker WORKDIR, etc.).
        repo_root = Path(__file__).resolve().parents[4]
        candidate = repo_root / model_path
        if candidate.exists():
            resolved = candidate

    if not resolved.exists():
        raise ModelNotFoundError(
            f"XGBoost model not found at '{model_path}'. "
            f"Run: python ml/train.py --version 1.0.0"
        )

    model = XGBRegressor()
    model.load_model(str(resolved))
    _model_cache[model_path] = model

    logger.info("xgboost_model_loaded", path=str(resolved))
    return model


def clear_model_cache() -> None:
    """Clear the in-memory model cache (useful in tests)."""
    _model_cache.clear()
