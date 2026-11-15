"""
ESP32 Serial Communication Module
Connects to Wokwi virtual ESP32 via RFC2217 TCP port (rfc2217://localhost:4000).
Maintains non-blocking bidirectional communication:
- Commands: ALERT, SAFE, PING, RESET
- Telemetry: Parsed JSON (pir, distance, ai_connected, ai_alert, system_alert)
"""

import time
import json
import logging
import threading
from typing import Optional, Dict, Any, Callable
import serial
import serial.rfc2217

from config import (
    ESP32_SERIAL_URL,
    SERIAL_BAUD_RATE,
    SERIAL_TIMEOUT_SECONDS,
    SERIAL_HEARTBEAT_INTERVAL
)

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [ESP32Serial] %(message)s")
logger = logging.getLogger("ESP32Serial")


class ESP32SerialClient:
    """Thread-safe RFC2217 Serial Client for Wokwi ESP32 simulation."""

    def __init__(self, port_url: str = ESP32_SERIAL_URL, baudrate: int = SERIAL_BAUD_RATE):
        self.port_url = port_url
        self.baudrate = baudrate
        self.timeout = SERIAL_TIMEOUT_SECONDS

        self.ser: Optional[serial.Serial] = None
        self._is_connected = False
        self._running = False

        # State Tracking
        self.current_ai_state = "SAFE"  # "ALERT" or "SAFE"
        self.last_state_sent = None
        self.last_detection_timestamp = 0.0
        self.last_heartbeat_timestamp = 0.0

        # Latest Telemetry Cache
        self.telemetry_lock = threading.Lock()
        self.latest_telemetry: Dict[str, Any] = {
            "pir": False,
            "distance": -1.0,
            "ai_connected": False,
            "ai_alert": False,
            "system_alert": False,
            "last_updated": 0.0,
            "status": "DISCONNECTED"
        }

        # Threading
        self.io_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        self.last_error_message = ""

    def connect(self) -> bool:
        """Establish RFC2217 connection to Wokwi ESP32. Prevents duplicate connections."""
        with self.lock:
            if self._is_connected and self.ser is not None and self.ser.is_open:
                logger.info("Already connected to Wokwi ESP32.")
                return True

            try:
                logger.info(f"Connecting to Wokwi RFC2217 serial at: {self.port_url}")
                # PySerial serial_for_url seamlessly handles RFC2217 URLs
                self.ser = serial.serial_for_url(
                    self.port_url,
                    baudrate=self.baudrate,
                    timeout=self.timeout
                )
                self._is_connected = True
                self._running = True
                self.last_error_message = ""

                # Start background thread for telemetry reading & heartbeat
                self.io_thread = threading.Thread(target=self._io_worker, daemon=True)
                self.io_thread.start()

                # Send initial PING to wake up ESP32 AI handler
                self._write_raw("PING")
                logger.info(f"Successfully connected to Wokwi ESP32 on {self.port_url}")
                return True

            except Exception as e:
                self._is_connected = False
                self.last_error_message = str(e)
                logger.warning(
                    f"Connection to Wokwi failed ({self.port_url}): {e}. "
                    "Ensure Wokwi simulation is running in VS Code with rfc2217ServerPort=4000."
                )
                return False

    def disconnect(self):
        """Cleanly close connection and stop background threads."""
        self._running = False
        with self.lock:
            if self.ser and self.ser.is_open:
                try:
                    # Inform ESP32 to release AI lock
                    self._write_raw("RESET")
                    time.sleep(0.1)
                    self.ser.close()
                except Exception:
                    pass
            self.ser = None
            self._is_connected = False

        with self.telemetry_lock:
            self.latest_telemetry["status"] = "DISCONNECTED"
            self.latest_telemetry["ai_connected"] = False

        logger.info("ESP32 serial connection closed cleanly.")

    @property
    def is_connected(self) -> bool:
        return self._is_connected and self.ser is not None and self.ser.is_open

    def update_detection_state(self, is_hazard_detected: bool, hold_time_seconds: float = 3.0) -> str:
        """
        Manages state transitions without flooding commands on every frame:
        - If hazard detected: immediately sends ALERT and updates last_detection_timestamp.
        - If clear: waits until hold_time_seconds have elapsed since last detection before sending SAFE.
        - Never lets a premature SAFE override an active ALERT.
        """
        now = time.time()

        if is_hazard_detected:
            self.last_detection_timestamp = now
            if self.current_ai_state != "ALERT" or self.last_state_sent != "ALERT":
                self.current_ai_state = "ALERT"
                self._send_command("ALERT")
            return "ALERT"

        else:
            # No target currently in frame
            time_since_detection = now - self.last_detection_timestamp
            if self.current_ai_state == "ALERT":
                if time_since_detection >= hold_time_seconds:
                    # Hold time has expired safely
                    self.current_ai_state = "SAFE"
                    self._send_command("SAFE")
                    return "SAFE"
                else:
                    # Retaining ALERT during hold time
                    return "ALERT_HOLDING"
            else:
                if self.last_state_sent != "SAFE":
                    self._send_command("SAFE")
                return "SAFE"

    def _send_command(self, cmd: str) -> bool:
        """Send formatted command line to ESP32."""
        if not self.is_connected:
            return False

        with self.lock:
            try:
                success = self._write_raw(cmd)
                if success:
                    self.last_state_sent = cmd
                    logger.info(f"Sent Command to ESP32: >> {cmd}")
                return success
            except Exception as e:
                logger.error(f"Failed to send command '{cmd}': {e}")
                self._is_connected = False
                return False

    def _write_raw(self, line: str) -> bool:
        """Raw line write terminated with newline."""
        if not self.ser or not self.ser.is_open:
            return False
        payload = (line.strip() + "\n").encode("utf-8")
        self.ser.write(payload)
        self.ser.flush()
        return True

    def get_telemetry(self) -> Dict[str, Any]:
        """Retrieve copy of latest parsed telemetry."""
        with self.telemetry_lock:
            data = self.latest_telemetry.copy()
            data["connection_state"] = "ONLINE" if self.is_connected else "OFFLINE"
            data["ai_command_state"] = self.current_ai_state
            return data

    def _io_worker(self):
        """Background thread handling continuous JSON telemetry reads & heartbeat."""
        while self._running and self._is_connected:
            now = time.time()

            # 1. Heartbeat to maintain ESP32 aiConnected (Timeout is 4.0s)
            if now - self.last_heartbeat_timestamp >= SERIAL_HEARTBEAT_INTERVAL:
                self.last_heartbeat_timestamp = now
                with self.lock:
                    try:
                        self._write_raw("PING")
                    except Exception:
                        self._is_connected = False
                        break

            # 2. Read incoming serial line
            try:
                if self.ser and self.ser.in_waiting > 0:
                    raw_bytes = self.ser.readline()
                    line = raw_bytes.decode("utf-8", errors="ignore").strip()

                    if line:
                        self._process_incoming_line(line)
            except Exception as e:
                logger.warning(f"Error in serial communication worker: {e}")
                self._is_connected = False
                break

            time.sleep(0.02)

    def _process_incoming_line(self, line: str):
        """Parse JSON telemetry or text acknowledgments from ESP32."""
        if line.startswith("{") and line.endswith("}"):
            try:
                data = json.loads(line)
                # ESP32 format: {"pir":bool,"distance":float,"ai_connected":bool,"ai_alert":bool,"system_alert":bool}
                with self.telemetry_lock:
                    self.latest_telemetry.update({
                        "pir": bool(data.get("pir", False)),
                        "distance": float(data.get("distance", -1.0)),
                        "ai_connected": bool(data.get("ai_connected", False)),
                        "ai_alert": bool(data.get("ai_alert", False)),
                        "system_alert": bool(data.get("system_alert", False)),
                        "last_updated": time.time(),
                        "status": "ACTIVE"
                    })
            except (json.JSONDecodeError, ValueError):
                pass
        else:
            # Informational text messages from ESP32
            if "AI ALERT" in line or "AI SAFE" in line or "TIMEOUT" in line:
                logger.info(f"ESP32 Message: {line}")

