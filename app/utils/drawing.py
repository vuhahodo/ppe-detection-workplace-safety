from __future__ import annotations

import cv2
import numpy as np


COLORS = {
    "person": (70, 170, 255),
    "helmet": (80, 200, 120),
    "no_helmet": (40, 40, 230),
    "no_vest": (40, 130, 230),
    "no_glove": (200, 90, 210),
}


def draw_roi(frame: np.ndarray, roi: list[list[int]] | None) -> np.ndarray:
    if not roi:
        return frame
    pts = np.array(roi, dtype=np.int32)
    cv2.polylines(frame, [pts], isClosed=True, color=(255, 210, 70), thickness=2)
    overlay = frame.copy()
    cv2.fillPoly(overlay, [pts], color=(255, 210, 70))
    return cv2.addWeighted(overlay, 0.12, frame, 0.88, 0)


def draw_detections(frame: np.ndarray, detections: list[dict], roi: list[list[int]] | None = None) -> np.ndarray:
    annotated = frame.copy()
    for det in detections:
        x1, y1, x2, y2 = [int(v) for v in det["bbox"]]
        class_name = det["class_name"]
        conf = det["confidence"]
        color = COLORS.get(class_name, (230, 230, 230))
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        label = f"{class_name} {conf:.2f}"
        cv2.putText(annotated, label, (x1, max(20, y1 - 7)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
    return draw_roi(annotated, roi)


def draw_event_header(frame: np.ndarray, camera_name: str, timestamp: str, violation_count: int) -> np.ndarray:
    text = f"{camera_name} | {timestamp} | no_helmet: {violation_count}"
    cv2.rectangle(frame, (0, 0), (frame.shape[1], 34), (25, 25, 25), -1)
    cv2.putText(frame, text, (10, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2)
    return frame
