"""
CommandBus — Async fan-out pub/sub for system → device command flow.

Services subscribe to specific command types they handle.
The KioskController dispatches commands; matching subscribers receive them.
Uses the same bounded-queue + drop-oldest pattern as EventBus.
"""

import asyncio
import logging
from typing import Dict, Optional, Set, FrozenSet

logger = logging.getLogger(__name__)

_DEFAULT_QUEUE_MAXSIZE = 100


class _Subscriber:
    """Internal: a subscriber with its queue and the command types it listens to."""

    __slots__ = ("queue", "filter_types")

    def __init__(self, queue: asyncio.Queue, filter_types: Optional[FrozenSet[str]]):
        self.queue = queue
        self.filter_types = filter_types  # None means accept all


class CommandBus:
    """
    Fan-out command bus.

    - Controller dispatches commands (e.g. START_ALCOHOL, PRINT_RECEIPT).
    - Services subscribe with an optional filter on command types.
    - Each subscriber gets its own bounded queue.
    """

    def __init__(self, queue_maxsize: int = _DEFAULT_QUEUE_MAXSIZE):
        self._subscribers: Set[_Subscriber] = set()
        self._queue_maxsize = queue_maxsize
        self._lock = asyncio.Lock()

    async def subscribe(self, filter_types: Optional[Set[str]] = None) -> asyncio.Queue:
        """
        Create and return a new subscriber queue.

        Args:
            filter_types: Set of command type strings this subscriber handles.
                          Pass None to receive all commands.
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=self._queue_maxsize)
        frozen = frozenset(filter_types) if filter_types else None
        sub = _Subscriber(queue=queue, filter_types=frozen)
        async with self._lock:
            self._subscribers.add(sub)
        logger.debug(
            "CommandBus: new subscriber filter=%s (total=%d)",
            frozen,
            len(self._subscribers),
        )
        return queue

    async def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Remove a subscriber by its queue reference."""
        async with self._lock:
            self._subscribers = {
                s for s in self._subscribers if s.queue is not queue
            }
        logger.debug("CommandBus: removed subscriber (total=%d)", len(self._subscribers))

    async def dispatch(self, command: dict) -> None:
        """
        Dispatch a command to all matching subscribers.

        Expected command format:
        {
            "command": "START_ALCOHOL",
            "session_id": "abc123",
            "params": { ... }
        }

        If a subscriber's queue is full, the oldest command is dropped.
        """
        cmd_type = command.get("command")

        async with self._lock:
            subscribers = set(self._subscribers)

        for sub in subscribers:
            # Skip if subscriber has a filter and this command doesn't match
            if sub.filter_types is not None and cmd_type not in sub.filter_types:
                continue

            if sub.queue.full():
                try:
                    sub.queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                logger.warning(
                    "CommandBus: subscriber queue full for %s, dropped oldest",
                    cmd_type,
                )
            try:
                sub.queue.put_nowait(command)
            except asyncio.QueueFull:
                logger.error("CommandBus: failed to enqueue command %s after drop", cmd_type)

    @property
    def subscriber_count(self) -> int:
        """Current number of active subscribers."""
        return len(self._subscribers)
