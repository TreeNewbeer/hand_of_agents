from __future__ import annotations

import json
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class EventStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )

    def add(
        self,
        node_id: str,
        event_type: str,
        payload: dict[str, Any],
        actor: str = "system",
    ) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT INTO events(created_at,node_id,event_type,actor,payload) VALUES(?,?,?,?,?)",
                (
                    datetime.now(UTC).isoformat(),
                    node_id,
                    event_type,
                    actor,
                    json.dumps(payload, separators=(",", ":")),
                ),
            )

    def recent(self, limit: int = 100, node_id: str | None = None) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 500))
        with self._lock:
            if node_id:
                rows = self._connection.execute(
                    "SELECT * FROM events WHERE node_id=? ORDER BY id DESC LIMIT ?",
                    (node_id, limit),
                ).fetchall()
            else:
                rows = self._connection.execute(
                    "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
                ).fetchall()
        return [
            {
                "id": row["id"],
                "created_at": row["created_at"],
                "node_id": row["node_id"],
                "event_type": row["event_type"],
                "actor": row["actor"],
                "payload": json.loads(row["payload"]),
            }
            for row in rows
        ]

