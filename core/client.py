# core/client.py
import logging
import discord
from discord.ext import commands, tasks
import datetime
from pymongo import MongoClient, UpdateOne # Import UpdateOne
from bson import ObjectId # Import ObjectId

from config.settings import TOKEN, BLACKLISTED_GUILDS, MONGODB_URI # Import MONGODB_URI
from core.errors import setup_error_handlers
from ui.embeds import get_premium_promotion_embed

logger = logging.getLogger(__name__) # Use __name__ for logger
# logger = logging.getLogger('discord.gateway') # Keep gateway logs less verbose if needed
# logger.setLevel(logging.ERROR)

# --- Database Migration Logic ---
async def run_database_migration():
    """Adds new fields to existing pet documents if they don't exist."""
    try:
        client = MongoClient(MONGODB_URI)
        db = client['astrostats_database']
        pets_collection = db['pets']
        logger.info("Running database migration check for pets...")

        # Fields to ensure exist with default values
        fields_to_add = {
            "balance": 0,
            "active_items": [],
            "claimed_daily_completion_bonus": False,
            # New fields for enhanced pet system
            "trainingCount": 0,
            "lastTrainingReset": None,
            "voted_battle_bonus_active": False, # Add the new vote bonus flag
            "bonus_battle_allowance": 0, # Bonus battles allowed from voting
            "battleRecord": {"wins": 0, "losses": 0},
            "lastDailyClaim": None,
            "lastHuntTime": None,
            "lastRenameTime": None
        }

        updates = []
        # Find pets missing any of the new fields
        query_conditions = [
            {field: {"$exists": False}} for field in fields_to_add.keys()
        ]
        pets_to_update = pets_collection.find({"$or": query_conditions})

        count = 0
        for pet in pets_to_update:
            # Ensure _id is ObjectId
            pet_id = pet.get('_id')
            if pet_id is None:
                continue # Skip if no ID somehow

            if not isinstance(pet_id, ObjectId):
                try:
                    pet_id = ObjectId(pet_id)
                except Exception:
                    logger.warning(f"Skipping migration for invalid pet ID: {pet_id}")
                    continue

            update_doc = {"$set": {}}
            for field, default_value in fields_to_add.items():
                if field not in pet:
                    update_doc["$set"][field] = default_value

            if update_doc["$set"]: # Only add if there's something to set
                updates.append(UpdateOne({"_id": pet_id}, update_doc))
                count += 1

        if updates:
            result = pets_collection.bulk_write(updates)
            logger.info(f"Database migration completed. Updated {result.modified_count} pet documents.")
        else:
            logger.info("No pet documents required migration.")

        client.close()
    except Exception as e:
        logger.error(f"Database migration failed: {e}", exc_info=True)
# --- End Database Migration Logic ---


