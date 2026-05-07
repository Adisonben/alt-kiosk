#!/usr/bin/env python3
"""
EBS-010 Breathalyzer Sensor Test Script
========================================
Test communication with EBS-010 alcohol sensor via USB Serial

Protocol:
  - Baudrate: 4800, Data: 8, Stop: 1, Parity: None
  - Commands end with 0x0D 0x0A (CR+LF)
  - Commands must be UPPERCASE

Sendable Commands: $START, $RECALL, $RESET
Device Responses:  $END, $WAIT, $STANBY, $BREATH, $TRIGGER, $CALIBRATION,
                   $FLOW,ERR, $RESULT,X.XXX-OK/HIGH, $U/B,L/000,H/000,T/0000

Usage:
  python3 test_alcohol_sensor.py                  # Auto-detect USB port
  python3 test_alcohol_sensor.py /dev/ttyUSB0     # Specify port
  python3 test_alcohol_sensor.py --list            # List available ports
"""

import serial
import serial.tools.list_ports
import sys
import time
import re

# ======== Configuration ========
BAUDRATE = 4800
DATA_BITS = serial.EIGHTBITS
STOP_BITS = serial.STOPBITS_ONE
PARITY = serial.PARITY_NONE
TIMEOUT = 2  # seconds
CR_LF = b"\x0D\x0A"

# ======== Sendable Commands (Computer -> EBS-010) ========
CMD_START = b"$START" + CR_LF    # Start measurement (triggers warm-up)
CMD_RECALL = b"$RECALL" + CR_LF  # Check preset values (works in $END state)
CMD_RESET = b"$RESET" + CR_LF   # Turn device OFF (works in $STANBY state)

# ======== Device States/Responses (EBS-010 -> Computer) ========
# $END        - Idle / ready to start
# $WAIT       - Warming up
# $STANBY     - Standby, ready for breath
# $BREATH     - Sampling breath
# $TRIGGER    - Breath detected / triggered
# $CALIBRATION - Calibration period info
# $FLOW,ERR   - Incorrect breath sampling
# $RESULT,X.XXX-OK/HIGH  - Measurement result
# $U/B,L/000,H/000,T/0000 - Detailed result


def list_serial_ports():
    """List all available serial ports."""
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("[!] No serial port found.")
        return []
    print("=" * 60)
    print(" Serial Ports found.")
    print("=" * 60)
    for p in ports:
        print(f"  Port : {p.device}")
        print(f"  Desc : {p.description}")
        print(f"  HWID : {p.hwid}")
        print("-" * 60)
    return ports


def auto_detect_port():
    """Try to auto-detect USB serial port for EBS-010."""
    ports = serial.tools.list_ports.comports()
    usb_ports = [p for p in ports if "USB" in p.device.upper() or "ACM" in p.device.upper()]
    if usb_ports:
        print(f"[*] Auto-detected port: {usb_ports[0].device} ({usb_ports[0].description})")
        return usb_ports[0].device
    if ports:
        print(f"[*] Using first available port: {ports[0].device} ({ports[0].description})")
        return ports[0].device
    return None


def open_serial(port):
    """Open serial connection to EBS-010."""
    try:
        ser = serial.Serial(
            port=port,
            baudrate=BAUDRATE,
            bytesize=DATA_BITS,
            stopbits=STOP_BITS,
            parity=PARITY,
            timeout=TIMEOUT,
        )
        print(f"[OK] Serial port opened: {port} @ {BAUDRATE} baud")
        return ser
    except serial.SerialException as e:
        print(f"[ERROR] Cannot open port {port}: {e}")
        return None


def send_command(ser, cmd, label=""):
    """Send a command to EBS-010."""
    cmd_str = cmd.rstrip(b"\x0D\x0A").decode("ascii", errors="replace")
    print(f"\n[TX] >> {cmd_str}  {label}")
    ser.write(cmd)
    ser.flush()


