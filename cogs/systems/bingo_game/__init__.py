# Standard Library Imports
import random
import asyncio
import logging
import datetime
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import timezone

# Discord Imports
import discord
from discord.ext import commands
from discord import app_commands, Interaction, Embed, Color, ButtonStyle
from discord.ui import View, Button
from services.premium import get_user_entitlements
from ui.embeds import get_premium_promotion_embed, get_premium_promotion_view

# Third-Party Imports
from pymongo import MongoClient
from pymongo.collection import Collection, UpdateOne
from pymongo.database import Database
from pymongo.errors import ConnectionFailure

# --- Logging Setup ---
logger = logging.getLogger(__name__)

# Local Application/Library Specific Imports
try:
    from core.utils import get_conditional_embed
except ImportError:
    logger.warning("core.utils.get_conditional_embed not found. Conditional embeds disabled.")
    get_conditional_embed = None

try:
    from config.settings import MONGODB_URI
except ImportError:
     logger.critical("config.settings.MONGODB_URI not found. Database functionality disabled.")
     MONGODB_URI = None


# --- Constants ---
# Emojis for UI elements
EMOJI_JOIN = "✅"
EMOJI_START = "🎲"
EMOJI_BINGO = "🎉"
EMOJI_CARD = "🎫"
EMOJI_STATUS = "📊"
EMOJI_LEADERBOARD = "🏆"
EMOJI_STOP = "🛑"
EMOJI_HOST = "👑"
EMOJI_WAITING = "⏳"
EMOJI_IN_PROGRESS = "⚙️"
EMOJI_COMPLETED = "🏁"
EMOJI_ERROR = "❌"
EMOJI_WARNING = "⚠️"
EMOJI_INFO = "ℹ️"
EMOJI_SUCCESS = "🎉"
EMOJI_NUMBER = "🔢"
EMOJI_HALFWAY = "⏸️"

# Embed Colors
COLOR_DEFAULT = Color.blue()
COLOR_SUCCESS = Color.green()
COLOR_ERROR = Color.red()
COLOR_WARNING = Color.orange()
COLOR_GOLD = Color.gold()
COLOR_WAITING = Color.light_grey()
COLOR_IN_PROGRESS = Color.dark_blue()
COLOR_PURPLE = Color.purple()

# Game Settings
MIN_PLAYERS = 2
MAX_PLAYERS_FREE = 10
MAX_PLAYERS_SUPPORTER = 20
MAX_PLAYERS_SPONSOR = 50
MAX_PLAYERS_VIP = -1  # Unlimited
BINGO_CARD_SIZE = 5
BINGO_RANGE_MIN = 1
BINGO_RANGE_MAX = 75
NUMBER_CALL_DELAY = 8  # Seconds between number calls
HALFWAY_POINT_RATIO = 0.4  # Show leaderboard at 40% of numbers called


# --- Database Setup ---
mongo_client: Optional[MongoClient] = None
db: Optional[Database] = None
bingo_sessions: Optional[Collection] = None
bingo_stats: Optional[Collection] = None
bingo_global_stats: Optional[Collection] = None

try:
    if MONGODB_URI:
        mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=30000, connectTimeoutMS=20000, socketTimeoutMS=20000)
        mongo_client.admin.command('ping')
        db = mongo_client['astrostats_database']
        bingo_sessions = db['bingo_sessions']
        bingo_stats = db['bingo_stats']
        bingo_global_stats = db['bingo_global_stats']
        logger.info("Bingo: MongoDB connection established")
    else:
        logger.warning("MONGODB_URI not set in config.settings. Database functionality will be disabled.")

except ConnectionFailure as e:
    logger.critical(f"MongoDB Connection Failure: Could not connect to server. {e}")
    mongo_client = None
    db = None
    bingo_sessions = None
    bingo_stats = None
    bingo_global_stats = None
except Exception as e:
    logger.critical(f"Failed to initialize MongoDB connection: {e}", exc_info=True)
    mongo_client = None
    db = None
    bingo_sessions = None
    bingo_stats = None
    bingo_global_stats = None


# --- Helper Functions ---

def generate_bingo_card() -> List[List[int]]:
    """Generate a random 5x5 bingo card with numbers 1-75."""
    card = []
    # B column: 1-15, I column: 16-30, N column: 31-45, G column: 46-60, O column: 61-75
    ranges = [
        (1, 15),    # B
        (16, 30),   # I
        (31, 45),   # N
        (46, 60),   # G
        (61, 75)    # O
    ]
    
    for col_idx, (min_val, max_val) in enumerate(ranges):
        column = random.sample(range(min_val, max_val + 1), BINGO_CARD_SIZE)
        card.append(column)
    
    # Transpose to get rows instead of columns
    card = [[card[col][row] for col in range(BINGO_CARD_SIZE)] for row in range(BINGO_CARD_SIZE)]
    
    # Set center as FREE space (represented as 0)
    card[2][2] = 0
    
    return card


def format_bingo_card(card: List[List[int]], marked: Set[int]) -> str:
    """Format a bingo card for display with marked numbers."""
    header = "```\n  B     I     N     G     O  \n"
    separator = "----+-----+-----+-----+-----\n"
    lines = []
    
    for row_idx, row in enumerate(card):
        row_str = ""
        for col_idx, num in enumerate(row):
            if num == 0:  # FREE space
                cell = " FREE"
            elif num in marked:
                cell = f"[{num:2d}]"
            else:
                cell = f" {num:2d} "
            
            row_str += cell
            if col_idx < 4:  # Add separator between columns
                row_str += " |"
        
        lines.append(row_str)
        if row_idx < 4:  # Add separator between rows
            lines.append(separator)
    
    return header + separator + "\n".join(lines) + "\n```"


def check_bingo(card: List[List[int]], marked: Set[int]) -> bool:
    """Check if a card has a bingo (row, column, or diagonal)."""
    # Check rows
    for row in card:
        if all(num == 0 or num in marked for num in row):
            return True
    
    # Check columns
    for col in range(BINGO_CARD_SIZE):
        if all(card[row][col] == 0 or card[row][col] in marked for row in range(BINGO_CARD_SIZE)):
            return True
    
    # Check diagonals
    if all(card[i][i] == 0 or card[i][i] in marked for i in range(BINGO_CARD_SIZE)):
        return True
    if all(card[i][BINGO_CARD_SIZE - 1 - i] == 0 or card[i][BINGO_CARD_SIZE - 1 - i] in marked for i in range(BINGO_CARD_SIZE)):
        return True
    
    return False


def count_remaining_numbers(card: List[List[int]], marked: Set[int]) -> int:
    """Count how many numbers remain unmarked on a card."""
    count = 0
    for row in card:
        for num in row:
            if num != 0 and num not in marked:
                count += 1
    return count


def get_max_players_for_entitlements(entitlements: Dict[str, Any]) -> int:
    """Get max players allowed based on user entitlements."""
    max_players = entitlements.get("bingoMaxPlayers", MAX_PLAYERS_FREE)
    # -1 means unlimited, return it as is (will be handled in display)
    return max_players


