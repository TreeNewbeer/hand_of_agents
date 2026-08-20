from __future__ import annotations

import asyncio
from typing import Any, Protocol

from hand_of_agents.client.config import PinConfig


class GpioDriver(Protocol):
    def read(self, name: str) -> bool | None: ...
    def write(self, name: str, value: bool) -> None: ...
    def configure(self, name: str, direction: str, pull: str, initial: bool) -> None: ...
    def release(self, name: str) -> None: ...
    def close(self) -> None: ...


class MockGpioDriver:
    def __init__(self, pins: tuple[PinConfig, ...]) -> None:
        self._pins = {pin.name: pin for pin in pins}
        self._values = {
            pin.name: (
                pin.safe_state
                if pin.direction == "output"
                else False if pin.direction == "input" else None
            )
            for pin in pins
        }
        self._modes = {pin.name: pin.direction for pin in pins}

    def read(self, name: str) -> bool | None:
        if name not in self._values:
            raise KeyError(f"Unknown pin {name!r}")
        return self._values[name]

    def write(self, name: str, value: bool) -> None:
        pin = self._pins.get(name)
        if not pin:
            raise KeyError(f"Unknown pin {name!r}")
        if self._modes[name] != "output":
            raise ValueError(f"Pin {name!r} is not an output")
        self._values[name] = bool(value)

    def configure(self, name: str, direction: str, pull: str, initial: bool) -> None:
        if name not in self._pins:
            raise KeyError(f"Unknown pin {name!r}")
        self._modes[name] = direction
        self._values[name] = bool(initial) if direction == "output" else False

    def release(self, name: str) -> None:
        if name not in self._pins:
            raise KeyError(f"Unknown pin {name!r}")
        self._modes[name] = "unconfigured"
        self._values[name] = None

    def close(self) -> None:
        pass


class GpioZeroDriver:
    def __init__(self, pins: tuple[PinConfig, ...]) -> None:
        self._pins = {pin.name: pin for pin in pins}
        self._devices: dict[str, Any] = {}
        try:
            for pin in pins:
                if pin.direction != "unconfigured":
                    self._devices[pin.name] = self._create_device(
                        pin, pin.direction, pin.pull, pin.safe_state
                    )
        except Exception:
            self.close()
            raise

    def _create_device(self, pin: PinConfig, direction: str, pull: str, initial: bool) -> Any:
        from gpiozero import DigitalInputDevice, OutputDevice

        if direction == "output":
            return OutputDevice(
                pin.bcm,
                active_high=pin.active_high,
                initial_value=initial,
            )
        pull_up = {"up": True, "down": False, "floating": None}[pull]
        if pull == "floating":
            return DigitalInputDevice(pin.bcm, pull_up=None, active_state=True)
        return DigitalInputDevice(pin.bcm, pull_up=pull_up)

    def read(self, name: str) -> bool | None:
        device = self._devices.get(name)
        if name not in self._pins:
            raise KeyError(f"Unknown pin {name!r}")
        if device is None:
            return None
        if not hasattr(device, "on"):
            return bool(device.pin.state)
        return bool(device.value)

    def write(self, name: str, value: bool) -> None:
        pin = self._pins.get(name)
        if not pin:
            raise KeyError(f"Unknown pin {name!r}")
        if name not in self._devices or not hasattr(self._devices[name], "on"):
            raise ValueError(f"Pin {name!r} is not an output")
        if value:
            self._devices[name].on()
        else:
            self._devices[name].off()

    def configure(self, name: str, direction: str, pull: str, initial: bool) -> None:
        pin = self._pins.get(name)
        if not pin:
            raise KeyError(f"Unknown pin {name!r}")
        self.release(name)
        self._devices[name] = self._create_device(pin, direction, pull, initial)

    def release(self, name: str) -> None:
        device = self._devices.pop(name, None)
        if device is not None:
            device.close()

    def close(self) -> None:
        for device in self._devices.values():
            device.close()
        self._devices.clear()


def create_driver(backend: str, pins: tuple[PinConfig, ...]) -> GpioDriver:
    if backend == "mock":
        return MockGpioDriver(pins)
    if backend in {"auto", "gpiozero"}:
        return GpioZeroDriver(pins)
    raise ValueError(f"Unsupported GPIO backend {backend!r}")


