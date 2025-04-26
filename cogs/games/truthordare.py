import discord
from discord.ext import commands
from discord import app_commands
import random
import os
from config import constants # Make sure constants.py is accessible

class TruthOrDare(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Get the absolute path to the images
        self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.truth_or_dare_img = os.path.join(self.base_path, 'images', 'truthordare.png')
        self.astrostats_img = os.path.join(self.base_path, 'images', 'astrostats.png')

    @app_commands.command(name="truthordare", description="Play a game of Truth or Dare!")
    @app_commands.describe(
        choice="Choose Truth or Dare",
        category="Choose SFW or NSFW"
    )
    @app_commands.choices(
        choice=[
            app_commands.Choice(name="Truth", value="TRUTH"),
            app_commands.Choice(name="Dare", value="DARE")
        ],
        category=[
            app_commands.Choice(name="SFW", value="SFW"),
            app_commands.Choice(name="NSFW", value="NSFW")
        ]
    )
    async def truth_or_dare(self, interaction: discord.Interaction, choice: app_commands.Choice[str], category: app_commands.Choice[str]):
        """Plays a game of Truth or Dare."""
        list_key = f"{category.value}_{choice.value}S" # e.g., SFW_TRUTHS, NSFW_DARES

        try:
            # Get the list of questions/dares from constants
            options_list = getattr(constants, list_key, None)

            if not options_list or not isinstance(options_list, list):
                await interaction.response.send_message(f"Could not find the list for {category.name} {choice.name}s.", ephemeral=True)
                return

            if not options_list: # Check if the list is empty
                 await interaction.response.send_message(f"The list for {category.name} {choice.name}s is empty!", ephemeral=True)
                 return

            # Pick a random item
            selected_item = random.choice(options_list)

            # Create emoji based on category
            category_emoji = "😈" if category.value == "NSFW" else "😇"
            
            # Get server name (or "DM" if in private message)
            server_name = interaction.guild.name if interaction.guild else "DM"

            # Create the embed
            embed = discord.Embed(
                title=f"{category_emoji} {server_name} - {interaction.user.display_name} chose {choice.name.lower()}!",
                description=selected_item,
                color=discord.Color.red() if category.value == "NSFW" else discord.Color.blue()
            )
            
            # Set thumbnail
            embed.set_thumbnail(url=f"attachment://truthordare.png")
            
            # Set footer with AstroStats branding
            embed.set_footer(text="AstroStats | astrostats.vercel.app", icon_url=f"attachment://astrostats.png")

            # Send the message with the image files
            await interaction.response.send_message(
                embed=embed,
                files=[
                    discord.File(self.truth_or_dare_img, "truthordare.png"),
                    discord.File(self.astrostats_img, "astrostats.png")
                ]
            )

        except Exception as e:
            # Log error for debugging - consider using a proper logger
            print(f"Error in truth_or_dare command: {e}")
            await interaction.response.send_message("An error occurred while processing your request.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(TruthOrDare(bot))
