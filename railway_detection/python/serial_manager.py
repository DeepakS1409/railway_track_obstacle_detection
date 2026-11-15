"""
Serial Communication Manager
Handles robust communication with ESP32 via physical COM ports or Wokwi RFC2217 TCP server.
"""

import time
import json
import threading
import logging
from typing import Optional, Dict, Any

try:
    import serial
    import serial.rfc2217
except ImportError:
    serial = None

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("SerialManager")


class SerialManager:
    def __init__(self, port: str = "rfc2217://localhost:4000", baudrate: int = 115200, timeout: float = 1.0):
        self.port_url = port
        self.baudrate = baudrate
        self.timeout = timeout

        self.ser: Optional[serial.Serial] = None
        self.is_running = False
        self._connected = False

        self.last_command_sent: Optional[str] = None
        self.last_command_time = 0.0
        self.command_lock = threading.Lock()

        # Telemetry storage
        self.latest_telemetry: Dict[str, Any] = {
            "distance": -1.0,
            "pir": 0,
            "state": "UNKNOWN",
            "source": "DISCONNECTED",
            "ai_mode": False,
            "timestamp": 0.0
        }
        self.telemetry_lock = threading.Lock()

        # Background reader thread
        self.reader_thread: Optional[threading.Thread] = None

    def connect(self) -> bool:
        """Establish connection with physical serial port or Wokwi RFC2217 bridge."""
        if serial is None:
            logger.error("pyserial is not installed! Run: pip install pyserial")
            return False

        try:
            logger.info(f"Connecting to ESP32 at '{self.port_url}' (baud: {self.baudrate})...")
            
            # serial_for_url handles standard COM ports, /dev/tty, and rfc2217:// URLs
            self.ser = serial.serial_for_url(
                self.port_url,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            self._connected = True
            self.is_running = True

            # Start background reader thread
            self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.reader_thread.start()

            logger.info(f"Successfully connected to ESP32 on {self.port_url}")
            return True

        except Exception as e:
            self._connected = False
            logger.warning(f"Failed to connect to {self.port_url}: {e}")
            return False

    def disconnect(self):
        """Disconnect and clean up resources."""
        self.is_running = False
        self._connected = False
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass
        self.ser = None
        logger.info("Serial connection closed.")

    def is_connected(self) -> bool:
        return self._connected and self.ser is not None and self.ser.is_open

    def send_command(self, command: str, force: bool = False, min_interval: float = 0.8) -> bool:
        """
        Send command to ESP32 with deduplication and cooldown to prevent command spam.
        """
        if not self.is_connected():
            return False

        now = time.time()
        with self.command_lock:
            # Prevent sending the exact same command repeatedly within min_interval unless forced
            if not force and command == self.last_command_sent and (now - self.last_command_time < min_interval):
                return True

            try:
                formatted_cmd = (command.strip() + "\n").encode("utf-8")
                self.ser.write(formatted_cmd)
                self.ser.flush()
                self.last_command_sent = command
                self.last_command_time = now
                logger.info(f"Sent command to ESP32: >> {command.strip()}")
                return True
            except Exception as e:
                logger.error(f"Error sending command '{command}': {e}")
                self._connected = False
                return False

    def send_alert(self, force: bool = False) -> bool:
        return self.send_command("ALERT", force=force)

    def send_safe(self, force: bool = False) -> bool:
        return self.send_command("SAFE", force=force)

    def send_ping(self) -> bool:
        return self.send_command("PING", force=True)

    def get_latest_telemetry(self) -> Dict[str, Any]:
        with self.telemetry_lock:
            return self.latest_telemetry.copy()

    def _read_loop(self):
        """Background thread continuously parsing incoming telemetry JSON lines."""
        buffer = ""
        while self.is_running and self._connected:
            try:
                if not self.ser or not self.ser.is_open:
                    break

                line = self.ser.readline().decode("utf-8", errors="ignore").strip()
                if not line:
                    continue

                # Attempt JSON decoding for structured telemetry
                if line.startswith("{") and line.endswith("}"):
                    try:
                        data = json.loads(line)
                        if "distance" in data:
                            with self.telemetry_lock:
                                self.latest_telemetry = {
                                    "distance": float(data.get("distance", -1.0)),
                                    "pir": int(data.get("pir", 0)),
                                    "state": str(data.get("state", "UNKNOWN")),
                                    "source": str(data.get("source", "STANDALONE")),
                                    "ai_mode": bool(data.get("ai_mode", False)),
                                    "timestamp": time.time()
                                }
                        elif "ack" in data:
                            logger.info(f"ESP32 Acknowledged: {data}")
                        elif "error" in data:
                            logger.warning(f"ESP32 Reported Error: {data}")
                    except json.JSONDecodeError:
                        pass
                else:
                    # Raw serial debug log
                    logger.debug(f"ESP32 Raw: {line}")

            except Exception as e:
                logger.warning(f"Serial reader disconnected or error: {e}")
                self._connected = False
                break

            time.sleep(0.01)

