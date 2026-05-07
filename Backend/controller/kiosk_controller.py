"""
KioskController — State machine managing the kiosk test flow.

States:
    IDLE → WAIT_USER → READY_TO_BLOW → BLOWING → ANALYZING → RESULT → PRINT → CLEANUP → IDLE

Subscribes to EventBus for device events.
Dispatches commands to CommandBus.
Publishes kiosk_state events to EventBus.
Each state has a timeout guard to prevent lockups.
"""

import asyncio
import logging
from enum import Enum
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class KioskState(str, Enum):
    IDLE = "IDLE"
    WAIT_USER = "WAIT_USER"
    READY_TO_BLOW = "READY_TO_BLOW"
    BLOWING = "BLOWING"
    ANALYZING = "ANALYZING"
    RESULT = "RESULT"
    PRINT = "PRINT"
    CLEANUP = "CLEANUP"


# Timeout in seconds per state (None = no timeout)
STATE_TIMEOUTS: Dict[KioskState, Optional[float]] = {
    KioskState.IDLE: None,
    KioskState.WAIT_USER: 60.0,
    KioskState.READY_TO_BLOW: 30.0,
    KioskState.BLOWING: 15.0,
    KioskState.ANALYZING: 30.0,
    KioskState.RESULT: 30.0,
    KioskState.PRINT: 15.0,
    KioskState.CLEANUP: 10.0,
}

# Where to go when a state times out
TIMEOUT_TARGETS: Dict[KioskState, KioskState] = {
    KioskState.WAIT_USER: KioskState.IDLE,
    KioskState.READY_TO_BLOW: KioskState.IDLE,
    KioskState.BLOWING: KioskState.IDLE,
    KioskState.ANALYZING: KioskState.IDLE,
    KioskState.RESULT: KioskState.PRINT,
    KioskState.PRINT: KioskState.CLEANUP,
    KioskState.CLEANUP: KioskState.IDLE,
}


