# Standard Library Imports
import random
import asyncio
import logging
import datetime
from typing import Dict, List, Any, Optional, Tuple
from datetime import timezone

# Discord Imports
import discord
from discord.ext import commands
from discord import app_commands, Interaction, Embed, Color, ButtonStyle
from discord.ui import View, Button
from services.premium import get_user_entitlements
from ui.embeds import get_premium_promotion_embed

# Third-Party Imports
from pymongo import MongoClient
from pymongo.collection import Collection, UpdateOne # Import UpdateOne for bulk writes
from pymongo.database import Database
from pymongo.errors import ConnectionFailure # Import specific error

# --- Logging Setup ---
logger = logging.getLogger(__name__) # Use __name__ for logger hierarchy
# Set default level if not configured elsewhere (optional, depends on main bot setup)
# logger.setLevel(logging.WARNING)

# Local Application/Library Specific Imports
try:
    from core.utils import get_conditional_embed # Assuming this fetches a specific embed structure
except ImportError:
    logger.warning("core.utils.get_conditional_embed not found. Conditional embeds disabled.")
    get_conditional_embed = None # Define as None if import fails

try:
    from config.settings import MONGODB_URI       # Assuming this holds the MongoDB connection string
except ImportError:
     logger.critical("config.settings.MONGODB_URI not found. Database functionality disabled.")
     MONGODB_URI = None # Define as None if import fails


# --- Constants ---
# Emojis for UI elements (using the enhanced set)
EMOJI_JOIN = "✅"
EMOJI_START = "🏁" # Used for initial /start command message
EMOJI_RUN = "▶️"   # Used for /run command message
EMOJI_STATUS = "📊"
EMOJI_LEADERBOARD = "🏆" # Kept in case you add leaderboard later
EMOJI_STOP = "🛑"
EMOJI_ALIVE = "🟢"
EMOJI_ELIMINATED = "💀"
EMOJI_HOST = "👑"
EMOJI_ROUND = "🔄"
EMOJI_WAITING = "⏳"
EMOJI_IN_PROGRESS = "⚙️"
EMOJI_COMPLETED = "🏁"
EMOJI_ERROR = "❌"
EMOJI_WARNING = "⚠️"
EMOJI_INFO = "ℹ️" # Kept for potential future use in embeds, not logging
EMOJI_SUCCESS = "🎉"
EMOJI_GAME = "🦑" # Squib Game main emoji

# Embed Colors (using the enhanced set)
COLOR_DEFAULT = Color.blue()
COLOR_SUCCESS = Color.green()
COLOR_ERROR = Color.red()
COLOR_WARNING = Color.orange()
COLOR_GOLD = Color.gold()
COLOR_WAITING = Color.light_grey()
COLOR_IN_PROGRESS = Color.dark_blue()

# Game Settings
MIN_PLAYERS = 2
ROUND_DELAY_SECONDS = 10 # Delay between rounds
MAX_DISPLAY_PLAYERS = 10 # Max players to list explicitly in embeds


# --- Database Setup ---
mongo_client: Optional[MongoClient] = None
db: Optional[Database] = None
squib_game_sessions: Optional[Collection] = None
squib_game_stats: Optional[Collection] = None

try:
    if MONGODB_URI:
        # Set serverSelectionTimeoutMS to handle connection issues faster
        mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        # The ismaster command is cheap and does not require auth.
        mongo_client.admin.command('ping')
        db = mongo_client['astrostats_database'] # Consider making the DB name configurable
        squib_game_sessions = db['squib_game_sessions']
        squib_game_stats = db['squib_game_stats']
    else:
        logger.warning("MONGODB_URI not set in config.settings. Database functionality will be disabled.")

except ConnectionFailure as e:
    logger.critical(f"MongoDB Connection Failure: Could not connect to server. {e}")
    mongo_client = None
    db = None
    squib_game_sessions = None
    squib_game_stats = None
except Exception as e:
    logger.critical(f"Failed to initialize MongoDB connection: {e}", exc_info=True)
    mongo_client = None # Ensure client is None if connection failed
    db = None
    squib_game_sessions = None
    squib_game_stats = None


