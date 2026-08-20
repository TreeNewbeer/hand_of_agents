from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_tokens(value: str) -> dict[str, str]:
    tokens: dict[str, str] = {}
    for item in _split_csv(value):
        node_id, separator, token = item.partition(":")
        if not separator or not node_id.strip() or not token.strip():
            raise ValueError("HOA_NODE_TOKENS must use node-id:token pairs")
        tokens[node_id.strip()] = token.strip()
    return tokens


@dataclass(slots=True)
class ServerSettings:
    bind_host: str = "0.0.0.0"
    bind_port: int = 8000
    api_key: str = "development-api-key"
    node_tokens: dict[str, str] = field(
        default_factory=lambda: {"pi-lab": "development-node-token"}
    )
    db_path: Path = Path("data/hand_of_agents.db")
    cors_origins: list[str] = field(default_factory=list)
    command_timeout: float = 5.0
    auth_mode: str = "api_key"

    @classmethod
    def from_env(cls) -> "ServerSettings":
        auth_mode = os.getenv("HOA_AUTH_MODE", "api_key").strip().lower()
        if auth_mode not in {"api_key", "none"}:
            raise ValueError("HOA_AUTH_MODE must be api_key or none")
        return cls(
            bind_host=os.getenv("HOA_BIND_HOST", "0.0.0.0"),
            bind_port=int(os.getenv("HOA_BIND_PORT", "8000")),
            api_key=os.getenv("HOA_API_KEY", "development-api-key"),
            node_tokens=_parse_tokens(
                os.getenv("HOA_NODE_TOKENS", "pi-lab:development-node-token")
            ),
            db_path=Path(os.getenv("HOA_DB_PATH", "data/hand_of_agents.db")),
            cors_origins=_split_csv(os.getenv("HOA_CORS_ORIGINS", "")),
            command_timeout=float(os.getenv("HOA_COMMAND_TIMEOUT", "5")),
            auth_mode=auth_mode,
        )
