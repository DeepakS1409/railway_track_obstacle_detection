"""
Ultralytics YOLO Object Detector
Optimized for Railway Track Intrusion Detection:
Target classes: Person (0), Dog (16), Cow (19)
Uses CPU-friendly YOLOv8 nano model suitable for 8GB RAM laptops.
"""

import os
import cv2
import numpy as np
import logging
from typing import List, Dict, Any, Tuple
from config import TARGET_CLASSES, DEFAULT_CONFIDENCE_THRESHOLD, DEFAULT_MODEL_PATH

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [Detector] %(message)s")
logger = logging.getLogger("Detector")

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None


class RailwayTrackDetector:
    """YOLOv8 Nano inference engine for Human & Animal Detection on Railway Tracks."""

    def __init__(self, model_path: str = str(DEFAULT_MODEL_PATH), conf_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD):
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.target_classes = TARGET_CLASSES
        self.model = None
        self.is_ready = False
        self.last_error = ""

        self._load_model()

    def _load_model(self):
        """Load YOLO model weights. Ultralytics automatically downloads yolov8n if not cached."""
        if YOLO is None:
            self.last_error = "Ultralytics package is not installed. Run: pip install ultralytics"
            logger.error(self.last_error)
            return

        try:
            logger.info(f"Loading YOLO model weights from '{self.model_path}'...")
            
            # If specified path does not exist, use default 'yolov8n.pt' which auto-downloads cleanly
            if not os.path.exists(self.model_path):
                self.model = YOLO("yolov8n.pt")
                # Save into models folder for local caching
                try:
                    os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
                except Exception:
                    pass
            else:
                self.model = YOLO(self.model_path)

            self.is_ready = True
            logger.info("YOLOv8 nano model loaded successfully and ready for inference.")

        except Exception as e:
            self.last_error = f"Failed to load YOLO model: {e}"
            logger.error(self.last_error)
            self.is_ready = False

    def detect(self, frame: np.ndarray) -> Tuple[np.ndarray, List[Dict[str, Any]], bool]:
        """
        Execute YOLO inference on a single video frame.

        Returns:
            annotated_frame: Frame with visual bounding boxes, class labels, and confidence tags.
            detections: List of target detection dictionaries.
            is_hazard_detected: True if target human or animal is detected above threshold.
        """
        if not self.is_ready or self.model is None or frame is None:
            return frame, [], False

        detections: List[Dict[str, Any]] = []
        is_hazard_detected = False
        annotated_frame = frame.copy()

        # Class IDs for target objects: 0 (person), 16 (dog), 19 (cow)
        target_class_ids = list(self.target_classes.keys())

        try:
            # Run inference targeting only specified classes for minimum CPU overhead
            results = self.model.predict(
                source=frame,
                classes=target_class_ids,
                conf=self.conf_threshold,
                device="cpu",
                verbose=False
            )

            if not results:
                return annotated_frame, detections, False

            result = results[0]
            boxes = result.boxes

            if boxes is not None and len(boxes) > 0:
                for box in boxes:
                    cls_id = int(box.cls[0].item())
                    confidence = float(box.conf[0].item())
                    coords = box.xyxy[0].cpu().numpy().astype(int)
                    x1, y1, x2, y2 = coords[0], coords[1], coords[2], coords[3]

                    class_name = self.target_classes.get(cls_id, f"ID_{cls_id}")
                    is_hazard_detected = True

                    detections.append({
                        "class_id": cls_id,
                        "class_name": class_name,
                        "confidence": confidence,
                        "bbox": (x1, y1, x2, y2)
                    })

                    # High-visibility Red Alert Bounding Box (BGR: 0, 0, 255)
                    box_color = (0, 0, 255)
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), box_color, 2)

                    # Top Badge with Target Name & Confidence
                    badge_text = f"{class_name.upper()}: {confidence * 100:.1f}%"
                    (tw, th), _ = cv2.getTextSize(badge_text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
                    cv2.rectangle(
                        annotated_frame,
                        (x1, max(0, y1 - 25)),
                        (x1 + tw + 10, y1),
                        box_color,
                        -1
                    )
                    cv2.putText(
                        annotated_frame,
                        badge_text,
                        (x1 + 5, max(15, y1 - 7)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (255, 255, 255),
                        2,
                        cv2.LINE_AA
                    )

        except Exception as e:
            logger.error(f"Inference error: {e}")
            return frame, [], False

        return annotated_frame, detections, is_hazard_detected