async def safe_send_with_view(channel_or_interaction, embeds=None, view=None, content=None, ephemeral=False):
    """
    Safely sends a message with embeds and view, handling Discord's 15-minute timeout.
    Falls back to channel.send if interaction.followup fails.
    """
    try:
        if channel_or_interaction is None:
            raise AttributeError("Interaction is None")
            
        if hasattr(channel_or_interaction, 'followup') and not channel_or_interaction.response.is_done():
            if embeds and view is not None:
                return await channel_or_interaction.followup.send(embeds=embeds, view=view, content=content, ephemeral=ephemeral)
            elif embeds:
                return await channel_or_interaction.followup.send(embeds=embeds, content=content, ephemeral=ephemeral)
            elif view is not None:
                return await channel_or_interaction.followup.send(view=view, content=content, ephemeral=ephemeral)
            else:
                return await channel_or_interaction.followup.send(content=content, ephemeral=ephemeral)
        else:
            channel = channel_or_interaction if hasattr(channel_or_interaction, 'send') else channel_or_interaction.channel
            if embeds and view is not None:
                return await channel.send(embeds=embeds, view=view, content=content)
            elif embeds:
                return await channel.send(embeds=embeds, content=content)
            elif view is not None:
                return await channel.send(view=view, content=content)
            else:
                return await channel.send(content=content)
    except (discord.HTTPException, AttributeError) as e:
        logger.error(f"Failed to send message via interaction or channel: {e}")
        raise


def create_new_session(guild_id: str, user_id: str, display_name: str) -> Tuple[str, dict]:
    """Create a new Bingo Game session."""
    if bingo_sessions is None:
        logger.error("bingo_sessions collection is not available.")
        raise ConnectionError("Database not initialized")

    session_id = f"{guild_id}_{user_id}_{int(datetime.datetime.now(timezone.utc).timestamp())}"
    new_session_doc = {
        "guild_id": guild_id,
        "host_user_id": user_id,
        "session_id": session_id,
        "current_game_state": "waiting_for_players",
        "participants": [
            {
                "user_id": user_id,
                "username": display_name,
                "card": generate_bingo_card(),
                "marked": [],
                "has_bingo": False
            }
        ],
        "called_numbers": [],
        "created_at": datetime.datetime.now(timezone.utc),
        "started_at": None,
        "ended_at": None,
        "winner_user_ids": [],
        "halfway_break_shown": False
    }
    try:
        result = bingo_sessions.insert_one(new_session_doc)
        new_session_doc["_id"] = result.inserted_id
        return session_id, new_session_doc
    except Exception as e:
        logger.error(f"Failed to insert new session {session_id} into MongoDB: {e}")
        raise


async def update_player_stats(winner_ids: List[str], guild_id: str, participants: List[Dict[str, Any]]) -> Dict[str, int]:
    """Updates win/played stats for all participants. Returns dict of winner_id -> new win count."""
    if bingo_stats is None or bingo_global_stats is None:
        logger.error("Stats collections not available. Cannot update stats.")
        return {}

    winner_new_wins = {}
    if not participants:
        logger.warning("update_player_stats called with empty participants list.")
        return {}

    try:
        # Update server stats
        bulk_ops = []
        global_bulk_ops = []
        
        for player in participants:
            player_id = player.get('user_id')
            if not player_id:
                logger.warning(f"Skipping participant with missing user_id: {player}")
                continue

            is_winner = player_id in winner_ids
            
            # Server stats
            bulk_ops.append(
                UpdateOne(
                    {"user_id": player_id, "guild_id": guild_id},
                    {
                        "$inc": {
                            "games_played": 1,
                            "wins": 1 if is_winner else 0
                        },
                        "$setOnInsert": {"username": player.get('username', 'Unknown')}
                    },
                    upsert=True
                )
            )
            
            # Global stats
            global_bulk_ops.append(
                UpdateOne(
                    {"user_id": player_id},
                    {
                        "$inc": {
                            "games_played": 1,
                            "wins": 1 if is_winner else 0
                        },
                        "$setOnInsert": {"username": player.get('username', 'Unknown')}
                    },
                    upsert=True
                )
            )

        if bulk_ops:
            bingo_stats.bulk_write(bulk_ops, ordered=False)
            bingo_global_stats.bulk_write(global_bulk_ops, ordered=False)
        else:
            logger.warning("No valid participants found to update stats.")

        # Fetch updated stats for winners
        for winner_id in winner_ids:
            updated_stats = bingo_stats.find_one({"user_id": winner_id, "guild_id": guild_id})
            winner_new_wins[winner_id] = updated_stats.get("wins", 0) if updated_stats else 0

        return winner_new_wins
    except Exception as e:
        logger.error(f"Failed to update player stats in MongoDB for guild {guild_id}: {e}", exc_info=True)
        return {}


async def conclude_game(bot: commands.Bot, interaction: Interaction, game_doc: dict, guild_id: str, winners: List[Dict[str, Any]]) -> List[Embed]:
    """Conclude a game and determine the winners. Returns list of embeds."""
    if bingo_sessions is None or bingo_stats is None:
        logger.error("Database collection not available. Cannot conclude game.")
        error_embed = Embed(title=f"{EMOJI_ERROR} Database Error", description="Could not connect to the database to conclude the game.", color=COLOR_ERROR)
        return [error_embed]

    session_id = game_doc.get('session_id', 'UnknownSession')
    participants = game_doc.get('participants', [])
    called_numbers = game_doc.get('called_numbers', [])

    # Update game state in DB
    winner_ids = [w['user_id'] for w in winners]
    try:
        bingo_sessions.update_one(
            {"_id": game_doc["_id"]},
            {"$set": {
                "current_game_state": "completed",
                "winner_user_ids": winner_ids,
                "ended_at": datetime.datetime.now(timezone.utc)
            }}
        )
    except Exception as e:
        logger.error(f"Failed to update session {session_id} to completed state: {e}")

    # Update Player Stats
    winner_stats = await update_player_stats(winner_ids, guild_id, participants)

    # --- Create Final Embed ---
    final_embed = Embed(title=f"{EMOJI_BINGO} BINGO! {EMOJI_LEADERBOARD}", color=COLOR_GOLD)

    if winners:
        winner_names = [f"**{w['username']}** (<@{w['user_id']}>)" for w in winners]
        winner_list = "\n".join(winner_names)
        
        final_embed.description = (
            f"After **{len(called_numbers)}** numbers called, we have a winner!\n\n"
            f"🎉 **BINGO WINNERS:**\n{winner_list}\n\n"
            f"Congratulations on your victory!"
        )
        
        # Show winner stats
        for winner in winners:
            winner_id = winner['user_id']
            wins = winner_stats.get(winner_id, 0)
            final_embed.add_field(
                name=f"📊 {winner['username']}'s Stats",
                value=f"🏆 Server Wins: **{wins}**",
                inline=True
            )
    else:
        final_embed.description = "The game has ended with no winners."
        final_embed.color = COLOR_WARNING

    final_embed.set_footer(text=f"Thanks for playing Bingo! | Session ID: {session_id}")
    final_embed.timestamp = datetime.datetime.now(timezone.utc)

    embeds_to_send = [final_embed]
    
    try:
        if get_conditional_embed and callable(get_conditional_embed) and interaction:
            conditional_embed = await get_conditional_embed(interaction, 'BINGO_GAME_COMMANDS_EMBED', COLOR_WARNING)
            if conditional_embed and isinstance(conditional_embed, Embed):
                embeds_to_send.append(conditional_embed)
    except NameError:
        pass
    except Exception as e:
        logger.error(f"Error calling get_conditional_embed: {e}", exc_info=True)

    return embeds_to_send


