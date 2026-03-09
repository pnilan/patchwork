from unittest.mock import MagicMock

import pytest
from pydantic_ai import RunContext
from pydantic_ai.usage import RunUsage

from patchwork.deps import PatchworkDeps
from patchwork.midi import MidiConnection
from patchwork.patch_library import PatchLibrary
from patchwork.synth_definitions import CCParameter, SynthDefinition
from patchwork.tools.patches import (
    delete_patch,
    list_patches,
    load_patch,
    recall_patch,
    save_patch,
)


@pytest.fixture
def patch_lib(tmp_path):
    with PatchLibrary(db_path=tmp_path / "test.db") as lib:
        yield lib


def _make_synth() -> SynthDefinition:
    return SynthDefinition(
        name="TestSynth",
        manufacturer="TestCo",
        midi_channel=1,
        cc_map={
            "cutoff": CCParameter(cc=74),
            "resonance": CCParameter(cc=71),
        },
    )


def _make_ctx(
    midi: MidiConnection | None = None,
    synths: dict[str, SynthDefinition] | None = None,
    patches: PatchLibrary | None = None,
) -> RunContext[PatchworkDeps]:
    if midi is None:
        midi = MidiConnection()
    if synths is None:
        synth = _make_synth()
        synths = {synth.name.lower(): synth}
    if patches is None:
        patches = MagicMock()
    deps = PatchworkDeps(midi=midi, synths=synths, patches=patches)
    return RunContext(deps=deps, model=MagicMock(), usage=RunUsage())


@pytest.mark.asyncio
async def test_save_patch_valid(patch_lib):
    ctx = _make_ctx(patches=patch_lib)
    result = await save_patch(
        ctx, name="bass", synth="testsynth", settings={"cutoff": 45, "resonance": 80}
    )
    assert "Saved patch 'bass'" in result
    assert "cutoff = 45" in result
    assert "resonance = 80" in result


@pytest.mark.asyncio
async def test_save_patch_unknown_synth(patch_lib):
    ctx = _make_ctx(patches=patch_lib)
    result = await save_patch(ctx, name="bass", synth="unknown", settings={"cutoff": 45})
    assert "Unknown synth 'unknown'" in result
    assert "testsynth" in result


@pytest.mark.asyncio
async def test_save_patch_invalid_parameter(patch_lib):
    ctx = _make_ctx(patches=patch_lib)
    result = await save_patch(ctx, name="bass", synth="testsynth", settings={"nonexistent": 45})
    assert "Unknown parameter(s)" in result
    assert "nonexistent" in result
    assert "cutoff" in result


@pytest.mark.asyncio
async def test_save_patch_normalizes_keys(patch_lib):
    ctx = _make_ctx(patches=patch_lib)
    # Use mixed case and spaces — should normalize to lowercase underscored
    synth = SynthDefinition(
        name="TestSynth",
        manufacturer="TestCo",
        midi_channel=1,
        cc_map={
            "filter_cutoff": CCParameter(cc=74),
        },
    )
    ctx = _make_ctx(synths={"testsynth": synth}, patches=patch_lib)
    result = await save_patch(ctx, name="bass", synth="testsynth", settings={"Filter Cutoff": 45})
    assert "Saved patch" in result
    stored = patch_lib.get("bass")
    assert stored is not None
    assert "filter_cutoff" in stored.settings
    assert stored.settings["filter_cutoff"] == 45


@pytest.mark.asyncio
async def test_save_patch_empty_description_stored_as_none(patch_lib):
    ctx = _make_ctx(patches=patch_lib)
    await save_patch(ctx, name="bass", synth="testsynth", settings={"cutoff": 45}, description="")
    stored = patch_lib.get("bass")
    assert stored is not None
    assert stored.description is None


@pytest.mark.asyncio
async def test_save_patch_value_out_of_range(patch_lib):
    synth = SynthDefinition(
        name="TestSynth",
        manufacturer="TestCo",
        midi_channel=1,
        cc_map={
            "special": CCParameter(cc=50, value_range=(0, 64)),
        },
    )
    ctx = _make_ctx(synths={"testsynth": synth}, patches=patch_lib)
    result = await save_patch(ctx, name="bass", synth="testsynth", settings={"special": 100})
    assert "out of range" in result
    assert "100" in result
    # Verify nothing was saved
    assert patch_lib.get("bass") is None