class GpioController:
    def __init__(self, driver: GpioDriver, pins: tuple[PinConfig, ...], max_pulse_ms: int) -> None:
        self.driver = driver
        self.pins = {pin.name: pin for pin in pins}
        self.modes = {pin.name: pin.direction for pin in pins}
        self.pulls = {pin.name: pin.pull for pin in pins}
        self.max_pulse_ms = max_pulse_ms
        self._pulse_tasks: dict[str, asyncio.Task[None]] = {}
        self._continuous_pins: set[str] = set()
        self._pulse_half_periods = {name: 0.5 for name in self.pins}

    def snapshot(self) -> dict[str, bool | None]:
        return {name: self.driver.read(name) for name in self.pins}

    def mode_snapshot(self) -> dict[str, str]:
        return dict(self.modes)

    def pull_snapshot(self) -> dict[str, str]:
        return dict(self.pulls)

    def behavior_snapshot(self) -> dict[str, str | None]:
        return {
            name: "pulse" if name in self._continuous_pins else None for name in self.pins
        }

    def pulse_frequency_snapshot(self) -> dict[str, float]:
        return {
            name: round(1 / (2 * half_period), 3)
            for name, half_period in self._pulse_half_periods.items()
        }

    def set_pulse_frequency(self, name: str, frequency_hz: float) -> None:
        self._require_pin(name)
        if frequency_hz < 0.1 or frequency_hz > 10:
            raise ValueError("pulse_hz must be between 0.1 and 10")
        self._pulse_half_periods[name] = 1 / (2 * frequency_hz)
        if name in self._continuous_pins:
            self._start_continuous_pulse(name)

    def configure(self, name: str, direction: str, pull: str = "floating") -> None:
        pin = self._require_pin(name)
        if direction not in {"input", "output", "unconfigured"}:
            raise ValueError("direction must be input, output, or unconfigured")
        if pull not in {"up", "down", "floating"}:
            raise ValueError("pull must be up, down, or floating")
        self._cancel_pulse(name)
        if direction == "unconfigured":
            self.driver.release(name)
        else:
            try:
                self.driver.configure(name, direction, pull, pin.safe_state)
            except Exception:
                self.driver.release(name)
                self.modes[name] = "unconfigured"
                self.pulls[name] = "floating"
                raise
        self.modes[name] = direction
        self.pulls[name] = pull

    def set_value(self, name: str, value: bool) -> None:
        self._require_output(name)
        self._cancel_pulse(name)
        self.driver.write(name, value)

    def toggle(self, name: str) -> None:
        self.set_value(name, not self.driver.read(name))

    def pulse(self, name: str, duration_ms: int, continuous: bool = False) -> None:
        pin = self._require_output(name)
        if duration_ms < 50 or duration_ms > self.max_pulse_ms:
            raise ValueError(f"duration_ms must be between 50 and {self.max_pulse_ms}")
        self._cancel_pulse(name)
        if continuous:
            self._pulse_half_periods[name] = duration_ms / 1000
        self.driver.write(name, not pin.safe_state)
        if continuous:
            self._start_continuous_pulse(name)
        else:
            self._pulse_tasks[name] = asyncio.create_task(
                self._finish_pulse(name, pin.safe_state, duration_ms / 1000)
            )

    def apply_safe_state(self) -> None:
        for name in list(self._pulse_tasks):
            self._cancel_pulse(name)
        for pin in self.pins.values():
            if self.modes[pin.name] == "output":
                self.driver.write(pin.name, pin.safe_state)

    def close(self) -> None:
        self.apply_safe_state()
        self.driver.close()

    def _require_pin(self, name: str) -> PinConfig:
        pin = self.pins.get(name)
        if not pin:
            raise KeyError(f"Unknown pin {name!r}")
        return pin

    def _require_output(self, name: str) -> PinConfig:
        pin = self._require_pin(name)
        if self.modes[name] != "output":
            raise ValueError(f"Pin {name!r} is not an output")
        return pin

    def _cancel_pulse(self, name: str) -> None:
        task = self._pulse_tasks.pop(name, None)
        self._continuous_pins.discard(name)
        if task:
            task.cancel()

    def _start_continuous_pulse(self, name: str) -> None:
        task = self._pulse_tasks.pop(name, None)
        if task:
            task.cancel()
        self._continuous_pins.add(name)
        self._pulse_tasks[name] = asyncio.create_task(self._run_continuous_pulse(name))

    async def _finish_pulse(self, name: str, safe_state: bool, delay: float) -> None:
        this_task = asyncio.current_task()
        try:
            await asyncio.sleep(delay)
            self.driver.write(name, safe_state)
        finally:
            if self._pulse_tasks.get(name) is this_task:
                self._pulse_tasks.pop(name, None)

    async def _run_continuous_pulse(self, name: str) -> None:
        this_task = asyncio.current_task()
        try:
            while True:
                await asyncio.sleep(self._pulse_half_periods[name])
                self.driver.write(name, not self.driver.read(name))
        finally:
            if self._pulse_tasks.get(name) is this_task:
                self._pulse_tasks.pop(name, None)
                self._continuous_pins.discard(name)
