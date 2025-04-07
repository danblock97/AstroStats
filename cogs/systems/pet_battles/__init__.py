# cogs/systems/pet_battles/__init__.py
import os
import random
import asyncio
import logging
from datetime import datetime, timedelta, timezone, time as dtime
import aiohttp
import json
import logging
from typing import List, Dict, Any, Optional, Tuple # Added Tuple

import discord
from discord.ext import commands, tasks
from discord import app_commands, Interaction # Added Interaction
from pymongo import MongoClient
from bson import ObjectId # Import ObjectId
import topgg # Ensure topgg is imported

from core.utils import get_conditional_embed, create_progress_bar # Import create_progress_bar
from config.settings import MONGODB_URI, TOPGG_TOKEN
from ui.embeds import create_error_embed, create_success_embed # Use standardized embeds

from .petconstants import (
    INITIAL_STATS,
    PET_LIST,
    COLOR_LIST,
    SHOP_ITEMS, # Import shop items
    DAILY_COMPLETION_BONUS, # Import daily bonus
    DAILY_QUESTS
)
from .petstats import (
    calculate_xp_needed,
    check_level_up,
    create_xp_bar # Keep this specific one if needed, or use core.utils one
)
from .petquests import (
    assign_daily_quests,
    assign_achievements,
    ensure_quests_and_achievements,
    update_quests_and_achievements
)
from .petbattle import calculate_damage, get_active_buff # Import buff getter

logger = logging.getLogger("PetBattlesCog")

mongo_client = MongoClient(MONGODB_URI)
db = mongo_client['astrostats_database']
pets_collection = db['pets']
battle_logs_collection = db['battle_logs']

# --- Helper Functions ---
def format_currency(amount: int) -> str:
    """Formats an integer as currency."""
    return f"🪙 {amount:,}"

def get_pet_document(user_id: str, guild_id: str) -> Optional[Dict[str, Any]]:
    """Fetches the pet document from the database."""
    return pets_collection.find_one({"user_id": user_id, "guild_id": guild_id})

def update_pet_document(pet: Dict[str, Any]):
    """Updates the pet document in the database."""
    pet_id = pet.get('_id')
    if pet_id is None:
        logger.error(f"Attempted to update pet without _id for user {pet.get('user_id')}")
        return False

    # Ensure _id is ObjectId before updating
    if not isinstance(pet_id, ObjectId):
        try:
            pet_id = ObjectId(pet_id)
        except Exception:
            logger.error(f"Could not convert pet_id {pet_id} to ObjectId during update.")
            return False

    # Remove _id before $set to avoid modifying it
    update_data = pet.copy()
    del update_data['_id']

    result = pets_collection.update_one({"_id": pet_id}, {"$set": update_data})
    return result.modified_count > 0