class AstroStatsBot(commands.Bot):
    """Custom bot class with additional functionality."""

    def __init__(self):
        intents = discord.Intents.default()
        # Add message content intent if needed, but be mindful of verification requirements
        # intents.message_content = True
        super().__init__(command_prefix="/", intents=intents)
        self._emoji_cache = {}
        self.processed_issues = {}

    async def setup_hook(self):
        """Called when the bot is started. Used to load cogs and sync commands."""
        # --- Run Database Migration ---
        await run_database_migration()
        # --- End Database Migration ---

        # Import cog setup functions only when needed to avoid circular imports
        from cogs.games.apex import setup as setup_apex
        from cogs.games.league import setup as setup_league
        from cogs.games.fortnite import setup as setup_fortnite
        from cogs.games.tft import setup as setup_tft
        from cogs.general.help import setup as setup_help
        from cogs.general.horoscope import setup as setup_horoscope
        from cogs.general.review import setup as setup_review
        from cogs.general.premium import setup as setup_premium
        from cogs.general.show_update import setup as setup_show_update
        from cogs.general.support import setup as setup_support
        from cogs.systems.pet_battles import setup as setup_pet_battles
        from cogs.systems.squib_game import setup as setup_squib_game
        from cogs.admin.kick import setup as setup_kick
        from cogs.admin.servers import setup as setup_servers
        from cogs.games.truthordare import setup as setup_truth_or_dare # Add this import
        from cogs.games.wouldyourather import setup as setup_would_you_rather

        # Setup all cogs
        await setup_apex(self)
        await setup_league(self)
        await setup_fortnite(self)
        await setup_tft(self)
        await setup_help(self)
        await setup_horoscope(self)
        await setup_review(self)
        await setup_premium(self)
        await setup_show_update(self)
        await setup_support(self)
        await setup_pet_battles(self)
        await setup_kick(self)
        await setup_servers(self)
        await setup_squib_game(self)
        await setup_truth_or_dare(self) # Add this line to load the cog
        await setup_would_you_rather(self)

        # Setup error handlers
        setup_error_handlers(self)

        # Start tasks
        self.update_presence.start()

        # Sync commands
        # Sync globally first
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} global application commands.")
        except Exception as e:
            logger.error(f"Failed to sync global commands: {e}")

        # Sync guild-specific commands if needed (e.g., for admin commands)
        # Example: await self.tree.sync(guild=discord.Object(id=YOUR_GUILD_ID))

        logger.info("Command syncing process completed.")


    @tasks.loop(hours=1)
    async def update_presence(self):
        """Update the bot's presence with the server count."""
        guild_count = len(self.guilds)
        activity_name = f"/help | {guild_count} servers"
        # Use Playing status which is common for bots
        presence = discord.Activity(type=discord.ActivityType.playing, name=activity_name)
        try:
            await self.change_presence(activity=presence)
        except Exception as e:
            logger.error(f"Failed to update presence: {e}")


    @update_presence.before_loop
    async def before_update_presence(self):
        """Wait until the bot is ready before updating presence."""
        await self.wait_until_ready()
        logger.info("Bot is ready, starting presence update loop.")

    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f"{self.user} connected to Discord (ID: {self.user.id}). Ready!")

    async def on_guild_join(self, guild: discord.Guild):
        # Check if the guild is blacklisted
        if guild.id in BLACKLISTED_GUILDS:
            logger.warning(f"Leaving blacklisted guild: {guild.name} ({guild.id})")
            try:
                await guild.leave()
            except discord.HTTPException as e:
                logger.error(f"Failed to leave blacklisted guild {guild.id}: {e}")
            return

        # Send welcome message
        await self.send_welcome_message(guild)

    async def send_welcome_message(self, guild: discord.Guild):
        """Sends a welcome message to a new guild."""
        embed = discord.Embed(
            title=f"Thanks for adding AstroStats to {guild.name}!",
            description="I'm here to help you track game stats and have fun with mini-games!",
            color=discord.Color.blue()
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(
            name="🚀 Getting Started",
            value=(
                "Use `/help` to see all my commands.\n"
                "Track stats for Apex, Fortnite, LoL, and TFT.\n"
                "Try the `/petbattles` or `/squibgames` mini-games!"
            ),
            inline=False
        )
        embed.add_field(
            name="🔗 Important Links",
            value=(
                "[Documentation](https://astrostats.info) | "
                "[Support](https://astrostats.info) | "
                "[Issue Tracker](https://astrostats.info) | "
                "[Support Us ❤️](https://astrostats.info)"
            ),
            inline=False
        )
        embed.add_field(
            name="⭐ Leave a Review!",
            value="Enjoying the bot? Consider leaving a review with `/review`!",
            inline=False
        )
        embed.set_footer(text="Let the stats tracking begin!")

        # Find a suitable channel to send the welcome message
        target_channel = guild.system_channel
        # If no system channel, try the first available text channel the bot can write to
        if target_channel is None or not target_channel.permissions_for(guild.me).send_messages:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    target_channel = channel
                    break

        # Build embeds list with optional promo
        embeds = [embed]
        try:
            promo_embed = get_premium_promotion_embed(str(guild.owner_id))
            if promo_embed:
                embeds.append(promo_embed)
        except Exception:
            # Never fail welcome on promo issues
            pass

        if target_channel:
            try:
                await target_channel.send(embeds=embeds)
            except discord.Forbidden:
                logger.warning(f"Missing permissions to send welcome message in {guild.name} ({target_channel.name})")
            except discord.HTTPException as e:
                logger.error(f"Failed to send welcome message to {guild.name}: {e}")
        else:
            logger.warning(f"No suitable channel found to send welcome message in {guild.name}")


def create_bot():
    """Create and return a new instance of the AstroStatsBot."""
    return AstroStatsBot()


async def run_bot():
    """Run the bot."""
    if not TOKEN:
        logger.critical("BOT TOKEN IS NOT SET. Please configure the TOKEN environment variable.")
        return # Exit if no token

    bot = create_bot()
    try:
        await bot.start(TOKEN)
    except discord.LoginFailure:
        logger.critical("Failed to log in: Improper token provided.")
    except Exception as e:
        logger.critical(f"Fatal error during bot execution: {e}", exc_info=True)