def read_response(ser, wait_sec=2, max_lines=10):
    """Read response lines from EBS-010."""
    responses = []
    end_time = time.time() + wait_sec
    while time.time() < end_time and len(responses) < max_lines:
        line = ser.readline()
        if line:
            decoded = line.decode("ascii", errors="replace").strip()
            if decoded:
                responses.append(decoded)
                print(f"[RX] << {decoded}")
        else:
            if responses:
                break
    if not responses:
        print("[RX] (no response)")
    return responses


def parse_state(response_line):
    """Parse device state from response."""
    known_states = ["$END", "$WAIT", "$STANBY", "$BREATH", "$TRIGGER", "$CALIBRATION"]
    for state in known_states:
        if state in response_line:
            return state
    if "$FLOW,ERR" in response_line:
        return "$FLOW,ERR"
    return None


def parse_result(response_line):
    """Parse measurement result from $RESULT,X.XXX-OK/HIGH."""
    match = re.match(r"\$RESULT,(\d+\.\d+)-(OK|HIGH)", response_line)
    if match:
        value = float(match.group(1))
        status = match.group(2)
        return {"value": value, "status": status}
    return None


def parse_detail(response_line):
    """Parse detailed result from $U/B,L/000,H/000,T/0000."""
    match = re.match(r"\$U/([BGM]),L/(\d+),H/(\d+),T/(\d+)", response_line)
    if match:
        unit_map = {"B": "%BAC", "G": "g/L", "M": "mg/L"}
        unit_code = match.group(1)
        return {
            "unit": unit_map.get(unit_code, unit_code),
            "low_count": int(match.group(2)),
            "high_count": int(match.group(3)),
            "test_number": int(match.group(4)),
        }
    return None


def run_start_measurement(ser):
    """Send $START and listen for device state changes through the full measurement cycle."""
    print("\n" + "=" * 60)
    print(" EBS-010 Start Measurement")
    print("=" * 60)
    print(" Flow: $START -> device warms up -> $STANBY -> blow ->")
    print("       $BREATH -> $TRIGGER -> $RESULT -> $END")
    print("=" * 60)

    # Send $START
    send_command(ser, CMD_START, "(start warm-up)")

    # Listen for state transitions and results
    print("\n[*] Listening for device responses... (Ctrl+C to stop)")
    result_found = False
    try:
        timeout = time.time() + 120  # 2 minutes max
        while time.time() < timeout:
            line = ser.readline()
            if line:
                decoded = line.decode("ascii", errors="replace").strip()
                if not decoded:
                    continue
                timestamp = time.strftime("%H:%M:%S")
                print(f"[{timestamp}] [RX] << {decoded}")

                # Parse state
                state = parse_state(decoded)
                if state:
                    if state == "$WAIT":
                        print("         -> Device is warming up...")
                    elif state == "$STANBY":
                        print("         -> Device ready! Please BLOW into sensor.")
                    elif state == "$BREATH":
                        print("         -> Sampling breath...")
                    elif state == "$TRIGGER":
                        print("         -> Breath detected, analyzing...")
                    elif state == "$FLOW,ERR":
                        print("         -> [!] FLOW ERROR: incorrect breath, try again.")
                    elif state == "$END":
                        print("         -> Measurement cycle complete.")
                        if result_found:
                            break
                    elif state == "$CALIBRATION":
                        print("         -> Calibration info received.")

                # Parse result
                result = parse_result(decoded)
                if result:
                    print(f"\n{'=' * 40}")
                    print(f"  ALCOHOL MEASUREMENT RESULT")
                    print(f"  Value  : {result['value']}")
                    print(f"  Status : {result['status']}")
                    print(f"{'=' * 40}")
                    result_found = True

                # Parse detail
                detail = parse_detail(decoded)
                if detail:
                    print(f"  Unit       : {detail['unit']}")
                    print(f"  LOW count  : {detail['low_count']}")
                    print(f"  HIGH count : {detail['high_count']}")
                    print(f"  Test #     : {detail['test_number']}")

        if not result_found:
            print("\n[!] Timeout — no result received within 2 minutes.")
    except KeyboardInterrupt:
        print("\n[*] Stopped by user.")

    return result_found