@pytest.mark.asyncio
async def test_save_patch_cross_synth_rejected(patch_lib):
    synth2 = SynthDefinition(
        name="OtherSynth",
        manufacturer="OtherCo",
        midi_channel=2,
        cc_map={"volume": CCParameter(cc=7)},
    )
    synths = {
        "testsynth": _make_synth(),
        "othersynth": synth2,
    }
    ctx = _make_ctx(synths=synths, patches=patch_lib)
    # Save "bass" for testsynth
    await save_patch(ctx, name="bass", synth="testsynth", settings={"cutoff": 45})
    # Try to save "bass" for a different synth
    result = await save_patch(ctx, name="bass", synth="othersynth", settings={"volume": 100})
    assert "already exists" in result
    assert "testsynth" in result
    # Verify original patch is unchanged
    stored = patch_lib.get("bass")
    assert stored is not None
    assert stored.synth == "testsynth"


@pytest.mark.asyncio
async def test_save_patch_same_synth_overwrites(patch_lib):
    ctx = _make_ctx(patches=patch_lib)
    await save_patch(ctx, name="bass", synth="testsynth", settings={"cutoff": 45})
    result = await save_patch(ctx, name="bass", synth="testsynth", settings={"cutoff": 90})
    assert "Saved patch 'bass'" in result
    stored = patch_lib.get("bass")
    assert stored is not None
    assert stored.settings["cutoff"] == 90


@pytest.mark.asyncio
async def test_save_patch_empty_settings(patch_lib):
    ctx = _make_ctx(patches=patch_lib)
    result = await save_patch(ctx, name="empty", synth="testsynth", settings={})
    assert "Saved patch 'empty'" in result
    stored = patch_lib.get("empty")
    assert stored is not None
    assert stored.settings == {}


@pytest.mark.asyncio
async def test_save_patch_with_description(patch_lib):
    ctx = _make_ctx(patches=patch_lib)
    await save_patch(
        ctx,
        name="bass",
        synth="testsynth",
        settings={"cutoff": 45},
        description="A deep bass",
    )
    stored = patch_lib.get("bass")
    assert stored is not None
    assert stored.description == "A deep bass"


@pytest.mark.asyncio
async def test_load_patch_exists(patch_lib):
    ctx = _make_ctx(patches=patch_lib)
    await save_patch(
        ctx,
        name="bass",
        synth="testsynth",
        settings={"cutoff": 45, "resonance": 80},
        description="Deep bass",
    )
    result = await load_patch(ctx, name="bass")
    assert "Patch 'bass'" in result
    assert "cutoff = 45" in result
    assert "resonance = 80" in result
    assert "Deep bass" in result


@pytest.mark.asyncio
async def test_load_patch_not_found(patch_lib):
    ctx = _make_ctx(patches=patch_lib)
    result = await load_patch(ctx, name="nonexistent")
    assert "No patch found" in result


@pytest.mark.asyncio
async def test_recall_patch_sends_cc(patch_lib):
    midi = MidiConnection()
    mock_out = MagicMock()
    midi._out = mock_out
    midi._port_name = "Test Port"

    ctx = _make_ctx(midi=midi, patches=patch_lib)
    await save_patch(ctx, name="bass", synth="testsynth", settings={"cutoff": 45, "resonance": 80})

    result = await recall_patch(ctx, name="bass")
    assert "Recalled patch 'bass'" in result
    assert "cutoff = 45" in result
    assert "resonance = 80" in result
    # Verify CC messages were sent (channel 1 = status 0xB0)
    assert mock_out.send_message.call_count == 2
    calls = [c.args[0] for c in mock_out.send_message.call_args_list]
    assert [0xB0, 74, 45] in calls  # cutoff CC 74
    assert [0xB0, 71, 80] in calls  # resonance CC 71


@pytest.mark.asyncio
async def test_recall_patch_not_found(patch_lib):
    ctx = _make_ctx(patches=patch_lib)
    result = await recall_patch(ctx, name="nonexistent")
    assert "No patch found" in result


@pytest.mark.asyncio
async def test_recall_patch_synth_not_loaded(patch_lib):
    ctx = _make_ctx(patches=patch_lib)
    # Save a patch for "testsynth"
    await save_patch(ctx, name="bass", synth="testsynth", settings={"cutoff": 45})
    # Now create a context without the synth definition
    ctx_no_synth = _make_ctx(synths={}, patches=patch_lib)
    result = await recall_patch(ctx_no_synth, name="bass")
    assert "no definition is loaded" in result


