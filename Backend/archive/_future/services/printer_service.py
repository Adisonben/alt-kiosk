"""
PrinterService — Manages ESC/POS receipt printing.

Subscribes to CommandBus for: PRINT_RECEIPT.
Publishes print_complete / print_error events to EventBus.
"""

import asyncio
import os
import logging
from datetime import datetime
from typing import Optional

from device.printer_protocol import VENDOR_ID, PRODUCT_ID, LOGO_PATH

logger = logging.getLogger(__name__)

try:
    from escpos.printer import Usb
    _escpos_available = True
except ImportError:
    _escpos_available = False

try:
    from PIL import Image
    _pil_available = True
except ImportError:
    _pil_available = False


class PrinterService:
    """
    Handles receipt printing via USB ESC/POS printer.

    Subscribes to PRINT_RECEIPT commands from the CommandBus.
    Can also be called directly via REST endpoint.
    """

    def __init__(self, event_bus, command_bus):
        self._event_bus = event_bus
        self._command_bus = command_bus
        self._cmd_queue: Optional[asyncio.Queue] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._cmd_listener_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Subscribe to command bus and start listening."""
        self._loop = asyncio.get_running_loop()
        self._cmd_queue = await self._command_bus.subscribe(
            filter_types={"PRINT_RECEIPT"}
        )
        self._cmd_listener_task = asyncio.create_task(self._listen_commands())
        logger.info("PrinterService started")

    async def stop(self) -> None:
        """Stop listening and unsubscribe."""
        if self._cmd_listener_task:
            self._cmd_listener_task.cancel()
            try:
                await self._cmd_listener_task
            except asyncio.CancelledError:
                pass
        if self._cmd_queue:
            await self._command_bus.unsubscribe(self._cmd_queue)
        logger.info("PrinterService stopped")

    # ── Health ────────────────────────────────────────────────

    def is_alive(self) -> bool:
        """Always True — no background thread."""
        return True

    def is_connected(self) -> bool:
        """True if escpos library is available."""
        return _escpos_available

    # ── Command listener ──────────────────────────────────────

    async def _listen_commands(self) -> None:
        """Async loop: wait for PRINT_RECEIPT commands."""
        try:
            while True:
                cmd = await self._cmd_queue.get()
                params = cmd.get("params", {})
                session_id = cmd.get("session_id")
                result = await self.print_receipt(
                    user_name=params.get("user_name", ""),
                    user_id=params.get("user_id", ""),
                    device_id=params.get("device_id", ""),
                    status=params.get("status", ""),
                    value=params.get("value", 0.0),
                    session_id=session_id,
                )
        except asyncio.CancelledError:
            pass

    # ── Print operation ───────────────────────────────────────

    async def print_receipt(
        self,
        user_name: str,
        user_id: str,
        device_id: str,
        status: str,
        value: float,
        session_id: Optional[str] = None,
    ) -> dict:
        """
        Print an alcohol test result receipt.
        Runs in executor to avoid blocking the event loop.
        Publishes print_complete or print_error event.
        """
        result = await self._loop.run_in_executor(
            None, self._do_print, user_name, user_id, device_id, status, value
        )

        event = {
            "type": "print_complete" if result["success"] else "print_error",
            "success": result["success"],
        }
        if not result["success"]:
            event["error"] = result.get("error", "Unknown error")
        if session_id:
            event["session_id"] = session_id
        await self._event_bus.publish(event)

        return result

    @staticmethod
    def _do_print(user_name: str, user_id: str, device_id: str, status: str, value: float) -> dict:
        """Blocking: send receipt data to ESC/POS printer."""
        if not _escpos_available:
            return {"success": False, "error": "python-escpos not installed"}

        try:
            p = Usb(VENDOR_ID, PRODUCT_ID)

            p.set(align="center", bold=True, width=3, height=3)
            if _pil_available and os.path.exists(LOGO_PATH):
                img = Image.open(LOGO_PATH).convert("1")
                p.image(img, impl="graphics")

            p.text("\nALCOHOL TEST RESULT\n")
            p.set(align="left", bold=False, width=2, height=2)

            p.text("--------------------------------\n")
            p.text(f"เครื่องทดสอบ (Device ID) : {device_id}\n")
            p.text(f"รหัสผู้ทดสอบ (User ID)   : {user_id}\n")
            p.text(f"ชื่อผู้ทดสอบ (Name)      : {user_name}\n")
            p.text(f"ปริมาณแอลกอฮอล์ (Value) : {value} mg/100ml\n")
            p.text(f"สรุปผลการทดสอบ (Result) : {status}\n")
            dt_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            p.text(f"วันที่ (Date) : {dt_str}\n")
            p.text("--------------------------------\n")

            p.set(align="center", bold=True, width=2, height=2)
            if status == "PASS":
                p.text("*** PASS ***")
            elif status == "FAIL":
                p.text("*** FAIL ***")
            else:
                p.text("*** ERROR ***")

            p.cut()
            p.close()
            return {"success": True}

        except Exception as exc:
            logger.exception("Printer error")
            return {"success": False, "error": str(exc)}
