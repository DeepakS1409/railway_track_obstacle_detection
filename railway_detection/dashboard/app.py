"""
Railway Track Human & Animal Detection System - Modern Streamlit Monitoring Dashboard
Professional dark-themed control center displaying real-time video feed, YOLO detections,
and live ESP32 hardware telemetry.
"""

import sys
import os
import time
from datetime import datetime
import streamlit as st
import cv2
import numpy as np

# Ensure python directory is in module search path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
PYTHON_DIR = os.path.join(PROJECT_ROOT, "python")
if PYTHON_DIR not in sys.path:
    sys.path.insert(0, PYTHON_DIR)

from serial_manager import SerialManager
from detector import RailwayTrackDetector
from camera import VideoStreamHandler
from config import DEFAULT_SERIAL_PORT, TARGET_CLASSES, DETECTION_CONFIDENCE_THRESHOLD

# -----------------------------------------------------------------------------
# Streamlit Page Setup
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Railway Track Safety Monitor",
    page_icon="🚆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Dark Theme Styling
st.markdown("""
<style>
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    .metric-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .metric-val {
        font-size: 26px;
        font-weight: 700;
        margin-top: 6px;
    }
    .status-alert {
        background: linear-gradient(135deg, #7a1c1c, #4a0f0f);
        border: 2px solid #f85149;
        color: #ff7b72;
        border-radius: 8px;
        padding: 18px;
        text-align: center;
        animation: pulse 1.5s infinite;
    }
    .status-safe {
        background: linear-gradient(135deg, #134e2c, #0a2d18);
        border: 2px solid #2ea043;
        color: #56d364;
        border-radius: 8px;
        padding: 18px;
        text-align: center;
    }
    .indicator-circle-red {
        height: 18px;
        width: 18px;
        background-color: #f85149;
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 12px #f85149;
    }
    .indicator-circle-green {
        height: 18px;
        width: 18px;
        background-color: #2ea043;
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 12px #2ea043;
    }
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.02); }
        100% { transform: scale(1); }
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Session State Initialization
# -----------------------------------------------------------------------------
if "alert_history" not in st.session_state:
    st.session_state.alert_history = []

if "serial_manager" not in st.session_state:
    st.session_state.serial_manager = None

if "detector" not in st.session_state:
    st.session_state.detector = RailwayTrackDetector(conf_thresh=DETECTION_CONFIDENCE_THRESHOLD)

# -----------------------------------------------------------------------------
# Sidebar Configuration
# -----------------------------------------------------------------------------
st.sidebar.title("🚆 Control Settings")

st.sidebar.subheader("Hardware & Simulation Link")
serial_port_input = st.sidebar.text_input(
    "Serial Port / Wokwi RFC2217 URL",
    value=DEFAULT_SERIAL_PORT,
    help="Use 'rfc2217://localhost:4000' for Wokwi VS Code extension or 'COM3' for physical USB."
)

col_s1, col_s2 = st.sidebar.columns(2)
with col_s1:
    if st.button("🔗 Connect", use_container_width=True):
        if st.session_state.serial_manager:
            st.session_state.serial_manager.disconnect()
        st.session_state.serial_manager = SerialManager(port=serial_port_input)
        if st.session_state.serial_manager.connect():
            st.sidebar.success("Connected!")
        else:
            st.sidebar.error("Failed to connect.")

with col_s2:
    if st.button("🔌 Disconnect", use_container_width=True):
        if st.session_state.serial_manager:
            st.session_state.serial_manager.disconnect()
            st.session_state.serial_manager = None
            st.sidebar.info("Disconnected.")

st.sidebar.divider()

st.sidebar.subheader("Camera / Video Input")
camera_mode = st.sidebar.selectbox(
    "Select Input Source",
    ["Laptop Webcam (0)", "Phone Camera Stream (IP Webcam)", "Custom Video File / Sample"]
)

stream_source = 0
if camera_mode == "Laptop Webcam (0)":
    stream_source = 0
elif camera_mode == "Phone Camera Stream (IP Webcam)":
    stream_source = st.sidebar.text_input(
        "IP Stream URL",
        value="http://192.168.1.100:8080/video",
        help="Install 'IP Webcam' on Android, start server, and paste URL ending in /video"
    )
elif camera_mode == "Custom Video File / Sample":
    stream_source = st.sidebar.text_input(
        "Video File Path",
        value="test_video.mp4",
        help="Local file path to an .mp4 or .avi file"
    )

conf_slider = st.sidebar.slider(
    "Detection Confidence Threshold",
    min_value=0.20,
    max_value=0.90,
    value=DETECTION_CONFIDENCE_THRESHOLD,
    step=0.05
)
st.session_state.detector.conf_thresh = conf_slider

is_monitoring = st.sidebar.toggle("▶ Start Live Monitoring", value=False)

# -----------------------------------------------------------------------------
# Main Dashboard Layout
# -----------------------------------------------------------------------------
st.title("Railway Track Human & Animal Detection System")
st.caption("College Prototype | Multi-Sensor ESP32 Telemetry & Real-Time Computer Vision")

# Top Status Indicators
status_col, pir_col, dist_col, link_col = st.columns([1.5, 1, 1, 1])

# Dynamic place holders
status_placeholder = status_col.empty()
pir_placeholder = pir_col.empty()
dist_placeholder = dist_col.empty()
link_placeholder = link_col.empty()

# Video & Telemetry Columns
video_col, history_col = st.columns([2, 1])

with video_col:
    st.subheader("Live Tracking Video Feed")
    video_placeholder = st.empty()

with history_col:
    st.subheader("Event & Alert Log")
    history_placeholder = st.empty()

# -----------------------------------------------------------------------------
# Live Processing Loop
# -----------------------------------------------------------------------------
if is_monitoring:
    cam = VideoStreamHandler(source=stream_source)
    sm = st.session_state.serial_manager

    while is_monitoring:
        ret, frame = cam.read_frame()
        if not ret or frame is None:
            video_placeholder.warning("Waiting for video stream... Check camera source.")
            time.sleep(0.2)
            continue

        # YOLO inference
        annotated_frame, detections, obstacle_found = st.session_state.detector.detect(frame)

        # Telemetry from ESP32
        telemetry = {"distance": -1.0, "pir": 0, "state": "DISCONNECTED", "source": "OFFLINE"}
        esp_online = False
        if sm and sm.is_connected():
            esp_online = True
            telemetry = sm.get_latest_telemetry()
            if obstacle_found:
                sm.send_alert()
            else:
                sm.send_safe()

        # Update Alert History if an obstacle is detected
        if obstacle_found:
            detected_names = ", ".join([d["class_name"] for d in detections])
            top_conf = max([d["confidence"] for d in detections])
            now_str = datetime.now().strftime("%H:%M:%S")

            # Avoid spamming history on adjacent frames
            if not st.session_state.alert_history or (
                time.time() - st.session_state.alert_history[0]["_raw_time"] > 2.0
            ):
                st.session_state.alert_history.insert(0, {
                    "_raw_time": time.time(),
                    "Time": now_str,
                    "Target": detected_names,
                    "Confidence": f"{top_conf * 100:.1f}%",
                    "Distance": f"{telemetry.get('distance', -1):.1f} cm" if telemetry.get('distance', -1) > 0 else "N/A"
                })
                # Keep last 15 records
                st.session_state.alert_history = st.session_state.alert_history[:15]

        # Update Status Card
        if obstacle_found:
            detected_names = ", ".join([d["class_name"] for d in detections])
            top_conf = max([d["confidence"] for d in detections])
            status_placeholder.markdown(f"""
            <div class="status-alert">
                <span class="indicator-circle-red"></span> <strong>TRACK OBSTACLE DETECTED!</strong>
                <div style="font-size: 14px; margin-top: 4px;">Detected: <b>{detected_names}</b> ({top_conf*100:.1f}%)</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            status_placeholder.markdown("""
            <div class="status-safe">
                <span class="indicator-circle-green"></span> <strong>TRACK CLEAR & SAFE</strong>
                <div style="font-size: 14px; margin-top: 4px;">No human or animal hazards detected</div>
            </div>
            """, unsafe_allow_html=True)

        # Update PIR Card
        pir_active = telemetry.get("pir", 0) == 1
        pir_placeholder.markdown(f"""
        <div class="metric-card">
            <div style="font-size: 13px; color: #8b949e;">PIR SENSOR</div>
            <div class="metric-val" style="color: {'#ff7b72' if pir_active else '#56d364'};">
                {'MOTION' if pir_active else 'CLEAR'}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Update Distance Card
        dist_val = telemetry.get("distance", -1.0)
        dist_display = f"{dist_val:.1f} cm" if dist_val > 0 else "Out of Range"
        dist_placeholder.markdown(f"""
        <div class="metric-card">
            <div style="font-size: 13px; color: #8b949e;">ULTRASONIC (HC-SR04)</div>
            <div class="metric-val" style="color: {'#ff7b72' if (0 < dist_val <= 50) else '#58a6ff'};">
                {dist_display}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Update Hardware Link Card
        link_placeholder.markdown(f"""
        <div class="metric-card">
            <div style="font-size: 13px; color: #8b949e;">ESP32 LINK</div>
            <div class="metric-val" style="color: {'#56d364' if esp_online else '#8b949e'};">
                {'ONLINE' if esp_online else 'OFFLINE'}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Render Video Frame (Convert BGR to RGB)
        rgb_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
        video_placeholder.image(rgb_frame, channels="RGB", use_container_width=True)

        # Render Alert History Table
        if st.session_state.alert_history:
            display_data = [
                {k: v for k, v in item.items() if not k.startswith("_")}
                for item in st.session_state.alert_history
            ]
            history_placeholder.table(display_data)
        else:
            history_placeholder.info("No alert events recorded yet.")

        # Brief sleep to yield CPU
        time.sleep(0.03)

    cam.release()
else:
    # Idle State Placeholders
    status_placeholder.markdown("""
    <div class="status-safe">
        <span class="indicator-circle-green"></span> <strong>SYSTEM STANDBY</strong>
        <div style="font-size: 14px; margin-top: 4px;">Toggle 'Start Live Monitoring' in the sidebar to begin.</div>
    </div>
    """, unsafe_allow_html=True)

    pir_placeholder.markdown("""
    <div class="metric-card">
        <div style="font-size: 13px; color: #8b949e;">PIR SENSOR</div>
        <div class="metric-val" style="color: #8b949e;">STANDBY</div>
    </div>
    """, unsafe_allow_html=True)

    dist_placeholder.markdown("""
    <div class="metric-card">
        <div style="font-size: 13px; color: #8b949e;">ULTRASONIC (HC-SR04)</div>
        <div class="metric-val" style="color: #8b949e;">STANDBY</div>
    </div>
    """, unsafe_allow_html=True)

    link_placeholder.markdown("""
    <div class="metric-card">
        <div style="font-size: 13px; color: #8b949e;">ESP32 LINK</div>
        <div class="metric-val" style="color: #8b949e;">DISCONNECTED</div>
    </div>
    """, unsafe_allow_html=True)

    video_placeholder.info("Video feed is currently stopped. Toggle 'Start Live Monitoring' in the sidebar.")
    history_placeholder.info("No alert events recorded yet.")

