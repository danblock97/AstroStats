import os
import datetime
import aiohttp
import discord
import logging

logger = logging.getLogger(__name__)

# Configuration for each Jira project.
JIRA_PROJECTS = {
    "ClutchGG.LOL": {
        "base_url": os.getenv("JIRA_BASE_URL"),
        "email": os.getenv("JIRA_EMAIL"),
        "token": os.getenv("JIRA_API_TOKEN"),
        "jql": 'project = "ClutchGG.LOL" AND type = Bug',
        "fields": "key,summary,description,issuetype,attachment,status,priority,components,reporter,project",
        # For ClutchGG.LOL we show the clutchgg image (via attachment).
        "thumbnail": "attachment://clutchgg.png",
        "attachment_file": "images/clutchgg.png",
    },
    "AstroStats Bot": {
        "base_url": os.getenv("JIRA_BASE_URL"),
        "email": os.getenv("JIRA_EMAIL"),
        "token": os.getenv("JIRA_API_TOKEN"),
        "jql": 'project = "AstroStats Bot" AND type = Bug',
        "fields": "key,summary,description,issuetype,attachment,status,priority,components,reporter,project",
        # For AstroStats (and Diverse Diaries) we show AstroStats.png.
        "thumbnail": "https://astrostats.vercel.app/images/astrostats.png",
        "attachment_file": None,
    },
    "Diverse Diaries": {
        "base_url": os.getenv("JIRA_BASE_URL"),
        "email": os.getenv("JIRA_EMAIL"),
        "token": os.getenv("JIRA_API_TOKEN"),
        "jql": 'project = "Diverse Diaries" AND type = Bug',
        "fields": "key,summary,description,issuetype,attachment,status,priority,components,reporter,project",
        "thumbnail": "attachment://diversediaries.png",
        "attachment_file": "images/diversediaries.png",
    },
}


def extract_text_from_adf(node):
    """Recursively extracts plain text from an Atlassian Document Format (ADF) node."""
    if isinstance(node, dict):
        if node.get("type") == "text":
            return node.get("text", "")
        elif "content" in node:
            return "".join(extract_text_from_adf(child) for child in node["content"])
        else:
            return ""
    elif isinstance(node, list):
        return "".join(extract_text_from_adf(child) for child in node)
    return str(node)


def convert_description(desc):
    """Converts a Jira description (ADF or plain text) to a plain string."""
    if isinstance(desc, dict):
        return extract_text_from_adf(desc)
    return str(desc)


def format_attachments(attachments):
    """Formats attachment data into a string with clickable links."""
    lines = []
    for att in attachments:
        filename = att.get("filename")
        content_url = att.get("content")
        if filename and content_url:
            lines.append(f"[{filename}]({content_url})")
    return "\n".join(lines)


def build_embed(issue, project_config):
    """Builds the Discord embed from a Jira issue using the project's configuration."""
    issue_key = issue.get("key")
    fields_data = issue.get("fields", {})
    summary = fields_data.get("summary", "No summary provided")
    raw_desc = fields_data.get("description", "No description provided")
    description = convert_description(raw_desc)
    status = fields_data.get("status", {}).get("name", "Unknown")
    priority = fields_data.get("priority", {}).get("name") if fields_data.get("priority") else None

    # Get project info from the issue (or use a fallback).
    project_name = fields_data.get("project", {}).get("name", "Unknown Project")
    reporter = fields_data.get("reporter", {})
    reporter_name = reporter.get("displayName", "Unknown")
    reporter_avatar = reporter.get("avatarUrls", {}).get("48x48", "")
    attachments = fields_data.get("attachment", [])
    att_text = format_attachments(attachments)

    # Use the thumbnail and attachment file from the project configuration.
    thumbnail_url = project_config.get("thumbnail", "https://astrostats.vercel.app/images/default.png")
    attachment_file = None
    if project_config.get("attachment_file"):
        attachment_file = discord.File(project_config["attachment_file"], filename="clutchgg.png")

    embed = discord.Embed(
        title=f"{issue_key}: {summary}",
        description=description,
        url=f"{project_config['base_url']}/browse/{issue_key}",
        color=0xff0000,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.set_author(name=f"{reporter_name} raised a new Bug", icon_url=reporter_avatar)
    embed.add_field(name="Status", value=status, inline=True)
    if priority:
        embed.add_field(name="Priority", value=priority, inline=True)
    embed.add_field(name="Project", value=project_name, inline=True)
    if att_text:
        embed.add_field(name="Attachments", value=att_text[:1024], inline=False)
    embed.set_thumbnail(url=thumbnail_url)
    embed.set_footer(text=project_name)

    # Create a snapshot for change detection.
    snapshot = {
        "summary": summary,
        "description": description,
        "status": status,
        "priority": priority,
        "project_name": project_name,
        "att_text": att_text,
        "reporter_name": reporter_name,
        "reporter_avatar": reporter_avatar,
    }
    return embed, snapshot, attachment_file


async def poll_jira_project(project_config):
    """Polls a single Jira project based on the given configuration."""
    auth = aiohttp.BasicAuth(project_config["email"], project_config["token"])
    jira_api_url = f"{project_config['base_url']}/rest/api/3/search"
    params = {
        "jql": project_config["jql"],
        "fields": project_config["fields"]
    }
    async with aiohttp.ClientSession(auth=auth) as session:
        async with session.get(jira_api_url, params=params) as response:
            if response.status != 200:
                logger.error(f"Failed to poll Jira for {project_config['base_url']}: HTTP {response.status}")
                return []
            data = await response.json()
            return data.get("issues", [])
