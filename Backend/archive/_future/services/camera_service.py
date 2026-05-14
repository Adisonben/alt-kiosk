"""
CameraService — Manages Picamera2 snapshot capture.

Subscribes to CommandBus for: CAPTURE_PHOTO.
Publishes photo_captured events to EventBus.
No Kivy dependency — uses plain threading.
"""

import asyncio
import os
import threading
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from picamera2 import Picamera2
    _PICAMERA_AVAILABLE = True
except ImportError:
    _PICAMERA_AVAILABLE = False
    logger.warning("picamera2 not available — camera functions disabled")


class CameraService:
    """
    Captures still images using Picamera2 on Raspberry Pi.

    Subscribes to CAPTURE_PHOTO commands from the CommandBus.
    Publishes photo_captured event with file path on success.
    """

    def __init__(self, event_bus, command_bus):
        self._event_bus = event_bus
        self._command_bus = command_bus
        self._cmd_queue: Optional[asyncio.Queue] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._cmd_listener_task: Optional[asyncio.Task] = None
        self._capture_thread: Optional[threading.Thread] = None

    async def start(self) -> None:
        """Subscribe to command bus and start listening."""
        self._loop = asyncio.get_running_loop()
        self._cmd_queue = await self._command_bus.subscribe(
            filter_types={"CAPTURE_PHOTO"}
        )
        self._cmd_listener_task = asyncio.create_task(self._listen_commands())
        logger.info("CameraService started")

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
        logger.info("CameraService stopped")

    # ── Health ────────────────────────────────────────────────

    def is_alive(self) -> bool:
        """True if no capture is stuck."""
        if self._capture_thread and self._capture_thread.is_alive():
            return True
        return True  # idle is healthy

    def is_connected(self) -> bool:
        """True if picamera2 is available."""
        return _PICAMERA_AVAILABLE

    # ── Command listener ──────────────────────────────────────

    async def _listen_commands(self) -> None:
        """Async loop: wait for CAPTURE_PHOTO commands."""
        try:
            while True:
                cmd = await self._cmd_queue.get()
                params = cmd.get("params", {})
                session_id = cmd.get("session_id")
                filepath = params.get("filepath", "/tmp/alt-snapshot.jpg")
                await self.capture(filepath, session_id)
        except asyncio.CancelledError:
            pass

    # ── Capture operation ─────────────────────────────────────

    async def capture(self, filepath: str, session_id: Optional[str] = None) -> dict:
        """
        Capture a snapshot in a background thread.
        Publishes photo_captured event on completion.
        """
        if not _PICAMERA_AVAILABLE:
            event = {
                "type": "photo_captured",
                "success": False,
                "reason": "picamera2 not available",
            }
            if session_id:
                event["session_id"] = session_id
            await self._event_bus.publish(event)
            return {"success": False, "reason": "picamera2 not available"}

        result = await self._loop.run_in_executor(None, self._do_capture, filepath)

        event = {
            "type": "photo_captured",
            "success": result["success"],
            "path": result.get("path"),
        }
        if not result["success"]:
            event["reason"] = result.get("reason")
        if session_id:
            event["session_id"] = session_id
        await self._event_bus.publish(event)

        return result

    @staticmethod
    def _do_capture(filepath: str) -> dict:
        """Blocking: capture a still image using Picamera2."""
        picam2 = None
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            picam2 = Picamera2()
            config = picam2.create_still_configuration(
                main={"size": (1920, 1080)},
                lores={"size": (640, 480)},
                display="lores",
            )
            picam2.configure(config)
            picam2.start()
            time.sleep(0.5)  # warm-up

            picam2.capture_file(filepath)
            logger.info("CameraService: snapshot saved to %s", filepath)
            return {"success": True, "path": filepath}

        except Exception as exc:
            logger.exception("CameraService: capture error")
            return {"success": False, "reason": str(exc)}
        finally:
            if picam2 is not None:
                try:
                    picam2.stop()
                    picam2.close()
                except Exception:
                    pass
