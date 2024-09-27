import discord
import os
import random
import asyncio
from discord.ext import commands, tasks
from discord import app_commands
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone, time
import topgg  # Added for top.gg API integration

# MongoDB setup
mongo_client = MongoClient(os.getenv('MONGODB_URI'))
db = mongo_client['pet_database']
pets_collection = db['pets']
battle_logs_collection = db['battle_logs']  # Collection to store battle logs

# Import DAILY_QUESTS and ACHIEVEMENTS from quests_and_achievements.py
from quests_and_achievements import DAILY_QUESTS, ACHIEVEMENTS

# Initial stats for all new pets
INITIAL_STATS = {
    "level": 1,
    "xp": 0,
    "strength": 10,
    "defense": 10,
    "health": 100  # Added health for more diversity in stats
}

# Stat increases per level
LEVEL_UP_INCREASES = {
    "strength": 5,
    "defense": 5,
    "health": 20  # Increase health as well
}

# Dictionary mapping pet types to their corresponding GitHub raw image URLs
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

# Example color list
COLOR_LIST = {
    "red": 0xFF0000,
    "green": 0x00FF00,
    "blue": 0x0000FF,
    "yellow": 0xFFFF00,
    "purple": 0x800080
}

# Calculate XP needed to level up
def calculate_xp_needed(level):
    return level ** 2 * 100

def check_level_up(pet):
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

# Create XP bar for visualization
def create_xp_bar(current, total):
    total_blocks = 10
    filled_blocks = int((current / total) * total_blocks)
    bar = "█" * filled_blocks + "░" * (total_blocks - filled_blocks)
    return bar

# Assign daily quests to a pet
def assign_daily_quests(pet):
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
    if pet['_id'] is not None:
        pets_collection.update_one({"_id": pet["_id"]}, {"$set": {"daily_quests": pet_daily_quests}})
    return pet

# Assign achievements to a pet
def assign_achievements(pet):
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
    if pet['_id'] is not None:
        pets_collection.update_one({"_id": pet["_id"]}, {"$set": {"achievements": pet_achievements}})
    return pet

# Ensure a pet has quests and achievements
def ensure_quests_and_achievements(pet):
    if 'daily_quests' not in pet or not pet['daily_quests']:
        pet = assign_daily_quests(pet)
    if 'achievements' not in pet or not pet['achievements']:
        pet = assign_achievements(pet)
    return pet

# Update quests and achievements progress
def update_quests_and_achievements(pet, battle_stats):
    completed_quests = []
    completed_achievements = []
    # Update daily quests
    for quest in pet['daily_quests']:
        if quest['completed']:
            continue
        if "Win " in quest['description']:
            quest['progress'] += battle_stats['battles_won']
        elif "battle win streak" in quest['description']:
            if pet.get('killstreak', 0) >= quest['progress_required']:
                quest['progress'] = quest['progress_required']
        elif "battle killstreak" in quest['description']:
            if pet.get('killstreak', 0) >= quest['progress_required']:
                quest['progress'] = quest['progress_required']
        elif "Inflict" in quest['description'] and "critical hits" in quest['description']:
            quest['progress'] += battle_stats['critical_hits']
        elif "Land" in quest['description'] and "lucky hits" in quest['description']:
            quest['progress'] += battle_stats['lucky_hits']
        elif "Lose" in quest['description']:
            quest['progress'] += battle_stats['battles_lost']
        elif "Earn" in quest['description'] and "XP from battles" in quest['description']:
            quest['progress'] += battle_stats['xp_earned']
        elif "Participate in" in quest['description'] and "battles" in quest['description']:
            quest['progress'] += 1  # Participated in one battle
        elif "Deal" in quest['description'] and "damage in total" in quest['description']:
            quest['progress'] += battle_stats['damage_dealt']

        # Check if quest is completed
        if quest['progress'] >= quest['progress_required']:
            quest['progress'] = quest['progress_required']
            quest['completed'] = True
            pet['xp'] += quest['xp_reward']
            completed_quests.append(quest)

    # Update achievements
    for achievement in pet['achievements']:
        if achievement['completed']:
            continue
        if "Win " in achievement['description']:
            achievement['progress'] += battle_stats['battles_won']
        elif "battle killstreak" in achievement['description']:
            if pet.get('killstreak', 0) >= achievement['progress_required']:
                achievement['progress'] = achievement['progress_required']
        elif "Deal" in achievement['description'] and "total damage" in achievement['description']:
            achievement['progress'] += battle_stats['damage_dealt']
        elif "Land" in achievement['description'] and "critical hits" in achievement['description']:
            achievement['progress'] += battle_stats['critical_hits']
        elif "Land" in achievement['description'] and "lucky hits" in achievement['description']:
            achievement['progress'] += battle_stats['lucky_hits']

        # Check if achievement is completed
        if achievement['progress'] >= achievement['progress_required']:
            achievement['progress'] = achievement['progress_required']
            achievement['completed'] = True
            pet['xp'] += achievement['xp_reward']
            completed_achievements.append(achievement)

    return completed_quests, completed_achievements

