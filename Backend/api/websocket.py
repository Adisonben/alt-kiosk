"""
WebSocket API — /ws endpoint (slim).

- send_loop: forwards EventBus events directly to the client.
- receive_loop: accepts commands and dispatches to CommandBus.
- Heartbeat: server sends ping every 15s.
- Supports multiple concurrent connections.
"""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()

HEARTBEAT_INTERVAL = 15.0  # seconds between pings

# ── Command mapping: frontend command → CommandBus command ────
_COMMAND_MAP = {
    "START_TEST": "START_ALCOHOL",
    "RESET": "STOP_ALCOHOL",
    "RESET_SENSOR": "RESET_SENSOR",
}


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """
    Main WebSocket endpoint.
    Subscribes directly to EventBus; dispatches commands to CommandBus.
    """
    await ws.accept()

    event_bus = ws.app.state.event_bus
    command_bus = ws.app.state.command_bus

    # Subscribe to EventBus
    event_queue: asyncio.Queue = await event_bus.subscribe()

    logger.info("WebSocket: client connected")

    # Send ready signal
    await ws.send_json({"type": "ready"})

    try:
        send_task = asyncio.create_task(_send_loop(ws, event_queue))
        receive_task = asyncio.create_task(_receive_loop(ws, command_bus))
        heartbeat_task = asyncio.create_task(_heartbeat_loop(ws))

        done, pending = await asyncio.wait(
            [send_task, receive_task, heartbeat_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    except Exception as exc:
        logger.exception("WebSocket: unexpected error — %s", exc)
    finally:
        await event_bus.unsubscribe(event_queue)
        logger.info("WebSocket: client disconnected, subscriber cleaned up")


async def _send_loop(ws: WebSocket, event_queue: asyncio.Queue) -> None:
    """Forward EventBus events directly to the WebSocket client."""
    try:
        while True:
            event = await event_queue.get()
            await ws.send_json(event)
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    except Exception as exc:
        logger.warning("WebSocket send_loop error: %s", exc)


async def _receive_loop(ws: WebSocket, command_bus) -> None:
    """Accept commands from the frontend and dispatch to CommandBus."""
    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("WebSocket: invalid JSON received: %s", raw[:200])
                continue

            command = data.get("command")
            if not command:
                logger.debug("WebSocket: message without 'command' key: %s", data)
                continue

            # Heartbeat pong — just ignore
            if command == "pong":
                continue

            # Map frontend command to backend command
            backend_cmd = _COMMAND_MAP.get(command)
            if backend_cmd:
                await command_bus.dispatch({
                    "command": backend_cmd,
                    "session_id": data.get("session_id"),
                    "params": data.get("params", {}),
                })
                logger.info("WebSocket: dispatched %s → %s", command, backend_cmd)
            else:
                logger.warning("WebSocket: unknown command '%s'", command)

    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    except Exception as exc:
        logger.warning("WebSocket receive_loop error: %s", exc)


async def _heartbeat_loop(ws: WebSocket) -> None:
    """Server-initiated heartbeat. Sends ping every HEARTBEAT_INTERVAL seconds."""
    try:
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            try:
                await ws.send_json({"type": "ping"})
            except Exception:
                break
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
