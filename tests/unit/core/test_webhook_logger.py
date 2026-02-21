import asyncio
import logging
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.webhook_logger import DiscordWebhookHandler


class _MockResponse:
    def __init__(self, status: int):
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _MockSession:
    def __init__(self, statuses: list[int]):
        self._statuses = statuses
        self.closed = False
        self.posts: list[tuple[str, dict]] = []

    def post(self, url, json, timeout):
        self.posts.append((url, json))
        status = self._statuses.pop(0) if self._statuses else 204
        return _MockResponse(status)

    async def close(self):
        self.closed = True


def _make_record(
    *,
    level: int = logging.ERROR,
    msg: str = "test error",
    exc_info=None,
) -> logging.LogRecord:
    return logging.LogRecord(
        name="discord.client",
        level=level,
        pathname="/usr/local/lib/python3.13/site-packages/discord/client.py",
        lineno=777,
        msg=msg,
        args=(),
        exc_info=exc_info,
        func="connect",
    )


class TestDiscordWebhookHandler:
    def test_create_embed_enforces_discord_limits(self):
        handler = DiscordWebhookHandler("https://discord.com/api/webhooks/test")

        try:
            raise RuntimeError("x" * 8_000)
        except RuntimeError:
            exc_info = sys.exc_info()

        record = _make_record(msg=("y" * 10_000), exc_info=exc_info)
        embed = handler._create_embed(record)

        assert len(embed["title"]) <= handler.MAX_TITLE_LENGTH
        assert len(embed["description"]) <= handler.MAX_DESCRIPTION_LENGTH

        traceback_fields = [f for f in embed["fields"] if f["name"] == "Traceback"]
        assert len(traceback_fields) == 1
        assert len(traceback_fields[0]["value"]) <= handler.MAX_FIELD_VALUE_LENGTH

    @pytest.mark.asyncio
    async def test_emit_schedules_send_for_error_logs(self):
        handler = DiscordWebhookHandler("https://discord.com/api/webhooks/test")
        record = _make_record(level=logging.ERROR)

        with patch.object(handler, "_send_webhook", new=AsyncMock()) as mock_send:
            handler.emit(record)
            await asyncio.sleep(0)
            mock_send.assert_awaited_once()

    def test_emit_uses_background_thread_without_running_loop(self):
        handler = DiscordWebhookHandler("https://discord.com/api/webhooks/test")
        record = _make_record(level=logging.ERROR)
        mock_thread = MagicMock()

        with patch("core.webhook_logger.threading.Thread", return_value=mock_thread) as mock_thread_cls:
            handler.emit(record)
            mock_thread_cls.assert_called_once()
            mock_thread.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_emit_ignores_non_error_logs(self):
        handler = DiscordWebhookHandler("https://discord.com/api/webhooks/test")
        record = _make_record(level=logging.INFO)

        with patch.object(handler, "_send_webhook", new=AsyncMock()) as mock_send:
            handler.emit(record)
            await asyncio.sleep(0)
            mock_send.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_send_webhook_falls_back_to_plain_content(self):
        handler = DiscordWebhookHandler("https://discord.com/api/webhooks/test")
        handler.session = _MockSession([400, 204])
        payload = {"embeds": [{"title": "Error Title", "description": "Error body"}]}

        await handler._send_webhook(payload)

        assert isinstance(handler.session, _MockSession)
        assert len(handler.session.posts) == 2
        assert "embeds" in handler.session.posts[0][1]
        assert "content" in handler.session.posts[1][1]
        assert "Error Title" in handler.session.posts[1][1]["content"]
