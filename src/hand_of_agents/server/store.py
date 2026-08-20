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
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS node_names (
                    node_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    updated_at TEXT NOT NULL
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

    def get_node_name(self, node_id: str) -> str | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT name FROM node_names WHERE node_id=?",
                (node_id,),
            ).fetchone()
        return str(row["name"]) if row else None

    def set_node_name(self, node_id: str, name: str) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO node_names(node_id,name,updated_at) VALUES(?,?,?)
                ON CONFLICT(node_id) DO UPDATE SET
                    name=excluded.name,
                    updated_at=excluded.updated_at
                """,
                (node_id, name, datetime.now(UTC).isoformat()),
            )
