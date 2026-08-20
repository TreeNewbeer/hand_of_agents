from pathlib import Path

import pytest

from hand_of_agents.client.config import ClientConfig


def test_load_client_config(tmp_path: Path) -> None:
    path = tmp_path / "client.toml"
    path.write_text(
        """
node_id = "test-node"
server_url = "ws://127.0.0.1:8000/ws/nodes/test-node"
token = "secret"
gpio_backend = "mock"

[[pins]]
name = "relay"
bcm = 17
direction = "output"
active_high = false
safe_state = false
"""
    )
    config = ClientConfig.load(path)
    assert config.node_id == "test-node"
    assert config.pins[0].name == "relay"
    assert config.pins[0].active_high is False


def test_duplicate_bcm_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "client.toml"
    path.write_text(
        """
node_id = "test"
server_url = "ws://localhost/ws/nodes/test"
token = "secret"
[[pins]]
name = "one"
bcm = 17
direction = "output"
[[pins]]
name = "two"
bcm = 17
direction = "input"
"""
    )
    with pytest.raises(ValueError, match="BCM"):
        ClientConfig.load(path)


def test_raspberry_pi_board_profile_exposes_general_gpio(tmp_path: Path) -> None:
    path = tmp_path / "client.toml"
    path.write_text(
        """
node_id = "test"
server_url = "ws://localhost/ws/nodes/test"
token = "secret"
gpio_backend = "mock"
board_profile = "raspberry-pi-40pin"

[[pins]]
name = "relay"
bcm = 17
direction = "output"
active_high = false
"""
    )
    config = ClientConfig.load(path)
    assert len(config.pins) == 26
    assert {pin.bcm for pin in config.pins} == set(range(28)) - {0, 1}
    gpio17 = next(pin for pin in config.pins if pin.name == "relay")
    assert gpio17.physical == 11
    assert gpio17.direction == "output"
    assert gpio17.active_high is False
