# Pao-L Backend — Architecture Manual

Production-grade kiosk backend for alcohol breath testing on Raspberry Pi.

---

## Stack

- **Runtime**: Python 3.11+ on Raspberry Pi
- **Framework**: FastAPI + Uvicorn
- **Real-time**: WebSocket (`/ws`)
- **Devices**: Alcohol sensor (serial), Fingerprint scanner (subprocess), Printer (ESC/POS USB), Camera (Picamera2)

---

## Folder Structure

```
Backend/
  main.py                    ← Entry point, FastAPI app, lifecycle
  api/
    websocket.py             ← /ws endpoint, heartbeat, dual send/receive loops
    rest.py                  ← Health, device status, fingerprint, printer REST
  controller/
    kiosk_controller.py      ← State machine (IDLE → … → CLEANUP → IDLE)
    session_manager.py       ← Session lifecycle, unique session_id per test
  services/
    alcohol_service.py       ← Sensor thread, serial read, publishes events
    fingerprint_service.py   ← Scan/compare via subprocess
    printer_service.py       ← ESC/POS receipt printing
    camera_service.py        ← Picamera2 snapshot capture
  core/
    event_bus.py             ← Fan-out pub/sub (device → system → UI)
    command_bus.py           ← Fan-out pub/sub (system → device)
    device_manager.py        ← Start/stop/restart/health for all devices
    watchdog.py              ← Periodic health checks, auto-restart
  device/
    alcohol_protocol.py      ← Serial constants, parse_state(), parse_result()
    fingerprint_protocol.py  ← Binary paths, raw↔base64 helpers
    printer_protocol.py      ← Vendor/product IDs, asset paths
  adapters/
    ui_event_adapter.py      ← Transforms internal events → UI-friendly format
  utils/
    logger.py                ← Structured logging (JSON + console)
    serial_utils.py          ← auto_detect_port(), open_with_retry()
  bin/                       ← Test scripts (unchanged)
  sdk/                       ← Fingerprint SDK (unchanged)
  assets/                    ← Logo, images (unchanged)
```

---

## Architecture Overview

```
Hardware → Services → EventBus → KioskController → CommandBus → Services
                         ↓                              ↓
                    UI Adapter                      (executes commands)
                         ↓
                    WebSocket /ws → Frontend (Next.js)
                         ↑
                    Frontend commands (START_TEST, RESET)
```

### Buses

| Bus | Direction | Purpose |
|-----|-----------|---------|
| **EventBus** | device → system → UI | Fan-out events from hardware to all subscribers |
| **CommandBus** | system → device | Dispatches commands from controller to services |

### EventBus Details

- Each subscriber gets its own `asyncio.Queue(maxsize=100)`.
- When a queue is full, the **oldest event is dropped**.
- Thread-safe publishing via `publish_threadsafe(event, loop)` for device threads.
- Call `unsubscribe(queue)` on disconnect to prevent memory leaks.

---

## Kiosk State Machine

```
IDLE → WAIT_USER → READY_TO_BLOW → BLOWING → ANALYZING → RESULT → PRINT → CLEANUP → IDLE
```

### Timeout Guards

| State | Timeout | Action |
|-------|---------|--------|
| WAIT_USER | 60s | → IDLE |
| READY_TO_BLOW | 30s | → IDLE |
| BLOWING | 15s | → IDLE |
| ANALYZING | 30s | → IDLE |
| RESULT | 30s | → PRINT |
| PRINT | 15s | → CLEANUP |
| CLEANUP | 10s | → IDLE |

---

## Session Management

- Each test creates a unique `session_id` (UUID4).
- All events and commands carry `session_id` during an active session.
- Session starts on `IDLE → WAIT_USER`, ends on `CLEANUP → IDLE`.

---

## Event Types

| Event | Source | Payload |
|-------|--------|---------|
| `alcohol_state` | AlcoholService | `{state, session_id}` |
| `alcohol_result` | AlcoholService | `{value, status, session_id}` |
| `fingerprint_result` | FingerprintService | `{success, data, session_id}` |
| `print_complete` | PrinterService | `{success, session_id}` |
| `photo_captured` | CameraService | `{path, session_id}` |
| `kiosk_state` | KioskController | `{state, session_id}` |
| `device_status` | DeviceManager/Watchdog | `{device, status}` |
| `session_started` | SessionManager | `{session_id}` |
| `session_ended` | SessionManager | `{session_id, duration}` |

---

## Command Types

| Command | Target | Params |
|---------|--------|--------|
| `START_TEST` | KioskController | — |
| `RESET` | KioskController | — |
| `START_ALCOHOL` | AlcoholService | `{session_id}` |
| `STOP_ALCOHOL` | AlcoholService | `{session_id}` |
| `PRINT_RECEIPT` | PrinterService | `{session_id, user_name, value, status}` |
| `CAPTURE_PHOTO` | CameraService | `{session_id, filepath}` |

---

## Device Status

Standardized status values: `connected`, `disconnected`, `error`, `recovering`.

```json
{
  "type": "device_status",
  "device": "alcohol",
  "status": "connected"
}
```

---

## WebSocket `/ws`

- Two concurrent loops per connection: **send_loop** (events → client) and **receive_loop** (client → commands).
- Heartbeat: server `ping` every 15s, expects `pong` within 5s.
- Supports multiple concurrent connections.
- Clean subscriber cleanup on disconnect.

### Frontend → Backend commands

```json
{"command": "START_TEST"}
{"command": "RESET"}
```

### Backend → Frontend events

```json
{"type": "kiosk_state", "state": "READY_TO_BLOW", "session_id": "abc123"}
{"type": "test_result", "value": 0.021, "status": "OK", "session_id": "abc123"}
```

---

## REST Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | App health + device statuses |
| GET | `/devices` | All device statuses |
| POST | `/fingerprint/scan` | Run fingerprint scan |
| POST | `/fingerprint/compare` | Compare two templates |
| POST | `/printer/print` | Print receipt (fallback) |

---

## Running

```bash
cd Backend
pip install -r requirements.txt
python main.py
```

Server starts on `http://0.0.0.0:8000`. WebSocket at `ws://0.0.0.0:8000/ws`.

---

## Raspberry Pi Deployment

- **systemd**: Create `pao-l-backend.service` with `Restart=always`.
- **Serial permissions**: Add user to `dialout` group.
- **Udev rules**: Symlink alcohol sensor to `/dev/alcohol_sensor`.
- **Logs**: `/var/log/pao-l/` with logrotate.
- **Auto-start**: `systemctl enable pao-l-backend`.
- **Graceful shutdown**: `SIGTERM` → `DeviceManager.stop_all()`.
