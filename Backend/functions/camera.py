"""
Camera functions using picamera2 for Raspberry Pi.
Provides snapshot capture only.
"""
import os
import threading
import time
from kivy.clock import Clock

# Try to import picamera2, set flag if unavailable
try:
    from picamera2 import Picamera2
    PICAMERA_AVAILABLE = True
except ImportError:
    PICAMERA_AVAILABLE = False
    print("[Camera] picamera2 not available. Camera functions disabled.")


def take_snapshot(filepath, callback=None):
    """
    Capture a still image and save to file.
    Runs in a background thread to avoid blocking the UI.

    Args:
        filepath: Path to save the image.
        callback: Optional callback(success: bool, path: str) called on Kivy main thread.
    """
    if not PICAMERA_AVAILABLE:
        print("[Camera] picamera2 module not installed.")
        if callback:
            Clock.schedule_once(lambda dt: callback(False, None), 0)
        return

    def _capture_thread():
        picam2 = None
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            picam2 = Picamera2()
            config = picam2.create_still_configuration(
                main={"size": (1920, 1080)},
                lores={"size": (640, 480)},
                display="lores"
            )
            picam2.configure(config)

            try:
                picam2.start()
            except Exception as e:
                print(f"[Camera] Failed to start camera: {e}")
                if callback:
                    Clock.schedule_once(lambda dt: callback(False, None), 0)
                return

            # Small delay to let camera warm up
            time.sleep(0.5)

            try:
                picam2.capture_file(filepath)
                print(f"[Camera] Snapshot saved: {filepath}")
            except Exception as e:
                print(f"[Camera] Capture failed: {e}")
                if callback:
                    Clock.schedule_once(lambda dt: callback(False, None), 0)
                return

            if callback:
                Clock.schedule_once(lambda dt: callback(True, filepath), 0)

        except Exception as e:
            print(f"[Camera] Snapshot error: {e}")
            if callback:
                Clock.schedule_once(lambda dt: callback(False, None), 0)
        finally:
            if picam2 is not None:
                try:
                    picam2.stop()
                    picam2.close()
                except Exception:
                    pass

    threading.Thread(target=_capture_thread, daemon=True).start()