# Global variables
client = None  # Will be set in setup()
topgg_client = None  # Will be initialized in setup()

# Summon a new pet with initial stats
@app_commands.command(name="summon_pet", description="Summon a new pet")
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
async def summon_pet(interaction: discord.Interaction, name: str, pet: app_commands.Choice[str]):
    user_id = str(interaction.user.id)
    guild_id = str(interaction.guild.id)

    # Check if the user already has a pet in this server
    if pets_collection.find_one({"user_id": user_id, "guild_id": guild_id}):
        embed = discord.Embed(
            title="Pet Summon Failed",
            description=f"{interaction.user.mention}, you already have a pet in this server!",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
        return

    # Assign a random color
    random_color = random.choice(list(COLOR_LIST.values()))

    # Create a new pet dictionary
    new_pet = {
        "user_id": user_id,
        "guild_id": guild_id,  # Include guild ID to ensure one pet per server
        "name": name,
        "icon": PET_LIST[pet.value],
        "color": random_color,
        **INITIAL_STATS,  # Add initial stats to the pet
        "killstreak": 0,  # Initial killstreak value
        "loss_streak": 0,  # Initial loss streak value
        "daily_quests": [],
        "achievements": [],
        "last_vote_reward_time": None  # Initialize vote reward time
    }

    # Insert the new pet into the database and get the _id
    result = pets_collection.insert_one(new_pet)
    new_pet['_id'] = result.inserted_id

    # Assign daily quests and achievements to the new pet
    new_pet = assign_daily_quests(new_pet)
    new_pet = assign_achievements(new_pet)

    # Update the pet with quests and achievements
    pets_collection.update_one({"_id": new_pet["_id"]}, {"$set": new_pet})

    embed = discord.Embed(
        title=f"Pet `{name}` Summoned!",
        description=f"Your new pet has been summoned successfully in this server.",
        color=random_color
    )
    embed.set_thumbnail(url=new_pet['icon'])
    embed.add_field(name="Level", value=new_pet['level'])
    embed.add_field(name="Strength", value=new_pet['strength'])
    embed.add_field(name="Defense", value=new_pet['defense'])
    embed.add_field(name="Health", value=new_pet['health'])

    await interaction.response.send_message(embed=embed)

# View pet stats
@app_commands.command(name="pet_stats", description="View your pet's stats")
async def pet_stats(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    guild_id = str(interaction.guild.id)

    # Fetch the pet for the user in this server
    pet = pets_collection.find_one({"user_id": user_id, "guild_id": guild_id})

    if not pet:
        embed = discord.Embed(
            title="No Pet Found",
            description=f"{interaction.user.mention}, you don't have a pet in this server. Summon one with `/summon_pet`!",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
        return

    xp_needed = calculate_xp_needed(pet['level'])
    xp_bar = create_xp_bar(pet['xp'], xp_needed)

    embed = discord.Embed(title=f"{interaction.user.display_name}'s Pet", color=pet['color'])
    embed.set_thumbnail(url=pet['icon'])
    embed.add_field(name="Name", value=pet['name'])
    embed.add_field(name="Level", value=pet['level'])
    embed.add_field(name="XP", value=f"{pet['xp']} / {xp_needed}\n{xp_bar}")
    embed.add_field(name="Strength", value=pet['strength'])
    embed.add_field(name="Defense", value=pet['defense'])
    embed.add_field(name="Health", value=pet['health'])

    # Display either killstreak or loss streak in the footer
    if pet.get('killstreak', 0) > 0:
        embed.set_footer(text=f"Killstreak: {pet['killstreak']}")
    elif pet.get('loss_streak', 0) > 0:
        embed.set_footer(text=f"Loss Streak: {pet['loss_streak']}")

    await interaction.response.send_message(embed=embed)

# Engage in a pet battle
@app_commands.command(name="pet_battle", description="Engage in a pet battle")
async def pet_battle(interaction: discord.Interaction, opponent: discord.Member):
    user_id = str(interaction.user.id)
    opponent_id = str(opponent.id)
    guild_id = str(interaction.guild.id)

    # Prevent self-battles
    if user_id == opponent_id:
        embed = discord.Embed(
            title="Battle Error",
            description="You cannot battle yourself. Please choose another member.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
        return

    # Ensure the bot isn't the selected opponent
    if opponent == client.user:
        embed = discord.Embed(
            title="Battle Error",
            description="You cannot battle the bot. Please choose another member with a pet.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
        return

    # Fetch the user's pet and the opponent's pet from the database for this server
    user_pet = pets_collection.find_one({"user_id": user_id, "guild_id": guild_id})
    opponent_pet = pets_collection.find_one({"user_id": opponent_id, "guild_id": guild_id})

    # Check if both participants have pets
    if not user_pet:
        embed = discord.Embed(
            title="No Pet Found",
            description=f"{interaction.user.mention}, you don't have a pet in this server. Summon one with `/summon_pet`!",
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

    # Ensure both pets have quests and achievements
    user_pet = ensure_quests_and_achievements(user_pet)
    opponent_pet = ensure_quests_and_achievements(opponent_pet)

    # Check level restrictions
    if opponent_pet['level'] > user_pet['level'] + 1 or opponent_pet['level'] < user_pet['level'] - 1:
        embed = discord.Embed(
            title="Battle Error",
            description=f"You can only battle someone with a pet that is higher level, the same level, or one level below yours.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
        return

    # Check if they have battled more than 5 times in the current UTC day
    now = datetime.now(timezone.utc)

    # Calculate the start of the current day in UTC
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
            description=f"You have already battled {opponent.display_name} 5 times today in this server. Please try again tomorrow.",
            color=0xFF0000  # Red color to indicate an error or warning
        )
        await interaction.response.send_message(embed=embed)
        return

    # Log this battle
    battle_logs_collection.insert_one({
        "user_id": user_id,
        "opponent_id": opponent_id,
        "guild_id": guild_id,
        "timestamp": now
    })

    # Create an initial embed to show who is battling
    battle_intro_embed = discord.Embed(
        title="Battle Begins!",
        description=f"{interaction.user.display_name}'s pet **{user_pet['name']}** vs {opponent.display_name}'s pet **{opponent_pet['name']}**",
        color=discord.Color.blue()
    )
    battle_intro_embed.set_thumbnail(url=user_pet['icon'])
    battle_intro_embed.set_image(url=opponent_pet['icon'])

    await interaction.response.send_message(embed=battle_intro_embed)

    # Introduce a short delay to build anticipation
    await asyncio.sleep(2)  # 2 seconds delay before starting the battle

    # Initialize health for both pets
    user_health = user_pet['health']
    opponent_health = opponent_pet['health']

    # Initialize battle stats for quests and achievements
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

    # Send an initial battle log message that will be updated
    battle_embed = discord.Embed(
        title="Battle in Progress...",
        description=f"{interaction.user.display_name}'s pet vs {opponent.display_name}'s pet",
        color=discord.Color.orange()
    )
    battle_embed.set_thumbnail(url=user_pet['icon'])
    battle_embed.set_image(url=opponent_pet['icon'])

    # Send the initial battle embed message and save the message object for editing later
    message = await interaction.followup.send(embed=battle_embed)

    # Function to calculate damage with enhanced randomness and integer results
    def calculate_damage(attacker, defender):
        # Apply random buffs/debuffs as integers
        attack_multiplier = random.randint(8, 15) / 10  # Random buff/debuff to attack between 0.8 and 1.5
        defense_multiplier = random.randint(8, 15) / 10  # Random buff/debuff to defense between 0.8 and 1.5

        # Base damage calculation with expanded randomness, rounded to nearest integer
        base_damage = int((attacker['strength'] * attack_multiplier) * random.randint(5, 15) / 10 - (defender['defense'] * defense_multiplier) * random.randint(3, 10) / 10)
        base_damage = max(5, base_damage)  # Ensure a minimum damage floor

        # Random chance for a critical hit with varying multipliers
        crit_chance = 15 + (10 if attacker['level'] < defender['level'] else 0)  # Critical hit chance as percentage
        critical_hit = random.randint(1, 100) <= crit_chance
        if critical_hit:
            crit_multiplier = random.randint(15, 30) / 10  # Random critical hit multiplier between 1.5x and 3.0x
            base_damage = int(base_damage * crit_multiplier)

        # Small chance for a random luck damage, added as an integer
        if random.randint(1, 10) == 1:  # 10% chance for a lucky hit
            luck_damage = random.randint(15, 50)  # Random flat damage
            base_damage += luck_damage
            return base_damage, True, "luck"

        return base_damage, critical_hit, "normal"

    round_number = 1
    while user_health > 0 and opponent_health > 0:
        round_log = f"**Round {round_number}**\n"

        # User's turn to attack
        user_damage, user_crit, user_event = calculate_damage(user_pet, opponent_pet)
        opponent_health -= user_damage
        user_battle_stats['damage_dealt'] += user_damage

        if user_event == "luck":
            user_battle_stats['lucky_hits'] += 1
            round_log += f"{interaction.user.display_name}'s pet lands a **lucky hit** for {user_damage} damage!\n"
        elif user_crit:
            user_battle_stats['critical_hits'] += 1
            round_log += f"{interaction.user.display_name}'s pet lands a **critical hit** for {user_damage} damage!\n"
        else:
            round_log += f"{interaction.user.display_name}'s pet attacks for {user_damage} damage.\n"

        if opponent_health <= 0:
            round_log += f"{opponent.display_name}'s pet has been defeated!\n"
            battle_result = f"{interaction.user.display_name}'s pet wins the battle!"
            user_xp_gain = random.randint(50, 100)  # Winner gets a random XP between 50 and 100
            opponent_xp_gain = random.randint(20, 50)  # Loser gets a random XP between 20 and 50
            user_pet['xp'] += user_xp_gain
            opponent_pet['xp'] += opponent_xp_gain
            user_battle_stats['xp_earned'] += user_xp_gain
            opponent_battle_stats['xp_earned'] += opponent_xp_gain
            user_battle_stats['battles_won'] += 1
            opponent_battle_stats['battles_lost'] += 1
            # Update the embed with the final round log
            battle_embed.description = round_log
            await message.edit(embed=battle_embed)
            break

        # Opponent's turn to attack
        opponent_damage, opponent_crit, opponent_event = calculate_damage(opponent_pet, user_pet)
        user_health -= opponent_damage
        opponent_battle_stats['damage_dealt'] += opponent_damage

        if opponent_event == "luck":
            opponent_battle_stats['lucky_hits'] += 1
            round_log += f"{opponent.display_name}'s pet lands a **lucky hit** for {opponent_damage} damage!\n"
        elif opponent_crit:
            opponent_battle_stats['critical_hits'] += 1
            round_log += f"{opponent.display_name}'s pet lands a **critical hit** for {opponent_damage} damage!\n"
        else:
            round_log += f"{opponent.display_name}'s pet attacks for {opponent_damage} damage.\n"

        if user_health <= 0:
            round_log += f"{interaction.user.display_name}'s pet has been defeated!\n"
            battle_result = f"{opponent.display_name}'s pet wins the battle!"
            opponent_xp_gain = random.randint(50, 100)  # Winner gets a random XP between 50 and 100
            user_xp_gain = random.randint(10, 30)  # Loser gets a random XP between 10 and 30
            opponent_pet['xp'] += opponent_xp_gain
            user_pet['xp'] += user_xp_gain
            user_battle_stats['xp_earned'] += user_xp_gain
            opponent_battle_stats['xp_earned'] += opponent_xp_gain
            opponent_battle_stats['battles_won'] += 1
            user_battle_stats['battles_lost'] += 1
            # Update the embed with the final round log
            battle_embed.description = round_log
            await message.edit(embed=battle_embed)
            break

        round_log += f"\n{interaction.user.display_name}'s pet health: {user_health}\n"
        round_log += f"{opponent.display_name}'s pet health: {opponent_health}\n"

        # Update the embed with the new round log and health statuses
        battle_embed.description = round_log
        await message.edit(embed=battle_embed)

        await asyncio.sleep(2)  # Add delay between rounds
        round_number += 1

    # Update killstreaks and loss streaks
    if user_health > 0:  # User won
        user_pet['killstreak'] = user_pet.get('killstreak', 0) + 1
        user_pet['loss_streak'] = 0  # Reset loss streak
        opponent_pet['killstreak'] = 0  # Reset opponent's killstreak
        opponent_pet['loss_streak'] = opponent_pet.get('loss_streak', 0) + 1
    else:  # Opponent won
        opponent_pet['killstreak'] = opponent_pet.get('killstreak', 0) + 1
        opponent_pet['loss_streak'] = 0  # Reset loss streak
        user_pet['killstreak'] = 0  # Reset user's killstreak
        user_pet['loss_streak'] = user_pet.get('loss_streak', 0) + 1

    # Update killstreak in battle stats
    user_battle_stats['killstreak'] = user_pet.get('killstreak', 0)
    opponent_battle_stats['killstreak'] = opponent_pet.get('killstreak', 0)

    # Update quests and achievements
    completed_quests_user, completed_achievements_user = update_quests_and_achievements(user_pet, user_battle_stats)
    completed_quests_opponent, completed_achievements_opponent = update_quests_and_achievements(opponent_pet, opponent_battle_stats)

    # Check if pets need to level up immediately after XP gain
    user_pet, user_leveled_up = check_level_up(user_pet)
    opponent_pet, opponent_leveled_up = check_level_up(opponent_pet)

    # Update the pets in the database after the potential level-ups and streak updates
    pets_collection.update_one({"_id": user_pet["_id"]}, {"$set": user_pet})
    pets_collection.update_one({"_id": opponent_pet["_id"]}, {"$set": opponent_pet})

    # Final update with the battle result, XP gain, and level-up details
    battle_embed.title = "Battle Concluded"
    battle_embed.description = (
        f"{battle_result}\n\n"
        f"**{interaction.user.display_name}'s pet {user_pet['name']}** gained **{user_battle_stats['xp_earned']} XP**\n"
        f"**{opponent.display_name}'s pet {opponent_pet['name']}** gained **{opponent_battle_stats['xp_earned']} XP**\n"
    )

    # Include quest and achievement completions
    if completed_quests_user or completed_achievements_user:
        completion_message = ""
        for quest in completed_quests_user:
            completion_message += f"📝 **Quest Completed**: {quest['description']} (+{quest['xp_reward']} XP)\n"
        for achievement in completed_achievements_user:
            completion_message += f"🏆 **Achievement Unlocked**: {achievement['description']} (+{achievement['xp_reward']} XP)\n"
        battle_embed.description += f"\n{completion_message}"

    if user_leveled_up or opponent_leveled_up:
        level_up_message = ""
        if user_leveled_up:
            level_up_message += f"{interaction.user.display_name}'s pet leveled up to **Level {user_pet['level']}**!\n"
        if opponent_leveled_up:
            level_up_message += f"{opponent.display_name}'s pet leveled up to **Level {opponent_pet['level']}**!\n"

        battle_embed.description += f"\n{level_up_message}"

    # Set the thumbnail to the winning pet's icon
    if user_health > 0:
        battle_embed.set_thumbnail(url=user_pet['icon'])
    else:
        battle_embed.set_thumbnail(url=opponent_pet['icon'])

    await message.edit(embed=battle_embed)

# Command to view current daily quests
@app_commands.command(name="quests", description="View your current daily quests")
async def quests(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    guild_id = str(interaction.guild.id)

    pet = pets_collection.find_one({"user_id": user_id, "guild_id": guild_id})
    if not pet:
        embed = discord.Embed(
            title="No Pet Found",
            description=f"{interaction.user.mention}, you don't have a pet in this server. Summon one with `/summon_pet`!",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
        return

    # Ensure the pet has quests and achievements
    pet = ensure_quests_and_achievements(pet)

    incomplete_quests = [q for q in pet['daily_quests'] if not q['completed']]
    if not incomplete_quests:
        now = datetime.now(timezone.utc)
        next_reset = datetime.combine(now.date(), time(hour=0, minute=0, tzinfo=timezone.utc)) + timedelta(days=1)
        time_until_reset = next_reset - now
        hours, remainder = divmod(int(time_until_reset.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        time_str = f"{hours}h {minutes}m"

        embed = discord.Embed(
            title="All Daily Quests Completed!",
            description=f"Your daily quests are complete.\nNew quests will be available in {time_str}.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
        return

    embed = discord.Embed(
        title="Your Daily Quests",
        color=discord.Color.blue()
    )
    for quest in incomplete_quests:
        progress_bar = create_xp_bar(quest['progress'], quest['progress_required'])
        embed.add_field(
            name=quest['description'],
            value=f"{quest['progress']} / {quest['progress_required']}\n{progress_bar}",
            inline=False
        )
    await interaction.response.send_message(embed=embed)

# Command to view achievements
@app_commands.command(name="achievements", description="View your achievements")
async def achievements(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    guild_id = str(interaction.guild.id)

    pet = pets_collection.find_one({"user_id": user_id, "guild_id": guild_id})
    if not pet:
        embed = discord.Embed(
            title="No Pet Found",
            description=f"{interaction.user.mention}, you don't have a pet in this server. Summon one with `/summon_pet`!",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
        return

    # Ensure the pet has achievements
    pet = ensure_quests_and_achievements(pet)

    achievements_list = pet['achievements']
    embed = discord.Embed(
        title="Your Achievements",
        color=discord.Color.gold()
    )
    for achievement in achievements_list:
        status = "✅ Completed" if achievement['completed'] else f"{achievement['progress']} / {achievement['progress_required']}"
        progress_bar = create_xp_bar(achievement['progress'], achievement['progress_required'])
        embed.add_field(
            name=achievement['description'],
            value=f"{status}\n{progress_bar}",
            inline=False
        )
    await interaction.response.send_message(embed=embed)

# Top pets leaderboard
@app_commands.command(name="top_pets", description="View the top pets leaderboard")
async def top_pets(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)

    # Sort first by level (descending) and then by XP (descending)
    top_pets = list(pets_collection.find({"guild_id": guild_id}).sort([("level", -1), ("xp", -1)]).limit(10))

    embed = discord.Embed(title="Top Pets Leaderboard", color=0xFFD700)
    for index, pet in enumerate(top_pets, 1):
        user = await client.fetch_user(int(pet['user_id']))
        embed.add_field(name=f"#{index}: {user.display_name}", value=f"Level: {pet['level']}, XP: {pet['xp']}", inline=False)
        embed.set_thumbnail(url=pet['icon'])

    await interaction.response.send_message(embed=embed)

# Function to reset daily quests at midnight UTC
@tasks.loop(time=time(hour=0, minute=0, tzinfo=timezone.utc))
async def reset_daily_quests():
    all_pets = pets_collection.find()
    for pet in all_pets:
        # Assign 3 new random daily quests
        pet = assign_daily_quests(pet)
    print("Daily quests have been reset.")

# Initialize the Top.gg client
async def initialize_topgg_client():
    global topgg_client
    topgg_token = os.getenv('TOPGG_TOKEN')
    if not topgg_token:
        print("Top.gg token is not configured. Voting functionality will not work.")
    else:
        topgg_client = topgg.DBLClient(client, topgg_token)

# New command to handle voting and rewarding XP
@app_commands.command(name="vote", description="Vote for the bot and earn rewards")
async def vote(interaction: discord.Interaction):
    global topgg_client
    if not topgg_client:
        await interaction.response.send_message("Voting functionality is not available.")
        return

    user_id = str(interaction.user.id)
    bot_id = "1088929834748616785"  # Replace with your bot's actual ID

    # Fetch the pet
    guild_id = str(interaction.guild.id)
    pet = pets_collection.find_one({"user_id": user_id, "guild_id": guild_id})
    if not pet:
        embed = discord.Embed(
            title="No Pet Found",
            description=f"{interaction.user.mention}, you don't have a pet in this server. Summon one with `/summon_pet`!",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
        return

    now = datetime.now(timezone.utc)

    # Check if the user has voted
    try:
        has_voted = await topgg_client.get_user_vote(int(user_id))
    except Exception as e:
        print(f"Error checking vote status: {e}")
        await interaction.response.send_message("Error checking vote status.")
        return

    if not has_voted:
        # User can vote
        vote_url = f"https://top.gg/bot/{bot_id}/vote"
        embed = discord.Embed(
            title="Vote for the Bot",
            description=f"To earn rewards, please vote for the bot on Top.gg.\nClick [here]({vote_url}) to vote.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)
    else:
        # User has voted within the last 12 hours
        # Check if they have claimed the reward
        last_vote_reward_time = pet.get('last_vote_reward_time')
        if last_vote_reward_time:
            last_vote_reward_time = datetime.fromisoformat(last_vote_reward_time)
            time_since_last_reward = now - last_vote_reward_time
            if time_since_last_reward < timedelta(hours=12):
                # They have already claimed the reward
                time_left = timedelta(hours=12) - time_since_last_reward
                hours, remainder = divmod(int(time_left.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                time_str = f"{hours}h {minutes}m"
                embed = discord.Embed(
                    title="Vote Cooldown",
                    description=f"You can vote again in {time_str}.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed)
                return
        # Grant XP
        xp_reward = 100  # Or any amount you prefer
        pet['xp'] += xp_reward
        pet['last_vote_reward_time'] = now.isoformat()
        # Check for level up
        pet, leveled_up = check_level_up(pet)
        # Update pet in database
        pets_collection.update_one({"_id": pet["_id"]}, {"$set": pet})
        # Send confirmation
        embed = discord.Embed(
            title="Thank You for Voting!",
            description=f"You have received {xp_reward} XP for your pet.",
            color=discord.Color.green()
        )
        if leveled_up:
            embed.add_field(name="Level Up!", value=f"Your pet is now level {pet['level']}!")
        await interaction.response.send_message(embed=embed)

# Register commands
async def setup(bot_client):
    global client
    client = bot_client
    client.tree.add_command(summon_pet)
    client.tree.add_command(pet_stats)
    client.tree.add_command(pet_battle)
    client.tree.add_command(quests)
    client.tree.add_command(achievements)
    client.tree.add_command(top_pets)
    client.tree.add_command(vote)  # Added the vote command
    reset_daily_quests.start()
    await initialize_topgg_client()  # Initialize top.gg client here
