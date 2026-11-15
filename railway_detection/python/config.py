"""
System Configuration
Railway Track Human & Animal Detection System
"""

import os

# -----------------------------------------------------------------------------
# Serial & Hardware Simulation Settings
# -----------------------------------------------------------------------------
# For Wokwi VS Code RFC2217 forwarding: "rfc2217://localhost:4000"
# For physical ESP32 on USB: "COM3" (Windows) or "/dev/ttyUSB0" (Linux)
DEFAULT_SERIAL_PORT = os.getenv("ESP32_PORT", "rfc2217://localhost:4000")
SERIAL_BAUD_RATE = 115200
SERIAL_TIMEOUT_SEC = 1.0

# -----------------------------------------------------------------------------
# AI & YOLO Detection Settings
# -----------------------------------------------------------------------------
# Lightweight YOLO model for 8GB RAM laptop
YOLO_MODEL_NAME = "yolov8n.pt"

# Target COCO classes: 0 = person, 16 = dog, 19 = cow
TARGET_CLASSES = {
    0: "Person",
    16: "Dog",
    19: "Cow"
}

# Detection confidence threshold (0.0 to 1.0)
DETECTION_CONFIDENCE_THRESHOLD = 0.45

# Command debounce interval in seconds (avoid spamming serial commands)
COMMAND_COOLDOWN_SEC = 1.0

# -----------------------------------------------------------------------------
# Camera / Video Stream Settings
# -----------------------------------------------------------------------------
# Options:
#   - Integer (e.g. 0): Built-in laptop webcam
#   - String URL (e.g. "http://192.168.1.5:8080/video"): Phone IP Webcam / RTSP
#   - File path (e.g. "assets/sample_tracks.mp4"): Pre-recorded video test file
DEFAULT_CAMERA_SOURCE = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
TARGET_FPS = 30

