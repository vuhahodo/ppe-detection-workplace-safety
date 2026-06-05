from __future__ import annotations

import time
from collections import defaultdict


class ViolationEngine:
    def __init__(self, config: dict):
        self.config = config
        self.confirm_counts = defaultdict(int)
        self.last_event_time = defaultdict(float)

    def analyze(
        self,
        detections: list[dict],
        roi_manager,
        camera_id: str,
        image_mode: bool = False,
        frame_shape=None,
    ) -> dict:
        classes = self.config["classes"]["required"]
        person_name = classes["person"]
        no_helmet_name = classes["no_helmet"]
        people = [
            d for d in detections if d["class_name"] == person_name and roi_manager.box_in_roi(d["bbox"], frame_shape)
        ]
        no_helmets = [d for d in detections if d["class_name"] == no_helmet_name]
        violating = []
        confidences = []

        for person in people:
            matches = [h for h in no_helmets if self._is_no_helmet_on_person(person["bbox"], h["bbox"])]
            if matches:
                best = max(matches, key=lambda d: d["confidence"])
                violating.append({"person": person, "no_helmet": best})
                confidences.append(best["confidence"])

        has_current = bool(violating)
        key = f"{camera_id}:no_helmet"
        required_frames = 1 if image_mode else int(self.config["violation"].get("confirmation_frames", 5))
        if has_current:
            self.confirm_counts[key] += 1
        else:
            self.confirm_counts[key] = 0

        confirmed = self.confirm_counts[key] >= required_frames
        cooldown_seconds = 0 if image_mode else int(self.config["violation"].get("cooldown_seconds", 30))
        cooldown_ok = (time.time() - self.last_event_time[key]) >= cooldown_seconds
        should_create_event = confirmed and cooldown_ok
        if should_create_event:
            self.last_event_time[key] = time.time()
            self.confirm_counts[key] = 0

        return {
            "has_violation": has_current,
            "confirmed": confirmed,
            "should_create_event": should_create_event,
            "violation_type": "no_helmet",
            "violation_count": len(violating),
            "violating_persons": violating,
            "avg_confidence": sum(confidences) / len(confidences) if confidences else 0.0,
        }

    def _is_no_helmet_on_person(self, person_box: list[float], no_helmet_box: list[float]) -> bool:
        px1, py1, px2, py2 = person_box
        hx1, hy1, hx2, hy2 = no_helmet_box
        ratio = float(self.config["violation"].get("head_region_ratio", 0.35))
        head_y2 = py1 + ratio * (py2 - py1)
        cx = (hx1 + hx2) / 2
        cy = (hy1 + hy2) / 2
        return px1 <= cx <= px2 and py1 <= cy <= head_y2
