import os
import random
import asyncio
from datetime import datetime, timezone

import discord
from discord.ext import commands
from discord import app_commands

from pymongo import MongoClient

# ------------------------------------------------------
# MongoDB Setup
# ------------------------------------------------------
mongo_client = MongoClient(os.getenv('MONGODB_URI'))
db = mongo_client['pet_database']

squib_game_sessions = db['squib_game_sessions']
squib_game_stats = db['squib_game_stats']

# ------------------------------------------------------
# Update Stats (Wins, Games Played)
# ------------------------------------------------------
def update_squib_game_stats(user_id: str, guild_id: str, win_increment: int = 0) -> int:
    """
    Increments the wins for user_id in guild_id.
    Returns the updated total wins.
    """
    user_stats = squib_game_stats.find_one({"user_id": user_id, "guild_id": guild_id})
    if not user_stats:
        new_stats = {
            "user_id": user_id,
            "guild_id": guild_id,
            "wins": win_increment,
            "games_played": 1
        }
        result = squib_game_stats.insert_one(new_stats)
        return new_stats["wins"]
    else:
        new_wins = user_stats.get("wins", 0) + win_increment
        new_games_played = user_stats.get("games_played", 0) + 1
        squib_game_stats.update_one(
            {"_id": user_stats["_id"]},
            {"$set": {"wins": new_wins, "games_played": new_games_played}}
        )
        return new_wins


# ------------------------------------------------------
# Minigames Configuration
# ------------------------------------------------------
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
    }
    # Add more minigames as desired
]

# ------------------------------------------------------
# Flavor Text Generator
# ------------------------------------------------------
def generate_flavor_text(minigame_desc: str, eliminated_this_round: list, alive_players: list) -> str:
    flavor_sentences = []
    max_display = 10  # Maximum number of names to display

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


# ------------------------------------------------------
# Minigame Logic
# ------------------------------------------------------
def play_minigame_logic(round_number: int, participants: list) -> (list, dict):
    """
    Selects a minigame and updates participant statuses based on elimination probabilities.
    Returns updated participants and the selected minigame details.
    """
    updated = [dict(p) for p in participants]  # copy

    # Select a minigame (randomly)
    minigame = random.choice(MINIGAMES)
    minigame_desc = f"{minigame['name']} {minigame['emoji']}"

    for p in updated:
        if p["status"] == "alive" and random.random() < minigame["elimination_probability"]:
            p["status"] = "eliminated"

    return updated, minigame


