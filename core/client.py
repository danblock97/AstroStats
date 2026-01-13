# core/client.py
import logging
import io
import base64
import asyncio
import discord
from discord.ext import commands, tasks
import datetime
from pymongo import MongoClient, UpdateOne # Import UpdateOne
from bson import ObjectId # Import ObjectId

from config.settings import TOKEN, BLACKLISTED_GUILDS, MONGODB_URI # Import MONGODB_URI
from core.errors import setup_error_handlers
from services.database.welcome import get_welcome_settings

logger = logging.getLogger(__name__) # Use __name__ for logger
# logger = logging.getLogger('discord.gateway') # Keep gateway logs less verbose if needed
# logger.setLevel(logging.ERROR)

# --- Database Migration Logic ---
async def run_database_migration():
    """Adds new fields to existing pet documents if they don't exist."""
    try:
        client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=30000,
            connectTimeoutMS=20000,
            socketTimeoutMS=20000,
        )
        db = client['astrostats_database']
        pets_collection = db['pets']
        welcome_collection = db['welcome_settings']
        logger.debug("Running database migration check for pets and welcome settings...")

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
            logger.debug(f"Database migration completed. Updated {result.modified_count} pet documents.")
        else:
            logger.debug("No pet documents required migration.")

        # Migrate welcome settings from custom_image_url to custom_image_data
        logger.debug("Migrating welcome settings...")
        welcome_docs = welcome_collection.find({"custom_image_url": {"$exists": True, "$ne": None}})
        welcome_updates = []
        
        for doc in welcome_docs:
            # Convert old URL field to new data fields (set to None for manual re-upload)
            welcome_updates.append(UpdateOne(
                {"_id": doc["_id"]},
                {
                    "$unset": {"custom_image_url": ""},
                    "$set": {
                        "custom_image_data": None,
                        "custom_image_filename": None
                    }
                }
            ))
        
        if welcome_updates:
            result = welcome_collection.bulk_write(welcome_updates)
            logger.debug(f"Migrated {result.modified_count} welcome settings. Users will need to re-upload images.")
        else:
            logger.debug("No welcome settings required migration.")

        # Summary info for tests and visibility
        logger.info("Database migration check completed.")
        client.close()
    except Exception as e:
        logger.error(f"Database migration failed: {e}", exc_info=True)
# --- End Database Migration Logic ---


