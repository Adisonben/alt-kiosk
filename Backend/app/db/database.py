"""
DatabaseManager — async context-manager wrapper around aiosqlite.

Usage:
    async with DatabaseManager(db_path) as db:
        async with db.connection() as conn:
            await conn.execute(...)

All connections use WAL mode and foreign key enforcement (set in migrations).
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import aiosqlite

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Lightweight async database connection manager.

    A single instance is created at startup and shared across services
    via app.state. Each service method opens its own short-lived connection.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[aiosqlite.Connection]:
        """
        Open a connection for one unit of work.
        Automatically closes when the context exits.
        """
        async with aiosqlite.connect(self._db_path) as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys=ON")
            try:
                yield conn
            except Exception:
                await conn.rollback()
                raise
