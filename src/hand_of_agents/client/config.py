from __future__ import annotations

import tomllib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal

PinDirection = Literal["input", "output", "unconfigured"]


RASPBERRY_PI_40PIN_GPIO: tuple[dict[str, Any], ...] = (
    {"physical": 3, "bcm": 2, "function": "I2C1 SDA"},
    {"physical": 5, "bcm": 3, "function": "I2C1 SCL"},
    {"physical": 7, "bcm": 4, "function": "GPCLK0"},
    {"physical": 8, "bcm": 14, "function": "UART TXD"},
    {"physical": 10, "bcm": 15, "function": "UART RXD"},
    {"physical": 11, "bcm": 17, "function": "GPIO"},
    {"physical": 12, "bcm": 18, "function": "PWM0 / PCM CLK"},
    {"physical": 13, "bcm": 27, "function": "GPIO"},
    {"physical": 15, "bcm": 22, "function": "GPIO"},
    {"physical": 16, "bcm": 23, "function": "GPIO"},
    {"physical": 18, "bcm": 24, "function": "GPIO"},
    {"physical": 19, "bcm": 10, "function": "SPI0 MOSI"},
    {"physical": 21, "bcm": 9, "function": "SPI0 MISO"},
    {"physical": 22, "bcm": 25, "function": "GPIO"},
    {"physical": 23, "bcm": 11, "function": "SPI0 SCLK"},
    {"physical": 24, "bcm": 8, "function": "SPI0 CE0"},
    {"physical": 26, "bcm": 7, "function": "SPI0 CE1"},
    {"physical": 29, "bcm": 5, "function": "GPIO"},
    {"physical": 31, "bcm": 6, "function": "GPIO"},
    {"physical": 32, "bcm": 12, "function": "PWM0"},
    {"physical": 33, "bcm": 13, "function": "PWM1"},
    {"physical": 35, "bcm": 19, "function": "PWM1 / PCM FS"},
    {"physical": 36, "bcm": 16, "function": "GPIO"},
    {"physical": 37, "bcm": 26, "function": "GPIO"},
    {"physical": 38, "bcm": 20, "function": "PCM DIN"},
    {"physical": 40, "bcm": 21, "function": "PCM DOUT"},
)


@dataclass(frozen=True, slots=True)
class PinConfig:
    name: str
    bcm: int
    direction: PinDirection
    active_high: bool = True
    safe_state: bool = False
    pull: Literal["up", "down", "floating"] = "floating"
    description: str = ""
    physical: int | None = None
    default_function: str = "GPIO"

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "PinConfig":
        direction = value.get("direction")
        if direction not in {"input", "output", "unconfigured"}:
            raise ValueError(
                f"Pin {value.get('name')!r}: direction must be input, output, or unconfigured"
            )
        pull = value.get("pull", "floating")
        if pull not in {"up", "down", "floating"}:
            raise ValueError(f"Pin {value.get('name')!r}: invalid pull value")
        return cls(
            name=str(value["name"]),
            bcm=int(value["bcm"]),
            direction=direction,
            active_high=bool(value.get("active_high", True)),
            safe_state=bool(value.get("safe_state", False)),
            pull=pull,
            description=str(value.get("description", "")),
            physical=int(value["physical"]) if value.get("physical") is not None else None,
            default_function=str(value.get("default_function", "GPIO")),
        )

    def public_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "bcm": self.bcm,
            "direction": self.direction,
            "active_high": self.active_high,
            "safe_state": self.safe_state,
            "pull": self.pull,
            "description": self.description,
            "physical": self.physical,
            "default_function": self.default_function,
        }


def raspberry_pi_40pin_gpio() -> tuple[PinConfig, ...]:
    return tuple(
        PinConfig(
            name=f"GPIO{item['bcm']}",
            bcm=item["bcm"],
            physical=item["physical"],
            direction="unconfigured",
            default_function=item["function"],
            description=f"Physical pin {item['physical']} · {item['function']}",
        )
        for item in RASPBERRY_PI_40PIN_GPIO
    )


@dataclass(frozen=True, slots=True)
class ClientConfig:
    node_id: str
    server_url: str
    token: str
    pins: tuple[PinConfig, ...]
    heartbeat_seconds: float = 5.0
    telemetry_seconds: float = 2.0
    reconnect_seconds: float = 3.0
    max_pulse_ms: int = 10000
    gpio_backend: Literal["auto", "gpiozero", "mock"] = "auto"
    board_profile: str | None = None

    @classmethod
    def load(cls, path: Path) -> "ClientConfig":
        with path.open("rb") as config_file:
            value = tomllib.load(config_file)
        board_profile = value.get("board_profile")
        if board_profile not in {None, "raspberry-pi-40pin"}:
            raise ValueError("board_profile must be raspberry-pi-40pin when set")
        configured_pins = tuple(PinConfig.from_dict(pin) for pin in value.get("pins", []))
        if board_profile == "raspberry-pi-40pin":
            generated = {pin.bcm: pin for pin in raspberry_pi_40pin_gpio()}
            for pin in configured_pins:
                base = generated.get(pin.bcm)
                if base:
                    pin = replace(
                        pin,
                        physical=pin.physical or base.physical,
                        default_function=(
                            base.default_function
                            if pin.default_function == "GPIO"
                            else pin.default_function
                        ),
                        description=pin.description or base.description,
                    )
                generated[pin.bcm] = pin
            pins = tuple(sorted(generated.values(), key=lambda pin: pin.physical or 100 + pin.bcm))
        else:
            pins = configured_pins
        names = [pin.name for pin in pins]
        bcm_numbers = [pin.bcm for pin in pins]
        if not pins:
            raise ValueError("Set board_profile or provide at least one [[pins]] entry")
        if len(names) != len(set(names)):
            raise ValueError("Pin names must be unique")
        if len(bcm_numbers) != len(set(bcm_numbers)):
            raise ValueError("BCM pin numbers must be unique")
        backend = value.get("gpio_backend", "auto")
        if backend not in {"auto", "gpiozero", "mock"}:
            raise ValueError("gpio_backend must be auto, gpiozero, or mock")
        server_url = str(value["server_url"]).rstrip("/")
        if not server_url.startswith(("ws://", "wss://")):
            raise ValueError("server_url must start with ws:// or wss://")
        return cls(
            node_id=str(value["node_id"]),
            server_url=server_url,
            token=str(value["token"]),
            pins=pins,
            heartbeat_seconds=float(value.get("heartbeat_seconds", 5)),
            telemetry_seconds=float(value.get("telemetry_seconds", 2)),
            reconnect_seconds=float(value.get("reconnect_seconds", 3)),
            max_pulse_ms=int(value.get("max_pulse_ms", 10000)),
            gpio_backend=backend,
            board_profile=board_profile,
        )
