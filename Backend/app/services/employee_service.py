"""
EmployeeService — local SQLite CRUD for employees and fingerprints.

This service is the only layer that reads/writes employee data.
All other services (SyncService, FingerprintService) go through here.

No business logic lives here — only data access.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from app.db.database import DatabaseManager
from app.db.models import Employee, Fingerprint

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EmployeeService:
    """
    Provides read and write access to local employee and fingerprint data.
    All methods are async and open their own short-lived DB connections.
    """

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    # ── Read ─────────────────────────────────────────────────────

    async def get_by_emp_id(self, emp_id: str) -> Optional[Employee]:
        """
        Fetch an employee + their fingerprints by display emp_id.
        Returns None if not found.
        """
        async with self._db.connection() as conn:
            cursor = await conn.execute(
                "SELECT id, emp_id, full_name, org_id, updated_at, synced_at "
                "FROM employees WHERE emp_id = ?",
                (emp_id,),
            )
            row = await cursor.fetchone()
            if not row:
                logger.debug("EmployeeService: emp_id '%s' not found in local DB", emp_id)
                return None

            employee = Employee(
                id=row["id"],
                emp_id=row["emp_id"],
                full_name=row["full_name"],
                org_id=row["org_id"],
                updated_at=row["updated_at"],
                synced_at=row["synced_at"],
            )
            employee.fingerprints = await self._get_fingerprints(conn, employee.id)
            return employee

    async def get_by_id(self, employee_id: str) -> Optional[Employee]:
        """Fetch an employee by their cloud UUID."""
        async with self._db.connection() as conn:
            cursor = await conn.execute(
                "SELECT id, emp_id, full_name, org_id, updated_at, synced_at "
                "FROM employees WHERE id = ?",
                (employee_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return None

            employee = Employee(
                id=row["id"],
                emp_id=row["emp_id"],
                full_name=row["full_name"],
                org_id=row["org_id"],
                updated_at=row["updated_at"],
                synced_at=row["synced_at"],
            )
            employee.fingerprints = await self._get_fingerprints(conn, employee.id)
            return employee

    async def count(self) -> int:
        """Return total number of employees stored locally."""
        async with self._db.connection() as conn:
            cursor = await conn.execute("SELECT COUNT(*) FROM employees")
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_all_fingerprints(self) -> list[Fingerprint]:
        """Fetch all fingerprint templates enrolled in the system."""
        async with self._db.connection() as conn:
            cursor = await conn.execute(
                "SELECT id, employee_id, finger_index, fingerprint_code, updated_at, synced_at "
                "FROM fingerprints"
            )
            rows = await cursor.fetchall()
            return [
                Fingerprint(
                    id=row["id"],
                    employee_id=row["employee_id"],
                    finger_index=row["finger_index"],
                    fingerprint_code=row["fingerprint_code"],
                    updated_at=row["updated_at"],
                    synced_at=row["synced_at"],
                )
                for row in rows
            ]

    # ── Write ────────────────────────────────────────────────────

    async def upsert(self, employee_data: dict) -> None:
        """
        Insert or update a single employee and their fingerprints.

        Expected employee_data shape (from cloud API response):
        {
            "id": "uuid",
            "emp_id": "ORG-0001",
            "full_name": "สมชาย รักดี",
            "org_id": "uuid",
            "updated_at": "2026-05-01T10:00:00Z",
            "fingerprints": [
                {
                    "id": "uuid",
                    "finger_index": 0,
                    "fingerprint_code": "base64string",
                    "updated_at": "2026-05-01T10:00:00Z"
                }
            ]
        }
        """
        now = _now_iso()

        async with self._db.connection() as conn:
            await conn.execute(
                """
                INSERT INTO employees (id, emp_id, full_name, org_id, updated_at, synced_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    emp_id     = excluded.emp_id,
                    full_name  = excluded.full_name,
                    org_id     = excluded.org_id,
                    updated_at = excluded.updated_at,
                    synced_at  = excluded.synced_at
                """,
                (
                    employee_data["id"],
                    employee_data["emp_id"],
                    employee_data["full_name"],
                    employee_data["org_id"],
                    employee_data["updated_at"],
                    now,
                ),
            )

            # Replace fingerprints for this employee
            # Unconditionally delete first to ensure any deleted fingerprints on the cloud are wiped locally
            await conn.execute(
                "DELETE FROM fingerprints WHERE employee_id = ?",
                (employee_data["id"],),
            )

            fingerprints = employee_data.get("fingerprints", [])
            if fingerprints:
                await conn.executemany(
                    """
                    INSERT INTO fingerprints
                        (id, employee_id, finger_index, fingerprint_code, updated_at, synced_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            fp["id"],
                            employee_data["id"],
                            fp.get("finger_index"),
                            fp["fingerprint_code"],
                            fp["updated_at"],
                            now,
                        )
                        for fp in fingerprints
                    ],
                )

            await conn.commit()

    async def upsert_many(self, employees: list[dict]) -> int:
        """
        Bulk upsert a list of employees. Returns the count inserted/updated.
        Used by SyncService for efficient batch writes.
        """
        for emp in employees:
            await self.upsert(emp)
        logger.info("EmployeeService: upserted %d employees", len(employees))
        return len(employees)

    async def delete(self, employee_id: str) -> None:
        """Remove an employee and their fingerprints (cascade)."""
        async with self._db.connection() as conn:
            await conn.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
            await conn.commit()

    async def save_fingerprint(
        self, employee_id: str, fingerprint_code: str, finger_index: int = 0
    ) -> str:
        """
        Save fingerprint locally in the database.
        Returns the generated fingerprint UUID.
        """
        import uuid
        now = _now_iso()
        fp_id = str(uuid.uuid4())

        async with self._db.connection() as conn:
            # Update the employee's updated_at timestamp
            await conn.execute(
                "UPDATE employees SET updated_at = ? WHERE id = ?",
                (now, employee_id),
            )

            # Remove any existing fingerprints for this employee and index to prevent duplicates
            await conn.execute(
                "DELETE FROM fingerprints WHERE employee_id = ? AND finger_index = ?",
                (employee_id, finger_index),
            )

            # Insert the new fingerprint template
            await conn.execute(
                """
                INSERT INTO fingerprints (id, employee_id, finger_index, fingerprint_code, updated_at, synced_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    fp_id,
                    employee_id,
                    finger_index,
                    fingerprint_code,
                    now,
                    now,
                ),
            )
            await conn.commit()

        logger.info(
            "EmployeeService: registered fingerprint locally (id: %s) for employee %s",
            fp_id,
            employee_id,
        )
        return fp_id

    # ── Private helpers ──────────────────────────────────────────

    @staticmethod
    async def _get_fingerprints(conn, employee_id: str) -> list[Fingerprint]:
        cursor = await conn.execute(
            "SELECT id, employee_id, finger_index, fingerprint_code, updated_at, synced_at "
            "FROM fingerprints WHERE employee_id = ?",
            (employee_id,),
        )
        rows = await cursor.fetchall()
        return [
            Fingerprint(
                id=row["id"],
                employee_id=row["employee_id"],
                finger_index=row["finger_index"],
                fingerprint_code=row["fingerprint_code"],
                updated_at=row["updated_at"],
                synced_at=row["synced_at"],
            )
            for row in rows
        ]
