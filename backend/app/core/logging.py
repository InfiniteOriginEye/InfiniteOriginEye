"""
Structured logging setup for SC&C backend.
Uses structlog for JSON logs in production, console in dev.
"""

import logging
import sys

import structlog


def setup_logging() -> None:
    """Configure structured logging for the application."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_loglevel,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer()
            if logging.getLogger().level == logging.DEBUG
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )
