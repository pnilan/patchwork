import asyncio

from dotenv import load_dotenv
from rich.console import Console

from patchwork.agent import agent
from patchwork.deps import PatchworkDeps
from patchwork.midi import MidiConnection
from patchwork.synth_definitions import load_synth_definitions

console = Console()


async def main():
    midi = MidiConnection()
    synths = load_synth_definitions()
    deps = PatchworkDeps(midi=midi, synths=synths)

    console.print("[bold]patchwork[/bold] — synth research agent\n")
    if synths:
        console.print(f"[dim]loaded {len(synths)} synth(s): {', '.join(s.name for s in synths.values())}[/dim]\n")
    else:
        console.print("[dim]no synth definitions found in synths/[/dim]\n")
    message_history = []

    try:
        while True:
            try:
                user_input = console.input("[bold cyan]patch>[/bold cyan] ")
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]goodbye[/dim]")
                break

            if not user_input.strip():
                continue

            if user_input.strip().lower() in ("quit", "exit"):
                console.print("[dim]goodbye[/dim]")
                break

            try:
                async with agent.run_stream(
                    user_input, message_history=message_history, deps=deps
                ) as result:
                    async for chunk in result.stream_text(delta=True):
                        console.print(chunk, end="", markup=False, highlight=False)
                    console.print()  # newline after stream

                message_history = result.all_messages()
            except Exception as e:
                console.print(f"\n[bold red]error:[/bold red] {e}")
    finally:
        midi.close()


def main_cli():
    load_dotenv()
    asyncio.run(main())


if __name__ == "__main__":
    main_cli()
