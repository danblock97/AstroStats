import logging
import traceback
import aiohttp
import asyncio
import os
import base64
from typing import Optional
from datetime import datetime

class DiscordWebhookHandler(logging.Handler):
    """Custom logging handler that sends ERROR and CRITICAL logs to Discord webhook."""

    def __init__(self, webhook_url: str, level: int = logging.ERROR):
        super().__init__(level)
        self.webhook_url = webhook_url
        self.jira_base_url = os.getenv("JIRA_BASE_URL")
        self.jira_project_key = os.getenv("JIRA_PROJECT_KEY")
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

            # Schedule Jira issue creation if configured
            if self.jira_base_url and self.jira_project_key:
                jira_issue = self._create_jira_issue_payload(record)
                asyncio.create_task(self._create_jira_issue(jira_issue))
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

    def _create_jira_issue_payload(self, record: logging.LogRecord) -> dict:
        """Create Jira issue payload from log record."""
        level_name = record.levelname.capitalize()  # "Error" instead of "ERROR"
        module_name = record.name.split('.')[-1] if record.name else "unknown"

        func_name = record.funcName if record.funcName and record.funcName != '<module>' else None
        if func_name:
            summary = f"{level_name} in {func_name}"
        else:
            summary = f"{level_name} in {module_name}"

        description_parts = [
            f"Error Message: {record.getMessage()}",
            f"Location: {record.pathname}:{record.lineno}",
            f"Function: {record.funcName}",
            f"Timestamp (UTC): {datetime.utcnow().isoformat()}Z",
        ]

        traceback_text = None
        if record.exc_info:
            traceback_text = ''.join(traceback.format_exception(*record.exc_info))
            if len(traceback_text) > 3000:
                traceback_text = traceback_text[:3000] + "... (truncated)"

        priority = "Highest" if record.levelno >= logging.CRITICAL else "High"

        return {
            "summary": summary,
            "description_parts": description_parts,
            "traceback": traceback_text,
            "priority": priority,
        }

    def _build_jira_description(self, parts: list[str], traceback_text: Optional[str]) -> dict:
        """Build Jira ADF description document."""
        content = []
        for part in parts:
            content.append({
                "type": "paragraph",
                "content": [{"type": "text", "text": part}]
            })

        if traceback_text:
            content.append({
                "type": "paragraph",
                "content": [{"type": "text", "text": "Traceback:"}]
            })
            content.append({
                "type": "codeBlock",
                "attrs": {"language": "python"},
                "content": [{"type": "text", "text": traceback_text}]
            })

        return {"type": "doc", "version": 1, "content": content}

    async def _create_jira_issue(self, issue_data: dict):
        """Create an issue in Jira via the Jira Cloud API."""
        try:
            jira_email = os.getenv("JIRA_EMAIL")
            jira_api_token = os.getenv("JIRA_API_TOKEN")
            if not jira_email or not jira_api_token:
                return

            async with self._lock:
                if not self.session or self.session.closed:
                    self.session = aiohttp.ClientSession()
                session = self.session

            auth_bytes = f"{jira_email}:{jira_api_token}".encode("utf-8")
            auth_header = base64.b64encode(auth_bytes).decode("utf-8")

            headers = {
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/json"
            }

            description_doc = self._build_jira_description(
                issue_data["description_parts"],
                issue_data["traceback"]
            )

            component_name = os.getenv("JIRA_COMPONENT", "Discord Bot")

            payload = {
                "fields": {
                    "project": {"key": self.jira_project_key},
                    "summary": issue_data["summary"],
                    "description": description_doc,
                    "issuetype": {"name": "Bug"},
                    "priority": {"name": issue_data["priority"]},
                    "components": [{"name": component_name}],
                }
            }

            url = f"{self.jira_base_url.rstrip('/')}/rest/api/3/issue"

            async with session.post(
                url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status not in (200, 201):
                    response_text = await response.text()
                    print(f"[Jira API Error] Status: {response.status}, Response: {response_text}")
                else:
                    print(f"[Jira API] Issue created successfully")
        except Exception as e:
            print(f"[Jira API Exception] {type(e).__name__}: {e}")