# --- Minigame Definitions ---
# Using the enhanced MINIGAMES list with varied flavor text
MINIGAMES = [
    {
        "name": "Red Light, Green Light", "emoji": "🚦",
        "description": "Freeze on 'Red Light', move on 'Green Light'. Don't get caught moving!",
        "elimination_probability": 0.4,
        "flavor_eliminated": [
            "was caught twitching during 'Red Light'!", "took one step too many...",
            "tripped right as the light turned red!", "thought they could sneak a move, but failed.",
            "couldn't resist scratching an itch at the wrong time.",
        ],
        "flavor_survived": ["froze perfectly still, like a statue.", "mastered the art of stillness.", "waited patiently for the green light."],
        "flavor_all_survived": "Everyone held their breath and froze! No eliminations this time."
    },
    {
        "name": "Glass Bridge", "emoji": "🌉",
        "description": "Choose wisely between tempered and regular glass panels to cross.",
        "elimination_probability": 0.35,
        "flavor_eliminated": [
            "chose the wrong panel and plummeted into the abyss!", "heard a crack before it was too late...",
            "hesitated and picked the fragile glass.", "followed someone else onto a weak panel.",
            "lost their balance on the treacherous path.",
        ],
        "flavor_survived": ["carefully navigated the fragile steps.", "made a leap of faith and landed safely.", "used deduction (or luck?) to cross."],
        "flavor_all_survived": "Incredible! Everyone navigated the treacherous bridge successfully!"
    },
    {
        "name": "Tug of War", "emoji": "🤼",
        "description": "Pure strength and teamwork. Pull the opposing team across the line.",
        "elimination_probability": 0.5,
        "flavor_eliminated": [
            "couldn't hold the line and was dragged down!", "lost their footing in the mud.",
            "was on the losing side of the struggle.", "their team's strategy faltered.",
            "the rope slipped from their grasp.",
        ],
        "flavor_survived": ["pulled with all their might to secure victory.", "anchored their team effectively.", "showed surprising strength."],
        "flavor_all_survived": "A rare stalemate! Both sides held firm, no eliminations in this brutal match."
    },
    {
        "name": "Marbles", "emoji": "🔮",
        "description": "A game of strategy and precision. Win your opponent's marbles.",
        "elimination_probability": 0.3,
        "flavor_eliminated": [
            "lost their last marble in a tense standoff!", "made a risky bet and lost everything.",
            "was outsmarted by their opponent.", "couldn't make the crucial shot.",
            "fumbled their marbles at the last second.",
        ],
        "flavor_survived": ["played strategically and kept their marbles safe.", "won a crucial round, securing their place.", "proved to be a marble master."],
        "flavor_all_survived": "A surprisingly peaceful round. Everyone managed to hold onto their marbles."
    },
    {
        "name": "Dalgona Candy", "emoji": "🍪",
        "description": "Carefully carve out the shape without breaking the candy.",
        "elimination_probability": 0.4,
        "flavor_eliminated": [
            "cracked the candy under pressure!", "licked too much and broke the shape.",
            "ran out of time with trembling hands.", "chose the notoriously difficult umbrella shape.",
            "a sudden sneeze sealed their fate.",
        ],
        "flavor_survived": ["carved their shape with surgical precision.", "used the needle skillfully.", "found a clever trick to succeed."],
        "flavor_all_survived": "Amazing concentration! Everyone successfully carved their shapes!"
    },
    {
        "name": "Odd One Out", "emoji": "❓",
        "description": "Identify the item that doesn't belong in the group.",
        "elimination_probability": 0.25,
        "flavor_eliminated": [
            "couldn't spot the difference in time!", "overthought the simple puzzle.",
            "was tricked by a clever distraction.", "focused on the wrong details.",
            "second-guessed their correct answer.",
        ],
        "flavor_survived": ["quickly identified the odd one out.", "has a keen eye for detail.", "saw through the deception."],
        "flavor_all_survived": "Sharp minds prevailed! Everyone correctly identified the odd one out."
    },
    {
        "name": "Rock Paper Scissors", "emoji": "✊✋✌️",
        "description": "Classic game of chance and psychology. Win the round to survive.",
        "elimination_probability": 0.33,
        "flavor_eliminated": [
            "chose rock, but was covered by paper!", "went with scissors, only to be crushed by rock!",
            "played paper, but got snipped by scissors!", "hesitated and lost the draw.",
            "tried to predict their opponent but failed.",
        ],
        "flavor_survived": ["won the round with a decisive choice.", "managed a draw, surviving another day.", "read their opponent like a book."],
        "flavor_all_survived": "A series of draws! Everyone lives to play another round."
    },
     {
        "name": "Memory Match", "emoji": "🧠",
        "description": "Remember the sequence or pattern shown. One mistake is fatal.",
        "elimination_probability": 0.3,
        "flavor_eliminated": [
            "forgot the last step in the sequence!", "mixed up the order.",
            "couldn't recall the pattern under pressure.", "was distracted and lost focus.",
            "blanked out at the crucial moment.",
        ],
        "flavor_survived": ["recalled the sequence perfectly.", "has an excellent memory.", "stayed focused and remembered."],
        "flavor_all_survived": "Incredible focus! Everyone aced the memory test."
    },
]

# --- Helper Functions ---
# Using the enhanced helper functions

async def get_guild_avatar_url(guild: Optional[discord.Guild], user_id: int) -> Optional[str]:
    """Safely fetches a user's guild-specific or default avatar URL."""
    if not guild:
        return None
    try:
        # Use cache first, then fetch if not found or member object is incomplete
        member = guild.get_member(user_id)
        if not member:
             member = await guild.fetch_member(user_id) # Fetch if not in cache

        if member:
            # Prefer guild avatar, fallback to global avatar
            if member.guild_avatar:
                return member.guild_avatar.url
            else:
                return member.display_avatar.url # display_avatar handles default/global
    except discord.NotFound:
        logger.warning(f"Member {user_id} not found in guild {guild.id}.")
    except discord.Forbidden:
         logger.warning(f"Missing permissions to fetch member {user_id} in guild {guild.id}.")
    except discord.HTTPException as e:
        logger.error(f"HTTP error fetching member {user_id} in guild {guild.id}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error fetching avatar for {user_id} in guild {guild.id}: {e}")
    return None # Fallback if any error occurs or member not found

def get_player_mentions(participants: List[Dict[str, Any]], status_filter: str = "alive") -> List[str]:
    """Returns a list of mentions for participants with the given status."""
    # Ensure user_id is present and correctly formatted
    mentions = []
    for p in participants:
        if p.get("status") == status_filter and p.get("user_id"):
            try:
                # Validate that user_id can be converted to int if needed elsewhere,
                # but keep as string for mention
                str_user_id = str(p['user_id'])
                mentions.append(f"<@{str_user_id}>")
            except (ValueError, TypeError):
                 logger.warning(f"Invalid user_id format found in participant data: {p.get('user_id')}")
    return mentions


def format_player_list(player_list: List[str], max_display: int = MAX_DISPLAY_PLAYERS) -> str:
    """Formats a list of player names or mentions for display in embeds."""
    if not player_list:
        return "None"
    count = len(player_list)
    if count > max_display:
        displayed = ", ".join(player_list[:max_display])
        remaining = count - max_display
        return f"{displayed}, and {remaining} more..."
    else:
        return ", ".join(player_list)

# Using the enhanced minigame logic function
def play_minigame_round(participants: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any], List[Dict[str, Any]]]:
    """
    Simulates a minigame round, determining eliminations based on probabilities.
    Returns:
        - Updated list of participants with new statuses.
        - The minigame dictionary that was played.
        - List of participants eliminated in this round.
    """
    if not participants: return [], random.choice(MINIGAMES), []
    current_participants = [p.copy() for p in participants] # Work on copies
    alive_participants = [p for p in current_participants if p.get("status") == "alive"]
    if not alive_participants: return current_participants, random.choice(MINIGAMES), []

    minigame = random.choice(MINIGAMES)
    eliminated_this_round = []
    # Shuffle alive participants to make elimination order random if needed later
    random.shuffle(alive_participants)
    for player in alive_participants:
        # Check if player should be eliminated based on probability
        if random.random() < minigame.get("elimination_probability", 0.3): # Default probability
            player["status"] = "eliminated"
            eliminated_this_round.append(player) # Add the full dict of the eliminated player

    # The function returns the list with updated statuses, the game played, and who was eliminated *this round*
    return current_participants, minigame, eliminated_this_round

