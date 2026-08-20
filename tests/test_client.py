import asyncio

from hand_of_agents.client.app import NodeClient
from hand_of_agents.client.config import ClientConfig, PinConfig


def test_stop_event_interrupts_active_connection() -> None:
    async def exercise() -> None:
        config = ClientConfig(
            node_id="test",
            server_url="ws://localhost/ws/nodes/test",
            token="secret",
            pins=(PinConfig("GPIO17", 17, "unconfigured"),),
            gpio_backend="mock",
        )
        client = NodeClient(config)

        async def connection_that_never_finishes() -> None:
            await asyncio.Event().wait()

        client._connection_session = connection_that_never_finishes  # type: ignore[method-assign]
        run_task = asyncio.create_task(client.run())
        await asyncio.sleep(0)
        client.stop_event.set()
        await asyncio.wait_for(run_task, timeout=0.2)

    asyncio.run(exercise())


def test_same_output_configuration_preserves_running_pulse() -> None:
    async def exercise() -> None:
        config = ClientConfig(
            node_id="test",
            server_url="ws://localhost/ws/nodes/test",
            token="secret",
            pins=(PinConfig("GPIO17", 17, "output"),),
            gpio_backend="mock",
        )
        client = NodeClient(config)
        client.controller.pulse("GPIO17", 100, continuous=True)

        class FakeWebSocket:
            def __init__(self) -> None:
                self.messages: list[str] = []

            async def send(self, message: str) -> None:
                self.messages.append(message)

        websocket = FakeWebSocket()
        await client._handle_message(
            websocket,
            {
                "type": "command",
                "command_id": "frequency-change",
                "action": "configure",
                "pin": "GPIO17",
                "direction": "output",
                "pull": "floating",
                "pulse_hz": 2,
            },
        )

        assert client.controller.mode_snapshot()["GPIO17"] == "output"
        assert client.controller.behavior_snapshot()["GPIO17"] == "pulse"
        assert client.controller.pulse_frequency_snapshot()["GPIO17"] == 2.0
        client.controller.close()

    asyncio.run(exercise())
