"""
SQLite migration runner — idempotent schema creation.

Call init_db() once on app startup. All CREATE TABLE statements use
IF NOT EXISTS so they are safe to run on an existing database.

Schema version is tracked in the sync_metadata table.
"""

import logging
import aiosqlite

from app.config import settings

logger = logging.getLogger(__name__)

# Bump this when the schema changes to trigger future migrations.
SCHEMA_VERSION = "1"

# ── DDL ────────────────────────────────────────────────────────

_DDL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS employees (
    id          TEXT PRIMARY KEY,
    emp_id      TEXT NOT NULL,
    full_name   TEXT NOT NULL,
    org_id      TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    synced_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fingerprints (
    id               TEXT PRIMARY KEY,
    employee_id      TEXT NOT NULL,
    finger_index     INTEGER,
    fingerprint_code TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    synced_at        TEXT NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sync_metadata (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scan_logs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id  TEXT NOT NULL,
    scan_type    TEXT NOT NULL,
    result       TEXT NOT NULL,
    value        REAL,
    scanned_at   TEXT NOT NULL,
    uploaded     INTEGER NOT NULL DEFAULT 0,
    upload_error TEXT,
    retry_count  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS anonymous_tests (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id       TEXT NOT NULL,
    value        REAL,
    result       TEXT NOT NULL,
    scanned_at   TEXT NOT NULL,
    image        TEXT,
    uploaded     INTEGER NOT NULL DEFAULT 0,
    upload_error TEXT,
    retry_count  INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_employees_emp_id ON employees(emp_id);
CREATE INDEX IF NOT EXISTS idx_employees_org_id ON employees(org_id);
CREATE INDEX IF NOT EXISTS idx_fingerprints_employee_id ON fingerprints(employee_id);
CREATE INDEX IF NOT EXISTS idx_scan_logs_uploaded ON scan_logs(uploaded);
CREATE INDEX IF NOT EXISTS idx_anonymous_tests_uploaded ON anonymous_tests(uploaded);
"""


async def init_db() -> None:
    """
    Create all tables and indexes if they do not exist.
    Safe to call on every startup.
    """
    logger.info("DB: initializing schema at %s", settings.DB_PATH)

    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.executescript(_DDL)
        await db.commit()

        # Safely add retry_count column to scan_logs if upgrading an existing DB
        try:
            await db.execute("ALTER TABLE scan_logs ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0")
            await db.commit()
        except aiosqlite.OperationalError:
            # Column already exists, ignore
            pass

    logger.info("DB: schema ready (version %s)", SCHEMA_VERSION)
