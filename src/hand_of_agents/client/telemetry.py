from __future__ import annotations

import os
import platform
import socket
from pathlib import Path
from typing import Any


def _read_text(path: str) -> str | None:
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def system_metadata() -> dict[str, Any]:
    model = _read_text("/proc/device-tree/model")
    return {
        "hostname": socket.gethostname(),
        "model": model.rstrip("\x00") if model else platform.machine(),
        "platform": platform.platform(),
        "python": platform.python_version(),
    }


def system_telemetry() -> dict[str, Any]:
    load_1m, load_5m, load_15m = os.getloadavg()
    memory = _read_text("/proc/meminfo") or ""
    mem_values: dict[str, int] = {}
    for line in memory.splitlines():
        key, separator, rest = line.partition(":")
        if separator and key in {"MemTotal", "MemAvailable"}:
            mem_values[key] = int(rest.strip().split()[0]) * 1024
    temperature = _read_text("/sys/class/thermal/thermal_zone0/temp")
    return {
        "uptime_seconds": float((_read_text("/proc/uptime") or "0").split()[0]),
        "load": [round(load_1m, 2), round(load_5m, 2), round(load_15m, 2)],
        "memory_total_bytes": mem_values.get("MemTotal"),
        "memory_available_bytes": mem_values.get("MemAvailable"),
        "temperature_c": round(int(temperature) / 1000, 1) if temperature else None,
    }

