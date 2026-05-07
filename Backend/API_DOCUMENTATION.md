# API Documentation

## Swagger/OpenAPI Documentation

This API includes automatic Swagger/OpenAPI documentation. When running the main application:

- **Swagger UI**: `http://localhost:8000/docs` - Interactive API documentation
- **ReDoc**: `http://localhost:8000/redoc` - Alternative documentation view
- **OpenAPI Schema**: `http://localhost:8000/openapi.json` - Raw OpenAPI specification

### Running the API Server

```bash
# Navigate to the services directory
cd Backend

# Run the main FastAPI application
python main.py
```

The server will start on `http://localhost:8000` with automatic API documentation enabled.

## Alcohol Service (`/alcohol`)

### GET `/alcohol/status`
Check if a USB serial device is connected.

**Response:**
```json
{
  "available": true,
  "port": "/dev/ttyUSB0",
  "description": "USB Serial Port"
}
```
or
```json
{
  "available": false,
  "reason": "pyserial not installed"
}
```

### POST `/alcohol/start`
Start a measurement cycle. Returns Server-Sent Events with status updates and the final result.

**Response:** Server-Sent Events (`text/event-stream`)

**Event Types:**
- `status` - Status updates during the measurement process
- `result` - Final measurement result

**Status Events:**
```json
{
  "type": "status",
  "state": "connecting|warming_up|ready|breath_detected|sampling|analyzing|flow_error|timeout|error",
  "message": "Status message in Thai/English"
}
```

**Result Events:**
```json
{
  "type": "result",
  "success": true,
  "value": 0.05,
  "status": "OK|HIGH"
}
```

### POST `/alcohol/stop`
Signal the background worker to stop.

**Response:**
```json
{
  "stopped": true
}
```

---

## Fingerprint Service (`/fingerprint`)

### GET `/fingerprint/status`
Check if the finger_scan binary exists.

**Response:**
```json
{
  "available": true,
  "binary_path": "/path/to/bin/finger_scan"
}
```

### POST `/fingerprint/scan`
Run the finger_scan binary and return the fingerprint template as base64.
Blocks until the scan completes or times out.

**Response:**
```json
{
  "success": true,
  "data": "base64-encoded-fingerprint-template",
  "reason": null
}
```
or
```json
{
  "success": false,
  "data": null,
  "reason": "timeout|error|binary_not_found"
}
```

### POST `/fingerprint/compare`
Compare two base64-encoded fingerprint templates.

**Request Body:**
```json
{
  "data1": "base64-fingerprint-template-1",
  "data2": "base64-fingerprint-template-2"
}
```

**Response:**
```json
{
  "match": true,
  "message": "Match|No Match|Error message"
}
```

**Error Response (400):**
```json
{
  "detail": "Invalid template size; each must decode to 400 bytes"
}
```

---

## Printer Service (`/printer`)

### POST `/printer/print`
Print an alcohol test result receipt via USB ESC/POS printer.

**Request Body:**
```json
{
  "user_name": "John Doe",
  "user_id": "123456",
  "device_id": "ALC001",
  "status": "PASS|FAIL|ERROR",
  "value": 0.05
}
```

**Response:**
```json
{
  "success": true
}
```

**Error Responses:**
- `503` - python-escpos not installed or printer error
```json
{
  "detail": "python-escpos not installed"
}
```
```json
{
  "detail": "Printer error message"
}
```

---

## Error Codes

- `400` - Bad Request (invalid input data)
- `503` - Service Unavailable (missing dependencies, hardware not found)
- `500` - Internal Server Error (unexpected failures)

---

## Dependencies

### Alcohol Service
- `pyserial` - USB serial communication

### Fingerprint Service  
- `finger_scan` binary - Hardware fingerprint scanner
- `match_template` binary - Template matching utility

### Printer Service
- `python-escpos` - ESC/POS printer library
- `Pillow` (PIL) - Image processing for logo printing
- USB ESC/POS printer (Vendor ID: 0x04b8, Product ID: 0x0E28)

---

## Usage Examples

### Alcohol Measurement Flow
```javascript
// Start measurement
const eventSource = new EventSource('/alcohol/start');

eventSource.onmessage = function(event) {
  const data = JSON.parse(event.data);
  
  if (data.type === 'status') {
    console.log('Status:', data.message);
  } else if (data.type === 'result') {
    console.log('Result:', data.value, data.status);
    eventSource.close();
  }
};

// Stop measurement if needed
fetch('/alcohol/stop', { method: 'POST' });
```

### Fingerprint Scan & Compare
```javascript
// Scan fingerprint
const scanResponse = await fetch('/fingerprint/scan', { method: 'POST' });
const scanData = await scanResponse.json();

if (scanData.success) {
  // Compare with stored template
  const compareResponse = await fetch('/fingerprint/compare', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      data1: scanData.data,
      data2: storedTemplate
    })
  });
  const compareResult = await compareResponse.json();
  console.log('Match:', compareResult.match);
}
```

### Print Test Result
```javascript
const printResponse = await fetch('/printer/print', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_name: 'John Doe',
    user_id: '123456',
    device_id: 'ALC001',
    status: 'PASS',
    value: 0.05
  })
});
const printResult = await printResponse.json();
console.log('Printed:', printResult.success);
```
