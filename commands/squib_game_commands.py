import random
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import logging

from utils.squib_game import (
    squib_game_sessions,
    get_guild_avatar_url,
    create_new_session,
    run_game_loop,
)

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("SquibGameBot")

class SquibGames(commands.GroupCog, name="squibgames"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.run_tasks = {}

    class JoinButtonView(discord.ui.View):
        def __init__(self, game_id: str, guild_id: str):
            super().__init__(timeout=None)
            self.game_id = game_id
            self.guild_id = guild_id

        def disable_all_buttons(self):
            for child in self.children:
                child.disabled = True

        @discord.ui.button(label="Join", style=discord.ButtonStyle.primary, emoji="➕")
        async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            try:
                game = squib_game_sessions.find_one({
                    "guild_id": self.guild_id,
                    "session_id": self.game_id,
                    "current_game_state": "waiting_for_players"
                })
                if not game:
                    await interaction.response.send_message("The game is no longer available for joining.", ephemeral=True)
                    self.disable_all_buttons()
                    embeds = interaction.message.embeds
                    if embeds:
                        main_embed = embeds[0]
                        updated_main_embed = discord.Embed(
                            title=main_embed.title,
                            description="The game is no longer accepting new players.",
                            color=discord.Color.red()
                        )
                        player_embed = embeds[1] if len(embeds) > 1 else None
                        if player_embed:
                            await interaction.message.edit(embeds=[updated_main_embed, player_embed], view=self)
                        else:
                            await interaction.message.edit(embeds=[updated_main_embed], view=self)
                    else:
                        await interaction.message.edit(view=self)
                    return
                user_id = str(interaction.user.id)
                if any(p["user_id"] == user_id for p in game["participants"]):
                    await interaction.response.send_message("You are already in the game session.", ephemeral=True)
                    return
                new_participant = {
                    "user_id": user_id,
                    "username": interaction.user.display_name,
                    "status": "alive"
                }
                squib_game_sessions.update_one(
                    {"_id": game["_id"]},
                    {"$push": {"participants": new_participant}}
                )
                if not interaction.message.embeds or len(interaction.message.embeds) < 2:
                    await interaction.response.send_message("Internal error: no embed found to update.", ephemeral=True)
                    return
                embeds = interaction.message.embeds
                main_embed = embeds[0]
                player_embed = embeds[1]
                player_count = len(game["participants"]) + 1
                new_description = f"{player_count} Player{' has' if player_count == 1 else 's have'} joined the ranks."
                new_player_embed = discord.Embed(
                    title=player_embed.title,
                    description=new_description,
                    color=player_embed.color
                )
                await interaction.message.edit(embeds=[main_embed, new_player_embed], view=self)
                await interaction.response.send_message("You have joined the game session!", ephemeral=True)
            except Exception as e:
                logger.error(f"Error in join_button: {e}")
                await interaction.response.send_message("An unexpected error occurred. Please try again later.", ephemeral=True)

    @app_commands.command(name="start", description="Start a new multi-minigame Squib Game session")
    async def start(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild_id)
        user_id = str(interaction.user.id)
        existing_game = squib_game_sessions.find_one({
            "guild_id": guild_id,
            "current_game_state": {"$in": ["waiting_for_players", "in_progress"]}
        })
        if existing_game:
            embed = discord.Embed(
                title="Session Already Exists ❌",
                description="A Squib Game session is already in progress or waiting in this server.\n**Please wait** for it to conclude before starting a new one.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        session_id, _ = create_new_session(guild_id, user_id, interaction.user.display_name)
        host_avatar = await get_guild_avatar_url(interaction.guild, int(user_id))
        main_embed = discord.Embed(
            title="New Squib Game Session Created 🎮",
            description=f"A new session has been **created by {interaction.user.mention}**!\n\nLet the games begin!",
            color=discord.Color.blue()
        )
        if host_avatar:
            main_embed.set_thumbnail(url=host_avatar)
        main_embed.set_footer(text="Get ready for the ultimate challenge!")
        player_embed = discord.Embed(
            description="1 Player has joined the ranks.",
            color=discord.Color.green()
        )
        view = self.JoinButtonView(game_id=session_id, guild_id=guild_id)
        await interaction.response.send_message(embeds=[main_embed, player_embed], view=view)

    @app_commands.command(name="run", description="Run all minigame rounds until one winner remains")
    async def run(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild_id)
        game = squib_game_sessions.find_one({
            "guild_id": guild_id,
            "current_game_state": {"$in": ["waiting_for_players", "in_progress"]}
        })
        if not game:
            embed = discord.Embed(
                title="No Active or Waiting Game 🛑",
                description="There is **no active or waiting** Squib Game session in this server.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if game["current_game_state"] == "in_progress" and game["session_id"] in self.run_tasks:
            embed = discord.Embed(
                title="Game Already Running ⚠️",
                description="The game is already in progress.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        host_avatar = await get_guild_avatar_url(interaction.guild, int(game["host_user_id"]))
        current_round = game["current_round"]
        participants_before = game["participants"]
        if game["current_game_state"] == "waiting_for_players":
            if len(participants_before) < 2:
                embed = discord.Embed(
                    title="Not Enough Players 🙋‍♂️",
                    description="You need at **least 2 players** to start a Squib Game session.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            current_round = 0
            squib_game_sessions.update_one(
                {"_id": game["_id"]},
                {"$set": {"current_game_state": "in_progress", "current_round": current_round}}
            )
            run_initiator = interaction.user.mention
            start_embed = discord.Embed(
                title="Squib Game Started 🏁",
                description=(
                    f"**Round {current_round + 1}** begins now!\n"
                    f"The game was started by {run_initiator}.\n"
                    "The game will **proceed automatically** through each round until one winner remains..."
                ),
                color=discord.Color.blue()
            )
            if host_avatar:
                start_embed.set_thumbnail(url=host_avatar)
            await interaction.response.send_message(embed=start_embed)
            await asyncio.sleep(10)
        else:
            run_initiator = interaction.user.mention
            await interaction.response.send_message(f"**{run_initiator}** has initiated the automatic rounds...", ephemeral=True)
        self.run_tasks[game["session_id"]] = asyncio.create_task(
            run_game_loop(self.bot, interaction, game["_id"], guild_id)
        )

    @app_commands.command(name="status", description="View the current Squib Game session status")
    async def status(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild_id)
        game = squib_game_sessions.find_one({
            "guild_id": guild_id,
            "current_game_state": {"$in": ["waiting_for_players", "in_progress"]}
        })
        if not game:
            embed = discord.Embed(
                title="No Active Session 🚫",
                description="No **active or waiting** Squib Game session in this server.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        embed = discord.Embed(
            title="Current Squib Game Status",
            description=(
                f"**Game State**: {game['current_game_state'].title()}\n"
                f"**Round**: {game['current_round']}\n"
                f"**Host**: <@{game['host_user_id']}>"
            ),
            color=discord.Color.dark_orange()
        )
        alive_list = [p["username"] for p in game["participants"] if p["status"] == "alive"]
        eliminated_list = [p["username"] for p in game["participants"] if p["status"] == "eliminated"]

        def summarize_list(player_list, title, max_display=10):
            if len(player_list) > max_display:
                displayed = player_list[:max_display]
                remaining = len(player_list) - max_display
                return f"**{title}**:\n" + ", ".join(displayed) + f" and {remaining} more..."
            else:
                return f"**{title}**:\n" + ", ".join(player_list) if player_list else f"**{title}**:\nNone"

        embed.add_field(name="💚 Alive Players", value=summarize_list(alive_list, "Alive Players"), inline=False)
        embed.add_field(name="💀 Eliminated Players", value=summarize_list(eliminated_list, "Eliminated Players"), inline=False)
        embed.set_footer(text="Will you survive the next round?")
        try:
            host_avatar = await get_guild_avatar_url(interaction.guild, int(game["host_user_id"]))
            if host_avatar:
                embed.set_thumbnail(url=host_avatar)
        except Exception as e:
            logger.error(f"Error fetching host avatar: {e}")
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(SquibGames(bot))
