from pydantic_ai import RunContext

from patchwork.deps import PatchworkDeps


async def save_patch(
    ctx: RunContext[PatchworkDeps],
    name: str,
    synth: str,
    settings: dict[str, int],
    description: str = "",
) -> str:
    """Save a patch to the library. If a patch with this name already exists, it will be updated.

    Args:
        name: Name for the patch (e.g. "dark-techno-bass")
        synth: Synth name this patch is for (e.g. "minitaur", "tb-03")
        settings: Dict of parameter names to CC values (e.g. {"filter_cutoff": 45, "resonance": 80})
        description: Optional description of the sound
    """
    synth_key = synth.lower()
    synth_def = ctx.deps.synths.get(synth_key)
    if synth_def is None:
        available = ", ".join(ctx.deps.synths.keys())
        return f"Unknown synth '{synth}'. Available: {available}"

    # Reject cross-synth overwrites
    existing = ctx.deps.patches.get(name)
    if existing and existing.synth != synth_key:
        return (
            f"A patch named '{name}' already exists for {existing.synth}. "
            f"Delete it first or choose a different name."
        )

    # Validate parameter names and normalize keys to canonical form (lowercase, underscored)
    normalized_settings: dict[str, int] = {}
    invalid_params = []
    out_of_range = []
    for param_name, value in settings.items():
        param_key = param_name.lower().replace(" ", "_")
        param = synth_def.cc_map.get(param_key)
        if param is None:
            invalid_params.append(param_name)
        else:
            low, high = param.value_range
            if not (low <= value <= high):
                out_of_range.append(f"{param_key}: {value} (valid: {low}-{high})")
            else:
                normalized_settings[param_key] = value
    if invalid_params:
        available = ", ".join(synth_def.cc_map.keys())
        return (
            f"Unknown parameter(s) for {synth_def.name}: {', '.join(invalid_params)}. "
            f"Available: {available}"
        )
    if out_of_range:
        return f"Value(s) out of range for {synth_def.name}: {'; '.join(out_of_range)}"

    patch = ctx.deps.patches.save(
        name=name,
        synth=synth_key,
        settings=normalized_settings,
        description=description or None,
    )
    param_lines = [f"  {k} = {v}" for k, v in patch.settings.items()]
    return (
        f"Saved patch '{patch.name}' for {synth_def.name}:\n"
        + "\n".join(param_lines)
    )


async def load_patch(
    ctx: RunContext[PatchworkDeps],
    name: str,
) -> str:
    """Load a patch from the library and display its settings (does NOT send to hardware).

    Args:
        name: Name of the patch to load
    """
    patch = ctx.deps.patches.get(name)
    if patch is None:
        return f"No patch found with name '{name}'."

    synth_def = ctx.deps.synths.get(patch.synth)
    synth_display = synth_def.name if synth_def else patch.synth

    lines = [f"Patch '{patch.name}' for {synth_display}:"]
    if patch.description:
        lines.append(f"  Description: {patch.description}")
    for param, value in patch.settings.items():
        lines.append(f"  {param} = {value}")
    lines.append(f"  Updated: {patch.updated_at:%Y-%m-%d %H:%M}")
    return "\n".join(lines)


async def recall_patch(
    ctx: RunContext[PatchworkDeps],
    name: str,
) -> str:
    """Load a patch from the library AND send all its CC values to the hardware synth.

    Args:
        name: Name of the patch to recall
    """
    patch = ctx.deps.patches.get(name)
    if patch is None:
        return f"No patch found with name '{name}'."

    synth_def = ctx.deps.synths.get(patch.synth)
    if synth_def is None:
        return (
            f"Patch '{name}' is for synth '{patch.synth}', "
            f"but no definition is loaded for that synth."
        )

    if not ctx.deps.midi.is_connected:
        return (
            "MIDI not connected. Use list_midi_ports to see available ports,"
            " then ask me to connect."
        )

    results = []
    for param_name, value in patch.settings.items():
        param = synth_def.cc_map.get(param_name)
        if param is None:
            results.append(f"  Skipped '{param_name}' (not in current CC map)")
            continue
        low, high = param.value_range
        if not (low <= value <= high):
            results.append(
                f"  Skipped '{param_name}': value {value} out of range ({low}-{high})"
            )
            continue
        ctx.deps.midi.send_cc(synth_def.midi_channel, param.cc, value)
        results.append(f"  {param_name} = {value} (CC {param.cc})")

    return (
        f"Recalled patch '{patch.name}' to {synth_def.name} "
        f"ch.{synth_def.midi_channel}:\n" + "\n".join(results)
    )


async def list_patches(
    ctx: RunContext[PatchworkDeps],
    synth: str | None = None,
) -> str:
    """List saved patches, optionally filtered by synth.

    Args:
        synth: Optional synth name to filter by (e.g. "minitaur"). If omitted, lists all patches.
    """
    patches = ctx.deps.patches.list(synth=synth)
    if not patches:
        if synth:
            return f"No patches saved for '{synth}'."
        return "No patches saved yet."

    lines = []
    for patch in patches:
        synth_def = ctx.deps.synths.get(patch.synth)
        synth_display = synth_def.name if synth_def else patch.synth
        desc = f" — {patch.description}" if patch.description else ""
        param_count = len(patch.settings)
        lines.append(f"  {patch.name} ({synth_display}, {param_count} params){desc}")

    header = f"Saved patches ({len(patches)}):"
    return header + "\n" + "\n".join(lines)


async def delete_patch(
    ctx: RunContext[PatchworkDeps],
    name: str,
) -> str:
    """Delete a patch from the library.

    Args:
        name: Name of the patch to delete
    """
    deleted = ctx.deps.patches.delete(name)
    if deleted:
        return f"Deleted patch '{name}'."
    return f"No patch found with name '{name}'."
