from __future__ import annotations

from dataclasses import dataclass

from PyQt5.QtWidgets import QMainWindow, QTabWidget

from app.core.config_loader import load_config
from app.core.database import Database
from app.core.detector import Detector
from app.core.event_manager import EventManager
from app.core.roi_manager import RoiManager
from app.core.violation_engine import ViolationEngine
from app.gui.camera_panel import CameraPanel
from app.gui.history_panel import HistoryPanel
from app.gui.roi_editor import RoiEditor
from app.gui.settings_panel import SettingsPanel
from app.gui.upload_panel import UploadPanel


@dataclass
class AppContext:
    config: dict
    database: Database
    detector: Detector
    violation_engine: ViolationEngine
    event_manager: EventManager
    roi_manager: RoiManager
    camera_id: str
    camera_name: str
    camera_source: str


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        config = load_config()
        db = Database(config["database"]["path"])
        camera_id = config["camera"]["default_id"]
        camera_name = config["camera"]["default_name"]
        camera_source = str(config["camera"]["default_source"])
        db.upsert_camera(camera_id, camera_name, camera_source, config["camera"].get("roi") or None)
        detector = Detector(config)
        ctx = AppContext(
            config=config,
            database=db,
            detector=detector,
            violation_engine=ViolationEngine(config),
            event_manager=EventManager(config, db),
            roi_manager=RoiManager(db, camera_id),
            camera_id=camera_id,
            camera_name=camera_name,
            camera_source=camera_source,
        )
        self.ctx = ctx
        self.setWindowTitle(config["app"]["name"])
        self.resize(1280, 860)
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #f5f7fb; color: #1f2937; font-size: 10pt; }
            QTabWidget::pane { border: 1px solid #d8dee8; background: #ffffff; }
            QTabBar::tab { padding: 8px 14px; border: 1px solid #d8dee8; background: #eef2f7; }
            QTabBar::tab:selected { background: #ffffff; border-bottom-color: #ffffff; }
            QPushButton { background: #ffffff; border: 1px solid #bfc8d6; border-radius: 4px; padding: 6px 12px; }
            QPushButton:hover { background: #eef6ff; border-color: #6aa6e8; }
            QPushButton:pressed { background: #dcecff; }
            QTableWidget { background: #ffffff; gridline-color: #e2e8f0; selection-background-color: #dcecff; }
            QHeaderView::section { background: #e9eef6; padding: 6px; border: 1px solid #d8dee8; font-weight: 600; }
            QComboBox, QDateEdit { background: #ffffff; border: 1px solid #bfc8d6; border-radius: 4px; padding: 5px 8px; }
            QLabel { color: #1f2937; }
            """
        )
        tabs = QTabWidget()
        self.camera_panel = CameraPanel(ctx)
        tabs.addTab(self.camera_panel, "Realtime Camera")
        tabs.addTab(UploadPanel(ctx), "Upload Image/Video")
        tabs.addTab(RoiEditor(ctx, self.camera_panel), "ROI Config")
        tabs.addTab(HistoryPanel(ctx), "Violation History")
        tabs.addTab(SettingsPanel(ctx), "Settings")
        self.setCentralWidget(tabs)

    def closeEvent(self, event) -> None:
        self.camera_panel.stop_camera()
        super().closeEvent(event)