@pytest.mark.asyncio
async def test_recall_patch_midi_not_connected(patch_lib):
    ctx = _make_ctx(patches=patch_lib)
    await save_patch(ctx, name="bass", synth="testsynth", settings={"cutoff": 45})
    result = await recall_patch(ctx, name="bass")
    assert "MIDI not connected" in result


@pytest.mark.asyncio
async def test_recall_patch_skips_out_of_range(patch_lib):
    # Save a patch with a value that's valid for default range (0-127)
    ctx = _make_ctx(patches=patch_lib)
    await save_patch(ctx, name="bass", synth="testsynth", settings={"cutoff": 45})

    # Now create a synth def where cutoff has a narrower range
    narrow_synth = SynthDefinition(
        name="TestSynth",
        manufacturer="TestCo",
        midi_channel=1,
        cc_map={"cutoff": CCParameter(cc=74, value_range=(0, 30))},
    )
    midi = MidiConnection()
    mock_out = MagicMock()
    midi._out = mock_out
    midi._port_name = "Test Port"

    ctx2 = _make_ctx(midi=midi, synths={"testsynth": narrow_synth}, patches=patch_lib)
    result = await recall_patch(ctx2, name="bass")
    assert "Skipped 'cutoff'" in result
    assert "out of range" in result
    assert mock_out.send_message.call_count == 0


@pytest.mark.asyncio
async def test_recall_patch_skips_unknown_params(patch_lib):
    # Save a patch with cutoff and resonance
    ctx = _make_ctx(patches=patch_lib)
    await save_patch(ctx, name="bass", synth="testsynth", settings={"cutoff": 45, "resonance": 80})

    # Now create a synth def that only has cutoff (resonance removed)
    limited_synth = SynthDefinition(
        name="TestSynth",
        manufacturer="TestCo",
        midi_channel=1,
        cc_map={"cutoff": CCParameter(cc=74)},
    )
    midi = MidiConnection()
    mock_out = MagicMock()
    midi._out = mock_out
    midi._port_name = "Test Port"

    ctx2 = _make_ctx(midi=midi, synths={"testsynth": limited_synth}, patches=patch_lib)
    result = await recall_patch(ctx2, name="bass")
    assert "cutoff = 45" in result
    assert "Skipped 'resonance'" in result
    assert mock_out.send_message.call_count == 1


@pytest.mark.asyncio
async def test_list_patches_all(patch_lib):
    ctx = _make_ctx(patches=patch_lib)
    await save_patch(ctx, name="bass", synth="testsynth", settings={"cutoff": 45})
    await save_patch(ctx, name="lead", synth="testsynth", settings={"cutoff": 100, "resonance": 90})
    result = await list_patches(ctx)
    assert "bass" in result
    assert "lead" in result
    assert "Saved patches (2)" in result


@pytest.mark.asyncio
async def test_list_patches_filtered(patch_lib):
    synth2 = SynthDefinition(
        name="OtherSynth",
        manufacturer="OtherCo",
        midi_channel=2,
        cc_map={"volume": CCParameter(cc=7)},
    )
    synths = {
        "testsynth": _make_synth(),
        "othersynth": synth2,
    }
    ctx = _make_ctx(synths=synths, patches=patch_lib)
    await save_patch(ctx, name="bass", synth="testsynth", settings={"cutoff": 45})
    await save_patch(ctx, name="pad", synth="othersynth", settings={"volume": 100})

    result = await list_patches(ctx, synth="testsynth")
    assert "bass" in result
    assert "pad" not in result


@pytest.mark.asyncio
async def test_list_patches_empty(patch_lib):
    ctx = _make_ctx(patches=patch_lib)
    result = await list_patches(ctx)
    assert "No patches saved yet" in result


@pytest.mark.asyncio
async def test_delete_patch_exists(patch_lib):
    ctx = _make_ctx(patches=patch_lib)
    await save_patch(ctx, name="bass", synth="testsynth", settings={"cutoff": 45})
    result = await delete_patch(ctx, name="bass")
    assert "Deleted patch 'bass'" in result


@pytest.mark.asyncio
async def test_delete_patch_not_found(patch_lib):
    ctx = _make_ctx(patches=patch_lib)
    result = await delete_patch(ctx, name="nonexistent")
    assert "No patch found" in result