# --- Game Loop ---
async def run_game_loop(bot: commands.Bot, interaction: Interaction, game_db_id: Any, guild_id: str):
    """Run the main game loop for a Bingo Game."""
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        logger.error(f"Game loop {game_db_id}: Invalid channel type {type(channel)}. Aborting.")
        return

    interaction_start_time = datetime.datetime.now(timezone.utc)
    interaction_timeout_threshold = datetime.timedelta(minutes=14)
    
    # Track the main announcement message to edit
    announcement_message: Optional[discord.Message] = None

    try:
        while True:
            current_time = datetime.datetime.now(timezone.utc)
            if current_time - interaction_start_time > interaction_timeout_threshold:
                logger.warning(f"Game loop {game_db_id}: Interaction approaching timeout, switching to channel-only mode.")
                interaction = None
            
            if bingo_sessions is None:
                logger.error(f"Game loop {game_db_id}: Database not available. Stopping.")
                await channel.send(f"{EMOJI_ERROR} Database connection lost. Game aborted.")
                break

            # Fetch latest game state
            game = bingo_sessions.find_one({"_id": game_db_id})

            if not game:
                logger.warning(f"Game loop {game_db_id}: Game document not found. Stopping.")
                break
                
            current_state = game.get("current_game_state")
            if current_state != "in_progress":
                break

            participants = game.get('participants', [])
            called_numbers = game.get('called_numbers', [])
            halfway_break_shown = game.get('halfway_break_shown', False)
            
            # Check for winners
            winners = [p for p in participants if p.get('has_bingo', False)]
            if winners:
                final_embeds = await conclude_game(bot, interaction, game, guild_id, winners)
                
                # Get premium view for first winner
                winner_id = winners[0]['user_id'] if winners else None
                premium_view = get_premium_promotion_view(winner_id) if winner_id else None
                
                try:
                    await safe_send_with_view(interaction, embeds=final_embeds, view=premium_view)
                except discord.HTTPException as e:
                    logger.error(f"Failed to send final message for {game_db_id}: {e}")
                    try:
                        await channel.send(content=f"{EMOJI_BINGO} Game concluded! Check bingo status for details.")
                    except:
                        pass
                break

            # Check if all numbers called (shouldn't happen but safety check)
            if len(called_numbers) >= BINGO_RANGE_MAX:
                # No winners, end game
                final_embeds = await conclude_game(bot, interaction, game, guild_id, [])
                try:
                    await safe_send_with_view(interaction, embeds=final_embeds)
                except:
                    pass
                break

            # Halfway break check
            numbers_to_call = BINGO_RANGE_MAX
            halfway_point = int(numbers_to_call * HALFWAY_POINT_RATIO)
            
            if len(called_numbers) >= halfway_point and not halfway_break_shown:
                # Show halfway leaderboard
                leaderboard_data = []
                for p in participants:
                    remaining = count_remaining_numbers(p['card'], set(called_numbers))
                    leaderboard_data.append({
                        'username': p['username'],
                        'user_id': p['user_id'],
                        'remaining': remaining
                    })
                
                # Sort by remaining numbers (ascending)
                leaderboard_data.sort(key=lambda x: x['remaining'])
                
                halfway_embed = Embed(
                    title=f"{EMOJI_HALFWAY} Halfway Break! {EMOJI_LEADERBOARD}",
                    description=f"**{len(called_numbers)}** numbers have been called. Here's the leaderboard!",
                    color=COLOR_PURPLE
                )
                
                leaderboard_text = []
                for i, player in enumerate(leaderboard_data[:10], 1):
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"`{i:2d}.`"
                    leaderboard_text.append(
                        f"{medal} **{player['username']}** - {player['remaining']} numbers left"
                    )
                
                halfway_embed.add_field(
                    name="📊 Current Standings (Closest to Bingo)",
                    value="\n".join(leaderboard_text) if leaderboard_text else "No players",
                    inline=False
                )
                
                halfway_embed.set_footer(text="The game continues! Good luck!")
                
                try:
                    await channel.send(embed=halfway_embed)
                except discord.HTTPException as e:
                    logger.error(f"Failed to send halfway embed: {e}")
                
                # Mark halfway break as shown
                try:
                    bingo_sessions.update_one(
                        {"_id": game_db_id},
                        {"$set": {"halfway_break_shown": True}}
                    )
                except Exception as e:
                    logger.error(f"Failed to update halfway_break_shown: {e}")
                
                await asyncio.sleep(5)  # Pause before continuing

            # Call next number
            available_numbers = [n for n in range(BINGO_RANGE_MIN, BINGO_RANGE_MAX + 1) if n not in called_numbers]
            if not available_numbers:
                break
            
            next_number = random.choice(available_numbers)
            called_numbers.append(next_number)
            
            # Update DB with new called number
            try:
                bingo_sessions.update_one(
                    {"_id": game_db_id},
                    {"$push": {"called_numbers": next_number}}
                )
            except Exception as e:
                logger.error(f"Failed to update called_numbers: {e}")
                break

            # Determine letter (B-I-N-G-O)
            if 1 <= next_number <= 15:
                letter = "B"
            elif 16 <= next_number <= 30:
                letter = "I"
            elif 31 <= next_number <= 45:
                letter = "N"
            elif 46 <= next_number <= 60:
                letter = "G"
            else:
                letter = "O"
            
            # Create/update announcement embed
            announce_embed = Embed(
                title=f"{EMOJI_NUMBER} Bingo Game In Progress",
                description=(
                    f"## Latest Number: **{letter}-{next_number}** 🎲\n\n"
                    f"📊 **Total Called:** {len(called_numbers)}/{BINGO_RANGE_MAX}\n"
                    f"👥 **Players:** {len(participants)}\n"
                    f"⏱️ **Next call in:** {NUMBER_CALL_DELAY} seconds"
                ),
                color=COLOR_IN_PROGRESS
            )
            
            # Recent calls with better formatting
            recent_calls = called_numbers[-15:]
            recent_formatted = []
            for num in recent_calls:
                if 1 <= num <= 15:
                    recent_formatted.append(f"B-{num}")
                elif 16 <= num <= 30:
                    recent_formatted.append(f"I-{num}")
                elif 31 <= num <= 45:
                    recent_formatted.append(f"N-{num}")
                elif 46 <= num <= 60:
                    recent_formatted.append(f"G-{num}")
                else:
                    recent_formatted.append(f"O-{num}")
            
            announce_embed.add_field(
                name="📋 Recent Numbers (Last 15)",
                value=", ".join(recent_formatted) if recent_formatted else "None yet",
                inline=False
            )
            
            # Progress bar
            progress = len(called_numbers) / BINGO_RANGE_MAX
            filled = int(progress * 20)
            bar = "█" * filled + "░" * (20 - filled)
            announce_embed.add_field(
                name="📈 Game Progress",
                value=f"{bar} {progress*100:.0f}%",
                inline=False
            )
            
            announce_embed.set_footer(text="👇 Click 'View My Card' below to see your updated card!")
            announce_embed.timestamp = datetime.datetime.now(timezone.utc)
            
            # Create view with "View My Card" button
            view = ViewCardButton(game_db_id=game_db_id, guild_id=guild_id)
            
            # Edit or send the announcement
            try:
                if announcement_message is None:
                    announcement_message = await channel.send(embed=announce_embed, view=view)
                else:
                    try:
                        await announcement_message.edit(embed=announce_embed, view=view)
                    except discord.NotFound:
                        # Message was deleted, send a new one
                        announcement_message = await channel.send(embed=announce_embed, view=view)
            except discord.HTTPException as e:
                logger.error(f"Failed to send/edit number announcement: {e}")

            # Update each player's card in database (no channel spam)
            for participant in participants:
                user_id = participant['user_id']
                card = participant['card']
                marked = set(participant.get('marked', []))
                
                # Mark number if on card
                for row in card:
                    if next_number in row:
                        marked.add(next_number)
                        break
                
                # Update marked in DB
                try:
                    bingo_sessions.update_one(
                        {"_id": game_db_id, "participants.user_id": user_id},
                        {"$set": {"participants.$.marked": list(marked)}}
                    )
                except Exception as e:
                    logger.error(f"Failed to update marked numbers for {user_id}: {e}")
                
                # Check for bingo
                has_bingo = check_bingo(card, marked)
                if has_bingo:
                    try:
                        bingo_sessions.update_one(
                            {"_id": game_db_id, "participants.user_id": user_id},
                            {"$set": {"participants.$.has_bingo": True}}
                        )
                    except Exception as e:
                        logger.error(f"Failed to update bingo status for {user_id}: {e}")

            # No need to spam channel with card updates - users can click the button
            await asyncio.sleep(NUMBER_CALL_DELAY)

    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Unexpected error in game loop for {game_db_id}: {e}", exc_info=True)
        try:
            await channel.send(f"{EMOJI_ERROR} A critical error occurred in the game loop. The game has been stopped.")
            if bingo_sessions is not None:
                bingo_sessions.update_one(
                    {"_id": game_db_id, "current_game_state": "in_progress"},
                    {"$set": {"current_game_state": "errored"}}
                )
        except Exception as report_e:
            logger.error(f"Failed to report game loop error or update DB for {game_db_id}: {report_e}")
    finally:
        pass


