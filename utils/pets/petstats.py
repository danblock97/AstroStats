from utils.pets.petconstants import LEVEL_UP_INCREASES

def calculate_xp_needed(level: int) -> int:
    """
    Calculate how much XP is required to level up from the given level.
    """
    return level ** 2 * 100

def check_level_up(pet: dict):
    """
    Checks whether a pet has enough XP to level up and applies
    the level-up stat bonuses repeatedly until it no longer can.
    Returns the updated pet and a bool indicating if a level-up occurred.
    """
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
    """
    Creates a 10-block XP progress bar.
    Filled blocks are determined by current / total XP ratio.
    """
    total_blocks = 10
    if total <= 0:
        total = 1  # to avoid division by zero
    filled_blocks = int((current / total) * total_blocks)
    return "█" * filled_blocks + "░" * (total_blocks - filled_blocks)
