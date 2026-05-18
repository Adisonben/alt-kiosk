"""
Centralized structured logging for the Alcohol Testing System backend.

- Console handler: human-readable format.
- File handler: JSON lines, rotated daily.
- Usage: from utils.logger import get_logger; logger = get_logger(__name__)
"""

import logging
import logging.handlers
import json
import os
from datetime import datetime, timezone
from app.config import settings

# ── Configuration ─────────────────────────────────────────────
# Calculate absolute log directory relative to project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, settings.LOG_DIR)
LOG_FILE = os.path.join(LOG_DIR, settings.LOG_FILE)
LOG_LEVEL = settings.LOG_LEVEL
MAX_BYTES = 5 * 1024 * 1024  # 5 MB per file
BACKUP_COUNT = 5


class _JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


class _ConsoleFormatter(logging.Formatter):
    """Colored, human-readable console output."""

    COLORS = {
        "DEBUG": "\033[36m",     # cyan
        "INFO": "\033[32m",      # green
        "WARNING": "\033[33m",   # yellow
        "ERROR": "\033[31m",     # red
        "CRITICAL": "\033[41m",  # red background
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        msg = record.getMessage()
        base = f"{color}{ts} [{record.levelname:<7}]{self.RESET} {record.name}: {msg}"
        if record.exc_info and record.exc_info[1]:
            base += "\n" + self.formatException(record.exc_info)
        return base


_initialized = False


def setup_logging() -> None:
    """Initialize logging handlers. Safe to call multiple times."""
    global _initialized
    if _initialized:
        return
    _initialized = True

    os.makedirs(LOG_DIR, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.DEBUG))

    # Console handler: Clean terminal by defaulting to INFO, allow override via CONSOLE_LOG_LEVEL
    console = logging.StreamHandler()
    console.setFormatter(_ConsoleFormatter())
    console_level = os.environ.get("CONSOLE_LOG_LEVEL", "INFO").upper()
    console.setLevel(getattr(logging, console_level, logging.INFO))
    root.addHandler(console)

    # Rotating file handler (JSON): Keeps all debug logs for backend analysis
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setFormatter(_JSONFormatter())
    file_handler.setLevel(logging.DEBUG)
    root.addHandler(file_handler)

    # Silence extremely noisy third-party loggers on the terminal
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger. Ensures logging is initialized on first call.
    """
    setup_logging()
    return logging.getLogger(name)