# --- Views ---

class ViewCardButton(View):
    """View with a button to check your bingo card during the game."""
    
    def __init__(self, game_db_id: Any, guild_id: str):
        super().__init__(timeout=None)
        self.game_db_id = game_db_id
        self.guild_id = guild_id
    
    @discord.ui.button(label="View My Card", style=ButtonStyle.primary, emoji=EMOJI_CARD, custom_id="bingo_view_card")
    async def view_card_button(self, interaction: Interaction, button: Button):
        """Show the user their current bingo card."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        if bingo_sessions is None:
            await interaction.followup.send(f"{EMOJI_ERROR} Database connection error.", ephemeral=True)
            return
        
        try:
            user_id = str(interaction.user.id)
            
            # Get game from database
            game = bingo_sessions.find_one({"_id": self.game_db_id})
            
            if not game:
                await interaction.followup.send("This game session no longer exists.", ephemeral=True)
                return
            
            # Find this user's participant data
            participant = None
            for p in game.get('participants', []):
                if p.get('user_id') == user_id:
                    participant = p
                    break
            
            if not participant:
                await interaction.followup.send(
                    "You are not in this game. Join the next one!",
                    ephemeral=True
                )
                return
            
            # Get their card data
            card = participant['card']
            marked = set(participant.get('marked', []))
            has_bingo = participant.get('has_bingo', False)
            called_numbers = game.get('called_numbers', [])
            participants_count = len(game.get('participants', []))
            
            # Determine latest number and if it was on their card
            latest_number = called_numbers[-1] if called_numbers else None
            latest_on_card = latest_number in marked if latest_number else False
            
            # Determine letter for latest number
            if latest_number:
                if 1 <= latest_number <= 15:
                    letter = "B"
                elif 16 <= latest_number <= 30:
                    letter = "I"
                elif 31 <= latest_number <= 45:
                    letter = "N"
                elif 46 <= latest_number <= 60:
                    letter = "G"
                else:
                    letter = "O"
                latest_str = f"{letter}-{latest_number}"
            else:
                latest_str = "None yet"
            
            # Create card embed
            card_color = COLOR_GOLD if has_bingo else COLOR_SUCCESS if latest_on_card else COLOR_DEFAULT
            
            card_embed = Embed(
                title=f"{EMOJI_CARD} Your Bingo Card",
                description=format_bingo_card(card, marked),
                color=card_color
            )
            
            # Status message
            if has_bingo:
                status_msg = "🎉 **BINGO! YOU WON!** 🎉\nYou've completed a line! Waiting for game to conclude..."
            elif latest_on_card and latest_number:
                status_msg = f"✅ **{latest_str}** was on your card and has been marked!"
            elif latest_number:
                status_msg = f"⚪ **{latest_str}** was not on your card."
            else:
                status_msg = "🎲 Game hasn't started calling numbers yet."
            
            card_embed.add_field(
                name="🎲 Latest Number",
                value=status_msg,
                inline=False
            )
            
            # Progress info
            remaining = count_remaining_numbers(card, marked)
            total_numbers = 24  # 25 squares minus FREE space
            marked_count = total_numbers - remaining
            progress_pct = (marked_count / total_numbers) * 100
            
            card_embed.add_field(
                name="📊 Your Progress",
                value=(
                    f"**Marked:** {marked_count}/{total_numbers} numbers\n"
                    f"**Remaining:** {remaining} numbers\n"
                    f"**Completion:** {progress_pct:.0f}%"
                ),
                inline=True
            )
            
            # Game info
            card_embed.add_field(
                name="🎮 Game Status",
                value=(
                    f"**Called:** {len(called_numbers)}/{BINGO_RANGE_MAX}\n"
                    f"**Players:** {participants_count}\n"
                    f"**Next:** ~{NUMBER_CALL_DELAY}s"
                ),
                inline=True
            )
            
            card_embed.set_footer(
                text="💡 Tip: Get 5 in a row (horizontal, vertical, or diagonal) to win!"
            )
            card_embed.timestamp = datetime.datetime.now(timezone.utc)
            
            await interaction.followup.send(embed=card_embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in view_card_button: {e}", exc_info=True)
            await interaction.followup.send(
                f"{EMOJI_ERROR} An error occurred while fetching your card.",
                ephemeral=True
            )


class JoinButtonView(View):
    """View with a button for joining a Bingo Game."""

    def __init__(self, game_id: str, guild_id: str):
        super().__init__(timeout=None)
        self.game_id = game_id
        self.guild_id = guild_id

    def disable_all_buttons(self):
        """Disables all buttons in this view."""
        for child in self.children:
            if isinstance(child, Button):
                child.disabled = True

    async def update_player_count_embed(self, interaction: Interaction, player_count: int, max_players: int):
        """Updates the player count embed."""
        if not interaction.message or len(interaction.message.embeds) < 2:
            logger.warning(f"Could not find player count embed to update for game {self.game_id}")
            return

        try:
            embeds = interaction.message.embeds
            main_embed = embeds[0]
            player_embed = embeds[1]

            # -1 means unlimited, otherwise show the number
            cap_text = "∞" if max_players == -1 else str(max_players)
            new_description = f"{player_count}/{cap_text} Players joined."
            
            new_player_embed = Embed(
                title=player_embed.title if hasattr(player_embed, 'title') else None,
                description=new_description,
                color=COLOR_SUCCESS
            )
            
            if player_embed.footer and player_embed.footer.text:
                new_player_embed.set_footer(text=player_embed.footer.text, icon_url=player_embed.footer.icon_url or Embed.Empty)

            await interaction.message.edit(embeds=[main_embed, new_player_embed], view=self)
        except discord.NotFound:
            logger.warning(f"Original message for game {self.game_id} not found when updating player count.")
        except discord.Forbidden:
            logger.warning(f"Message too old to edit for game {self.game_id}. Sending new player count update.")
            try:
                update_embed = Embed(
                    description=f"🔄 Player count updated: {player_count}/{cap_text} players",
                    color=COLOR_SUCCESS
                )
                await interaction.channel.send(embed=update_embed)
            except Exception as send_e:
                logger.error(f"Failed to send player count update message for game {self.game_id}: {send_e}")
        except discord.HTTPException as e:
            logger.error(f"Failed to edit message to update player count for game {self.game_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error updating player count embed for game {self.game_id}: {e}", exc_info=True)

    @discord.ui.button(label="Join", style=ButtonStyle.primary, emoji=EMOJI_JOIN, custom_id="bingo_join_button")
    async def join_button(self, interaction: Interaction, button: Button):
        """Allows a user to join the game via the button."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        if bingo_sessions is None:
            await interaction.followup.send(f"{EMOJI_ERROR} Database connection error. Cannot join game.", ephemeral=True)
            return

        try:
            game = bingo_sessions.find_one({
                "guild_id": self.guild_id,
                "session_id": self.game_id,
            })

            if not game:
                await interaction.followup.send("This Bingo Game session could not be found or is no longer active.", ephemeral=True)
                self.disable_all_buttons()
                if interaction.message:
                    try:
                        await interaction.message.edit(view=self)
                    except discord.NotFound:
                        logger.warning(f"Original message for game {self.game_id} not found when disabling join button.")
                    except discord.Forbidden:
                        logger.warning(f"Message too old to edit for game {self.game_id}. Join button disabled in memory.")
                    except discord.HTTPException as e:
                        logger.error(f"Failed to edit message to disable join button for {self.game_id}: {e}")
                return

            if game.get("current_game_state") != "waiting_for_players":
                await interaction.followup.send(f"{EMOJI_WARNING} This game has already started or finished. You can no longer join.", ephemeral=True)
                self.disable_all_buttons()
                if interaction.message:
                    try:
                        await interaction.message.edit(view=self)
                    except discord.NotFound:
                        logger.warning(f"Original message for game {self.game_id} not found when disabling join button (already started).")
                    except discord.Forbidden:
                        logger.warning(f"Message too old to edit for game {self.game_id} (already started). Join button disabled in memory.")
                    except discord.HTTPException as e:
                        logger.error(f"Failed to edit message to disable join button for already started game {self.game_id}: {e}")
                return

            user_id = str(interaction.user.id)
            participants = game.get("participants", [])

            # Enforce max players based on host entitlements
            try:
                host_id = str(game.get("host_user_id"))
                ent = get_user_entitlements(host_id)
                max_players = get_max_players_for_entitlements(ent)
                
                # Only enforce if not unlimited (-1)
                if max_players != -1 and len(participants) >= max_players:
                    await interaction.followup.send(
                        f"{EMOJI_WARNING} This session has reached the maximum of {max_players} players for the host's tier.",
                        ephemeral=True,
                    )
                    return
            except Exception as e:
                logger.error(f"Error determining Bingo max players cap: {e}")

            # Check if already joined
            if any(p.get("user_id") == user_id for p in participants):
                await interaction.followup.send("You are already in this game session.", ephemeral=True)
                return

            # Add participant with their bingo card
            new_participant = {
                "user_id": user_id,
                "username": interaction.user.display_name,
                "card": generate_bingo_card(),
                "marked": [],
                "has_bingo": False
            }
            result = bingo_sessions.update_one(
                {"_id": game["_id"]},
                {"$push": {"participants": new_participant}}
            )

            if result.modified_count == 1:
                # Send initial card to player (ephemeral in channel)
                try:
                    card_embed = Embed(
                        title=f"{EMOJI_SUCCESS} Welcome to Bingo!",
                        description=(
                            f"You've successfully joined the game!\n\n"
                            f"## {EMOJI_CARD} Your Bingo Card\n"
                            f"{format_bingo_card(new_participant['card'], set())}"
                        ),
                        color=COLOR_SUCCESS
                    )
                    
                    card_embed.add_field(
                        name="🎯 How to Win",
                        value=(
                            "Get **5 in a row** to win:\n"
                            "✅ Horizontal row\n"
                            "✅ Vertical column\n"
                            "✅ Diagonal line\n\n"
                            "The FREE space in the center is already marked!"
                        ),
                        inline=False
                    )
                    
                    card_embed.add_field(
                        name="🎲 What Happens Next",
                        value=(
                            f"• Wait for the host to start with `/bingo run`\n"
                            f"• Numbers will be called every {NUMBER_CALL_DELAY} seconds\n"
                            f"• You'll get updates here in the channel (only you can see them)\n"
                            f"• First to get BINGO wins!"
                        ),
                        inline=False
                    )
                    
                    card_embed.add_field(
                        name="📊 Your Stats",
                        value=f"**Numbers to mark:** 24\n**FREE space:** Already marked\n**Players:** {len(participants) + 1}",
                        inline=False
                    )
                    
                    card_embed.set_footer(text=f"Game ID: {self.game_id} • Good luck! 🍀")
                    card_embed.timestamp = datetime.datetime.now(timezone.utc)
                    
                    await interaction.followup.send(embed=card_embed, ephemeral=True)
                    
                except Exception as e:
                    logger.error(f"Failed to send initial card to {user_id}: {e}")
                    await interaction.followup.send(
                        f"{EMOJI_SUCCESS} You have joined the Bingo Game! You'll receive updates in this channel.",
                        ephemeral=True
                    )
                
                # Update player count display
                try:
                    host_id = str(game.get("host_user_id"))
                    ent = get_user_entitlements(host_id)
                    max_players = get_max_players_for_entitlements(ent)
                except Exception:
                    max_players = MAX_PLAYERS_FREE
                
                await self.update_player_count_embed(interaction, len(participants) + 1, max_players)
            else:
                logger.warning(f"Failed to add participant {user_id} to game {self.game_id}. Modified count was 0.")
                await interaction.followup.send(f"{EMOJI_ERROR} Failed to add you to the game session in the database. Please try again.", ephemeral=True)

        except Exception as e:
            logger.error(f"Error in join_button for game {self.game_id}: {e}", exc_info=True)
            await interaction.followup.send(f"{EMOJI_ERROR} An unexpected error occurred while trying to join.", ephemeral=True)


