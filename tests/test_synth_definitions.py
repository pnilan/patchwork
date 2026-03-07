from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from patchwork.synth_definitions import (
    CCParameter,
    SynthDefinition,
    load_synth_definitions,
)


def test_cc_parameter_defaults():
    param = CCParameter(cc=22)
    assert param.value_range == (0, 127)
    assert param.notes is None


def test_cc_parameter_validation():
    with pytest.raises(ValidationError):
        CCParameter(cc=-1)
    with pytest.raises(ValidationError):
        CCParameter(cc=128)


def test_cc_parameter_range_order():
    with pytest.raises(ValidationError):
        CCParameter(cc=22, value_range=(127, 0))


def test_synth_definition_valid():
    synth = SynthDefinition(
        name="TestSynth",
        manufacturer="TestCo",
        midi_channel=1,
        cc_map={"cutoff": CCParameter(cc=74)},
    )
    assert synth.name == "TestSynth"
    assert synth.manufacturer == "TestCo"
    assert synth.midi_channel == 1
    assert "cutoff" in synth.cc_map
    assert synth.cc_map["cutoff"].cc == 74


def test_synth_definition_channel_validation():
    with pytest.raises(ValidationError):
        SynthDefinition(
            name="X",
            manufacturer="Y",
            midi_channel=0,
            cc_map={},
        )
    with pytest.raises(ValidationError):
        SynthDefinition(
            name="X",
            manufacturer="Y",
            midi_channel=17,
            cc_map={},
        )


def test_load_synth_definitions(tmp_path):
    data = {
        "name": "TestSynth",
        "manufacturer": "TestCo",
        "midi_channel": 1,
        "cc_map": {
            "cutoff": {"cc": 74},
            "resonance": {"cc": 71},
        },
    }
    yaml_file = tmp_path / "test_synth.yaml"
    yaml_file.write_text(yaml.dump(data))

    result = load_synth_definitions(tmp_path)
    assert "testsynth" in result
    assert result["testsynth"].name == "TestSynth"
    assert result["testsynth"].cc_map["cutoff"].cc == 74


def test_load_synth_definitions_empty_dir(tmp_path):
    result = load_synth_definitions(tmp_path)
    assert result == {}


def test_load_synth_definitions_missing_dir(tmp_path):
    result = load_synth_definitions(tmp_path / "nonexistent")
    assert result == {}


def test_load_synth_definitions_invalid_yaml(tmp_path):
    yaml_file = tmp_path / "bad.yaml"
    yaml_file.write_text("name: Bad\nmanufacturer: X\nmidi_channel: 999\ncc_map: {}")
    with pytest.raises(ValidationError):
        load_synth_definitions(tmp_path)


def test_load_synth_definitions_duplicate_name(tmp_path):
    data = {
        "name": "Dupe",
        "manufacturer": "X",
        "midi_channel": 1,
        "cc_map": {"cutoff": {"cc": 74}},
    }
    (tmp_path / "dupe1.yaml").write_text(yaml.dump(data))
    (tmp_path / "dupe2.yaml").write_text(yaml.dump(data))
    with pytest.raises(ValueError, match="Duplicate synth name"):
        load_synth_definitions(tmp_path)


def test_load_synth_definitions_yml_extension(tmp_path):
    data = {
        "name": "YmlSynth",
        "manufacturer": "Y",
        "midi_channel": 5,
        "cc_map": {"vol": {"cc": 7}},
    }
    yaml_file = tmp_path / "synth.yml"
    yaml_file.write_text(yaml.dump(data))

    result = load_synth_definitions(tmp_path)
    assert "ymlsynth" in result
