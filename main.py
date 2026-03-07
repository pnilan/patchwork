import asyncio

from dotenv import load_dotenv
from rich.console import Console

from patchwork.agent import agent

console = Console()


async def main():
    load_dotenv()
    console.print("[bold]patchwork[/bold] — synth research agent\n")
    message_history = []

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

        async with agent.run_stream(
            user_input, message_history=message_history
        ) as result:
            async for chunk in result.stream_text(delta=True):
                console.print(chunk, end="")
            console.print()  # newline after stream

        message_history = result.all_messages()


def main_cli():
    asyncio.run(main())


if __name__ == "__main__":
    main_cli()
