"""
Unit tests for app.core.logging.
"""
from __future__ import annotations

from app.core.logging import configure_logging


def test_configure_logging_environments() -> None:
    """Test configure_logging runs across environments without exception."""
    for env in ["development", "production", "staging"]:
        configure_logging(env)
