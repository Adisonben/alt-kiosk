"""
SyncService — background worker that syncs employee data from Cloud to SQLite.

Responsibilities:
- Full sync on startup: fetch ALL employees for the device's org_id
- Incremental sync every SYNC_INTERVAL_SECONDS: fetch only updated records
- Force sync: triggered via FORCE_SYNC command from the WebSocket
- Retry on failure with SYNC_RETRY_DELAY_SECONDS backoff
- Track is_online state and publish sync_status events to EventBus
- Store last sync timestamp in sync_metadata table
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from app.config import settings
from app.db.database import DatabaseManager
from app.services.employee_service import EmployeeService
from app.utils.http_client import CloudHttpClient

logger = logging.getLogger(__name__)

# sync_metadata keys
_KEY_LAST_FULL_SYNC = "employees_last_full_sync"
_KEY_LAST_INCREMENTAL_SYNC = "employees_last_sync"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SyncService:
    """
    Manages Cloud ↔ Local DB synchronization for employee data.

    Lifecycle:
        start() → runs full sync, starts periodic worker, listens for commands
        stop()  → cancels tasks, closes HTTP client
    """

    def __init__(
        self,
        db: DatabaseManager,
        employee_svc: EmployeeService,
        http_client: CloudHttpClient,
        event_bus,
        command_bus,
    ) -> None:
        self._db = db
        self._employee_svc = employee_svc
        self._event_bus = event_bus
        self._command_bus = command_bus
        self._http = http_client

        self._is_online: bool = False
        self._last_sync_time: Optional[str] = None

        self._cmd_queue: Optional[asyncio.Queue] = None
        self._periodic_task: Optional[asyncio.Task] = None
        self._cmd_listener_task: Optional[asyncio.Task] = None

    # ── Lifecycle ─────────────────────────────────────────────────

    async def start(self) -> None:
        """
        Start the sync service:
        1. Subscribe to FORCE_SYNC command
        2. Run initial full sync (non-blocking)
        3. Launch periodic incremental sync worker
        """
        self._cmd_queue = await self._command_bus.subscribe(
            filter_types={"FORCE_SYNC"}
        )
        self._cmd_listener_task = asyncio.create_task(
            self._listen_commands(), name="sync-cmd-listener"
        )

        # Full sync runs in background so it does not block startup
        asyncio.create_task(self._initial_sync(), name="sync-initial")

        self._periodic_task = asyncio.create_task(
            self._periodic_worker(), name="sync-periodic"
        )
        logger.info("SyncService: started")

    async def stop(self) -> None:
        """Cancel background tasks and close HTTP client."""
        for task in [self._periodic_task, self._cmd_listener_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        if self._cmd_queue:
            await self._command_bus.unsubscribe(self._cmd_queue)

        logger.info("SyncService: stopped")

    # ── Command listener ──────────────────────────────────────────

    async def _listen_commands(self) -> None:
        """Handle FORCE_SYNC commands dispatched from the WebSocket."""
        try:
            while True:
                cmd = await self._cmd_queue.get()
                if cmd.get("command") == "FORCE_SYNC":
                    logger.info("SyncService: FORCE_SYNC command received")
                    # Run in a separate task so the listener stays responsive
                    asyncio.create_task(self._full_sync(), name="sync-forced")
        except asyncio.CancelledError:
            pass

    # ── Sync workers ──────────────────────────────────────────────

    async def _initial_sync(self) -> None:
        """Run once after startup. Falls back gracefully if offline."""
        logger.info("SyncService: running initial full sync...")
        try:
            await self._full_sync()
        except Exception as exc:
            logger.warning("SyncService: initial sync failed — %s. Will retry on next cycle.", exc)

    async def _periodic_worker(self) -> None:
        """Loop: sleep → incremental sync → repeat."""
        try:
            while True:
                await asyncio.sleep(settings.SYNC_INTERVAL_SECONDS)
                try:
                    await self._incremental_sync()
                except Exception as exc:
                    logger.warning(
                        "SyncService: incremental sync failed — %s. "
                        "Retrying in %ds.",
                        exc, settings.SYNC_RETRY_DELAY_SECONDS,
                    )
                    self._is_online = False
                    await self._publish_sync_status()
                    await asyncio.sleep(settings.SYNC_RETRY_DELAY_SECONDS)
        except asyncio.CancelledError:
            pass

    async def _full_sync(self) -> None:
        """
        Fetch ALL employees for this org from Cloud and upsert into local DB.
        Endpoint: GET /device/employees/{org_id}
        """
        logger.info("SyncService: starting full sync for org=%s", settings.CLOUD_ORG_ID)

        response = await self._http.get(f"/device/employees/{settings.CLOUD_ORG_ID}")
        employees = self._extract_list(response)

        count = await self._employee_svc.upsert_many(employees)

        # Sweep deleted employees that are no longer present in the cloud payload list
        if employees:
            active_ids = [emp["id"] for emp in employees]
            async with self._db.connection() as conn:
                placeholders = ",".join("?" for _ in active_ids)
                cursor = await conn.execute(
                    f"DELETE FROM employees WHERE org_id = ? AND id NOT IN ({placeholders})",
                    (settings.CLOUD_ORG_ID, *active_ids),
                )
                deleted_count = cursor.rowcount
                await conn.commit()
                if deleted_count > 0:
                    logger.info("SyncService: swept %d deleted employees and their fingerprints locally", deleted_count)
        else:
            # If the cloud returned 0 active employees, delete all local employees for this org
            async with self._db.connection() as conn:
                cursor = await conn.execute(
                    "DELETE FROM employees WHERE org_id = ?",
                    (settings.CLOUD_ORG_ID,),
                )
                deleted_count = cursor.rowcount
                await conn.commit()
                if deleted_count > 0:
                    logger.info("SyncService: swept all %d local employees because cloud has 0 records", deleted_count)

        now = _now_iso()

        await self._set_sync_metadata(_KEY_LAST_FULL_SYNC, now)
        await self._set_sync_metadata(_KEY_LAST_INCREMENTAL_SYNC, now)

        self._is_online = True
        self._last_sync_time = now

        logger.info("SyncService: full sync complete — %d employees upserted", count)
        await self._publish_sync_status(employee_count=count)

    async def _incremental_sync(self) -> None:
        """
        Fetch only employees updated since the last sync timestamp.
        Endpoint: GET /device/employees/{org_id}?updated_since={timestamp}
        """
        last_sync = await self._get_sync_metadata(_KEY_LAST_INCREMENTAL_SYNC)

        if not last_sync:
            # No prior sync — fall back to full sync
            logger.info("SyncService: no previous sync found, running full sync")
            await self._full_sync()
            return

        logger.info(
            "SyncService: incremental sync since %s for org=%s",
            last_sync, settings.CLOUD_ORG_ID,
        )

        response = await self._http.get(
            f"/device/employees/{settings.CLOUD_ORG_ID}",
            params={"updated_since": last_sync},
        )
        employees = self._extract_list(response)

        if employees:
            count = await self._employee_svc.upsert_many(employees)
            logger.info("SyncService: incremental sync — %d employees updated", count)
        else:
            logger.debug("SyncService: incremental sync — no changes")

        now = _now_iso()
        await self._set_sync_metadata(_KEY_LAST_INCREMENTAL_SYNC, now)

        self._is_online = True
        self._last_sync_time = now

        total = await self._employee_svc.count()
        await self._publish_sync_status(employee_count=total)

    # ── sync_metadata helpers ─────────────────────────────────────

    async def _get_sync_metadata(self, key: str) -> Optional[str]:
        """Read a value from the sync_metadata table. Returns None if not found."""
        async with self._db.connection() as conn:
            cursor = await conn.execute(
                "SELECT value FROM sync_metadata WHERE key = ?", (key,)
            )
            row = await cursor.fetchone()
            return row["value"] if row else None

    async def _set_sync_metadata(self, key: str, value: str) -> None:
        """Insert or update a sync_metadata entry."""
        now = _now_iso()
        async with self._db.connection() as conn:
            await conn.execute(
                """
                INSERT INTO sync_metadata (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (key, value, now),
            )
            await conn.commit()

    # ── EventBus publishing ───────────────────────────────────────

    async def _publish_sync_status(self, employee_count: Optional[int] = None) -> None:
        """Broadcast current sync state to React via EventBus → WebSocket."""
        event = {
            "type": "sync_status",
            "is_online": self._is_online,
            "last_sync": self._last_sync_time,
        }
        if employee_count is not None:
            event["employee_count"] = employee_count

        await self._event_bus.publish(event)

    # ── Internal helpers ──────────────────────────────────────────

    @staticmethod
    def _extract_list(response: any) -> list:
        """
        Normalize Cloud API response to a plain list of employee dicts.

        Handles both:
          - { "data": [...] }   (Laravel ResourceCollection)
          - [...]               (plain array)
        """
        if isinstance(response, list):
            return response
        if isinstance(response, dict):
            data = response.get("data", [])
            if isinstance(data, list):
                return data
        logger.warning("SyncService: unexpected response shape — %s", type(response))
        return []
