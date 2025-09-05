import discord
from discord.ext import commands
from discord import app_commands
import random
from collections import deque
from typing import Dict
import os
from config import constants
from ui.embeds import get_premium_promotion_view

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

    def _get_context_key(self, interaction: discord.Interaction) -> str:
        """Return a stable key for per-context memory (guild id or 'DM')."""
        return str(interaction.guild.id) if interaction.guild else "DM"

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
            # Log error for debugging
            import logging
            logging.getLogger(__name__).error(f"Error in would_you_rather command: {e}")
            await interaction.response.send_message("An error occurred while processing your request.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(WouldYouRather(bot))