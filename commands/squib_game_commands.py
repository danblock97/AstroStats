import os
import random
import asyncio
from datetime import datetime, timezone
import logging

import discord
from discord.ext import commands
from discord import app_commands

from pymongo import MongoClient

from utils.embeds import get_conditional_embed

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("SquibGameBot")

mongo_client = MongoClient(os.getenv('MONGODB_URI'))
db = mongo_client['astrostats_database']

squib_game_sessions = db['squib_game_sessions']
squib_game_stats = db['squib_game_stats']

async def get_guild_avatar_url(guild: discord.Guild, user_id: int) -> str:
    try:
        member = await guild.fetch_member(user_id)
        if member and member.guild_avatar:
            return member.guild_avatar.url
        elif member:
            return member.display_avatar.url
        else:
            return None
    except:
        return None

def update_squib_game_stats(user_id: str, guild_id: str, win_increment: int = 0) -> int:
    user_stats = squib_game_stats.find_one({"user_id": user_id, "guild_id": guild_id})
    if not user_stats:
        new_stats = {
            "user_id": user_id,
            "guild_id": guild_id,
            "wins": win_increment,
            "games_played": 1
        }
        squib_game_stats.insert_one(new_stats)
        return new_stats["wins"]
    else:
        new_wins = user_stats.get("wins", 0) + win_increment
        new_games_played = user_stats.get("games_played", 0) + 1
        squib_game_stats.update_one(
            {"_id": user_stats["_id"]},
            {"$set": {"wins": new_wins, "games_played": new_games_played}}
        )
        return new_wins

MINIGAMES = [
    {
        "name": "Red Light, Green Light 🚦",
        "emoji": "\U0001F6A5",
        "description": "Players must stay still when 'Red Light' is called.",
        "elimination_probability": 0.5
    },
    {
        "name": "Glass Bridge 🌉",
        "emoji": "\U0001F309",
        "description": "Choose the correct glass panels to cross safely.",
        "elimination_probability": 0.3
    },
    {
        "name": "Random Mayhem ⚡",
        "emoji": "\U000026A1",
        "description": "Unpredictable chaos ensues, testing players' luck.",
        "elimination_probability": 0.2
    },
    {
        "name": "Simon Says 🎤",
        "emoji": "\U0001F3A4",
        "description": "Players must follow the leader's commands precisely.",
        "elimination_probability": 0.25
    },
    {
        "name": "Treasure Hunt 🗺️",
        "emoji": "\U0001F5FA",
        "description": "Players search for hidden treasures under time pressure.",
        "elimination_probability": 0.35
    },
    {
        "name": "Knife Throwing 🗡️",
        "emoji": "\U0001F5E1",
        "description": "Players attempt to throw knives at a target with precision.",
        "elimination_probability": 0.4
    },
    {
        "name": "Marbles Madness 🏀",
        "emoji": "\U0001F3C0",
        "description": "Compete in a fast-paced marbles game where the last marble standing wins.",
        "elimination_probability": 0.3
    },
    {
        "name": "Dollmaker 🪆",
        "emoji": "\U0001FA86",
        "description": "Create dolls based on specific criteria; the least creative ones are eliminated.",
        "elimination_probability": 0.25
    },
    {
        "name": "Heartbeat 💓",
        "emoji": "\U0001F493",
        "description": "Players must keep their heartbeats steady; sudden changes lead to elimination.",
        "elimination_probability": 0.35
    },
    {
        "name": "Tug of War 🤼",
        "emoji": "\U0001F93C",
        "description": "Teams compete in a tug of war; the losing team faces elimination.",
        "elimination_probability": 0.5
    },
    {
        "name": "Quiz Show 🧠",
        "emoji": "\U0001F4DA",
        "description": "Answer rapid-fire trivia questions correctly to stay in the game.",
        "elimination_probability": 0.3
    },
    {
        "name": "Paintball 🖌️",
        "emoji": "\U0001F58C",
        "description": "Engage in a virtual paintball match; the last player unhit wins.",
        "elimination_probability": 0.4
    },
    {
        "name": "Maze Runner 🌀",
        "emoji": "\U0001F300",
        "description": "Navigate through a complex maze; failing to find the exit leads to elimination.",
        "elimination_probability": 0.35
    },
    {
        "name": "Jigsaw Puzzle 🧩",
        "emoji": "\U0001F9E9",
        "description": "Complete a jigsaw puzzle within the time limit to avoid elimination.",
        "elimination_probability": 0.25
    },
    {
        "name": "Scavenger Hunt 🔍",
        "emoji": "\U0001F50D",
        "description": "Find hidden items based on clues; failure to locate them results in elimination.",
        "elimination_probability": 0.3
    }
]

