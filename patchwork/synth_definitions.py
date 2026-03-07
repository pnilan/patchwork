from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator


class CCParameter(BaseModel):
    cc: int = Field(ge=0, le=127)
    value_range: tuple[int, int] = (0, 127)
    notes: str | None = None

    @model_validator(mode="after")
    def check_range_order(self) -> CCParameter:
        low, high = self.value_range
        if low > high:
            raise ValueError(f"value_range low ({low}) must be <= high ({high})")
        return self


class SynthDefinition(BaseModel):
    name: str
    manufacturer: str
    midi_channel: int = Field(ge=1, le=16)
    cc_map: dict[str, CCParameter]


_DEFAULT_SYNTHS_DIR = Path(__file__).resolve().parent.parent / "synths"


def load_synth_definitions(synths_dir: Path = _DEFAULT_SYNTHS_DIR) -> dict[str, SynthDefinition]:
    """Load and validate all synth YAML files from the given directory."""
    definitions: dict[str, SynthDefinition] = {}
    if not synths_dir.exists():
        return definitions
    yaml_files = sorted([*synths_dir.glob("*.yaml"), *synths_dir.glob("*.yml")])
    for yaml_file in yaml_files:
        data = yaml.safe_load(yaml_file.read_text())
        synth = SynthDefinition(**data)
        key = synth.name.lower()
        if key in definitions:
            raise ValueError(
                f"Duplicate synth name '{synth.name}' "
                f"(from {yaml_file.name} and existing definition)"
            )
        definitions[key] = synth
    return definitions
