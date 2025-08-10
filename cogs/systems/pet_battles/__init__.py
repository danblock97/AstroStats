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
import asyncio # For retry delays
import aiohttp # For network error handling

from core.utils import get_conditional_embed, create_progress_bar # Import create_progress_bar
from services.premium import get_user_entitlements, invalidate_user_entitlements
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
    """Fetches the ACTIVE, unlocked pet document for the user in this guild.
    Falls back to any unlocked pet if none active. Enforces capacity first."""
    try:
        enforce_user_pet_capacity(user_id, guild_id)
    except Exception:
        pass
    active = pets_collection.find_one({
        "user_id": user_id,
        "guild_id": guild_id,
        "is_active": True,
        "is_locked": {"$ne": True}
    })
    if active:
        return active
    return pets_collection.find_one({
        "user_id": user_id,
        "guild_id": guild_id,
        "is_locked": {"$ne": True}
    })

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

# --- Multi-pet Helpers ---
def get_user_pets(user_id: str, guild_id: str) -> List[Dict[str, Any]]:
    """Return all pets for a user within a guild, newest first."""
    return list(pets_collection.find({"user_id": user_id, "guild_id": guild_id}).sort([("_id", -1)]))

def get_unlocked_user_pets(user_id: str, guild_id: str) -> List[Dict[str, Any]]:
    return list(pets_collection.find({
        "user_id": user_id,
        "guild_id": guild_id,
        "is_locked": {"$ne": True}
    }).sort([("_id", -1)]))

def count_user_pets(user_id: str, guild_id: str) -> int:
    return pets_collection.count_documents({"user_id": user_id, "guild_id": guild_id})

def count_unlocked_user_pets(user_id: str, guild_id: str) -> int:
    return pets_collection.count_documents({
        "user_id": user_id,
        "guild_id": guild_id,
        "is_locked": {"$ne": True}
    })

def get_active_pet_document(user_id: str, guild_id: str) -> Optional[Dict[str, Any]]:
    return pets_collection.find_one({"user_id": user_id, "guild_id": guild_id, "is_active": True})

def set_active_pet(user_id: str, guild_id: str, pet_id: ObjectId) -> bool:
    try:
        # Unset others
        pets_collection.update_many({"user_id": user_id, "guild_id": guild_id}, {"$set": {"is_active": False}})
        # Set selected
        result = pets_collection.update_one({"_id": pet_id, "user_id": user_id, "guild_id": guild_id}, {"$set": {"is_active": True}})
        return result.modified_count > 0
    except Exception:
        return False

def enforce_user_pet_capacity(user_id: str, guild_id: str) -> None:
    """Ensure the user does not exceed pet capacity.
    Soft-block extras by marking them as locked, keeping earliest pets unlocked.
    Keeps the first unlocked pet active.
    """
    from services.premium import get_user_entitlements
    try:
        ent = get_user_entitlements(user_id)
        extra = int(ent.get("extraPets", 0) or 0)
        capacity = max(1, 1 + extra)
    except Exception:
        capacity = 1

    # Priority order for kept pets: active first (if present), then most recently used, then earliest created
    pets_all = list(pets_collection.find({"user_id": user_id, "guild_id": guild_id}))
    # Add a stable key for creation time from _id
    def oid_time(p):
        try:
            return int(str(p.get("_id"))[:8], 16)
        except Exception:
            return 0
    # Default last_used to 0 to push to the end
    def last_used_ts(p):
        try:
            return int(p.get("last_used_ts", 0))
        except Exception:
            return 0
    pets_all_sorted = sorted(
        pets_all,
        key=lambda p: (
            0 if p.get("is_active") else 1,      # active first
            -last_used_ts(p),                      # most recently used next
            oid_time(p),                           # earliest created next
        )
    )
    total = len(pets_all_sorted)
    # Determine keep vs lock sets regardless of total
    to_keep = pets_all_sorted[:capacity]
    to_lock = pets_all_sorted[capacity:]
    keep_ids = [p.get("_id") for p in to_keep if p.get("_id")]
    lock_ids = [p.get("_id") for p in to_lock if p.get("_id")]

    if keep_ids:
        pets_collection.update_many({"user_id": user_id, "guild_id": guild_id}, {"$set": {"is_locked": True, "is_active": False}})
        pets_collection.update_many({"_id": {"$in": keep_ids}}, {"$set": {"is_locked": False}})
        # Ensure exactly one active among kept (earliest)
        pets_collection.update_one({"_id": keep_ids[0]}, {"$set": {"is_active": True}})
    elif lock_ids:
        # No keep ids (capacity somehow 0, though we force >=1) -> lock all
        pets_collection.update_many({"_id": {"$in": lock_ids}}, {"$set": {"is_locked": True, "is_active": False}})

