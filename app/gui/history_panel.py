from __future__ import annotations

import csv

import cv2
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QGridLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.gui.image_label import ImageLabel


class HistoryPanel(QWidget):
    SOURCE_LABELS = {
        "camera": "Camera",
        "image": "Ảnh",
        "video": "video",
    }

    def __init__(self, context):
        super().__init__()
        self.ctx = context
        self.rows = []
        self.current_date_filter: str | None = None
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            ["Time", "Camera", "Type", "Violation", "Count", "Confidence", "Telegram", "Raw", "Annotated"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.cellClicked.connect(self.show_selected)
        self.preview = ImageLabel()
        self.preview.setMinimumSize(640, 300)
        self.status = QLabel("")
        self.date_filter = QDateEdit()
        self.date_filter.setDate(QDate.currentDate())
        self.date_filter.setCalendarPopup(True)
        self.source_filter = QComboBox()
        self.source_filter.addItem("All types", "")
        self.source_filter.addItem("Camera", "camera")
        self.source_filter.addItem("Ảnh", "image")
        self.source_filter.addItem("video", "video")
        self.violation_filter = QComboBox()
        self.violation_filter.addItem("All violations", "")
        self.violation_filter.addItem("No helmet", "no_helmet")
        refresh_btn = QPushButton("Refresh")
        today_btn = QPushButton("Filter Date")
        all_btn = QPushButton("Show All")
        export_btn = QPushButton("Export CSV")
        delete_btn = QPushButton("Delete Selected")
        refresh_btn.clicked.connect(lambda: self.load(self.current_date_filter))
        today_btn.clicked.connect(lambda: self.load(self.date_filter.date().toString("yyyy-MM-dd")))
        all_btn.clicked.connect(lambda: self.load(None))
        export_btn.clicked.connect(self.export_csv)
        delete_btn.clicked.connect(self.delete_selected)
        self.source_filter.currentIndexChanged.connect(lambda: self.load(self.current_date_filter))
        self.violation_filter.currentIndexChanged.connect(lambda: self.load(self.current_date_filter))

        bar = QGridLayout()
        bar.addWidget(QLabel("Date"), 0, 0)
        bar.addWidget(self.date_filter, 0, 1)
        bar.addWidget(today_btn, 0, 2)
        bar.addWidget(all_btn, 0, 3)
        bar.addWidget(QLabel("Type"), 0, 4)
        bar.addWidget(self.source_filter, 0, 5)
        bar.addWidget(QLabel("Violation"), 0, 6)
        bar.addWidget(self.violation_filter, 0, 7)
        bar.addWidget(refresh_btn, 0, 8)
        bar.addWidget(export_btn, 0, 9)
        bar.addWidget(delete_btn, 0, 10)
        bar.addWidget(self.status, 0, 11)
        bar.setColumnStretch(11, 1)

        self.stats_table = QTableWidget(0, 6)
        self.stats_table.setHorizontalHeaderLabels(["Date", "Camera", "Type", "Violation", "Events", "Violations"])
        self.stats_table.setAlternatingRowColors(True)

        stats_panel = QWidget()
        stats_layout = QVBoxLayout(stats_panel)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(6)
        stats_layout.addWidget(QLabel("Daily Statistics"))
        stats_layout.addWidget(self.stats_table)
        stats_panel.setMinimumHeight(150)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.table)
        splitter.addWidget(self.preview)
        splitter.addWidget(stats_panel)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setCollapsible(2, False)
        splitter.setSizes([250, 380, 170])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.addLayout(bar)
        layout.addWidget(splitter, 1)
        self.load()

    def load(self, date_filter: str | None = None) -> None:
        self.current_date_filter = date_filter
        source_type = self.source_filter.currentData() or None
        violation_type = self.violation_filter.currentData() or None
        self.rows = self.ctx.database.list_events(date_filter, source_type, violation_type)
        self.table.setRowCount(len(self.rows))
        for r, row in enumerate(self.rows):
            source_type = row["source_type"] if "source_type" in row.keys() and row["source_type"] else "camera"
            values = [
                row["timestamp"],
                row["camera_name"],
                self.SOURCE_LABELS.get(source_type, source_type),
                self.violation_label(row["violation_type"]),
                str(row["violation_count"]),
                f"{float(row['avg_confidence'] or 0):.2f}",
                "Sent" if row["telegram_sent"] else "Failed",
                row["raw_image_path"],
                row["annotated_image_path"],
            ]
            for c, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setToolTip(str(value))
                self.table.setItem(r, c, item)
        self.configure_history_columns()
        self.status.setText(f"{len(self.rows)} events")
        self.load_stats()

    def load_stats(self) -> None:
        rows = self.ctx.database.daily_stats()
        self.stats_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            source_type = row["source_type"] if "source_type" in row.keys() and row["source_type"] else "camera"
            values = [
                row["date"],
                row["camera_name"],
                self.SOURCE_LABELS.get(source_type, source_type),
                self.violation_label(row["violation_type"]),
                row["event_count"],
                row["total_violations"],
            ]
            for c, value in enumerate(values):
                self.stats_table.setItem(r, c, QTableWidgetItem(str(value)))
        self.configure_stats_columns()

    def show_selected(self, row: int, column: int) -> None:
        if row >= len(self.rows):
            return
        path = self.rows[row]["raw_image_path"] if column == 7 else self.rows[row]["annotated_image_path"]
        frame = cv2.imread(path)
        if frame is not None:
            self.preview.set_cv_image(frame)

    def delete_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.rows):
            self.status.setText("Select an event to delete.")
            return
        event_id = self.rows[row]["event_id"]
        answer = QMessageBox.question(self, "Delete event", f"Delete event {event_id}?")
        if answer != QMessageBox.Yes:
            return
        self.ctx.database.delete_event(event_id)
        self.load(self.current_date_filter)

    def export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "violation_history.csv", "CSV Files (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["event_id", "timestamp", "camera", "type", "violation", "count", "confidence", "raw", "annotated"])
            for row in self.rows:
                source_type = row["source_type"] if "source_type" in row.keys() and row["source_type"] else "camera"
                writer.writerow(
                    [
                        row["event_id"],
                        row["timestamp"],
                        row["camera_name"],
                        self.SOURCE_LABELS.get(source_type, source_type),
                        self.violation_label(row["violation_type"]),
                        row["violation_count"],
                        f"{float(row['avg_confidence'] or 0):.4f}",
                        row["raw_image_path"],
                        row["annotated_image_path"],
                    ]
                )
        self.status.setText(f"Exported CSV: {path}")

    def violation_label(self, value: str) -> str:
        return {"no_helmet": "Không đội mũ"}.get(value, value)

    def configure_history_columns(self) -> None:
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(48)
        for column in range(self.table.columnCount()):
            header.setSectionResizeMode(column, QHeaderView.Interactive)

        compact_columns = {
            0: 155,
            1: 90,
            2: 70,
            4: 65,
            5: 88,
            6: 88,
            7: 210,
            8: 210,
        }
        for column, width in compact_columns.items():
            self.table.setColumnWidth(column, width)

        header.setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(34)

    def configure_stats_columns(self) -> None:
        header = self.stats_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(54)
        for column in range(self.stats_table.columnCount()):
            header.setSectionResizeMode(column, QHeaderView.Interactive)

        self.stats_table.setColumnWidth(0, 110)
        self.stats_table.setColumnWidth(1, 95)
        self.stats_table.setColumnWidth(2, 80)
        self.stats_table.setColumnWidth(4, 75)
        self.stats_table.setColumnWidth(5, 90)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        self.stats_table.verticalHeader().setDefaultSectionSize(34)
