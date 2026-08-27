"""
Common Pydantic schemas shared across all endpoints.
ErrorResponse includes trace_id for OpenTelemetry log correlation.
"""
from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated list response."""
    model_config = ConfigDict(frozen=True)

    data: list[T]
    total: int
    page: int
    page_size: int
    has_next: bool


class ErrorResponse(BaseModel):
    """Structured error response — always includes trace_id for log correlation."""
    model_config = ConfigDict(frozen=True)

    error: str           # Machine-readable error code, e.g. "EVENT_NOT_FOUND"
    message: str         # Human-readable description
    trace_id: str | None = None  # OpenTelemetry trace_id
    timestamp: datetime = datetime.utcnow()


def get_trace_id() -> str | None:
    """Extract current OpenTelemetry trace_id as hex string."""
    try:
        from opentelemetry import trace
        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx and ctx.trace_id:
            return format(ctx.trace_id, "032x")
    except Exception:
        pass
    return None
