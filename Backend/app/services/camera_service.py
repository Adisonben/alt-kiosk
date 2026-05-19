"""
CameraService — Manages Picamera2 snapshot capture.
"""

import base64
import os
import tempfile
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from picamera2 import Picamera2
    _PICAMERA_AVAILABLE = True
except ImportError:
    _PICAMERA_AVAILABLE = False
    logger.warning("picamera2 not available — camera functions disabled")


class CameraService:
    """
    Captures still images using Picamera2 on Raspberry Pi.
    """

    def __init__(self) -> None:
        self.picam2: Optional[Picamera2] = None
        self.is_running: bool = False

    def start(self) -> None:
        """Initializes and starts the camera to allow sensor warmup."""
        if not _PICAMERA_AVAILABLE:
            logger.warning("CameraService: picamera2 not available, cannot start.")
            return

        if self.is_running:
            return

        try:
            self.picam2 = Picamera2()
            # Configure to capture at 640x480 to keep WebSocket payload small and fast
            camera_config = self.picam2.create_still_configuration(main={"size": (640, 480)})
            self.picam2.configure(camera_config)
            self.picam2.start()
            self.is_running = True
            logger.info("CameraService: started and sensor is active.")
        except Exception as e:
            logger.error("CameraService: failed to start picamera2: %s", e)
            self.picam2 = None
            self.is_running = False

    def capture_image_base64(self) -> Optional[str]:
        """Captures a frame to a temp file and returns it as a Base64 string."""
        if not _PICAMERA_AVAILABLE or not self.is_running or not self.picam2:
            logger.warning("CameraService: camera not running, cannot capture.")
            return None

        temp_path = os.path.join(tempfile.gettempdir(), "kiosk_capture.jpg")

        try:
            # Capture the file synchronously (sensor is already active, so it is fast)
            self.picam2.capture_file(temp_path)

            if not os.path.exists(temp_path):
                logger.error("CameraService: captured file does not exist.")
                return None

            with open(temp_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

            try:
                os.remove(temp_path)
            except OSError as e:
                logger.warning("CameraService: failed to delete temp file %s: %s", temp_path, e)

            return encoded_string
        except Exception as e:
            logger.error("CameraService: failed to capture image: %s", e)
            return None

    def stop(self) -> None:
        """Stops the camera safely."""
        if not _PICAMERA_AVAILABLE or not self.is_running or not self.picam2:
            return

        try:
            self.picam2.stop()
            self.picam2.close()
            logger.info("CameraService: stopped camera successfully.")
        except Exception as e:
            logger.error("CameraService: error stopping picamera2: %s", e)
        finally:
            self.picam2 = None
            self.is_running = False
