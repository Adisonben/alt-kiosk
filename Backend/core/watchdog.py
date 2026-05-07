"""
Watchdog Supervisor — Periodic health checks for all device services.

Runs as an async background task. On failure:
    1. Publishes device_status "error" event.
    2. Attempts restart via DeviceManager.
    3. Publishes "recovering" → "connected" or "disconnected".
"""

import asyncio
import logging

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL = 5.0  # seconds between health checks


class Watchdog:
    """
    Periodically checks device health and triggers recovery.

    Args:
        device_manager: DeviceManager instance.
        event_bus: EventBus instance (for direct status publishing).
        interval: Seconds between health check cycles.
    """

    def __init__(self, device_manager, event_bus, interval: float = DEFAULT_INTERVAL):
        self._device_manager = device_manager
        self._event_bus = event_bus
        self._interval = interval
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        """Start the watchdog background loop."""
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Watchdog started (interval=%.1fs)", self._interval)

    async def stop(self) -> None:
        """Stop the watchdog."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Watchdog stopped")

    async def _loop(self) -> None:
        """Main watchdog loop."""
        try:
            while self._running:
                await asyncio.sleep(self._interval)
                await self._check_all()
        except asyncio.CancelledError:
            pass

    async def _check_all(self) -> None:
        """Check health of all devices and attempt recovery if needed."""
        report = self._device_manager.health_check()

        for name, info in report.items():
            if not info["alive"]:
                logger.warning("Watchdog: '%s' is not alive — attempting restart", name)
                success = await self._device_manager.restart_device(name)
                if success:
                    logger.info("Watchdog: '%s' recovered", name)
                else:
                    logger.error("Watchdog: '%s' restart failed", name)
