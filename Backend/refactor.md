You are a senior Python backend engineer specializing in IoT and kiosk systems.

I have an existing Python module that controls an alcohol breath sensor using serial communication. 
The current implementation was designed for a Kivy UI application and uses threads + asyncio.Queue to send events to the UI.

I am now migrating the system to a production kiosk architecture using:

- Raspberry Pi
- Python backend
- FastAPI
- WebSocket communication
- Next.js frontend

The backend must follow a clean architecture suitable for an industrial kiosk device.

Your task is to refactor the code into a modular backend architecture with the following structure:

backend/
  app/
    main.py
    api/
      websocket.py
    controller/
      kiosk_controller.py
    services/
      alcohol_service.py
    core/
      event_bus.py
      state_machine.py
    device/
      alcohol_protocol.py
    utils/
      logger.py

Architecture requirements:

1. Device Layer
- alcohol_service.py handles serial communication with the alcohol sensor.
- It should parse device messages like:
  $WAIT
  $STANBY
  $TRIGGER
  $BREATH
  $FLOW,ERR
  $CALIBRATION
  $RESULT,0.021-OK
- Convert these into events.

2. Event Bus
- Implement a global asyncio-based event bus using asyncio.Queue.
- Services publish events to the bus.
- Controller and WebSocket consumers subscribe to the bus.

Example event format:

{
  "type": "alcohol_state",
  "state": "READY"
}

or

{
  "type": "alcohol_result",
  "value": 0.021,
  "status": "OK"
}

3. Kiosk Controller
- Implement a state machine that manages the kiosk flow:

IDLE
WAIT_USER
READY_TO_BLOW
BLOWING
ANALYZING
RESULT
PRINT
DONE

- The controller listens to events from the event bus and updates kiosk state.
- It publishes kiosk state updates back to the event bus.

Example:

{
  "type": "kiosk_state",
  "state": "READY_TO_BLOW"
}

4. WebSocket API
- Implement a FastAPI WebSocket endpoint `/ws`.
- The WebSocket should subscribe to the event bus and stream events to the frontend.
- The frontend can send commands like:

START_TEST
RESET

5. Concurrency
- Alcohol sensor reading should run in a separate thread.
- Use asyncio-safe communication with the event bus.

6. Reliability
Implement production-ready features:
- serial auto reconnect
- graceful shutdown
- logging
- watchdog for sensor thread

7. Code Quality
- Use clear separation of concerns.
- Avoid tight coupling between device logic and API.
- Follow async best practices.

Below is the existing alcohol sensor code that must be refactored into the new architecture:

[PASTE CURRENT ALCOHOL CODE HERE]

Generate the refactored code for all necessary modules.
Explain briefly how the modules interact.