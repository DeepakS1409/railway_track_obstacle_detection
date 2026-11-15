"""
Mobile Phone & Web Camera Stream Handler
Provides zero-latency threaded capture for live mobile streams (e.g., IP Webcam over Wi-Fi),
laptop webcams, and local test video files.
"""

import cv2
import time
import threading
import logging
from typing import Tuple, Optional, Union
from config import FRAME_WIDTH, FRAME_HEIGHT

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [CameraStream] %(message)s")
logger = logging.getLogger("CameraStream")


class MobileCameraStream:
    """Threaded Video Stream with zero-buffer lag optimization for IP cameras."""

    def __init__(self, source: Union[str, int], target_width: int = FRAME_WIDTH, target_height: int = FRAME_HEIGHT):
        self.source = source
        self.target_width = target_width
        self.target_height = target_height

        self.cap: Optional[cv2.VideoCapture] = None
        self.latest_frame: Optional[cv2.Mat] = None
        self.is_connected = False
        self.running = False
        self.lock = threading.Lock()
        self.last_frame_time = 0.0
        self.last_error = ""

        # Check if source is a file
        self.is_file = isinstance(source, str) and not source.startswith(("http://", "https://", "rtsp://"))
        self._thread: Optional[threading.Thread] = None

    def start(self) -> bool:
        """Open video capture source and launch grabber thread."""
        self.stop()

        resolved_source = self.source
        if isinstance(self.source, str) and self.source.isdigit():
            resolved_source = int(self.source)

        logger.info(f"Connecting to camera stream: {resolved_source}")

        try:
            self.cap = cv2.VideoCapture(resolved_source)

            # Optimizations for IP Webcam / RTSP
            if not self.is_file and isinstance(resolved_source, str) and resolved_source.startswith("http"):
                # OpenCV buffer size 1 for minimal latency
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            # Test first frame
            if not self.cap.isOpened():
                self.last_error = f"Cannot open stream at: {resolved_source}"
                logger.error(self.last_error)
                self.is_connected = False
                return False

            ret, test_frame = self.cap.read()
            if not ret or test_frame is None:
                self.last_error = f"Stream opened but failed to capture first frame from: {resolved_source}"
                logger.warning(self.last_error)
                self.is_connected = False
                return False

            with self.lock:
                self.latest_frame = cv2.resize(test_frame, (self.target_width, self.target_height))
                self.last_frame_time = time.time()
                self.is_connected = True
                self.running = True

            # Start background reader thread
            self._thread = threading.Thread(target=self._capture_worker, daemon=True)
            self._thread.start()
            logger.info("Camera stream connected and worker started successfully.")
            return True

        except Exception as e:
            self.last_error = f"Exception opening video source: {e}"
            logger.error(self.last_error)
            self.is_connected = False
            return False

    def _capture_worker(self):
        """Continuously grab latest frame, discarding buffered stale frames."""
        consecutive_failures = 0

        while self.running and self.cap and self.cap.isOpened():
            try:
                ret, frame = self.cap.read()

                if ret and frame is not None:
                    consecutive_failures = 0
                    resized = cv2.resize(frame, (self.target_width, self.target_height))
                    with self.lock:
                        self.latest_frame = resized
                        self.last_frame_time = time.time()
                        self.is_connected = True
                else:
                    if self.is_file:
                        # Video file looping
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        time.sleep(0.03)
                        continue

                    consecutive_failures += 1
                    if consecutive_failures > 30:
                        logger.warning("Camera stream dropped or timed out.")
                        with self.lock:
                            self.is_connected = False
                        break

            except Exception as e:
                logger.warning(f"Error reading frame: {e}")
                with self.lock:
                    self.is_connected = False
                break

            time.sleep(0.01)

    def read(self) -> Tuple[bool, Optional[cv2.Mat]]:
        """Return the most recent frame."""
        with self.lock:
            if not self.is_connected or self.latest_frame is None:
                return False, None
            return True, self.latest_frame.copy()

    def stop(self):
        """Stop background worker and release OpenCV capture."""
        self.running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
            self._thread = None

        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

        with self.lock:
            self.is_connected = False
            self.latest_frame = None

        logger.info("Camera stream stopped.")

