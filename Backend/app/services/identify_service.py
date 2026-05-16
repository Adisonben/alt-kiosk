"""
IdentifyService — orchestrates the full identification and verification flow.

Listens for IDENTIFY commands from the WebSocket (via CommandBus).
For each request:
  1. Looks up the employee in the local SQLite DB
  2. Publishes identify_result event (found / not found)
  3. Triggers fingerprint scan + compare via FingerprintService
  4. Publishes verify_result event with the final outcome
  5. Logs the scan result asynchronously via ScanLogService

This service is the single point of business logic for identification.
React only needs to send { command: "IDENTIFY", params: { employee_id } }
and listen for the resulting events.

New events introduced:
  identify_result — employee lookup outcome
  verify_result   — fingerprint match outcome (replaces relying on fingerprint_result in new flow)
"""

import asyncio
import logging
from typing import Optional

from app.services.employee_service import EmployeeService
from app.services.fingerprint_service import FingerprintService
from app.services.scan_log_service import ScanLogService
from app.config import settings

logger = logging.getLogger(__name__)


class IdentifyService:
    """
    Orchestrates: employee lookup → fingerprint scan → result publishing → log.

    Subscribes to IDENTIFY command on CommandBus.
    Publishes identify_result and verify_result events via EventBus.
    """

    def __init__(
        self,
        employee_svc: EmployeeService,
        fingerprint_svc: FingerprintService,
        scan_log_svc: ScanLogService,
        http_client,
        event_bus,
        command_bus,
    ) -> None:
        self._employee_svc = employee_svc
        self._fingerprint_svc = fingerprint_svc
        self._scan_log_svc = scan_log_svc
        self._http = http_client
        self._event_bus = event_bus
        self._command_bus = command_bus

        self._cmd_queue: Optional[asyncio.Queue] = None
        self._cmd_listener_task: Optional[asyncio.Task] = None

    # ── Lifecycle ─────────────────────────────────────────────────

    async def start(self) -> None:
        self._cmd_queue = await self._command_bus.subscribe(
            filter_types={"IDENTIFY"}
        )
        self._cmd_listener_task = asyncio.create_task(
            self._listen_commands(), name="identify-cmd-listener"
        )
        logger.info("IdentifyService: started")

    async def stop(self) -> None:
        if self._cmd_listener_task and not self._cmd_listener_task.done():
            self._cmd_listener_task.cancel()
            try:
                await self._cmd_listener_task
            except asyncio.CancelledError:
                pass

        if self._cmd_queue:
            await self._command_bus.unsubscribe(self._cmd_queue)

        logger.info("IdentifyService: stopped")

    # ── Command listener ──────────────────────────────────────────

    async def _listen_commands(self) -> None:
        """Wait for IDENTIFY commands and spawn a workflow task per request."""
        try:
            while True:
                cmd = await self._cmd_queue.get()
                if cmd.get("command") == "IDENTIFY":
                    employee_id = cmd.get("params", {}).get("employee_id", "")
                    session_id = cmd.get("session_id")

                    if not employee_id:
                        logger.warning("IdentifyService: IDENTIFY command missing employee_id")
                        continue

                    # Run each identification in its own task so the listener
                    # stays free to accept new commands immediately.
                    asyncio.create_task(
                        self._identify_workflow(employee_id, session_id),
                        name=f"identify-{employee_id}",
                    )
        except asyncio.CancelledError:
            pass

    # ── Identification workflow ───────────────────────────────────

    async def _identify_workflow(
        self, employee_id: str, session_id: Optional[str]
    ) -> None:
        """
        Full identification flow for a single request.
        All events include session_id if provided.
        """
        def push(event: dict) -> None:
            if session_id:
                event["session_id"] = session_id
            asyncio.create_task(self._event_bus.publish(event))

        logger.info("IdentifyService: identifying emp_id='%s'", employee_id)

        # Prepend Org Code and 'E' to the employee_id for lookup
        # Example: IDD + E + 00001 = IDDE00001
        formatted_id = f"{settings.CLOUD_ORG_CODE}E{employee_id}"
        logger.debug("IdentifyService: formatted lookup ID: '%s'", formatted_id)

        # ── Step 1: Lookup employee in local DB ───────────────────
        employee = await self._employee_svc.get_by_emp_id(formatted_id)

        if not employee:
            logger.warning("IdentifyService: emp_id '%s' not found in local DB", employee_id)
            push({
                "type": "identify_result",
                "success": False,
                "message": "ไม่พบข้อมูลพนักงาน",
            })
            return

        # ── Step 2: Publish employee found ────────────────────────
        push({
            "type": "identify_result",
            "success": True,
            "employee": {
                "id": employee.id,
                "name": employee.full_name,
                "emp_id": employee.emp_id,
            },
            "has_fingerprints": len(employee.fingerprints) > 0,
        })

        # (Merged logging: we now only log once at the end of the workflow)

        # ── Step 3: Guard — no fingerprints enrolled ──────────────
        if not employee.fingerprints:
            logger.warning(
                "IdentifyService: emp_id '%s' has no fingerprint templates", employee_id
            )
            push({
                "type": "verify_result",
                "success": False,
                "match": False,
                "message": "ไม่มีข้อมูลลายนิ้วมือในระบบ",
            })
            
            # Log single result: no templates
            asyncio.create_task(
                self._scan_log_svc.log_fingerprint(employee.id, "no_templates"),
                name=f"log-fp-{employee.id}",
            )
            return

        # ── Step 4: Run fingerprint scan + compare ────────────────
        templates = [fp.fingerprint_code for fp in employee.fingerprints]

        try:
            match = await self._fingerprint_svc.scan_and_verify(templates, session_id)
        except Exception as exc:
            logger.exception("IdentifyService: fingerprint scan error — %s", exc)
            push({
                "type": "verify_result",
                "success": False,
                "match": False,
                "message": "เกิดข้อผิดพลาดกับอุปกรณ์สแกนลายนิ้วมือ",
            })

            # Log single result: device error
            asyncio.create_task(
                self._scan_log_svc.log_fingerprint(employee.id, "scan_error"),
                name=f"log-fp-{employee.id}",
            )
            return

        # ── Step 5: Publish verification result ───────────────────
        push({
            "type": "verify_result",
            "success": True,
            "match": match,
            "employee": {
                "name": employee.full_name,
                "emp_id": employee.emp_id,
            },
        })

        logger.info(
            "IdentifyService: emp_id='%s' — %s",
            employee_id, "MATCH" if match else "NO MATCH",
        )

        # ── Step 6: Log result locally (LogUploader will sync to cloud) ───
        asyncio.create_task(
            self._scan_log_svc.log_fingerprint(
                employee.id, "match" if match else "no_match"
            ),
            name=f"log-fp-{employee.id}",
        )
