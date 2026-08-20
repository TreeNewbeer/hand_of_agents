from hand_of_agents.client import telemetry


def test_board_serial_prefers_device_tree(monkeypatch) -> None:
    values = {
        "/sys/firmware/devicetree/base/serial-number": "000000001234abcd\x00",
        "/proc/cpuinfo": "Serial : ignored",
    }
    monkeypatch.setattr(telemetry, "_read_text", values.get)

    assert telemetry.board_serial() == "000000001234abcd"


def test_board_serial_falls_back_to_cpuinfo(monkeypatch) -> None:
    values = {
        "/proc/cpuinfo": "Processor\t: ARMv7\nSerial\t\t: 00000000deadbeef\n",
    }
    monkeypatch.setattr(telemetry, "_read_text", values.get)

    assert telemetry.board_serial() == "00000000deadbeef"
