import os
import logging
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from commands import (
    apex, league, fortnite, horoscope, help,
    review, tft, kick, servers, pet_commands, show_update, squib_game_commands
)
from commands.league import fetch_application_emojis

load_dotenv()
logger = logging.getLogger('discord.gateway')
logger.setLevel(logging.ERROR)

blacklisted_guilds = set()
if os.getenv('BLACKLISTED_GUILDS'):
    blacklisted_guilds = set(map(int, os.getenv('BLACKLISTED_GUILDS', '').split(',')))

intents = discord.Intents.default()
client = commands.Bot(command_prefix="/", intents=intents)

emojis = {}

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
