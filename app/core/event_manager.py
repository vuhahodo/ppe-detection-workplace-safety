from __future__ import annotations

import uuid

from app.core.snapshot_saver import SnapshotSaver
from app.core.telegram_notifier import TelegramNotifier
from app.utils.drawing import draw_event_header
from app.utils.time_utils import date_str, timestamp_str


class EventManager:
    def __init__(self, config: dict, database):
        self.config = config
        self.database = database
        self.snapshot_saver = SnapshotSaver(config["app"]["save_dir"])
        self.telegram = TelegramNotifier(config)

    def create_event(
        self,
        camera_id: str,
        camera_name: str,
        violation: dict,
        raw_frame,
        annotated_frame,
        source_type: str = "camera",
    ) -> dict:
        ts = timestamp_str()
        d = date_str()
        event_id = f"EVT_{ts.replace('-', '').replace(':', '').replace(' ', '_')}_{uuid.uuid4().hex[:4].upper()}"
        annotated_for_save = draw_event_header(annotated_frame.copy(), camera_name, ts, violation["violation_count"])
        raw_path, annotated_path = self.snapshot_saver.save(event_id, d, camera_id, raw_frame, annotated_for_save)
        caption = (
            "[CANH BAO AN TOAN LAO DONG]\n\n"
            f"Camera: {camera_name}\n"
            f"Thoi gian: {ts}\n"
            "Loai vi pham: Nguoi lao dong khong doi mu bao ho\n"
            f"So luong vi pham: {violation['violation_count']}\n\n"
            "Anh dinh kem:\n1. Anh goc\n2. Anh da phan tich"
        )
        telegram_sent, telegram_error = self.telegram.send_violation_alert(caption, raw_path, annotated_path)
        event = {
            "event_id": event_id,
            "camera_id": camera_id,
            "camera_name": camera_name,
            "timestamp": ts,
            "date": d,
            "violation_type": violation["violation_type"],
            "source_type": source_type,
            "violation_count": violation["violation_count"],
            "raw_image_path": raw_path,
            "annotated_image_path": annotated_path,
            "telegram_sent": 1 if telegram_sent else 0,
            "telegram_error": telegram_error,
            "avg_confidence": violation["avg_confidence"],
            "extra_json": {"violating_persons": violation.get("violating_persons", [])},
        }
        self.database.insert_event(event)
        return event
