"""
ScanLogService — persists scan results locally and queues them for cloud upload.

Handles both fingerprint and alcohol scan types.
Upload to cloud is handled by the LogUploaderService in Phase 5.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from app.db.database import DatabaseManager
from app.db.models import ScanLog

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ScanLogService:
    """
    Writes scan results to the local scan_logs table.
    All records start with uploaded=0 (pending).
    The Phase 5 LogUploaderService will flush pending records to the cloud.
    """

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    # ── Write ─────────────────────────────────────────────────────

    async def log_fingerprint(self, employee_id: str, result: str) -> None:
        """Save a fingerprint scan result (match, no_match, no_templates, etc)."""
        await self._insert(
            employee_id=employee_id,
            scan_type="fingerprint",
            result=result,
            value=None,
        )
        logger.info(
            "ScanLogService: fingerprint logged — employee=%s result=%s",
            employee_id, result,
        )

    async def log_alcohol(
        self, employee_id: str, value: float, status: str
    ) -> None:
        """
        Save an alcohol test result (fallback).
        status: "OK" (pass) | "HIGH" (fail) — from AlcoholService
        """
        result = "pass" if status == "OK" else "fail"
        await self._insert(
            employee_id=employee_id,
            scan_type="alcohol",
            result=result,
            value=value,
        )
        logger.info(
            "ScanLogService: alcohol logged locally (fallback) — employee=%s value=%.3f result=%s",
            employee_id, value, result,
        )


    # ── Read (used by LogUploaderService in Phase 5) ──────────────

    async def get_pending(self, limit: int = 50) -> list[ScanLog]:
        """Return scan logs that have not yet been uploaded to the cloud."""
        async with self._db.connection() as conn:
            cursor = await conn.execute(
                "SELECT id, employee_id, scan_type, result, value, scanned_at, "
                "uploaded, upload_error "
                "FROM scan_logs WHERE uploaded = 0 ORDER BY id ASC LIMIT ?",
                (limit,),
            )
            rows = await cursor.fetchall()
            return [
                ScanLog(
                    id=row["id"],
                    employee_id=row["employee_id"],
                    scan_type=row["scan_type"],
                    result=row["result"],
                    value=row["value"],
                    scanned_at=row["scanned_at"],
                    uploaded=bool(row["uploaded"]),
                    upload_error=row["upload_error"],
                )
                for row in rows
            ]

    async def mark_uploaded(self, log_id: int) -> None:
        """Mark a scan log record as successfully uploaded."""
        async with self._db.connection() as conn:
            await conn.execute(
                "UPDATE scan_logs SET uploaded = 1, upload_error = NULL WHERE id = ?",
                (log_id,),
            )
            await conn.commit()

    async def mark_failed(self, log_id: int, error: str) -> None:
        """Record the upload error for a scan log entry."""
        async with self._db.connection() as conn:
            await conn.execute(
                "UPDATE scan_logs SET upload_error = ? WHERE id = ?",
                (error, log_id),
            )
            await conn.commit()

    async def delete_log(self, log_id: int) -> None:
        """Permanently remove a scan log record after successful upload."""
        async with self._db.connection() as conn:
            await conn.execute("DELETE FROM scan_logs WHERE id = ?", (log_id,))
            await conn.commit()
            logger.debug("ScanLogService: deleted log %d", log_id)

    async def delete_old_uploaded(self, older_than_days: int) -> int:
        """
        Remove uploaded logs older than N days to prevent SD card bloat.
        Returns the number of rows deleted.
        """
        async with self._db.connection() as conn:
            cursor = await conn.execute(
                """
                DELETE FROM scan_logs
                WHERE uploaded = 1
                  AND datetime(scanned_at) < datetime('now', ? || ' days')
                """,
                (f"-{older_than_days}",),
            )
            await conn.commit()
            deleted = cursor.rowcount
            if deleted:
                logger.info("ScanLogService: deleted %d old uploaded logs", deleted)
            return deleted

    # ── Private helpers ───────────────────────────────────────────

    async def _insert(
        self,
        employee_id: str,
        scan_type: str,
        result: str,
        value: Optional[float],
    ) -> None:
        async with self._db.connection() as conn:
            await conn.execute(
                """
                INSERT INTO scan_logs (employee_id, scan_type, result, value, scanned_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (employee_id, scan_type, result, value, _now_iso()),
            )
            await conn.commit()
