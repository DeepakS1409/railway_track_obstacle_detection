"""
Railway Track Human & Animal Detection System
Configuration Parameters
"""

import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
DEFAULT_MODEL_PATH = MODELS_DIR / "yolov8n.pt"

# Wokwi RFC2217 Serial Bridge Settings
# Wokwi VS Code extension exposes the simulated UART via RFC2217 on port 4000
ESP32_SERIAL_URL = os.getenv("ESP32_SERIAL_URL", "rfc2217://localhost:4000")
SERIAL_BAUD_RATE = 115200
SERIAL_TIMEOUT_SECONDS = 1.0
SERIAL_HEARTBEAT_INTERVAL = 1.5  # Seconds between PING commands (ESP32 timeout is 4.0s)

# YOLO Detection Settings
# Target COCO classes: 0 = Person, 16 = Dog, 19 = Cow
TARGET_CLASSES = {
    0: "Person",
    16: "Dog",
    19: "Cow"
}

DEFAULT_CONFIDENCE_THRESHOLD = 0.45
DEFAULT_ALERT_HOLD_TIME = 3.0  # Seconds to hold ALERT state before reverting to SAFE

# Camera & Video Stream Settings
DEFAULT_CAMERA_URL = os.getenv("CAMERA_STREAM_URL", "http://192.168.1.100:8080/video")
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
STREAM_BUFFER_SIZE = 1  # Always keep latest frame for minimal latency

