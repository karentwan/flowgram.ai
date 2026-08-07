"""Structured logging setup (grill decision: observability route 2).

Uses structlog with JSON output in production and pretty console output in
development. Every log line carries structured fields (task_id, node_id,
event, duration_ms, status) so downstream log collectors (ELK/Loki) can index
them without grep.
"""

from __future__ import annotations

import logging
import sys

import structlog

from app.core.config import get_settings


def setup_logging() -> None:
    """Configure structlog + stdlib logging once at startup."""
    settings = get_settings()

    # Stdlib root: route everything to stdout.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if settings.is_dev else logging.INFO,
    )

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.is_dev:
        # Pretty console rendering for local dev.
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer(colors=True)
    else:
        # JSON for production log collectors.
        renderer = structlog.processors.JSONRenderer()

    # Route structlog records through the stdlib logging tree so that
    # `add_logger_name` / `PositionalArgumentsFormatter` (stdlib processors)
    # find the attributes they expect on the underlying logger.
    structlog.configure(
        processors=[
            *shared_processors,
            # Hand off the rendered event dict to stdlib logging.
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if settings.is_dev else logging.INFO
        ),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Make stdlib handlers render via structlog too, so every log line
    # (ours and third-party libs') shares one JSON/console format.
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structured logger. Use as: ``log = get_logger(__name__)``."""
    return structlog.get_logger(name)  # type: ignore[no-any-return]
