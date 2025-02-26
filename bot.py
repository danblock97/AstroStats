import os
import logging
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

# Import your commands
from commands import (
    apex, league, fortnite, horoscope, help,
    review, tft, kick, servers, pet_commands, show_update, squib_game_commands
)
from commands.league import fetch_application_emojis

# Import Jira polling utilities from the utils folder.
from utils.jira_poll import JIRA_PROJECTS, poll_jira_project, build_embed

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


@tasks.loop(minutes=20)
async def poll_jira():
    global processed_issues
    channel = client.get_channel(DISCORD_CHANNEL_ID)
    if channel is None:
        channel = await client.fetch_channel(DISCORD_CHANNEL_ID)

    # Iterate over each Jira project configuration
    for project_name, config in JIRA_PROJECTS.items():
        issues = await poll_jira_project(config)
        for issue in issues:
            issue_key = issue.get("key")
            # Create a unique key for each issue by combining project name and issue key.
            unique_key = f"{project_name}_{issue_key}"
            new_embed, new_snapshot, attachment_file = build_embed(issue, config)

            # If the issue is marked as "Released", delete any previous message.
                if new_snapshot.get("status") == "Released":
                if unique_key in processed_issues:
                    try:
                        msg = await channel.fetch_message(processed_issues[unique_key]["message_id"])
                        await msg.delete()
                        del processed_issues[unique_key]
                    except Exception as e:
                        print(f"Failed to delete message for {unique_key}: {e}")
                continue

            # Send a new message if not already processed; otherwise, update it.
            if unique_key not in processed_issues:
                try:
                    if attachment_file is not None:
                        msg = await channel.send(embed=new_embed, file=attachment_file)
                    else:
                        msg = await channel.send(embed=new_embed)
                    processed_issues[unique_key] = {"message_id": msg.id, "snapshot": new_snapshot}
                except Exception as e:
                    print(f"Failed to send embed for {unique_key}: {e}")
            else:
                stored = processed_issues[unique_key]["snapshot"]
                if any(new_snapshot.get(k) != stored.get(k) for k in
                       ["summary", "description", "status", "priority", "att_text"]):
                    try:
                        msg = await channel.fetch_message(processed_issues[unique_key]["message_id"])
                        await msg.edit(embed=new_embed)
                        processed_issues[unique_key]["snapshot"] = new_snapshot
                    except Exception as e:
                        print(f"Failed to update embed for {unique_key}: {e}")


@tasks.loop(hours=1)
async def update_presence():
    guild_count = len(client.guilds)
    presence = discord.Game(name=f"/help | {guild_count} servers")
    await client.change_presence(activity=presence)


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
