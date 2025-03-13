import random
import asyncio
from datetime import datetime, timezone

import discord
from typing import Tuple

from utils.squib_game.database import squib_game_sessions, update_squib_game_stats
from utils.squib_game.minigames import play_minigame_logic, generate_flavor_text
from utils.squib_game.helpers import get_guild_avatar_url
from utils.embeds import get_conditional_embed

async def run_game_loop(bot, interaction, game_id: str, guild_id: str):
    """
    Runs the game loop until one winner remains.
    Sends round updates via interaction.followup.
    """
    while True:
        game = squib_game_sessions.find_one({"_id": game_id})
        current_round = game["current_round"]
        participants_before = game["participants"]
        alive_before = [p for p in participants_before if p["status"] == "alive"]
        if len(alive_before) < 1:
            winner = None
            final_embeds = await conclude_game_auto(bot, interaction, game, guild_id, current_round, winner=winner)
            await interaction.followup.send(embeds=final_embeds)
            break
        elif len(alive_before) == 1:
            winner = alive_before[0]
            final_embeds = await conclude_game_auto(bot, interaction, game, guild_id, current_round, winner=winner)
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
            except Exception:
                host_avatar = await get_guild_avatar_url(interaction.guild, int(game["host_user_id"]))
                if host_avatar:
                    round_embed.set_thumbnail(url=host_avatar)
        else:
            host_avatar = await get_guild_avatar_url(interaction.guild, int(game["host_user_id"]))
            if host_avatar:
                round_embed.set_thumbnail(url=host_avatar)
        await interaction.followup.send(embed=round_embed)
        await asyncio.sleep(10)

async def conclude_game_auto(bot, interaction, game_doc: dict, guild_id: str, final_round: int, winner=None) -> list:
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
    except Exception:
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
    conditional_embed = await get_conditional_embed(interaction, 'SQUIB_GAME_COMMANDS_EMBED', discord.Color.orange())
    embeds = [final_embed]
    if conditional_embed:
        embeds.append(conditional_embed)
    return embeds
def create_new_session(guild_id: str, user_id: str, display_name: str) -> Tuple[str, dict]:
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
                "username": display_name,
                "status": "alive"
            }
        ],
        "created_at": datetime.now(timezone.utc)
    }
    squib_game_sessions.insert_one(new_session_doc)
    return session_id, new_session_doc