# Using the enhanced flavor text generation
def generate_round_flavor_text(minigame: Dict[str, Any], eliminated_players: List[Dict[str, Any]], survived_players: List[Dict[str, Any]]) -> str:
    """Generates descriptive flavor text for the round's results."""
    flavor_parts = []
    eliminated_names = [p.get('username', 'Unknown') for p in eliminated_players] # Use .get with fallback
    survived_names = [p.get('username', 'Unknown') for p in survived_players]

    flavor_parts.append(f"*{minigame.get('description', 'A mysterious game unfolded...')}*")
    flavor_parts.append("-" * 20) # Separator line

    if eliminated_players:
        # Show specific flavor for up to 2 eliminated players
        for i in range(min(2, len(eliminated_players))):
            player = eliminated_players[i]
            flavor = random.choice(minigame.get("flavor_eliminated", ["met an unfortunate end."]))
            flavor_parts.append(f"{EMOJI_ELIMINATED} **{player.get('username', 'Someone')}** {flavor}")

        # General statement if more than 2 were eliminated
        if len(eliminated_players) > 2:
            flavor_parts.append(f"...along with {len(eliminated_players) - 2} others who couldn't make it.")

        # Add a survival statement if anyone survived
        if survived_players:
            survival_flavor = random.choice(minigame.get("flavor_survived", ["managed to survive."]))
            # Format survivor names, limit display
            survivor_summary = format_player_list([f"**{name}**" for name in survived_names], max_display=5)
            flavor_parts.append(f"{EMOJI_ALIVE} Meanwhile, {survivor_summary} {survival_flavor}")

    else:
        # All survived flavor text
        all_survived_flavor = minigame.get("flavor_all_survived", "Everyone managed to survive this round!")
        flavor_parts.append(f"{EMOJI_SUCCESS} {all_survived_flavor}")

    return "\n".join(flavor_parts)

# Reverted to original function name and structure, fixed DB check
def create_new_session(guild_id: str, user_id: str, display_name: str) -> Tuple[str, dict]:
    """Create a new Squib Game session."""
    # Fixed check: Compare with None
    if squib_game_sessions is None:
        logger.error("squib_game_sessions collection is not available.")
        raise ConnectionError("Database not initialized") # Raise specific error

    session_id = f"{guild_id}_{user_id}_{int(datetime.datetime.now(timezone.utc).timestamp())}"
    new_session_doc = {
        "guild_id": guild_id,
        "host_user_id": user_id,
        "session_id": session_id,
        "current_round": 0,
        "current_game_state": "waiting_for_players", # Original states
        "participants": [
            {
                "user_id": user_id,
                "username": display_name,
                "status": "alive"
            }
        ],
        "created_at": datetime.datetime.now(timezone.utc),
        "started_at": None, # Keep useful fields from v2
        "ended_at": None,
        "winner_user_id": None,
    }
    try:
        result = squib_game_sessions.insert_one(new_session_doc)
        new_session_doc["_id"] = result.inserted_id
        return session_id, new_session_doc
    except Exception as e:
        logger.error(f"Failed to insert new session {session_id} into MongoDB: {e}")
        raise # Re-raise the exception to be handled by the command caller

# Using enhanced stats update logic, fixed DB check
async def update_player_stats(winner_id: Optional[str], guild_id: str, participants: List[Dict[str, Any]]) -> int:
    """Updates win/played stats for all participants, returns winner's new win count."""
    # Fixed check: Compare with None
    if squib_game_stats is None:
        logger.error("squib_game_stats collection not available. Cannot update stats.")
        return 0

    winner_new_wins = 0
    if not participants: # Handle empty participant list
        logger.warning("update_player_stats called with empty participants list.")
        return 0

    try:
        bulk_ops = []
        for player in participants:
            player_id = player.get('user_id')
            if not player_id: # Skip if participant data is malformed
                logger.warning(f"Skipping participant with missing user_id: {player}")
                continue

            is_winner = (winner_id is not None and player_id == winner_id)
            bulk_ops.append(
                 UpdateOne( # Use pymongo UpdateOne
                    {"user_id": player_id, "guild_id": guild_id},
                    {
                        "$inc": {
                            "games_played": 1,
                            "wins": 1 if is_winner else 0
                        },
                        # Optionally update username on each game played? Or only on insert?
                        # "$set": {"username": player.get('username', 'Unknown')}
                        "$setOnInsert": {"username": player.get('username', 'Unknown')} # Set username only if new doc created
                    },
                    upsert=True
                )
            )

        if bulk_ops:
             # Perform bulk write
             update_result = squib_game_stats.bulk_write(bulk_ops, ordered=False) # ordered=False allows non-atomic operations
        else:
             logger.warning("No valid participants found to update stats.")


        # Fetch the winner's updated stats separately AFTER the bulk write completes
        if winner_id:
            updated_stats = squib_game_stats.find_one({"user_id": winner_id, "guild_id": guild_id})
            winner_new_wins = updated_stats.get("wins", 0) if updated_stats else 0

        return winner_new_wins
    except Exception as e:
        logger.error(f"Failed to update player stats in MongoDB for guild {guild_id}: {e}", exc_info=True)
        return 0

