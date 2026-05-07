"""
EventBus — Async fan-out pub/sub for device → system event flow.

Each subscriber gets its own asyncio.Queue (maxsize=100).
When a queue is full, the oldest event is dropped to prevent backpressure.
Thread-safe publishing via publish_threadsafe() for device threads.
"""

import asyncio
import logging
from typing import Dict, Optional, Set

logger = logging.getLogger(__name__)

# Default max size for subscriber queues
_DEFAULT_QUEUE_MAXSIZE = 100


class EventBus:
    """
    Fan-out event bus.

    - Services publish events (from threads or async code).
    - Controller, WebSocket subscribe and each get their own queue.
    - Subscriber queues are bounded; oldest events are dropped when full.
    """

    def __init__(self, queue_maxsize: int = _DEFAULT_QUEUE_MAXSIZE):
        self._subscribers: Set[asyncio.Queue] = set()
        self._queue_maxsize = queue_maxsize
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue:
        """Create and return a new subscriber queue."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=self._queue_maxsize)
        async with self._lock:
            self._subscribers.add(queue)
        logger.debug("EventBus: new subscriber (total=%d)", len(self._subscribers))
        return queue

    async def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Remove a subscriber queue. Prevents memory leaks on disconnect."""
        async with self._lock:
            self._subscribers.discard(queue)
        logger.debug("EventBus: removed subscriber (total=%d)", len(self._subscribers))

    async def publish(self, event: dict) -> None:
        """
        Publish an event to all subscriber queues.
        If a queue is full, drop the oldest event before pushing the new one.
        """
        async with self._lock:
            subscribers = set(self._subscribers)

        for queue in subscribers:
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                logger.warning("EventBus: subscriber queue full, dropped oldest event")
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # Should not happen after dropping, but guard anyway
                logger.error("EventBus: failed to enqueue event after drop")

    def publish_threadsafe(self, event: dict, loop: asyncio.AbstractEventLoop) -> None:
        """
        Publish an event from a non-async thread (e.g. serial reader thread).
        Schedules the publish coroutine on the given event loop.
        """
        asyncio.run_coroutine_threadsafe(self.publish(event), loop)

    @property
    def subscriber_count(self) -> int:
        """Current number of active subscribers."""
        return len(self._subscribers)
