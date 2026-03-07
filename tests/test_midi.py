from unittest.mock import MagicMock, patch

import pytest

from patchwork.midi import MidiConnection


def test_midi_connection_initial_state():
    conn = MidiConnection()
    assert conn.is_connected is False
    assert conn.port_name is None


def test_send_cc_without_open():
    conn = MidiConnection()
    with pytest.raises(RuntimeError, match="MIDI port not open"):
        conn.send_cc(channel=1, cc_number=22, value=64)


def test_send_cc_channel_validation():
    conn = MidiConnection()
    conn._out = MagicMock()
    with pytest.raises(ValueError, match="MIDI channel must be 1-16"):
        conn.send_cc(channel=0, cc_number=22, value=64)
    with pytest.raises(ValueError, match="MIDI channel must be 1-16"):
        conn.send_cc(channel=17, cc_number=22, value=64)


def test_send_cc_value_validation():
    conn = MidiConnection()
    conn._out = MagicMock()
    with pytest.raises(ValueError, match="CC value must be 0-127"):
        conn.send_cc(channel=1, cc_number=22, value=-1)
    with pytest.raises(ValueError, match="CC value must be 0-127"):
        conn.send_cc(channel=1, cc_number=22, value=128)


def test_send_cc_number_validation():
    conn = MidiConnection()
    conn._out = MagicMock()
    with pytest.raises(ValueError, match="CC number must be 0-127"):
        conn.send_cc(channel=1, cc_number=-1, value=64)
    with pytest.raises(ValueError, match="CC number must be 0-127"):
        conn.send_cc(channel=1, cc_number=128, value=64)


def test_send_cc_message_format():
    conn = MidiConnection()
    mock_out = MagicMock()
    conn._out = mock_out
    conn.send_cc(channel=2, cc_number=22, value=64)
    mock_out.send_message.assert_called_once_with([0xB1, 22, 64])


@patch("patchwork.midi.rtmidi.MidiOut")
def test_open_no_ports(mock_midi_out_cls):
    mock_instance = MagicMock()
    mock_instance.get_ports.return_value = []
    mock_midi_out_cls.return_value = mock_instance

    conn = MidiConnection()
    with pytest.raises(RuntimeError, match="No MIDI output ports available"):
        conn.open()


@patch("patchwork.midi.rtmidi.MidiOut")
def test_list_ports(mock_midi_out_cls):
    mock_instance = MagicMock()
    mock_instance.get_ports.return_value = ["Port A", "Port B"]
    mock_midi_out_cls.return_value = mock_instance

    conn = MidiConnection()
    ports = conn.list_ports()
    assert ports == ["Port A", "Port B"]
