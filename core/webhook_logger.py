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
        self.notion_api_token = os.getenv("NOTION_API_TOKEN")
        self.notion_database_id = os.getenv("NOTION_DATABASE_ID")
        self.notion_api_version = os.getenv("NOTION_API_VERSION", "2025-09-03")
        self.session: Optional[aiohttp.ClientSession] = None
        self._lock = asyncio.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._notion_schema_lock = asyncio.Lock()
        self._notion_parent: Optional[dict] = None
        self._notion_properties: Optional[dict] = None
    
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

            # Schedule Notion issue creation if configured
            if self.notion_api_token and self.notion_database_id:
                asyncio.create_task(self._create_notion_issue(record))
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

    def _create_issue_summary(self, record: logging.LogRecord) -> str:
        """Create a concise issue title from the log record."""
        level_name = record.levelname.capitalize()
        module_name = record.name.split('.')[-1] if record.name else "unknown"

        func_name = record.funcName if record.funcName and record.funcName != '<module>' else None
        if func_name:
            return f"{level_name} in {func_name}"
        return f"{level_name} in {module_name}"

    def _notion_text(self, content: str) -> list[dict]:
        return [{"type": "text", "text": {"content": content}}]

    def _truncate(self, text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return text[: max(0, limit - 15)] + "... (truncated)"

    def _priority_for_record(self, record: logging.LogRecord) -> str:
        return "High" if record.levelno >= logging.CRITICAL else "Medium"

    def _extract_traceback(self, record: logging.LogRecord) -> Optional[str]:
        if not record.exc_info:
            return None
        traceback_text = ''.join(traceback.format_exception(*record.exc_info))
        return self._truncate(traceback_text, 3000)

    def _pick_option(self, prop: dict, desired: str) -> Optional[str]:
        options: list[dict] = []
        prop_type = prop.get("type")
        if prop_type == "select":
            options = prop.get("select", {}).get("options", [])
        elif prop_type == "multi_select":
            options = prop.get("multi_select", {}).get("options", [])
        elif prop_type == "status":
            options = prop.get("status", {}).get("options", [])
        if not desired or not options:
            return None
        desired_lower = desired.lower()
        for option in options:
            name = option.get("name", "")
            if name.lower() == desired_lower:
                return name
        return None

    def _pick_options(self, prop: dict, desired_list: list[str]) -> list[str]:
        prop_type = prop.get("type")
        if prop_type != "multi_select":
            return []
        options = prop.get("multi_select", {}).get("options", [])
        if not options:
            return []
        desired_lookup = {item.lower(): item for item in desired_list if item}
        selected = []
        for option in options:
            name = option.get("name", "")
            if name.lower() in desired_lookup:
                selected.append(name)
        return selected

    def _build_notion_properties(self, schema: dict, record: logging.LogRecord) -> dict:
        summary = self._create_issue_summary(record)
        message = record.getMessage()
        level_name = record.levelname.capitalize()
        module_name = record.name.split('.')[-1] if record.name else "unknown"
        func_name = record.funcName if record.funcName and record.funcName != '<module>' else None
        timestamp = datetime.utcfromtimestamp(record.created).isoformat() + "Z"
        location = f"{record.pathname}:{record.lineno}" if record.pathname else None
        traceback_text = self._extract_traceback(record)

        details_lines = [
            f"Message: {message}",
            f"Level: {record.levelname}",
            f"Logger: {record.name}",
            f"Location: {location}" if location else "Location: unknown",
            f"Function: {func_name}" if func_name else "Function: unknown",
            f"Timestamp (UTC): {timestamp}",
        ]
        details_text = "\n".join(details_lines)

        properties: dict = {}
        for prop_name, prop in schema.items():
            prop_type = prop.get("type")
            name_lower = prop_name.lower()

            if prop_type == "title":
                properties[prop_name] = {
                    "title": self._notion_text(self._truncate(summary, 200))
                }
                continue

            if prop_type == "rich_text":
                text_value: Optional[str] = None
                if "message" in name_lower or "error" in name_lower:
                    text_value = message
                elif "detail" in name_lower or "description" in name_lower:
                    text_value = details_text
                elif "traceback" in name_lower or "stack" in name_lower:
                    text_value = traceback_text
                elif "location" in name_lower or "file" in name_lower or "path" in name_lower:
                    text_value = location
                elif "function" in name_lower:
                    text_value = func_name
                elif "module" in name_lower or "logger" in name_lower:
                    text_value = record.name
                elif "level" in name_lower or "severity" in name_lower:
                    text_value = record.levelname
                elif "time" in name_lower or "date" in name_lower:
                    text_value = timestamp
                elif "summary" in name_lower:
                    text_value = summary

                if text_value:
                    properties[prop_name] = {
                        "rich_text": self._notion_text(self._truncate(text_value, 1800))
                    }
                continue

            if prop_type in {"select", "status"}:
                desired: Optional[str] = None
                if "status" in name_lower:
                    desired = "Backlog"
                elif "priority" in name_lower or "prio" in name_lower:
                    desired = self._priority_for_record(record)
                elif "severity" in name_lower or "level" in name_lower:
                    desired = level_name
                elif "type" in name_lower:
                    desired = "Error"

                selected = self._pick_option(prop, desired) if desired else None
                if selected:
                    properties[prop_name] = {prop_type: {"name": selected}}
                continue

            if prop_type == "multi_select":
                desired_list: list[str] = []
                if "tag" in name_lower or "label" in name_lower:
                    desired_list = [level_name, module_name]
                elif "component" in name_lower or "service" in name_lower:
                    desired_list = [module_name]

                selected = self._pick_options(prop, desired_list)
                if selected:
                    properties[prop_name] = {
                        "multi_select": [{"name": name} for name in selected]
                    }
                continue

            if prop_type == "date":
                if "time" in name_lower or "date" in name_lower or "created" in name_lower:
                    properties[prop_name] = {"date": {"start": timestamp}}
                continue

            if prop_type == "number":
                if "line" in name_lower and record.lineno:
                    properties[prop_name] = {"number": record.lineno}
                continue

            if prop_type == "checkbox":
                if "urgent" in name_lower or "critical" in name_lower:
                    properties[prop_name] = {
                        "checkbox": record.levelno >= logging.CRITICAL
                    }
                elif "resolved" in name_lower or "fixed" in name_lower:
                    properties[prop_name] = {"checkbox": False}
                continue

        return properties

    def _build_notion_children(self, record: logging.LogRecord) -> list[dict]:
        message = record.getMessage()
        level_name = record.levelname
        timestamp = datetime.utcfromtimestamp(record.created).isoformat() + "Z"
        location = f"{record.pathname}:{record.lineno}" if record.pathname else None
        func_name = record.funcName if record.funcName and record.funcName != '<module>' else None
        traceback_text = self._extract_traceback(record)

        blocks: list[dict] = []

        def add_paragraph(label: str, value: Optional[str]):
            if not value:
                return
            text = f"{label}: {value}"
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": self._notion_text(self._truncate(text, 2000))
                }
            })

        add_paragraph("Message", message)
        add_paragraph("Level", level_name)
        add_paragraph("Timestamp (UTC)", timestamp)
        add_paragraph("Location", location)
        add_paragraph("Function", func_name)
        add_paragraph("Logger", record.name)

        if traceback_text:
            blocks.append({
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": self._notion_text(self._truncate(traceback_text, 2000)),
                    "language": "python"
                }
            })

        return blocks

    async def _get_session(self) -> aiohttp.ClientSession:
        async with self._lock:
            if not self.session or self.session.closed:
                self.session = aiohttp.ClientSession()
            return self.session

    def _notion_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.notion_api_token}",
            "Notion-Version": self.notion_api_version,
            "Content-Type": "application/json",
        }

    async def _load_notion_schema(self) -> None:
        if self._notion_parent and self._notion_properties:
            return

        async with self._notion_schema_lock:
            if self._notion_parent and self._notion_properties:
                return

            if not self.notion_api_token or not self.notion_database_id:
                return

            session = await self._get_session()
            headers = self._notion_headers()

            db_url = f"https://api.notion.com/v1/databases/{self.notion_database_id}"
            async with session.get(
                db_url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    response_text = await response.text()
                    print(f"[Notion API Error] Database fetch failed: {response.status} {response_text}")
                    return
                database_data = await response.json()

            data_sources = database_data.get("data_sources")
            if data_sources:
                data_source_id = data_sources[0].get("id")
                if not data_source_id:
                    return
                self._notion_parent = {
                    "type": "data_source_id",
                    "data_source_id": data_source_id
                }

                ds_url = f"https://api.notion.com/v1/data_sources/{data_source_id}"
                async with session.get(
                    ds_url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        response_text = await response.text()
                        print(f"[Notion API Error] Data source fetch failed: {response.status} {response_text}")
                        return
                    data_source_data = await response.json()
                self._notion_properties = data_source_data.get("properties", {})
                return

            legacy_properties = database_data.get("properties")
            if legacy_properties:
                self._notion_parent = {
                    "type": "database_id",
                    "database_id": self.notion_database_id
                }
                self._notion_properties = legacy_properties

    async def _create_notion_issue(self, record: logging.LogRecord) -> None:
        """Create an issue in Notion via the Notion API."""
        try:
            if not self.notion_api_token or not self.notion_database_id:
                return

            await self._load_notion_schema()
            if not self._notion_parent or not self._notion_properties:
                return

            properties = self._build_notion_properties(self._notion_properties, record)
            if not properties:
                return

            payload = {
                "parent": self._notion_parent,
                "properties": properties,
            }

            children = self._build_notion_children(record)
            if children:
                payload["children"] = children

            session = await self._get_session()
            headers = self._notion_headers()

            async with session.post(
                "https://api.notion.com/v1/pages",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status not in (200, 201):
                    response_text = await response.text()
                    print(f"[Notion API Error] Status: {response.status}, Response: {response_text}")
                else:
                    print("[Notion API] Issue created successfully")
        except Exception as e:
            print(f"[Notion API Exception] {type(e).__name__}: {e}")
