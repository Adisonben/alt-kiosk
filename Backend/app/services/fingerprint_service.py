"""
FingerprintService — Manages fingerprint scan and verify operations.

Listens to CommandBus for VERIFY_FINGERPRINT (legacy path, backward-compatible).
Exposes scan_and_verify() as a public method for IdentifyService (new path).
Publishes fingerprint_state and fingerprint_result events to EventBus.
"""

import asyncio
import os
import subprocess
import logging
from typing import Optional

from app.hardware.fingerprint_protocol import (
    BIN_PATH, MATCH_BIN_PATH,
    SCAN_CMD, MATCH_CMD_BASE,
    SCAN_PROCESS_TIMEOUT, MATCH_PROCESS_TIMEOUT,
    TEMPLATE_SIZE,
    raw_to_base64, base64_to_raw,
)

logger = logging.getLogger(__name__)

_STATUS_MSG = {
    "scanning": "กำลังสแกนลายนิ้วมือ... / Scanning fingerprint...",
    "processing": "กำลังตรวจสอบ... / Verifying...",
}

class FingerprintService:
    """
    Service to handle fingerprint verification.
    Subscribes to CommandBus and publishes to EventBus.
    """

    def __init__(self, event_bus, command_bus):
        self._event_bus = event_bus
        self._command_bus = command_bus
        self._cmd_queue: Optional[asyncio.Queue] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._cmd_listener_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Initialize the service and subscribe to commands."""
        self._loop = asyncio.get_running_loop()
        self._cmd_queue = await self._command_bus.subscribe(
            filter_types={"VERIFY_FINGERPRINT"}
        )
        self._cmd_listener_task = asyncio.create_task(self._listen_commands())
        logger.info("FingerprintService started")

    async def stop(self) -> None:
        """Clean up."""
        if self._cmd_listener_task:
            self._cmd_listener_task.cancel()
            try:
                await self._cmd_listener_task
            except asyncio.CancelledError:
                pass
        if self._cmd_queue:
            await self._command_bus.unsubscribe(self._cmd_queue)
        logger.info("FingerprintService stopped")

    def is_alive(self) -> bool:
        return self._cmd_listener_task is not None and not self._cmd_listener_task.done()

    async def scan_and_verify(
        self, target_templates: list, session_id: Optional[str] = None
    ) -> bool:
        """
        Public entry point for IdentifyService.
        Runs the full scan + compare workflow and returns True if match found.
        Also publishes fingerprint_state and fingerprint_result events.
        """
        return await self._verify_workflow(target_templates, session_id)

    async def scan_and_identify(
        self, all_fingerprints: list, session_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Runs the fingerprint scan and compares the scanned template against
        all registered templates. Returns the matched employee_id or None.
        """
        def push(event: dict):
            if session_id:
                event["session_id"] = session_id
            asyncio.create_task(self._event_bus.publish(event))

        # 1. State: Scanning
        push({"type": "fingerprint_state", "state": "scanning", "message": _STATUS_MSG["scanning"]})

        # 2. Capture Fingerprint
        scan_result = await self._loop.run_in_executor(None, self._run_scan)
        if not scan_result["success"]:
            logger.warning("Fingerprint scan failed: %s", scan_result.get("reason"))
            push({
                "type": "fingerprint_result",
                "success": False,
                "match": False,
                "message": f"Scan failed: {scan_result.get('reason')}"
            })
            return None

        # 3. State: Processing
        push({"type": "fingerprint_state", "state": "processing", "message": _STATUS_MSG["processing"]})

        scanned_base64 = scan_result["data"]
        scanned_raw = base64_to_raw(scanned_base64)
        if len(scanned_raw) != TEMPLATE_SIZE:
            push({
                "type": "fingerprint_result",
                "success": False,
                "match": False,
                "message": "Invalid scanned template size"
            })
            return None

        # 4. Compare sequentially against templates
        match_employee_id = None
        error_msg = ""

        if not all_fingerprints:
            error_msg = "No registered fingerprints"
        else:
            for fp in all_fingerprints:
                target_raw = base64_to_raw(fp.fingerprint_code)
                if len(target_raw) != TEMPLATE_SIZE:
                    continue

                compare_result = await self._loop.run_in_executor(
                    None, self._run_compare, scanned_raw, target_raw
                )
                if compare_result.get("match"):
                    match_employee_id = fp.employee_id
                    break

                if not compare_result.get("match") and "Error" in compare_result.get("message", ""):
                    error_msg = compare_result.get("message")

        # 5. Publish Final Result
        if match_employee_id:
            push({
                "type": "fingerprint_result",
                "success": True,
                "match": True,
                "message": "Match successful"
            })
        else:
            push({
                "type": "fingerprint_result",
                "success": True,
                "match": False,
                "message": error_msg or "No match found"
            })

        return match_employee_id

    async def capture_fingerprint(
        self, session_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Runs the fingerprint scan workflow to capture a template for registration.
        Returns the captured Base64 fingerprint template if successful, or None.
        """
        def push(event: dict):
            if session_id:
                event["session_id"] = session_id
            asyncio.create_task(self._event_bus.publish(event))

        # 1. State: Scanning
        push({"type": "fingerprint_state", "state": "scanning", "message": _STATUS_MSG["scanning"]})

        # 2. Capture Fingerprint
        scan_result = await self._loop.run_in_executor(None, self._run_scan)
        if not scan_result["success"]:
            logger.warning("Fingerprint registration scan failed: %s", scan_result.get("reason"))
            push({
                "type": "fingerprint_result",
                "success": False,
                "match": False,
                "message": f"Scan failed: {scan_result.get('reason')}"
            })
            return None

        # 3. State: Processing
        push({"type": "fingerprint_state", "state": "processing", "message": _STATUS_MSG["processing"]})

        scanned_base64 = scan_result["data"]
        scanned_raw = base64_to_raw(scanned_base64)
        if len(scanned_raw) != TEMPLATE_SIZE:
            push({
                "type": "fingerprint_result",
                "success": False,
                "match": False,
                "message": "Invalid scanned template size"
            })
            return None

        # 4. Notify scanning success
        push({
            "type": "fingerprint_result",
            "success": True,
            "match": False,
            "message": "Capture successful"
        })

        return scanned_base64

    async def _listen_commands(self) -> None:
        """Async loop: wait for commands from the CommandBus."""
        try:
            while True:
                cmd = await self._cmd_queue.get()
                cmd_type = cmd.get("command")
                session_id = cmd.get("session_id")
                params = cmd.get("params", {})

                if cmd_type == "VERIFY_FINGERPRINT":
                    target_templates = params.get("target_templates", [])
                    # Run verification without blocking the command loop
                    asyncio.create_task(self._verify_workflow(target_templates, session_id))
        except asyncio.CancelledError:
            pass

    async def _verify_workflow(
        self, target_templates: list, session_id: Optional[str]
    ) -> bool:
        """Execute the full scan and compare flow. Returns True if match found."""
        def push(event: dict):
            if session_id:
                event["session_id"] = session_id
            asyncio.create_task(self._event_bus.publish(event))

        # 1. State: Scanning
        push({"type": "fingerprint_state", "state": "scanning", "message": _STATUS_MSG["scanning"]})

        # 2. Perform Scan
        scan_result = await self._loop.run_in_executor(None, self._run_scan)
        
        if not scan_result["success"]:
            logger.warning("Fingerprint scan failed: %s", scan_result.get("reason"))
            push({
                "type": "fingerprint_result",
                "success": False,
                "match": False,
                "message": f"Scan failed: {scan_result.get('reason')}"
            })
            return False

        # 3. State: Processing
        push({"type": "fingerprint_state", "state": "processing", "message": _STATUS_MSG["processing"]})

        scanned_base64 = scan_result["data"]
        scanned_raw = base64_to_raw(scanned_base64)

        if len(scanned_raw) != TEMPLATE_SIZE:
            push({
                "type": "fingerprint_result",
                "success": False,
                "match": False,
                "message": "Invalid scanned template size"
            })
            return False

        # 4. Compare against provided templates
        match_found = False
        error_msg = ""

        if not target_templates:
            error_msg = "No target templates provided."
        else:
            for template_b64 in target_templates:
                target_raw = base64_to_raw(template_b64)
                if len(target_raw) != TEMPLATE_SIZE:
                    logger.warning("Skipping invalid target template size.")
                    continue
                
                compare_result = await self._loop.run_in_executor(None, self._run_compare, scanned_raw, target_raw)
                
                if compare_result.get("match"):
                    match_found = True
                    break
                
                if not compare_result.get("match") and "Error" in compare_result.get("message", ""):
                    error_msg = compare_result.get("message")

        # 5. Publish Result
        if match_found:
            push({
                "type": "fingerprint_result",
                "success": True,
                "match": True,
                "message": "Match successful"
            })
        else:
            push({
                "type": "fingerprint_result",
                "success": True,
                "match": False,
                "message": error_msg or "No match found"
            })

        return match_found

    # ── Blocking helpers (run in executor) ────────────────────

    @staticmethod
    def _run_scan() -> dict:
        """Blocking: execute finger_scan binary."""
        if not os.path.exists(BIN_PATH):
            return {"success": False, "data": None, "reason": f"binary not found at {BIN_PATH}"}

        try:
            proc = subprocess.Popen(SCAN_CMD, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                stdout, stderr = proc.communicate(timeout=SCAN_PROCESS_TIMEOUT)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()
                return {"success": False, "data": None, "reason": "timeout"}

            if stderr:
                logger.debug("finger_scan STDERR: %s", stderr.decode(errors="ignore").strip())

            if len(stdout) == TEMPLATE_SIZE:
                return {"success": True, "data": raw_to_base64(stdout)}
            elif len(stdout) == 8:
                return {"success": False, "data": None, "reason": "timeout"}
            elif len(stdout) == 5:
                return {"success": False, "data": None, "reason": "error"}
            else:
                return {"success": False, "data": None, "reason": f"unknown_size_{len(stdout)}"}

        except Exception as exc:
            logger.exception("finger_scan error")
            return {"success": False, "data": None, "reason": str(exc)}

    @staticmethod
    def _run_compare(data1: bytes, data2: bytes) -> dict:
        """Blocking: execute match_template binary."""
        import tempfile

        fpath1 = fpath2 = None
        try:
            t1 = tempfile.NamedTemporaryFile(delete=False)
            t2 = tempfile.NamedTemporaryFile(delete=False)
            t1.write(data1)
            t2.write(data2)
            t1.flush(); t2.flush()
            t1.close(); t2.close()
            fpath1, fpath2 = t1.name, t2.name

            cmd = MATCH_CMD_BASE + [fpath1, fpath2]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = proc.communicate(timeout=MATCH_PROCESS_TIMEOUT)

            if stderr:
                logger.debug("match_template STDERR: %s", stderr.decode(errors="ignore").strip())

            result_str = stdout.decode().strip()
            if result_str == "1":
                return {"match": True, "message": "Match"}
            elif result_str == "0":
                return {"match": False, "message": "No Match"}
            else:
                return {"match": False, "message": f"Error: {result_str}"}

        except Exception as exc:
            logger.exception("match_template error")
            return {"match": False, "message": str(exc)}
        finally:
            for p in [fpath1, fpath2]:
                if p and os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass
