import logging
import sys

import structlog

from excelpilot.config import settings


def setup_logging() -> None:
    # Set up basic logging level from settings
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=log_level)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    if settings.logfire_token:
        try:
            import logfire

            logfire.configure(token=settings.logfire_token)
            logfire.instrument_pydantic_ai()
        except Exception:
            pass


logger = structlog.get_logger("excelpilot")
