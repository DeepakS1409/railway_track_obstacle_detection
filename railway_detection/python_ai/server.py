"""
FastAPI Backend Server
Receives camera frames from Expo Go Mobile App over Wi-Fi,
runs lightweight Ultralytics YOLOv8 nano inference,
bridges with Wokwi ESP32 via RFC2217 serial port 4000,
and returns real-time detection & sensor telemetry.
"""

import os
import sys
import time
import base64
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure current directory is in path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from config import (
    ESP32_SERIAL_URL,
    SERIAL_BAUD_RATE,
    DEFAULT_CONFIDENCE_THRESHOLD,
    DEFAULT_ALERT_HOLD_TIME,
    TARGET_CLASSES,
    DEFAULT_MODEL_PATH
)
from detector import RailwayTrackDetector
from esp32_serial import ESP32SerialClient

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [Server] %(message)s")
logger = logging.getLogger("FastAPIServer")

# -----------------------------------------------------------------------------
# FastAPI App Initialization
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Railway Track Obstacle Detection API",
    description="Edge AI Backend connecting Expo Go Mobile App with YOLO AI & Wokwi ESP32",
    version="2.0.0"
)

# Enable CORS for Mobile App Wi-Fi access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared Subsystems
detector: Optional[RailwayTrackDetector] = None
esp32_client: Optional[ESP32SerialClient] = None


@app.on_event("startup")
def startup_event():
    global detector, esp32_client
    logger.info("Starting Railway Detection Backend Server...")

    # 1. Initialize YOLO Detector
    detector = RailwayTrackDetector(
        model_path=str(DEFAULT_MODEL_PATH),
        conf_threshold=DEFAULT_CONFIDENCE_THRESHOLD
    )
    logger.info(f"YOLO Detector initialized. Target classes: {TARGET_CLASSES}")

    # 2. Initialize ESP32 Serial Link
    esp32_client = ESP32SerialClient(port_url=ESP32_SERIAL_URL, baudrate=SERIAL_BAUD_RATE)
    connected = esp32_client.connect()
    if connected:
        logger.info(f"Connected to Wokwi virtual ESP32 on {ESP32_SERIAL_URL}")
    else:
        logger.warning(
            f"Could not connect to {ESP32_SERIAL_URL}. "
            "Ensure Wokwi simulation is running in VS Code with rfc2217ServerPort=4000."
        )


@app.on_event("shutdown")
def shutdown_event():
    global esp32_client
    if esp32_client and esp32_client.is_connected:
        esp32_client.disconnect()
    logger.info("Backend server shut down cleanly.")


# -----------------------------------------------------------------------------
# Data Models
# -----------------------------------------------------------------------------
class Base64FramePayload(BaseModel):
    image: str  # Base64 encoded JPEG / PNG string


class CommandPayload(BaseModel):
    command: str  # ALERT, SAFE, PING, RESET


# -----------------------------------------------------------------------------
# API Endpoints
# -----------------------------------------------------------------------------
@app.get("/")
@app.get("/health")
def health_check():
    """Health status and current ESP32 connection state."""
    esp_online = esp32_client.is_connected if esp32_client else False
    telemetry = esp32_client.get_telemetry() if esp32_client else {}
    return {
        "status": "online",
        "service": "Railway Track Detection API",
        "esp32_connected": esp_online,
        "esp32_port": ESP32_SERIAL_URL,
        "telemetry": telemetry
    }


