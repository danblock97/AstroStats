import os
import logging
import discord
from discord.ext import commands, tasks
import aiohttp
import datetime
from dotenv import load_dotenv

from commands import (
    apex, league, fortnite, horoscope, help,
    review, tft, kick, servers, pet_commands, show_update, squib_game_commands
)
from commands.league import fetch_application_emojis

load_dotenv()
logger = logging.getLogger('discord.gateway')
logger.setLevel(logging.ERROR)

# Discord channel where Jira bug notifications are posted.
DISCORD_CHANNEL_ID = int(os.getenv('JIRA_CHANNEL_ID'))

blacklisted_guilds = set()
if os.getenv('BLACKLISTED_GUILDS'):
    blacklisted_guilds = set(map(int, os.getenv('BLACKLISTED_GUILDS', '').split(',')))

intents = discord.Intents.default()
client = commands.Bot(command_prefix="/", intents=intents)

emojis = {}

processed_issues = {}

# Jira API details.
JIRA_API_URL = f"{os.getenv('JIRA_BASE_URL')}/rest/api/3/search"
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
# Using a JQL that returns all bugs in the project regardless of status.
JIRA_JQL = 'project = "Operational Support" AND type = Bug'
# Request additional fields.
JIRA_FIELDS = "key,summary,description,issuetype,attachment,status,priority,components,reporter,project"


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
    """Converts the Jira description (ADF or plain text) to a plain string."""
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


