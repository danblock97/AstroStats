import os
import random
import asyncio
from datetime import datetime, timedelta, timezone, time as dtime

import discord
from discord.ext import commands, tasks
from discord import app_commands
from pymongo import MongoClient
import topgg

from quests_and_achievements import DAILY_QUESTS, ACHIEVEMENTS

# ------------------------------------------------------
# Configure Logging
# ------------------------------------------------------
import logging

logging.basicConfig(
    level=logging.ERROR,  # Set logging level to ERROR only
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

# Create a logger instance
logger = logging.getLogger("PetBattlesCog")

# ------------------------------------------------------
# MongoDB Setup
# ------------------------------------------------------
mongo_client = MongoClient(os.getenv('MONGODB_URI'))
db = mongo_client['pet_database']
pets_collection = db['pets']
battle_logs_collection = db['battle_logs']

# ------------------------------------------------------
# Constants
# ------------------------------------------------------
INITIAL_STATS = {
    "level": 1,
    "xp": 0,
    "strength": 10,
    "defense": 10,
    "health": 100
}

LEVEL_UP_INCREASES = {
    "strength": 5,
    "defense": 5,
    "health": 20
}

PET_LIST = {
    "lion": "https://raw.githubusercontent.com/danblock97/astrostats/main/images/lion.png",
    "dog": "https://raw.githubusercontent.com/danblock97/astrostats/main/images/dog.png",
    "cat": "https://raw.githubusercontent.com/danblock97/astrostats/main/images/cat.png",
    "tiger": "https://raw.githubusercontent.com/danblock97/astrostats/main/images/tiger.png",
    "rhino": "https://raw.githubusercontent.com/danblock97/astrostats/main/images/rhino.png",
    "panda": "https://raw.githubusercontent.com/danblock97/astrostats/main/images/panda.png",
    "red panda": "https://raw.githubusercontent.com/danblock97/astrostats/main/images/red_panda.png",
    "fox": "https://raw.githubusercontent.com/danblock97/astrostats/main/images/fox.png"
}

COLOR_LIST = {
    "red": 0xFF0000,
    "green": 0x00FF00,
    "blue": 0x0000FF,
    "yellow": 0xFFFF00,
    "purple": 0x800080
}

# ------------------------------------------------------
# Utility Functions
# ------------------------------------------------------
def calculate_xp_needed(level: int) -> int:
    return level ** 2 * 100

def check_level_up(pet: dict):
    leveled_up = False
    while True:
        xp_needed = calculate_xp_needed(pet['level'])
        if pet['xp'] >= xp_needed:
            pet['level'] += 1
            pet['xp'] -= xp_needed
            pet['strength'] += LEVEL_UP_INCREASES["strength"]
            pet['defense'] += LEVEL_UP_INCREASES["defense"]
            pet['health'] += LEVEL_UP_INCREASES["health"]
            leveled_up = True
        else:
            break
    return pet, leveled_up

def create_xp_bar(current: int, total: int) -> str:
    total_blocks = 10
    filled_blocks = int((current / total) * total_blocks)
    return "█" * filled_blocks + "░" * (total_blocks - filled_blocks)

def assign_daily_quests(pet: dict) -> dict:
    random_daily_quests = random.sample(DAILY_QUESTS, 3)
    pet_daily_quests = []
    for quest in random_daily_quests:
        pet_daily_quests.append({
            "id": quest["id"],
            "description": quest["description"],
            "progress_required": quest["progress_required"],
            "progress": 0,
            "completed": False,
            "xp_reward": quest["xp_reward"]
        })
    pet['daily_quests'] = pet_daily_quests
    if pet.get('_id') is not None:
        pets_collection.update_one({"_id": pet["_id"]}, {"$set": {"daily_quests": pet_daily_quests}})
    return pet

def assign_achievements(pet: dict) -> dict:
    pet_achievements = []
    for achievement in ACHIEVEMENTS:
        pet_achievements.append({
            "id": achievement["id"],
            "description": achievement["description"],
            "progress_required": achievement["progress_required"],
            "progress": 0,
            "completed": False,
            "xp_reward": achievement["xp_reward"]
        })
    pet['achievements'] = pet_achievements
    if pet.get('_id') is not None:
        pets_collection.update_one({"_id": pet["_id"]}, {"$set": {"achievements": pet_achievements}})
    return pet

def ensure_quests_and_achievements(pet: dict) -> dict:
    if 'daily_quests' not in pet or not pet['daily_quests']:
        pet = assign_daily_quests(pet)
    if 'achievements' not in pet or not pet['achievements']:
        pet = assign_achievements(pet)
    return pet

def update_quests_and_achievements(pet: dict, battle_stats: dict):
    completed_quests = []
    completed_achievements = []

    # Update Daily Quests
    for quest in pet['daily_quests']:
        if quest['completed']:
            continue
        if "Win " in quest['description']:
            quest['progress'] += battle_stats.get('battles_won', 0)
        elif "battle win streak" in quest['description']:
            if pet.get('killstreak', 0) >= quest['progress_required']:
                quest['progress'] = quest['progress_required']
        elif "battle killstreak" in quest['description']:
            if pet.get('killstreak', 0) >= quest['progress_required']:
                quest['progress'] = quest['progress_required']
        elif "Inflict" in quest['description'] and "critical hits" in quest['description']:
            quest['progress'] += battle_stats.get('critical_hits', 0)
        elif "Land" in quest['description'] and "lucky hits" in quest['description']:
            quest['progress'] += battle_stats.get('lucky_hits', 0)
        elif "Lose" in quest['description']:
            quest['progress'] += battle_stats.get('battles_lost', 0)
        elif "Earn" in quest['description'] and "XP from battles" in quest['description']:
            quest['progress'] += battle_stats.get('xp_earned', 0)
        elif "Participate in" in quest['description'] and "battles" in quest['description']:
            quest['progress'] += 1
        elif "Deal" in quest['description'] and "damage in total" in quest['description']:
            quest['progress'] += battle_stats.get('damage_dealt', 0)

        if quest['progress'] >= quest['progress_required']:
            quest['progress'] = quest['progress_required']
            quest['completed'] = True
            pet['xp'] += quest['xp_reward']
            completed_quests.append(quest)

    # Update Achievements
    for achievement in pet['achievements']:
        if achievement['completed']:
            continue
        if "Win " in achievement['description']:
            achievement['progress'] += battle_stats.get('battles_won', 0)
        elif "battle killstreak" in achievement['description']:
            if pet.get('killstreak', 0) >= achievement['progress_required']:
                achievement['progress'] = achievement['progress_required']
        elif "Deal" in achievement['description'] and "total damage" in achievement['description']:
            achievement['progress'] += battle_stats.get('damage_dealt', 0)
        elif "Land" in achievement['description'] and "critical hits" in achievement['description']:
            achievement['progress'] += battle_stats.get('critical_hits', 0)
        elif "Land" in achievement['description'] and "lucky hits" in achievement['description']:
            achievement['progress'] += battle_stats.get('lucky_hits', 0)

        if achievement['progress'] >= achievement['progress_required']:
            achievement['progress'] = achievement['progress_required']
            achievement['completed'] = True
            pet['xp'] += achievement['xp_reward']
            completed_achievements.append(achievement)

    return completed_quests, completed_achievements

# ------------------------------------------------------
# PetBattles GroupCog
# ------------------------------------------------------
class PetBattles(commands.GroupCog, name="petbattles"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reset_daily_quests.start()
        self.topgg_client = None
        self.bot.loop.create_task(self.initialize_topgg_client())

    # ------------------------------------------------------
    # Top.gg Client Initialization
    # ------------------------------------------------------
    async def initialize_topgg_client(self):
        topgg_token = os.getenv('TOPGG_TOKEN')
        if not topgg_token:
            logger.error("Top.gg token is not configured. Voting functionality will not work.")
            return
        try:
            self.topgg_client = topgg.DBLClient(self.bot, topgg_token)
        except Exception as e:
            logger.error(f"Failed to initialize Top.gg client: {e}")

    # ------------------------------------------------------
    # Daily Quests Reset Task
    # ------------------------------------------------------
    @tasks.loop(time=dtime(hour=0, minute=0, tzinfo=timezone.utc))
    async def reset_daily_quests(self):
        try:
            all_pets = pets_collection.find()
            for pet in all_pets:
                assign_daily_quests(pet)
        except Exception as e:
            logger.error(f"Error resetting daily quests: {e}")

    # ------------------------------------------------------
    # /petbattles summon
    # ------------------------------------------------------
    @app_commands.command(name="summon", description="Summon a new pet")
    @app_commands.describe(name="Name your pet", pet="Choose your pet")
    @app_commands.choices(
        pet=[
            app_commands.Choice(name="Lion", value="lion"),
            app_commands.Choice(name="Dog", value="dog"),
            app_commands.Choice(name="Cat", value="cat"),
            app_commands.Choice(name="Tiger", value="tiger"),
            app_commands.Choice(name="Rhino", value="rhino"),
            app_commands.Choice(name="Panda", value="panda"),
            app_commands.Choice(name="Red Panda", value="red panda"),
            app_commands.Choice(name="Fox", value="fox"),
        ]
    )
    async def summon(self, interaction: discord.Interaction, name: str, pet: app_commands.Choice[str]):
        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild.id)

        try:
            if pets_collection.find_one({"user_id": user_id, "guild_id": guild_id}):
                embed = discord.Embed(
                    title="Pet Summon Failed",
                    description=f"{interaction.user.mention}, you already have a pet in this server!",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed)
                return

            random_color = random.choice(list(COLOR_LIST.values()))
            new_pet = {
                "user_id": user_id,
                "guild_id": guild_id,
                "name": name,
                "icon": PET_LIST[pet.value],
                "color": random_color,
                **INITIAL_STATS,
                "killstreak": 0,
                "loss_streak": 0,
                "daily_quests": [],
                "achievements": [],
                "last_vote_reward_time": None
            }

            result = pets_collection.insert_one(new_pet)
            new_pet['_id'] = result.inserted_id
            new_pet = assign_daily_quests(new_pet)
            new_pet = assign_achievements(new_pet)
            pets_collection.update_one({"_id": new_pet["_id"]}, {"$set": new_pet})

            embed = discord.Embed(
                title=f"Pet `{name}` Summoned!",
                description="Your new pet has been summoned successfully in this server.",
                color=random_color
            )
            embed.set_thumbnail(url=new_pet['icon'])
            embed.add_field(name="Level", value=new_pet['level'])
            embed.add_field(name="Strength", value=new_pet['strength'])
            embed.add_field(name="Defense", value=new_pet['defense'])
            embed.add_field(name="Health", value=new_pet['health'], inline=False)
            embed.add_field(
                name="Support Us ❤️",
                value=(
                    "[If you enjoy using this bot, consider supporting us!]"
                    "(https://buymeacoffee.com/danblock97)"
                )
            )
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Error in summon command: {e}")
            embed = discord.Embed(
                title="Error",
                description="An error occurred while summoning your pet. Please try again later.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)

    # ------------------------------------------------------
    # /petbattles stats
    # ------------------------------------------------------
    @app_commands.command(name="stats", description="View your pet's stats")
    async def stats(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild.id)
        try:
            pet = pets_collection.find_one({"user_id": user_id, "guild_id": guild_id})

            if not pet:
                embed = discord.Embed(
                    title="No Pet Found",
                    description=(
                        f"{interaction.user.mention}, you don't have a pet in this server. "
                        "Summon one with `/petbattles summon`!"
                    ),
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed)
                return

            xp_needed = calculate_xp_needed(pet['level'])
            xp_bar = create_xp_bar(pet['xp'], xp_needed)

            embed = discord.Embed(
                title=f"{interaction.user.display_name}'s Pet",
                color=pet['color']
            )
            embed.set_thumbnail(url=pet['icon'])
            embed.add_field(name="Name", value=pet['name'])
            embed.add_field(name="Level", value=pet['level'])
            embed.add_field(name="XP", value=f"{pet['xp']} / {xp_needed}\n{xp_bar}")
            embed.add_field(name="Strength", value=pet['strength'])
            embed.add_field(name="Defense", value=pet['defense'])
            embed.add_field(name="Health", value=pet['health'])

            if pet.get('killstreak', 0) > 0:
                embed.set_footer(text=f"Killstreak: {pet['killstreak']}")
            elif pet.get('loss_streak', 0) > 0:
                embed.set_footer(text=f"Loss Streak: {pet['loss_streak']}")

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Error in stats command: {e}")
            embed = discord.Embed(
                title="Error",
                description="An error occurred while fetching your pet's stats. Please try again later.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)

    # ------------------------------------------------------
    # /petbattles battle
    # ------------------------------------------------------
    @app_commands.command(name="battle", description="Engage in a pet battle")
    @app_commands.describe(opponent="Choose a member to battle their pet")
    async def battle(self, interaction: discord.Interaction, opponent: discord.Member):
        user_id = str(interaction.user.id)
        opponent_id = str(opponent.id)
        guild_id = str(interaction.guild.id)

        try:
            if user_id == opponent_id:
                embed = discord.Embed(
                    title="Battle Error",
                    description="You cannot battle yourself. Please choose another member.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed)
                return

            if opponent == self.bot.user:
                embed = discord.Embed(
                    title="Battle Error",
                    description="You cannot battle the bot. Please choose another member with a pet.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed)
                return

            user_pet = pets_collection.find_one({"user_id": user_id, "guild_id": guild_id})
            opponent_pet = pets_collection.find_one({"user_id": opponent_id, "guild_id": guild_id})

            if not user_pet:
                embed = discord.Embed(
                    title="No Pet Found",
                    description=(
                        f"{interaction.user.mention}, you don't have a pet in this server. "
                        "Summon one with `/petbattles summon`!"
                    ),
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed)
                return

            if not opponent_pet:
                embed = discord.Embed(
                    title="Opponent Has No Pet",
                    description=f"{opponent.mention} doesn't have a pet in this server. They need to summon one first.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed)
                return

            user_pet = ensure_quests_and_achievements(user_pet)
            opponent_pet = ensure_quests_and_achievements(opponent_pet)

            if (opponent_pet['level'] > user_pet['level'] + 1
                    or opponent_pet['level'] < user_pet['level'] - 1):
                embed = discord.Embed(
                    title="Battle Error",
                    description=(
                        "You can only battle someone with a pet that is at most one level above or below yours."
                    ),
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed)
                return

            now = datetime.now(timezone.utc)
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            recent_battles = battle_logs_collection.count_documents({
                "user_id": user_id,
                "opponent_id": opponent_id,
                "guild_id": guild_id,
                "timestamp": {"$gte": start_of_day}
            })

            if recent_battles >= 5:
                embed = discord.Embed(
                    title="Battle Limit Reached",
                    description=(
                        f"You have already battled {opponent.display_name} 5 times today in this server. "
                        "Please try again tomorrow."
                    ),
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed)
                return

            battle_logs_collection.insert_one({
                "user_id": user_id,
                "opponent_id": opponent_id,
                "guild_id": guild_id,
                "timestamp": now
            })

            battle_intro_embed = discord.Embed(
                title="Battle Begins!",
                description=(
                    f"{interaction.user.display_name}'s pet **{user_pet['name']}** vs "
                    f"{opponent.display_name}'s pet **{opponent_pet['name']}**"
                ),
                color=discord.Color.blue()
            )
            battle_intro_embed.set_thumbnail(url=user_pet['icon'])
            battle_intro_embed.set_image(url=opponent_pet['icon'])
            await interaction.response.send_message(embed=battle_intro_embed)
            await asyncio.sleep(2)

            user_health = user_pet['health']
            opponent_health = opponent_pet['health']

            user_battle_stats = {
                "damage_dealt": 0,
                "critical_hits": 0,
                "lucky_hits": 0,
                "battles_won": 0,
                "battles_lost": 0,
                "xp_earned": 0,
                "killstreak": user_pet.get('killstreak', 0)
            }
            opponent_battle_stats = {
                "damage_dealt": 0,
                "critical_hits": 0,
                "lucky_hits": 0,
                "battles_won": 0,
                "battles_lost": 0,
                "xp_earned": 0,
                "killstreak": opponent_pet.get('killstreak', 0)
            }

            battle_embed = discord.Embed(
                title="Battle in Progress...",
                description=(
                    f"{interaction.user.display_name}'s pet vs {opponent.display_name}'s pet"
                ),
                color=discord.Color.orange()
            )
            battle_embed.set_thumbnail(url=user_pet['icon'])
            battle_embed.set_image(url=opponent_pet['icon'])
            message = await interaction.followup.send(embed=battle_embed)

            def calculate_damage(attacker: dict, defender: dict):
                attack_multiplier = random.randint(8, 15) / 10
                defense_multiplier = random.randint(8, 15) / 10
                base_damage = int(
                    (attacker['strength'] * attack_multiplier)
                    * (random.randint(5, 15) / 10)
                    - (defender['defense'] * defense_multiplier)
                    * (random.randint(3, 10) / 10)
                )
                base_damage = max(5, base_damage)
                crit_chance = 15 + (10 if attacker['level'] < defender['level'] else 0)
                critical_hit = random.randint(1, 100) <= crit_chance
                if critical_hit:
                    crit_multiplier = random.randint(15, 30) / 10
                    base_damage = int(base_damage * crit_multiplier)

                if random.randint(1, 10) == 1:  # 10% chance
                    luck_damage = random.randint(15, 50)
                    base_damage += luck_damage
                    return base_damage, critical_hit, "luck"

                return base_damage, critical_hit, "normal"

            round_number = 1
            battle_result = ""
            while user_health > 0 and opponent_health > 0:
                round_log = f"**Round {round_number}**\n"
                user_damage, user_crit, user_event = calculate_damage(user_pet, opponent_pet)
                opponent_health -= user_damage
                user_battle_stats['damage_dealt'] += user_damage

                if user_event == "luck":
                    user_battle_stats['lucky_hits'] += 1
                    round_log += (
                        f"{interaction.user.display_name}'s pet lands a **lucky hit** "
                        f"for {user_damage} damage!\n"
                    )
                elif user_crit:
                    user_battle_stats['critical_hits'] += 1
                    round_log += (
                        f"{interaction.user.display_name}'s pet lands a **critical hit** "
                        f"for {user_damage} damage!\n"
                    )
                else:
                    round_log += (
                        f"{interaction.user.display_name}'s pet attacks for {user_damage} damage.\n"
                    )

                if opponent_health <= 0:
                    round_log += f"{opponent.display_name}'s pet has been defeated!\n"
                    battle_result = f"{interaction.user.display_name}'s pet wins the battle!"
                    user_xp_gain = random.randint(50, 100)
                    opponent_xp_gain = random.randint(20, 50)
                    user_pet['xp'] += user_xp_gain
                    opponent_pet['xp'] += opponent_xp_gain
                    user_battle_stats['xp_earned'] += user_xp_gain
                    opponent_battle_stats['xp_earned'] += opponent_xp_gain
                    user_battle_stats['battles_won'] += 1
                    opponent_battle_stats['battles_lost'] += 1
                    battle_embed.description = round_log
                    await message.edit(embed=battle_embed)
                    break

                opponent_damage, opponent_crit, opponent_event = calculate_damage(opponent_pet, user_pet)
                user_health -= opponent_damage
                opponent_battle_stats['damage_dealt'] += opponent_damage

                if opponent_event == "luck":
                    opponent_battle_stats['lucky_hits'] += 1
                    round_log += (
                        f"{opponent.display_name}'s pet lands a **lucky hit** "
                        f"for {opponent_damage} damage!\n"
                    )
                elif opponent_crit:
                    opponent_battle_stats['critical_hits'] += 1
                    round_log += (
                        f"{opponent.display_name}'s pet lands a **critical hit** "
                        f"for {opponent_damage} damage!\n"
                    )
                else:
                    round_log += (
                        f"{opponent.display_name}'s pet attacks for {opponent_damage} damage.\n"
                    )

                if user_health <= 0:
                    round_log += f"{interaction.user.display_name}'s pet has been defeated!\n"
                    battle_result = f"{opponent.display_name}'s pet wins the battle!"
                    opponent_xp_gain = random.randint(50, 100)
                    user_xp_gain = random.randint(10, 30)
                    opponent_pet['xp'] += opponent_xp_gain
                    user_pet['xp'] += user_xp_gain
                    user_battle_stats['xp_earned'] += user_xp_gain
                    opponent_battle_stats['xp_earned'] += opponent_xp_gain
                    opponent_battle_stats['battles_won'] += 1
                    user_battle_stats['battles_lost'] += 1
                    battle_embed.description = round_log
                    await message.edit(embed=battle_embed)
                    break

                round_log += (
                    f"\n{interaction.user.display_name}'s pet health: {user_health}\n"
                    f"{opponent.display_name}'s pet health: {opponent_health}\n"
                )
                battle_embed.description = round_log
                await message.edit(embed=battle_embed)
                await asyncio.sleep(2)
                round_number += 1

            # Update killstreaks and loss streaks
            if user_health > 0:
                user_pet['killstreak'] = user_pet.get('killstreak', 0) + 1
                user_pet['loss_streak'] = 0
                opponent_pet['killstreak'] = 0
                opponent_pet['loss_streak'] = opponent_pet.get('loss_streak', 0) + 1
            else:
                opponent_pet['killstreak'] = opponent_pet.get('killstreak', 0) + 1
                opponent_pet['loss_streak'] = 0
                user_pet['killstreak'] = 0
                user_pet['loss_streak'] = user_pet.get('loss_streak', 0) + 1

            user_battle_stats['killstreak'] = user_pet.get('killstreak', 0)
            opponent_battle_stats['killstreak'] = opponent_pet.get('killstreak', 0)

            completed_quests_user, completed_achievements_user = update_quests_and_achievements(
                user_pet, user_battle_stats
            )
            completed_quests_opponent, completed_achievements_opponent = update_quests_and_achievements(
                opponent_pet, opponent_battle_stats
            )

            user_pet, user_leveled_up = check_level_up(user_pet)
            opponent_pet, opponent_leveled_up = check_level_up(opponent_pet)

            pets_collection.update_one({"_id": user_pet["_id"]}, {"$set": user_pet})
            pets_collection.update_one({"_id": opponent_pet["_id"]}, {"$set": opponent_pet})

            battle_embed.title = "Battle Concluded"
            battle_embed.description = (
                f"{battle_result}\n\n"
                f"**{interaction.user.display_name}'s pet {user_pet['name']}** gained "
                f"**{user_battle_stats['xp_earned']} XP**\n"
                f"**{opponent.display_name}'s pet {opponent_pet['name']}** gained "
                f"**{opponent_battle_stats['xp_earned']} XP**\n"
            )

            if completed_quests_user or completed_achievements_user:
                completion_message = ""
                for quest in completed_quests_user:
                    completion_message += (
                        f"📝 **Quest Completed**: {quest['description']} "
                        f"(+{quest['xp_reward']} XP)\n"
                    )
                for achievement in completed_achievements_user:
                    completion_message += (
                        f"🏆 **Achievement Unlocked**: {achievement['description']} "
                        f"(+{achievement['xp_reward']} XP)\n"
                    )
                battle_embed.description += f"\n{completion_message}"

            if user_leveled_up or opponent_leveled_up:
                level_up_message = ""
                if user_leveled_up:
                    level_up_message += (
                        f"{interaction.user.display_name}'s pet leveled up to "
                        f"**Level {user_pet['level']}**!\n"
                    )
                if opponent_leveled_up:
                    level_up_message += (
                        f"{opponent.display_name}'s pet leveled up to "
                        f"**Level {opponent_pet['level']}**!\n"
                    )
                battle_embed.description += f"\n{level_up_message}"

            if user_health > 0:
                battle_embed.set_thumbnail(url=user_pet['icon'])
            else:
                battle_embed.set_thumbnail(url=opponent_pet['icon'])

            # ------------------------------------------------------
            # Create the Promotional Embed
            # ------------------------------------------------------
            promo_embed = discord.Embed(
                description="⭐ **New:** Squib Games Has Arrived to AstroStats! Check out `/help` for more information!",
                color=discord.Color.blue(),  # Customize the color as desired
                timestamp=datetime.now(timezone.utc)
            )
            promo_embed.set_footer(text="Built By Goldiez ❤️ Support: https://astrostats.vercel.app")

            # ------------------------------------------------------
            # Send Both Embeds Together
            # ------------------------------------------------------
            await message.edit(embed=battle_embed, embeds=[promo_embed])

        except Exception as e:
            logger.error(f"Error in battle command: {e}")
            embed = discord.Embed(
                title="Battle Error",
                description="An error occurred during the battle. Please try again later.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)

    # ------------------------------------------------------
    # /petbattles quests
    # ------------------------------------------------------
    @app_commands.command(name="quests", description="View your current daily quests")
    async def quests(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild.id)
        try:
            pet = pets_collection.find_one({"user_id": user_id, "guild_id": guild_id})

            if not pet:
                embed = discord.Embed(
                    title="No Pet Found",
                    description=(
                        f"{interaction.user.mention}, you don't have a pet in this server. "
                        "Summon one with `/petbattles summon`!"
                    ),
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed)
                return

            pet = ensure_quests_and_achievements(pet)
            incomplete_quests = [q for q in pet['daily_quests'] if not q['completed']]

            if not incomplete_quests:
                now = datetime.now(timezone.utc)
                next_reset = datetime.combine(now.date(), dtime(hour=0, minute=0, tzinfo=timezone.utc)) + timedelta(days=1)
                time_until_reset = next_reset - now
                hours, remainder = divmod(int(time_until_reset.total_seconds()), 3600)
                minutes, _ = divmod(remainder, 60)
                time_str = f"{hours}h {minutes}m"
                embed = discord.Embed(
                    title="All Daily Quests Completed!",
                    description=f"Your daily quests are complete.\nNew quests will be available in {time_str}.",
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=embed)
                return

            embed = discord.Embed(title="Your Daily Quests", color=discord.Color.blue())
            for quest in incomplete_quests:
                progress_bar = create_xp_bar(quest['progress'], quest['progress_required'])
                embed.add_field(
                    name=quest['description'],
                    value=f"{quest['progress']} / {quest['progress_required']}\n{progress_bar}",
                    inline=False
                )
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Error in quests command: {e}")
            embed = discord.Embed(
                title="Error",
                description="An error occurred while fetching your quests. Please try again later.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)

    # ------------------------------------------------------
    # /petbattles achievements
    # ------------------------------------------------------
    @app_commands.command(name="achievements", description="View your achievements")
    async def achievements(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild.id)
        try:
            pet = pets_collection.find_one({"user_id": user_id, "guild_id": guild_id})

            if not pet:
                embed = discord.Embed(
                    title="No Pet Found",
                    description=(
                        f"{interaction.user.mention}, you don't have a pet in this server. "
                        "Summon one with `/petbattles summon`!"
                    ),
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed)
                return

            pet = ensure_quests_and_achievements(pet)
            achievements_list = pet['achievements']
            embed = discord.Embed(title="Your Achievements", color=discord.Color.gold())

            for achievement in achievements_list:
                status = "✅ Completed" if achievement['completed'] else (
                    f"{achievement['progress']} / {achievement['progress_required']}"
                )
                progress_bar = create_xp_bar(achievement['progress'], achievement['progress_required'])
                embed.add_field(
                    name=achievement['description'],
                    value=f"{status}\n{progress_bar}",
                    inline=False
                )
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Error in achievements command: {e}")
            embed = discord.Embed(
                title="Error",
                description="An error occurred while fetching your achievements. Please try again later.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)

    # ------------------------------------------------------
    # /petbattles leaderboard
    # ------------------------------------------------------
    @app_commands.command(name="leaderboard", description="View the top pets leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        try:
            top_data = pets_collection.find({"guild_id": guild_id}).sort(
                [("level", -1), ("xp", -1)]
            ).limit(10)

            embed = discord.Embed(title="Top Pets Leaderboard", color=0xFFD700)
            for index, pet in enumerate(top_data, 1):
                user = await self.bot.fetch_user(int(pet['user_id']))
                embed.add_field(
                    name=f"#{index}: {user.display_name}",
                    value=f"Level: {pet['level']}, XP: {pet['xp']}",
                    inline=False
                )
                embed.set_thumbnail(url=pet['icon'])

            embed.add_field(
                name="Support Us ❤️",
                value="[If you enjoy using this bot, consider supporting us!](https://buymeacoffee.com/danblock97)"
            )
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Error in leaderboard command: {e}")
            embed = discord.Embed(
                title="Error",
                description="An error occurred while fetching the leaderboard. Please try again later.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)

    # ------------------------------------------------------
    # /petbattles vote
    # ------------------------------------------------------
    @app_commands.command(name="vote", description="Vote for the bot and earn rewards")
    async def vote(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild.id)
        bot_id = "1088929834748616785"

        try:
            pet = pets_collection.find_one({"user_id": user_id, "guild_id": guild_id})

            if not pet:
                embed = discord.Embed(
                    title="No Pet Found",
                    description=(
                        f"{interaction.user.mention}, you don't have a pet in this server. "
                        "Summon one with `/petbattles summon`!"
                    ),
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed)
                return

            if not self.topgg_client:
                await interaction.response.send_message("Voting functionality is not available.")
                return

            now = datetime.now(timezone.utc)
            try:
                has_voted = await self.topgg_client.get_user_vote(int(user_id))
            except Exception as e:
                logger.error(f"Error checking vote status: {e}")
                await interaction.response.send_message("Error checking vote status.")
                return

            if not has_voted:
                vote_url = f"https://top.gg/bot/{bot_id}/vote"
                embed = discord.Embed(
                    title="Vote for the Bot",
                    description=(
                        "To earn rewards, please vote for the bot on Top.gg.\n"
                        f"Click [here]({vote_url}) to vote."
                    ),
                    color=discord.Color.blue()
                )
                await interaction.response.send_message(embed=embed)
            else:
                last_vote_reward_time = pet.get('last_vote_reward_time')
                if last_vote_reward_time:
                    last_vote_reward_time = datetime.fromisoformat(last_vote_reward_time)
                    time_since_last_reward = now - last_vote_reward_time
                    if time_since_last_reward < timedelta(hours=12):
                        time_left = timedelta(hours=12) - time_since_last_reward
                        hours, remainder = divmod(int(time_left.total_seconds()), 3600)
                        minutes, _ = divmod(remainder, 60)
                        time_str = f"{hours}h {minutes}m"
                        embed = discord.Embed(
                            title="Vote Cooldown",
                            description=f"You can vote again in {time_str}.",
                            color=discord.Color.red()
                        )
                        await interaction.response.send_message(embed=embed)
                        return

                xp_reward = 100
                pet['xp'] += xp_reward
                pet['last_vote_reward_time'] = now.isoformat()
                pet, leveled_up = check_level_up(pet)
                pets_collection.update_one({"_id": pet["_id"]}, {"$set": pet})

                embed = discord.Embed(
                    title="Thank You for Voting!",
                    description=f"You have received {xp_reward} XP for your pet.",
                    color=discord.Color.green()
                )
                if leveled_up:
                    embed.add_field(
                        name="Level Up!",
                        value=f"Your pet is now level {pet['level']}!"
                    )
                await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"Error in vote command: {e}")
            embed = discord.Embed(
                title="Error",
                description="An error occurred while processing your vote. Please try again later.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)

    # ------------------------------------------------------
    # GroupCog Lifecycle Events
    # ------------------------------------------------------
    async def cog_load(self):
        logger.error("PetBattles Cog loaded.")

    async def cog_unload(self):
        self.reset_daily_quests.cancel()
        if self.topgg_client:
            await self.topgg_client.close()

# ------------------------------------------------------
# Setup Function
# ------------------------------------------------------
async def setup(bot: commands.Bot):
    await bot.add_cog(PetBattles(bot))
