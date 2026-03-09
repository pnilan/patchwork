from dataclasses import dataclass

from patchwork.midi import MidiConnection
from patchwork.patch_library import PatchLibrary
from patchwork.synth_definitions import SynthDefinition


@dataclass
class PatchworkDeps:
    midi: MidiConnection
    synths: dict[str, SynthDefinition]
    patches: PatchLibrary
