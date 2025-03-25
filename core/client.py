import logging
import discord
from discord.ext import commands, tasks
import datetime

from config.settings import TOKEN, BLACKLISTED_GUILDS
from core.errors import setup_error_handlers

logger = logging.getLogger('discord.gateway')
logger.setLevel(logging.ERROR)


class AstroStatsBot(commands.Bot):
    """Custom bot class with additional functionality."""

    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="/", intents=intents)
        # Use a different attribute name to avoid conflict with potential built-in property
        self._emoji_cache = {}
        self.processed_issues = {}

    async def setup_hook(self):
        """Called when the bot is started. Used to load cogs and sync commands."""
        # Import cog setup functions only when needed to avoid circular imports
        from cogs.games.apex import setup as setup_apex
        from cogs.games.league import setup as setup_league
        from cogs.games.fortnite import setup as setup_fortnite
        from cogs.games.tft import setup as setup_tft
        from cogs.general.help import setup as setup_help
        from cogs.general.horoscope import setup as setup_horoscope
        from cogs.general.review import setup as setup_review
        from cogs.general.show_update import setup as setup_show_update
        from cogs.systems.pet_battles import setup as setup_pet_battles
        from cogs.systems.squib_game import setup as setup_squib_game
        from cogs.admin.kick import setup as setup_kick
        from cogs.admin.servers import setup as setup_servers

        # Setup all cogs
        await setup_apex(self)
        await setup_league(self)
        await setup_fortnite(self)
        await setup_tft(self)
        await setup_help(self)
        await setup_horoscope(self)
        await setup_review(self)
        await setup_show_update(self)
        await setup_pet_battles(self)
        await setup_kick(self)
        await setup_servers(self)
        await setup_squib_game(self)

        # Setup error handlers
        setup_error_handlers(self)

        # Start tasks
        self.update_presence.start()

        # Sync commands
        await self.tree.sync()
        logger.info("Commands synced successfully.")

    @tasks.loop(hours=1)
    async def update_presence(self):
        """Update the bot's presence with the server count."""
        guild_count = len(self.guilds)
        presence = discord.Game(name=f"/help | {guild_count} servers")
        await self.change_presence(activity=presence)

    @update_presence.before_loop
    async def before_update_presence(self):
        """Wait until the bot is ready before updating presence."""
        await self.wait_until_ready()

    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f"{self.user} connected to Discord.")

    async def on_guild_join(self, guild: discord.Guild):
        """Called when the bot joins a new guild."""
        # Check if the guild is blacklisted
        if guild.id in BLACKLISTED_GUILDS:
            await guild.leave()
            logger.info(f"Left blacklisted guild: {guild.name} ({guild.id})")
            return

        # Send welcome message
        await self.send_welcome_message(guild)

    async def send_welcome_message(self, guild: discord.Guild):
        """Sends a welcome message to a new guild."""
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
            name="Check Out My Other Apps",
            value=(
                "[ClutchGG.LOL](https://clutchgg.lol)\n"
                "[Diverse Diaries](https://diversediaries.com)\n"
                "[SwiftTasks](https://swifttasks.co.uk)"
            ),
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

        # Find a channel to send the welcome message
        channel = guild.system_channel
        if channel is None or not channel.permissions_for(guild.me).send_messages:
            for ch in guild.text_channels:
                if ch.permissions_for(guild.me).send_messages:
                    channel = ch
                    break
            else:
                logger.info(f"No sendable channel in {guild.name} ({guild.id})")
                return

        try:
            await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to send welcome message to {guild.name} ({guild.id}): {e}")


def create_bot():
    """Create and return a new instance of the AstroStatsBot."""
    return AstroStatsBot()


async def run_bot():
    """Run the bot."""
    bot = create_bot()
    await bot.start(TOKEN)