# --- Main Cog Class ---

class BingoGames(commands.GroupCog, name="bingo"):
    """Bingo Games cog for server-wide bingo games."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.run_tasks: Dict[str, asyncio.Task] = {}
        if mongo_client is None:
            logger.critical("BingoGames initialized WITHOUT a MongoDB connection.")

    def cog_unload(self):
        """Cancel any running game loop tasks when the cog is unloaded."""
        for task in self.run_tasks.values():
            task.cancel()
        self.run_tasks.clear()

    @app_commands.command(name="start", description="Start a new server-wide Bingo game session")
    @app_commands.checks.cooldown(1, 60, key=lambda i: i.guild_id)
    async def start(self, interaction: Interaction):
        """Starts a new Bingo Game session and allows players to join."""
        await interaction.response.defer(thinking=True)

        if bingo_sessions is None:
            await interaction.followup.send(f"{EMOJI_ERROR} Database is not connected. Cannot start game.", ephemeral=True)
            return

        guild_id = str(interaction.guild_id)
        user_id = str(interaction.user.id)

        # Check for existing game
        try:
            existing_game = bingo_sessions.find_one({
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
                description=f"A Bingo Game session is already `{state}` in this server, hosted by {host_mention}.\nPlease wait for it to conclude.",
                color=COLOR_WARNING
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        try:
            session_id, new_session_doc = create_new_session(guild_id, user_id, interaction.user.display_name)
        except ConnectionError:
            await interaction.followup.send(f"{EMOJI_ERROR} Database connection error prevented session creation.", ephemeral=True)
            return
        except Exception as e:
            logger.error(f"Error creating session in /start: {e}", exc_info=True)
            await interaction.followup.send(f"{EMOJI_ERROR} Failed to create the game session. Please try again.", ephemeral=True)
            return

        # Main Embed
        main_embed = Embed(
            title=f"{EMOJI_START} New Bingo Game Session Created!",
            description=(
                f"A new Bingo session has been created by {interaction.user.mention}!\n\n"
                f"🎯 Click the **Join** button below to enter.\n"
                f"📱 You'll receive your bingo card via DM.\n"
                f"🎲 Numbers will be called automatically once the game starts.\n\n"
                f"The host needs to use `/bingo run` to start the game once enough players have joined (min {MIN_PLAYERS})."
            ),
            color=COLOR_WAITING
        )
        
        main_embed.set_thumbnail(url=interaction.user.display_avatar.url)
        main_embed.set_footer(text=f"Session ID: {session_id}")
        main_embed.timestamp = new_session_doc.get('created_at', datetime.datetime.now(timezone.utc))

        # Player Count Embed
        try:
            ent = get_user_entitlements(user_id)
            max_players = get_max_players_for_entitlements(ent)
            # -1 means unlimited, otherwise show the number
            cap_text = "∞" if max_players == -1 else str(max_players)
        except Exception:
            cap_text = str(MAX_PLAYERS_FREE)
            
        player_embed = Embed(
            description=f"1/{cap_text} Players joined.",
            color=COLOR_SUCCESS
        )

        # Attach Join Button View
        view = JoinButtonView(game_id=session_id, guild_id=guild_id)
        
        await interaction.followup.send(embeds=[main_embed, player_embed], view=view)
        
        # Send initial card to host (ephemeral in channel)
        try:
            host_card = new_session_doc['participants'][0]['card']
            card_embed = Embed(
                title=f"{EMOJI_SUCCESS} Bingo Game Created!",
                description=(
                    f"Your game is ready!\n\n"
                    f"## {EMOJI_CARD} Your Bingo Card\n"
                    f"{format_bingo_card(host_card, set())}"
                ),
                color=COLOR_SUCCESS
            )
            
            card_embed.add_field(
                name="👑 As the Host",
                value=(
                    f"• Wait for players to join (minimum {MIN_PLAYERS})\n"
                    f"• Use `/bingo run` to start the game\n"
                    f"• Numbers will be called automatically\n"
                    f"• You can cancel anytime with `/bingo cancel`"
                ),
                inline=False
            )
            
            card_embed.add_field(
                name="🎯 How to Win",
                value=(
                    "Get **5 in a row**:\n"
                    "✅ Horizontal • ✅ Vertical • ✅ Diagonal\n"
                    "The FREE space is already marked!"
                ),
                inline=False
            )
            
            card_embed.add_field(
                name="📊 Game Settings",
                value=(
                    f"**Max Players:** {cap_text}\n"
                    f"**Current Players:** 1\n"
                    f"**Call Interval:** {NUMBER_CALL_DELAY} seconds"
                ),
                inline=False
            )
            
            card_embed.set_footer(text=f"Game ID: {session_id} • Good luck! 🍀")
            card_embed.timestamp = datetime.datetime.now(timezone.utc)
            
            await interaction.followup.send(embed=card_embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Failed to send initial card to host {user_id}: {e}")

    @app_commands.command(name="run", description="Start the bingo game and begin calling numbers")
    @app_commands.checks.cooldown(1, 15, key=lambda i: i.guild_id)
    async def run(self, interaction: Interaction):
        """Starts the rounds for the currently waiting Bingo Game."""
        if bingo_sessions is None:
            await interaction.response.send_message(f"{EMOJI_ERROR} Database is not connected. Cannot run game.", ephemeral=True)
            return

        guild_id = str(interaction.guild_id)

        # Find the game waiting for players
        try:
            game = bingo_sessions.find_one({
                "guild_id": guild_id,
                "current_game_state": "waiting_for_players"
            })
        except Exception as e:
            logger.error(f"Database error finding waiting game in guild {guild_id}: {e}")
            await interaction.response.send_message(f"{EMOJI_ERROR} Database error finding waiting game. Please try again.", ephemeral=True)
            return

        if not game:
            embed = Embed(
                title=f"{EMOJI_INFO} No Waiting Game Found",
                description="There is no Bingo Game session currently waiting for players in this server. Use `/bingo start` first.",
                color=COLOR_WARNING
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check if the user running the command is the host
        if str(interaction.user.id) != game.get("host_user_id"):
            host_mention = f"<@{game.get('host_user_id', 'Unknown')}>"
            embed = Embed(
                title=f"{EMOJI_WARNING} Host Only Command",
                description=f"Only the host ({host_mention}) can start the game using `/bingo run`.",
                color=COLOR_WARNING
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check for minimum players
        participants = game.get("participants", [])
        if len(participants) < MIN_PLAYERS:
            embed = Embed(
                title=f"{EMOJI_WARNING} Not Enough Players",
                description=f"You need at least **{MIN_PLAYERS} players** to start the game. Currently {len(participants)}.",
                color=COLOR_WARNING
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # --- Start the Game ---
        await interaction.response.defer()

        session_id = game.get('session_id', 'UnknownSession')
        db_id = game.get('_id')
        if not session_id or not db_id:
            logger.error(f"Missing session_id or _id in game document for guild {guild_id}")
            await interaction.followup.send(f"{EMOJI_ERROR} Critical error: Game data is corrupted. Cannot start game.", ephemeral=True)
            return

        # Update game state to in_progress
        try:
            update_result = bingo_sessions.update_one(
                {"_id": db_id},
                {"$set": {
                    "current_game_state": "in_progress",
                    "started_at": datetime.datetime.now(timezone.utc)
                }}
            )
            if update_result.matched_count == 0:
                logger.error(f"Failed to find game {session_id} to update state to in_progress.")
                await interaction.followup.send(f"{EMOJI_ERROR} Failed to update the game state in the database. Cannot start game.", ephemeral=True)
                return
        except Exception as e:
            logger.error(f"Failed to update game state to in_progress for {session_id}: {e}", exc_info=True)
            await interaction.followup.send(f"{EMOJI_ERROR} Failed to update the game state in the database. Cannot start game.", ephemeral=True)
            return

        # Send start confirmation message
        start_embed = Embed(
            title=f"{EMOJI_START} Bingo Game Starting!",
            description=(
                f"The host {interaction.user.mention} has started the game!\n"
                f"**{len(participants)}** players are competing. Good luck!\n\n"
                f"📱 Watch your DMs for your card updates!\n"
                f"🎲 Numbers will be called every {NUMBER_CALL_DELAY} seconds.\n"
                f"🏆 First to get BINGO wins!\n\n"
                f"The game will now proceed automatically..."
            ),
            color=COLOR_IN_PROGRESS
        )
        start_embed.set_thumbnail(url=interaction.user.display_avatar.url)

        try:
            await interaction.followup.send(embed=start_embed)
        except discord.HTTPException as e:
            logger.error(f"Failed to send start confirmation for game {session_id}: {e}")
            if interaction.channel:
                await interaction.channel.send(embed=start_embed, content=f"{EMOJI_WARNING} Game starting (interaction followup failed).")
            return

        # Start the game loop task
        if session_id in self.run_tasks:
            logger.warning(f"Task already exists for session {session_id}. Cancelling old one.")
            self.run_tasks[session_id].cancel()

        task = asyncio.create_task(
            run_game_loop(self.bot, interaction, db_id, guild_id)
        )
        self.run_tasks[session_id] = task

        # Add callback to remove task from dict when done
        def cleanup_task(fut: asyncio.Task):
            try:
                if fut.cancelled():
                    pass
                elif fut.exception():
                    exc = fut.exception()
                    logger.error(f"Game loop task {session_id} raised an exception: {exc}", exc_info=exc)
            except Exception as cb_e:
                logger.error(f"Error during game loop task cleanup callback for {session_id}: {cb_e}", exc_info=True)
            finally:
                if session_id in self.run_tasks:
                    del self.run_tasks[session_id]

        task.add_done_callback(cleanup_task)

    @app_commands.command(name="status", description="View the current Bingo Game session status")
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.guild_id)
    async def status(self, interaction: Interaction):
        """Displays the status of the current game session."""
        await interaction.response.defer(ephemeral=True)

        if bingo_sessions is None:
            await interaction.followup.send(f"{EMOJI_ERROR} Database is not connected. Cannot check status.", ephemeral=True)
            return

        guild_id = str(interaction.guild_id)
        try:
            game = bingo_sessions.find_one({
                "guild_id": guild_id,
                "current_game_state": {"$in": ["waiting_for_players", "in_progress"]}
            })
        except Exception as e:
            logger.error(f"Database error finding active game in guild {guild_id} for status: {e}")
            await interaction.followup.send(f"{EMOJI_ERROR} Database error checking game status. Please try again.", ephemeral=True)
            return

        if not game:
            embed = Embed(
                title=f"{EMOJI_INFO} No Active Session",
                description="No Bingo Game session is currently active or waiting in this server.",
                color=COLOR_WARNING
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Game found, prepare status embed
        state = game.get('current_game_state', 'Unknown').replace('_', ' ').title()
        state_emoji = EMOJI_WAITING if state == 'Waiting For Players' else EMOJI_IN_PROGRESS
        host_id = game.get('host_user_id')
        participants = game.get('participants', [])
        called_numbers = game.get('called_numbers', [])
        
        status_embed = Embed(
            title=f"{EMOJI_STATUS} Current Bingo Game Status",
            description=f"**State:** {state_emoji} `{state}`\n**Host:** <@{host_id}>",
            color=COLOR_WAITING if state == 'Waiting For Players' else COLOR_IN_PROGRESS
        )

        if state == 'In Progress':
            status_embed.description += f"\n**Numbers Called:** {EMOJI_NUMBER} `{len(called_numbers)}`"
            if called_numbers:
                recent = called_numbers[-10:]
                status_embed.add_field(
                    name="📋 Recent Numbers",
                    value=", ".join(str(n) for n in recent),
                    inline=False
                )

        status_embed.add_field(
            name=f"👥 Players ({len(participants)})",
            value=", ".join([f"**{p['username']}**" for p in participants[:15]]) or "None",
            inline=False
        )

        status_embed.set_footer(text=f"Session ID: {game.get('session_id', 'N/A')}")
        status_embed.timestamp = datetime.datetime.now(timezone.utc)

        await interaction.followup.send(embed=status_embed, ephemeral=False)

    @app_commands.command(name="cancel", description="Cancel the current Bingo Game session (host only)")
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.guild_id)
    async def cancel(self, interaction: Interaction):
        """Cancels the active or waiting Bingo Game session. Only the host can cancel."""
        await interaction.response.defer(ephemeral=True)

        if bingo_sessions is None:
            await interaction.followup.send(f"{EMOJI_ERROR} Database is not connected. Cannot cancel session.", ephemeral=True)
            return

        guild_id = str(interaction.guild_id)
        user_id = str(interaction.user.id)

        try:
            game = bingo_sessions.find_one({
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
            bingo_sessions.update_one(
                {"_id": game["_id"]},
                {"$set": {"current_game_state": "cancelled", "ended_at": datetime.datetime.now(timezone.utc)}}
            )
        except Exception as e:
            logger.error(f"Failed to mark session {session_id} as cancelled: {e}")

        # Confirmation embed
        confirm_embed = Embed(
            title=f"{EMOJI_STOP} Session Cancelled",
            description=(
                f"The Bingo Game session has been cancelled by {interaction.user.mention}.\n"
                f"Session ID: `{session_id}`"
            ),
            color=COLOR_ERROR
        )

        # Send public confirmation in channel
        try:
            await interaction.followup.send(embed=confirm_embed, ephemeral=False)
        except discord.HTTPException:
            if interaction.channel:
                await interaction.channel.send(embed=confirm_embed)

    @app_commands.command(name="stats", description="View your Bingo game statistics")
    @app_commands.describe(user="User to check stats for (optional)")
    async def stats(self, interaction: Interaction, user: Optional[discord.Member] = None):
        """Display user's bingo stats."""
        await interaction.response.defer()
        
        target_user = user or interaction.user
        guild_id = str(interaction.guild_id)
        user_id = str(target_user.id)
        
        try:
            # Get server stats
            server_stats = None
            if bingo_stats is not None:
                server_stats = bingo_stats.find_one({"user_id": user_id, "guild_id": guild_id})
            
            # Get global stats
            global_stats = None
            if bingo_global_stats is not None:
                global_stats = bingo_global_stats.find_one({"user_id": user_id})
            
            embed = Embed(
                title=f"{EMOJI_BINGO} {target_user.display_name}'s Bingo Stats",
                color=COLOR_GOLD
            )
            
            embed.set_thumbnail(url=target_user.display_avatar.url)
            
            # Server stats
            server_wins = server_stats.get("wins", 0) if server_stats else 0
            server_games = server_stats.get("games_played", 0) if server_stats else 0
            server_win_rate = (server_wins / server_games * 100) if server_games > 0 else 0
            
            embed.add_field(
                name=f"📊 Server Stats ({interaction.guild.name})",
                value=(
                    f"🏆 **Wins:** {server_wins}\n"
                    f"🎮 **Games Played:** {server_games}\n"
                    f"📈 **Win Rate:** {server_win_rate:.1f}%"
                ),
                inline=True
            )
            
            # Global stats
            global_wins = global_stats.get("wins", 0) if global_stats else 0
            global_games = global_stats.get("games_played", 0) if global_stats else 0
            global_win_rate = (global_wins / global_games * 100) if global_games > 0 else 0
            
            embed.add_field(
                name="🌍 Global Stats (All Servers)",
                value=(
                    f"🏆 **Wins:** {global_wins}\n"
                    f"🎮 **Games Played:** {global_games}\n"
                    f"📈 **Win Rate:** {global_win_rate:.1f}%"
                ),
                inline=True
            )
            
            if server_games == 0 and global_games == 0:
                embed.add_field(
                    name="💡 Ready to Play?",
                    value="You haven't played any bingo games yet! Use `/bingo start` to create a game!",
                    inline=False
                )
            
            embed.timestamp = datetime.datetime.now(timezone.utc)
            
            # Get premium view
            premium_view = get_premium_promotion_view(str(interaction.user.id))
            
            await interaction.followup.send(embed=embed, view=premium_view)
            
        except Exception as e:
            logger.error(f"Error in stats command: {e}")
            error_embed = Embed(
                title="❌ Stats Error",
                description="Couldn't fetch bingo stats. Try again later!",
                color=COLOR_ERROR
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)

    @app_commands.command(name="leaderboard", description="View the server's bingo leaderboard")
    async def leaderboard(self, interaction: Interaction):
        """Display server bingo leaderboard."""
        await interaction.response.defer()
        
        guild_id = str(interaction.guild_id)
        server_name = interaction.guild.name
        
        try:
            leaderboard = []
            if bingo_stats is not None:
                leaderboard = list(bingo_stats.find(
                    {"guild_id": guild_id}
                ).sort([("wins", -1), ("games_played", -1)]).limit(15))
            
            embed = Embed(
                title=f"🏆 {server_name} Bingo Leaderboard",
                description="The luckiest bingo players in the server!",
                color=COLOR_GOLD
            )
            
            if not leaderboard:
                embed.add_field(
                    name="📊 No Games Yet",
                    value="No one has played bingo yet! Use `/bingo start` to begin!",
                    inline=False
                )
            else:
                medals = ["🥇", "🥈", "🥉"]
                
                leaderboard_text = []
                for i, stats in enumerate(leaderboard):
                    position = i + 1
                    username = stats.get('username', 'Unknown')
                    wins = stats.get('wins', 0)
                    games = stats.get('games_played', 0)
                    win_rate = (wins / games * 100) if games > 0 else 0
                    
                    if position <= 3:
                        medal = medals[position - 1]
                        leaderboard_text.append(
                            f"{medal} **{username}** - {wins}W/{games}G ({win_rate:.1f}%)"
                        )
                    else:
                        leaderboard_text.append(
                            f"`{position:2d}.` **{username}** - {wins}W/{games}G ({win_rate:.1f}%)"
                        )
                
                embed.add_field(
                    name="📊 Rankings",
                    value="\n".join(leaderboard_text),
                    inline=False
                )
                
                total_games = sum(stats.get('games_played', 0) for stats in leaderboard)
                embed.add_field(
                    name="📈 Server Stats",
                    value=f"Total Players: **{len(leaderboard)}**\nTotal Games: **{total_games}**",
                    inline=False
                )
            
            embed.set_footer(text="Start a game with /bingo start!")
            embed.timestamp = datetime.datetime.now(timezone.utc)
            
            premium_view = get_premium_promotion_view(str(interaction.user.id))
            
            await interaction.followup.send(embed=embed, view=premium_view)
            
        except Exception as e:
            logger.error(f"Error in leaderboard command: {e}")
            error_embed = Embed(
                title="❌ Leaderboard Error",
                description="Couldn't fetch the leaderboard. Try again later!",
                color=COLOR_ERROR
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)

    # --- Error Handling ---
    async def cog_app_command_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        """Handles errors for the bingo commands."""
        original_error = getattr(error, 'original', error)

        if isinstance(error, app_commands.CommandOnCooldown):
            message = f"{EMOJI_WARNING} This command is on cooldown. Please try again in {error.retry_after:.2f} seconds."
        elif isinstance(error, app_commands.CheckFailure):
            message = f"{EMOJI_ERROR} You do not have the necessary permissions to use this command."
        elif isinstance(original_error, ConnectionError) and "Database not initialized" in str(original_error):
            message = f"{EMOJI_ERROR} Database connection error. Please try again later or contact admin."
        elif isinstance(original_error, ConnectionFailure):
            logger.error(f"Database ConnectionFailure during '{interaction.command.name if interaction.command else 'Unknown'}' command: {original_error}")
            message = f"{EMOJI_ERROR} Could not connect to the database. Please try again later."
        else:
            logger.error(f"Unhandled error in bingo command '{interaction.command.name if interaction.command else 'Unknown'}': {error}", exc_info=error)
            message = f"{EMOJI_ERROR} An unexpected error occurred. Please try again later."

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


# --- Setup Function ---
async def setup(bot: commands.Bot):
    """Adds the BingoGames cog to the bot."""
    if mongo_client is None:
        logger.error("Cannot add BingoGames cog: MongoDB connection failed or MONGODB_URI not set.")
    else:
        try:
            await bot.add_cog(BingoGames(bot))
            logger.info("BingoGames cog loaded successfully")
        except Exception as e:
            logger.critical(f"Failed to load BingoGames cog: {e}", exc_info=True)