# ------------------------------------------------------
# Command Group: SquibGames
# ------------------------------------------------------
class SquibGames(commands.GroupCog, name="squibgames"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.run_tasks = {}  # To keep track of running game loops per game session

    class JoinButtonView(discord.ui.View):
        def __init__(self, game_id: str, guild_id: str):
            super().__init__(timeout=None)
            self.game_id = game_id
            self.guild_id = guild_id

        @discord.ui.button(label="Join", style=discord.ButtonStyle.primary, emoji="➕")
        async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            # Handle user joining
            game = squib_game_sessions.find_one({
                "guild_id": self.guild_id,
                "session_id": self.game_id,
                "current_game_state": "waiting_for_players"
            })

            if not game:
                await interaction.response.send_message("The game is no longer available for joining.", ephemeral=True)
                self.disable_all_items()
                await interaction.message.edit(view=self)
                return

            user_id = str(interaction.user.id)
            if any(p["user_id"] == user_id for p in game["participants"]):
                await interaction.response.send_message("You are already in the game session.", ephemeral=True)
                return

            # Add the user to participants
            new_participant = {
                "user_id": user_id,
                "username": interaction.user.display_name,
                "status": "alive"
            }
            squib_game_sessions.update_one(
                {"_id": game["_id"]},
                {"$push": {"participants": new_participant}}
            )

            # Update the "Players Joined" embed (second embed, index 1)
            if not interaction.message.embeds or len(interaction.message.embeds) < 2:
                await interaction.response.send_message("Internal error: no embed found to update.", ephemeral=True)
                return

            # Retrieve existing embeds
            embeds = interaction.message.embeds
            main_embed = embeds[0]
            player_embed = embeds[1]

            # Update the "Players Joined" description
            player_count = len(game["participants"]) + 1  # since added

            new_description = f"{player_count} Player{' has' if player_count == 1 else 's have'} joined the ranks."

            # Create a new embed with updated description
            new_player_embed = discord.Embed(
                title=player_embed.title,
                description=new_description,
                color=player_embed.color
            )

            # Edit the message with updated embeds
            await interaction.message.edit(embeds=[main_embed, new_player_embed], view=self)

            # Acknowledge the user
            await interaction.response.send_message(f"You have joined the game session!", ephemeral=True)

    # ----------------------------------
    # /squibgames start
    # ----------------------------------
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

        host_user = await interaction.client.fetch_user(int(user_id))
        main_embed = discord.Embed(
            title="New Squib Game Session Created 🎮",
            description=(
                f"A new session has been **created by {interaction.user.mention}**!\n\n"
                "Let the games begin!"
            ),
            color=discord.Color.blue()
        )
        if host_user and host_user.avatar:
            main_embed.set_thumbnail(url=host_user.display_avatar.url)
        main_embed.set_footer(text="Get ready for the ultimate challenge!")

        # Create the "Players Joined" embed
        player_embed = discord.Embed(
            title="👍 Players Joined",
            description="1 Player has joined the ranks.",
            color=discord.Color.green()
        )

        # Create the Join button View
        view = self.JoinButtonView(game_id=session_id, guild_id=guild_id)

        # Send the message with both embeds and the Join button
        await interaction.response.send_message(embeds=[main_embed, player_embed], view=view)

    # ----------------------------------
    # /squibgames run
    # ----------------------------------
    @app_commands.command(name="run", description="(Automatic) Run all minigame rounds until one winner remains")
    async def run(self, interaction: discord.Interaction):
        """
        Auto-run from current_round until only one player remains.
        """
        guild_id = str(interaction.guild_id)
        user_id = str(interaction.user.id)

        game = squib_game_sessions.find_one({
            "guild_id": guild_id,
            "host_user_id": user_id,
            "current_game_state": {"$in": ["waiting_for_players", "in_progress"]}
        })
        if not game:
            embed = discord.Embed(
                title="Not a Host or No Game 🛑",
                description=(
                    "You are **not** the host of an active/waiting Squib Game session, "
                    "or no active session exists."
                ),
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Prevent multiple run commands for the same game session
        if game["current_game_state"] == "in_progress" and game["session_id"] in self.run_tasks:
            embed = discord.Embed(
                title="Game Already Running ⚠️",
                description="The game is already in progress.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Host's avatar for the embed
        host_user = await interaction.client.fetch_user(int(user_id))
        host_avatar = host_user.display_avatar.url if (host_user and host_user.avatar) else None

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

            current_round = 1
            squib_game_sessions.update_one(
                {"_id": game["_id"]},
                {"$set": {
                    "current_game_state": "in_progress",
                    "current_round": current_round
                }}
            )

            start_embed = discord.Embed(
                title="Squib Game Started (Auto) 🏁",
                description=(
                    f"**Round {current_round}** begins now!\n"
                    "The game will **proceed automatically** through each round until one winner remains..."
                ),
                color=discord.Color.blue()
            )
            if host_avatar:
                start_embed.set_thumbnail(url=host_avatar)

            await interaction.response.send_message(embed=start_embed)
            await asyncio.sleep(2)

        else:
            await interaction.response.send_message(
                "**Starting automatic rounds...**", ephemeral=True
            )

        # Start the game loop as a background task
        self.run_tasks[game["session_id"]] = asyncio.create_task(
            self.game_loop(interaction, game["_id"], guild_id)
        )

    async def game_loop(self, interaction: discord.Interaction, game_id: str, guild_id: str):
        while True:
            game = squib_game_sessions.find_one({"_id": game_id})
            current_round = game["current_round"]
            participants_before = game["participants"]
            alive_before = [p for p in participants_before if p["status"] == "alive"]

            # Check for termination condition
            if len(alive_before) <= 1:
                final_embed = await self.conclude_game_auto(interaction, game, guild_id, current_round)
                await interaction.followup.send(embed=final_embed)
                break

            # Play a minigame
            updated_participants, minigame = play_minigame_logic(current_round + 1, participants_before)

            # Determine newly eliminated players
            newly_eliminated = [
                p["username"] for p, q in zip(participants_before, updated_participants)
                if p["status"] == "alive" and q["status"] == "eliminated"
            ]

            # Update the game session with new participant statuses and round number
            squib_game_sessions.update_one(
                {"_id": game_id},
                {"$set": {"participants": updated_participants, "current_round": current_round + 1}}
            )

            alive_after = [p for p in updated_participants if p["status"] == "alive"]
            total_eliminated = len([p for p in updated_participants if p["status"] == "eliminated"])

            # Generate flavor text
            round_flavor = generate_flavor_text(
                minigame["description"],
                newly_eliminated,
                [p["username"] for p in alive_after]
            )

            # Create the round embed
            round_embed = discord.Embed(
                title=f"Round {current_round + 1} - {minigame['name']} {minigame['emoji']}",
                description=(
                    f"🔥 **Eliminated so far**: {total_eliminated}/{len(updated_participants)}\n"
                    f"🏆 **Players still alive**: {len(alive_after)}\n\n"
                    f"{round_flavor}\n\n"
                    "*Next round will start automatically in a few seconds...*"
                ),
                color=discord.Color.blue()
            )

            # If we have newly eliminated, pick one at random to show as the thumbnail
            if newly_eliminated:
                chosen_elim_username = random.choice(newly_eliminated)
                try:
                    # Fetch the user to get their avatar
                    chosen_elim = next(p for p in updated_participants if p["username"] == chosen_elim_username)
                    user_obj = await interaction.client.fetch_user(int(chosen_elim["user_id"]))
                    if user_obj.avatar:
                        round_embed.set_thumbnail(url=user_obj.display_avatar.url)
                except Exception as e:
                    # Fallback to host avatar if fetching fails
                    host_user = await interaction.client.fetch_user(int(game["host_user_id"]))
                    if host_user and host_user.avatar:
                        round_embed.set_thumbnail(url=host_user.display_avatar.url)

            else:
                # No one eliminated => keep host's avatar or none
                host_user = await interaction.client.fetch_user(int(game["host_user_id"]))
                if host_user and host_user.avatar:
                    round_embed.set_thumbnail(url=host_user.display_avatar.url)

            await interaction.followup.send(embed=round_embed)
            await asyncio.sleep(5)  # Short delay before next round

    async def conclude_game_auto(self, interaction: discord.Interaction, game_doc: dict, guild_id: str, final_round: int) -> discord.Embed:
        """
        Concludes the auto-run session by declaring the sole remaining player as the winner.
        If all players are eliminated, randomly select one participant as the winner.
        """
        squib_game_sessions.update_one(
            {"_id": game_doc["_id"]},
            {"$set": {"current_game_state": "completed"}}
        )

        participants = game_doc["participants"]
        alive_players = [p for p in participants if p["status"] == "alive"]
        total_alive = len(alive_players)

        embed = discord.Embed(title="Game Over! 🏆", color=discord.Color.gold())
        round_title = f"Final Round {final_round}"

        if total_alive == 1:
            winner = alive_players[0]
        elif total_alive > 1:
            # If multiple alive players (due to some minigame logic), randomly pick one
            winner = random.choice(alive_players)
        else:
            # All players eliminated, pick one randomly from all participants
            winner = random.choice(participants)

        # Increment the winner's wins
        new_wins = update_squib_game_stats(winner["user_id"], guild_id, win_increment=1)

        # Fetch the winner to get their avatar
        try:
            user_obj = await interaction.client.fetch_user(int(winner["user_id"]))
            if user_obj.avatar:
                embed.set_thumbnail(url=user_obj.display_avatar.url)
        except:
            pass  # If fetching fails, skip setting the thumbnail

        embed.description = (
            f"**{round_title}** concluded.\n\n"
            f"The winner is **{winner['username']}**! 🎉🏆\n\n"
            f"They now have **{new_wins} wins** in this server."
        )

        embed.set_footer(text="Thanks for playing Squib Game!")

        return embed

    # ----------------------------------
    # /squibgames status
    # ----------------------------------
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

        # To prevent overly long lists, we can summarize if needed
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
        host_user = await interaction.client.fetch_user(int(host_id))
        if host_user and host_user.avatar:
            embed.set_thumbnail(url=host_user.display_avatar.url)

        await interaction.response.send_message(embed=embed)

# ------------------------------------------------------
# Setup
# ------------------------------------------------------
async def setup(bot_client: commands.Bot):
    await bot_client.add_cog(SquibGames(bot_client))
