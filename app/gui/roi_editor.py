from __future__ import annotations

import cv2
import yaml
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.core.config_loader import DEFAULT_CONFIG_PATH
from app.gui.image_label import ImageLabel
from app.utils.drawing import draw_roi


class RoiEditor(QWidget):
    def __init__(self, context, camera_panel=None):
        super().__init__()
        self.ctx = context
        self.camera_panel = camera_panel
        self.points: list[list[int]] = list(self.ctx.roi_manager.roi or [])
        self.base_frame = None
        self.image = ImageLabel()
        self.image.point_clicked.connect(self.add_point)
        self.status = QLabel("Capture a frame, click polygon points, then save ROI.")

        capture_btn = QPushButton("Use Current Frame")
        save_btn = QPushButton("Save ROI")
        reset_btn = QPushButton("Reset ROI")
        undo_btn = QPushButton("Undo Point")
        capture_btn.clicked.connect(self.capture_frame)
        save_btn.clicked.connect(self.save_roi)
        reset_btn.clicked.connect(self.reset_roi)
        undo_btn.clicked.connect(self.undo_point)

        bar = QHBoxLayout()
        for btn in (capture_btn, save_btn, reset_btn, undo_btn):
            bar.addWidget(btn)
        bar.addWidget(self.status)
        bar.addStretch()
        layout = QVBoxLayout(self)
        layout.addLayout(bar)
        layout.addWidget(self.image, 1)

    def capture_frame(self) -> None:
        if self.camera_panel and self.camera_panel.last_frame is not None:
            self.base_frame = self.camera_panel.last_frame.copy()
        else:
            source = self.ctx.camera_source
            try:
                source = int(source)
            except (TypeError, ValueError):
                pass
            cap = cv2.VideoCapture(source)
            ok, frame = cap.read()
            cap.release()
            if not ok:
                self.status.setText("Cannot capture frame.")
                return
            self.base_frame = frame
        self.redraw()

    def add_point(self, x: int, y: int) -> None:
        if self.base_frame is None:
            self.status.setText("Capture a frame first.")
            return
        self.points.append([x, y])
        self.redraw()

    def undo_point(self) -> None:
        if self.points:
            self.points.pop()
            self.redraw()

    def reset_roi(self) -> None:
        self.points = []
        self.ctx.roi_manager.reset_roi()
        self.export_roi_to_config([])
        self.redraw()
        self.status.setText("ROI reset.")

    def save_roi(self) -> None:
        if len(self.points) < 3:
            self.status.setText("ROI needs at least 3 points.")
            return
        self.ctx.roi_manager.set_roi(self.points)
        self.export_roi_to_config(self.points)
        self.status.setText("ROI saved to SQLite and config.yaml.")

    def export_roi_to_config(self, roi: list[list[int]]) -> None:
        with DEFAULT_CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        data.setdefault("camera", {})["roi"] = roi
        with DEFAULT_CONFIG_PATH.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)

    def redraw(self) -> None:
        if self.base_frame is None:
            return
        frame = draw_roi(self.base_frame.copy(), self.points)
        for x, y in self.points:
            cv2.circle(frame, (x, y), 5, (255, 255, 255), -1)
        self.image.set_cv_image(frame)
