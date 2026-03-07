import os

import pytest
from pydantic_ai import Agent

from patchwork.agent import SYSTEM_PROMPT, agent


def test_agent_exists():
    assert isinstance(agent, Agent)


def test_agent_model():
    assert agent.model == "anthropic:claude-sonnet-4-6"


def test_system_prompt_contains_synth_context():
    for synth in ["Minitaur", "TB-03", "Minilogue XD", "Roland S-1", "Blackbox", "Digitakt", "Minibrute 2S"]:
        assert synth in SYSTEM_PROMPT, f"System prompt missing {synth}"


def test_system_prompt_mentions_midi():
    assert "MIDI CC" in SYSTEM_PROMPT


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"), reason="no API key"
)
@pytest.mark.asyncio
async def test_agent_responds():
    result = await agent.run("What synths do I have?")
    assert isinstance(result.output, str)
    assert len(result.output) > 0
