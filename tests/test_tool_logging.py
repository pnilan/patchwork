import logging
from unittest.mock import MagicMock

import pytest

from patchwork.cli import _make_event_handler


def _make_mock_tool_call_event(tool_name: str, args: dict | None = None):
    """Create a mock FunctionToolCallEvent."""
    from pydantic_ai import FunctionToolCallEvent
    from pydantic_ai.messages import ToolCallPart

    part = ToolCallPart(tool_name=tool_name, args=args or {})
    return FunctionToolCallEvent(part=part)


async def _to_async_iterable(items):
    for item in items:
        yield item


@pytest.fixture
def logger():
    log = logging.getLogger("patchwork.test_tool_logging")
    log.handlers.clear()
    log.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    log.addHandler(handler)
    return log


class TestToolCallEventHandler:
    @pytest.mark.asyncio
    async def test_logs_tool_name(self, logger, caplog):
        handler = _make_event_handler(verbose=False, logger=logger)
        event = _make_mock_tool_call_event("send_cc")
        ctx = MagicMock()

        with caplog.at_level(logging.INFO, logger=logger.name):
            await handler(ctx, _to_async_iterable([event]))

        assert any("send_cc" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_verbose_logs_args(self, logger, caplog):
        handler = _make_event_handler(verbose=True, logger=logger)
        args = {"synth_id": "minitaur", "param": "cutoff", "value": 64}
        event = _make_mock_tool_call_event("send_cc", args)
        ctx = MagicMock()

        with caplog.at_level(logging.DEBUG, logger=logger.name):
            await handler(ctx, _to_async_iterable([event]))

        debug_msgs = [r.message for r in caplog.records if r.levelno == logging.DEBUG]
        assert any("minitaur" in msg for msg in debug_msgs)

    @pytest.mark.asyncio
    async def test_ignores_non_tool_events(self, logger, caplog):
        handler = _make_event_handler(verbose=False, logger=logger)
        ctx = MagicMock()

        # A non-FunctionToolCallEvent object
        other_event = MagicMock()
        other_event.event_kind = "part_start"

        with caplog.at_level(logging.INFO, logger=logger.name):
            await handler(ctx, _to_async_iterable([other_event]))

        tool_records = [r for r in caplog.records if "tool call" in r.message]
        assert len(tool_records) == 0

    @pytest.mark.asyncio
    async def test_handles_multiple_events(self, logger, caplog):
        handler = _make_event_handler(verbose=False, logger=logger)
        events = [
            _make_mock_tool_call_event("list_synths"),
            _make_mock_tool_call_event("send_cc"),
        ]
        ctx = MagicMock()

        with caplog.at_level(logging.INFO, logger=logger.name):
            await handler(ctx, _to_async_iterable(events))

        tool_records = [r for r in caplog.records if "tool call" in r.message]
        assert len(tool_records) == 2

    @pytest.mark.asyncio
    async def test_non_verbose_does_not_print_tool_indicator(self, logger, capsys):
        handler = _make_event_handler(verbose=False, logger=logger)
        event = _make_mock_tool_call_event("send_cc")
        ctx = MagicMock()

        await handler(ctx, _to_async_iterable([event]))

        captured = capsys.readouterr()
        assert "⚙" not in captured.out