# Reverted to original function name, incorporating enhanced embed logic, fixed DB checks
async def conclude_game_auto(bot: commands.Bot, interaction: Interaction, game_doc: dict, guild_id: str, final_round: int, winner=None) -> list[Embed]:
    """Conclude a game and determine the winner. Returns list of embeds."""
    # Fixed checks: Compare with None
    if squib_game_sessions is None or squib_game_stats is None:
         logger.error("Database collection not available. Cannot conclude game.")
         error_embed = Embed(title=f"{EMOJI_ERROR} Database Error", description="Could not connect to the database to conclude the game.", color=COLOR_ERROR)
         return [error_embed]

    session_id = game_doc.get('session_id', 'UnknownSession') # Use .get with fallback
    participants = game_doc.get('participants', [])

    # Determine winner if not provided (usually means end of loop)
    winner_determined_by = "N/A" # Default value
    if winner is None:
        alive_players = [p for p in participants if p.get("status") == "alive"]
        total_alive = len(alive_players)

        if total_alive == 1:
            winner = alive_players[0]
            winner_determined_by = "last one standing"
        elif total_alive > 1:
            winner = random.choice(alive_players) # Random among survivors if > 1 somehow remain
            winner_determined_by = "random draw among survivors"
        else: # No one alive
             # Original logic picked random from *all* participants if none alive
             winner = random.choice(participants) if participants else None
             winner_determined_by = "random draw (all eliminated)" if winner else "no survivors"

    # Update game state in DB
    winner_id = winner.get('user_id') if winner else None # Use .get safely
    try:
        squib_game_sessions.update_one(
            {"_id": game_doc["_id"]},
            {"$set": {
                "current_game_state": "completed",
                "winner_user_id": winner_id,
                "ended_at": datetime.datetime.now(timezone.utc) # Add end time
                }}
        )
    except Exception as e:
        logger.error(f"Failed to update session {session_id} to completed state: {e}")
        # Continue anyway, but log it

    # Update Player Stats using the enhanced function
    new_wins = await update_player_stats(winner_id, guild_id, participants)

    # --- Create Final Embed (using enhanced style) ---
    final_embed = Embed(title=f"{EMOJI_GAME} Game Over! {EMOJI_LEADERBOARD}", color=COLOR_GOLD)

    if winner and winner_id:
        winner_username = winner.get('username', 'Unknown Winner')
        winner_avatar = await get_guild_avatar_url(interaction.guild, int(winner_id))
        if winner_avatar:
            final_embed.set_thumbnail(url=winner_avatar)

        final_embed.description = (
            f"After **{final_round}** intense rounds, a winner has emerged!\n\n"
            f"Congratulations to **{winner_username}** (<@{winner_id}>)! {EMOJI_SUCCESS}\n\n"
            f"They survived the challenges and claimed victory.\n"
            f"_(Winner determined by: {winner_determined_by})_\n\n"
            f"They now have **{new_wins}** total wins in this server!"
        )
    else:
         final_embed.description = (
            f"After **{final_round}** grueling rounds, there were no survivors.\n\n"
            f"The Squib Game claims all..."
        )
         final_embed.color = COLOR_WARNING # Use warning color if no winner

    final_embed.set_footer(text=f"Thanks for playing Squib Game! | Session ID: {session_id}")
    final_embed.timestamp = datetime.datetime.now(timezone.utc)

    # Include conditional embed if function exists and returns one
    embeds_to_send = [final_embed]
    try:
        # Check if get_conditional_embed is callable and interaction is valid
        if get_conditional_embed and callable(get_conditional_embed) and interaction:
             # Ensure interaction object is valid for this context if needed by the function
             conditional_embed = await get_conditional_embed(interaction, 'SQUIB_GAME_COMMANDS_EMBED', COLOR_WARNING) # Use appropriate color
             if conditional_embed and isinstance(conditional_embed, Embed): # Check type
                 embeds_to_send.append(conditional_embed)
    except NameError:
         # This happens if get_conditional_embed failed import
         pass # Already logged warning at import time
    except Exception as e:
         logger.error(f"Error calling get_conditional_embed: {e}", exc_info=True)

    # Add premium promotion embed
    try:
        if winner_id:
            promo_embed = get_premium_promotion_embed(winner_id)
            if promo_embed:
                embeds_to_send.append(promo_embed)
    except Exception as e:
        logger.error(f"Error getting premium promotion embed: {e}", exc_info=True)

    return embeds_to_send


# --- Game Loop (Original Structure, adapted for enhanced functions, fixed DB check) ---
async def run_game_loop(bot: commands.Bot, interaction: Interaction, game_db_id: Any, guild_id: str):
    """Run the main game loop for a Squib Game. (Adapted from original structure)"""
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel): # Check if it's a text channel
        logger.error(f"Game loop {game_db_id}: Invalid channel type {type(channel)}. Aborting.")
        return # Stop if channel is invalid

    try:
        while True:
            # Fixed check: Compare with None
            if squib_game_sessions is None:
                 logger.error(f"Game loop {game_db_id}: Database not available. Stopping.")
                 await channel.send(f"{EMOJI_ERROR} Database connection lost. Game aborted.")
                 break

            # Fetch latest game state inside loop
            game = squib_game_sessions.find_one({"_id": game_db_id})

            if not game:
                logger.warning(f"Game loop {game_db_id}: Game document not found. Stopping.")
                break
            current_state = game.get("current_game_state")
            if current_state != "in_progress":
                if current_state == "completed" and interaction:
                     logger.warning(f"Game loop {game_db_id} detected completed state; ensuring final message.")
                     if not game.get("winner_user_id") and not game.get("ended_at"):
                          winner = None
                          final_round = game.get("current_round", 0)
                          final_embeds = await conclude_game_auto(bot, interaction, game, guild_id, final_round, winner=winner)
                          try:
                              await interaction.followup.send(embeds=final_embeds)
                          except discord.HTTPException as e:
                              # Handle cases where followup might fail (e.g., interaction expired)
                              logger.error(f"Failed to send final followup for {game_db_id} after state check: {e}")
                              await channel.send(embeds=final_embeds)
                     else:
                          pass

                break

            current_round = game.get("current_round", 0)
            participants_before = game.get("participants", [])
            alive_before = [p for p in participants_before if p.get("status") == "alive"]

            if len(alive_before) <= 1:
                winner = alive_before[0] if len(alive_before) == 1 else None
                final_embeds = await conclude_game_auto(bot, interaction, game, guild_id, current_round, winner=winner)
                try:
                     await interaction.followup.send(embeds=final_embeds)
                except discord.HTTPException as e:
                     logger.error(f"Failed to send final followup for {game_db_id}: {e}")
                     await channel.send(embeds=final_embeds)
                break # Exit loop

            # --- Play the next round ---
            next_round_num = current_round + 1

            updated_participants, minigame, eliminated_this_round = play_minigame_round(participants_before)
            eliminated_names = [p.get('username', 'Unknown') for p in eliminated_this_round]
            alive_after_round = [p for p in updated_participants if p.get("status") == "alive"]
            survived_this_round = [p for p in alive_after_round if p not in eliminated_this_round]

            # Update DB
            try:
                update_result = squib_game_sessions.update_one(
                    {"_id": game_db_id},
                    {"$set": {"participants": updated_participants}, "$inc": {"current_round": 1}}
                )
                if update_result.matched_count == 0:
                     logger.error(f"Game loop {game_db_id}: Failed to find game document during round update for round {next_round_num}. Stopping.")
                     await channel.send(f"{EMOJI_ERROR} Critical error: Game data lost during round {next_round_num}. Game aborted.")
                     break
            except Exception as e:
                logger.error(f"Game loop {game_db_id}: Failed DB update for round {next_round_num}: {e}. Stopping.")
                await channel.send(f"{EMOJI_ERROR} Database error during round {next_round_num}. Game aborted.")
                break

            # --- Announce Round Results (using enhanced generation) ---
            round_flavor = generate_round_flavor_text(minigame, eliminated_this_round, survived_this_round)

            round_embed = Embed(
                title=f"{EMOJI_ROUND} Round {next_round_num}: {minigame.get('name', '???')} {minigame.get('emoji', '')}",
                description=round_flavor,
                color=COLOR_DEFAULT
            )

            elim_field_value = format_player_list([f"**{name}**" for name in eliminated_names]) if eliminated_names else "None"
            # Show usernames for alive players in round summary
            alive_field_value = format_player_list([p.get('username', 'Unknown') for p in alive_after_round])

            round_embed.add_field(name=f"{EMOJI_ELIMINATED} Eliminated This Round ({len(eliminated_names)})", value=elim_field_value, inline=False)
            round_embed.add_field(name=f"{EMOJI_ALIVE} Remaining Players ({len(alive_after_round)})", value=alive_field_value, inline=False)

            # Try setting thumbnail (adapted from v2)
            thumb_player = random.choice(eliminated_this_round) if eliminated_this_round else random.choice(alive_after_round) if alive_after_round else None
            if thumb_player and thumb_player.get('user_id'):
                avatar_url = await get_guild_avatar_url(interaction.guild, int(thumb_player['user_id']))
                if avatar_url:
                    round_embed.set_thumbnail(url=avatar_url)

            round_embed.set_footer(text=f"Next round starts in {ROUND_DELAY_SECONDS} seconds...")
            round_embed.timestamp = datetime.datetime.now(timezone.utc)

            # Send round update using interaction.followup (as in original structure)
            try:
                await interaction.followup.send(embed=round_embed)
            except discord.HTTPException as e:
                 logger.warning(f"Failed to send followup for round {next_round_num} of {game_db_id} (Interaction might have expired): {e}. Sending to channel.")
                 await channel.send(embed=round_embed) # Fallback

            await asyncio.sleep(ROUND_DELAY_SECONDS)

    except asyncio.CancelledError:
         pass
    except Exception as e:
        logger.error(f"Unexpected error in game loop for {game_db_id}: {e}", exc_info=True)
        try:
            # Try to inform the channel about the error
            await channel.send(f"{EMOJI_ERROR} A critical error occurred in the game loop. The game has been stopped.")
            # Attempt to mark game as errored/cancelled in DB
            if squib_game_sessions is not None: # Check again before using
                 squib_game_sessions.update_one(
                      {"_id": game_db_id, "current_game_state": "in_progress"}, # Only update if still marked as in_progress
                      {"$set": {"current_game_state": "errored"}}
                 )
        except Exception as report_e:
             logger.error(f"Failed to report game loop error or update DB for {game_db_id}: {report_e}")

    finally:
        pass


