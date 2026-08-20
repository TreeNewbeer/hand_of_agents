from pathlib import Path

from starlette.testclient import TestClient

from hand_of_agents.server.app import create_app
from hand_of_agents.server.config import ServerSettings


def make_client(tmp_path: Path, auth_mode: str = "api_key") -> TestClient:
    settings = ServerSettings(
        api_key="test-api-key",
        node_tokens={"test-node": "test-node-token"},
        db_path=tmp_path / "events.db",
        auth_mode=auth_mode,
    )
    return TestClient(create_app(settings))


def test_events_requires_api_key(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        assert client.get("/api/v1/events").status_code == 401
        response = client.get("/api/v1/events", headers={"X-API-Key": "test-api-key"})
        assert response.status_code == 200
        assert response.json() == {"events": []}


def test_control_requires_key_then_reports_offline(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        url = "/api/v1/nodes/test-node/pins/relay"
        body = {"action": "set", "value": True}
        assert client.post(url, json=body).status_code == 401
        response = client.post(
            url,
            json=body,
            headers={"X-API-Key": "test-api-key"},
        )
        assert response.status_code == 409
        assert "offline" in response.json()["detail"]


def test_node_websocket_uses_token_header(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        with client.websocket_connect(
            "/ws/nodes/test-node",
            headers={"X-Node-Token": "test-node-token"},
        ) as websocket:
            websocket.send_json(
                {
                    "type": "hello",
                    "metadata": {"hostname": "test-pi"},
                    "pins": [],
                }
            )
            websocket.send_json(
                {"type": "state", "state": {"pins": {}, "system": {}}}
            )
            response = client.get("/api/v1/nodes/test-node")
            assert response.status_code == 200
            assert response.json()["metadata"]["hostname"] == "test-pi"
            assert response.json()["name"] == "Pi"

            renamed = client.post(
                "/api/v1/nodes/test-node/name",
                json={"name": "Bench Pi"},
                headers={"X-API-Key": "test-api-key"},
            )
            assert renamed.status_code == 200
            assert renamed.json()["name"] == "Bench Pi"
            assert client.get("/api/v1/nodes/test-node").json()["name"] == "Bench Pi"


def test_lan_mode_does_not_require_api_key(tmp_path: Path) -> None:
    with make_client(tmp_path, auth_mode="none") as client:
        assert client.get("/api/v1/settings").json() == {"auth_mode": "none"}
        response = client.post(
            "/api/v1/nodes/test-node/pins/GPIO17",
            json={"action": "configure", "direction": "output"},
        )
        assert response.status_code == 409
        assert "offline" in response.json()["detail"]