class KioskController:
    """
    Central kiosk state machine.

    - Subscribes to EventBus to react to device events.
    - Dispatches commands to CommandBus on state transitions.
    - Manages session via SessionManager.
    - Each state has a timeout guard.
    """

    def __init__(self, event_bus, command_bus, session_manager):
        self._event_bus = event_bus
        self._command_bus = command_bus
        self._session_manager = session_manager

        self._state = KioskState.IDLE
        self._event_queue: Optional[asyncio.Queue] = None
        self._listener_task: Optional[asyncio.Task] = None
        self._timeout_task: Optional[asyncio.Task] = None

        # Store last alcohol result for PRINT phase
        self._last_result: Optional[dict] = None

    @property
    def state(self) -> KioskState:
        return self._state

    # ── Lifecycle ─────────────────────────────────────────────

    async def start(self) -> None:
        """Subscribe to event bus and start processing events."""
        self._event_queue = await self._event_bus.subscribe()
        self._listener_task = asyncio.create_task(self._event_loop())
        logger.info("KioskController started (state=%s)", self._state.value)

    async def stop(self) -> None:
        """Stop event processing and clean up."""
        self._cancel_timeout()
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self._event_queue:
            await self._event_bus.unsubscribe(self._event_queue)
        logger.info("KioskController stopped")

    # ── External command entry point ──────────────────────────

    async def handle_command(self, command: str) -> None:
        """
        Handle a command from the WebSocket (e.g. START_TEST, RESET).
        """
        logger.info("KioskController: received command %s (state=%s)", command, self._state.value)

        if command == "START_TEST":
            if self._state == KioskState.IDLE:
                await self._transition(KioskState.WAIT_USER)
            else:
                logger.warning("START_TEST ignored — not in IDLE (current=%s)", self._state.value)

        elif command == "RESET":
            await self._reset()

    # ── Event loop ────────────────────────────────────────────

    async def _event_loop(self) -> None:
        """Main loop: consume events from EventBus and react."""
        try:
            while True:
                event = await self._event_queue.get()
                await self._handle_event(event)
        except asyncio.CancelledError:
            pass

    async def _handle_event(self, event: dict) -> None:
        """Route an event based on current state and event type."""
        event_type = event.get("type")

        # ── WAIT_USER: waiting for user identification ────────
        if self._state == KioskState.WAIT_USER:
            if event_type == "fingerprint_result" and event.get("success"):
                await self._transition(KioskState.READY_TO_BLOW)

        # ── READY_TO_BLOW: sensor warming up / standby ────────
        elif self._state == KioskState.READY_TO_BLOW:
            if event_type == "alcohol_state":
                alcohol_state = event.get("state")
                if alcohol_state == "breath_detected":
                    await self._transition(KioskState.BLOWING)

        # ── BLOWING: user is blowing ──────────────────────────
        elif self._state == KioskState.BLOWING:
            if event_type == "alcohol_state":
                alcohol_state = event.get("state")
                if alcohol_state == "analyzing":
                    await self._transition(KioskState.ANALYZING)
                elif alcohol_state == "flow_error":
                    await self._transition(KioskState.READY_TO_BLOW)

        # ── ANALYZING: waiting for result ─────────────────────
        elif self._state == KioskState.ANALYZING:
            if event_type == "alcohol_result":
                self._last_result = event
                self._session_manager.update_session(
                    alcohol_value=event.get("value"),
                    alcohol_status=event.get("status"),
                )
                await self._transition(KioskState.RESULT)

        # ── RESULT: displaying result ─────────────────────────
        elif self._state == KioskState.RESULT:
            pass  # Timeout will auto-advance to PRINT

        # ── PRINT: printing receipt ───────────────────────────
        elif self._state == KioskState.PRINT:
            if event_type in ("print_complete", "print_error"):
                await self._transition(KioskState.CLEANUP)

        # ── CLEANUP: cleaning cycle ───────────────────────────
        elif self._state == KioskState.CLEANUP:
            pass  # Timeout will auto-advance to IDLE

    # ── State transitions ─────────────────────────────────────

    async def _transition(self, new_state: KioskState) -> None:
        """
        Transition to a new state.
        - Cancel existing timeout.
        - Execute on-enter actions (dispatch commands).
        - Publish kiosk_state event.
        - Start new timeout if applicable.
        """
        old_state = self._state
        self._state = new_state
        self._cancel_timeout()

        logger.info("KioskController: %s → %s", old_state.value, new_state.value)

        session_id = self._session_manager.current_session_id

        # ── On-enter actions ──────────────────────────────────
        if new_state == KioskState.WAIT_USER:
            session_id = await self._session_manager.create_session()

        elif new_state == KioskState.READY_TO_BLOW:
            await self._command_bus.dispatch({
                "command": "START_ALCOHOL",
                "session_id": session_id,
                "params": {},
            })

        elif new_state == KioskState.PRINT:
            if self._last_result:
                session_data = self._session_manager.current_session_data
                await self._command_bus.dispatch({
                    "command": "PRINT_RECEIPT",
                    "session_id": session_id,
                    "params": {
                        "user_name": session_data.get("user_name", ""),
                        "user_id": session_data.get("user_id", ""),
                        "device_id": "PAO-L-001",
                        "value": self._last_result.get("value", 0.0),
                        "status": "PASS" if self._last_result.get("status") == "OK" else "FAIL",
                    },
                })

        elif new_state == KioskState.CLEANUP:
            await self._command_bus.dispatch({
                "command": "STOP_ALCOHOL",
                "session_id": session_id,
                "params": {},
            })

        elif new_state == KioskState.IDLE:
            await self._session_manager.end_session()
            self._last_result = None

        # ── Publish kiosk_state event ─────────────────────────
        event = {"type": "kiosk_state", "state": new_state.value}
        if session_id:
            event["session_id"] = session_id
        await self._event_bus.publish(event)

        # ── Start timeout for new state ───────────────────────
        timeout = STATE_TIMEOUTS.get(new_state)
        if timeout is not None:
            self._timeout_task = asyncio.create_task(
                self._state_timeout(new_state, timeout)
            )

    async def _state_timeout(self, state: KioskState, timeout: float) -> None:
        """Wait for timeout, then transition to the timeout target state."""
        try:
            await asyncio.sleep(timeout)
            # Only transition if we're still in the same state
            if self._state == state:
                target = TIMEOUT_TARGETS.get(state, KioskState.IDLE)
                logger.warning(
                    "KioskController: timeout in %s (%.0fs) → %s",
                    state.value, timeout, target.value,
                )
                await self._transition(target)
        except asyncio.CancelledError:
            pass

    def _cancel_timeout(self) -> None:
        """Cancel the current timeout task if active."""
        if self._timeout_task and not self._timeout_task.done():
            self._timeout_task.cancel()
            self._timeout_task = None

    # ── Reset ─────────────────────────────────────────────────

    async def _reset(self) -> None:
        """Force-reset to IDLE from any state."""
        logger.info("KioskController: RESET from %s", self._state.value)
        session_id = self._session_manager.current_session_id
        if session_id:
            await self._command_bus.dispatch({
                "command": "STOP_ALCOHOL",
                "session_id": session_id,
                "params": {},
            })
        await self._transition(KioskState.IDLE)