# --- Cog Definition ---
class PetBattles(commands.GroupCog, name="petbattles"):
    """Commands for the Pet Battles mini-game."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reset_daily_quests.start()
        self.topgg_client = None
        # --- FIX: Store the token directly on the instance ---
        self.topgg_token = TOPGG_TOKEN # Store the imported token
        # --- End FIX ---
        if self.topgg_token: # Use the stored token for the check
            self.bot.loop.create_task(self.initialize_topgg_client())
        else:
            logger.warning("Top.gg token not found. Voting features disabled.")

    async def initialize_topgg_client(self):
        """Initializes the Top.gg client."""
        # Use the stored token
        if not self.topgg_token:
            logger.error("Top.gg token is not configured. Voting functionality will not work.")
            return
        try:
            # Pass autopost=True if you want the library to handle posting server count
            # Use the stored token here as well
            self.topgg_client = topgg.DBLClient(self.bot, self.topgg_token, autopost=True)
            logger.info("Top.gg client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialise Top.gg client: {e}", exc_info=True)
            self.topgg_client = None # Ensure client is None if init fails

    async def check_user_vote(self, user_id: int) -> bool:
        """
        Checks if a user has voted on Top.gg using a direct API call.

        Args:
            user_id: The Discord user ID.

        Returns:
            True if the user has voted, False otherwise.
        """
        # --- Pre-checks ---
        if not self.topgg_token:
            logger.error("Cannot perform Top.gg API call: Top.gg token is missing.")
            return False

        if not self.bot or not self.bot.user or not self.bot.user.id:
             logger.error("Cannot perform Top.gg API call: Bot information is missing.")
             return False

        # --- Direct API Call using aiohttp ---
        try:
            base_url = "https://top.gg/api"
            headers = {"Authorization": self.topgg_token} # Use the stored token
            url = f"{base_url}/bots/{self.bot.user.id}/check?userId={user_id}" # Use bot ID and user ID

            logger.debug(f"Making direct API call to {url} for user {user_id}")
            # Consider using a shared session if this function is called often
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    logger.debug(f"Received status {resp.status} for user {user_id}")

                    if resp.status == 200:
                        try:
                            data = await resp.json()
                            logger.debug(f"Received data: {data} for user {user_id}")
                            # The API returns {"voted": 0 or 1}
                            voted_status = data.get("voted", 0) # Default to 0 if key missing
                            return bool(voted_status)
                        except aiohttp.ContentTypeError:
                            # Handle cases where response is not valid JSON
                            raw_response = await resp.text()
                            logger.error(f"Top.gg API returned non-JSON response for user {user_id}. Status: {resp.status}. Response: {raw_response[:200]}")
                            return False
                        except Exception as json_err:
                            logger.error(f"Error parsing JSON response for user {user_id}. Status: {resp.status}. Error: {json_err}", exc_info=True)
                            return False
                    elif resp.status == 401:
                         logger.error(f"Top.gg API returned 401 Unauthorized. Check your TOPGG_TOKEN.")
                         return False
                    elif resp.status == 404:
                         logger.warning(f"Top.gg API returned 404 Not Found for user {user_id}. Assuming not voted.")
                         return False
                    elif resp.status == 429:
                         logger.warning(f"Top.gg API rate limit hit while checking user {user_id}.")
                         # Depending on policy, might want to return False or raise an exception
                         return False
                    else:
                        # Handle other unexpected HTTP errors
                        raw_response = await resp.text()
                        logger.error(f"Top.gg API returned unexpected status {resp.status} for user {user_id}. Response: {raw_response[:200]}")
                        return False
        except aiohttp.ClientError as http_err:
            logger.error(f"Network error during API call for user {user_id}: {http_err}", exc_info=True)
            return False
        except Exception as err:
            # Catch any other unexpected errors during the API call
            logger.exception(f"Unexpected error during vote check for user {user_id}: {err}")
            return False

    @tasks.loop(time=dtime(hour=0, minute=0, tzinfo=timezone.utc))
    async def reset_daily_quests(self):
        """Resets daily quests for all pets at midnight UTC."""
        logger.info("Starting daily quest reset...")
        try:
            # Find all pets. Use a cursor to handle potentially large numbers.
            all_pets_cursor = pets_collection.find({})
            updated_count = 0
            for pet in all_pets_cursor:
                # Ensure _id is ObjectId
                pet_id = pet.get('_id')
                if pet_id is None: continue
                if not isinstance(pet_id, ObjectId):
                    try: pet_id = ObjectId(pet_id)
                    except Exception: continue # Skip invalid IDs

                # Assign new quests and reset bonus flag
                new_quests = []
                random_daily_quests = random.sample(DAILY_QUESTS, 3)
                for quest in random_daily_quests:
                       new_quests.append({
                           "id": quest["id"],
                           "description": quest["description"],
                           "progress_required": quest["progress_required"],
                           "progress": 0,
                           "completed": False,
                           "xp_reward": quest["xp_reward"],
                           "cash_reward": quest["cash_reward"]
                       })

                update_result = pets_collection.update_one(
                    {"_id": pet_id},
                    {"$set": {"daily_quests": new_quests, "claimed_daily_completion_bonus": False}}
                )
                if update_result.modified_count > 0:
                    updated_count += 1

            logger.info(f"Daily quest reset completed. Updated {updated_count} pets.")
        except Exception as e:
            logger.error(f"Error during daily quest reset task: {e}", exc_info=True)

    @reset_daily_quests.before_loop
    async def before_reset_daily_quests(self):
        await self.bot.wait_until_ready() # Ensure bot is ready before starting the loop
        logger.info("Daily quest reset task ready.")


    @app_commands.command(name="summon", description="Summon a new pet to join your adventures!")
    @app_commands.describe(name="Give your new companion a name", pet="Choose the type of your pet")
    @app_commands.choices(
        pet=[
            app_commands.Choice(name="Lion 🦁", value="lion"),
            app_commands.Choice(name="Dog 🐶", value="dog"),
            app_commands.Choice(name="Cat 🐱", value="cat"),
            app_commands.Choice(name="Tiger 🐯", value="tiger"),
            app_commands.Choice(name="Rhino 🦏", value="rhino"),
            app_commands.Choice(name="Panda 🐼", value="panda"),
            app_commands.Choice(name="Red Panda <:red_panda:123>", value="red panda"), # Example custom emoji if available - MAKE SURE ID IS CORRECT
            app_commands.Choice(name="Fox 🦊", value="fox"),
        ]
    )
    async def summon(self, interaction: Interaction, name: str, pet: app_commands.Choice[str]):
        """Summons a new pet for the user in the current server."""
        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild.id)

        try:
            if get_pet_document(user_id, guild_id):
                embed = create_error_embed(
                    title="Summon Failed",
                    description=f"{interaction.user.mention}, you already have a pet in this server!"
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if len(name) > 32: # Discord embed field value limit is 1024, but keep names reasonable
                 embed = create_error_embed(
                     title="Summon Failed",
                     description="Pet name cannot be longer than 32 characters."
                 )
                 await interaction.response.send_message(embed=embed, ephemeral=True)
                 return

            random_color_name = random.choice(list(COLOR_LIST.keys()))
            random_color_hex = COLOR_LIST[random_color_name]

            # Create the pet data including new fields
            new_pet_data = {
                "user_id": user_id,
                "guild_id": guild_id,
                "name": name,
                "icon": PET_LIST[pet.value],
                "color": random_color_hex,
                **INITIAL_STATS, # Includes balance: 0, active_items: []
                "killstreak": 0,
                "loss_streak": 0,
                "daily_quests": [],
                "achievements": [],
                "last_vote_reward_time": None,
                "claimed_daily_completion_bonus": False
            }

            # Insert into DB first to get the _id
            result = pets_collection.insert_one(new_pet_data)
            new_pet_data['_id'] = result.inserted_id # Store the ObjectId

            # Assign initial quests and achievements using the data with _id
            # These functions now need to handle the update internally or return the modified dict
            # Assuming they modify and save internally based on the original code's comment
            assign_daily_quests(new_pet_data) # Pass the dict, assume it modifies and saves
            assign_achievements(new_pet_data) # Pass the dict, assume it modifies and saves
            # Fetch the latest data after assignment functions might have updated it
            new_pet_data = get_pet_document(user_id, guild_id)
            if not new_pet_data: # Check if fetch failed
                 logger.error(f"Failed to fetch pet data after assignment for user {user_id}")
                 # Handle error appropriately, maybe send an error message
                 embed = create_error_embed("Summon Error", "Failed to initialize pet data. Please try again.")
                 await interaction.response.send_message(embed=embed, ephemeral=True)
                 return


            # --- Create Success Embed ---
            embed = discord.Embed(
                title=f"✨ Pet Summoned: {name} ✨",
                description=f"Welcome, {name} the {pet.name}! Get ready for adventure!",
                color=random_color_hex
            )
            embed.set_thumbnail(url=new_pet_data['icon'])

            # Add stats fields using code blocks for better alignment
            stats_text = (
                f"```\n"
                f"Level    : {new_pet_data['level']}\n"
                f"Health   : {new_pet_data['health']}\n"
                f"Strength : {new_pet_data['strength']}\n"
                f"Defense  : {new_pet_data['defense']}\n"
                f"Balance  : {format_currency(new_pet_data['balance'])}\n" # Format balance
                f"```"
            )
            embed.add_field(name="📊 Base Stats", value=stats_text, inline=False)

            embed.add_field(
                name="➡️ Next Steps",
                value="Use `/petbattles stats` to see details.\n"
                      "Use `/petbattles battle @user` to fight!\n"
                      "Use `/petbattles shop` to buy items.",
                inline=False
            )

            embed.timestamp = datetime.now(timezone.utc)
            embed.set_footer(text="Let the Pet Battles begin!")

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            logger.error(f"Error in summon command for user {user_id}: {e}", exc_info=True)
            embed = create_error_embed(
                title="Summon Error",
                description="An unexpected error occurred while summoning your pet. Please try again later."
            )
            # Use followup if interaction already responded (e.g., defer)
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command(name="stats", description="View your pet's detailed statistics and status")
    async def stats(self, interaction: Interaction):
        """Displays the user's pet stats, including balance and active items."""
        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild.id)
        try:
            pet = get_pet_document(user_id, guild_id)

            if not pet:
                embed = create_error_embed(
                    title="No Pet Found",
                    description=(f"{interaction.user.mention}, you don't have a pet in this server. "
                                 "Summon one with `/petbattles summon`!")
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Ensure pet has all necessary fields (for backward compatibility)
            pet = ensure_quests_and_achievements(pet) # Assume this returns the updated pet dict

            xp_needed = calculate_xp_needed(pet['level'])
            xp_bar = create_xp_bar(pet['xp'], xp_needed) # Use the function from petstats

            embed = discord.Embed(
                title=f"{interaction.user.display_name}'s Pet: {pet['name']}",
                color=pet.get('color', discord.Color.blue()) # Use .get for safety
            )
            embed.set_thumbnail(url=pet['icon'])

            # --- Core Stats Field ---
            core_stats_text = (
                f"```\n"
                f"Level    : {pet['level']}\n"
                f"XP       : {pet['xp']}/{xp_needed}\n"
                f"{xp_bar}\n"
                f"Health   : {pet['health']} HP\n"
                f"Strength : {pet['strength']}\n"
                f"Defense  : {pet['defense']}\n"
                f"Balance  : {format_currency(pet['balance'])}\n" # Format balance
                f"```"
            )
            embed.add_field(name="📊 Core Stats", value=core_stats_text, inline=False)

            # --- Streaks Field ---
            streaks_text = ""
            if pet.get('killstreak', 0) > 0:
                streaks_text += f"🔥 Killstreak: {pet['killstreak']}\n"
            if pet.get('loss_streak', 0) > 0:
                streaks_text += f"🧊 Loss Streak: {pet['loss_streak']}\n"
            if not streaks_text:
                streaks_text = "No active streaks."

            embed.add_field(name="📈 Streaks", value=streaks_text, inline=True)

             # --- Active Items/Buffs Field ---
            active_items = pet.get('active_items', [])
            if active_items:
                items_text_lines = []
                for item in active_items:
                     # Ensure battles_remaining is an int
                     try:
                         battles_remaining = int(item.get('battles_remaining', 0))
                     except (ValueError, TypeError):
                         battles_remaining = 0

                     items_text_lines.append(
                         f"- {item.get('name', 'Unknown Item')}: "
                         f"+{item.get('value', 0)} {item.get('stat', '?').capitalize()} "
                         f"({battles_remaining} battles left)"
                     )
                items_text = "\n".join(items_text_lines)
                embed.add_field(name="✨ Active Buffs", value=items_text, inline=False)
            else:
                embed.add_field(name="✨ Active Buffs", value="No active buffs.", inline=False)


            embed.timestamp = datetime.now(timezone.utc)
            embed.set_footer(text="Use /petbattles help for more commands.")

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            logger.error(f"Error in stats command for user {user_id}: {e}", exc_info=True)
            embed = create_error_embed(
                title="Stats Error",
                description="An error occurred while fetching your pet's stats. Please try again later."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command(name="battle", description="Challenge another user's pet to a battle!")
    @app_commands.describe(opponent="The user whose pet you want to battle")
    async def battle(self, interaction: Interaction, opponent: discord.Member):
        """Initiates a battle between the user's pet and the opponent's pet."""
        user_id = str(interaction.user.id)
        opponent_id = str(opponent.id)
        guild_id = str(interaction.guild.id)

        battle_message: Optional[discord.WebhookMessage] = None # To store the message for editing

        try:
            # --- Initial Checks ---
            if user_id == opponent_id:
                embed = create_error_embed("Battle Error", "You cannot battle yourself!")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if opponent.bot:
                embed = create_error_embed("Battle Error", "You cannot battle bots.")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            user_pet = get_pet_document(user_id, guild_id)
            opponent_pet = get_pet_document(opponent_id, guild_id)

            if not user_pet:
                embed = create_error_embed(
                    "No Pet Found",
                    f"{interaction.user.mention}, you need a pet! Use `/petbattles summon`."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if not opponent_pet:
                embed = create_error_embed(
                    "Opponent Has No Pet",
                    f"{opponent.mention} doesn't have a pet in this server."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Ensure pets have necessary fields
            user_pet = ensure_quests_and_achievements(user_pet)
            opponent_pet = ensure_quests_and_achievements(opponent_pet)

            # Level difference check (optional, adjust as needed)
            level_diff = abs(user_pet['level'] - opponent_pet['level'])
            if level_diff > 5: # Allow battling pets within 5 levels
                embed = create_error_embed(
                    "Battle Error",
                    "You can only battle pets within 5 levels of your own."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Battle cooldown check (5 battles per opponent per day)
            now = datetime.now(timezone.utc)
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            recent_battles_count = battle_logs_collection.count_documents({
                "$or": [
                     {"user_id": user_id, "opponent_id": opponent_id},
                     {"user_id": opponent_id, "opponent_id": user_id} # Count battles initiated by either
                ],
                "guild_id": guild_id,
                "timestamp": {"$gte": start_of_day}
            })

            BATTLE_LIMIT = 5
            if recent_battles_count >= BATTLE_LIMIT:
                embed = create_error_embed(
                    "Battle Limit Reached",
                    (f"You and {opponent.display_name} have already battled {BATTLE_LIMIT} times today "
                     f"in this server. Please try again tomorrow.")
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Log the battle attempt (before the actual fight)
            battle_logs_collection.insert_one({
                "user_id": user_id,
                "opponent_id": opponent_id,
                "guild_id": guild_id,
                "timestamp": now
            })

            # --- Battle Setup ---
            await interaction.response.defer() # Defer response as battle takes time

            # Calculate initial health considering buffs
            user_max_health = user_pet['health'] + get_active_buff(user_pet.get('active_items', []), 'health')
            opponent_max_health = opponent_pet['health'] + get_active_buff(opponent_pet.get('active_items', []), 'health')
            user_current_health = user_max_health
            opponent_current_health = opponent_max_health

            # Store initial stats for quest tracking
            user_battle_stats = {"damage_dealt": 0, "critical_hits": 0, "lucky_hits": 0, "battles_won": 0, "battles_lost": 0, "xp_earned": 0}
            opponent_battle_stats = {"damage_dealt": 0, "critical_hits": 0, "lucky_hits": 0, "battles_won": 0, "battles_lost": 0, "xp_earned": 0}

            # --- Initial Battle Embed ---
            embed = discord.Embed(
                title=f"⚔️ Battle Starting: {user_pet['name']} vs {opponent_pet['name']} ⚔️",
                description="The pets face off! Prepare for battle...",
                color=discord.Color.orange()
            )
            embed.add_field(name=f"{interaction.user.display_name}'s {user_pet['name']}", value=f"HP: {user_current_health}/{user_max_health}", inline=True)
            embed.add_field(name=f"{opponent.display_name}'s {opponent_pet['name']}", value=f"HP: {opponent_current_health}/{opponent_max_health}", inline=True)
            embed.set_thumbnail(url=user_pet['icon'])
            # embed.set_image(url=opponent_pet['icon']) # Maybe too large, thumbnail is often enough
            battle_message = await interaction.followup.send(embed=embed)
            await asyncio.sleep(3) # Pause for suspense

            # --- Battle Loop ---
            round_number = 1
            battle_log_text = ""
            winner = None
            loser = None
            winner_owner = None # Added initialization
            loser_owner = None # Added initialization

            while user_current_health > 0 and opponent_current_health > 0:
                round_log_entry = f"\n\n**--- Round {round_number} ---**\n"

                # User attacks opponent
                user_damage, user_crit, user_event = calculate_damage(user_pet, opponent_pet)
                opponent_current_health -= user_damage
                opponent_current_health = max(0, opponent_current_health) # Ensure health doesn't go below 0
                user_battle_stats['damage_dealt'] += user_damage

                attack_desc = f"{user_pet['name']} attacks {opponent_pet['name']}!"
                if user_event == "luck":
                    user_battle_stats['lucky_hits'] += 1
                    attack_desc += f" ✨ **Lucky Hit!** Deals **{user_damage}** damage!"
                elif user_crit:
                    user_battle_stats['critical_hits'] += 1
                    attack_desc += f" 💥 **Critical Hit!** Deals **{user_damage}** damage!"
                else:
                    attack_desc += f" Deals **{user_damage}** damage."
                round_log_entry += attack_desc + "\n"

                if opponent_current_health <= 0:
                    winner = user_pet
                    loser = opponent_pet
                    winner_owner = interaction.user
                    loser_owner = opponent
                    break # Exit loop, user wins

                # Opponent attacks user
                opponent_damage, opponent_crit, opponent_event = calculate_damage(opponent_pet, user_pet)
                user_current_health -= opponent_damage
                user_current_health = max(0, user_current_health) # Ensure health doesn't go below 0
                opponent_battle_stats['damage_dealt'] += opponent_damage

                attack_desc = f"{opponent_pet['name']} attacks {user_pet['name']}!"
                if opponent_event == "luck":
                    opponent_battle_stats['lucky_hits'] += 1
                    attack_desc += f" ✨ **Lucky Hit!** Deals **{opponent_damage}** damage!"
                elif opponent_crit:
                    opponent_battle_stats['critical_hits'] += 1
                    attack_desc += f" 💥 **Critical Hit!** Deals **{opponent_damage}** damage!"
                else:
                    attack_desc += f" Deals **{opponent_damage}** damage."
                round_log_entry += attack_desc + "\n"

                if user_current_health <= 0:
                    winner = opponent_pet
                    loser = user_pet
                    winner_owner = opponent
                    loser_owner = interaction.user
                    break # Exit loop, opponent wins

                # Update embed with round results
                battle_log_text += round_log_entry
                embed.description = battle_log_text[-1900:] # Keep description length reasonable
                embed.set_field_at(0, name=f"{interaction.user.display_name}'s {user_pet['name']}", value=f"HP: {user_current_health}/{user_max_health}", inline=True)
                embed.set_field_at(1, name=f"{opponent.display_name}'s {opponent_pet['name']}", value=f"HP: {opponent_current_health}/{opponent_max_health}", inline=True)
                await battle_message.edit(embed=embed)

                round_number += 1
                await asyncio.sleep(2.5) # Pause between rounds

            # --- Battle Conclusion ---
            if not winner or not loser or not winner_owner or not loser_owner: # Check owner variables too
                 # Should not happen in normal flow, but handle defensively
                 logger.error(f"Battle concluded without a clear winner/loser/owner between {user_id} and {opponent_id}")
                 await battle_message.edit(embed=create_error_embed("Battle Error", "An unexpected error occurred determining the winner."))
                 return

            # Update streaks and battle stats
            winner_battle_stats = user_battle_stats if winner == user_pet else opponent_battle_stats
            loser_battle_stats = opponent_battle_stats if loser == opponent_pet else user_battle_stats
            winner_battle_stats['battles_won'] += 1
            loser_battle_stats['battles_lost'] += 1

            winner['killstreak'] = winner.get('killstreak', 0) + 1
            winner['loss_streak'] = 0
            loser['killstreak'] = 0
            loser['loss_streak'] = loser.get('loss_streak', 0) + 1

            # Calculate XP gains (more for winner, less for loser)
            winner_xp_gain = random.randint(75, 150) + (winner['level'] * 5) # Scale slightly with level
            loser_xp_gain = random.randint(25, 75) + (loser['level'] * 2)
            winner['xp'] += winner_xp_gain
            loser['xp'] += loser_xp_gain
            winner_battle_stats['xp_earned'] = winner_xp_gain
            loser_battle_stats['xp_earned'] = loser_xp_gain

            # Process item duration decay
            for item in winner.get('active_items', []):
                item['battles_remaining'] = max(0, item.get('battles_remaining', 0) - 1)
            for item in loser.get('active_items', []):
                item['battles_remaining'] = max(0, item.get('battles_remaining', 0) - 1)
            # Filter out expired items
            winner['active_items'] = [item for item in winner.get('active_items', []) if item.get('battles_remaining', 0) > 0]
            loser['active_items'] = [item for item in loser.get('active_items', []) if item.get('battles_remaining', 0) > 0]

            # Update quests and achievements - Assume these functions handle DB updates or return updated dicts
            completed_quests_winner, completed_achievements_winner, daily_bonus_winner = update_quests_and_achievements(winner, winner_battle_stats)
            completed_quests_loser, completed_achievements_loser, daily_bonus_loser = update_quests_and_achievements(loser, loser_battle_stats)

            # Check for level ups - Assume these functions handle DB updates or return updated dicts
            winner, winner_leveled_up = check_level_up(winner)
            loser, loser_leveled_up = check_level_up(loser)

            # Save updated pet data to DB (if not handled by above functions)
            # If check_level_up and update_quests return the modified dicts, update here:
            update_pet_document(winner)
            update_pet_document(loser)

            # --- Final Battle Embed ---
            result_embed = discord.Embed(
                title=f"🏆 Battle Over: {winner['name']} is Victorious! 🏆",
                description=f"{winner_owner.mention}'s **{winner['name']}** defeated {loser_owner.mention}'s **{loser['name']}**!",
                color=winner.get('color', discord.Color.gold())
            )
            result_embed.set_thumbnail(url=winner['icon'])

            # Rewards Section
            rewards_text = (
                f"**{winner_owner.display_name} ({winner['name']}):**\n"
                f"+{winner_xp_gain} XP\n"
            )
            if winner_leveled_up: rewards_text += f"🎉 **Leveled up to Level {winner['level']}!**\n"
            rewards_text += (
                f"\n**{loser_owner.display_name} ({loser['name']}):**\n"
                f"+{loser_xp_gain} XP\n"
            )
            if loser_leveled_up: rewards_text += f"🎉 **Leveled up to Level {loser['level']}!**\n"
            result_embed.add_field(name="🌟 Rewards", value=rewards_text, inline=False)

            # Quest/Achievement Completion Section
            completions_text = ""
            if completed_quests_winner or completed_achievements_winner or daily_bonus_winner:
                completions_text += f"**{winner_owner.display_name}'s Completions:**\n"
                for q in completed_quests_winner: completions_text += f"📝 Quest: {q['description']} (+{q['xp_reward']} XP, +{format_currency(q['cash_reward'])})\n"
                for a in completed_achievements_winner: completions_text += f"🏆 Achievement: {a['description']} (+{a['xp_reward']} XP, +{format_currency(a['cash_reward'])})\n"
                if daily_bonus_winner: completions_text += f"📅 Daily Bonus! (+{DAILY_COMPLETION_BONUS['xp']} XP, +{format_currency(DAILY_COMPLETION_BONUS['cash'])})\n"
            if completed_quests_loser or completed_achievements_loser or daily_bonus_loser:
                 completions_text += f"\n**{loser_owner.display_name}'s Completions:**\n"
                 for q in completed_quests_loser: completions_text += f"📝 Quest: {q['description']} (+{q['xp_reward']} XP, +{format_currency(q['cash_reward'])})\n"
                 for a in completed_achievements_loser: completions_text += f"🏆 Achievement: {a['description']} (+{a['xp_reward']} XP, +{format_currency(a['cash_reward'])})\n"
                 if daily_bonus_loser: completions_text += f"📅 Daily Bonus! (+{DAILY_COMPLETION_BONUS['xp']} XP, +{format_currency(DAILY_COMPLETION_BONUS['cash'])})\n"

            if completions_text:
                result_embed.add_field(name="🎯 Progress", value=completions_text, inline=False)

            result_embed.timestamp = datetime.now(timezone.utc)
            result_embed.set_footer(text="Battle concluded.")

            await battle_message.edit(embed=result_embed)

        except Exception as e:
            logger.error(f"Error in battle command between {user_id} and {opponent_id}: {e}", exc_info=True)
            error_embed = create_error_embed(
                "Battle Error",
                "An unexpected error occurred during the battle. Please try again later."
            )
            try:
                # Try to edit the existing message if possible, otherwise send new
                if battle_message:
                    await battle_message.edit(embed=error_embed, view=None) # Clear view if any
                elif interaction.response.is_done():
                    await interaction.followup.send(embed=error_embed, ephemeral=True)
                else:
                    # This case should be rare due to defer, but handle it
                     await interaction.response.send_message(embed=error_embed, ephemeral=True)
            except Exception as followup_e:
                 logger.error(f"Failed to send battle error message: {followup_e}")


    @app_commands.command(name="quests", description="View your current daily quests and progress")
    async def quests(self, interaction: Interaction):
        """Displays the user's active daily quests."""
        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild.id)
        try:
            pet = get_pet_document(user_id, guild_id)

            if not pet:
                embed = create_error_embed(
                    "No Pet Found",
                    f"{interaction.user.mention}, you need a pet! Use `/petbattles summon`."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            pet = ensure_quests_and_achievements(pet) # Ensure quests are assigned

            # Check if all quests are complete
            incomplete_quests = [q for q in pet.get('daily_quests', []) if not q.get('completed', False)]
            all_complete = not incomplete_quests
            bonus_claimed = pet.get('claimed_daily_completion_bonus', False)

            embed = discord.Embed(title="📅 Your Daily Quests", color=discord.Color.blue())
            embed.set_thumbnail(url=pet.get('icon')) # Add pet icon

            if not pet.get('daily_quests'):
                 embed.description = "You currently have no daily quests assigned. They reset daily at midnight UTC."
            elif all_complete:
                 now = datetime.now(timezone.utc)
                 # Calculate time until next reset (midnight UTC)
                 today_midnight = datetime.combine(now.date(), dtime(0, 0, tzinfo=timezone.utc))
                 next_reset = today_midnight if now < today_midnight else today_midnight + timedelta(days=1)
                 # Ensure next_reset is always in the future if exactly midnight
                 if next_reset <= now:
                     next_reset += timedelta(days=1)

                 time_until_reset = next_reset - now
                 hours, remainder = divmod(int(time_until_reset.total_seconds()), 3600)
                 minutes, _ = divmod(remainder, 60)
                 time_str = f"{hours}h {minutes}m" if hours > 0 or minutes > 0 else "soon"

                 bonus_message = ('Bonus already claimed.' if bonus_claimed
                  else f'Daily completion bonus of **{DAILY_COMPLETION_BONUS["xp"]} XP** and **{format_currency(DAILY_COMPLETION_BONUS["cash"])}** awarded!')

                 embed.description = (
                     f"🎉 **All daily quests completed!** 🎉\n"
                     f"{bonus_message}\n\n"  # Include the pre-formatted bonus message
                     f"New quests available in **{time_str}**."
                 )
                 embed.color = discord.Color.green()
            else:
                embed.description = "Complete these quests for rewards!"
                for quest in pet['daily_quests']:
                     progress_bar = create_progress_bar(quest.get('progress', 0), quest['progress_required'])
                     status_emoji = "✅" if quest.get('completed') else "⏳"
                     reward_str = f"(+{quest['xp_reward']} XP, +{format_currency(quest['cash_reward'])})"
                     embed.add_field(
                         name=f"{status_emoji} {quest['description']}",
                         value=f"`{quest.get('progress', 0)}/{quest['progress_required']}` {reward_str}\n{progress_bar}",
                         inline=False
                     )

            embed.timestamp = datetime.now(timezone.utc)
            embed.set_footer(text="Quests reset daily at midnight UTC.")

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            logger.error(f"Error in quests command for user {user_id}: {e}", exc_info=True)
            embed = create_error_embed("Quest Error", "An error occurred while fetching your quests.")
            await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command(name="achievements", description="View your long-term achievements and progress")
    async def achievements(self, interaction: Interaction):
        """Displays the user's achievements and their progress."""
        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild.id)
        try:
            pet = get_pet_document(user_id, guild_id)

            if not pet:
                embed = create_error_embed(
                    "No Pet Found",
                    f"{interaction.user.mention}, you need a pet! Use `/petbattles summon`."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            pet = ensure_quests_and_achievements(pet) # Ensure achievements are assigned
            achievements_list = pet.get('achievements', [])

            embed = discord.Embed(title="🏆 Your Achievements 🏆", color=discord.Color.gold())
            embed.set_thumbnail(url=pet.get('icon')) # Add pet icon
            embed.description = "Track your long-term progress and earn big rewards!"

            if not achievements_list:
                 embed.description = "No achievements found for your pet." # Should not happen with ensure
            else:
                for achievement in achievements_list:
                    progress = achievement.get('progress', 0)
                    required = achievement['progress_required']
                    is_completed = achievement.get('completed', False)

                    progress_bar = create_progress_bar(progress, required)
                    status_emoji = "✅" if is_completed else "⏳"
                    reward_str = f"(+{achievement['xp_reward']} XP, +{format_currency(achievement['cash_reward'])})"
                    status_text = "Completed!" if is_completed else f"`{progress}/{required}`"

                    embed.add_field(
                        name=f"{status_emoji} {achievement['description']}",
                        value=f"{status_text} {reward_str}\n{progress_bar}",
                        inline=False
                    )

            embed.timestamp = datetime.now(timezone.utc)
            embed.set_footer(text="Keep battling to unlock more!")

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            logger.error(f"Error in achievements command for user {user_id}: {e}", exc_info=True)
            embed = create_error_embed("Achievement Error", "An error occurred while fetching your achievements.")
            await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command(name="leaderboard", description="View the top pets in this server based on level and XP")
    async def leaderboard(self, interaction: Interaction):
        """Displays the top 10 pets in the server."""
        guild_id = str(interaction.guild.id)
        try:
            # Fetch top 10 pets sorted by level descending, then XP descending
            top_pets_cursor = pets_collection.find({"guild_id": guild_id}).sort(
                [("level", -1), ("xp", -1)]
            ).limit(10)

            top_pets_list = list(top_pets_cursor) # Convert cursor to list

            embed = discord.Embed(
                title=f"🏆 Top Pets Leaderboard - {interaction.guild.name} 🏆",
                color=discord.Color.gold() # Gold color for leaderboards
            )

            if not top_pets_list:
                embed.description = "No pets found in this server yet. Be the first!"
            else:
                leaderboard_entries = []
                # Using standard emojis for top 3, numbers for rest
                rank_emojis = ["🥇", "🥈", "🥉"]

                for index, pet in enumerate(top_pets_list):
                    try:
                        # Fetch user object - might fail if user left the server
                        user = await self.bot.fetch_user(int(pet['user_id']))
                        user_display_name = user.display_name
                    except (discord.NotFound, ValueError):
                        user_display_name = f"Unknown User ({pet['user_id'][-4:]})" # Show partial ID if user not found
                    except Exception as fetch_err:
                         logger.warning(f"Could not fetch user {pet['user_id']} for leaderboard: {fetch_err}")
                         user_display_name = "Error Fetching Name"


                    rank_display = rank_emojis[index] if index < len(rank_emojis) else f"{index+1}." # Use number if no emoji
                    entry = (
                        f"{rank_display} **{user_display_name}** (Pet: {pet.get('name', 'N/A')})\n"
                        f"> Level: `{pet['level']}` | XP: `{pet['xp']:,}` | Bal: `{format_currency(pet.get('balance', 0))}`"
                    )
                    leaderboard_entries.append(entry)

                embed.description = "\n\n".join(leaderboard_entries)
                # Set thumbnail to the #1 pet's icon if available
                if top_pets_list and top_pets_list[0].get('icon'):
                     embed.set_thumbnail(url=top_pets_list[0]['icon'])


            embed.timestamp = datetime.now(timezone.utc)
            embed.set_footer(text="Battle your way to the top!")

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            logger.error(f"Error in leaderboard command for guild {guild_id}: {e}", exc_info=True)
            embed = create_error_embed("Leaderboard Error", "An error occurred while fetching the leaderboard.")
            await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command(name="vote", description="Vote for AstroStats on Top.gg to earn rewards!")
    async def vote(self, interaction: Interaction):
        """Allows users to claim rewards for voting on Top.gg."""
        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild.id)
        bot_id = "1088929834748616785" # Your bot's ID on Top.gg
        vote_url = f"https://top.gg/bot/{bot_id}/vote"
        VOTE_REWARD_XP = 200 # Increased XP reward
        VOTE_REWARD_CASH = 100 # Added cash reward
        VOTE_COOLDOWN_HOURS = 12

        try:
            pet = get_pet_document(user_id, guild_id)
            if not pet:
                embed = create_error_embed(
                    "No Pet Found",
                    f"{interaction.user.mention}, you need a pet to claim vote rewards! Use `/petbattles summon`."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            pet = ensure_quests_and_achievements(pet) # Ensure fields exist

            # --- FIX: Check the stored token attribute ---
            if not self.topgg_token: # Check if token exists before proceeding
                embed = create_error_embed("Voting Unavailable", "The Top.gg connection is not configured correctly by the bot owner.")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            # --- End FIX ---

            # Check if user has voted
            await interaction.response.defer(ephemeral=True) # Defer as API call can take time
            # Pass the integer user ID to check_user_vote
            has_voted = await self.check_user_vote(int(user_id))

            if not has_voted:
                embed = discord.Embed(
                    title="🗳️ Vote for AstroStats!",
                    description=(f"You haven't voted recently!\n"
                                 f"Click [here]({vote_url}) to vote on Top.gg and then use this command again "
                                 f"to claim **{VOTE_REWARD_XP} XP** and **{format_currency(VOTE_REWARD_CASH)}**!"),
                    color=discord.Color.blue()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                # Check cooldown
                now = datetime.now(timezone.utc)
                last_reward_time_str = pet.get('last_vote_reward_time')
                can_claim = True
                time_left_str = ""

                if last_reward_time_str:
                    try:
                        # Ensure the stored string is timezone-aware if needed, or make 'now' naive
                        # Assuming stored time is UTC from isoformat()
                        last_reward_time = datetime.fromisoformat(last_reward_time_str)
                        # Ensure comparison is between offset-aware datetimes if needed
                        if last_reward_time.tzinfo is None:
                             last_reward_time = last_reward_time.replace(tzinfo=timezone.utc) # Assume UTC if naive

                        time_since_last = now - last_reward_time
                        if time_since_last < timedelta(hours=VOTE_COOLDOWN_HOURS):
                            can_claim = False
                            time_left = timedelta(hours=VOTE_COOLDOWN_HOURS) - time_since_last
                            hours, remainder = divmod(int(time_left.total_seconds()), 3600)
                            minutes, _ = divmod(remainder, 60)
                            time_left_str = f"{hours}h {minutes}m"
                    except ValueError:
                        logger.warning(f"Invalid ISO format for last_vote_reward_time for user {user_id}: {last_reward_time_str}")
                        # Allow claiming if the stored time is invalid

                if not can_claim:
                    embed = create_error_embed(
                        "Vote Cooldown Active",
                        f"You've already claimed your vote reward recently. Please wait **{time_left_str}**."
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    # Grant rewards
                    pet['xp'] += VOTE_REWARD_XP
                    pet['balance'] = pet.get('balance', 0) + VOTE_REWARD_CASH
                    pet['last_vote_reward_time'] = now.isoformat() # Store timestamp

                    pet, leveled_up = check_level_up(pet) # Assume returns updated dict
                    update_pet_document(pet) # Save changes

                    embed = create_success_embed(
                        "🎉 Thank You for Voting! 🎉",
                        (f"You received **{VOTE_REWARD_XP} XP** and **{format_currency(VOTE_REWARD_CASH)}**!\n"
                         f"Your new balance is {format_currency(pet['balance'])}.")
                    )
                    if leveled_up:
                        embed.add_field(name="🌟 Level Up! 🌟", value=f"Your pet reached **Level {pet['level']}**!", inline=False)

                    await interaction.followup.send(embed=embed, ephemeral=True) # Send reward confirmation privately

        except Exception as e:
            logger.error(f"Error in vote command for user {user_id}: {e}", exc_info=True)
            embed = create_error_embed("Vote Error", "An error occurred while processing your vote.")
            # Use followup if deferred
            if interaction.response.is_done():
                 await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                 await interaction.response.send_message(embed=embed, ephemeral=True)


    # --- Shop Command ---
    @app_commands.command(name="shop", description="Browse and purchase items for your pet")
    async def shop(self, interaction: Interaction):
        """Displays the pet shop items."""
        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild.id)

        pet = get_pet_document(user_id, guild_id)
        if not pet:
            embed = create_error_embed(
                "No Pet Found",
                f"{interaction.user.mention}, you need a pet to use the shop! Use `/petbattles summon`."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        pet = ensure_quests_and_achievements(pet) # Ensure balance field exists

        embed = discord.Embed(
            title="🛒 Pet Shop 🛒",
            description=f"Welcome! Spend your hard-earned cash on upgrades.\nYour Balance: **{format_currency(pet.get('balance', 0))}**",
            color=discord.Color.dark_green()
        )

        if not SHOP_ITEMS:
            embed.description += "\nThe shop is currently empty. Check back later!"
        else:
            for item_id, item_data in SHOP_ITEMS.items():
                embed.add_field(
                    name=f"{item_data.get('emoji', '❓')} {item_data['name']} - {format_currency(item_data['cost'])}",
                    value=(
                        f"{item_data['description']}\n"
                        f"*Effect: +{item_data['value']} {item_data['stat'].capitalize()} for {item_data['duration']} battles.*\n"
                        f"To buy: `/petbattles buy item_id:{item_id}`" # Show the ID needed for buying
                    ),
                    inline=False
                )

        embed.set_footer(text="Items provide temporary buffs for battles.")
        await interaction.response.send_message(embed=embed)

    # --- Buy Command (Separate for clarity) ---
    @app_commands.command(name="buy", description="Purchase an item from the pet shop")
    @app_commands.describe(item_id="The ID of the item to purchase (see /petbattles shop)")
    async def buy(self, interaction: Interaction, item_id: str):
        """Allows the user to buy an item from the shop."""
        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild.id)
        item_id = item_id.lower().strip() # Normalize item ID

        try:
            pet = get_pet_document(user_id, guild_id)
            if not pet:
                embed = create_error_embed("No Pet Found", "You need a pet to buy items.")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            pet = ensure_quests_and_achievements(pet) # Ensure fields exist

            # Find the item in the shop
            item_to_buy = SHOP_ITEMS.get(item_id)

            if not item_to_buy:
                embed = create_error_embed("Item Not Found", f"Could not find an item with ID `{item_id}`. Check `/petbattles shop` for valid IDs.")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Check balance
            cost = item_to_buy['cost']
            current_balance = pet.get('balance', 0)

            if current_balance < cost:
                embed = create_error_embed(
                    "Insufficient Funds",
                    f"You need **{format_currency(cost)}** to buy {item_to_buy['name']}, but you only have **{format_currency(current_balance)}**."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Process purchase
            pet['balance'] -= cost

            # Add item to active items
            # Ensure active_items is a list
            if not isinstance(pet.get('active_items'), list):
                 pet['active_items'] = []

            # Check if item already active (optional: decide if stacking is allowed)
            # For simplicity, let's overwrite/reset duration if bought again
            existing_item_index = -1
            for i, active_item in enumerate(pet['active_items']):
                if active_item.get('item_id') == item_id:
                    existing_item_index = i
                    break

            new_item_data = {
                "item_id": item_id,
                "name": item_to_buy['name'],
                "stat": item_to_buy['stat'],
                "value": item_to_buy['value'],
                "battles_remaining": item_to_buy['duration']
            }

            if existing_item_index != -1:
                 # Replace existing item (resets duration)
                 pet['active_items'][existing_item_index] = new_item_data
                 action_text = "Refreshed"
            else:
                 # Add new item
                 pet['active_items'].append(new_item_data)
                 action_text = "Purchased"


            # Save changes to DB
            if update_pet_document(pet):
                embed = create_success_embed(
                    f"Item {action_text}!",
                    (f"You spent **{format_currency(cost)}** and acquired **{item_to_buy['name']}**!\n"
                     f"Your new balance is **{format_currency(pet['balance'])}**.\n"
                     f"The buff will last for **{item_to_buy['duration']}** battles.")
                )
                await interaction.response.send_message(embed=embed)
            else:
                 # Rollback balance if DB update failed
                 pet['balance'] += cost # Add cost back
                 # We might not be able to save this rollback either, but log it
                 logger.error(f"Failed to save pet update after purchase for user {user_id}, item {item_id}. Balance potentially incorrect.")
                 embed = create_error_embed("Purchase Error", "Failed to save the purchase. Please try again.")
                 await interaction.response.send_message(embed=embed, ephemeral=True)


        except Exception as e:
            logger.error(f"Error in buy command for user {user_id}, item {item_id}: {e}", exc_info=True)
            embed = create_error_embed("Shop Error", "An unexpected error occurred while buying the item.")
            await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command(name="globalrank", description="See how your pet ranks globally")
    async def globalrank(self, interaction: Interaction):
        """Shows the user's pet rank in the global leaderboard."""
        user_id = str(interaction.user.id)
        try:
            pet = get_pet_document(user_id, str(interaction.guild.id))
            
            if not pet:
                embed = create_error_embed(
                    "No Pet Found",
                    f"{interaction.user.mention}, you need a pet! Use `/petbattles summon`."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Defer response as global ranking might take time
            await interaction.response.defer()
            
            # Get all pets sorted by level descending, then XP descending
            all_pets_cursor = pets_collection.find({}).sort(
                [("level", -1), ("xp", -1)]
            )
            
            all_pets_list = list(all_pets_cursor) # Convert cursor to list
            total_pets = len(all_pets_list)
            
            # Find user's pet rank
            user_pet_rank = None
            top_pets = []
            for index, ranked_pet in enumerate(all_pets_list):
                if index < 3:  # Get top 3 for display
                    top_pets.append(ranked_pet)
                    
                if ranked_pet.get('_id') == pet.get('_id'):
                    user_pet_rank = index + 1  # +1 because index is 0-based but ranks start at 1
                    if index >= 3:  # If user isn't in top 3, add their pet to the display list
                        ranked_pet['rank'] = user_pet_rank  # Add rank for later display
                        top_pets.append(ranked_pet)
            
            # Create embed
            embed = discord.Embed(
                title="🌍 Global Pet Rankings 🌍",
                description=f"Your pet **{pet['name']}** is ranked **#{user_pet_rank}** out of **{total_pets}** pets globally!",
                color=discord.Color.gold()
            )
            
            # Set thumbnail to user's pet icon
            embed.set_thumbnail(url=pet['icon'])
            
            # Top pets section (always shows top 3 and the user if not in top 3)
            rank_emojis = ["🥇", "🥈", "🥉"]
            
            embed.add_field(
                name="🏆 Top Pets",
                value="The best pets across all servers:",
                inline=False
            )
            
            for index, top_pet in enumerate(top_pets):
                try:
                    # Fetch user object
                    pet_user = await self.bot.fetch_user(int(top_pet['user_id']))
                    user_name = pet_user.display_name
                except (discord.NotFound, ValueError):
                    user_name = f"Unknown User ({top_pet['user_id'][-4:]})"
                except Exception:
                    user_name = "Error Fetching Name"
                
                # Determine if this is the user's pet
                is_user_pet = top_pet.get('_id') == pet.get('_id')
                
                # Use emojis for top 3, numbers for others
                if index < 3:
                    rank_display = rank_emojis[index]
                    rank_num = index + 1
                else:
                    # This should be the user's pet outside top 3
                    rank_display = f"#{top_pet.get('rank')}"
                    rank_num = top_pet.get('rank')
                
                # Highlight the user's pet
                pet_name_display = f"**{top_pet['name']}**" if is_user_pet else top_pet['name']
                user_name_display = f"**{user_name}**" if is_user_pet else user_name
                
                embed.add_field(
                    name=f"{rank_display} {pet_name_display}",
                    value=f"Level: {top_pet['level']} | XP: {top_pet['xp']:,}",
                    inline=True
                )
            
            embed.timestamp = datetime.now(timezone.utc)
            embed.set_footer(text="Battle to climb the global rankings!")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in globalrank command for user {user_id}: {e}", exc_info=True)
            embed = create_error_embed("Global Ranking Error", "An error occurred while fetching the global rankings.")
            
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)


# --- Setup Function ---
async def setup(bot: commands.Bot):
    """Adds the PetBattles cog to the bot."""
    await bot.add_cog(PetBattles(bot))
    logger.info("PetBattles Cog loaded.")

