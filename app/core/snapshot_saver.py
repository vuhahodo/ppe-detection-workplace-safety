from __future__ import annotations

from pathlib import Path

import cv2


class SnapshotSaver:
    def __init__(self, save_dir: str | Path):
        self.save_dir = Path(save_dir)
        self.raw_dir = self.save_dir / "raw"
        self.annotated_dir = self.save_dir / "annotated"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.annotated_dir.mkdir(parents=True, exist_ok=True)

    def save(self, event_id: str, date: str, camera_id: str, raw_frame, annotated_frame) -> tuple[str, str]:
        raw_path = self.raw_dir / f"{date}_{camera_id}_{event_id}_raw.jpg"
        annotated_path = self.annotated_dir / f"{date}_{camera_id}_{event_id}_annotated.jpg"
        cv2.imwrite(str(raw_path), raw_frame)
        cv2.imwrite(str(annotated_path), annotated_frame)
        return str(raw_path), str(annotated_path)
