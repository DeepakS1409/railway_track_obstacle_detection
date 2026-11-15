"""
Camera & Video Stream Manager
Supports:
  1. Built-in laptop webcam (index 0, 1)
  2. Pre-recorded video files (with seamless loop for testing)
  3. Phone camera stream via IP Webcam app (HTTP/RTSP stream)
"""

import cv2
import time
from typing import Union, Tuple, Optional
from config import FRAME_WIDTH, FRAME_HEIGHT

class VideoStreamHandler:
    def __init__(self, source: Union[int, str] = 0, width: int = FRAME_WIDTH, height: int = FRAME_HEIGHT):
        self.source = source
        self.width = width
        self.height = height
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_file = isinstance(source, str) and not source.startswith(("http://", "https://", "rtsp://"))
        self._open_stream()

    def _open_stream(self):
        """Initialize the OpenCV VideoCapture source."""
        if self.cap is not None:
            self.cap.release()

        # Handle numeric string passed from CLI/UI
        resolved_source = self.source
        if isinstance(self.source, str) and self.source.isdigit():
            resolved_source = int(self.source)

        print(f"[INFO] Opening video source: {resolved_source}")
        self.cap = cv2.VideoCapture(resolved_source)

        if not self.is_file:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

    def read_frame(self) -> Tuple[bool, Optional[cv2.Mat]]:
        """Read the next frame. Automatically rewinds if playing a video file."""
        if self.cap is None or not self.cap.isOpened():
            return False, None

        ret, frame = self.cap.read()

        # Handle end of video file by rewinding to frame 0
        if not ret and self.is_file:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()

        if ret and frame is not None:
            # Resize frame to standardized lightweight dimensions
            frame = cv2.resize(frame, (self.width, self.height))
            return True, frame

        return False, None

    def release(self):
        """Release camera resources."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        print("[INFO] Video stream released.")

