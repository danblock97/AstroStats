import logging
import traceback
import aiohttp
import asyncio
from typing import Optional
from datetime import datetime

class DiscordWebhookHandler(logging.Handler):
    """Custom logging handler that sends ERROR and CRITICAL logs to Discord webhook."""
    
    def __init__(self, webhook_url: str, level: int = logging.ERROR):
        super().__init__(level)
        self.webhook_url = webhook_url
        self.session: Optional[aiohttp.ClientSession] = None
        self._lock = asyncio.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
    
    def emit(self, record: logging.LogRecord):
        """Send log record to Discord webhook."""
        if record.levelno < logging.ERROR:
            return
        
        try:
            # Get or create event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # No event loop running, skip webhook send
                return
            
            if not loop.is_running():
                # Event loop not running, skip webhook send
                return
            
            # Create embed payload
            embed = self._create_embed(record)
            payload = {"embeds": [embed]}
            
            # Schedule async webhook send
            asyncio.create_task(self._send_webhook(payload))
        except Exception:
            # Prevent logging errors from causing infinite loops
            self.handleError(record)
    
    def _create_embed(self, record: logging.LogRecord) -> dict:
        """Create Discord embed from log record."""
        level_name = record.levelname
        color = 0xFF0000 if record.levelno == logging.CRITICAL else 0xFF6B6B
        
        embed = {
            "title": f"🚨 {level_name}: {record.name}",
            "description": record.getMessage(),
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "fields": []
        }
        
        # Add exception info if available
        if record.exc_info:
            exc_text = ''.join(traceback.format_exception(*record.exc_info))
            # Discord embed field value limit is 1024 chars
            if len(exc_text) > 1024:
                exc_text = exc_text[:1000] + "... (truncated)"
            embed["fields"].append({
                "name": "Traceback",
                "value": f"```python\n{exc_text}\n```",
                "inline": False
            })
        
        # Add file and line info
        if record.pathname:
            embed["fields"].append({
                "name": "Location",
                "value": f"`{record.pathname}:{record.lineno}`",
                "inline": True
            })
        
        # Add function name if available
        if record.funcName:
            embed["fields"].append({
                "name": "Function",
                "value": f"`{record.funcName}`",
                "inline": True
            })
        
        return embed
    
    async def _send_webhook(self, payload: dict):
        """Send payload to Discord webhook asynchronously."""
        try:
            # Ensure session exists
            async with self._lock:
                if not self.session or self.session.closed:
                    self.session = aiohttp.ClientSession()
                session = self.session
            
            # Make request outside lock to avoid blocking
            async with session.post(
                self.webhook_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status not in (200, 204):
                    # Silently fail to avoid logging loops
                    pass
        except Exception:
            # Silently fail to avoid logging loops
            pass
    
    async def close(self):
        """Clean up the session."""
        if self.session:
            await self.session.close()
            self.session = None