# --- Cog Definition ---
class PetBattles(commands.GroupCog, name="petbattles"):
    """Commands for the Pet Battles mini-game."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reset_daily_quests.start()
        self.reset_daily_training.start()  # Start daily training reset task
        self.topgg_client = None
        # --- FIX: Store the token directly on the instance ---
        self.topgg_token = TOPGG_TOKEN # Store the imported token
        # Circuit breaker for TopGG failures
        self.topgg_failure_count = 0
        self.topgg_circuit_open = False
        self.topgg_last_failure_time = None
        self.topgg_circuit_timeout = 3600  # 1 hour in seconds
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
            from core.utils import handle_api_error
            
            # Use autopost=True to handle posting server count
            self.topgg_client = topgg.DBLClient(
                self.bot, 
                self.topgg_token, 
                autopost=True,
                # Add an error handler for the autopost
                post_shard_count=False
            )
            
            # Patch the client's _auto_post method to handle errors better
            original_auto_post = self.topgg_client._auto_post
            
            async def patched_auto_post():
                # Check circuit breaker state
                if self.topgg_circuit_open:
                    if self.topgg_last_failure_time:
                        time_since_failure = (datetime.now(timezone.utc) - self.topgg_last_failure_time).total_seconds()
                        if time_since_failure < self.topgg_circuit_timeout:
                            # Circuit still open, skip silently
                            return
                        else:
                            # Try to reset circuit breaker
                            logger.info("Attempting to reset TopGG circuit breaker after timeout")
                            self.topgg_circuit_open = False
                            self.topgg_failure_count = 0
                
                max_retries = 3
                base_delay = 5  # Increased base delay for network issues
                
                for attempt in range(max_retries + 1):
                    try:
                        await original_auto_post()
                        # Success - reset failure count
                        if self.topgg_failure_count > 0:
                            logger.info("TopGG autoposting recovered successfully")
                            self.topgg_failure_count = 0
                            self.topgg_circuit_open = False
                        return
                    except (aiohttp.ClientConnectorDNSError, aiohttp.ClientError) as e:
                        # Network/DNS specific errors - longer delays
                        self.topgg_failure_count += 1
                        self.topgg_last_failure_time = datetime.now(timezone.utc)
                        
                        if attempt == max_retries:
                            # Open circuit breaker after repeated DNS failures
                            if self.topgg_failure_count >= 5:
                                self.topgg_circuit_open = True
                                logger.warning(f"TopGG circuit breaker opened after {self.topgg_failure_count} failures. Disabling for {self.topgg_circuit_timeout/60:.0f} minutes.")
                            else:
                                logger.warning(f"TopGG autoposting failed due to network issues (attempt {self.topgg_failure_count}). Will retry later.")
                            return
                        
                        # Longer delay for network issues
                        delay = base_delay * (2 ** attempt)
                        await asyncio.sleep(delay)
                    except topgg.errors.ServerError as e:
                        # TopGG server errors - normal retry logic
                        if attempt == max_retries:
                            handle_api_error(e, f"TopGG server error after {max_retries + 1} attempts")
                            return
                        delay = base_delay * (2 ** attempt)
                        await asyncio.sleep(delay)
                    except Exception as e:
                        # Unexpected error, log it but don't crash the bot
                        handle_api_error(e, "Unexpected TopGG autoposting error")
                        return
            
            # Replace the method with our patched version
            self.topgg_client._auto_post = patched_auto_post
            
            logger.info("Top.gg client initialized successfully with improved error handling.")
        except Exception as e:
            from core.utils import handle_api_error
            handle_api_error(e, "Failed to initialize Top.gg client")
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
        except (aiohttp.ClientConnectorDNSError, aiohttp.ClientError) as http_err:
            # Update circuit breaker for network errors
            self.topgg_failure_count += 1
            self.topgg_last_failure_time = datetime.now(timezone.utc)
            if self.topgg_failure_count >= 5:
                self.topgg_circuit_open = True
                logger.warning(f"TopGG circuit breaker opened due to vote check failures. Count: {self.topgg_failure_count}")
            else:
                logger.warning(f"Network error during vote check for user {user_id}: {type(http_err).__name__}. Failure count: {self.topgg_failure_count}")
            return False
        except Exception as err:
            # Catch any other unexpected errors during the API call
            logger.exception(f"Unexpected error during vote check for user {user_id}: {err}")
            return False

    def reset_topgg_circuit_breaker(self):
        """Manually reset the TopGG circuit breaker (for admin use)."""
        self.topgg_circuit_open = False
        self.topgg_failure_count = 0
        self.topgg_last_failure_time = None
        logger.info("TopGG circuit breaker manually reset")

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
                # Determine number of daily quests by entitlements
                try:
                    ent = get_user_entitlements(str(pet.get('user_id', '')))
                    num_quests = 3 + int(ent.get('dailyPetQuestsBonus', 0))
                except Exception:
                    num_quests = 3
                num_quests = max(1, min(len(DAILY_QUESTS), num_quests))
                random_daily_quests = random.sample(DAILY_QUESTS, num_quests)
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
                    {"_id": pet_id, "is_locked": {"$ne": True}},
                    {"$set": {
                        "daily_quests": new_quests,
                        "claimed_daily_completion_bonus": False,
                        "voted_battle_bonus_active": False # Reset vote bonus flag
                    }}
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

    @tasks.loop(time=dtime(hour=0, minute=0, tzinfo=timezone.utc))
    async def reset_daily_training(self):
        """Resets daily training count for all pets at midnight UTC."""
        logger.info("Starting daily training reset...")
        try:
            # Use update_many to efficiently reset all pets' training count
            result = pets_collection.update_many(
                {"trainingCount": {"$exists": True}},  # Only update pets with the training field
                {"$set": {"trainingCount": 0, "lastTrainingReset": datetime.now(timezone.utc).isoformat()}}
            )
            logger.info(f"Daily training reset completed. Reset {result.modified_count} pets.")
        except Exception as e:
            logger.error(f"Error during daily training reset task: {e}", exc_info=True)

    @reset_daily_training.before_loop
    async def before_reset_daily_training(self):
        await self.bot.wait_until_ready()  # Ensure bot is ready before starting the loop
        logger.info("Daily training reset task ready.")


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
            app_commands.Choice(name="Red Panda 🦊", value="red panda"),  # Using fox emoji as placeholder
            app_commands.Choice(name="Fox 🦊", value="fox"),
        ]
    )
    async def summon(self, interaction: Interaction, name: str, pet: app_commands.Choice[str]):
        """Summons a new pet for the user in the current server."""
        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild.id)

        try:
            # Enforce capacity by entitlements
            from services.premium import get_user_entitlements
            ent = get_user_entitlements(user_id)
            extra = int(ent.get("extraPets", 0) or 0)
            capacity = 1 + extra
            existing_count = count_unlocked_user_pets(user_id, guild_id)
            if existing_count >= capacity:
                embed = create_error_embed(
                    title="Summon Failed",
                    description=(
                        f"{interaction.user.mention}, you've reached your pet capacity for your tier.\n"
                        f"Capacity: **{capacity}** (Tier: {ent.get('tier', 'free').title()}).\n"
                        f"Release a pet or upgrade your tier to summon more."
                    )
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
                "claimed_daily_completion_bonus": False,
                "is_locked": False,
                "is_active": False
            }

            # Insert into DB first to get the _id
            result = pets_collection.insert_one(new_pet_data)
            new_pet_data['_id'] = result.inserted_id # Store the ObjectId
            # If this is the user's first pet, mark active. If not, keep active status on existing one
            if existing_count == 0:
                try:
                    pets_collection.update_one({"_id": result.inserted_id}, {"$set": {"is_active": True}})
                except Exception:
                    pass
            # Invalidate entitlement cache for safety (no-op if unchanged)
            try:
                invalidate_user_entitlements(user_id)
            except Exception:
                pass

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


    @app_commands.command(name="pets", description="List your pets and active status")
    async def pets(self, interaction: Interaction):
        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild.id)
        try:
            # Enforce capacity on list to reflect any downgrades
            try:
                enforce_user_pet_capacity(user_id, guild_id)
            except Exception:
                pass
            pets = get_user_pets(user_id, guild_id)
            if not pets:
                embed = create_error_embed("No Pets", "You have no pets. Use `/petbattles summon` to create one.")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Build a nicer embed with emoji markers and active thumbnail
            active_pet = get_active_pet_document(user_id, guild_id)
            lines = []
            for p in pets:
                if p.get("is_locked"):
                    status_emoji = "🔒"
                elif p.get("is_active"):
                    status_emoji = "🟢"
                else:
                    status_emoji = "⚪"
                pet_name = p.get('name', 'Unnamed')
                pet_level = p.get('level', 1)
                lines.append(f"{status_emoji} **{pet_name}** — L{pet_level}")

            from services.premium import get_user_entitlements
            ent = get_user_entitlements(user_id)
            capacity = 1 + int(ent.get("extraPets", 0) or 0)

            embed = discord.Embed(
                title="🐾 Your Pets",
                description="\n".join(lines),
                color=discord.Color.blue()
            )
            if active_pet and active_pet.get('icon'):
                embed.set_thumbnail(url=active_pet['icon'])
            from_here_unlocked = count_unlocked_user_pets(user_id, guild_id)
            embed.add_field(name="Capacity (Unlocked)", value=f"{from_here_unlocked}/{capacity}", inline=True)
            embed.add_field(name="Tips", value=(
                "Use `/petbattles setactive name:<PetName>` to switch active.\n"
                "Use `/petbattles stats name:<PetName>` to view a specific pet."
            ), inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error listing pets for {user_id}: {e}", exc_info=True)
            await interaction.response.send_message(embed=create_error_embed("Error", "Failed to list your pets."), ephemeral=True)


    @app_commands.command(name="setactive", description="Set one of your pets active by name")
    async def setactive(self, interaction: Interaction, name: str):
        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild.id)
        try:
            pet_doc = pets_collection.find_one({"user_id": user_id, "guild_id": guild_id, "name": name})
            if not pet_doc:
                await interaction.response.send_message(embed=create_error_embed("Not Found", f"No pet named '{name}' found."), ephemeral=True)
                return
            pet_id = pet_doc.get("_id")
            if not isinstance(pet_id, ObjectId):
                try:
                    pet_id = ObjectId(pet_id)
                except Exception:
                    await interaction.response.send_message(embed=create_error_embed("Error", "Invalid pet ID."), ephemeral=True)
                    return
            # If the target pet is locked, do not allow setting active (prevents bypassing locks)
            if pet_doc.get("is_locked"):
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Pet Locked",
                        "This pet is locked due to your current tier capacity. Upgrade or release other pets to unlock it."
                    ),
                    ephemeral=True
                )
                return

            # Otherwise, set active normally and bump last_used_ts
            if set_active_pet(user_id, guild_id, pet_id):
                try:
                    now_ts = int(datetime.now(timezone.utc).timestamp())
                    pets_collection.update_one({"_id": pet_id}, {"$set": {"last_used_ts": now_ts}})
                except Exception:
                    pass
                await interaction.response.send_message(embed=create_success_embed("Active Pet Set", f"'{name}' is now your active pet."), ephemeral=True)
            else:
                await interaction.response.send_message(embed=create_error_embed("Error", "Failed to set active pet."), ephemeral=True)
        except Exception as e:
            logger.error(f"Error setting active pet for {user_id}: {e}", exc_info=True)
            await interaction.response.send_message(embed=create_error_embed("Error", "An error occurred."), ephemeral=True)


    @app_commands.command(name="release", description="Release a pet you own by name")
    async def release(self, interaction: Interaction, name: str):
        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild.id)
        try:
            pet_doc = pets_collection.find_one({"user_id": user_id, "guild_id": guild_id, "name": name})
            if not pet_doc:
                await interaction.response.send_message(embed=create_error_embed("Not Found", f"No pet named '{name}' found."), ephemeral=True)
                return
            was_active = bool(pet_doc.get("is_active"))
            result = pets_collection.delete_one({"_id": pet_doc["_id"]})
            if result.deleted_count == 1:
                # If active pet was released, set another pet active if any remain
                if was_active:
                    remaining = get_user_pets(user_id, guild_id)
                    if remaining:
                        try:
                            next_id = remaining[0].get("_id")
                            if next_id:
                                pets_collection.update_one({"_id": next_id}, {"$set": {"is_active": True}})
                        except Exception:
                            pass
                await interaction.response.send_message(embed=create_success_embed("Pet Released", f"You released '{name}'."), ephemeral=True)
            else:
                await interaction.response.send_message(embed=create_error_embed("Error", "Failed to release pet."), ephemeral=True)
        except Exception as e:
            logger.error(f"Error releasing pet for {user_id}: {e}", exc_info=True)
            await interaction.response.send_message(embed=create_error_embed("Error", "An error occurred."), ephemeral=True)

    @app_commands.command(name="stats", description="View your pet's detailed statistics and status")
    @app_commands.describe(name="Optionally view stats for a specific pet by name")
    async def stats(self, interaction: Interaction, name: Optional[str] = None):
        """Displays the user's pet stats, including balance and active items."""
        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild.id)
        try:
            # If a name is provided, fetch that unlocked pet; else use active/default
            if name:
                pet = pets_collection.find_one({
                    "user_id": user_id,
                    "guild_id": guild_id,
                    "name": name,
                    "is_locked": {"$ne": True}
                })
            else:
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

            # Multi-pet: show active marker and total count/capacity
            all_pets = get_user_pets(user_id, guild_id)
            num_pets = len(all_pets)
            from services.premium import get_user_entitlements
            ent = get_user_entitlements(user_id)
            extra = int(ent.get("extraPets", 0) or 0)
            capacity = 1 + extra
            active_marker = " (Active)" if pet.get("is_active") else ""

            ent = get_user_entitlements(user_id)
            badge = " ⭐" if ent.get("premiumBadge") else ""
            tier = ent.get("tier", "free")

            embed = discord.Embed(
                title=f"{interaction.user.display_name}'s Pet: {pet['name']}{active_marker}{badge}",
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
            # Premium tier info and capacity
            embed.add_field(name="Premium Tier", value=tier.title(), inline=True)
            from_here_unlocked = count_unlocked_user_pets(user_id, guild_id)
            embed.add_field(name="Pet Capacity (Unlocked)", value=f"{from_here_unlocked}/{capacity}", inline=True)

            # Add quick list of your pets with active/locked markers for convenience
            pet_lines = []
            for p in all_pets:
                is_active = "(Active) " if p.get("is_active") else ""
                locked = " [LOCKED]" if p.get("is_locked") else ""
                pet_lines.append(f"{is_active}{p.get('name','Unnamed')} — L{p.get('level',1)}{locked}")
            if pet_lines:
                embed.add_field(name="Your Pets", value="\n".join(pet_lines), inline=False)

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

            # Prevent using a locked pet
            if user_pet.get("is_locked"):
                embed = create_error_embed(
                    "Pet Locked",
                    "Your active pet is locked due to your current tier capacity. Upgrade to unlock it or set another active pet."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Ensure pets have necessary fields
            user_pet = ensure_quests_and_achievements(user_pet)
            opponent_pet = ensure_quests_and_achievements(opponent_pet)

            # Record usage timestampts for prioritizing keeps
            try:
                now_ts = int(datetime.now(timezone.utc).timestamp())
                pets_collection.update_one({"_id": user_pet["_id"]}, {"$set": {"last_used_ts": now_ts}})
                pets_collection.update_one({"_id": opponent_pet["_id"]}, {"$set": {"last_used_ts": now_ts}})
            except Exception:
                pass

            # Level difference check (optional, adjust as needed)
            level_diff = abs(user_pet['level'] - opponent_pet['level'])
            if level_diff > 5: # Allow battling pets within 5 levels
                embed = create_error_embed(
                    "Battle Error",
                    "You can only battle pets within 5 levels of your own."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Battle cooldown check
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

            # Determine battle limit based on vote bonus for BOTH users
            BASE_BATTLE_LIMIT = 5
            VOTE_BATTLE_BONUS = 10
            battle_limit = BASE_BATTLE_LIMIT
            user_bonus_active = user_pet.get("voted_battle_bonus_active", False)
            opponent_bonus_active = opponent_pet.get("voted_battle_bonus_active", False)
            bonus_contributors = []

            if user_bonus_active:
                battle_limit += VOTE_BATTLE_BONUS
                bonus_contributors.append(interaction.user.display_name)
            if opponent_bonus_active:
                battle_limit += VOTE_BATTLE_BONUS
                bonus_contributors.append(opponent.display_name)

            if recent_battles_count >= battle_limit:
                limit_message = (f"You and {opponent.display_name} have already battled "
                                 f"{recent_battles_count} times today (Daily Limit: {battle_limit}).")

                if bonus_contributors:
                    limit_message += f" (Vote bonus active for: {', '.join(bonus_contributors)})"
                else:
                    limit_message += " Vote with `/petbattles vote` for more battles!"
                limit_message += " Please try again tomorrow."

                embed = create_error_embed(
                    "Battle Limit Reached",
                    limit_message
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

            # Update battle record for profile display
            winner_battle_record = winner.get('battleRecord', {"wins": 0, "losses": 0})
            loser_battle_record = loser.get('battleRecord', {"wins": 0, "losses": 0})
            
            # Increment wins and losses without overwriting the entire record
            if 'battleRecord' not in winner:
                winner['battleRecord'] = {"wins": 0, "losses": 0}
            if 'battleRecord' not in loser:
                loser['battleRecord'] = {"wins": 0, "losses": 0}
                
            winner['battleRecord']['wins'] = winner_battle_record.get('wins', 0) + 1
            loser['battleRecord']['losses'] = loser_battle_record.get('losses', 0) + 1

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
            
            # Check circuit breaker state
            if self.topgg_circuit_open:
                embed = create_error_embed(
                    "Voting Temporarily Unavailable", 
                    "Top.gg connection is experiencing issues. Please try again later."
                )
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
                                 f"to claim **{VOTE_REWARD_XP} XP**, **10 more battles with the same person** and **{format_currency(VOTE_REWARD_CASH)}**!"),
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
                    pet['voted_battle_bonus_active'] = True # Activate the battle bonus flag
                    pet['bonus_battle_allowance'] = 10 # Set the allowance amount

                    pet, leveled_up = check_level_up(pet) # Assume returns updated dict
                    update_pet_document(pet) # Save changes

                    embed = create_success_embed(
                        "🎉 Thank You for Voting! 🎉",
                        (f"You received **{VOTE_REWARD_XP} XP** and **{format_currency(VOTE_REWARD_CASH)}**!\n"
                         f"You can now battle the same opponent **10 extra times** today!\n"
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

    @app_commands.command(name="train", description="Train your pet to gain XP for a cost")
    async def train(self, interaction: Interaction):
        """Train your pet to gain XP in exchange for currency."""
        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild.id)
        TRAINING_COST = 75  # Cost in currency
        TRAINING_XP_MIN = 50  # Minimum XP gained
        TRAINING_XP_MAX = 100  # Maximum XP gained
        DAILY_TRAINING_LIMIT = 5  # Maximum trainings per day
        
        try:
            pet = get_pet_document(user_id, guild_id)
            if not pet:
                embed = create_error_embed(
                    "No Pet Found",
                    f"{interaction.user.mention}, you need a pet to train! Use `/petbattles summon`."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Ensure pet has necessary fields
            pet = ensure_quests_and_achievements(pet)
            
            # Check if pet has reached daily training limit
            training_count = pet.get('trainingCount', 0)
            if training_count >= DAILY_TRAINING_LIMIT:
                # Calculate time until reset
                now = datetime.now(timezone.utc)
                midnight = datetime.combine(now.date() + timedelta(days=1), 
                                          dtime(0, 0, tzinfo=timezone.utc))
                time_until_reset = midnight - now
                hours, remainder = divmod(int(time_until_reset.total_seconds()), 3600)
                minutes, _ = divmod(remainder, 60)
                time_str = f"{hours}h {minutes}m"
                
                embed = create_error_embed(
                    "Training Limit Reached",
                    f"Your pet has reached the daily training limit of {DAILY_TRAINING_LIMIT} sessions. Training will reset in **{time_str}**."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Check if pet has enough currency
            if pet.get('balance', 0) < TRAINING_COST:
                embed = create_error_embed(
                    "Insufficient Funds",
                    f"You need **{format_currency(TRAINING_COST)}** to train your pet, but you only have **{format_currency(pet.get('balance', 0))}**."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Process training
            xp_gained = random.randint(TRAINING_XP_MIN, TRAINING_XP_MAX)
            pet['balance'] -= TRAINING_COST
            pet['xp'] += xp_gained
            pet['trainingCount'] = training_count + 1
            
            # Check for level up
            pet, leveled_up = check_level_up(pet)
            
            # Save changes
            update_pet_document(pet)
            
            # Create success embed
            embed = create_success_embed(
                "🏋️ Training Complete!",
                f"You spent **{format_currency(TRAINING_COST)}** to train {pet['name']}.\n"
                f"Your pet gained **{xp_gained} XP**!\n"
                f"Training sessions used today: **{pet['trainingCount']}/{DAILY_TRAINING_LIMIT}**\n"
                f"New balance: **{format_currency(pet['balance'])}**"
            )
            
            if leveled_up:
                embed.add_field(
                    name="🌟 Level Up!",
                    value=f"Your pet reached **Level {pet['level']}**!",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in train command for user {user_id}: {e}", exc_info=True)
            embed = create_error_embed("Training Error", "An unexpected error occurred during training.")
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="rename", description="Change your pet's name for a fee")
    @app_commands.describe(new_name="The new name for your pet")
    async def rename(self, interaction: Interaction, new_name: str):
        """Allows a user to rename their pet for a fee."""
        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild.id)
        RENAME_COST = 200  # Cost in currency
        
        try:
            pet = get_pet_document(user_id, guild_id)
            if not pet:
                embed = create_error_embed(
                    "No Pet Found",
                    f"{interaction.user.mention}, you need a pet first! Use `/petbattles summon`."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Ensure pet has necessary fields
            pet = ensure_quests_and_achievements(pet)
            
            # Validate name length
            if len(new_name) > 32:
                embed = create_error_embed(
                    "Name Too Long",
                    "Pet name cannot be longer than 32 characters."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Check for inappropriate names - could be expanded
            if any(word in new_name.lower() for word in ["discord.gg/", "http://", "https://", "@everyone", "@here"]):
                embed = create_error_embed(
                    "Invalid Name",
                    "The name contains disallowed content."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Check if pet has enough currency
            if pet.get('balance', 0) < RENAME_COST:
                embed = create_error_embed(
                    "Insufficient Funds",
                    f"You need **{format_currency(RENAME_COST)}** to rename your pet, but you only have **{format_currency(pet.get('balance', 0))}**."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Store old name for confirmation message
            old_name = pet['name']
            
            # Process renaming
            pet['balance'] -= RENAME_COST
            pet['name'] = new_name
            pet['lastRenameTime'] = datetime.now(timezone.utc).isoformat()
            
            # Save changes
            if update_pet_document(pet):
                embed = create_success_embed(
                    "✏️ Pet Renamed!",
                    f"You spent **{format_currency(RENAME_COST)}** to rename your pet.\n"
                    f"**{old_name}** is now known as **{new_name}**!\n"
                    f"New balance: **{format_currency(pet['balance'])}**"
                )
                embed.set_thumbnail(url=pet['icon'])
                await interaction.response.send_message(embed=embed)
            else:
                embed = create_error_embed(
                    "Rename Error",
                    "Failed to save the new name. Please try again."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in rename command for user {user_id}: {e}", exc_info=True)
            embed = create_error_embed("Rename Error", "An unexpected error occurred while renaming your pet.")
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="profile", description="View detailed profile of your pet")
    async def profile(self, interaction: Interaction):
        """Shows detailed profile information about a pet, including battle records and achievements."""
        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild.id)
        
        try:
            pet = get_pet_document(user_id, guild_id)
            if not pet:
                embed = create_error_embed(
                    "No Pet Found",
                    f"{interaction.user.mention}, you need a pet first! Use `/petbattles summon`."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Ensure pet has necessary fields
            pet = ensure_quests_and_achievements(pet)
            
            # Get battle record
            battle_record = pet.get('battleRecord', {"wins": 0, "losses": 0})
            total_battles = battle_record.get('wins', 0) + battle_record.get('losses', 0)
            win_rate = 0
            if total_battles > 0:
                win_rate = round((battle_record.get('wins', 0) / total_battles) * 100, 1)
            
            # Create the profile embed
            embed = discord.Embed(
                title=f"{pet['name']}'s Profile",
                description=f"Level {pet['level']} {pet.get('pet_type', 'Pet')}",
                color=pet.get('color', discord.Color.blue())
            )
            
            # Set the pet image as the thumbnail
            embed.set_thumbnail(url=pet['icon'])
            
            # Add owner field
            try:
                owner = await self.bot.fetch_user(int(pet['user_id']))
                owner_name = owner.display_name
                owner_avatar = owner.display_avatar.url
                embed.set_author(name=f"{owner_name}'s Pet", icon_url=owner_avatar)
            except:
                embed.set_author(name="Pet Profile")
            
            # Add XP progress bar
            xp_needed = calculate_xp_needed(pet['level'])
            xp_bar = create_progress_bar(pet['xp'], xp_needed)
            
            # Add the general stats section
            general_stats = (
                f"**Level:** {pet['level']}\n"
                f"**XP:** {pet['xp']}/{xp_needed}\n"
                f"{xp_bar}\n"
                f"**Balance:** {format_currency(pet.get('balance', 0))}"
            )
            embed.add_field(name="📊 General Stats", value=general_stats, inline=False)
            
            # Add battle stats section
            battle_stats = (
                f"**Wins:** {battle_record.get('wins', 0)}\n"
                f"**Losses:** {battle_record.get('losses', 0)}\n"
                f"**Total Battles:** {total_battles}\n"
                f"**Win Rate:** {win_rate}%\n"
                f"**Current Streak:** {pet.get('killstreak', 0)} wins"
            )
            embed.add_field(name="⚔️ Battle Record", value=battle_stats, inline=False)
            
            # Add combat stats section
            combat_stats = (
                f"**Strength:** {pet['strength']}\n"
                f"**Defense:** {pet['defense']}\n"
                f"**Health:** {pet['health']} HP"
            )
            embed.add_field(name="💪 Combat Stats", value=combat_stats, inline=True)
            
            # Show active buffs if any
            active_items = pet.get('active_items', [])
            if active_items:
                buffs_text = "\n".join([f"• {item.get('name', 'Unknown')}: +{item.get('value', 0)} {item.get('stat', '?').capitalize()} ({item.get('battles_remaining', 0)} battles left)" for item in active_items])
                embed.add_field(name="✨ Active Buffs", value=buffs_text, inline=True)
            
            # Add achievement progress section - show 3 in-progress achievements
            achievements = pet.get('achievements', [])
            incomplete_achievements = [a for a in achievements if not a.get('completed', False)]
            if incomplete_achievements:
                # Sort by progress percentage
                incomplete_achievements.sort(key=lambda a: a.get('progress', 0) / a['progress_required'], reverse=True)
                # Take top 3
                top_achievements = incomplete_achievements[:3]
                
                achievements_text = ""
                for achievement in top_achievements:
                    progress = achievement.get('progress', 0)
                    required = achievement['progress_required']
                    percent = int((progress / required) * 100)
                    achievements_text += f"• {achievement['description']}: {progress}/{required} ({percent}%)\n"
                
                embed.add_field(name="🏆 Achievement Progress", value=achievements_text, inline=False)
            
            # Add completed achievement count
            completed_count = len([a for a in achievements if a.get('completed', False)])
            if completed_count > 0:
                embed.add_field(
                    name="🏅 Completed Achievements", 
                    value=f"{completed_count}/{len(achievements)} achievements completed",
                    inline=True
                )
                
            embed.set_footer(text="Use /petbattles help for more commands")
            embed.timestamp = datetime.now(timezone.utc)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in profile command for user {user_id}: {e}", exc_info=True)
            embed = create_error_embed("Profile Error", "An unexpected error occurred while fetching the pet profile.")
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="daily", description="Claim your daily pet rewards")
    async def daily(self, interaction: Interaction):
        """Claim daily XP and currency rewards once per day."""
        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild.id)
        DAILY_REWARD_XP = 100  # Base XP reward
        DAILY_REWARD_CASH = 50  # Base cash reward
        STREAK_BONUS_MULTIPLIER = 0.1  # 10% bonus per day in streak
        MAX_STREAK_BONUS = 1.0  # Maximum 100% bonus (double rewards)
        MAX_STREAK_DAYS = 10   # For display purposes, cap visible streak at 10 days
        
        try:
            pet = get_pet_document(user_id, guild_id)
            if not pet:
                embed = create_error_embed(
                    "No Pet Found",
                    f"{interaction.user.mention}, you need a pet first! Use `/petbattles summon`."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Ensure pet has necessary fields
            pet = ensure_quests_and_achievements(pet)
            
            # Check if they've already claimed today
            now = datetime.now(timezone.utc)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            last_claim_str = pet.get('lastDailyClaim')
            if last_claim_str:
                try:
                    last_claim = datetime.fromisoformat(last_claim_str)
                    if last_claim.tzinfo is None:
                        last_claim = last_claim.replace(tzinfo=timezone.utc)
                    
                    # Check if last claim was today
                    if last_claim >= today_start:
                        # Calculate time until next reset
                        tomorrow = today_start + timedelta(days=1)
                        time_until_reset = tomorrow - now
                        hours, remainder = divmod(int(time_until_reset.total_seconds()), 3600)
                        minutes, _ = divmod(remainder, 60)
                        time_str = f"{hours}h {minutes}m"
                        
                        embed = create_error_embed(
                            "Already Claimed Today",
                            f"You've already claimed your daily rewards today. Come back in **{time_str}**."
                        )
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        return
                except (ValueError, TypeError):
                    # Continue if last claim date is invalid - they get to claim
                    pass
            
            # Calculate streak
            streak = 0
            streak_broken = True
            
            if last_claim_str:
                try:
                    last_claim = datetime.fromisoformat(last_claim_str)
                    if last_claim.tzinfo is None:
                        last_claim = last_claim.replace(tzinfo=timezone.utc)
                    
                    # Check if last claim was yesterday
                    yesterday = today_start - timedelta(days=1)
                    if last_claim >= yesterday and last_claim < today_start:
                        # Continued streak - add to existing streak count or start at 1
                        streak = pet.get('dailyStreak', 0) + 1
                        streak_broken = False
                    else:
                        # Streak broken - reset to 1
                        streak = 1
                except (ValueError, TypeError):
                    # Invalid date format, treat as new streak
                    streak = 1
            else:
                # First time claiming - start streak at 1
                streak = 1
            
            # Apply streak bonus
            streak_bonus = min(streak * STREAK_BONUS_MULTIPLIER, MAX_STREAK_BONUS)
            xp_reward = int(DAILY_REWARD_XP * (1 + streak_bonus))
            cash_reward = int(DAILY_REWARD_CASH * (1 + streak_bonus))
            
            # Apply rewards
            pet['xp'] += xp_reward
            pet['balance'] = pet.get('balance', 0) + cash_reward
            pet['lastDailyClaim'] = now.isoformat()
            pet['dailyStreak'] = streak
            
            # Check for level up
            pet, leveled_up = check_level_up(pet)
            
            # Save changes
            update_pet_document(pet)
            
            # Create success embed
            if streak_broken:
                streak_text = f"New streak started! (Day 1)"
            else:
                display_streak = min(streak, MAX_STREAK_DAYS)
                display_streak_text = f"{display_streak}" if streak <= MAX_STREAK_DAYS else f"{display_streak}+" 
                streak_emoji = "🔥" * min(5, max(1, (streak + 1) // 2))  # 1-2→🔥, 3-4→🔥🔥, 5-6→🔥🔥🔥, etc. up to 5 emojis
                streak_text = f"{streak_emoji} Streak: Day {display_streak_text} (+{int(streak_bonus * 100)}% bonus)"
            
            embed = create_success_embed(
                "📅 Daily Rewards Claimed!",
                f"You received **{xp_reward} XP** and **{format_currency(cash_reward)}**!\n\n"
                f"{streak_text}\n\n"
                f"New balance: **{format_currency(pet['balance'])}**\n"
                f"Come back tomorrow for more rewards!"
            )
            
            if leveled_up:
                embed.add_field(
                    name="🌟 Level Up!",
                    value=f"Your pet reached **Level {pet['level']}**!",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in daily command for user {user_id}: {e}", exc_info=True)
            embed = create_error_embed("Daily Claim Error", "An unexpected error occurred while claiming daily rewards.")
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="hunt", description="Send your pet hunting for rewards")
    async def hunt(self, interaction: Interaction):
        """Allows your pet to go hunting for currency and items with a cooldown."""
        # Defer the response immediately to prevent timeout
        await interaction.response.defer()
        
        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild.id)
        HUNT_COOLDOWN_HOURS = 2  # Cooldown between hunts
        MIN_HUNT_CASH = 30  # Minimum currency reward
        MAX_HUNT_CASH = 150  # Maximum currency reward
        
        try:
            pet = get_pet_document(user_id, guild_id)
            if not pet:
                embed = create_error_embed(
                    "No Pet Found",
                    f"{interaction.user.mention}, you need a pet to go hunting! Use `/petbattles summon`."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Ensure pet has necessary fields
            pet = ensure_quests_and_achievements(pet)
            
            # Check if pet is on cooldown
            now = datetime.now(timezone.utc)
            last_hunt_str = pet.get('lastHuntTime')
            
            if last_hunt_str:
                try:
                    last_hunt = datetime.fromisoformat(last_hunt_str)
                    if last_hunt.tzinfo is None:
                        last_hunt = last_hunt.replace(tzinfo=timezone.utc)
                    
                    # Calculate time since last hunt
                    time_since_hunt = now - last_hunt
                    cooldown_seconds = HUNT_COOLDOWN_HOURS * 3600
                    
                    if time_since_hunt.total_seconds() < cooldown_seconds:
                        # Still on cooldown
                        time_left = timedelta(seconds=cooldown_seconds) - time_since_hunt
                        minutes, seconds = divmod(int(time_left.total_seconds()), 60)
                        hours, minutes = divmod(minutes, 60)
                        
                        time_str = ""
                        if hours > 0:
                            time_str += f"{hours}h "
                        if minutes > 0 or hours > 0:
                            time_str += f"{minutes}m "
                        time_str += f"{seconds}s"
                        
                        embed = create_error_embed(
                            "Hunt Cooldown",
                            f"Your pet is still tired from the last hunt. Try again in **{time_str}**."
                        )
                        await interaction.followup.send(embed=embed, ephemeral=True)
                        return
                except (ValueError, TypeError):
                    # Invalid date format, allow hunt
                    pass
            
            # Calculate hunt success chance based on pet level
            # Higher level pets have better chances
            base_success_chance = 70  # 70% base success rate
            level_bonus = min(20, pet['level'] * 2)  # +2% per level, max +20%
            success_chance = base_success_chance + level_bonus
            
            # Calculate hunt reward modifier based on pet level
            reward_modifier = 1.0 + (pet['level'] * 0.05)  # +5% per level
            
            # Determine if hunt was successful
            hunt_roll = random.randint(1, 100)
            hunt_success = hunt_roll <= success_chance
            
            # Update last hunt time
            pet['lastHuntTime'] = now.isoformat()
            
            if hunt_success:
                # Calculate cash reward
                cash_base = random.randint(MIN_HUNT_CASH, MAX_HUNT_CASH)
                cash_reward = int(cash_base * reward_modifier)
                pet['balance'] = pet.get('balance', 0) + cash_reward
                
                # Determine if pet found a special item (20% chance)
                found_item = random.random() < 0.2
                item_description = ""
                
                if found_item:
                    # Select a random item from the shop or create a hunt-exclusive item
                    shop_items = list(SHOP_ITEMS.values())
                    if shop_items:
                        # 20% chance to find a shop item
                        if random.random() < 0.2 and shop_items:
                            found_item_data = random.choice(shop_items)
                            
                            new_item_data = {
                                "item_id": "hunt_" + str(random.randint(1000, 9999)),  # Generate a random ID
                                "name": found_item_data['name'],
                                "stat": found_item_data['stat'],
                                "value": found_item_data['value'],
                                "battles_remaining": found_item_data['duration']
                            }
                            
                            # Add item to pet's inventory
                            if not isinstance(pet.get('active_items'), list):
                                pet['active_items'] = []
                            
                            pet['active_items'].append(new_item_data)
                            item_description = f"Found **{new_item_data['name']}** (+{new_item_data['value']} {new_item_data['stat'].capitalize()} for {new_item_data['battles_remaining']} battles)"
                        else:
                            # Otherwise, just add extra cash
                            bonus_cash = random.randint(20, 50)
                            pet['balance'] += bonus_cash
                            item_description = f"Found a **small treasure** worth {format_currency(bonus_cash)}!"
                
                # Save pet data
                update_pet_document(pet)
                
                # Create success embed
                embed = create_success_embed(
                    "🏹 Successful Hunt!",
                    f"Your pet ventured into the wilderness and returned with rewards!\n\n"
                    f"Rewards:\n"
                    f"• {format_currency(cash_reward)}"
                )
                
                if item_description:
                    embed.add_field(name="Special Find!", value=item_description, inline=False)
                
                # Add some flavor text based on what the pet found
                hunt_outcomes = [
                    f"{pet['name']} tracked down elusive prey through dense undergrowth.",
                    f"{pet['name']} discovered abandoned treasure in a forgotten cave.",
                    f"{pet['name']} skillfully hunted in the moonlight.",
                    f"{pet['name']} caught several small creatures through stealth and patience.",
                    f"{pet['name']} found valuable resources in the wilderness."
                ]
                
                embed.add_field(name="Hunt Details", value=random.choice(hunt_outcomes), inline=False)
                embed.set_footer(text=f"New Balance: {format_currency(pet['balance'])} | Next hunt available in {HUNT_COOLDOWN_HOURS} hours")
            else:
                # Failed hunt - no rewards
                update_pet_document(pet)
                
                # Create failure embed
                embed = discord.Embed(
                    title="🏹 Hunt Failed",
                    description=f"Your pet ventured into the wilderness but returned empty-pawed.",
                    color=discord.Color.orange()
                )
                
                # Add some flavor text for the failure
                failure_outcomes = [
                    f"{pet['name']} lost track of prey at the last moment.",
                    f"{pet['name']} was spotted before getting close enough.",
                    f"{pet['name']} wandered into unfamiliar territory and got lost for a while.",
                    f"{pet['name']} was intimidated by a larger creature and retreated.",
                    f"{pet['name']} spent hours searching but found nothing of value."
                ]
                
                embed.add_field(name="Hunt Details", value=random.choice(failure_outcomes), inline=False)
                embed.set_footer(text=f"Better luck next time! | Next hunt available in {HUNT_COOLDOWN_HOURS} hours")
            
            # Add thumbnail of pet
            embed.set_thumbnail(url=pet['icon'])
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in hunt command for user {user_id}: {e}", exc_info=True)
            embed = create_error_embed("Hunt Error", "An unexpected error occurred during the hunt.")
            # Check if the interaction has already been responded to
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)

# --- Setup Function ---
async def setup(bot: commands.Bot):
    """Adds the PetBattles cog to the bot."""
    await bot.add_cog(PetBattles(bot))
    logger.info("PetBattles Cog loaded.")

