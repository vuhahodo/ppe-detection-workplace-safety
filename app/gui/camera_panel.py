from __future__ import annotations

import time

import cv2
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.core.roi_manager import RoiManager
from app.gui.image_label import ImageLabel
from app.utils.drawing import draw_detections


class CameraPanel(QWidget):
    def __init__(self, context):
        super().__init__()
        self.ctx = context
        self.capture = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_frame)
        self.last_frame = None
        self.status = QLabel("Stopped")
        self.image = ImageLabel()
        self.mirror_fix = bool(self.ctx.config.get("display", {}).get("flip_webcam_horizontal", True))
        self.start_btn = QPushButton("Start Camera")
        self.stop_btn = QPushButton("Stop")
        self.start_btn.clicked.connect(self.start_camera)
        self.stop_btn.clicked.connect(self.stop_camera)

        buttons = QHBoxLayout()
        buttons.addWidget(self.start_btn)
        buttons.addWidget(self.stop_btn)
        buttons.addWidget(self.status)
        buttons.addStretch()
        layout = QVBoxLayout(self)
        layout.addLayout(buttons)
        layout.addWidget(self.image, 1)

    def start_camera(self) -> None:
        source = self.ctx.camera_source
        try:
            source = int(source)
        except (TypeError, ValueError):
            pass
        self.capture = cv2.VideoCapture(source)
        if not self.capture.isOpened():
            self.status.setText(f"Cannot open camera: {source}")
            return
        self.status.setText("Running")
        self.timer.start(30)

    def stop_camera(self) -> None:
        self.timer.stop()
        if self.capture:
            self.capture.release()
            self.capture = None
        self.status.setText("Stopped")

    def next_frame(self) -> None:
        if not self.capture:
            return
        ok, frame = self.capture.read()
        if not ok:
            self.status.setText("Frame read failed")
            return
        if self.mirror_fix:
            frame = cv2.flip(frame, 1)
        self.last_frame = frame.copy()
        try:
            detections = self.ctx.detector.predict(frame)
            roi = self.ctx.roi_manager.roi
            annotated = draw_detections(frame, detections, roi)
            violation = self.ctx.violation_engine.analyze(
                detections, self.ctx.roi_manager, self.ctx.camera_id, frame_shape=frame.shape
            )
            if violation["should_create_event"]:
                event = self.ctx.event_manager.create_event(
                    self.ctx.camera_id,
                    self.ctx.camera_name,
                    violation,
                    frame.copy(),
                    annotated.copy(),
                    source_type="camera",
                )
                self.status.setText(f"Event saved: {event['event_id']}")
            else:
                self.status.setText(
                    f"Running | current violations: {violation['violation_count']} | {time.strftime('%H:%M:%S')}"
                )
            self.image.set_cv_image(annotated)
        except Exception as exc:
            self.status.setText(str(exc))
            self.image.set_cv_image(frame)

    def closeEvent(self, event) -> None:
        self.stop_camera()
        super().closeEvent(event)
