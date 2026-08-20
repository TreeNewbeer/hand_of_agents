from __future__ import annotations

import argparse
import asyncio
import json
import logging
import signal
from pathlib import Path
from typing import Any

from websockets.asyncio.client import connect

from hand_of_agents import __version__
from hand_of_agents.client.config import ClientConfig
from hand_of_agents.client.gpio import GpioController, create_driver
from hand_of_agents.client.telemetry import system_metadata, system_telemetry

LOGGER = logging.getLogger(__name__)


class NodeClient:
    def __init__(self, config: ClientConfig) -> None:
        self.config = config
        self.controller = GpioController(
            create_driver(config.gpio_backend, config.pins),
            config.pins,
            config.max_pulse_ms,
        )
        self.stop_event = asyncio.Event()

    async def run(self) -> None:
        try:
            while not self.stop_event.is_set():
                connection_task: asyncio.Task[None] | None = None
                stop_task: asyncio.Task[bool] | None = None
                try:
                    connection_task = asyncio.create_task(self._connection_session())
                    stop_task = asyncio.create_task(self.stop_event.wait())
                    done, _ = await asyncio.wait(
                        {connection_task, stop_task},
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    if stop_task in done:
                        connection_task.cancel()
                        await asyncio.gather(connection_task, return_exceptions=True)
                        break
                    stop_task.cancel()
                    await asyncio.gather(stop_task, return_exceptions=True)
                    await connection_task
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    LOGGER.warning("Server connection unavailable: %s", exc)
                finally:
                    for task in (connection_task, stop_task):
                        if task and not task.done():
                            task.cancel()
                    self.controller.apply_safe_state()
                try:
                    await asyncio.wait_for(
                        self.stop_event.wait(), timeout=self.config.reconnect_seconds
                    )
                except TimeoutError:
                    pass
        finally:
            self.controller.close()

    async def _connection_session(self) -> None:
        LOGGER.info("Connecting to %s", self.config.server_url)
        async with connect(
            self.config.server_url,
            additional_headers={"X-Node-Token": self.config.token},
            open_timeout=10,
            ping_interval=None,
        ) as websocket:
            LOGGER.info("Connected as node %s", self.config.node_id)
            await websocket.send(json.dumps(self._hello_message()))
            telemetry_task = asyncio.create_task(self._telemetry_loop(websocket))
            heartbeat_task = asyncio.create_task(self._heartbeat_loop(websocket))
            try:
                async for raw_message in websocket:
                    await self._handle_message(websocket, json.loads(raw_message))
            finally:
                telemetry_task.cancel()
                heartbeat_task.cancel()
                await asyncio.gather(telemetry_task, heartbeat_task, return_exceptions=True)

    def _hello_message(self) -> dict[str, Any]:
        return {
            "type": "hello",
            "version": __version__,
            "metadata": system_metadata(),
            "pins": [pin.public_dict() for pin in self.config.pins],
        }

    def _state_message(self, message_type: str = "state") -> dict[str, Any]:
        return {
            "type": message_type,
            "state": {
                "pins": self.controller.snapshot(),
                "pin_modes": self.controller.mode_snapshot(),
                "pin_pulls": self.controller.pull_snapshot(),
                "pin_behaviors": self.controller.behavior_snapshot(),
                "pin_pulse_hz": self.controller.pulse_frequency_snapshot(),
                "system": system_telemetry(),
            },
        }

    async def _telemetry_loop(self, websocket: Any) -> None:
        while True:
            message = self._state_message()
            await websocket.send(json.dumps(message))
            behaviors = message["state"]["pin_behaviors"].values()
            delay = min(self.config.telemetry_seconds, 0.5) if "pulse" in behaviors else self.config.telemetry_seconds
            await asyncio.sleep(delay)

    async def _heartbeat_loop(self, websocket: Any) -> None:
        while True:
            await asyncio.sleep(self.config.heartbeat_seconds)
            await websocket.send(json.dumps({"type": "pong", "state": self._state_message()["state"]}))

    async def _handle_message(self, websocket: Any, message: dict[str, Any]) -> None:
        if message.get("type") != "command":
            return
        command_id = message.get("command_id")
        try:
            action = message.get("action")
            pin = str(message.get("pin", ""))
            if action == "set":
                if not isinstance(message.get("value"), bool):
                    raise ValueError("set command requires a boolean value")
                self.controller.set_value(pin, message["value"])
            elif action == "toggle":
                self.controller.toggle(pin)
            elif action == "pulse":
                self.controller.pulse(
                    pin,
                    int(message.get("duration_ms", 500)),
                    continuous=bool(message.get("continuous", False)),
                )
            elif action == "configure":
                direction = str(message.get("direction", ""))
                pull = str(message.get("pull", "floating"))
                current_mode = self.controller.mode_snapshot().get(pin)
                current_pull = self.controller.pull_snapshot().get(pin)
                if direction != current_mode or (
                    direction == "input" and pull != current_pull
                ):
                    self.controller.configure(pin, direction, pull)
                if message.get("pulse_hz") is not None:
                    self.controller.set_pulse_frequency(pin, float(message["pulse_hz"]))
            else:
                raise ValueError(f"Unsupported action {action!r}")
            response = {
                "type": "ack",
                "command_id": command_id,
                "ok": True,
                "state": self._state_message()["state"],
            }
        except Exception as exc:
            LOGGER.warning("GPIO command %s failed: %s", command_id, exc)
            response = {
                "type": "ack",
                "command_id": command_id,
                "ok": False,
                "error": str(exc),
                "state": self._state_message()["state"],
            }
        await websocket.send(json.dumps(response))


async def async_main(config_path: Path) -> None:
    config = ClientConfig.load(config_path)
    client = NodeClient(config)
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signum, client.stop_event.set)
    await client.run()


def main() -> None:
    parser = argparse.ArgumentParser(description="Hand of Agents Raspberry Pi client")
    parser.add_argument("--config", type=Path, required=True, help="Path to client TOML config")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(async_main(args.config))


if __name__ == "__main__":
    main()
