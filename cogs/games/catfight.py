"""
Catfight PvP Battle System
Player vs Player battles with server leaderboards and dynamic images.
"""
import asyncio
import random
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple
from io import BytesIO

import discord
from discord.ext import commands
from discord import app_commands, Interaction
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from config.settings import MONGODB_URI
from services.image_generator import battle_image_generator
from ui.embeds import get_premium_promotion_view
from core.utils import get_conditional_embed

logger = logging.getLogger(__name__)

# MongoDB setup
mongo_client: Optional[MongoClient] = None
db = None
catfight_stats = None

try:
    if MONGODB_URI:
        mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=30000, connectTimeoutMS=20000, socketTimeoutMS=20000)
        mongo_client.admin.command('ping')
        db = mongo_client['astrostats_database']
        catfight_stats = db['catfight_stats']
        logger.debug("Catfight: MongoDB connection established")
    else:
        logger.warning("Catfight: MONGODB_URI not set, database functionality disabled")
except ConnectionFailure as e:
    logger.error(f"Catfight: MongoDB connection failed: {e}")
    mongo_client = None
    db = None
    catfight_stats = None
except Exception as e:
    logger.error(f"Catfight: Failed to initialize MongoDB: {e}")
    mongo_client = None
    db = None
    catfight_stats = None

# Battle attacks with damage ranges
BATTLE_ATTACKS = [
    {"name": "Claw Swipe", "damage": (8, 18), "emoji": "🐾", "desc": "rakes their claws across their opponent"},
    {"name": "Pounce Attack", "damage": (12, 22), "emoji": "🦘", "desc": "leaps through the air with deadly precision"},
    {"name": "Tail Whip", "damage": (6, 16), "emoji": "🌪️", "desc": "delivers a spinning tail strike"},
    {"name": "Bite Strike", "damage": (10, 20), "emoji": "🦷", "desc": "sinks their fangs deep"},
    {"name": "Fury Swipes", "damage": (4, 14), "emoji": "💥", "desc": "unleashes a flurry of rapid strikes"},
    {"name": "Stealth Strike", "damage": (15, 25), "emoji": "🥷", "desc": "emerges from the shadows for a sneak attack"},
    {"name": "Sonic Screech", "damage": (7, 17), "emoji": "📢", "desc": "lets out a deafening battle cry"},
    {"name": "Nine Lives Rush", "damage": (11, 21), "emoji": "✨", "desc": "channels their mystical cat powers"},
    {"name": "Hairball Launcher", "damage": (5, 15), "emoji": "💩", "desc": "launches a disgusting but effective projectile"},
    {"name": "Catnip Frenzy", "damage": (9, 19), "emoji": "🌿", "desc": "goes into a wild catnip-induced rage"},
    {"name": "Laser Eyes", "damage": (13, 23), "emoji": "👁️", "desc": "fires concentrated laser beams"},
    {"name": "Purr Vibration", "damage": (6, 16), "emoji": "😸", "desc": "creates destructive sound waves with their purr"},
    {"name": "Whisker Sense", "damage": (8, 18), "emoji": "😺", "desc": "uses enhanced senses for a precision strike"},
    {"name": "Belly Rub Trap", "damage": (10, 20), "emoji": "🪤", "desc": "lures their opponent into a false sense of security"},
    {"name": "Cardboard Box Slam", "damage": (12, 22), "emoji": "📦", "desc": "weaponizes their favorite hiding spot"},
]

# Critical hit messages (20% chance for extra damage)
CRITICAL_HITS = [
    "delivers a DEVASTATING blow!",
    "scores a CRITICAL HIT!",
    "finds the perfect opening!",
    "channels their inner warrior!",
    "strikes with legendary precision!",
]

# Miss messages (10% chance to miss)
MISS_MESSAGES = [
    "swipes at thin air!",
    "gets distracted by a dust bunny!",
    "slips on an imaginary banana peel!",
    "aims for the opponent but hits a pillow instead!",
    "gets confused and attacks their own reflection!",
]

