from pydantic_ai import RunContext

from patchwork.deps import PatchworkDeps


async def list_midi_ports(ctx: RunContext[PatchworkDeps]) -> str:
    """List available MIDI output ports."""
    ports = ctx.deps.midi.list_ports()
    if not ports:
        return "No MIDI output ports found. Is your MIDI interface connected?"
    lines = [f"{i}: {name}" for i, name in enumerate(ports)]
    return "Available MIDI ports:\n" + "\n".join(lines)


async def send_cc(
    ctx: RunContext[PatchworkDeps],
    synth: str,
    parameter: str,
    value: int,
) -> str:
    """Send a MIDI CC value to a parameter on a synth.

    Args:
        synth: Synth name (e.g. "minitaur", "tb-03")
        parameter: Parameter name from the synth's CC map (e.g. "filter_cutoff")
        value: CC value to send (0-127)
    """
    synth_def = ctx.deps.synths.get(synth.lower())
    if synth_def is None:
        available = ", ".join(ctx.deps.synths.keys())
        return f"Unknown synth '{synth}'. Available: {available}"

    if not ctx.deps.midi.is_connected:
        return "MIDI not connected. Use list_midi_ports to see available ports, then ask me to connect."

    param_key = parameter.lower().replace(" ", "_")
    param = synth_def.cc_map.get(param_key)
    if param is None:
        available = ", ".join(synth_def.cc_map.keys())
        return f"Unknown parameter '{parameter}' for {synth_def.name}. Available: {available}"

    low, high = param.value_range
    if not (low <= value <= high):
        return f"Value {value} out of range for {parameter} ({low}-{high})"

    ctx.deps.midi.send_cc(synth_def.midi_channel, param.cc, value)
    return f"Sent CC {param.cc} = {value} to {synth_def.name} ch.{synth_def.midi_channel} ({parameter})"


async def send_patch(
    ctx: RunContext[PatchworkDeps],
    synth: str,
    settings: dict[str, int],
) -> str:
    """Send multiple CC values at once to set a full patch on a synth.

    Args:
        synth: Synth name (e.g. "minitaur", "tb-03")
        settings: Dict of parameter name to CC value (e.g. {"filter_cutoff": 64, "resonance": 80})
    """
    synth_def = ctx.deps.synths.get(synth.lower())
    if synth_def is None:
        available = ", ".join(ctx.deps.synths.keys())
        return f"Unknown synth '{synth}'. Available: {available}"

    if not ctx.deps.midi.is_connected:
        return "MIDI not connected. Use list_midi_ports to see available ports, then ask me to connect."

    results = []
    for param_name, value in settings.items():
        param_key = param_name.lower().replace(" ", "_")
        param = synth_def.cc_map.get(param_key)
        if param is None:
            results.append(f"  ✗ Unknown parameter '{param_name}'")
            continue
        low, high = param.value_range
        if not (low <= value <= high):
            results.append(f"  ✗ {param_name}: value {value} out of range ({low}-{high})")
            continue
        ctx.deps.midi.send_cc(synth_def.midi_channel, param.cc, value)
        results.append(f"  ✓ {param_name} = {value} (CC {param.cc})")

    return f"Patch sent to {synth_def.name} ch.{synth_def.midi_channel}:\n" + "\n".join(results)


async def list_synths(ctx: RunContext[PatchworkDeps]) -> str:
    """List all loaded synth definitions and their controllable parameters."""
    if not ctx.deps.synths:
        return "No synth definitions loaded. Add YAML files to the synths/ directory."
    lines = []
    for synth in ctx.deps.synths.values():
        params = ", ".join(synth.cc_map.keys())
        lines.append(f"- {synth.manufacturer} {synth.name} (ch.{synth.midi_channel}): {params}")
    return "Loaded synths:\n" + "\n".join(lines)


async def connect_midi(
    ctx: RunContext[PatchworkDeps],
    port_index: int = 0,
) -> str:
    """Connect to a MIDI output port by index. Use list_midi_ports first to see available ports.

    Args:
        port_index: Index of the MIDI port to connect to (default: 0, the first port)
    """
    try:
        port_name = ctx.deps.midi.open(port_index)
        return f"Connected to MIDI port: {port_name}"
    except (RuntimeError, ValueError) as e:
        return str(e)
