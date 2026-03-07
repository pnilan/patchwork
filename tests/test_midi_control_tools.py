from unittest.mock import MagicMock

import pytest
from pydantic_ai import RunContext
from pydantic_ai.usage import RunUsage

from patchwork.deps import PatchworkDeps
from patchwork.midi import MidiConnection
from patchwork.synth_definitions import CCParameter, SynthDefinition
from patchwork.tools.midi_control import (
    connect_midi,
    list_midi_ports,
    list_synths,
    send_cc,
    send_patch,
)


def _make_synth() -> SynthDefinition:
    return SynthDefinition(
        name="TestSynth",
        manufacturer="TestCo",
        midi_channel=1,
        cc_map={
            "cutoff": CCParameter(cc=74),
            "resonance": CCParameter(cc=71),
            "special": CCParameter(cc=50, value_range=(0, 64)),
        },
    )


def _make_ctx(
    midi: MidiConnection | None = None,
    synths: dict[str, SynthDefinition] | None = None,
) -> RunContext[PatchworkDeps]:
    if midi is None:
        midi = MidiConnection()
    if synths is None:
        synth = _make_synth()
        synths = {synth.name.lower(): synth}
    deps = PatchworkDeps(midi=midi, synths=synths)
    return RunContext(deps=deps, model=MagicMock(), usage=RunUsage())


@pytest.mark.asyncio
async def test_send_cc_valid():
    midi = MidiConnection()
    mock_out = MagicMock()
    midi._out = mock_out
    midi._port_name = "Test Port"

    ctx = _make_ctx(midi=midi)
    result = await send_cc(ctx, synth="testsynth", parameter="cutoff", value=64)
    assert "Sent CC 74 = 64" in result
    mock_out.send_message.assert_called_once_with([0xB0, 74, 64])


@pytest.mark.asyncio
async def test_send_cc_unknown_synth():
    ctx = _make_ctx()
    result = await send_cc(ctx, synth="unknown", parameter="cutoff", value=64)
    assert "Unknown synth" in result
    assert "testsynth" in result


@pytest.mark.asyncio
async def test_send_cc_unknown_parameter():
    midi = MidiConnection()
    midi._out = MagicMock()
    midi._port_name = "Test Port"
    ctx = _make_ctx(midi=midi)
    result = await send_cc(ctx, synth="testsynth", parameter="nonexistent", value=64)
    assert "Unknown parameter" in result
    assert "cutoff" in result


@pytest.mark.asyncio
async def test_send_cc_value_out_of_range():
    midi = MidiConnection()
    midi._out = MagicMock()
    midi._port_name = "Test Port"
    ctx = _make_ctx(midi=midi)
    result = await send_cc(ctx, synth="testsynth", parameter="special", value=100)
    assert "out of range" in result
    assert "0-64" in result


@pytest.mark.asyncio
async def test_send_cc_not_connected():
    ctx = _make_ctx()
    result = await send_cc(ctx, synth="testsynth", parameter="cutoff", value=64)
    assert "MIDI not connected" in result


@pytest.mark.asyncio
async def test_send_patch_valid():
    midi = MidiConnection()
    mock_out = MagicMock()
    midi._out = mock_out
    midi._port_name = "Test Port"

    ctx = _make_ctx(midi=midi)
    result = await send_patch(ctx, synth="testsynth", settings={"cutoff": 64, "resonance": 80})
    assert "cutoff = 64" in result
    assert "resonance = 80" in result
    assert mock_out.send_message.call_count == 2


@pytest.mark.asyncio
async def test_send_patch_partial_failure():
    midi = MidiConnection()
    mock_out = MagicMock()
    midi._out = mock_out
    midi._port_name = "Test Port"

    ctx = _make_ctx(midi=midi)
    result = await send_patch(
        ctx,
        synth="testsynth",
        settings={"cutoff": 64, "nonexistent": 50, "special": 100},
    )
    assert "cutoff = 64" in result
    assert "Unknown parameter" in result
    assert "out of range" in result
    assert mock_out.send_message.call_count == 1


@pytest.mark.asyncio
async def test_list_midi_ports_empty():
    midi = MidiConnection()
    with MagicMock() as mock_rtmidi:
        midi.list_ports = MagicMock(return_value=[])
    ctx = _make_ctx(midi=midi)
    result = await list_midi_ports(ctx)
    assert "No MIDI output ports found" in result


@pytest.mark.asyncio
async def test_list_midi_ports_with_ports():
    midi = MidiConnection()
    midi.list_ports = MagicMock(return_value=["Port A", "Port B"])
    ctx = _make_ctx(midi=midi)
    result = await list_midi_ports(ctx)
    assert "Port A" in result
    assert "Port B" in result
    assert "0: Port A" in result
    assert "1: Port B" in result


@pytest.mark.asyncio
async def test_connect_midi_success():
    midi = MidiConnection()
    midi.open = MagicMock(return_value="Test Port")
    ctx = _make_ctx(midi=midi)
    result = await connect_midi(ctx, port_index=0)
    assert "Connected to MIDI port: Test Port" in result


@pytest.mark.asyncio
async def test_connect_midi_no_ports():
    midi = MidiConnection()
    midi.open = MagicMock(side_effect=RuntimeError("No MIDI output ports available"))
    ctx = _make_ctx(midi=midi)
    result = await connect_midi(ctx, port_index=0)
    assert "No MIDI output ports available" in result


@pytest.mark.asyncio
async def test_list_synths_with_synths():
    ctx = _make_ctx()
    result = await list_synths(ctx)
    assert "TestCo TestSynth" in result
    assert "cutoff" in result
    assert "resonance" in result


@pytest.mark.asyncio
async def test_list_synths_empty():
    ctx = _make_ctx(synths={})
    result = await list_synths(ctx)
    assert "No synth definitions loaded" in result
