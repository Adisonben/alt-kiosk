"""
SessionManager — Manages unique session IDs for each kiosk test cycle.

Each user interaction (fingerprint → blow → result → print) is a session.
All events and commands carry the session_id to prevent cross-test mixing.
"""

import uuid
import time
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Creates, tracks, and ends kiosk test sessions.

    A session starts when the kiosk transitions from IDLE → WAIT_USER
    and ends when it returns to IDLE (via CLEANUP).
    """

    def __init__(self, event_bus):
        self._event_bus = event_bus
        self._current_session_id: Optional[str] = None
        self._current_session_data: Dict[str, Any] = {}

    @property
    def current_session_id(self) -> Optional[str]:
        """Return the active session ID, or None if no session is active."""
        return self._current_session_id

    @property
    def current_session_data(self) -> Dict[str, Any]:
        """Return metadata dict for the active session."""
        return dict(self._current_session_data)

    async def create_session(self) -> str:
        """
        Start a new session. Ends any existing session first.
        Returns the new session_id (UUID4 hex).
        """
        if self._current_session_id is not None:
            await self.end_session()

        session_id = uuid.uuid4().hex[:12]
        self._current_session_id = session_id
        self._current_session_data = {
            "session_id": session_id,
            "start_time": time.time(),
            "user_id": None,
            "alcohol_value": None,
            "alcohol_status": None,
        }

        await self._event_bus.publish({
            "type": "session_started",
            "session_id": session_id,
        })
        logger.info("Session created: %s", session_id)
        return session_id

    async def end_session(self) -> None:
        """End the current session and publish session_ended event."""
        if self._current_session_id is None:
            return

        session_id = self._current_session_id
        start_time = self._current_session_data.get("start_time", time.time())
        duration = round(time.time() - start_time, 2)

        await self._event_bus.publish({
            "type": "session_ended",
            "session_id": session_id,
            "duration": duration,
        })
        logger.info("Session ended: %s (duration=%.1fs)", session_id, duration)

        self._current_session_id = None
        self._current_session_data = {}

    def update_session(self, **kwargs) -> None:
        """Update metadata on the current session (e.g. user_id, alcohol_value)."""
        self._current_session_data.update(kwargs)
