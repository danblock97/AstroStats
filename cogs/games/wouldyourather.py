import discord
from discord.ext import commands
from discord import app_commands
import random
import os
from config import constants
from ui.embeds import send_premium_promotion

class WouldYouRather(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Get the absolute path to the images
        self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.would_you_rather_img = os.path.join(self.base_path, 'images', 'wouldyourather.png')
        self.astrostats_img = os.path.join(self.base_path, 'images', 'astrostats.png')

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

            # Pick a random question
            selected_question = random.choice(questions_list)

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

            # Send the message with the image files
            await interaction.response.send_message(
                embed=embed,
                files=[
                    discord.File(thumbnail_file, "wouldyourather.png"),
                    discord.File(self.astrostats_img, "astrostats.png")
                ]
            )
            
            # Add premium promotion
            await send_premium_promotion(interaction, str(interaction.user.id))

        except Exception as e:
            # Log error for debugging
            print(f"Error in would_you_rather command: {e}")
            await interaction.response.send_message("An error occurred while processing your request.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(WouldYouRather(bot))