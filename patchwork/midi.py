import rtmidi


class MidiConnection:
    def __init__(self):
        self._out: rtmidi.MidiOut | None = None
        self._port_name: str | None = None

    @property
    def is_connected(self) -> bool:
        return self._out is not None

    @property
    def port_name(self) -> str | None:
        return self._port_name

    def list_ports(self) -> list[str]:
        """List available MIDI output port names."""
        out = rtmidi.MidiOut()
        ports = out.get_ports()
        del out
        return ports

    def open(self, port_index: int = 0) -> str:
        """Open a MIDI output port by index. Returns the port name."""
        self.close()
        self._out = rtmidi.MidiOut()
        ports = self._out.get_ports()
        if not ports:
            raise RuntimeError("No MIDI output ports available")
        if not (0 <= port_index < len(ports)):
            raise ValueError(f"Port index {port_index} out of range (0-{len(ports) - 1})")
        self._out.open_port(port_index)
        self._port_name = ports[port_index]
        return self._port_name

    def close(self):
        """Close the current MIDI connection."""
        if self._out is not None:
            self._out.close_port()
            del self._out
            self._out = None
            self._port_name = None

    def send_cc(self, channel: int, cc_number: int, value: int):
        """Send a MIDI CC message. Channel is 1-16 (converted to 0-15 internally)."""
        if self._out is None:
            raise RuntimeError("MIDI port not open — call open() first")
        if not (1 <= channel <= 16):
            raise ValueError(f"MIDI channel must be 1-16, got {channel}")
        if not (0 <= cc_number <= 127):
            raise ValueError(f"CC number must be 0-127, got {cc_number}")
        if not (0 <= value <= 127):
            raise ValueError(f"CC value must be 0-127, got {value}")
        status = 0xB0 | (channel - 1)
        self._out.send_message([status, cc_number, value])
