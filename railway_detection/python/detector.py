"""
YOLO Object Detector
Specialized for detecting humans (person) and animals (cow, dog) on railway tracks.
Uses Ultralytics YOLO nano (yolov8n.pt) for high FPS on laptops with 8GB RAM.
"""

import cv2
import numpy as np
from typing import List, Dict, Any, Tuple
from config import YOLO_MODEL_NAME, TARGET_CLASSES, DETECTION_CONFIDENCE_THRESHOLD

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None


class RailwayTrackDetector:
    def __init__(self, model_path: str = YOLO_MODEL_NAME, conf_thresh: float = DETECTION_CONFIDENCE_THRESHOLD):
        self.model_path = model_path
        self.conf_thresh = conf_thresh
        self.target_classes = TARGET_CLASSES
        self.model = None

        self._load_model()

    def _load_model(self):
        """Load YOLO model lazily with fallback handling."""
        if YOLO is None:
            print("[WARNING] ultralytics package is not installed. Run: pip install ultralytics")
            return

        try:
            print(f"[INFO] Loading lightweight YOLO model '{self.model_path}'...")
            self.model = YOLO(self.model_path)
            print("[INFO] YOLO model loaded successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to load YOLO model: {e}")
            self.model = None

    def detect(self, frame: np.ndarray) -> Tuple[np.ndarray, List[Dict[str, Any]], bool]:
        """
        Run inference on an OpenCV frame.
        
        Returns:
            annotated_frame: Frame with drawn bounding boxes and labels
            detections: List of detected objects with class name, confidence, box
            is_obstacle_detected: True if at least one person/cow/dog was found
        """
        if self.model is None or frame is None:
            return frame, [], False

        detections = []
        is_obstacle_detected = False
        annotated_frame = frame.copy()

        # Run inference filtering for target class indices: [0, 16, 19]
        target_ids = list(self.target_classes.keys())
        
        # Verbose=False keeps the console clean
        results = self.model.predict(
            source=frame,
            classes=target_ids,
            conf=self.conf_thresh,
            verbose=False
        )

        if not results:
            return annotated_frame, detections, is_obstacle_detected

        result = results[0]
        boxes = result.boxes

        if boxes is not None and len(boxes) > 0:
            for box in boxes:
                cls_id = int(box.cls[0].item())
                confidence = float(box.conf[0].item())
                coords = box.xyxy[0].cpu().numpy().astype(int)
                x1, y1, x2, y2 = coords[0], coords[1], coords[2], coords[3]

                class_name = self.target_classes.get(cls_id, f"Class {cls_id}")
                is_obstacle_detected = True

                detections.append({
                    "class_id": cls_id,
                    "class_name": class_name,
                    "confidence": confidence,
                    "bbox": (x1, y1, x2, y2)
                })

                # Visual Bounding Box (Red for Alert)
                box_color = (0, 0, 255)  # BGR Red
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), box_color, 2)

                # Label Badge
                label = f"{class_name.upper()} {confidence * 100:.1f}%"
                (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                cv2.rectangle(annotated_frame, (x1, y1 - 25), (x1 + w + 10, y1), box_color, -1)
                cv2.putText(
                    annotated_frame,
                    label,
                    (x1 + 5, y1 - 7),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA
                )

        return annotated_frame, detections, is_obstacle_detected

