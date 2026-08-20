import asyncio

import pytest

from hand_of_agents.client.config import PinConfig
from hand_of_agents.client.gpio import GpioController, MockGpioDriver


@pytest.fixture
def pins() -> tuple[PinConfig, ...]:
    return (
        PinConfig("relay", 17, "output", active_high=False, safe_state=False),
        PinConfig("sensor", 27, "input"),
    )


def test_set_toggle_and_safe_state(pins: tuple[PinConfig, ...]) -> None:
    controller = GpioController(MockGpioDriver(pins), pins, max_pulse_ms=1000)
    controller.set_value("relay", True)
    assert controller.snapshot()["relay"] is True
    controller.toggle("relay")
    assert controller.snapshot()["relay"] is False
    controller.set_value("relay", True)
    controller.apply_safe_state()
    assert controller.snapshot()["relay"] is False


def test_input_cannot_be_written(pins: tuple[PinConfig, ...]) -> None:
    controller = GpioController(MockGpioDriver(pins), pins, max_pulse_ms=1000)
    with pytest.raises(ValueError, match="not an output"):
        controller.set_value("sensor", True)


def test_pulse_returns_to_safe_state(pins: tuple[PinConfig, ...]) -> None:
    async def exercise() -> None:
        controller = GpioController(MockGpioDriver(pins), pins, max_pulse_ms=1000)
        controller.pulse("relay", 50)
        assert controller.snapshot()["relay"] is True
        await asyncio.sleep(0.08)
        assert controller.snapshot()["relay"] is False

    asyncio.run(exercise())


def test_replacing_pulse_does_not_lose_new_task(pins: tuple[PinConfig, ...]) -> None:
    async def exercise() -> None:
        controller = GpioController(MockGpioDriver(pins), pins, max_pulse_ms=1000)
        controller.pulse("relay", 50)
        controller.pulse("relay", 100)
        await asyncio.sleep(0)
        controller.set_value("relay", True)
        await asyncio.sleep(0.12)
        assert controller.snapshot()["relay"] is True

    asyncio.run(exercise())


def test_continuous_pulse_runs_until_level_is_set(pins: tuple[PinConfig, ...]) -> None:
    async def exercise() -> None:
        controller = GpioController(MockGpioDriver(pins), pins, max_pulse_ms=1000)
        controller.pulse("relay", 50, continuous=True)
        assert controller.behavior_snapshot()["relay"] == "pulse"
        assert controller.pulse_frequency_snapshot()["relay"] == 10.0
        assert controller.snapshot()["relay"] is True
        await asyncio.sleep(0.07)
        assert controller.snapshot()["relay"] is False
        await asyncio.sleep(0.06)
        assert controller.snapshot()["relay"] is True
        controller.set_value("relay", False)
        assert controller.behavior_snapshot()["relay"] is None
        await asyncio.sleep(0.07)
        assert controller.snapshot()["relay"] is False

    asyncio.run(exercise())


def test_pulse_frequency_defaults_and_validation(pins: tuple[PinConfig, ...]) -> None:
    controller = GpioController(MockGpioDriver(pins), pins, max_pulse_ms=1000)

    assert controller.pulse_frequency_snapshot()["relay"] == 1.0
    controller.set_pulse_frequency("relay", 2.5)
    assert controller.pulse_frequency_snapshot()["relay"] == 2.5

    with pytest.raises(ValueError, match="between 0.1 and 10"):
        controller.set_pulse_frequency("relay", 0.09)


def test_frequency_change_preserves_continuous_pulse(pins: tuple[PinConfig, ...]) -> None:
    async def exercise() -> None:
        controller = GpioController(MockGpioDriver(pins), pins, max_pulse_ms=1000)
        controller.pulse("relay", 100, continuous=True)
        initial_level = controller.snapshot()["relay"]

        controller.set_pulse_frequency("relay", 10)

        assert controller.snapshot()["relay"] is initial_level
        assert controller.behavior_snapshot()["relay"] == "pulse"
        assert controller.pulse_frequency_snapshot()["relay"] == 10.0
        await asyncio.sleep(0.07)
        assert controller.snapshot()["relay"] is not initial_level
        controller.close()

    asyncio.run(exercise())


def test_dynamic_pin_can_be_configured_and_released() -> None:
    pins = (PinConfig("GPIO4", 4, "unconfigured", physical=7),)
    controller = GpioController(MockGpioDriver(pins), pins, max_pulse_ms=1000)
    assert controller.snapshot()["GPIO4"] is None
    assert controller.mode_snapshot()["GPIO4"] == "unconfigured"

    controller.configure("GPIO4", "input", "up")
    assert controller.snapshot()["GPIO4"] is False
    with pytest.raises(ValueError, match="not an output"):
        controller.set_value("GPIO4", True)

    controller.configure("GPIO4", "output")
    controller.set_value("GPIO4", True)
    assert controller.snapshot()["GPIO4"] is True

    controller.configure("GPIO4", "unconfigured")
    assert controller.snapshot()["GPIO4"] is None


def test_failed_dynamic_configuration_rolls_back_to_unconfigured() -> None:
    class FailingDriver(MockGpioDriver):
        def configure(self, name: str, direction: str, pull: str, initial: bool) -> None:
            self.release(name)
            raise OSError("GPIO unavailable")

    pins = (PinConfig("GPIO4", 4, "unconfigured"),)
    controller = GpioController(FailingDriver(pins), pins, max_pulse_ms=1000)
    with pytest.raises(OSError, match="unavailable"):
        controller.configure("GPIO4", "input", "down")
    assert controller.mode_snapshot()["GPIO4"] == "unconfigured"
    assert controller.snapshot()["GPIO4"] is None
