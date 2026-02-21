import logging
import traceback
import aiohttp
import asyncio
import threading
from typing import Optional
from datetime import datetime, timezone

class DiscordWebhookHandler(logging.Handler):
    """Logging handler that sends ERROR and CRITICAL logs to a Discord webhook."""

    MAX_TITLE_LENGTH = 256
    MAX_DESCRIPTION_LENGTH = 4096
    MAX_FIELD_NAME_LENGTH = 256
    MAX_FIELD_VALUE_LENGTH = 1024
    TRACEBACK_CODEBLOCK_OVERHEAD = len("```python\n\n```")

    def __init__(self, webhook_url: str, level: int = logging.ERROR):
        super().__init__(level)
        self.webhook_url = webhook_url
        self.session: Optional[aiohttp.ClientSession] = None
        self._lock = threading.Lock()

    @staticmethod
    def _truncate(text: str, limit: int) -> str:
        if not text:
            return ""
        if len(text) <= limit:
            return text
        suffix = "... (truncated)"
        head = max(0, limit - len(suffix))
        return text[:head] + suffix

    def _truncate_field_name(self, name: str) -> str:
        return self._truncate(name, self.MAX_FIELD_NAME_LENGTH)

    def _truncate_field_value(self, value: str) -> str:
        return self._truncate(value, self.MAX_FIELD_VALUE_LENGTH)

    def _format_traceback_field(self, exc_text: str) -> str:
        allowed = max(0, self.MAX_FIELD_VALUE_LENGTH - self.TRACEBACK_CODEBLOCK_OVERHEAD)
        truncated = self._truncate(exc_text, allowed)
        return f"```python\n{truncated}\n```"

    def emit(self, record: logging.LogRecord):
        """Send log record to Discord webhook asynchronously."""
        if record.levelno < logging.ERROR:
            return

        try:
            embed = self._create_embed(record)
            payload = {"embeds": [embed]}
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._send_webhook(payload))
            except RuntimeError:
                # No running loop (e.g. startup/shutdown). Use background thread.
                thread = threading.Thread(
                    target=self._send_webhook_in_thread,
                    args=(payload,),
                    daemon=True,
                )
                thread.start()
        except Exception:
            # Prevent logging errors from causing infinite loops
            self.handleError(record)

    def _create_embed(self, record: logging.LogRecord) -> dict:
        """Create Discord embed from log record."""
        level_name = record.levelname
        color = 0xFF0000 if record.levelno == logging.CRITICAL else 0xFF6B6B
        description = self._truncate(record.getMessage(), self.MAX_DESCRIPTION_LENGTH)

        embed = {
            "title": self._truncate(f"🚨 {level_name}: {record.name}", self.MAX_TITLE_LENGTH),
            "description": description,
            "color": color,
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "fields": []
        }

        # Add exception info if available
        if record.exc_info:
            exc_text = ''.join(traceback.format_exception(*record.exc_info))
            embed["fields"].append({
                "name": self._truncate_field_name("Traceback"),
                "value": self._format_traceback_field(exc_text),
                "inline": False
            })

        # Add file and line info
        if record.pathname:
            embed["fields"].append({
                "name": self._truncate_field_name("Location"),
                "value": self._truncate_field_value(f"`{record.pathname}:{record.lineno}`"),
                "inline": True
            })

        # Add function name if available
        if record.funcName:
            embed["fields"].append({
                "name": self._truncate_field_name("Function"),
                "value": self._truncate_field_value(f"`{record.funcName}`"),
                "inline": True
            })

        return embed

    def _get_session(self) -> aiohttp.ClientSession:
        with self._lock:
            if not self.session or self.session.closed:
                self.session = aiohttp.ClientSession()
            return self.session

    async def _send_webhook(self, payload: dict):
        """Send payload to Discord webhook asynchronously."""
        try:
            session = self._get_session()
            async with session.post(
                self.webhook_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                # Discord webhooks return 204 on success (200 when wait=true).
                # If embed payload is rejected, retry with plain content fallback.
                if response.status not in (200, 204):
                    await self._send_fallback_content(session, payload)
        except Exception:
            # Silently fail to avoid logging loops
            pass

    def _send_webhook_in_thread(self, payload: dict) -> None:
        try:
            asyncio.run(self._send_webhook(payload))
        except Exception:
            return

    async def _send_fallback_content(self, session: aiohttp.ClientSession, payload: dict) -> None:
        try:
            embed = (payload.get("embeds") or [{}])[0]
            title = embed.get("title", "Error")
            description = embed.get("description", "")
            content = self._truncate(f"{title}\n{description}", 1900)
            fallback_payload = {"content": content}
            async with session.post(
                self.webhook_url,
                json=fallback_payload,
                timeout=aiohttp.ClientTimeout(total=5)
            ):
                return
        except Exception:
            return

    async def aclose(self):
        """Clean up the underlying aiohttp session."""
        with self._lock:
            session = self.session
            self.session = None
        if session and not session.closed:
            await session.close()

    def close(self):
        """Close the handler and release resources."""
        try:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.aclose())
            except RuntimeError:
                # Best effort cleanup when no loop is running.
                if self.session and not self.session.closed:
                    asyncio.run(self.session.close())
                self.session = None
        except Exception:
            self.session = None
        finally:
            super().close()
