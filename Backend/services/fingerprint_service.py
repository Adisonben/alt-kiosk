"""
FingerprintService — Manages fingerprint scan and compare operations.

Publishes fingerprint_result events to EventBus.
Fingerprint operations are REST-driven (not command bus) since they are
request-response in nature, but results are also published to the event bus
for the kiosk controller to react to.
"""

import asyncio
import os
import subprocess
import logging
from typing import Optional

from device.fingerprint_protocol import (
    BIN_PATH, MATCH_BIN_PATH,
    SCAN_CMD, MATCH_CMD_BASE,
    SCAN_PROCESS_TIMEOUT, MATCH_PROCESS_TIMEOUT,
    TEMPLATE_SIZE,
    raw_to_base64, base64_to_raw,
)

logger = logging.getLogger(__name__)


class FingerprintService:
    """
    Wraps fingerprint scan/compare binaries.

    Runs subprocess calls in asyncio executors to avoid blocking.
    Publishes results to EventBus so KioskController can react.
    """

    def __init__(self, event_bus):
        self._event_bus = event_bus
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def start(self) -> None:
        """Initialize the service."""
        self._loop = asyncio.get_running_loop()
        logger.info("FingerprintService started")

    async def stop(self) -> None:
        """Clean up."""
        logger.info("FingerprintService stopped")

    # ── Health ────────────────────────────────────────────────

    def is_alive(self) -> bool:
        """Always True — no background thread."""
        return True

    def is_connected(self) -> bool:
        """True if the finger_scan binary exists."""
        return os.path.exists(BIN_PATH)

    # ── Operations ────────────────────────────────────────────

    async def scan(self, session_id: Optional[str] = None) -> dict:
        """
        Run the finger_scan binary and return the template as base64.

        Returns dict with keys: success, data, reason.
        Also publishes a fingerprint_result event.
        """
        result = await self._loop.run_in_executor(None, self._run_scan)

        event = {
            "type": "fingerprint_result",
            "success": result["success"],
            "data": result.get("data"),
            "reason": result.get("reason"),
        }
        if session_id:
            event["session_id"] = session_id
        await self._event_bus.publish(event)

        return result

    async def compare(self, data1_b64: str, data2_b64: str, session_id: Optional[str] = None) -> dict:
        """
        Compare two base64-encoded fingerprint templates.

        Returns dict with keys: match, message.
        """
        raw1 = base64_to_raw(data1_b64)
        raw2 = base64_to_raw(data2_b64)

        if len(raw1) != TEMPLATE_SIZE or len(raw2) != TEMPLATE_SIZE:
            return {"match": False, "message": f"Invalid template size (expected {TEMPLATE_SIZE} bytes each)"}

        result = await self._loop.run_in_executor(None, self._run_compare, raw1, raw2)
        return result

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
