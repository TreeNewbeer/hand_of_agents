from __future__ import annotations

import asyncio
import hmac
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any, Literal

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from hand_of_agents import __version__
from hand_of_agents.server.config import ServerSettings
from hand_of_agents.server.manager import NodeManager
from hand_of_agents.server.store import EventStore

LOGGER = logging.getLogger(__name__)


class PinCommand(BaseModel):
    action: Literal["set", "toggle", "pulse", "configure"]
    value: bool | None = None
    duration_ms: int | None = Field(default=None, ge=50, le=60000)
    continuous: bool = False
    pulse_hz: float | None = Field(default=None, ge=0.1, le=10)
    direction: Literal["input", "output", "unconfigured"] | None = None
    pull: Literal["up", "down", "floating"] = "floating"


def create_app(settings: ServerSettings | None = None) -> FastAPI:
    settings = settings or ServerSettings.from_env()
    manager = NodeManager()
    store = EventStore(settings.db_path)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if settings.auth_mode == "api_key" and settings.api_key == "development-api-key":
            LOGGER.warning("Using development API key; set HOA_API_KEY before deployment")
        yield

    app = FastAPI(
        title="Hand of Agents API",
        version=__version__,
        description="Control and observe Raspberry Pi GPIO nodes.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.manager = manager
    app.state.store = store

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["X-API-Key", "Content-Type"],
        )

    async def require_api_key(
        x_api_key: Annotated[str | None, Header()] = None,
    ) -> str:
        if settings.auth_mode == "none":
            return "lan-user"
        if not x_api_key or not hmac.compare_digest(x_api_key, settings.api_key):
            raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")
        return "api-key"

    @app.get("/healthz", tags=["system"])
    async def health() -> dict[str, Any]:
        return {
            "ok": True,
            "version": __version__,
            "connected_nodes": manager.connected_count(),
        }

    @app.get("/api/v1/settings", tags=["system"])
    async def public_settings() -> dict[str, Any]:
        return {"auth_mode": settings.auth_mode}

    @app.get("/api/v1/nodes", tags=["nodes"])
    async def list_nodes() -> dict[str, Any]:
        return {"nodes": manager.list_nodes()}

    @app.get("/api/v1/nodes/{node_id}", tags=["nodes"])
    async def get_node(node_id: str) -> dict[str, Any]:
        node = next((item for item in manager.list_nodes() if item["node_id"] == node_id), None)
        if not node:
            raise HTTPException(status_code=404, detail="Unknown node")
        return node

    @app.post("/api/v1/nodes/{node_id}/pins/{pin_name}", tags=["control"])
    async def control_pin(
        node_id: str,
        pin_name: str,
        body: PinCommand,
        actor: str = Depends(require_api_key),
    ) -> dict[str, Any]:
        command = {"action": body.action, "pin": pin_name}
        if body.action == "set":
            if body.value is None:
                raise HTTPException(status_code=422, detail="value is required for set")
            command["value"] = body.value
        if body.action == "pulse":
            command["duration_ms"] = body.duration_ms or 500
            command["continuous"] = body.continuous
        if body.action == "configure":
            if body.direction is None:
                raise HTTPException(status_code=422, detail="direction is required for configure")
            command["direction"] = body.direction
            command["pull"] = body.pull
            if body.pulse_hz is not None:
                command["pulse_hz"] = body.pulse_hz
        store.add(node_id, "command_requested", command, actor)
        try:
            result = await manager.command(node_id, command, settings.command_timeout)
        except ConnectionError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except TimeoutError as exc:
            raise HTTPException(status_code=504, detail="Node command timed out") from exc
        store.add(node_id, "command_result", result, actor)
        if not result.get("ok"):
            raise HTTPException(status_code=422, detail=result.get("error", "Command failed"))
        return result

    @app.get("/api/v1/events", tags=["audit"])
    async def recent_events(
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
        node_id: str | None = None,
        _actor: str = Depends(require_api_key),
    ) -> dict[str, Any]:
        return {"events": await asyncio.to_thread(store.recent, limit, node_id)}

    @app.websocket("/ws/nodes/{node_id}")
    async def node_socket(websocket: WebSocket, node_id: str) -> None:
        token = websocket.headers.get("x-node-token", "")
        expected_token = settings.node_tokens.get(node_id)
        if not expected_token or not hmac.compare_digest(token, expected_token):
            await websocket.close(code=1008, reason="Invalid node token")
            return
        connection = await manager.connect(node_id, websocket)
        store.add(node_id, "connected", {"client": str(websocket.client)})
        try:
            while True:
                message = await websocket.receive_json()
                manager.update(connection, message)
        except WebSocketDisconnect:
            pass
        except Exception:
            LOGGER.exception("Node %s connection failed", node_id)
        finally:
            await manager.disconnect(connection)
            store.add(node_id, "disconnected", {})

    web_dir = Path(__file__).resolve().parent.parent / "web"
    app.mount("/static", StaticFiles(directory=web_dir), name="static")

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(web_dir / "index.html")

    return app


app = create_app()


def main() -> None:
    settings = ServerSettings.from_env()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    uvicorn.run(app, host=settings.bind_host, port=settings.bind_port)


if __name__ == "__main__":
    main()