class CatfightCog(commands.Cog):
    """Catfight PvP battle system with leaderboards."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    def is_database_available(self) -> bool:
        """Check if database is available."""
        return catfight_stats is not None
    
    async def get_user_stats(self, user_id: str, guild_id: str) -> Dict:
        """Get user's catfight stats."""
        if not self.is_database_available():
            return {"wins": 0, "losses": 0, "win_streak": 0, "loss_streak": 0}
        
        try:
            stats = catfight_stats.find_one({
                "user_id": user_id,
                "guild_id": guild_id
            })
            
            if stats:
                return {
                    "wins": stats.get("wins", 0),
                    "losses": stats.get("losses", 0),
                    "win_streak": stats.get("win_streak", 0),
                    "loss_streak": stats.get("loss_streak", 0),
                    "username": stats.get("username", "Unknown")
                }
            else:
                return {"wins": 0, "losses": 0, "win_streak": 0, "loss_streak": 0}
                
        except Exception as e:
            logger.error(f"Failed to get user stats: {e}")
            return {"wins": 0, "losses": 0, "win_streak": 0, "loss_streak": 0}
    
    async def update_user_stats(self, user_id: str, guild_id: str, username: str, won: bool):
        """Update user's battle stats."""
        if not self.is_database_available():
            return
        
        try:
            current_stats = await self.get_user_stats(user_id, guild_id)
            
            if won:
                new_stats = {
                    "wins": current_stats["wins"] + 1,
                    "win_streak": current_stats["win_streak"] + 1,
                    "loss_streak": 0,  # Reset loss streak
                    "losses": current_stats["losses"]
                }
            else:
                new_stats = {
                    "losses": current_stats["losses"] + 1,
                    "loss_streak": current_stats["loss_streak"] + 1,
                    "win_streak": 0,  # Reset win streak
                    "wins": current_stats["wins"]
                }
            
            # Update in database
            catfight_stats.update_one(
                {"user_id": user_id, "guild_id": guild_id},
                {
                    "$set": {
                        **new_stats,
                        "username": username,
                        "last_battle": datetime.now(timezone.utc)
                    }
                },
                upsert=True
            )
            
        except Exception as e:
            logger.error(f"Failed to update user stats: {e}")
    
    async def get_leaderboard(self, guild_id: str, limit: int = 10) -> List[Dict]:
        """Get server leaderboard."""
        if not self.is_database_available():
            return []
        
        try:
            # Sort by wins descending, then by win_streak descending
            leaderboard = list(catfight_stats.find(
                {"guild_id": guild_id}
            ).sort([
                ("wins", -1),
                ("win_streak", -1)
            ]).limit(limit))
            
            return leaderboard
            
        except Exception as e:
            logger.error(f"Failed to get leaderboard: {e}")
            return []
    
    def create_hp_bar(self, current_hp: int, max_hp: int = 100, length: int = 20) -> str:
        """Create a visual HP bar."""
        filled = int((current_hp / max_hp) * length)
        empty = length - filled
        
        if current_hp > 60:
            bar_char = "🟢"
        elif current_hp > 30:
            bar_char = "🟡"
        else:
            bar_char = "🔴"
            
        return f"{bar_char * filled}{'⚫' * empty} {current_hp}/{max_hp} HP"
    
    def execute_attack(self) -> Dict:
        """Execute a random attack and return results."""
        attack = random.choice(BATTLE_ATTACKS)
        
        # 10% chance to miss
        if random.random() < 0.1:
            return {
                "attack": attack,
                "damage": 0,
                "missed": True,
                "critical": False,
                "message": random.choice(MISS_MESSAGES)
            }
        
        # Calculate damage
        min_dmg, max_dmg = attack["damage"]
        base_damage = random.randint(min_dmg, max_dmg)
        
        # 20% chance for critical hit (1.5x damage)
        is_critical = random.random() < 0.2
        final_damage = int(base_damage * 1.5) if is_critical else base_damage
        
        return {
            "attack": attack,
            "damage": final_damage,
            "missed": False,
            "critical": is_critical,
            "message": random.choice(CRITICAL_HITS) if is_critical else attack["desc"]
        }
    
    @app_commands.command(name="catfight", description="Challenge another user to an epic HP-based cat battle!")
    @app_commands.describe(opponent="The user you want to battle against")
    async def catfight(self, interaction: Interaction, opponent: discord.Member):
        """Initiate an epic HP-based catfight battle."""
        await interaction.response.defer()
        
        user1 = interaction.user
        user2 = opponent
        guild_id = str(interaction.guild_id)
        
        # Validation checks
        if user1.id == user2.id:
            embed = discord.Embed(
                title="❌ Invalid Battle",
                description="You can't battle yourself! Find a worthy opponent!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        if user2.bot:
            embed = discord.Embed(
                title="❌ Invalid Battle",
                description="You can't battle bots! They don't have the warrior spirit!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        try:
            # Initialize battle state
            user1_hp = 100
            user2_hp = 100
            round_num = 1
            battle_log = []
            
            # Create dynamic battle image
            battle_image = None
            file = None
            try:
                user1_avatar = user1.display_avatar.url
                user2_avatar = user2.display_avatar.url
                
                battle_image = await battle_image_generator.create_battle_image(
                    user1_avatar, user2_avatar,
                    user1.display_name, user2.display_name
                )
                
                file = discord.File(battle_image, filename="catfight_battle.png")
                
            except Exception as e:
                logger.error(f"Failed to create battle image: {e}")
            
            # Create initial battle embed
            embed = discord.Embed(
                title="⚔️ EPIC CATFIGHT BATTLE BEGINS!",
                description=f"**{user1.display_name}** VS **{user2.display_name}**\n\nPrepare for an epic showdown!",
                color=discord.Color.blue()
            )
            
            # Don't set image in embed - we want it outside
            
            # Add HP bars
            embed.add_field(
                name=f"💖 {user1.display_name}",
                value=self.create_hp_bar(user1_hp),
                inline=False
            )
            embed.add_field(
                name=f"💖 {user2.display_name}",
                value=self.create_hp_bar(user2_hp),
                inline=False
            )
            
            embed.add_field(
                name="⚡ Battle Status",
                value="The battle is about to begin! Who will emerge victorious?",
                inline=False
            )
            
            # Send initial battle message
            if file:
                message = await interaction.followup.send(embed=embed, file=file)
            else:
                message = await interaction.followup.send(embed=embed)
            
            # Battle loop
            while user1_hp > 0 and user2_hp > 0:
                await asyncio.sleep(3)  # Suspenseful pause
                
                # Determine who attacks (alternating turns with slight randomness)
                if round_num % 2 == 1:
                    attacker = user1
                    defender = user2
                    defender_hp = user2_hp
                else:
                    attacker = user2
                    defender = user1
                    defender_hp = user1_hp
                
                # Execute attack
                attack_result = self.execute_attack()
                damage = attack_result["damage"]
                
                # Apply damage
                if attacker == user1:
                    user2_hp = max(0, user2_hp - damage)
                    defender_hp = user2_hp
                else:
                    user1_hp = max(0, user1_hp - damage)
                    defender_hp = user1_hp
                
                # Create battle log entry
                if attack_result["missed"]:
                    log_entry = f"**{attacker.display_name}** {attack_result['attack']['emoji']} {attack_result['attack']['name']} but {attack_result['message']}"
                else:
                    critical_text = " ⚡**CRITICAL**⚡" if attack_result["critical"] else ""
                    log_entry = f"**{attacker.display_name}** {attack_result['attack']['emoji']} {attack_result['attack']['name']} and {attack_result['message']}! **{damage} damage**{critical_text}"
                
                battle_log.append(log_entry)
                
                # Update embed
                embed = discord.Embed(
                    title=f"⚔️ CATFIGHT BATTLE - Round {round_num}",
                    description=f"**{user1.display_name}** VS **{user2.display_name}**",
                    color=discord.Color.red() if min(user1_hp, user2_hp) < 30 else discord.Color.orange()
                )
                
                # Image is sent separately outside the embed
                
                # Add HP bars with updated values
                embed.add_field(
                    name=f"💖 {user1.display_name}",
                    value=self.create_hp_bar(user1_hp),
                    inline=False
                )
                embed.add_field(
                    name=f"💖 {user2.display_name}",
                    value=self.create_hp_bar(user2_hp),
                    inline=False
                )
                
                # Show recent battle log (last 3 actions)
                recent_log = battle_log[-3:] if len(battle_log) > 3 else battle_log
                embed.add_field(
                    name="⚡ Recent Actions",
                    value="\n".join(recent_log) if recent_log else "The battle begins!",
                    inline=False
                )
                
                # Check for battle end
                if user1_hp <= 0 or user2_hp <= 0:
                    break
                
                try:
                    await message.edit(embed=embed)
                except discord.NotFound:
                    # Message was deleted, send a new one
                    message = await interaction.followup.send(embed=embed)
                except Exception as e:
                    logger.error(f"Failed to edit battle message: {e}")
                
                round_num += 1
            
            # Determine winner and update stats
            winner = user1 if user2_hp <= 0 else user2
            loser = user2 if winner == user1 else user1
            user1_wins = winner == user1
            
            # Final victory embed
            final_embed = discord.Embed(
                title="🏆 BATTLE COMPLETE! 🏆",
                description=(
                    f"After **{round_num}** intense rounds...\n\n"
                    f"🎉 **WINNER: {winner.display_name}!** 🎉\n"
                    f"💔 **Defeated: {loser.display_name}**"
                ),
                color=discord.Color.gold()
            )
            
            final_embed.add_field(
                name="⚡ Final Battle Log",
                value="\n".join(battle_log[-5:]) if battle_log else "Epic battle!",
                inline=False
            )
            
            # Update stats
            await self.update_user_stats(str(user1.id), guild_id, user1.display_name, user1_wins)
            await self.update_user_stats(str(user2.id), guild_id, user2.display_name, not user1_wins)
            
            # Get updated stats
            updated_user1_stats = await self.get_user_stats(str(user1.id), guild_id)
            updated_user2_stats = await self.get_user_stats(str(user2.id), guild_id)
            
            # Stats display
            final_embed.add_field(
                name=f"📊 {user1.display_name}'s Stats",
                value=(
                    f"🏆 Wins: **{updated_user1_stats['wins']}**\n"
                    f"💔 Losses: **{updated_user1_stats['losses']}**\n"
                    f"🔥 Win Streak: **{updated_user1_stats['win_streak']}**"
                ),
                inline=True
            )
            
            final_embed.add_field(
                name=f"📊 {user2.display_name}'s Stats",
                value=(
                    f"🏆 Wins: **{updated_user2_stats['wins']}**\n"
                    f"💔 Losses: **{updated_user2_stats['losses']}**\n"
                    f"🔥 Win Streak: **{updated_user2_stats['win_streak']}**"
                ),
                inline=True
            )
            
            final_embed.set_footer(text="Use /catfight-leaderboard to see server rankings!")
            final_embed.timestamp = datetime.now(timezone.utc)
            
            # Get premium view
            premium_view = get_premium_promotion_view(str(winner.id))
            
            # Edit original message with final result
            await asyncio.sleep(2)  # Final dramatic pause
            try:
                await message.edit(embed=final_embed, view=premium_view)
            except discord.NotFound:
                # Fallback if original message was deleted
                await interaction.followup.send(embed=final_embed, view=premium_view)
            except Exception as e:
                logger.error(f"Failed to edit final message: {e}")
                await interaction.followup.send(embed=final_embed, view=premium_view)
            
        except Exception as e:
            logger.error(f"Error in catfight command: {e}")
            error_embed = discord.Embed(
                title="❌ Battle Error",
                description="Something went wrong during the battle! Try again later.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    @app_commands.command(name="catfight-leaderboard", description="View the server's catfight leaderboard")
    async def catfight_leaderboard(self, interaction: Interaction):
        """Display server catfight leaderboard."""
        await interaction.response.defer()
        
        guild_id = str(interaction.guild_id)
        server_name = interaction.guild.name
        
        try:
            leaderboard = await self.get_leaderboard(guild_id, limit=15)
            
            embed = discord.Embed(
                title=f"🏆 {server_name} Catfight Leaderboard",
                description="The fiercest warriors in the server!",
                color=discord.Color.gold()
            )
            
            if not leaderboard:
                embed.add_field(
                    name="📊 No Battles Yet",
                    value="No one has fought yet! Use `/catfight @user` to start the battles!",
                    inline=False
                )
            else:
                # Top 3 special formatting
                medals = ["🥇", "🥈", "🥉"]
                
                leaderboard_text = []
                for i, stats in enumerate(leaderboard):
                    position = i + 1
                    username = stats.get('username', 'Unknown')
                    wins = stats.get('wins', 0)
                    losses = stats.get('losses', 0)
                    win_streak = stats.get('win_streak', 0)
                    
                    total_battles = wins + losses
                    win_rate = (wins / total_battles * 100) if total_battles > 0 else 0
                    
                    if position <= 3:
                        medal = medals[position - 1]
                        leaderboard_text.append(
                            f"{medal} **{username}** - {wins}W/{losses}L ({win_rate:.1f}%) 🔥{win_streak}"
                        )
                    else:
                        leaderboard_text.append(
                            f"`{position:2d}.` **{username}** - {wins}W/{losses}L ({win_rate:.1f}%) 🔥{win_streak}"
                        )
                
                embed.add_field(
                    name="📊 Rankings",
                    value="\n".join(leaderboard_text),
                    inline=False
                )
                
                # Server stats
                total_battles = sum(stats.get('wins', 0) + stats.get('losses', 0) for stats in leaderboard)
                embed.add_field(
                    name="📈 Server Stats",
                    value=f"Total Warriors: **{len(leaderboard)}**\nTotal Battles: **{total_battles // 2}**",
                    inline=False
                )
            
            embed.set_footer(text="Challenge someone with /catfight @user!")
            embed.timestamp = datetime.now(timezone.utc)
            
            # Get premium view
            premium_view = get_premium_promotion_view(str(interaction.user.id))
            
            await interaction.followup.send(embed=embed, view=premium_view)
            
        except Exception as e:
            logger.error(f"Error in leaderboard command: {e}")
            error_embed = discord.Embed(
                title="❌ Leaderboard Error",
                description="Couldn't fetch the leaderboard. Try again later!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    @app_commands.command(name="catfight-stats", description="View your catfight battle statistics")
    @app_commands.describe(user="User to check stats for (optional)")
    async def catfight_stats(self, interaction: Interaction, user: Optional[discord.Member] = None):
        """Display user's catfight stats."""
        await interaction.response.defer()
        
        target_user = user or interaction.user
        guild_id = str(interaction.guild_id)
        
        try:
            stats = await self.get_user_stats(str(target_user.id), guild_id)
            
            embed = discord.Embed(
                title=f"⚔️ {target_user.display_name}'s Battle Stats",
                color=discord.Color.blue()
            )
            
            embed.set_thumbnail(url=target_user.display_avatar.url)
            
            # Basic stats
            total_battles = stats['wins'] + stats['losses']
            win_rate = (stats['wins'] / total_battles * 100) if total_battles > 0 else 0
            
            embed.add_field(
                name="📊 Battle Record",
                value=(
                    f"🏆 **Wins:** {stats['wins']}\n"
                    f"💔 **Losses:** {stats['losses']}\n"
                    f"⚖️ **Win Rate:** {win_rate:.1f}%\n"
                    f"📈 **Total Battles:** {total_battles}"
                ),
                inline=True
            )
            
            embed.add_field(
                name="🔥 Streaks",
                value=(
                    f"🔥 **Win Streak:** {stats['win_streak']}\n"
                    f"❄️ **Loss Streak:** {stats['loss_streak']}\n"
                ),
                inline=True
            )
            
            # Battle tier based on wins
            if stats['wins'] >= 50:
                tier = "🔱 Legendary Warrior"
                tier_color = 0xFFD700
            elif stats['wins'] >= 25:
                tier = "👑 Elite Fighter"
                tier_color = 0xC0C0C0
            elif stats['wins'] >= 10:
                tier = "⚔️ Veteran"
                tier_color = 0xCD7F32
            elif stats['wins'] >= 5:
                tier = "🛡️ Fighter"
                tier_color = 0x90EE90
            else:
                tier = "🐱 Novice"
                tier_color = 0x87CEEB
            
            embed.color = tier_color
            embed.add_field(
                name="🎖️ Battle Tier",
                value=tier,
                inline=False
            )
            
            if total_battles == 0:
                embed.add_field(
                    name="💡 Ready to Fight?",
                    value="You haven't fought any battles yet! Use `/catfight @user` to start your warrior journey!",
                    inline=False
                )
            
            embed.timestamp = datetime.now(timezone.utc)
            
            # Get premium view
            premium_view = get_premium_promotion_view(str(interaction.user.id))
            
            await interaction.followup.send(embed=embed, view=premium_view)
            
        except Exception as e:
            logger.error(f"Error in stats command: {e}")
            error_embed = discord.Embed(
                title="❌ Stats Error",
                description="Couldn't fetch battle stats. Try again later!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)

async def setup(bot: commands.Bot):
    """Add the CatfightCog to the bot."""
    if catfight_stats is None:
        logger.error("Cannot add CatfightCog: MongoDB connection failed")
    else:
        try:
            await bot.add_cog(CatfightCog(bot))
            logger.debug("CatfightCog loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load CatfightCog: {e}")
            print(f"[Catfight] CRITICAL: Failed to load cog: {e}")