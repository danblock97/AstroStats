# Define 20 Daily Quests
DAILY_QUESTS = [
    {"id": 1, "description": "Win 3 battles", "progress_required": 3, "xp_reward": 100},
    {"id": 2, "description": "Win 5 battles", "progress_required": 5, "xp_reward": 150},
    {"id": 3, "description": "Win 10 battles", "progress_required": 10, "xp_reward": 300},
    {"id": 4, "description": "Achieve a 3-battle win streak", "progress_required": 3, "xp_reward": 120},
    {"id": 5, "description": "Achieve a 5-battle win streak", "progress_required": 5, "xp_reward": 250},
    {"id": 6, "description": "Achieve a 2-battle killstreak", "progress_required": 2, "xp_reward": 80},
    {"id": 7, "description": "Achieve a 4-battle killstreak", "progress_required": 4, "xp_reward": 200},
    {"id": 8, "description": "Achieve a 5-battle killstreak", "progress_required": 5, "xp_reward": 300},
    {"id": 9, "description": "Inflict 10 critical hits in battles", "progress_required": 10, "xp_reward": 200},
    {"id": 10, "description": "Inflict 20 critical hits in battles", "progress_required": 20, "xp_reward": 400},
    {"id": 11, "description": "Land 5 lucky hits", "progress_required": 5, "xp_reward": 150},
    {"id": 12, "description": "Land 10 lucky hits", "progress_required": 10, "xp_reward": 300},
    {"id": 13, "description": "Lose 3 battles (learn from mistakes)", "progress_required": 3, "xp_reward": 100},
    {"id": 14, "description": "Lose 5 battles", "progress_required": 5, "xp_reward": 150},
    {"id": 15, "description": "Earn 100 XP from battles", "progress_required": 100, "xp_reward": 200},
    {"id": 16, "description": "Earn 300 XP from battles", "progress_required": 300, "xp_reward": 400},
    {"id": 17, "description": "Participate in 5 battles", "progress_required": 5, "xp_reward": 150},
    {"id": 18, "description": "Participate in 10 battles", "progress_required": 10, "xp_reward": 300},
    {"id": 19, "description": "Deal 500 damage in total", "progress_required": 500, "xp_reward": 250},
    {"id": 20, "description": "Deal 1000 damage in total", "progress_required": 1000, "xp_reward": 500}
]

# Define 5 Achievements (Hard to reach)
ACHIEVEMENTS = [
    {"id": 1, "description": "Win 50 battles", "progress_required": 50, "xp_reward": 2000},
    {"id": 2, "description": "Achieve a 10-battle killstreak", "progress_required": 10, "xp_reward": 2500},
    {"id": 3, "description": "Deal 5000 total damage", "progress_required": 5000, "xp_reward": 3000},
    {"id": 4, "description": "Land 50 critical hits", "progress_required": 50, "xp_reward": 2200},
    {"id": 5, "description": "Land 25 lucky hits", "progress_required": 25, "xp_reward": 1800}
]

# Basic pet stats that every new pet starts with
INITIAL_STATS = {
    "level": 1,
    "xp": 0,
    "strength": 10,
    "defense": 10,
    "health": 100
}

# How much, stats increase when a pet levels up
LEVEL_UP_INCREASES = {
    "strength": 5,
    "defense": 5,
    "health": 20
}

# The list of available pet icons (by pet name)
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

# A small color palette for random embed colors
COLOR_LIST = {
    "red": 0xFF0000,
    "green": 0x00FF00,
    "blue": 0x0000FF,
    "yellow": 0xFFFF00,
    "purple": 0x800080
}