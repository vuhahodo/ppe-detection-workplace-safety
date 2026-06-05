from __future__ import annotations

import cv2
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.gui.image_label import ImageLabel
from app.utils.drawing import draw_detections


class UploadRoi:
    def __init__(self):
        self.roi: list[list[int]] = []

    def box_in_roi(self, bbox: list[float], frame_shape=None) -> bool:
        if not self.roi or len(self.roi) < 3:
            return True
        import cv2
        import numpy as np

        x1, y1, x2, y2 = bbox
        h, w = frame_shape[:2] if frame_shape is not None else (0, 0)
        margin = max(12, int(min(w, h) * 0.02)) if w and h else 12
        x1 -= margin
        y1 -= margin
        x2 += margin
        y2 += margin
        width = x2 - x1
        height = y2 - y1
        points = [
            ((x1 + x2) / 2, (y1 + y2) / 2),
            (x1, y1),
            (x2, y1),
            (x2, y2),
            (x1, y2),
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
        contour = np.array(self.roi, dtype=np.int32)
        if any(cv2.pointPolygonTest(contour, (float(x), float(y)), False) >= 0 for x, y in points):
            return True
        lower_y = y1 + height * 0.45
        return any(x1 <= x <= x2 and lower_y <= y <= y2 for x, y in self.roi)


class UploadPanel(QWidget):
    def __init__(self, context):
        super().__init__()
        self.ctx = context
        self.image = ImageLabel()
        self.image.point_clicked.connect(self.add_roi_point)
        self.status = QLabel("Choose an image or video. ROI defaults to full frame.")
        self.video_capture = None
        self.current_frame = None
        self.current_detections: list[dict] = []
        self.current_source_type = "image"
        self.upload_roi = UploadRoi()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_video_frame)

        image_btn = QPushButton("Open Image")
        video_btn = QPushButton("Open Video")
        stop_btn = QPushButton("Stop Video")
        clear_roi_btn = QPushButton("Full Frame ROI")
        undo_roi_btn = QPushButton("Undo ROI Point")
        reanalyze_btn = QPushButton("Re-analyze")
        image_btn.clicked.connect(self.open_image)
        video_btn.clicked.connect(self.open_video)
        stop_btn.clicked.connect(self.stop_video)
        clear_roi_btn.clicked.connect(self.clear_roi)
        undo_roi_btn.clicked.connect(self.undo_roi_point)
        reanalyze_btn.clicked.connect(lambda: self.process_current_frame(save_event=True))

        bar = QHBoxLayout()
        bar.addWidget(image_btn)
        bar.addWidget(video_btn)
        bar.addWidget(stop_btn)
        bar.addWidget(clear_roi_btn)
        bar.addWidget(undo_roi_btn)
        bar.addWidget(reanalyze_btn)
        bar.addWidget(self.status)
        bar.addStretch()
        layout = QVBoxLayout(self)
        layout.addLayout(bar)
        layout.addWidget(self.image, 1)

    def open_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.jpg *.jpeg *.png *.bmp *.webp)")
        if not path:
            return
        frame = cv2.imread(path)
        if frame is None:
            self.status.setText("Cannot read image.")
            return
        self.current_source_type = "image"
        self.current_frame = frame
        self.process_current_frame(save_event=True)

    def open_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Video", "", "Videos (*.mp4 *.avi *.mov *.mkv)")
        if not path:
            return
        self.stop_video()
        self.video_capture = cv2.VideoCapture(path)
        if not self.video_capture.isOpened():
            self.status.setText("Cannot open video.")
            return
        self.current_source_type = "video"
        self.timer.start(30)

    def stop_video(self) -> None:
        self.timer.stop()
        if self.video_capture:
            self.video_capture.release()
            self.video_capture = None

    def next_video_frame(self) -> None:
        if not self.video_capture:
            return
        ok, frame = self.video_capture.read()
        if not ok:
            self.stop_video()
            self.status.setText("Video finished.")
            return
        self.current_frame = frame
        self.process_current_frame(save_event=True)

    def add_roi_point(self, x: int, y: int) -> None:
        if self.current_frame is None:
            self.status.setText("Open an image or video first.")
            return
        self.upload_roi.roi.append([x, y])
        self.render_current()
        self.status.setText(f"Upload ROI points: {len(self.upload_roi.roi)}. Re-analyze to apply.")

    def undo_roi_point(self) -> None:
        if self.upload_roi.roi:
            self.upload_roi.roi.pop()
        self.render_current()

    def clear_roi(self) -> None:
        self.upload_roi.roi = []
        self.render_current()
        self.status.setText("Upload ROI reset to full frame.")

    def process_current_frame(self, save_event: bool) -> None:
        if self.current_frame is None:
            return
        frame = self.current_frame
        image_mode = self.current_source_type == "image"
        try:
            detections = self.ctx.detector.predict(frame)
            self.current_detections = detections
            annotated = draw_detections(frame, detections, self.upload_roi.roi)
            violation = self.ctx.violation_engine.analyze(
                detections,
                self.upload_roi,
                f"{self.ctx.camera_id}:{self.current_source_type}",
                image_mode=image_mode,
                frame_shape=frame.shape,
            )
            if save_event and violation["should_create_event"]:
                event = self.ctx.event_manager.create_event(
                    self.ctx.camera_id,
                    self.ctx.camera_name,
                    violation,
                    frame.copy(),
                    annotated.copy(),
                    source_type=self.current_source_type,
                )
                self.status.setText(f"Event saved: {event['event_id']}")
            else:
                scope = "selected ROI" if len(self.upload_roi.roi) >= 3 else "full frame"
                self.status.setText(f"Violations in {scope}: {violation['violation_count']}")
            self.image.set_cv_image(annotated)
        except Exception as exc:
            self.status.setText(str(exc))
            self.image.set_cv_image(frame)

    def render_current(self) -> None:
        if self.current_frame is None:
            return
        self.image.set_cv_image(draw_detections(self.current_frame, self.current_detections, self.upload_roi.roi))
