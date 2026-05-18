import socket
import uuid
import platform
import subprocess
import re

def get_serial_number() -> str:
    """Get device serial number (Linux /proc/cpuinfo or fallback to uuid)."""
    if platform.system() == "Linux":
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if line.startswith("Serial"):
                        return line.split(":")[1].strip()
        except Exception:
            pass
    elif platform.system() == "Windows":
        try:
            output = subprocess.check_output("wmic csproduct get identifyingnumber", shell=True).decode()
            parts = output.split()
            if len(parts) > 1:
                return parts[1].strip()
        except Exception:
            pass
    # Fallback
    return str(uuid.getnode())

def get_mac_address() -> str:
    """Get MAC address formatted as XX:XX:XX:XX:XX:XX."""
    node = uuid.getnode()
    mac = uuid.UUID(int=node).hex[-12:]
    return ":".join([mac[e:e+2] for e in range(0, 11, 2)]).upper()

def get_ip_address() -> str:
    """Get primary IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Doesn't need to be reachable, just forces routing
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return socket.gethostbyname(socket.gethostname())
