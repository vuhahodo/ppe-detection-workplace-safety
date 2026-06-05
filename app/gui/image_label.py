from __future__ import annotations

import cv2
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QImage, QMouseEvent, QPixmap
from PyQt5.QtWidgets import QLabel, QSizePolicy


class ImageLabel(QLabel):
    point_clicked = pyqtSignal(int, int)

    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(720, 420)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("background:#15171a;color:#d8dee9;border:1px solid #30343b;")
        self._frame_shape: tuple[int, int] | None = None
        self._pixmap_size: tuple[int, int] | None = None

    def set_cv_image(self, frame) -> None:
        self._frame_shape = (frame.shape[1], frame.shape[0])
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        image = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(image).scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._pixmap_size = (pixmap.width(), pixmap.height())
        self.setPixmap(pixmap)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self._frame_shape or not self._pixmap_size or not self.pixmap():
            return
        label_w, label_h = self.width(), self.height()
        pix_w, pix_h = self._pixmap_size
        off_x = (label_w - pix_w) / 2
        off_y = (label_h - pix_h) / 2
        x = event.pos().x() - off_x
        y = event.pos().y() - off_y
        if x < 0 or y < 0 or x > pix_w or y > pix_h:
            return
        frame_w, frame_h = self._frame_shape
        self.point_clicked.emit(int(x * frame_w / pix_w), int(y * frame_h / pix_h))
