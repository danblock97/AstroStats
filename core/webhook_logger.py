import logging
import traceback
import aiohttp
import asyncio
import os
from typing import Optional
from datetime import datetime

class DiscordWebhookHandler(logging.Handler):
    """Custom logging handler that sends ERROR and CRITICAL logs to Discord webhook."""

    def __init__(self, webhook_url: str, level: int = logging.ERROR):
        super().__init__(level)
        self.webhook_url = webhook_url
        self.notion_data_source_id = os.getenv("NOTION_TRACKER_ID")
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

            # Schedule Notion task creation if configured
            if self.notion_data_source_id:
                notion_task = self._create_notion_task_payload(record)
                asyncio.create_task(self._create_notion_task(notion_task))
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

    def _create_notion_task_payload(self, record: logging.LogRecord) -> dict:
        """Create Notion task payload from log record."""
        level_name = record.levelname.capitalize()  # "Error" instead of "ERROR"
        module_name = record.name.split('.')[-1] if record.name else "unknown"

        # Build summary (title) - more readable format
        func_name = record.funcName if record.funcName and record.funcName != '<module>' else None
        if func_name:
            summary = f"{level_name} in {func_name}"
        else:
            summary = f"{level_name} in {module_name}"

        # Build description with details
        description_parts = [
            f"**Error Message:** {record.getMessage()}",
            f"**Location:** `{record.pathname}:{record.lineno}`",
            f"**Function:** `{record.funcName}`",
            f"**Timestamp:** {datetime.utcnow().isoformat()}Z",
        ]

        # Add traceback if available
        if record.exc_info:
            exc_text = ''.join(traceback.format_exception(*record.exc_info))
            # Truncate if too long for Notion
            if len(exc_text) > 1500:
                exc_text = exc_text[:1500] + "... (truncated)"
            description_parts.append(f"\n**Traceback:**\n```\n{exc_text}\n```")

        description = "\n".join(description_parts)

        # Map priority based on log level
        priority = "High" if record.levelno >= logging.CRITICAL else "Medium"

        return {
            "summary": summary,
            "description": description,
            "priority": priority,
            "task_type": ["🐞 Bug"],
            "status": "Not started"
        }

    async def _create_notion_task(self, task_data: dict):
        """Create a task in Notion via the Notion API."""
        try:
            async with self._lock:
                if not self.session or self.session.closed:
                    self.session = aiohttp.ClientSession()
                session = self.session

            # Notion API endpoint
            url = "https://api.notion.com/v1/pages"

            # Get Notion API key from environment
            notion_api_key = os.getenv("NOTION_API_KEY")
            if not notion_api_key:
                return

            headers = {
                "Authorization": f"Bearer {notion_api_key}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28"
            }

            # Build the Notion page payload
            payload = {
                "parent": {"database_id": self.notion_data_source_id},
                "properties": {
                    "Summary": {
                        "title": [{"text": {"content": task_data["summary"]}}]
                    },
                    "Description": {
                        "rich_text": [{"text": {"content": task_data["description"][:2000]}}]
                    },
                    "Priority": {
                        "select": {"name": task_data["priority"]}
                    },
                    "Task type": {
                        "multi_select": [{"name": name} for name in task_data["task_type"]]
                    },
                    "Status": {
                        "status": {"name": task_data["status"]}
                    }
                }
            }

            async with session.post(
                url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status not in (200, 201):
                    # Log to console for debugging (not through logger to avoid loops)
                    response_text = await response.text()
                    print(f"[Notion API Error] Status: {response.status}, Response: {response_text}")
                else:
                    print(f"[Notion API] Task created successfully")
        except Exception as e:
            # Log to console for debugging (not through logger to avoid loops)
            print(f"[Notion API Exception] {type(e).__name__}: {e}")
