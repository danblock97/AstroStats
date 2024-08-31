import discord
import os
import random
import asyncio
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient
from datetime import timedelta

# MongoDB setup
client = MongoClient(os.getenv('MONGODB_URI'))
db = client['pet_database']
pets_collection = db['pets']
battle_logs_collection = db['battle_logs']  # Collection to store battle logs

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

# Check and apply level up if XP is sufficient
def check_level_up(pet):
    xp_needed = calculate_xp_needed(pet['level'])
    leveled_up = False
    while pet['xp'] >= xp_needed:
        pet['level'] += 1
        pet['xp'] -= xp_needed
        pet['strength'] += LEVEL_UP_INCREASES["strength"]
        pet['defense'] += LEVEL_UP_INCREASES["defense"]
        pet['health'] += LEVEL_UP_INCREASES["health"]
        xp_needed = calculate_xp_needed(pet['level'])
        leveled_up = True
    return pet, leveled_up

# Create XP bar for visualization
def create_xp_bar(current_xp, xp_needed):
    total_blocks = 10
    filled_blocks = int((current_xp / xp_needed) * total_blocks)
    bar = "█" * filled_blocks + "░" * (total_blocks - filled_blocks)
    return bar

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

    new_pet = {
        "user_id": user_id,
        "guild_id": guild_id,  # Include guild ID to ensure one pet per server
        "name": name,
        "icon": PET_LIST[pet.value],
        "color": random_color,
        **INITIAL_STATS  # Add initial stats to the pet
    }
    pets_collection.insert_one(new_pet)

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
    if opponent == interaction.client.user:
        await interaction.response.send_message("You cannot battle the bot. Please choose another member with a pet.")
        return

    # Fetch the user's pet and the opponent's pet from the database for this server
    user_pet = pets_collection.find_one({"user_id": user_id, "guild_id": guild_id})
    opponent_pet = pets_collection.find_one({"user_id": opponent_id, "guild_id": guild_id})

    # Check if both participants have pets
    if not user_pet:
        await interaction.response.send_message(f"{interaction.user.mention}, you don't have a pet to battle with in this server!")
        return

    if not opponent_pet:
        await interaction.response.send_message(f"{opponent.mention} doesn't have a pet in this server. They need to summon one first.")
        return

    # Check if they have battled more than 5 times in the last 24 hours
    now = discord.utils.utcnow()
    twenty_four_hours_ago = now - timedelta(hours=24)
    recent_battles = battle_logs_collection.count_documents({
        "user_id": user_id,
        "opponent_id": opponent_id,
        "guild_id": guild_id,
        "timestamp": {"$gte": twenty_four_hours_ago}
    })

    if recent_battles >= 5:
        await interaction.response.send_message(f"You have already battled {opponent.display_name} 5 times in the last 24 hours in this server. Please try again later.")
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
        if user_event == "luck":
            round_log += f"{interaction.user.display_name}'s pet lands a **lucky hit** for {user_damage} damage!\n"
        elif user_crit:
            round_log += f"{interaction.user.display_name}'s pet lands a **critical hit** for {user_damage} damage!\n"
        else:
            round_log += f"{interaction.user.display_name}'s pet attacks for {user_damage} damage.\n"

        if opponent_health <= 0:
            round_log += f"{opponent.display_name}'s pet has been defeated!\n"
            battle_result = f"{interaction.user.display_name}'s pet wins the battle!"
            break

        # Opponent's turn to attack
        opponent_damage, opponent_crit, opponent_event = calculate_damage(opponent_pet, user_pet)
        user_health -= opponent_damage
        if opponent_event == "luck":
            round_log += f"{opponent.display_name}'s pet lands a **lucky hit** for {opponent_damage} damage!\n"
        elif opponent_crit:
            round_log += f"{opponent.display_name}'s pet lands a **critical hit** for {opponent_damage} damage!\n"
        else:
            round_log += f"{opponent.display_name}'s pet attacks for {opponent_damage} damage.\n"

        if user_health <= 0:
            round_log += f"{interaction.user.display_name}'s pet has been defeated!\n"
            battle_result = f"{opponent.display_name}'s pet wins the battle!"
            break

        round_log += f"\n{interaction.user.display_name}'s pet health: {user_health}\n"
        round_log += f"{opponent.display_name}'s pet health: {opponent_health}\n"

        # Update the embed with the new round log and health statuses
        battle_embed.description = round_log
        await message.edit(embed=battle_embed)

        await asyncio.sleep(2)  # Add delay between rounds
        round_number += 1

    # Final update with the battle result
    battle_embed.title = "Battle Concluded"
    battle_embed.description = f"{battle_result}\n\n{interaction.user.display_name}'s pet health: {max(0, user_health)}\n{opponent.display_name}'s pet health: {max(0, opponent_health)}"
    await message.edit(embed=battle_embed)

    # Award XP to the winner
    winner = interaction.user if user_health > 0 else opponent
    winner_pet = pets_collection.find_one({"user_id": str(winner.id), "guild_id": guild_id})
    xp_gain = random.randint(50, 100)
    winner_pet['xp'] += xp_gain
    winner_pet, leveled_up = check_level_up(winner_pet)

    # Update the pet data in the database
    pets_collection.update_one({"user_id": str(winner.id), "guild_id": guild_id}, {"$set": winner_pet})

    level_up_message = f" and leveled up to {winner_pet['level']}!" if leveled_up else "!"
    result_message = f"**{winner.display_name}'s pet wins the battle and gains {xp_gain} XP{level_up_message}**"

    final_embed = discord.Embed(
        title="Battle Result",
        description=result_message,
        color=discord.Color.green()
    )
    final_embed.set_thumbnail(url=winner_pet['icon'])

    await interaction.followup.send(embed=final_embed)


# Top pets leaderboard
@app_commands.command(name="top_pets", description="View the top pets leaderboard")
async def top_pets(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    
    # Sort first by level (descending) and then by XP (descending)
    top_pets = list(pets_collection.find({"guild_id": guild_id}).sort([("level", -1), ("xp", -1)]).limit(10))

    embed = discord.Embed(title="Top Pets Leaderboard", color=0xFFD700)
    for index, pet in enumerate(top_pets, 1):
        user = await interaction.client.fetch_user(int(pet['user_id']))
        embed.add_field(name=f"#{index}: {user.display_name}", value=f"Level: {pet['level']}, XP: {pet['xp']}", inline=False)
        embed.set_thumbnail(url=pet['icon'])
    
    await interaction.response.send_message(embed=embed)


# Register commands
def setup(client):
    client.tree.add_command(summon_pet)
    client.tree.add_command(pet_stats)
    client.tree.add_command(pet_battle)
    client.tree.add_command(top_pets)