@app.post("/detect")
async def detect_frame(payload: Base64FramePayload):
    """
    Receives compressed base64 frame from Expo Go mobile app,
    decodes in-memory (zero disk writing), executes YOLOv8 nano inference,
    updates ESP32 state machine, and returns detection results + telemetry.
    """
    if not detector or not detector.is_ready:
        raise HTTPException(status_code=503, detail="YOLO AI detector is not ready.")

    # 1. Decode base64 image in-memory
    try:
        raw_b64 = payload.image
        if "," in raw_b64:
            raw_b64 = raw_b64.split(",", 1)[1]

        image_bytes = base64.b64decode(raw_b64)
        np_arr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            raise ValueError("cv2.imdecode returned None.")
    except Exception as e:
        logger.error(f"Error decoding image frame: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid image format: {e}")

    # 2. Execute YOLO Inference on CPU
    annotated_frame, detections, is_hazard = detector.detect(frame)

    # 3. Synchronize with ESP32 Serial Link
    decision_state = "SAFE"
    if esp32_client and esp32_client.is_connected:
        decision_state = esp32_client.update_detection_state(
            is_hazard_detected=is_hazard,
            hold_time_seconds=DEFAULT_ALERT_HOLD_TIME
        )
    elif esp32_client and not esp32_client.is_connected:
        # Non-blocking auto-reconnect attempt
        esp32_client.connect()

    # 4. Fetch Latest Hardware Telemetry
    telemetry = esp32_client.get_telemetry() if esp32_client else {}

    return {
        "status": "success",
        "is_hazard": is_hazard,
        "decision_state": decision_state,
        "detections": detections,
        "esp32": {
            "connected": esp32_client.is_connected if esp32_client else False,
            "distance": telemetry.get("distance", -1.0),
            "pir": telemetry.get("pir", False),
            "system_alert": telemetry.get("system_alert", False),
            "ai_alert": telemetry.get("ai_alert", False)
        },
        "timestamp": time.time()
    }


@app.post("/detect/file")
async def detect_frame_file(file: UploadFile = File(...)):
    """Alternative multipart file upload endpoint for standard HTTP multipart requests."""
    if not detector or not detector.is_ready:
        raise HTTPException(status_code=503, detail="YOLO AI detector is not ready.")

    try:
        content = await file.read()
        np_arr = np.frombuffer(content, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Could not decode image.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Image decode failed: {e}")

    _, detections, is_hazard = detector.detect(frame)

    decision_state = "SAFE"
    if esp32_client and esp32_client.is_connected:
        decision_state = esp32_client.update_detection_state(
            is_hazard_detected=is_hazard,
            hold_time_seconds=DEFAULT_ALERT_HOLD_TIME
        )

    telemetry = esp32_client.get_telemetry() if esp32_client else {}

    return {
        "status": "success",
        "is_hazard": is_hazard,
        "decision_state": decision_state,
        "detections": detections,
        "esp32": {
            "connected": esp32_client.is_connected if esp32_client else False,
            "distance": telemetry.get("distance", -1.0),
            "pir": telemetry.get("pir", False),
            "system_alert": telemetry.get("system_alert", False)
        }
    }


@app.get("/telemetry")
def get_esp32_telemetry():
    """Retrieve live ESP32 telemetry (PIR motion & ultrasonic distance)."""
    if not esp32_client:
        return {"connected": False}
    return esp32_client.get_telemetry()


@app.post("/esp32/connect")
def reconnect_esp32():
    """Attempt reconnection to Wokwi virtual serial."""
    global esp32_client
    if not esp32_client:
        esp32_client = ESP32SerialClient(port_url=ESP32_SERIAL_URL, baudrate=SERIAL_BAUD_RATE)
    success = esp32_client.connect()
    return {"success": success, "port": ESP32_SERIAL_URL}


@app.post("/esp32/command")
def send_manual_command(payload: CommandPayload):
    """Send manual ALERT, SAFE, PING, or RESET command to ESP32."""
    if not esp32_client or not esp32_client.is_connected:
        raise HTTPException(status_code=503, detail="ESP32 is not connected.")
    success = esp32_client._send_command(payload.command)
    return {"command": payload.command, "sent": success}


if __name__ == "__main__":
    import uvicorn
    # Bind to 0.0.0.0 so phone on same Wi-Fi can reach the laptop
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
