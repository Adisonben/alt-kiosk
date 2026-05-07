# Alcohol Testing System — Backend Integration Guide

This document explains how to connect the React/Next.js frontend to the Python backend via WebSockets.

## 🔗 Connection Details

- **Protocol**: WebSocket (WS)
- **Endpoint**: `ws://[HOST]:8000/ws`
- **Port**: `8000` (Default, configurable in `.env`)

---

## 🛰️ Communication Flow

1. **Connect**: Frontend opens a WebSocket connection.
2. **Handshake**: Backend sends `{"type": "ready"}` to confirm the connection is active.
3. **Heartbeat**: Backend sends `{"type": "ping"}` every 15 seconds. Frontend should ignore this or respond with `{"command": "pong"}` (optional).
4. **Commands**: Frontend sends JSON commands to trigger hardware actions.
5. **Events**: Backend streams real-time status and results back to the frontend.

---

## 📤 Commands (Frontend → Backend)

All messages sent to the backend are strictly validated using a Pydantic schema. They **must** follow this exact format:
```json
{
  "command": "COMMAND_NAME",          // REQUIRED: The exact command string
  "session_id": "optional_unique_id", // OPTIONAL: String for session tracking
  "params": {}                        // OPTIONAL: Dictionary of arguments
}
```
*Note: Any payload missing the `command` key or using an incorrect structure (like `{"type": "CMD"}`) will be rejected with a ValidationError and safely ignored by the backend.*


| Command | Action | Description |
|---------|--------|-------------|
| `START_TEST` | **Start Alcohol Test** | Triggers sensor warmup. Use this when the user is ready to blow. |
| `RESET` | **Stop/Reset Flow** | Stops the current measurement and turns off the sensor thread. |
| `RESET_SENSOR` | **Sensor Cleaning** | Triggers the 10-minute hardware cleaning/calibration cycle. |
| `VERIFY_FINGERPRINT` | **Verify Fingerprint** | Triggers the fingerprint scanner and compares it against provided templates. |

#### Example: VERIFY_FINGERPRINT Command
```json
{
  "command": "VERIFY_FINGERPRINT",
  "session_id": "optional_unique_id",
  "params": {
    "target_templates": [
      "<base64_string_finger_1>",
      "<base64_string_finger_2>"
    ]
  }
}
```

---

## 📥 Events (Backend → Frontend)

### 1. Ready Event
Sent immediately after connection.
```json
{ "type": "ready" }
```

### 2. Alcohol State Event
Sent whenever the sensor status changes.
```json
{
  "type": "alcohol_state",
  "state": "warming_up",
  "message": "กำลังอุ่นเครื่อง... / Warming up...",
  "session_id": "..."
}
```

**Common States:**
- `connecting`: Opening serial port.
- `warming_up`: Sensor is heating up.
- `ready`: Ready for the user to blow.
- `breath_detected`: Initial air flow detected.
- `sampling`: Actively sampling the breath.
- `analyzing`: Calculating the alcohol level.
- `flow_error`: Incorrect blowing technique (too soft or interrupted).
- `timeout`: User took too long to blow.
- `error`: Hardware or connection failure.

### 3. Alcohol Result Event
Sent once the test is complete.
```json
{
  "type": "alcohol_result",
  "success": true,
  "value": 0.021,
  "status": "OK", 
  "session_id": "..."
}
```
- `status`: `OK` (Safe) or `HIGH` (Above threshold).

### 4. Reset Result Event
Sent after a `RESET_SENSOR` command finishes (after 10 mins).
```json
{ "type": "reset_result", "success": true }
```

### 5. Fingerprint State Event
Sent to update the status of the fingerprint scanner.
```json
{
  "type": "fingerprint_state",
  "state": "scanning",
  "message": "กำลังสแกนลายนิ้วมือ... / Scanning fingerprint...",
  "session_id": "..."
}
```

### 6. Fingerprint Result Event
Sent after the fingerprint scanning and matching process is complete.
```json
{
  "type": "fingerprint_result",
  "success": true,
  "match": true,
  "message": "Match successful",
  "session_id": "..."
}
```
- `success`: `true` if the scanner ran without hardware errors.
- `match`: `true` if the scanned fingerprint matched any of the provided `target_templates`.

---

## 💡 React Integration Example

```javascript
const socket = new WebSocket('ws://localhost:8000/ws');

socket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch (data.type) {
    case 'ready':
      console.log('Connected to backend');
      break;
      
    case 'alcohol_state':
      console.log('Status:', data.message); // Show this to user
      if (data.state === 'ready') {
          // Play "Please Blow" audio
      }
      break;
      
    case 'alcohol_result':
      console.log('Result:', data.value); // Navigate to result page
      break;
  }
};

// Recommended: Create a wrapper to ensure payload standardization
const sendCommand = (command, params = {}, sessionId = null) => {
  if (socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({
      command: command,
      session_id: sessionId,
      params: params
    }));
  }
};

// Start the test
const startTest = () => {
  sendCommand('START_TEST');
};
```

## 🛠️ Error Handling
- If the WebSocket closes unexpectedly, the frontend should attempt to reconnect with an exponential backoff.
- If `alcohol_state` is `error`, display a "Device Error" message and provide a "Retry" button that sends the `RESET` command before `START_TEST`.

---

## ⚙️ Fingerprint Binaries Setup
For the fingerprint scanner to work, you must place the compiled C binaries in the `Backend/scripts/` directory:

1. `Backend/scripts/finger_scan`
2. `Backend/scripts/match_template`

Ensure that these binaries have execution permissions (`chmod +x`). The backend uses `sudo` to execute them, so the user running the FastAPI app must have passwordless sudo privileges for these specific binaries, or the app must be run with the necessary permissions.