def generate_flavor_text(minigame_desc: str, eliminated_this_round: list, alive_players: list) -> str:
    flavor_sentences = []
    max_display = 10
    if "Red Light" in minigame_desc:
        if eliminated_this_round:
            if len(eliminated_this_round) > max_display:
                displayed = eliminated_this_round[:max_display]
                remaining = len(eliminated_this_round) - max_display
                flavor_sentences.append(
                    f"As the lights flickered, **{', '.join(displayed)}** "
                    f"{'and ' + str(remaining) + ' others' if remaining > 0 else ''} were caught moving at the wrong moment..."
                )
            else:
                flavor_sentences.append(
                    f"As the lights flickered, **{', '.join(eliminated_this_round)}** were caught moving at the wrong moment..."
                )
        else:
            flavor_sentences.append("Everyone froze perfectly still—no one got caught this time!")
        if alive_players:
            flavor_sentences.append(
                f"The relentless spotlights scanned the field, but **{', '.join(alive_players)}** "
                "made it through unscathed."
            )
    elif "Glass Bridge" in minigame_desc:
        if eliminated_this_round:
            if len(eliminated_this_round) > max_display:
                displayed = eliminated_this_round[:max_display]
                remaining = len(eliminated_this_round) - max_display
                flavor_sentences.append(
                    f"**{', '.join(displayed)}** "
                    f"{'and ' + str(remaining) + ' others' if remaining > 0 else ''} chose the wrong panel and plummeted into the abyss..."
                )
            else:
                flavor_sentences.append(
                    f"**{', '.join(eliminated_this_round)}** chose the wrong panel and plummeted into the abyss..."
                )
        else:
            flavor_sentences.append(
                "Miraculously, nobody fell this round—every guess was spot on!"
            )
        if alive_players:
            flavor_sentences.append(
                f"Shards of glass littered the bridge, yet **{', '.join(alive_players)}** "
                "bravely reached the other side."
            )
    elif "Simon Says" in minigame_desc:
        if eliminated_this_round:
            if len(eliminated_this_round) > max_display:
                displayed = eliminated_this_round[:max_display]
                remaining = len(eliminated_this_round) - max_display
                flavor_sentences.append(
                    f"**{', '.join(displayed)}** "
                    f"{'and ' + str(remaining) + ' others' if remaining > 0 else ''} failed to follow the commands and were eliminated..."
                )
            else:
                flavor_sentences.append(
                    f"**{', '.join(eliminated_this_round)}** failed to follow the commands and were eliminated..."
                )
        else:
            flavor_sentences.append(
                "Everyone followed the commands flawlessly—no eliminations this round!"
            )
        if alive_players:
            flavor_sentences.append(
                f"**{', '.join(alive_players)}** showed impeccable discipline and stayed in the game."
            )
    elif "Treasure Hunt" in minigame_desc:
        if eliminated_this_round:
            if len(eliminated_this_round) > max_display:
                displayed = eliminated_this_round[:max_display]
                remaining = len(eliminated_this_round) - max_display
                flavor_sentences.append(
                    f"**{', '.join(displayed)}** "
                    f"{'and ' + str(remaining) + ' others' if remaining > 0 else ''} couldn't find the hidden treasures in time and were eliminated..."
                )
            else:
                flavor_sentences.append(
                    f"**{', '.join(eliminated_this_round)}** couldn't find the hidden treasures in time and were eliminated..."
                )
        else:
            flavor_sentences.append(
                "All players found the treasures swiftly—no eliminations this round!"
            )
        if alive_players:
            flavor_sentences.append(
                f"**{', '.join(alive_players)}** continue their quest with renewed vigor."
            )
    else:
        if eliminated_this_round:
            if len(eliminated_this_round) > max_display:
                displayed = eliminated_this_round[:max_display]
                remaining = len(eliminated_this_round) - max_display
                flavor_sentences.append(
                    f"The chaos claimed **{', '.join(displayed)}** "
                    f"{'and ' + str(remaining) + ' others' if remaining > 0 else ''} as they stumbled in the mayhem..."
                )
            else:
                flavor_sentences.append(
                    f"The chaos claimed **{', '.join(eliminated_this_round)}** as they stumbled in the mayhem..."
                )
        else:
            flavor_sentences.append("Somehow, no one fell victim to the chaos this round!")
        if alive_players:
            flavor_sentences.append(
                f"By skill or sheer luck, **{', '.join(alive_players)}** remain in the competition."
            )
    return "\n".join(flavor_sentences)

