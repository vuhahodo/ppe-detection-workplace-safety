from __future__ import annotations

import cv2
import numpy as np


class RoiManager:
    def __init__(self, database, camera_id: str):
        self.database = database
        self.camera_id = camera_id
        self.roi = database.get_camera_roi(camera_id)

    def set_roi(self, roi: list[list[int]]) -> None:
        self.roi = roi
        self.database.save_roi(self.camera_id, roi)

    def reset_roi(self) -> None:
        self.set_roi([])

    def contains_point(self, x: float, y: float, frame_shape=None) -> bool:
        if not self.roi or len(self.roi) < 3:
            return True
        contour = np.array(self.roi, dtype=np.int32)
        return cv2.pointPolygonTest(contour, (float(x), float(y)), False) >= 0

    def box_in_roi(self, bbox: list[float], frame_shape=None) -> bool:
        if not self.roi or len(self.roi) < 3:
            return True
        x1, y1, x2, y2 = bbox
        margin = 12
        if frame_shape is not None:
            h, w = frame_shape[:2]
            margin = max(12, int(min(w, h) * 0.02))
        x1 -= margin
        y1 -= margin
        x2 += margin
        y2 += margin
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        width = x2 - x1
        height = y2 - y1
        points = [
            (cx, cy),
            (x1, y1),
            (x2, y1),
            (x2, y2),
            (x1, y2),
            ((x1 + x2) / 2, y1),
            ((x1 + x2) / 2, y2),
        ]
        for ratio in (0.55, 0.7, 0.85, 1.0):
            y = y1 + height * ratio
            points.extend(
                [
                    (x1 + width * 0.25, y),
                    (x1 + width * 0.5, y),
                    (x1 + width * 0.75, y),
                ]
            )
        if any(self.contains_point(x, y, frame_shape) for x, y in points):
            return True
        return self._roi_vertex_in_box(x1, y1, x2, y2)

    def _roi_vertex_in_box(self, x1: float, y1: float, x2: float, y2: float) -> bool:
        lower_y = y1 + (y2 - y1) * 0.45
        return any(x1 <= x <= x2 and lower_y <= y <= y2 for x, y in self.roi)
