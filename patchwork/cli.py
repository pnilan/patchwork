import argparse
import asyncio
import json
import logging
from collections.abc import AsyncIterable

from dotenv import load_dotenv
from pydantic_ai import FunctionToolCallEvent, RunContext
from rich.console import Console

from patchwork.agent import agent
from patchwork.deps import PatchworkDeps
from patchwork.logging_config import setup_logging
from patchwork.midi import MidiConnection
from patchwork.patch_library import PatchLibrary
from patchwork.synth_definitions import load_synth_definitions

console = Console()
stderr_console = Console(stderr=True)


def _make_event_handler(verbose: bool, logger: logging.Logger):
    """Return an event_stream_handler that logs tool calls."""

    async def handle_events(ctx: RunContext[PatchworkDeps], events: AsyncIterable) -> None:
        async for event in events:
            if isinstance(event, FunctionToolCallEvent):
                tool_name = event.part.tool_name
                stderr_console.print(f"[dim]\U0001f6e0\ufe0f tool call: {tool_name}[/dim]")

                if verbose:
                    try:
                        args = event.part.args_as_dict()
                    except Exception:
                        args = event.part.args
                    logger.debug("tool args: %s %s", tool_name, json.dumps(args, default=str))

    return handle_events


async def main(verbose: bool = False):
    logger = setup_logging(verbose=verbose)
    midi = MidiConnection()
    synths = load_synth_definitions()

    with PatchLibrary() as patches:
        deps = PatchworkDeps(midi=midi, synths=synths, patches=patches)

        console.print("[bold]patchwork[/bold] — synth research agent\n")
        if synths:
            synth_names = ", ".join(s.name for s in synths.values())
            console.print(f"[dim]loaded {len(synths)} synth(s): {synth_names}[/dim]\n")
        else:
            console.print("[dim]no synth definitions found in synths/[/dim]\n")
        message_history = []

        event_handler = _make_event_handler(verbose, logger)

        try:
            while True:
                try:
                    user_input = console.input("[bold cyan]patch>[/bold cyan] ")
                except KeyboardInterrupt, EOFError:
                    console.print("\n[dim]goodbye[/dim]")
                    break

                if not user_input.strip():
                    continue

                if user_input.strip().lower() in ("quit", "exit"):
                    console.print("[dim]goodbye[/dim]")
                    break

                try:
                    async with agent.run_stream(
                        user_input,
                        message_history=message_history,
                        deps=deps,
                        event_stream_handler=event_handler,
                    ) as result:
                        async for chunk in result.stream_text(delta=True):
                            console.print(chunk, end="", markup=False, highlight=False)
                        console.print()  # newline after stream

                    message_history = result.all_messages()
                except Exception as e:
                    logger.exception("Error during agent run")
                    console.print(f"\n[bold red]error:[/bold red] {e}")
        finally:
            midi.close()


def main_cli():
    load_dotenv()

    parser = argparse.ArgumentParser(description="patchwork — synth research agent")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable verbose logging")
    args = parser.parse_args()

    asyncio.run(main(verbose=args.verbose))


if __name__ == "__main__":
    main_cli()
