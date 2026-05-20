"""
AnonymousTestService — persists anonymous test results locally and queues them for cloud upload.
Does not relate to employees.
"""

import logging
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional

from app.db.database import DatabaseManager

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AnonymousTest:
    id: Optional[int]
    org_id: str
    value: Optional[float]
    result: str
    scanned_at: str
    image: Optional[str]
    uploaded: bool
    upload_error: Optional[str]
    retry_count: int = 0


class AnonymousTestService:
    """
    Writes anonymous scan results to the local anonymous_tests table.
    All records start with uploaded=0 (pending).
    """

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    # ── Write ─────────────────────────────────────────────────────

    async def log_anonymous_test(
        self, org_id: str, value: float, status: str, image: Optional[str] = None
    ) -> None:
        """
        Save an anonymous alcohol test result (fallback).
        status: "OK" (pass) | "HIGH" (fail) — from AlcoholService
        """
        result = "pass" if status == "OK" else "fail"
        async with self._db.connection() as conn:
            await conn.execute(
                """
                INSERT INTO anonymous_tests (org_id, value, result, scanned_at, image)
                VALUES (?, ?, ?, ?, ?)
                """,
                (org_id, value, result, _now_iso(), image),
            )
            await conn.commit()

        logger.info(
            "AnonymousTestService: anonymous alcohol logged locally (fallback) — value=%.3f result=%s",
            value, result,
        )

    # ── Read (used by LogUploaderService) ─────────────────────────

    async def get_pending_anonymous(self, limit: int = 20) -> list[AnonymousTest]:
        """Return anonymous tests that have not yet been uploaded and haven't exceeded retry limit."""
        async with self._db.connection() as conn:
            cursor = await conn.execute(
                "SELECT id, org_id, value, result, scanned_at, image, uploaded, upload_error, retry_count "
                "FROM anonymous_tests WHERE uploaded = 0 AND retry_count < 5 ORDER BY id ASC LIMIT ?",
                (limit,),
            )
            rows = await cursor.fetchall()
            return [
                AnonymousTest(
                    id=row["id"],
                    org_id=row["org_id"],
                    value=row["value"],
                    result=row["result"],
                    scanned_at=row["scanned_at"],
                    image=row["image"],
                    uploaded=bool(row["uploaded"]),
                    upload_error=row["upload_error"],
                    retry_count=row["retry_count"],
                )
                for row in rows
            ]

    async def mark_uploaded(self, log_id: int) -> None:
        """Mark an anonymous test record as successfully uploaded."""
        async with self._db.connection() as conn:
            await conn.execute(
                "UPDATE anonymous_tests SET uploaded = 1, upload_error = NULL WHERE id = ?",
                (log_id,),
            )
            await conn.commit()

    async def mark_failed(self, log_id: int, error: str) -> None:
        """Record the upload error and increment the retry count for an anonymous test entry."""
        async with self._db.connection() as conn:
            await conn.execute(
                "UPDATE anonymous_tests SET upload_error = ?, retry_count = retry_count + 1 WHERE id = ?",
                (error, log_id),
            )
            await conn.commit()

    async def delete_log(self, log_id: int) -> None:
        """Permanently remove an anonymous test record after successful upload."""
        async with self._db.connection() as conn:
            await conn.execute("DELETE FROM anonymous_tests WHERE id = ?", (log_id,))
            await conn.commit()
            logger.debug("AnonymousTestService: deleted anonymous log %d", log_id)