def run_recall(ser):
    """Send $RECALL to check preset values."""
    print("\n" + "=" * 60)
    print(" EBS-010 Recall (check preset values)")
    print("=" * 60)
    send_command(ser, CMD_RECALL, "(check preset values)")
    responses = read_response(ser, wait_sec=5)
    for r in responses:
        detail = parse_detail(r)
        if detail:
            print(f"\n  Unit       : {detail['unit']}")
            print(f"  LOW count  : {detail['low_count']}")
            print(f"  HIGH count : {detail['high_count']}")
            print(f"  Test #     : {detail['test_number']}")
    return responses


def run_reset(ser):
    """Send $RESET to turn device OFF."""
    print("\n" + "=" * 60)
    print(" EBS-010 Reset (turn OFF)")
    print("=" * 60)
    print("[!] Note: $RESET only works when device is in $STANBY state.")
    send_command(ser, CMD_RESET, "(turn OFF)")
    responses = read_response(ser, wait_sec=3)
    return responses


def run_listen_mode(ser):
    """Passive listen mode — read all data from sensor continuously."""
    print("\n" + "=" * 60)
    print(" EBS-010 Listen Mode (Ctrl+C to stop)")
    print("=" * 60)
    try:
        while True:
            line = ser.readline()
            if line:
                decoded = line.decode("ascii", errors="replace").strip()
                if decoded:
                    timestamp = time.strftime("%H:%M:%S")
                    print(f"[{timestamp}] {decoded}")

                    state = parse_state(decoded)
                    if state:
                        print(f"           -> State: {state}")

                    result = parse_result(decoded)
                    if result:
                        print(f"           -> Alcohol: {result['value']} ({result['status']})")

                    detail = parse_detail(decoded)
                    if detail:
                        print(f"           -> Unit: {detail['unit']}, Test#{detail['test_number']}")
    except KeyboardInterrupt:
        print("\n[*] Listen mode stopped.")


def show_menu():
    """Show test menu."""
    print("\n" + "=" * 60)
    print(" EBS-010 Breathalyzer Test Menu")
    print("=" * 60)
    print("  1. $START   — Start measurement (warm-up -> blow -> result)")
    print("  2. $RECALL  — Check preset values")
    print("  3. $RESET   — Turn device OFF (only in $STANBY state)")
    print("  4. Listen   — Passive listen mode")
    print("  0. Exit")
    print("=" * 60)


def main():
    # Handle --list flag
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        list_serial_ports()
        sys.exit(0)

    # Determine port
    if len(sys.argv) > 1:
        port = sys.argv[1]
    else:
        print("[*] Searching serial ports...")
        list_serial_ports()
        port = auto_detect_port()
        if not port:
            print("[ERROR] No serial port found. Please specify, e.g. /dev/ttyUSB0")
            sys.exit(1)

    # Open serial
    ser = open_serial(port)
    if not ser:
        sys.exit(1)

    try:
        while True:
            show_menu()
            choice = input("\nSelect [0-4]: ").strip()

            if choice == "1":
                run_start_measurement(ser)
            elif choice == "2":
                run_recall(ser)
            elif choice == "3":
                run_reset(ser)
            elif choice == "4":
                run_listen_mode(ser)
            elif choice == "0":
                print("[*] Exiting.")
                break
            else:
                print("[!] Please select 0-4")

    except KeyboardInterrupt:
        print("\n[*] Exiting (Ctrl+C)")
    finally:
        if ser and ser.is_open:
            ser.close()
            print("[OK] Serial port closed.")


if __name__ == "__main__":
    main()
