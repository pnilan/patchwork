from pathlib import Path

import yaml

from patchwork.synth_definitions import SynthDefinition

SYNTHS_DIR = Path(__file__).parent.parent / "synths"


def test_minitaur_yaml_loads():
    data = yaml.safe_load((SYNTHS_DIR / "moog_minitaur.yaml").read_text())
    synth = SynthDefinition(**data)
    assert synth.name == "Minitaur"
    assert synth.manufacturer == "Moog"
    assert synth.midi_channel == 16
    assert "filter_cutoff" in synth.cc_map
    assert synth.cc_map["filter_cutoff"].cc == 19


def test_tb03_yaml_loads():
    data = yaml.safe_load((SYNTHS_DIR / "roland_tb03.yaml").read_text())
    synth = SynthDefinition(**data)
    assert synth.name == "TB-03"
    assert synth.manufacturer == "Roland"
    assert synth.midi_channel == 14
    assert "cutoff" in synth.cc_map
    assert synth.cc_map["cutoff"].cc == 74


def test_s1_yaml_loads():
    data = yaml.safe_load((SYNTHS_DIR / "roland_s1.yaml").read_text())
    synth = SynthDefinition(**data)
    assert synth.name == "S-1"
    assert synth.manufacturer == "Roland"
    assert synth.midi_channel == 1
    assert "filter_cutoff" in synth.cc_map
    assert synth.cc_map["filter_cutoff"].cc == 74


def test_all_synth_yamls_valid():
    yaml_files = list(SYNTHS_DIR.glob("*.yaml")) + list(SYNTHS_DIR.glob("*.yml"))
    assert len(yaml_files) > 0, "No synth YAML files found"
    for yaml_file in yaml_files:
        data = yaml.safe_load(yaml_file.read_text())
        synth = SynthDefinition(**data)
        assert synth.name
        assert synth.manufacturer
        assert len(synth.cc_map) > 0
