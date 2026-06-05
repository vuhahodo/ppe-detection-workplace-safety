from __future__ import annotations

from pathlib import Path


class Detector:
    def __init__(self, config: dict):
        self.config = config
        self.model_path = Path(config["model"]["path"])
        self.model = None
        self.names: dict[int, str] = {}
        self._load_model()

    def _load_model(self) -> None:
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError("Missing dependency: install ultralytics with `pip install -r requirements.txt`.") from exc
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        self.model = YOLO(str(self.model_path))
        raw_names = self.model.names
        self.names = {int(k): str(v) for k, v in raw_names.items()} if isinstance(raw_names, dict) else {
            i: str(v) for i, v in enumerate(raw_names)
        }

    def predict(self, frame) -> list[dict]:
        thresholds = self.config["thresholds"]
        conf = min(
            thresholds.get("person_conf", 0.35),
            thresholds.get("helmet_conf", 0.35),
            thresholds.get("no_helmet_conf", 0.4),
        )
        result = self.model.predict(
            source=frame,
            imgsz=self.config["model"].get("input_size", 640),
            conf=conf,
            iou=thresholds.get("iou_threshold", 0.45),
            verbose=False,
            device=None if self.config["model"].get("device") == "auto" else self.config["model"].get("device"),
        )[0]
        detections: list[dict] = []
        if result.boxes is None:
            return detections
        for box in result.boxes:
            class_id = int(box.cls[0])
            class_name = self.names.get(class_id, str(class_id))
            confidence = float(box.conf[0])
            if confidence < self._threshold_for(class_name):
                continue
            bbox = [float(v) for v in box.xyxy[0].tolist()]
            detections.append(
                {
                    "class_id": class_id,
                    "class_name": class_name,
                    "confidence": confidence,
                    "bbox": bbox,
                }
            )
        return detections

    def _threshold_for(self, class_name: str) -> float:
        key = f"{class_name}_conf"
        return float(self.config["thresholds"].get(key, 0.35))
