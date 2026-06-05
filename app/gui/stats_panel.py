from __future__ import annotations

from PyQt5.QtWidgets import QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget


class StatsPanel(QWidget):
    def __init__(self, context):
        super().__init__()
        self.ctx = context
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Date", "Camera", "Type", "Events", "Violations"])
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.load)
        layout = QVBoxLayout(self)
        layout.addWidget(refresh)
        layout.addWidget(self.table)
        self.load()

    def load(self) -> None:
        rows = self.ctx.database.daily_stats()
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            values = [row["date"], row["camera_name"], row["violation_type"], row["event_count"], row["total_violations"]]
            for c, value in enumerate(values):
                self.table.setItem(r, c, QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents()
