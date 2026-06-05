from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.utils.time_utils import timestamp_str


class Database:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cameras (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    camera_id TEXT UNIQUE NOT NULL,
                    camera_name TEXT NOT NULL,
                    source TEXT NOT NULL,
                    roi_json TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
            self._ensure_column(conn, "violation_events", "source_type", "TEXT DEFAULT 'camera'")

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS violation_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    camera_id TEXT NOT NULL,
                    camera_name TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    date TEXT NOT NULL,
                    violation_type TEXT NOT NULL,
                    violation_count INTEGER NOT NULL,
                    raw_image_path TEXT NOT NULL,
                    annotated_image_path TEXT NOT NULL,
                    telegram_sent INTEGER DEFAULT 0,
                    telegram_error TEXT,
                    avg_confidence REAL,
                    extra_json TEXT
                )
                """
            )

    def upsert_camera(self, camera_id: str, camera_name: str, source: str, roi: list | None = None) -> None:
        now = timestamp_str()
        roi_json = json.dumps(roi) if roi else None
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO cameras (camera_id, camera_name, source, roi_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(camera_id) DO UPDATE SET
                    camera_name=excluded.camera_name,
                    source=excluded.source,
                    roi_json=COALESCE(excluded.roi_json, cameras.roi_json),
                    updated_at=excluded.updated_at
                """,
                (camera_id, camera_name, str(source), roi_json, now, now),
            )

    def get_camera_roi(self, camera_id: str) -> list | None:
        with self.connect() as conn:
            row = conn.execute("SELECT roi_json FROM cameras WHERE camera_id = ?", (camera_id,)).fetchone()
        if not row or not row["roi_json"]:
            return None
        return json.loads(row["roi_json"])

    def save_roi(self, camera_id: str, roi: list[list[int]]) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE cameras SET roi_json = ?, updated_at = ? WHERE camera_id = ?",
                (json.dumps(roi), timestamp_str(), camera_id),
            )

    def insert_event(self, event: dict[str, Any]) -> None:
        fields = (
            "event_id",
            "camera_id",
            "camera_name",
            "timestamp",
            "date",
            "violation_type",
            "source_type",
            "violation_count",
            "raw_image_path",
            "annotated_image_path",
            "telegram_sent",
            "telegram_error",
            "avg_confidence",
            "extra_json",
        )
        values = [event.get(field) for field in fields]
        values[-1] = json.dumps(values[-1] or {})
        placeholders = ",".join(["?"] * len(fields))
        with self.connect() as conn:
            conn.execute(f"INSERT INTO violation_events ({','.join(fields)}) VALUES ({placeholders})", values)

    def list_events(
        self,
        date_filter: str | None = None,
        source_type: str | None = None,
        violation_type: str | None = None,
    ) -> list[sqlite3.Row]:
        query = "SELECT * FROM violation_events"
        clauses = []
        params: list[str] = []
        if date_filter:
            clauses.append("date = ?")
            params.append(date_filter)
        if source_type:
            clauses.append("COALESCE(source_type, 'camera') = ?")
            params.append(source_type)
        if violation_type:
            clauses.append("violation_type = ?")
            params.append(violation_type)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY timestamp DESC LIMIT 500"
        with self.connect() as conn:
            return conn.execute(query, tuple(params)).fetchall()

    def delete_event(self, event_id: str) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM violation_events WHERE event_id = ?", (event_id,))

    def daily_stats(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT date, camera_name, COALESCE(source_type, 'camera') AS source_type,
                       violation_type, COUNT(*) AS event_count,
                       SUM(violation_count) AS total_violations
                FROM violation_events
                GROUP BY date, camera_name, source_type, violation_type
                ORDER BY date DESC
                """
            ).fetchall()
