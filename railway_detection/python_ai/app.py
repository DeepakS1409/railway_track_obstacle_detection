"""
Railway Track Human & Animal Detection System
Professional Dark-Themed Desktop Dashboard (Streamlit)
Integrated with Wokwi ESP32 Virtual Hardware & Mobile Phone Wi-Fi Camera.
"""

import sys
import time
from datetime import datetime
from pathlib import Path
import streamlit as st
import cv2
import numpy as np

# Ensure local imports resolve cleanly
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from config import (
    ESP32_SERIAL_URL,
    DEFAULT_CAMERA_URL,
    DEFAULT_CONFIDENCE_THRESHOLD,
    DEFAULT_ALERT_HOLD_TIME,
    TARGET_CLASSES
)
from esp32_serial import ESP32SerialClient
from camera import MobileCameraStream
from detector import RailwayTrackDetector

# -----------------------------------------------------------------------------
# Streamlit UI Configuration & Styling
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Railway Track Safety Monitor",
    page_icon="🚆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark Theme Stylesheet
st.markdown("""
<style>
    .stApp {
        background-color: #0b0f19;
        color: #e2e8f0;
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    }
    .metric-panel {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 10px;
        padding: 14px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.4);
    }
    .metric-panel-title {
        font-size: 11px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #9ca3af;
        margin-bottom: 4px;
    }
    .metric-panel-value {
        font-size: 22px;
        font-weight: 700;
    }
    .banner-danger {
        background: linear-gradient(135deg, #7f1d1d, #450a0a);
        border: 2px solid #ef4444;
        color: #fecaca;
        border-radius: 10px;
        padding: 18px;
        text-align: center;
        box-shadow: 0 0 25px rgba(239, 68, 68, 0.4);
        animation: pulseDanger 1.5s infinite;
    }
    .banner-safe {
        background: linear-gradient(135deg, #064e3b, #022c22);
        border: 2px solid #10b981;
        color: #a7f3d0;
        border-radius: 10px;
        padding: 18px;
        text-align: center;
        box-shadow: 0 0 15px rgba(16, 185, 129, 0.25);
    }
    .led-dot-red {
        height: 14px;
        width: 14px;
        background-color: #ef4444;
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 10px #ef4444;
        margin-right: 6px;
    }
    .led-dot-green {
        height: 14px;
        width: 14px;
        background-color: #10b981;
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 10px #10b981;
        margin-right: 6px;
    }
    @keyframes pulseDanger {
        0% { transform: scale(1); }
        50% { transform: scale(1.015); }
        100% { transform: scale(1); }
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Session State Management
# -----------------------------------------------------------------------------
if "serial_client" not in st.session_state:
    st.session_state.serial_client = None

if "detector" not in st.session_state:
    st.session_state.detector = RailwayTrackDetector(conf_threshold=DEFAULT_CONFIDENCE_THRESHOLD)

if "camera_stream" not in st.session_state:
    st.session_state.camera_stream = None

if "alert_history" not in st.session_state:
    st.session_state.alert_history = []

if "detection_active" not in st.session_state:
    st.session_state.detection_active = False

# -----------------------------------------------------------------------------
# Sidebar: Section E - Controls & Configuration
# -----------------------------------------------------------------------------
st.sidebar.title("🚆 Control Center")

st.sidebar.subheader("1. Wokwi ESP32 Connection")
serial_url_input = st.sidebar.text_input(
    "RFC2217 Port URL",
    value=ESP32_SERIAL_URL,
    help="Default is 'rfc2217://localhost:4000' forwarded by Wokwi VS Code extension."
)

col_conn_btn1, col_conn_btn2 = st.sidebar.columns(2)
with col_conn_btn1:
    if st.button("🔗 Connect", use_container_width=True):
        if st.session_state.serial_client:
            st.session_state.serial_client.disconnect()
        st.session_state.serial_client = ESP32SerialClient(port_url=serial_url_input)
        if st.session_state.serial_client.connect():
            st.sidebar.success("Connected to Wokwi ESP32!")
        else:
            st.sidebar.error("Could not reach port 4000. Start Wokwi in VS Code first!")

with col_conn_btn2:
    if st.button("🔌 Disconnect", use_container_width=True):
        if st.session_state.serial_client:
            st.session_state.serial_client.disconnect()
            st.session_state.serial_client = None
            st.sidebar.info("Disconnected from ESP32.")

st.sidebar.divider()

st.sidebar.subheader("2. Camera Stream Configuration")
camera_source_type = st.sidebar.radio(
    "Camera Source",
    ["Phone Wi-Fi Stream (IP Webcam)", "Laptop Webcam (0)", "Custom Video File"],
    index=0
)

if camera_source_type == "Phone Wi-Fi Stream (IP Webcam)":
    camera_url_selected = st.sidebar.text_input(
        "Phone Stream URL",
        value=DEFAULT_CAMERA_URL,
        help="On Android, open IP Webcam app -> click 'Start Server' -> enter URL ending in /video (e.g., http://192.168.1.5:8080/video)"
    )
elif camera_source_type == "Laptop Webcam (0)":
    camera_url_selected = 0
else:
    camera_url_selected = st.sidebar.text_input(
        "Video File Path",
        value="sample_railway.mp4",
        help="Path to pre-recorded test video (.mp4, .avi)"
    )

st.sidebar.divider()

st.sidebar.subheader("3. AI Detection Parameters")
conf_val = st.sidebar.slider(
    "Confidence Threshold",
    min_value=0.20,
    max_value=0.90,
    value=DEFAULT_CONFIDENCE_THRESHOLD,
    step=0.05
)
st.session_state.detector.conf_threshold = conf_val

hold_time_val = st.sidebar.slider(
    "Alert Hold Time (Seconds)",
    min_value=1.0,
    max_value=10.0,
    value=DEFAULT_ALERT_HOLD_TIME,
    step=0.5,
    help="When a target leaves the frame, system holds ALERT for this duration before sending SAFE."
)

st.sidebar.divider()

# Start / Stop Toggle
st.sidebar.subheader("4. Execution Control")
col_start, col_stop = st.sidebar.columns(2)
with col_start:
    if st.button("▶ Start", type="primary", use_container_width=True):
        st.session_state.detection_active = True
with col_stop:
    if st.button("⏹ Stop", use_container_width=True):
        st.session_state.detection_active = False
        if st.session_state.camera_stream:
            st.session_state.camera_stream.stop()
            st.session_state.camera_stream = None
        if st.session_state.serial_client and st.session_state.serial_client.is_connected:
            st.session_state.serial_client._send_command("SAFE")

# -----------------------------------------------------------------------------
# Main Interface Layout
# -----------------------------------------------------------------------------
st.title("Railway Track Human & Animal Intrusion Detection System")
st.caption("College Educational Prototype | Real-time YOLO AI + Wokwi Virtual ESP32 Bridge")

# Section A: System Overview Metric Cards
ov_col1, ov_col2, ov_col3, ov_col4 = st.columns(4)

system_status_box = ov_col1.empty()
ai_status_box = ov_col2.empty()
esp_status_box = ov_col3.empty()
cam_status_box = ov_col4.empty()

# Section D: Railway Alert Panel (SAFE / DANGER)
alert_panel_placeholder = st.empty()

# Video Stream & Telemetry Columns
col_cam_view, col_sensors_view = st.columns([1.6, 1.0])

with col_cam_view:
    st.subheader("Live Video Stream (YOLO Inferred)")
    video_placeholder = st.empty()

with col_sensors_view:
    st.subheader("ESP32 Sensor Telemetry")
    pir_metric_box = st.empty()
    dist_metric_box = st.empty()
    sensor_alert_box = st.empty()

    st.subheader("Recent Intrusion Events")
    history_table_box = st.empty()

# -----------------------------------------------------------------------------
# Active Loop Execution
# -----------------------------------------------------------------------------
if st.session_state.detection_active:
    # 1. Initialize Camera Stream if not running or source changed
    if st.session_state.camera_stream is None or st.session_state.camera_stream.source != camera_url_selected:
        if st.session_state.camera_stream:
            st.session_state.camera_stream.stop()
        st.session_state.camera_stream = MobileCameraStream(source=camera_url_selected)
        success = st.session_state.camera_stream.start()
        if not success:
            st.error(f"Failed to connect to camera source: {camera_url_selected}. Verify Wi-Fi network and URL.")

    cam_stream = st.session_state.camera_stream
    ser_client = st.session_state.serial_client

    # Continuous frame loop
    while st.session_state.detection_active:
        frame_available, frame = cam_stream.read() if cam_stream else (False, None)

        if not frame_available or frame is None:
            video_placeholder.warning(
                f"Waiting for video frames from '{camera_url_selected}'... "
                "Ensure phone IP Webcam is running and both devices are on the same Wi-Fi."
            )
            time.sleep(0.1)
            # Yield to Streamlit event processing
            break

        # 2. YOLO Object Detection
        annotated_frame, detections, is_hazard = st.session_state.detector.detect(frame)

        # 3. Decision Logic & ESP32 State Transition
        decision_state = "SAFE"
        if ser_client and ser_client.is_connected:
            decision_state = ser_client.update_detection_state(
                is_hazard_detected=is_hazard,
                hold_time_seconds=hold_time_val
            )

        # 4. Read Telemetry from ESP32
        telemetry = {}
        if ser_client and ser_client.is_connected:
            telemetry = ser_client.get_telemetry()
        else:
            telemetry = {
                "pir": False,
                "distance": -1.0,
                "ai_connected": False,
                "ai_alert": False,
                "system_alert": False,
                "connection_state": "OFFLINE"
            }

        # 5. Update Alert History if hazard detected
        if is_hazard:
            detected_classes = ", ".join([d["class_name"] for d in detections])
            max_conf = max([d["confidence"] for d in detections]) if detections else 0.0
            now_ts = time.time()

            # Prevent adjacent duplicate entries (throttle by 2.0s)
            if not st.session_state.alert_history or (now_ts - st.session_state.alert_history[0]["_ts"] > 2.0):
                st.session_state.alert_history.insert(0, {
                    "_ts": now_ts,
                    "Time": datetime.now().strftime("%H:%M:%S"),
                    "Target Object": detected_classes,
                    "Confidence": f"{max_conf * 100:.1f}%",
                    "ESP32 Actuation": "ALERT (Red LED + Buzzer)",
                    "US-Distance": f"{telemetry.get('distance', -1.0):.1f} cm" if telemetry.get('distance', -1.0) > 0 else "N/A"
                })
                # Retain last 10 intrusions
                st.session_state.alert_history = st.session_state.alert_history[:10]

        # ---------------------------------------------------------------------
        # Render UI Elements
        # ---------------------------------------------------------------------
        # System Overview Cards
        is_esp_online = ser_client is not None and ser_client.is_connected
        is_cam_online = cam_stream is not None and cam_stream.is_connected

        system_status_box.markdown("""
        <div class="metric-panel">
            <div class="metric-panel-title">SYSTEM STATUS</div>
            <div class="metric-panel-value" style="color: #10b981;">ACTIVE</div>
        </div>
        """, unsafe_allow_html=True)

        ai_status_box.markdown(f"""
        <div class="metric-panel">
            <div class="metric-panel-title">YOLO AI INFERENCE</div>
            <div class="metric-panel-value" style="color: {'#ef4444' if is_hazard else '#10b981'};">
                {'INTRUSION' if is_hazard else 'NORMAL'}
            </div>
        </div>
        """, unsafe_allow_html=True)

        esp_status_box.markdown(f"""
        <div class="metric-panel">
            <div class="metric-panel-title">WOKWI ESP32 LINK</div>
            <div class="metric-panel-value" style="color: {'#10b981' if is_esp_online else '#9ca3af'};">
                {'ONLINE' if is_esp_online else 'OFFLINE'}
            </div>
        </div>
        """, unsafe_allow_html=True)

        cam_status_box.markdown(f"""
        <div class="metric-panel">
            <div class="metric-panel-title">CAMERA STREAM</div>
            <div class="metric-panel-value" style="color: {'#10b981' if is_cam_online else '#ef4444'};">
                {'STREAMING' if is_cam_online else 'NO FEED'}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Section D: Railway Alert Banner
        if decision_state in ("ALERT", "ALERT_HOLDING"):
            hazard_names = ", ".join([d["class_name"] for d in detections]) if detections else "Intruder (Held)"
            alert_panel_placeholder.markdown(f"""
            <div class="banner-danger">
                <span class="led-dot-red"></span>
                <strong style="font-size: 20px;">DANGER! RAILWAY TRACK INTRUSION DETECTED</strong>
                <div style="font-size: 15px; margin-top: 4px;">
                    Target: <b>{hazard_names.upper()}</b> | ESP32 State: <b>RED LED ON + BUZZER ACTIVE</b>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            alert_panel_placeholder.markdown("""
            <div class="banner-safe">
                <span class="led-dot-green"></span>
                <strong style="font-size: 20px;">TRACK CLEAR - SAFE FOR PASSAGE</strong>
                <div style="font-size: 14px; margin-top: 4px;">
                    No human or animal hazards detected on track | ESP32 State: <b>GREEN LED ON</b>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Section B: Live Video Feed
        rgb_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
        video_placeholder.image(rgb_frame, channels="RGB", use_container_width=True)

        # Section C: Sensor Monitoring Cards
        pir_state = telemetry.get("pir", False)
        dist_state = telemetry.get("distance", -1.0)
        sys_alert = telemetry.get("system_alert", False)

        pir_metric_box.markdown(f"""
        <div class="metric-panel" style="margin-bottom: 10px;">
            <div class="metric-panel-title">PIR MOTION SENSOR (GPIO 27)</div>
            <div class="metric-panel-value" style="color: {'#ef4444' if pir_state else '#10b981'};">
                {'MOTION DETECTED' if pir_state else 'CLEAR'}
            </div>
        </div>
        """, unsafe_allow_html=True)

        dist_metric_box.markdown(f"""
        <div class="metric-panel" style="margin-bottom: 10px;">
            <div class="metric-panel-title">ULTRASONIC SENSOR (HC-SR04)</div>
            <div class="metric-panel-value" style="color: {'#ef4444' if (0 < dist_state <= 50) else '#38bdf8'};">
                {f"{dist_state:.1f} cm" if dist_state > 0 else "Out of Range"}
            </div>
        </div>
        """, unsafe_allow_html=True)

        sensor_alert_box.markdown(f"""
        <div class="metric-panel" style="margin-bottom: 10px;">
            <div class="metric-panel-title">ESP32 ACTUATOR STATE</div>
            <div class="metric-panel-value" style="color: {'#ef4444' if sys_alert else '#10b981'};">
                {'ALERT (Buzzer ON)' if sys_alert else 'SAFE (Green LED)'}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Intrusion History Table
        if st.session_state.alert_history:
            display_records = [
                {k: v for k, v in rec.items() if not k.startswith("_")}
                for rec in st.session_state.alert_history
            ]
            history_table_box.table(display_records)
        else:
            history_table_box.info("No intrusions recorded yet.")

        # Yield to allow UI interactions
        time.sleep(0.03)

else:
    # Standby State
    system_status_box.markdown("""
    <div class="metric-panel">
        <div class="metric-panel-title">SYSTEM STATUS</div>
        <div class="metric-panel-value" style="color: #9ca3af;">STANDBY</div>
    </div>
    """, unsafe_allow_html=True)

    ai_status_box.markdown("""
    <div class="metric-panel">
        <div class="metric-panel-title">YOLO AI INFERENCE</div>
        <div class="metric-panel-value" style="color: #9ca3af;">PAUSED</div>
    </div>
    """, unsafe_allow_html=True)

    esp_status_box.markdown("""
    <div class="metric-panel">
        <div class="metric-panel-title">WOKWI ESP32 LINK</div>
        <div class="metric-panel-value" style="color: #9ca3af;">DISCONNECTED</div>
    </div>
    """, unsafe_allow_html=True)

    cam_status_box.markdown("""
    <div class="metric-panel">
        <div class="metric-panel-title">CAMERA STREAM</div>
        <div class="metric-panel-value" style="color: #9ca3af;">IDLE</div>
    </div>
    """, unsafe_allow_html=True)

    alert_panel_placeholder.markdown("""
    <div class="banner-safe">
        <span class="led-dot-green"></span>
        <strong style="font-size: 18px;">SYSTEM ON STANDBY</strong>
        <div style="font-size: 14px; margin-top: 4px;">Click '▶ Start' in the sidebar to activate real-time detection.</div>
    </div>
    """, unsafe_allow_html=True)

    video_placeholder.info("Video streaming is currently stopped. Click '▶ Start' in the sidebar to begin monitoring.")
    pir_metric_box.empty()
    dist_metric_box.empty()
    sensor_alert_box.empty()
    history_table_box.info("No active events in standby mode.")

