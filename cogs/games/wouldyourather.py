import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
from collections import deque
from typing import Dict, Optional
import os
import logging
from datetime import time as dtime
from zoneinfo import ZoneInfo
from config import constants
from ui.embeds import get_premium_promotion_view
from services.database.wouldyourather import get_wyr_auto_settings, update_wyr_auto_settings, get_all_enabled_guilds

logger = logging.getLogger(__name__)

class WouldYouRather(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Get the absolute path to the images
        self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.would_you_rather_img = os.path.join(self.base_path, 'images', 'wouldyourather.png')
        self.astrostats_img = os.path.join(self.base_path, 'images', 'astrostats.png')
        # Recent-question memory per context (guild or DM) and category (SFW/NSFW)
        # Structure: { context_key: { category: deque(maxlen=N) } }
        self._recent_questions: Dict[str, Dict[str, deque]] = {}

    async def cog_load(self):
        """Called when the cog is loaded."""
        self.auto_wyr_task.start()

    async def cog_unload(self):
        """Called when the cog is unloaded."""
        self.auto_wyr_task.cancel()

    def _get_context_key(self, interaction: discord.Interaction) -> str:
        """Return a stable key for per-context memory (guild id or 'DM')."""
        return str(interaction.guild.id) if interaction.guild else "DM"

    def _get_context_key_for_guild(self, guild_id: Optional[int]) -> str:
        """Return a stable key for per-context memory (guild id or 'DM')."""
        return str(guild_id) if guild_id else "DM"

    def _select_non_repeating(self, interaction: discord.Interaction, category: str, questions_list: list) -> str:
        """Select a question avoiding recent repeats within the same context and category.

        Uses a sliding window sized to 20% of the pool (min 10, max len-1). Resets when exhausted.
        """
        context_key = self._get_context_key(interaction)
        # Initialize storage for this context and category
        if context_key not in self._recent_questions:
            self._recent_questions[context_key] = {}

        # Determine memory size based on pool size
        pool_size = len(questions_list)
        if pool_size <= 1:
            return questions_list[0]
        recent_window = max(10, min(pool_size - 1, pool_size // 5))  # 20% window, at least 10, at most pool_size-1

        recent_for_category = self._recent_questions[context_key].get(category)
        if recent_for_category is None or recent_for_category.maxlen != recent_window:
            recent_for_category = deque(maxlen=recent_window)
            self._recent_questions[context_key][category] = recent_for_category

        # Build candidate pool excluding recent
        candidates = [q for q in questions_list if q not in recent_for_category]
        if not candidates:
            # All questions recently used; reset memory for freshness
            recent_for_category.clear()
            candidates = questions_list[:]

        selected = random.choice(candidates)
        recent_for_category.append(selected)
        return selected

    def _select_non_repeating_for_guild(self, guild_id: Optional[int], category: str, questions_list: list) -> str:
        """Select a question avoiding recent repeats for a guild (used in auto mode)."""
        context_key = self._get_context_key_for_guild(guild_id)
        # Initialize storage for this context and category
        if context_key not in self._recent_questions:
            self._recent_questions[context_key] = {}

        # Determine memory size based on pool size
        pool_size = len(questions_list)
        if pool_size <= 1:
            return questions_list[0]
        recent_window = max(10, min(pool_size - 1, pool_size // 5))

        recent_for_category = self._recent_questions[context_key].get(category)
        if recent_for_category is None or recent_for_category.maxlen != recent_window:
            recent_for_category = deque(maxlen=recent_window)
            self._recent_questions[context_key][category] = recent_for_category

        # Build candidate pool excluding recent
        candidates = [q for q in questions_list if q not in recent_for_category]
        if not candidates:
            recent_for_category.clear()
            candidates = questions_list[:]

        selected = random.choice(candidates)
        recent_for_category.append(selected)
        return selected

    async def _send_wyr_message(self, channel: discord.TextChannel, category: str, guild_name: str):
        """Send a would you rather message to a channel."""
        list_key = f"{category}_WOULD_YOU_RATHER"
        questions_list = getattr(constants, list_key, None)
        if not questions_list or not isinstance(questions_list, list) or not questions_list:
            logger.error(f"Could not find questions list for {category}")
            return

        selected_question = self._select_non_repeating_for_guild(channel.guild.id if channel.guild else None, category, questions_list)
        category_emoji = "😈" if category == "NSFW" else "🤔"

        embed = discord.Embed(
            title=f"{category_emoji} {guild_name} - Would You Rather",
            description=selected_question,
            color=discord.Color.red() if category == "NSFW" else discord.Color.blue()
        )

        thumbnail_file = self.would_you_rather_img if os.path.exists(self.would_you_rather_img) else os.path.join(self.base_path, 'images', 'truthordare.png')
        embed.set_thumbnail(url=f"attachment://wouldyourather.png")
        embed.set_footer(text="AstroStats | astrostats.info", icon_url=f"attachment://astrostats.png")

        try:
            await channel.send(
                embeds=[embed],
                files=[
                    discord.File(thumbnail_file, "wouldyourather.png"),
                    discord.File(self.astrostats_img, "astrostats.png")
                ]
            )
        except Exception as e:
            logger.error(f"Error sending auto would you rather message to channel {channel.id}: {e}", exc_info=True)

    @app_commands.command(name="wouldyourather", description="Play a game of Would You Rather!")
    @app_commands.describe(
        category="Choose SFW or NSFW"
    )
    @app_commands.choices(
        category=[
            app_commands.Choice(name="SFW", value="SFW"),
            app_commands.Choice(name="NSFW", value="NSFW")
        ]
    )
    async def would_you_rather(self, interaction: discord.Interaction, category: app_commands.Choice[str]):
        """Plays a game of Would You Rather."""
        list_key = f"{category.value}_WOULD_YOU_RATHER"

        try:
            # Get the list of questions from constants
            questions_list = getattr(constants, list_key, None)

            if not questions_list or not isinstance(questions_list, list):
                await interaction.response.send_message(f"Could not find the list for {category.name} Would You Rather questions.", ephemeral=True)
                return

            if not questions_list:
                await interaction.response.send_message(f"The list for {category.name} Would You Rather questions is empty!", ephemeral=True)
                return

            # Pick a question with reduced repeat probability per context/category
            selected_question = self._select_non_repeating(interaction, category.value, questions_list)

            # Create emoji based on category
            category_emoji = "😈" if category.value == "NSFW" else "🤔"
            
            # Get server name (or "DM" if in private message)
            server_name = interaction.guild.name if interaction.guild else "DM"

            # Create the embed
            embed = discord.Embed(
                title=f"{category_emoji} {server_name} - Would You Rather",
                description=selected_question,
                color=discord.Color.red() if category.value == "NSFW" else discord.Color.blue()
            )
            
            # Set thumbnail - fallback to truthordare.png if wouldyourather.png doesn't exist
            thumbnail_file = self.would_you_rather_img if os.path.exists(self.would_you_rather_img) else os.path.join(self.base_path, 'images', 'truthordare.png')
            embed.set_thumbnail(url=f"attachment://wouldyourather.png")
            
            # Set footer with AstroStats branding
            embed.set_footer(text="AstroStats | astrostats.info", icon_url=f"attachment://astrostats.png")

            embeds = [embed]
            premium_view = get_premium_promotion_view(str(interaction.user.id))
            
            # Send the message with the image files
            await interaction.response.send_message(
                embeds=embeds,
                view=premium_view,
                files=[
                    discord.File(thumbnail_file, "wouldyourather.png"),
                    discord.File(self.astrostats_img, "astrostats.png")
                ]
            )

        except Exception as e:
            logger.error(f"Error in would_you_rather command: {e}", exc_info=True)
            await interaction.response.send_message("An error occurred while processing your request.", ephemeral=True)

    @app_commands.command(name="wouldyourather-automode", description="Toggle auto mode for Would You Rather (Admin only)")
    @app_commands.describe(
        enabled="Enable or disable auto mode",
        category="Choose SFW or NSFW for auto mode (required when enabling)"
    )
    @app_commands.choices(
        category=[
            app_commands.Choice(name="SFW", value="SFW"),
            app_commands.Choice(name="NSFW", value="NSFW")
        ]
    )
    async def would_you_rather_automode(self, interaction: discord.Interaction, enabled: bool, category: Optional[str] = None):
        """Toggle auto mode for Would You Rather questions."""
        try:
            if not interaction.user.guild_permissions.manage_guild:
                embed = discord.Embed(
                    title="❌ Missing Permissions",
                    description="You need the **Manage Server** permission to use this command.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if not interaction.guild:
                await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
                return

            guild_id = str(interaction.guild.id)

            if enabled:
                if not category or category not in ["SFW", "NSFW"]:
                    await interaction.response.send_message("Please specify a valid category (SFW or NSFW) when enabling auto mode.", ephemeral=True)
                    return

                channel_id = str(interaction.channel.id) if interaction.channel else None
                if not channel_id:
                    await interaction.response.send_message("Could not determine channel ID.", ephemeral=True)
                    return

                success = update_wyr_auto_settings(
                    guild_id=guild_id,
                    enabled=True,
                    category=category,
                    channel_id=channel_id
                )

                if not success:
                    await interaction.response.send_message("Failed to update auto mode settings. Please try again.", ephemeral=True)
                    return

                embed = discord.Embed(
                    title="✅ Auto Mode Enabled",
                    description=f"Would You Rather auto mode has been enabled for **{category}** questions.\n\n"
                               f"Questions will be automatically posted daily at 12:00 PM (Europe/London time) in this channel.",
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                success = update_wyr_auto_settings(guild_id=guild_id, enabled=False)
                if not success:
                    await interaction.response.send_message("Failed to update auto mode settings. Please try again.", ephemeral=True)
                    return

                embed = discord.Embed(
                    title="❌ Auto Mode Disabled",
                    description="Would You Rather auto mode has been disabled.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error in would_you_rather_automode command: {e}", exc_info=True)
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("An error occurred while processing your request. Please try again.", ephemeral=True)
                else:
                    await interaction.followup.send("An error occurred while processing your request. Please try again.", ephemeral=True)
            except Exception as followup_error:
                logger.error(f"Error sending error message: {followup_error}", exc_info=True)

    @tasks.loop(time=dtime(hour=12, minute=0, tzinfo=ZoneInfo("Europe/London")))
    async def auto_wyr_task(self):
        """Automatically send Would You Rather questions at 12:00 PM Europe/London time."""
        logger.debug("Starting auto would you rather task...")
        try:
            enabled_guilds = get_all_enabled_guilds()
            if not enabled_guilds:
                logger.debug("No guilds with auto mode enabled.")
                return

            for guild_doc in enabled_guilds:
                try:
                    guild_id = int(guild_doc.get("guild_id"))
                    category = guild_doc.get("category")
                    channel_id_str = guild_doc.get("channel_id")

                    if not category or not channel_id_str:
                        logger.warning(f"Skipping guild {guild_id}: missing category or channel_id")
                        continue

                    guild = self.bot.get_guild(guild_id)
                    if not guild:
                        logger.debug(f"Guild {guild_id} not found, skipping")
                        continue

                    channel_id = int(channel_id_str)
                    channel = guild.get_channel(channel_id)
                    if not channel:
                        logger.warning(f"Channel {channel_id} not found in guild {guild_id}")
                        continue

                    if not isinstance(channel, discord.TextChannel):
                        logger.warning(f"Channel {channel_id} is not a text channel")
                        continue

                    if not channel.permissions_for(guild.me).send_messages:
                        logger.warning(f"Bot lacks permission to send messages in channel {channel_id}")
                        continue

                    await self._send_wyr_message(channel, category, guild.name)
                    logger.debug(f"Sent auto would you rather message to guild {guild_id} in channel {channel_id}")

                except Exception as e:
                    logger.error(f"Error processing auto would you rather for guild {guild_doc.get('guild_id')}: {e}", exc_info=True)
                    continue

        except Exception as e:
            logger.error(f"Error in auto would you rather task: {e}", exc_info=True)

    @auto_wyr_task.before_loop
    async def before_auto_wyr_task(self):
        """Wait until the bot is ready before starting the auto task."""
        await self.bot.wait_until_ready()
        logger.debug("Auto would you rather task ready.")


async def setup(bot: commands.Bot):
    await bot.add_cog(WouldYouRather(bot))