def play_minigame_logic(round_number: int, participants: list) -> (list, dict):
    updated = [dict(p) for p in participants]
    minigame = random.choice(MINIGAMES)
    minigame_desc = f"{minigame['name']} {minigame['emoji']}"
    elimination_candidates = [p for p in updated if p["status"] == "alive" and random.random() < minigame["elimination_probability"]]
    random.shuffle(elimination_candidates)
    for p in elimination_candidates[:3]:
        p["status"] = "eliminated"
    return updated, minigame

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
                await interaction.response.send_message(f"You have joined the game session!", ephemeral=True)
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
                description=(
                    "A Squib Game session is already in progress or waiting in this server.\n"
                    "**Please wait** for it to conclude before starting a new one."
                ),
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        session_id = f"{guild_id}_{user_id}_{int(datetime.now().timestamp())}"
        new_session_doc = {
            "guild_id": guild_id,
            "host_user_id": user_id,
            "session_id": session_id,
            "current_round": 0,
            "current_game_state": "waiting_for_players",
            "participants": [
                {
                    "user_id": user_id,
                    "username": interaction.user.display_name,
                    "status": "alive"
                }
            ],
            "created_at": datetime.now(timezone.utc)
        }
        squib_game_sessions.insert_one(new_session_doc)
        host_avatar = await get_guild_avatar_url(interaction.guild, int(user_id))
        main_embed = discord.Embed(
            title="New Squib Game Session Created 🎮",
            description=(
                f"A new session has been **created by {interaction.user.mention}**!\n\n"
                "Let the games begin!"
            ),
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
                description=(
                    "There is **no active or waiting** Squib Game session in this server."
                ),
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
                {"$set": {
                 "current_game_state": "in_progress",
                    "current_round": current_round
                }}
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
            await interaction.response.send_message(
                f"**{run_initiator}** has initiated the automatic rounds...", ephemeral=True
            )
        self.run_tasks[game["session_id"]] = asyncio.create_task(
            self.game_loop(interaction, game["_id"], guild_id)
        )

    async def game_loop(self, interaction: discord.Interaction, game_id: str, guild_id: str):
        while True:
            game = squib_game_sessions.find_one({"_id": game_id})
            current_round = game["current_round"]
            participants_before = game["participants"]
            alive_before = [p for p in participants_before if p["status"] == "alive"]
            if len(alive_before) < 1:
                winner = None
                final_embeds = await self.conclude_game_auto(interaction, game, guild_id, current_round, winner=winner)
                await interaction.followup.send(embeds=final_embeds)
                break
            elif len(alive_before) == 1:
                winner = alive_before[0]
                final_embeds = await self.conclude_game_auto(interaction, game, guild_id, current_round, winner=winner)
                await interaction.followup.send(embeds=final_embeds)
                break
            updated_participants, minigame = play_minigame_logic(current_round + 1, participants_before)
            newly_eliminated = []
            for old_p in participants_before:
                if old_p["status"] == "alive":
                    match = next((x for x in updated_participants if x["user_id"] == old_p["user_id"]), None)
                    if match and match["status"] == "eliminated":
                        newly_eliminated.append(old_p["username"])
            squib_game_sessions.update_one(
                {"_id": game_id},
                {"$set": {"participants": updated_participants, "current_round": current_round + 1}}
            )
            alive_after = [p for p in updated_participants if p["status"] == "alive"]
            total_eliminated = len([p for p in updated_participants if p["status"] == "eliminated"])
            round_flavor = generate_flavor_text(
                minigame["description"],
                newly_eliminated,
                [p["username"] for p in alive_after]
            )
            round_embed = discord.Embed(
                title=f"Round {current_round + 1} - {minigame['name']} {minigame['emoji']}",
                description=(
                    f"🔥 **Eliminated this round**: {total_eliminated}/{len(updated_participants)}\n"
                    f"🏆 **Players still alive**: {len(alive_after)}\n\n"
                    f"{round_flavor}\n\n"
                    "*Next round will start automatically in a few seconds...*"
                ),
                color=discord.Color.blue()
            )
            if newly_eliminated:
                chosen_elim_username = random.choice(newly_eliminated)
                try:
                    chosen_elim = next(p for p in updated_participants if p["username"] == chosen_elim_username)
                    elim_avatar = await get_guild_avatar_url(interaction.guild, int(chosen_elim["user_id"]))
                    if elim_avatar:
                        round_embed.set_thumbnail(url=elim_avatar)
                except Exception as e:
                    logger.error(f"Error fetching user avatar: {e}")
                    host_avatar = await get_guild_avatar_url(interaction.guild, int(game["host_user_id"]))
                    if host_avatar:
                        round_embed.set_thumbnail(url=host_avatar)
            else:
                host_avatar = await get_guild_avatar_url(interaction.guild, int(game["host_user_id"]))
                if host_avatar:
                    round_embed.set_thumbnail(url=host_avatar)
            await interaction.followup.send(embed=round_embed)
            await asyncio.sleep(10)

    async def conclude_game_auto(self, interaction: discord.Interaction, game_doc: dict, guild_id: str, final_round: int, winner=None) -> list:
        squib_game_sessions.update_one(
            {"_id": game_doc["_id"]},
            {"$set": {"current_game_state": "completed"}}
        )
        if winner is None:
            participants = game_doc["participants"]
            alive_players = [p for p in participants if p["status"] == "alive"]
            total_alive = len(alive_players)
            if total_alive == 1:
                winner = alive_players[0]
            elif total_alive > 1:
                winner = random.choice(alive_players)
            else:
                winner = random.choice(participants)
        new_wins = update_squib_game_stats(winner["user_id"], guild_id, win_increment=1)
        try:
            winner_avatar = await get_guild_avatar_url(interaction.guild, int(winner["user_id"]))
        except Exception as e:
            logger.error(f"Error fetching user avatar: {e}")
            winner_avatar = None
        final_embed = discord.Embed(title="Game Over! 🏆", color=discord.Color.gold())
        round_title = f"Final Round {final_round}"
        final_embed.description = (
            f"**{round_title}** concluded.\n\n"
            f"The winner is **{winner['username']}**! 🎉🏆\n\n"
            f"They now have **{new_wins} wins** in this server."
        )
        if winner_avatar:
            final_embed.set_thumbnail(url=winner_avatar)
        final_embed.set_footer(text="Thanks for playing Squib Game!")
        conditional_embed = await get_conditional_embed(
            interaction, 'SQUIB_GAME_COMMANDS_EMBED', discord.Color.orange()
        )
        embeds = [final_embed]
        if conditional_embed:
            embeds.append(conditional_embed)
        return embeds

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
        embed.add_field(
            name="💚 Alive Players",
            value=summarize_list(alive_list, "Alive Players"),
            inline=False
        )
        embed.add_field(
            name="💀 Eliminated Players",
            value=summarize_list(eliminated_list, "Eliminated Players"),
            inline=False
        )
        embed.set_footer(text="Will you survive the next round?")
        host_id = game["host_user_id"]
        try:
            host_avatar = await get_guild_avatar_url(interaction.guild, int(host_id))
            if host_avatar:
                embed.set_thumbnail(url=host_avatar)
        except Exception as e:
            logger.error(f"Error fetching host avatar: {e}")
        await interaction.response.send_message(embed=embed)

async def setup(bot_client: commands.Bot):
    await bot_client.add_cog(SquibGames(bot_client))
