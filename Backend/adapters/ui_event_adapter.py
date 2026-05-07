"""
UI Event Adapter — Transforms internal events into frontend-friendly format.

Subscribes to EventBus, filters/maps events, and outputs to a dedicated
queue consumed by the WebSocket layer. The frontend never sees raw hardware events.
"""

import asyncio
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

_DEFAULT_QUEUE_MAXSIZE = 100

# ── Internal alcohol_state → UI kiosk_update mapping ──────────
_ALCOHOL_STATE_MAP: Dict[str, str] = {
    "connecting": "CONNECTING",
    "warming_up": "WARMING_UP",
    "ready": "READY_TO_BLOW",
    "breath_detected": "BLOWING",
    "sampling": "BLOWING",
    "analyzing": "ANALYZING",
    "flow_error": "FLOW_ERROR",
    "timeout": "TIMEOUT",
    "error": "ERROR",
}


class UIEventAdapter:
    """
    Sits between EventBus and WebSocket.

    - Subscribes to the EventBus.
    - Transforms internal events into UI-friendly payloads.
    - Exposes an output queue that WebSocket connections consume.
    """

    def __init__(self, event_bus, queue_maxsize: int = _DEFAULT_QUEUE_MAXSIZE):
        self._event_bus = event_bus
        self._queue_maxsize = queue_maxsize

        self._input_queue: Optional[asyncio.Queue] = None
        self._output_queues: set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Subscribe to EventBus and start the transform loop."""
        self._input_queue = await self._event_bus.subscribe()
        self._task = asyncio.create_task(self._transform_loop())
        logger.info("UIEventAdapter started")

    async def stop(self) -> None:
        """Stop and unsubscribe."""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._input_queue:
            await self._event_bus.unsubscribe(self._input_queue)
        logger.info("UIEventAdapter stopped")

    async def subscribe(self) -> asyncio.Queue:
        """
        Create a new output queue for a WebSocket connection.
        Each WS connection gets its own queue.
        """
        queue = asyncio.Queue(maxsize=self._queue_maxsize)
        async with self._lock:
            self._output_queues.add(queue)
        logger.debug("UIEventAdapter: new output subscriber (total=%d)", len(self._output_queues))
        return queue

    async def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Remove a WebSocket output queue on disconnect."""
        async with self._lock:
            self._output_queues.discard(queue)
        logger.debug("UIEventAdapter: removed output subscriber (total=%d)", len(self._output_queues))

    # ── Transform loop ────────────────────────────────────────

    async def _transform_loop(self) -> None:
        """Read from EventBus, transform, fan-out to output queues."""
        try:
            while True:
                event = await self._input_queue.get()
                ui_event = self._transform(event)
                if ui_event is not None:
                    await self._fan_out(ui_event)
        except asyncio.CancelledError:
            pass

    def _transform(self, event: dict) -> Optional[dict]:
        """
        Convert an internal event to a UI event.
        Returns None if the event should be filtered out (not sent to UI).
        """
        event_type = event.get("type")

        # ── alcohol_state → kiosk_update ──────────────────────
        if event_type == "alcohol_state":
            ui_state = _ALCOHOL_STATE_MAP.get(event.get("state"))
            if ui_state is None:
                return None
            ui = {
                "type": "kiosk_update",
                "state": ui_state,
            }
            if event.get("message"):
                ui["message"] = event["message"]
            if event.get("session_id"):
                ui["session_id"] = event["session_id"]
            return ui

        # ── alcohol_result → test_result ──────────────────────
        if event_type == "alcohol_result":
            ui = {
                "type": "test_result",
                "success": event.get("success", False),
                "value": event.get("value"),
                "status": event.get("status"),
            }
            if event.get("session_id"):
                ui["session_id"] = event["session_id"]
            return ui

        # ── kiosk_state → pass-through ────────────────────────
        if event_type == "kiosk_state":
            return dict(event)

        # ── device_status → pass-through ──────────────────────
        if event_type == "device_status":
            return dict(event)

        # ── session_started / session_ended → pass-through ────
        if event_type in ("session_started", "session_ended"):
            return dict(event)

        # ── fingerprint_result → pass-through ─────────────────
        if event_type == "fingerprint_result":
            return dict(event)

        # ── print events → pass-through ───────────────────────
        if event_type in ("print_complete", "print_error"):
            return dict(event)

        # ── photo_captured → pass-through ─────────────────────
        if event_type == "photo_captured":
            return dict(event)

        # ── Unknown events: filter out ────────────────────────
        logger.debug("UIEventAdapter: filtered out event type '%s'", event_type)
        return None

    async def _fan_out(self, ui_event: dict) -> None:
        """Push a UI event to all output queues, dropping oldest if full."""
        async with self._lock:
            queues = set(self._output_queues)

        for queue in queues:
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                queue.put_nowait(ui_event)
            except asyncio.QueueFull:
                pass