# --- Views (Reverted to original Join Button View, fixed DB check) ---

class JoinButtonView(View):
    """View with a button for joining a Squib Game."""

    def __init__(self, game_id: str, guild_id: str):
        super().__init__(timeout=None) # Persistent view until game starts or is invalid
        self.game_id = game_id
        self.guild_id = guild_id
        # Button added via decorator

    def disable_all_buttons(self):
        """Disables all buttons in this view."""
        for child in self.children:
            if isinstance(child, Button):
                child.disabled = True

    async def update_player_count_embed(self, interaction: Interaction, player_count: int):
         """Updates the player count embed (assumed to be the second embed)."""
         # Check if message exists and has enough embeds
         if not interaction.message or len(interaction.message.embeds) < 2:
             logger.warning(f"Could not find player count embed to update for game {self.game_id}")
             return

         try:
             embeds = interaction.message.embeds
             main_embed = embeds[0]
             player_embed = embeds[1] # The one to update

             # Determine capacity text based on host entitlements
             cap_text = "∞"
             try:
                 from services.premium import get_user_entitlements
                 # Get host_id from game document, then get their entitlements
                 if squib_game_sessions is not None:
                     game = squib_game_sessions.find_one({"guild_id": self.guild_id, "session_id": self.game_id})
                     if game:
                         host_id = str(game.get("host_user_id"))
                         ent = get_user_entitlements(host_id)
                         if ent:
                             cap = ent.get("squibgamesMaxPlayers")
                             if isinstance(cap, int) and cap > 0:
                                 cap_text = str(cap)
             except Exception:
                 pass

             new_description = f"{player_count}/{cap_text} Players joined."
             # Recreate embed to ensure changes apply (safer than modifying fields)
             new_player_embed = Embed(
                 # Keep original title if it exists, otherwise None
                 title=player_embed.title if hasattr(player_embed, 'title') else None,
                 description=new_description,
                 color=COLOR_SUCCESS # Use consistent color
             )
             # Copy footer if it exists
             if player_embed.footer and player_embed.footer.text:
                  new_player_embed.set_footer(text=player_embed.footer.text, icon_url=player_embed.footer.icon_url or Embed.Empty)

             await interaction.message.edit(embeds=[main_embed, new_player_embed], view=self)
         except discord.NotFound:
              logger.warning(f"Original message for game {self.game_id} not found when updating player count.")
         except discord.HTTPException as e:
             logger.error(f"Failed to edit message to update player count for game {self.game_id}: {e}")
         except Exception as e:
             logger.error(f"Unexpected error updating player count embed for game {self.game_id}: {e}", exc_info=True)


    @discord.ui.button(label="Join", style=ButtonStyle.primary, emoji=EMOJI_JOIN, custom_id="squib_join_button") # Unique custom_id
    async def join_button(self, interaction: Interaction, button: Button):
        """Allows a user to join the game via the button."""
        await interaction.response.defer(ephemeral=True, thinking=True) # Respond privately

        # Fixed check: Compare with None
        if squib_game_sessions is None:
            await interaction.followup.send(f"{EMOJI_ERROR} Database connection error. Cannot join game.", ephemeral=True)
            return

        try:
            # Find the specific game this button belongs to
            game = squib_game_sessions.find_one({
                "guild_id": self.guild_id,
                "session_id": self.game_id,
            })

            if not game:
                await interaction.followup.send("This Squib Game session could not be found or is no longer active.", ephemeral=True)
                self.disable_all_buttons()
                # Try to edit the original message if possible
                if interaction.message:
                    try:
                        await interaction.message.edit(view=self) # Update message to show disabled button
                    except discord.NotFound:
                         logger.warning(f"Original message for game {self.game_id} not found when disabling join button.")
                    except discord.HTTPException as e:
                         logger.error(f"Failed to edit message to disable join button for {self.game_id}: {e}")
                return

            # Check game state *after* finding the game doc
            if game.get("current_game_state") != "waiting_for_players":
                await interaction.followup.send(f"{EMOJI_WARNING} This game has already started or finished. You can no longer join.", ephemeral=True)
                self.disable_all_buttons()
                if interaction.message:
                    try:
                        await interaction.message.edit(view=self)
                    except discord.NotFound:
                         logger.warning(f"Original message for game {self.game_id} not found when disabling join button (already started).")
                    except discord.HTTPException as e:
                         logger.error(f"Failed to edit message to disable join button for already started game {self.game_id}: {e}")
                return

            user_id = str(interaction.user.id)
            participants = game.get("participants", [])

            # Enforce max players based on host entitlements if specified
            try:
                host_id = str(game.get("host_user_id"))
                ent = get_user_entitlements(host_id)
                cap = ent.get("squibgamesMaxPlayers")
                if isinstance(cap, int) and cap > 0:
                    # Don't allow join if cap reached
                    if len(participants) >= cap:
                        await interaction.followup.send(
                            f"{EMOJI_WARNING} This session has reached the maximum of {cap} players for the host's tier.",
                            ephemeral=True,
                        )
                        return
            except Exception as e:
                logger.error(f"Error determining Squib Games cap: {e}")

            # Check if already joined
            if any(p.get("user_id") == user_id for p in participants):
                await interaction.followup.send("You are already in this game session.", ephemeral=True)
                return

            # Add participant
            new_participant = {
                "user_id": user_id,
                "username": interaction.user.display_name, # Use display_name
                "status": "alive"
            }
            result = squib_game_sessions.update_one(
                {"_id": game["_id"]},
                {"$push": {"participants": new_participant}}
            )

            if result.modified_count == 1:
                await interaction.followup.send(f"{EMOJI_SUCCESS} You have joined the Squib Game!", ephemeral=True)
                # Update the player count embed on the original message
                await self.update_player_count_embed(interaction, len(participants) + 1)
            else:
                 # This might happen if the document was modified between find_one and update_one
                 logger.warning(f"Failed to add participant {user_id} to game {self.game_id}. Modified count was 0.")
                 await interaction.followup.send(f"{EMOJI_ERROR} Failed to add you to the game session in the database. Please try again.", ephemeral=True)

        except Exception as e:
            logger.error(f"Error in join_button for game {self.game_id}: {e}", exc_info=True)
            await interaction.followup.send(f"{EMOJI_ERROR} An unexpected error occurred while trying to join.", ephemeral=True)


