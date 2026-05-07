"""
DeviceManager — Centralized lifecycle management for all hardware services.

Responsibilities:
    - start_all() / stop_all() on app startup/shutdown.
    - restart_device(name) for recovery.
    - health_check() returns status of each device.
    - Publishes device_status events to EventBus.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Standardized device status values
STATUS_CONNECTED = "connected"
STATUS_DISCONNECTED = "disconnected"
STATUS_ERROR = "error"
STATUS_RECOVERING = "recovering"


class DeviceManager:
    """
    Holds references to all device services and manages their lifecycle.

    Each service must implement:
        async start() -> None
        async stop() -> None
        is_alive() -> bool
        is_connected() -> bool
    """

    def __init__(self, event_bus):
        self._event_bus = event_bus
        self._services: Dict[str, Any] = {}

    def register(self, name: str, service) -> None:
        """Register a device service by name."""
        self._services[name] = service
        logger.info("DeviceManager: registered '%s'", name)

    async def start_all(self) -> None:
        """Start all registered services and publish device_status events."""
        for name, service in self._services.items():
            try:
                await service.start()
                status = STATUS_CONNECTED if service.is_connected() else STATUS_DISCONNECTED
                await self._publish_status(name, status)
                logger.info("DeviceManager: started '%s' (status=%s)", name, status)
            except Exception as exc:
                await self._publish_status(name, STATUS_ERROR)
                logger.exception("DeviceManager: failed to start '%s' — %s", name, exc)

    async def stop_all(self) -> None:
        """Stop all registered services gracefully."""
        for name, service in self._services.items():
            try:
                await service.stop()
                await self._publish_status(name, STATUS_DISCONNECTED)
                logger.info("DeviceManager: stopped '%s'", name)
            except Exception as exc:
                logger.exception("DeviceManager: error stopping '%s' — %s", name, exc)

    async def restart_device(self, name: str) -> bool:
        """
        Restart a single device service.
        Returns True if restart succeeded, False otherwise.
        """
        service = self._services.get(name)
        if service is None:
            logger.error("DeviceManager: unknown device '%s'", name)
            return False

        await self._publish_status(name, STATUS_RECOVERING)
        logger.info("DeviceManager: restarting '%s'", name)

        try:
            await service.stop()
        except Exception as exc:
            logger.warning("DeviceManager: error stopping '%s' during restart — %s", name, exc)

        try:
            await service.start()
            status = STATUS_CONNECTED if service.is_connected() else STATUS_DISCONNECTED
            await self._publish_status(name, status)
            logger.info("DeviceManager: restarted '%s' (status=%s)", name, status)
            return status == STATUS_CONNECTED
        except Exception as exc:
            await self._publish_status(name, STATUS_ERROR)
            logger.exception("DeviceManager: restart failed for '%s' — %s", name, exc)
            return False

    def health_check(self) -> Dict[str, dict]:
        """
        Return health status for all registered devices.

        Returns:
            {
                "alcohol": {"alive": True, "connected": True, "status": "connected"},
                "printer": {"alive": True, "connected": False, "status": "disconnected"},
                ...
            }
        """
        report = {}
        for name, service in self._services.items():
            alive = service.is_alive()
            connected = service.is_connected()
            if not alive:
                status = STATUS_ERROR
            elif connected:
                status = STATUS_CONNECTED
            else:
                status = STATUS_DISCONNECTED
            report[name] = {
                "alive": alive,
                "connected": connected,
                "status": status,
            }
        return report

    def get_service(self, name: str):
        """Retrieve a service instance by name."""
        return self._services.get(name)

    @property
    def service_names(self):
        """List of registered service names."""
        return list(self._services.keys())

    async def _publish_status(self, device: str, status: str) -> None:
        """Publish a device_status event."""
        await self._event_bus.publish({
            "type": "device_status",
            "device": device,
            "status": status,
        })
