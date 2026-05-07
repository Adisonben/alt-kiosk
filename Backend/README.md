# Alcohol Testing System Backend (v3.0.0)

A simplified, production-ready backend for industrial alcohol breathalyzer kiosks.

## 🚀 Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure**:
   Copy `app/.env.example` to `app/.env` and adjust your settings (e.g., serial port).

3. **Run the Server**:
   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## 📂 Project Structure

- `app/` - Core application package
  - `api/` - WebSocket router (`/ws`)
  - `core/` - EventBus & CommandBus (The communication backbone)
  - `hardware/` - Alcohol sensor protocol & parsing
  - `services/` - Background worker threads for hardware
  - `utils/` - Logging and serial connection helpers
  - `main.py` - FastAPI entry point
  - `config.py` - Pydantic settings management
- `_future/` - Archived modules (Camera, Fingerprint, Printer) for later use
- `scripts/` - Standalone test/utility scripts
- `logs/` - Runtime log files (Auto-generated)

## 🔌 WebSocket API

The frontend connects via `ws://HOST:8000/ws`.

### Commands (Frontend → Backend)
- `{"command": "START_TEST"}`: Begins the sensor warmup and measurement cycle.
- `{"command": "RESET"}`: Stops any active measurement.
- `{"command": "RESET_SENSOR"}`: Triggers the 10-minute hardware reset/cleaning cycle.

### Events (Backend → Frontend)
- `{"type": "ready"}`: WebSocket connection established.
- `{"type": "alcohol_state", "state": "...", "message": "..."}`: Real-time sensor status.
- `{"type": "alcohol_result", "value": 0.0, "status": "OK"}`: Final test results.

## 🛠️ Configuration

Settings are managed via `app/config.py` and can be overridden in `app/.env`:
- `ALCOHOL_PORT`: Path to sensor (e.g., `COM3` or `/dev/ttyUSB0`). Auto-detects if empty.
- `CORS_ORIGINS`: Allowed frontend URLs.
- `LOG_LEVEL`: `DEBUG`, `INFO`, `WARNING`, `ERROR`.