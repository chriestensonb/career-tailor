import structlog
from opentelemetry import trace
from opentelemetry.trace import get_current_span


def _otel_context(logger: object, method: str, event_dict: dict) -> dict:
    ctx = get_current_span().get_span_context()
    if ctx.is_valid:
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
    return event_dict


def configure_logging() -> None:
    """Call once at app startup to enable structured JSON logs with trace context."""
    structlog.configure(
        processors=[
            _otel_context,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
    )


def get_tracer(name: str) -> trace.Tracer:
    return trace.get_tracer(name)


def get_logger(name: str) -> structlog.BoundLogger:
    return structlog.get_logger(name)