# --- Main Cog Class (Reverted Structure, fixed DB checks) ---

class SquibGames(commands.GroupCog, name="squibgames"): # Reverted name
    """Squib Games cog for multi-minigame challenge sessions."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.run_tasks: Dict[str, asyncio.Task] = {}
        if mongo_client is None: # Fixed check
             logger.critical("SquibGames initialized WITHOUT a MongoDB connection.")

    # Cleanup tasks on cog unload
    def cog_unload(self):
        """Cancel any running game loop tasks when the cog is unloaded."""
        for task in self.run_tasks.values():
            task.cancel()
        self.run_tasks.clear()


    @app_commands.command(name="start", description="Start a new multi-minigame Squib Game session")
    @app_commands.checks.cooldown(1, 60, key=lambda i: i.guild_id)
    async def start(self, interaction: Interaction):
        """Starts a new Squib Game session and allows players to join."""
        await interaction.response.defer(thinking=True) # Defer response

        # Fixed check: Compare with None
        if squib_game_sessions is None:
            await interaction.followup.send(f"{EMOJI_ERROR} Database is not connected. Cannot start game.", ephemeral=True)
            return

        guild_id = str(interaction.guild_id)
        user_id = str(interaction.user.id)

        # Check for existing game (using enhanced check)
        try:
            existing_game = squib_game_sessions.find_one({
                "guild_id": guild_id,
                "current_game_state": {"$in": ["waiting_for_players", "in_progress"]}
            })
        except Exception as e:
             logger.error(f"Database error checking for existing game in guild {guild_id}: {e}")
             await interaction.followup.send(f"{EMOJI_ERROR} Database error checking for existing games. Please try again.", ephemeral=True)
             return


        if existing_game:
            state = existing_game.get('current_game_state', 'unknown').replace('_',' ')
            host_mention = f"<@{existing_game.get('host_user_id', 'Unknown')}>"
            embed = Embed(
                title=f"{EMOJI_WARNING} Session Already Exists",
                description=f"A Squib Game session is already `{state}` in this server, hosted by {host_mention}.\nPlease wait for it to conclude.",
                color=COLOR_WARNING
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        try:
            # Create session using original function name
            session_id, new_session_doc = create_new_session(guild_id, user_id, interaction.user.display_name)
        except ConnectionError: # Catch specific error from create_new_session
             await interaction.followup.send(f"{EMOJI_ERROR} Database connection error prevented session creation.", ephemeral=True)
             return
        except Exception as e:
             logger.error(f"Error creating session in /start: {e}", exc_info=True)
             await interaction.followup.send(f"{EMOJI_ERROR} Failed to create the game session. Please try again.", ephemeral=True)
             return

        host_avatar = await get_guild_avatar_url(interaction.guild, int(user_id))

        # Main Embed (using enhanced style)
        main_embed = Embed(
            title=f"{EMOJI_START} New Squib Game Session Created!",
            description=(
                f"A new session has been created by {interaction.user.mention}!\n\n"
                f"Click the **Join** button below to enter.\n"
                f"The host needs to use `/squibgames run` to start the rounds once enough players have joined (min {MIN_PLAYERS})."
            ),
            color=COLOR_WAITING # Use waiting color
        )
        if host_avatar:
            main_embed.set_thumbnail(url=host_avatar)
        main_embed.set_footer(text=f"Session ID: {session_id} | Get ready!")
        main_embed.timestamp = new_session_doc.get('created_at', datetime.datetime.now(timezone.utc)) # Use .get


        # Player Count Embed (now shows capacity based on host entitlements)
        try:
            from services.premium import get_user_entitlements
            ent = get_user_entitlements(user_id)
            cap = ent.get("squibgamesMaxPlayers")
            cap_text = str(cap) if isinstance(cap, int) and cap > 0 else "∞"
        except Exception:
            cap_text = "∞"
        player_embed = Embed(
            description=f"1/{cap_text} Players joined.",
            color=COLOR_SUCCESS
        )

        # Attach the original Join Button View
        view = JoinButtonView(game_id=session_id, guild_id=guild_id)
        await interaction.followup.send(embeds=[main_embed, player_embed], view=view)


    @app_commands.command(name="run", description="Run all minigame rounds until one winner remains")
    @app_commands.checks.cooldown(1, 15, key=lambda i: i.guild_id) # Slightly shorter cooldown maybe
    async def run(self, interaction: Interaction):
        """Starts the rounds for the currently waiting Squib Game."""
        # Defer after finding the game, as we might need ephemeral response first
        # Fixed check: Compare with None
        if squib_game_sessions is None:
            await interaction.response.send_message(f"{EMOJI_ERROR} Database is not connected. Cannot run game.", ephemeral=True)
            return

        guild_id = str(interaction.guild_id)

        # Find the game waiting for players
        try:
            game = squib_game_sessions.find_one({
                "guild_id": guild_id,
                "current_game_state": "waiting_for_players" # Only run games that are waiting
            })
        except Exception as e:
             logger.error(f"Database error finding waiting game in guild {guild_id}: {e}")
             await interaction.response.send_message(f"{EMOJI_ERROR} Database error finding waiting game. Please try again.", ephemeral=True)
             return

        if not game:
            embed = Embed(
                title=f"{EMOJI_INFO} No Waiting Game Found",
                description="There is no Squib Game session currently waiting for players in this server. Use `/squibgames start` first.",
                color=COLOR_WARNING # Changed to WARNING as it's an actionable info
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check if the user running the command is the host
        if str(interaction.user.id) != game.get("host_user_id"):
            host_mention = f"<@{game.get('host_user_id', 'Unknown')}>"
            embed = Embed(
                title=f"{EMOJI_WARNING} Host Only Command",
                description=f"Only the host ({host_mention}) can start the rounds using `/squibgames run`.",
                color=COLOR_WARNING
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check for minimum players
        participants = game.get("participants", [])
        if len(participants) < MIN_PLAYERS:
            embed = Embed(
                title=f"{EMOJI_WARNING} Not Enough Players",
                description=f"You need at least **{MIN_PLAYERS} players** to start the rounds. Currently {len(participants)}.",
                color=COLOR_WARNING
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # --- Start the Game Rounds ---
        await interaction.response.defer() # Now defer the public response

        session_id = game.get('session_id', 'UnknownSession')
        db_id = game.get('_id')
        if not session_id or not db_id:
             logger.error(f"Missing session_id or _id in game document for guild {guild_id}")
             await interaction.followup.send(f"{EMOJI_ERROR} Critical error: Game data is corrupted. Cannot start rounds.", ephemeral=True)
             return


        # Update game state to in_progress
        try:
            update_result = squib_game_sessions.update_one(
                {"_id": db_id},
                {"$set": {
                    "current_game_state": "in_progress",
                    "started_at": datetime.datetime.now(timezone.utc) # Add start time
                    }}
            )
            if update_result.matched_count == 0:
                 logger.error(f"Failed to find game {session_id} to update state to in_progress.")
                 await interaction.followup.send(f"{EMOJI_ERROR} Failed to update the game state in the database (game not found). Cannot start rounds.", ephemeral=True)
                 return

        except Exception as e:
             logger.error(f"Failed to update game state to in_progress for {session_id}: {e}", exc_info=True)
             await interaction.followup.send(f"{EMOJI_ERROR} Failed to update the game state in the database. Cannot start rounds.", ephemeral=True)
             return

        # Disable button on the original /start message (Attempt - best effort)
        try:
            # Skipping disabling join button (reverted logic).
            pass
        except Exception as e:
             logger.error(f"Could not disable join button on start message for {session_id}: {e}")


        # Send start confirmation message
        host_avatar = await get_guild_avatar_url(interaction.guild, int(game["host_user_id"]))
        start_embed = Embed(
            title=f"{EMOJI_RUN} Squib Game Rounds Starting!",
            description=(
                f"The host {interaction.user.mention} has started the rounds!\n"
                f"**{len(participants)}** players are competing. Good luck!\n\n"
                f"{EMOJI_ROUND} The game will now proceed automatically..."
            ),
            color=COLOR_IN_PROGRESS
        )
        if host_avatar:
            start_embed.set_thumbnail(url=host_avatar)

        try:
            await interaction.followup.send(embed=start_embed) # Send public confirmation
        except discord.HTTPException as e:
             logger.error(f"Failed to send start confirmation for game {session_id}: {e}")
             # Attempt to send to channel if followup fails
             if interaction.channel:
                  await interaction.channel.send(embed=start_embed, content=f"{EMOJI_WARNING} Game starting (interaction followup failed).")
             return # Don't start loop if we can't confirm

        # Start the game loop task (using original structure)
        if session_id in self.run_tasks:
            logger.warning(f"Task already exists for session {session_id}. Cancelling old one.")
            self.run_tasks[session_id].cancel()

        # Pass necessary arguments based on original run_game_loop signature
        # Ensure db_id is passed correctly
        task = asyncio.create_task(
            run_game_loop(self.bot, interaction, db_id, guild_id)
        )
        self.run_tasks[session_id] = task

        # Add callback to remove task from dict when done/cancelled
        def cleanup_task(fut: asyncio.Task):
            # Ensure removal happens even if task raises exception
            try:
                # Log exception if one occurred in the task
                if fut.cancelled():
                    pass
                elif fut.exception():
                    exc = fut.exception()
                    logger.error(f"Game loop task {session_id} raised an exception: {exc}", exc_info=exc)
            except Exception as cb_e:
                 # Log errors within the callback itself
                 logger.error(f"Error during game loop task cleanup callback for {session_id}: {cb_e}", exc_info=True)
            finally:
                 # Remove task from tracking dict regardless of outcome
                 if session_id in self.run_tasks:
                     del self.run_tasks[session_id]

        task.add_done_callback(cleanup_task)


    @app_commands.command(name="status", description="View the current Squib Game session status")
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.guild_id)
    async def status(self, interaction: Interaction):
        """Displays the status of the current game session."""
        await interaction.response.defer(ephemeral=True) # Check status privately

        # Fixed check: Compare with None
        if squib_game_sessions is None:
            await interaction.followup.send(f"{EMOJI_ERROR} Database is not connected. Cannot check status.", ephemeral=True)
            return

        guild_id = str(interaction.guild_id)
        try:
            game = squib_game_sessions.find_one({
                "guild_id": guild_id,
                "current_game_state": {"$in": ["waiting_for_players", "in_progress"]}
            })
        except Exception as e:
             logger.error(f"Database error finding active game in guild {guild_id} for status: {e}")
             await interaction.followup.send(f"{EMOJI_ERROR} Database error checking game status. Please try again.", ephemeral=True)
             return

        if not game:
            embed = Embed(
                title=f"{EMOJI_INFO} No Active Session", # Using INFO emoji, but WARNING color for visibility
                description="No Squib Game session is currently active or waiting in this server.",
                color=COLOR_WARNING
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Game found, prepare status embed (using enhanced style)
        state = game.get('current_game_state', 'Unknown').replace('_', ' ').title()
        state_emoji = EMOJI_WAITING if state == 'Waiting For Players' else EMOJI_IN_PROGRESS
        current_round = game.get('current_round', 0)
        host_id = game.get('host_user_id')
        participants = game.get('participants', [])
        alive_players = [p for p in participants if p.get("status") == "alive"]
        eliminated_players = [p for p in participants if p.get("status") == "eliminated"]

        status_embed = Embed(
            title=f"{EMOJI_STATUS} Current Squib Game Status",
            description=f"**State:** {state_emoji} `{state}`\n**Host:** <@{host_id}>",
            color=COLOR_WAITING if state == 'Waiting For Players' else COLOR_IN_PROGRESS
        )

        if state == 'In Progress':
             status_embed.description += f"\n**Current Round:** {EMOJI_ROUND} `{current_round}`"

        host_avatar = await get_guild_avatar_url(interaction.guild, int(host_id)) if host_id else None
        if host_avatar:
            status_embed.set_thumbnail(url=host_avatar)

        # Use helper functions for formatting lists
        alive_mentions = get_player_mentions(alive_players, "alive")
        eliminated_mentions = get_player_mentions(eliminated_players, "eliminated") # Get mentions for eliminated

        status_embed.add_field(
            name=f"{EMOJI_ALIVE} Alive Players ({len(alive_players)})",
            value=format_player_list(alive_mentions) or "None", # Show mentions, handle empty list
            inline=False
        )
        status_embed.add_field(
            name=f"{EMOJI_ELIMINATED} Eliminated Players ({len(eliminated_players)})",
            value=format_player_list(eliminated_mentions) or "None", # Show mentions, handle empty list
            inline=False
        )

        status_embed.set_footer(text=f"Session ID: {game.get('session_id', 'N/A')}") # Use .get
        status_embed.timestamp = datetime.datetime.now(timezone.utc)

        # Send status publicly using followup on the deferred ephemeral response
        await interaction.followup.send(embed=status_embed, ephemeral=False)


    @app_commands.command(name="cancel", description="Cancel the current Squib Game session (host only)")
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.guild_id)
    async def cancel(self, interaction: Interaction):
        """Cancels the active or waiting Squib Game session. Only the host can cancel."""
        await interaction.response.defer(ephemeral=True)

        if squib_game_sessions is None:
            await interaction.followup.send(f"{EMOJI_ERROR} Database is not connected. Cannot cancel session.", ephemeral=True)
            return

        guild_id = str(interaction.guild_id)
        user_id = str(interaction.user.id)

        try:
            game = squib_game_sessions.find_one({
                "guild_id": guild_id,
                "current_game_state": {"$in": ["waiting_for_players", "in_progress"]}
            })
        except Exception as e:
            logger.error(f"Database error finding active game for cancel in guild {guild_id}: {e}")
            await interaction.followup.send(f"{EMOJI_ERROR} Database error finding session. Please try again.", ephemeral=True)
            return

        if not game:
            await interaction.followup.send(f"{EMOJI_INFO} No active session to cancel.", ephemeral=True)
            return

        host_id = str(game.get("host_user_id"))
        if user_id != host_id:
            await interaction.followup.send(f"{EMOJI_ERROR} Only the host (<@{host_id}>) can cancel this session.", ephemeral=True)
            return

        session_id = game.get("session_id", "UnknownSession")

        # Cancel run loop if present
        try:
            task = self.run_tasks.get(session_id)
            if task and not task.done():
                task.cancel()
        except Exception as e:
            logger.warning(f"Failed to cancel run task for session {session_id}: {e}")

        # Update DB to cancelled
        try:
            squib_game_sessions.update_one(
                {"_id": game["_id"]},
                {"$set": {"current_game_state": "cancelled", "ended_at": datetime.datetime.now(timezone.utc)}}
            )
        except Exception as e:
            logger.error(f"Failed to mark session {session_id} as cancelled: {e}")

        # Confirmation embeds
        confirm_embed = Embed(
            title=f"{EMOJI_STOP} Session Cancelled",
            description=(
                f"The Squib Game session has been cancelled by {interaction.user.mention}.\n"
                f"Session ID: `{session_id}`"
            ),
            color=COLOR_ERROR
        )

        # Send public confirmation in channel
        try:
            await interaction.followup.send(embed=confirm_embed, ephemeral=False)
        except discord.HTTPException:
            # Fallback to channel send if followup fails
            if interaction.channel:
                await interaction.channel.send(embed=confirm_embed)

    # --- Error Handling (Generic for the group, fixed DB check) ---
    async def cog_app_command_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        """Handles errors for the squibgames commands."""
        original_error = getattr(error, 'original', error) # Get original error if wrapped

        if isinstance(error, app_commands.CommandOnCooldown):
            message = f"{EMOJI_WARNING} This command is on cooldown. Please try again in {error.retry_after:.2f} seconds."
        elif isinstance(error, app_commands.CheckFailure):
             message = f"{EMOJI_ERROR} You do not have the necessary permissions to use this command."
        # Check for the specific ConnectionError raised in the code now
        elif isinstance(original_error, ConnectionError) and "Database not initialized" in str(original_error):
             message = f"{EMOJI_ERROR} Database connection error. Please try again later or contact admin."
        # Catch general PyMongo connection errors during command execution
        elif isinstance(original_error, ConnectionFailure):
             logger.error(f"Database ConnectionFailure during '{interaction.command.name if interaction.command else 'Unknown'}' command: {original_error}")
             message = f"{EMOJI_ERROR} Could not connect to the database. Please try again later."
        else:
            logger.error(f"Unhandled error in squibgames command '{interaction.command.name if interaction.command else 'Unknown'}': {error}", exc_info=error)
            message = f"{EMOJI_ERROR} An unexpected error occurred. Please try again later."

        # Send error message ephemerally
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


# --- Setup Function (Fixed DB check) ---
async def setup(bot: commands.Bot):
    """Adds the SquibGames cog to the bot."""
    # Fixed check: Compare with None
    if mongo_client is None:
         logger.error("Cannot add SquibGames cog: MongoDB connection failed or MONGODB_URI not set.")
         print("[SquibGames] Cog not loaded due to MongoDB connection failure or missing URI.")
    else:
        try:
            await bot.add_cog(SquibGames(bot))
        except Exception as e:
             logger.critical(f"Failed to load SquibGames cog: {e}", exc_info=True)
             print(f"[SquibGames] CRITICAL: Failed to load cog: {e}")

