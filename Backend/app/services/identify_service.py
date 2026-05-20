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
        alcohol_svc,
    ) -> None:
        self._employee_svc = employee_svc
        self._fingerprint_svc = fingerprint_svc
        self._scan_log_svc = scan_log_svc
        self._http = http_client
        self._event_bus = event_bus
        self._command_bus = command_bus
        self._alcohol_svc = alcohol_svc

        self._cmd_queue: Optional[asyncio.Queue] = None
        self._cmd_listener_task: Optional[asyncio.Task] = None
        self._workflow_lock = asyncio.Lock()

    # ── Lifecycle ─────────────────────────────────────────────────

    async def start(self) -> None:
        self._cmd_queue = await self._command_bus.subscribe(
            filter_types={"IDENTIFY", "SCAN_FINGERPRINT"}
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
        """Wait for IDENTIFY/SCAN_FINGERPRINT commands and spawn workflow tasks."""
        try:
            while True:
                cmd = await self._cmd_queue.get()
                cmd_type = cmd.get("command")
                session_id = cmd.get("session_id")

                if cmd_type == "IDENTIFY":
                    employee_id = cmd.get("params", {}).get("employee_id", "")

                    # Debounce duplicate concurrent commands
                    if self._workflow_lock.locked():
                        logger.warning(
                            "IdentifyService: workflow is already running. Ignoring concurrent IDENTIFY command"
                        )
                        continue

                    # Run each identification in its own task so the listener
                    # stays free to accept new commands immediately.
                    if employee_id:
                        asyncio.create_task(
                            self._identify_workflow(employee_id, session_id),
                            name=f"identify-{employee_id}",
                        )
                    else:
                        asyncio.create_task(
                            self._identify_all_workflow(session_id),
                            name="identify-all",
                        )
                elif cmd_type == "SCAN_FINGERPRINT":
                    employee_id = cmd.get("params", {}).get("employee_id", "")

                    if self._workflow_lock.locked():
                        logger.warning(
                            "IdentifyService: workflow is already running. Ignoring concurrent SCAN_FINGERPRINT command"
                        )
                        continue

                    if employee_id:
                        asyncio.create_task(
                            self._enroll_workflow(employee_id, session_id),
                            name=f"enroll-{employee_id}",
                        )
                    else:
                        logger.warning("IdentifyService: SCAN_FINGERPRINT received without employee_id")
        except asyncio.CancelledError:
            pass

    async def _identify_all_workflow(self, session_id: Optional[str]) -> None:
        """1-to-N Identification Workflow for rapid fingerprint logins."""
        async with self._workflow_lock:
            def push(event: dict) -> None:
                if session_id:
                    event["session_id"] = session_id
                asyncio.create_task(self._event_bus.publish(event))

            logger.info("IdentifyService: starting 1-to-N identification flow")

            # 1. Fetch all enrolled fingerprints
            all_fps = await self._employee_svc.get_all_fingerprints()
            if not all_fps:
                logger.warning("IdentifyService: no fingerprints enrolled in database")
                push({
                    "type": "verify_result",
                    "success": False,
                    "match": False,
                    "message": "ไม่มีข้อมูลลายนิ้วมือในระบบ",
                })
                return

            # 2. Run scan & identify
            try:
                matched_emp_id = await self._fingerprint_svc.scan_and_identify(all_fps, session_id)
            except Exception as exc:
                logger.exception("IdentifyService: error during 1-to-N identify — %s", exc)
                push({
                    "type": "verify_result",
                    "success": False,
                    "match": False,
                    "message": "เกิดข้อผิดพลาดกับอุปกรณ์สแกนลายนิ้วมือ",
                })
                return

            # 3. Handle matching outcome
            if matched_emp_id:
                employee = await self._employee_svc.get_by_id(matched_emp_id)
                if employee:
                    self._alcohol_svc.set_active_employee_id(employee.id)
                    
                    push({
                        "type": "verify_result",
                        "success": True,
                        "match": True,
                        "employee": {
                            "id": employee.id,
                            "name": employee.full_name,
                            "emp_id": employee.emp_id,
                        },
                    })
                    logger.info("IdentifyService: 1-to-N Match Found -> %s (%s)", employee.full_name, employee.emp_id)
                    
                    # Log fingerprint match
                    asyncio.create_task(
                        self._scan_log_svc.log_fingerprint(employee.id, "match"),
                        name=f"log-fp-{employee.id}",
                    )
                    return

            # If unmatched
            push({
                "type": "verify_result",
                "success": True,
                "match": False,
                "message": "ไม่พบลายนิ้วมือที่ตรงกัน",
            })
            logger.info("IdentifyService: 1-to-N Identification - NO MATCH")

            # Log failed attempt locally against "UNKNOWN"
            asyncio.create_task(
                self._scan_log_svc.log_fingerprint("UNKNOWN", "no_match"),
                name="log-fp-unknown",
            )

    # ── Identification workflow ───────────────────────────────────

    async def _identify_workflow(
        self, employee_id: str, session_id: Optional[str]
    ) -> None:
        """
        Full identification flow for a single request.
        All events include session_id if provided.
        """
        async with self._workflow_lock:
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

            if match:
                self._alcohol_svc.set_active_employee_id(employee.id)

            # ── Step 5: Publish verification result ───────────────────
            push({
                "type": "verify_result",
                "success": True,
                "match": match,
                "employee": {
                    "id": employee.id,
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

    # ── Enrollment workflow ───────────────────────────────────────

    async def _enroll_workflow(
        self, employee_id: str, session_id: Optional[str]
    ) -> None:
        """
        Enrollment workflow: captures fingerprint, saves it locally, and uploads to cloud.
        """
        async with self._workflow_lock:
            def push(event: dict) -> None:
                if session_id:
                    event["session_id"] = session_id
                asyncio.create_task(self._event_bus.publish(event))

            logger.info("IdentifyService: starting fingerprint enrollment for employee_id='%s'", employee_id)

            # 1. Fetch employee from local SQLite using primary key (id)
            employee = await self._employee_svc.get_by_id(employee_id)
            if not employee:
                logger.warning("IdentifyService: employee '%s' not found for enrollment", employee_id)
                push({
                    "type": "enroll_result",
                    "success": False,
                    "message": "ไม่พบข้อมูลพนักงานในระบบ",
                })
                return

            # 2. Call capture_fingerprint from FingerprintService
            try:
                fingerprint_code = await self._fingerprint_svc.capture_fingerprint(session_id)
            except Exception as exc:
                logger.exception("IdentifyService: error capturing fingerprint — %s", exc)
                push({
                    "type": "enroll_result",
                    "success": False,
                    "message": "เกิดข้อผิดพลาดกับอุปกรณ์สแกนลายนิ้วมือ",
                })
                return

            if not fingerprint_code:
                logger.warning("IdentifyService: fingerprint capture failed (None returned)")
                push({
                    "type": "enroll_result",
                    "success": False,
                    "message": "การสแกนลายนิ้วมือล้มเหลว หรือหมดเวลาสแกน",
                })
                return

            # 3. Save template locally in SQLite
            try:
                await self._employee_svc.save_fingerprint(
                    employee_id=employee.id,
                    fingerprint_code=fingerprint_code,
                    finger_index=0
                )
            except Exception as exc:
                logger.exception("IdentifyService: failed to save fingerprint locally — %s", exc)
                push({
                    "type": "enroll_result",
                    "success": False,
                    "message": "เกิดข้อผิดพลาดในการบันทึกข้อมูลลายนิ้วมือบนเครื่อง Kiosk",
                })
                return

            # 4. POST the template to the cloud via CloudHttpClient
            try:
                payload = {
                    "employee_id": employee.id,
                    "finger_index": 0,
                    "fingerprint_code": fingerprint_code,
                }
                
                # Cloud REST API endpoint as per approved spec
                await self._http.post("/device/employee/fingerprint", json=payload)
                
                logger.info(
                    "IdentifyService: successfully uploaded fingerprint for %s to cloud",
                    employee.full_name,
                )
            except Exception as exc:
                logger.exception("IdentifyService: failed to upload fingerprint to cloud — %s", exc)
                push({
                    "type": "enroll_result",
                    "success": False,
                    "message": f"ไม่สามารถส่งข้อมูลลายนิ้วมือไปยังระบบคลาวด์ได้ ({str(exc)})",
                })
                return

            # 5. Broadcast success
            push({
                "type": "enroll_result",
                "success": True,
                "message": "ลงทะเบียนลายนิ้วมือสำเร็จ",
            })
            logger.info("IdentifyService: successfully completed enrollment workflow for %s", employee.full_name)
