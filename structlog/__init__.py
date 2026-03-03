from __future__ import annotations

"""
Lightweight in-repo shim for structlog-style logging.

This module provides a minimal subset of the structlog API used by the agents
codebase, while avoiding imports of external packages that transitively depend
on a broken `platform` module in the current environment.

It is intentionally small: enough for `structlog.get_logger().info(...)` and
friends to work with structured key/value events, backed by the standard
library `logging` module.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict


_ROOT_LOGGER_NAME = "agents"


def _configure_root_logger() -> logging.Logger:
    """
    Configure and return the shared root logger for the agents.

    The logger emits plain JSON lines to standard output, compatible with the
    expectations in the architecture docs without requiring the real structlog
    package or any rich/attrs extras.
    """
    logger = logging.getLogger(_ROOT_LOGGER_NAME)
    if logger.handlers:
        return logger

    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


_LOGGER = _configure_root_logger()


@dataclass
class BoundLogger:
    """
    Minimal stand-in for structlog's bound logger.

    Events are encoded as a single JSON object per line, where the `event`
    field contains the event name and all additional keyword arguments are
    attached as top-level keys.
    """

    _logger: logging.Logger = field(default=_LOGGER)
    _context: Dict[str, Any] = field(default_factory=dict)

    def bind(self, **new_context: Any) -> "BoundLogger":
        """
        Return a new BoundLogger with additional bound context fields.
        """
        merged = {**self._context, **new_context}
        return BoundLogger(_logger=self._logger, _context=merged)

    def _log(self, level: int, event: str, **kwargs: Any) -> None:
        """
        Emit a structured log line at the given level.
        """
        record: Dict[str, Any] = {"event": event, **self._context, **kwargs}
        try:
            message = json.dumps(record, default=str)
        except TypeError:
            # Fallback: best-effort stringification of non-serializable values.
            safe_record = {
                key: (str(value) if not isinstance(value, (str, int, float, bool, type(None))) else value)
                for key, value in record.items()
            }
            message = json.dumps(safe_record, default=str)
        self._logger.log(level, message)

    def info(self, event: str, **kwargs: Any) -> None:
        """
        Log an informational event.
        """
        self._log(logging.INFO, event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        """
        Log a warning event.
        """
        self._log(logging.WARNING, event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        """
        Log an error event.
        """
        self._log(logging.ERROR, event, **kwargs)


def get_logger() -> BoundLogger:
    """
    Return a BoundLogger instance for use by application code.
    """
    return BoundLogger()