def build_embed(issue):
    issue_key = issue.get("key")
    fields_data = issue.get("fields", {})
    summary = fields_data.get("summary", "No summary provided")
    raw_desc = fields_data.get("description", "No description provided")
    description = convert_description(raw_desc)
    status = fields_data.get("status", {}).get("name", "Unknown")
    priority = fields_data.get("priority", {}).get("name") if fields_data.get("priority") else None

    # Components as a list of dicts.
    components = fields_data.get("components", [])
    components_text = ", ".join(comp.get("name", "") for comp in components) if components else None

    reporter = fields_data.get("reporter", {})
    reporter_name = reporter.get("displayName", "Unknown")
    reporter_avatar = reporter.get("avatarUrls", {}).get("48x48", "")
    project_name = fields_data.get("project", {}).get("name", "Unknown Project")
    attachments = fields_data.get("attachment", [])
    att_text = format_attachments(attachments)

    # Determine thumbnail.
    attachment_file = None
    thumbnail_url = "https://astrostats.vercel.app/images/default.png"
    for comp in components:
        comp_name = comp.get("name", "")
        if comp_name == "AstroStats":
            thumbnail_url = "https://astrostats.vercel.app/images/astrostats.png"
            break
        elif comp_name == "ClutchGG.LOL":
            thumbnail_url = "attachment://clutchgg.png"
            attachment_file = discord.File("images/clutchgg.png", filename="clutchgg.png")

    embed = discord.Embed(
        title=f"{issue_key}: {summary}",
        description=description,
        url=f"https://danblock97.atlassian.net/browse/{issue_key}",
        color=0xff0000,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.set_author(name=f"{reporter_name} raised a new Bug", icon_url=reporter_avatar)
    embed.add_field(name="Status", value=status, inline=True)
    if priority:
        embed.add_field(name="Priority", value=priority, inline=True)
    if components_text:
        embed.add_field(name="Component(s)", value=components_text, inline=True)
    if att_text:
        embed.add_field(name="Attachments", value=att_text[:1024], inline=False)

    embed.set_thumbnail(url=thumbnail_url)
    embed.set_footer(text=f"{project_name}")

    # Create a snapshot for change detection.
    snapshot = {
        "summary": summary,
        "description": description,
        "status": status,
        "priority": priority,
        "components_text": components_text,
        "att_text": att_text,
        "project_name": project_name,
        "reporter_name": reporter_name,
        "reporter_avatar": reporter_avatar,
    }
    return embed, snapshot, attachment_file


async def setup_commands():
    await apex.setup(client)
    await league.setup(client)
    await fortnite.setup(client)
    await horoscope.setup(client)
    await tft.setup(client)
    await help.setup(client)
    await review.setup(client)
    await pet_commands.setup(client)
    await show_update.setup(client)
    await kick.setup(client)
    await servers.setup(client)
    await squib_game_commands.setup(client)


@tasks.loop(minutes=1)
async def poll_jira():
    global processed_issues
    auth = aiohttp.BasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
    params = {
        "jql": JIRA_JQL,
        "fields": JIRA_FIELDS
    }
    async with aiohttp.ClientSession(auth=auth) as session:
        async with session.get(JIRA_API_URL, params=params) as response:
            if response.status != 200:
                print(f"Failed to poll Jira: HTTP {response.status}")
                return
            data = await response.json()
            issues = data.get("issues", [])
            channel = client.get_channel(DISCORD_CHANNEL_ID)
            if channel is None:
                channel = await client.fetch_channel(DISCORD_CHANNEL_ID)

            for issue in issues:
                issue_key = issue.get("key")
                new_embed, new_snapshot, attachment_file = build_embed(issue)
                # Check if the issue status is Done
                if new_snapshot.get("status") == "Done":
                    # If a message was previously sent, delete it
                    if issue_key in processed_issues:
                        try:
                            msg = await channel.fetch_message(processed_issues[issue_key]["message_id"])
                            await msg.delete()
                            del processed_issues[issue_key]
                            print(f"Deleted message for {issue_key} as status is Done.")
                        except Exception as e:
                            print(f"Failed to delete message for {issue_key}: {e}")
                    continue  # Skip sending or updating the embed if done

                if issue_key not in processed_issues:
                    try:
                        if attachment_file is not None:
                            msg = await channel.send(embed=new_embed, file=attachment_file)
                        else:
                            msg = await channel.send(embed=new_embed)
                        processed_issues[issue_key] = {
                            "message_id": msg.id,
                            "snapshot": new_snapshot
                        }
                    except Exception as e:
                        print(f"Failed to send embed for {issue_key}: {e}")
                else:
                    stored = processed_issues[issue_key]["snapshot"]
                    if any(new_snapshot.get(k) != stored.get(k) for k in
                           ["summary", "description", "status", "priority", "components_text", "att_text"]):
                        try:
                            msg = await channel.fetch_message(processed_issues[issue_key]["message_id"])
                            await msg.edit(embed=new_embed)
                            processed_issues[issue_key]["snapshot"] = new_snapshot
                        except Exception as e:
                            print(f"Failed to update embed for {issue_key}: {e}")


@client.event
async def on_ready():
    print(f"{client.user} connected to Discord.")
    try:
        await client.wait_until_ready()
        await setup_commands()
        await client.tree.sync()
        print("Commands synced.")
        global emojis
        emoji_data = await fetch_application_emojis()
        if emoji_data:
            for e in emoji_data:
                if isinstance(e, dict) and 'name' in e and 'id' in e:
                    emojis[e['name']] = f"<:{e['name']}:{e['id']}>"
                else:
                    logging.error(f"Invalid emoji format: {e}")
        print("Bot is ready.")
    except Exception as e:
        print(f"Error in on_ready: {e}")
    poll_jira.start()
    update_presence.start()


@tasks.loop(hours=1)
async def update_presence():
    guild_count = len(client.guilds)
    presence = discord.Game(name=f"/help | {guild_count} servers")
    await client.change_presence(activity=presence)


@client.event
async def on_command_error(ctx: commands.Context, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Missing required arguments.")
    else:
        print(f"Unhandled command error: {error}")


@client.event
async def on_guild_join(guild: discord.Guild):
    if guild.id in blacklisted_guilds:
        await guild.leave()
        print(f"Left blacklisted guild: {guild.name} ({guild.id})")
        return

    embed = discord.Embed(
        title=guild.name,
        description="Thank you for using AstroStats!",
        color=discord.Color.blue()
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    embed.add_field(
        name="\u200b",
        value=(
            "AstroStats helps you keep track of your gaming stats for titles like Apex, "
            "Fortnite, League of Legends, and TFT."
        ),
        inline=False
    )
    embed.add_field(
        name="Important Commands",
        value="/help - Lists all commands & support\n/review - Leave a review on Top.gg",
        inline=False
    )
    embed.add_field(
        name="Links",
        value=(
            "[Documentation](https://astrostats.vercel.app)\n"
            "[Support Server](https://discord.com/invite/BeszQxTn9D)\n"
            "[Support Us ❤️](https://buymeacoffee.com/danblock97)"
        ),
        inline=False
    )

    channel = guild.system_channel
    if channel is None or not channel.permissions_for(guild.me).send_messages:
        for ch in guild.text_channels:
            if ch.permissions_for(guild.me).send_messages:
                channel = ch
                break
        else:
            print(f"No sendable channel in {guild.name} ({guild.id})")
            return

    try:
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Failed to send welcome message to {guild.name} ({guild.id}): {e}")


def main():
    client.run(os.getenv('TOKEN'))


if __name__ == "__main__":
    main()
