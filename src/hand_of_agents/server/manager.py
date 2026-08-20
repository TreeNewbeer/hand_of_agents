from __future__ import annotations

import asyncio
import contextlib
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from fastapi import WebSocket


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class NodeConnection:
    node_id: str
    websocket: WebSocket
    connected_at: str = field(default_factory=utc_now)
    last_seen: str = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)
    pins: list[dict[str, Any]] = field(default_factory=list)
    state: dict[str, Any] = field(default_factory=dict)
    pending: dict[str, asyncio.Future[dict[str, Any]]] = field(default_factory=dict)
    send_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def snapshot(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "connected": True,
            "connected_at": self.connected_at,
            "last_seen": self.last_seen,
            "metadata": self.metadata,
            "pins": self.pins,
            "state": self.state,
        }


class NodeManager:
    def __init__(self) -> None:
        self._nodes: dict[str, NodeConnection] = {}
        self._last_snapshots: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, node_id: str, websocket: WebSocket) -> NodeConnection:
        await websocket.accept()
        connection = NodeConnection(node_id=node_id, websocket=websocket)
        async with self._lock:
            old = self._nodes.get(node_id)
            self._nodes[node_id] = connection
        if old:
            with contextlib.suppress(Exception):
                await old.websocket.close(code=1012, reason="Replaced by a new connection")
        return connection

    async def disconnect(self, connection: NodeConnection) -> None:
        async with self._lock:
            if self._nodes.get(connection.node_id) is not connection:
                return
            snapshot = connection.snapshot()
            snapshot["connected"] = False
            self._last_snapshots[connection.node_id] = snapshot
            del self._nodes[connection.node_id]
        for future in connection.pending.values():
            if not future.done():
                future.set_exception(ConnectionError("Node disconnected"))

    def update(self, connection: NodeConnection, message: dict[str, Any]) -> None:
        connection.last_seen = utc_now()
        message_type = message.get("type")
        if message_type == "hello":
            connection.metadata = dict(message.get("metadata", {}))
            peer = connection.websocket.client
            if peer:
                connection.metadata["ip_address"] = peer.host
            connection.pins = message.get("pins", [])
        elif message_type in {"state", "pong"}:
            if message.get("state"):
                connection.state = message["state"]
        elif message_type == "ack":
            if message.get("state"):
                connection.state = message["state"]
            command_id = message.get("command_id")
            future = connection.pending.get(command_id)
            if future and not future.done():
                future.set_result(message)

    def list_nodes(self) -> list[dict[str, Any]]:
        connected = {node_id: node.snapshot() for node_id, node in self._nodes.items()}
        return [connected.get(node_id, snapshot) for node_id, snapshot in sorted(
            {**self._last_snapshots, **connected}.items()
        )]

    def get_node(self, node_id: str) -> NodeConnection | None:
        return self._nodes.get(node_id)

    def connected_count(self) -> int:
        return len(self._nodes)

    async def command(
        self,
        node_id: str,
        command: dict[str, Any],
        timeout: float,
    ) -> dict[str, Any]:
        connection = self._nodes.get(node_id)
        if not connection:
            raise ConnectionError(f"Node {node_id!r} is offline")
        command_id = uuid.uuid4().hex
        payload = {"type": "command", "command_id": command_id, **command}
        future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        connection.pending[command_id] = future
        try:
            async with connection.send_lock:
                await connection.websocket.send_json(payload)
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            connection.pending.pop(command_id, None)