class AstroStatsBot(commands.Bot):
    """Custom bot class with additional functionality."""

    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True  # Required for member join events
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
        
        # Initialize premium service connection early
        from services.premium import initialize_premium_service
        initialize_premium_service()

        # Import cog setup functions only when needed to avoid circular imports
        from cogs.games.apex import setup as setup_apex
        from cogs.games.league import setup as setup_league
        from cogs.games.fortnite import setup as setup_fortnite
        from cogs.games.tft import setup as setup_tft
        from cogs.general.help import setup as setup_help
        from cogs.general.horoscope import setup as setup_horoscope
        from cogs.general.review import setup as setup_review
        from cogs.general.premium import setup as setup_premium
        from cogs.general.support import setup as setup_support
        from cogs.systems.pet_battles import setup as setup_pet_battles
        from cogs.systems.squib_game import setup as setup_squib_game
        from cogs.systems.bingo_game import setup as setup_bingo_game
        from cogs.admin.kick import setup as setup_kick
        from cogs.admin.servers import setup as setup_servers
        from cogs.admin.welcome import setup as setup_welcome
        from cogs.games.truthordare import setup as setup_truth_or_dare # Add this import
        from cogs.games.wouldyourather import setup as setup_would_you_rather
        from cogs.games.catfight import setup as setup_catfight
        from cogs.general.cosmos import setup as setup_cosmos

        # Setup all cogs concurrently to reduce startup time
        await asyncio.gather(
            setup_apex(self),
            setup_league(self),
            setup_fortnite(self),
            setup_tft(self),
            setup_help(self),
            setup_horoscope(self),
            setup_review(self),
            setup_premium(self),
            setup_support(self),
            setup_pet_battles(self),
            setup_kick(self),
            setup_servers(self),
            setup_welcome(self),
            setup_squib_game(self),
            setup_bingo_game(self),
            setup_truth_or_dare(self),
            setup_would_you_rather(self),
            setup_catfight(self),
            setup_cosmos(self),
        )

        # Setup error handlers
        setup_error_handlers(self)

        # Start tasks
        self.update_presence.start()

        # Sync commands (tests expect this to be awaited here)
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} global application commands.")
        except Exception as e:
            logger.error(f"Failed to sync global commands: {e}")
        logger.debug("Command syncing process completed.")


    @tasks.loop(hours=1)
    async def update_presence(self):
        """Update the bot's presence with the server count."""
        guild_count = len(self.guilds)
        activity_name = f"/premium | {guild_count} servers"
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
            title=f"🎉 Welcome to AstroStats!",
            description=(
                f"Thanks for adding me to **{guild.name}**!\n\n"
                "I'm your all-in-one gaming companion for **stat tracking**, **mini-games**, and **entertainment**. "
                "Let's explore what I can do for you!"
            ),
            color=0x00d4ff
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        # Game Stats Section
        embed.add_field(
            name="📊 **Game Statistics**",
            value=(
                "**🎯 Apex Legends** - `/apex <platform> <username>`\n"
                "**⚔️ League of Legends** - `/league profile <region> <riotid>`\n"
                "**🏆 Teamfight Tactics** - `/tft <region> <riotid>`\n"
                "**🏗️ Fortnite** - `/fortnite <timeframe> <username>`"
            ),
            inline=False
        )

        # Mini-Games Section
        embed.add_field(
            name="🎮 **Interactive Mini-Games**",
            value=(
                "**🐾 Pet Battles** - `/petbattles summon` • `/petbattles battle` • `/petbattles stats`\n"
                "**🦑 Squib Games** - `/squibgames start` • `/squibgames run` • `/squibgames status`\n"
                "**🎲 Bingo** - `/bingo start` • `/bingo run` • `/bingo stats` • `/bingo leaderboard`\n"
                "**⚔️ Catfight PvP** - `/catfight @user` • `/catfight-leaderboard` • `/catfight-stats`\n"
                "**🎲 Party Games** - `/truthordare` • `/wouldyourather`"
            ),
            inline=False
        )

        # Entertainment Section
        embed.add_field(
            name="✨ **Entertainment & More**",
            value=(
                "**🔮 Daily Horoscope** - `/horoscope <sign>`\n"
                "**❓ Help & Support** - `/help` • `/support` • `/issues`\n"
                "**⭐ Show Love** - `/review` (Leave us a review!)"
            ),
            inline=False
        )

        # Premium Section
        embed.add_field(
            name="💎 **Premium Features**",
            value=(
                "Unlock **unlimited players** in Squib Games, **extended pet capacity**, "
                "and exclusive features!\n\n"
                "**💰 Pricing:** Supporter £3/mo • Sponsor £5/mo • VIP £10/mo\n\n"
                "**🚀 Get Premium** - `/premium`\n"
                "**📖 View Details** - [astrostats.info/pricing](https://astrostats.info/pricing)"
            ),
            inline=False
        )

        # Links Section
        embed.add_field(
            name="🔗 **Quick Links**",
            value=(
                "[📖 Documentation](https://astrostats.info) • "
                "[💬 Support](https://www.astrostats.info/support) • "
                "[🐛 Report Issues](https://astrostats.info) • "
                "[❤️ Support Us](https://astrostats.info/pricing)"
            ),
            inline=False
        )
        
        embed.set_footer(
            text="🚀 Ready to dominate the leaderboards? Let's get started!",
            icon_url="https://astrostats.info/favicon.ico"
        )

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
            pass
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

    async def on_member_join(self, member: discord.Member):
        """Called when a new member joins a guild."""
        try:
            # Get welcome settings for the guild
            welcome_settings = get_welcome_settings(str(member.guild.id))
            
            # Check if welcome messages are enabled for this guild
            if not welcome_settings or not welcome_settings.enabled:
                return
            
            # Find the target channel (system channel or first available text channel)
            target_channel = member.guild.system_channel
            
            if target_channel is None or not target_channel.permissions_for(member.guild.me).send_messages:
                for channel in member.guild.text_channels:
                    if channel.permissions_for(member.guild.me).send_messages:
                        target_channel = channel
                        break
            
            if target_channel is None:
                logger.warning(f"No suitable channel found to send member welcome in {member.guild.name}")
                return
            
            # Create the welcome message
            if welcome_settings.custom_message:
                # Use custom message with placeholder replacement
                message_content = welcome_settings.custom_message.replace(
                    "{user}", member.mention
                ).replace(
                    "{username}", member.display_name
                ).replace(
                    "{server}", member.guild.name
                )
                
                # Replace channel mentions like {#channel-name} with actual channel mentions
                import re
                def replace_channel_mention(match):
                    channel_name = match.group(1)
                    # Find channel by name (case insensitive)
                    for channel in member.guild.text_channels:
                        if channel.name.lower() == channel_name.lower():
                            return channel.mention
                    # If channel not found, return original text
                    return f"#{channel_name}"
                
                message_content = re.sub(r'\{#([^}]+)\}', replace_channel_mention, message_content)
            else:
                # Use default welcome message
                message_content = f"Welcome {member.mention} to **{member.guild.name}**! Please verify yourself and get to know everyone!"
            
            # Send message with optional image attachment in single message
            if welcome_settings.custom_image_data:
                try:
                    # Decode base64 image data and send with text
                    image_bytes = base64.b64decode(welcome_settings.custom_image_data)
                    filename = welcome_settings.custom_image_filename or "welcome_image.webp"
                    file = discord.File(io.BytesIO(image_bytes), filename=filename)
                    await target_channel.send(content=message_content, file=file)
                except Exception as e:
                    logger.error(f"Error sending welcome image: {e}")
                    # Fallback to text only if image fails
                    await target_channel.send(content=message_content)
            else:
                # Send just the text message
                await target_channel.send(content=message_content)
            logger.debug(f"Sent welcome message for {member} in {member.guild.name}")
            
        except Exception as e:
            logger.error(f"Error sending welcome message for {member} in {member.guild.name}: {e}", exc_info=True)


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
