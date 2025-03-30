# cogs/systems/pet_battles/petbattle.py
import random
from typing import Dict, Tuple, List, Any

# Helper function to get active buffs for a specific stat
def get_active_buff(active_items: List[Dict[str, Any]], stat_name: str) -> int:
    """Calculates the total buff value for a given stat from active items."""
    total_buff = 0
    for item in active_items:
        if item.get('stat') == stat_name and item.get('battles_remaining', 0) > 0:
            total_buff += item.get('value', 0)
    return total_buff

def calculate_damage(attacker_pet: Dict[str, Any], defender_pet: Dict[str, Any]) -> Tuple[int, bool, str]:
    """
    Calculates the damage dealt by the attacker to the defender, considering active items.
    Includes random multipliers, critical hit chance, and a chance for a lucky hit.
    Returns the damage value, a boolean for critical hit, and an event type ("normal" or "luck").
    """
    # Get active buffs
    attacker_strength_buff = get_active_buff(attacker_pet.get('active_items', []), 'strength')
    defender_defense_buff = get_active_buff(defender_pet.get('active_items', []), 'defense')
    # Note: Health buffs apply to max health, handled separately if needed during battle init/display

    # Apply buffs to base stats for calculation
    effective_strength = attacker_pet.get('strength', 10) + attacker_strength_buff
    effective_defense = defender_pet.get('defense', 10) + defender_defense_buff

    # --- Damage Calculation ---
    attack_multiplier = random.randint(8, 15) / 10
    defense_multiplier = random.randint(8, 15) / 10

    # Calculate base damage using effective stats
    base_damage = int(
        (effective_strength * attack_multiplier * (random.randint(5, 15) / 10))
        - (effective_defense * defense_multiplier * (random.randint(3, 10) / 10))
    )
    base_damage = max(5, base_damage)  # Ensure minimum damage of 5

    # --- Critical Hit Check ---
    # Crit chance increases slightly if attacker level is lower
    crit_chance = 15 + (10 if attacker_pet.get('level', 1) < defender_pet.get('level', 1) else 0)
    critical_hit = random.randint(1, 100) <= crit_chance

    if critical_hit:
        crit_multiplier = random.randint(15, 30) / 10 # Crit multiplier between 1.5x and 3.0x
        base_damage = int(base_damage * crit_multiplier)

    # --- Lucky Hit Check ---
    # 10% chance for a lucky hit adding bonus damage
    if random.randint(1, 10) == 1:
        luck_damage = random.randint(15, 50) # Add 15-50 extra damage on lucky hit
        base_damage += luck_damage
        return base_damage, critical_hit, "luck" # Return damage, crit status, and 'luck' event

    # Return normal damage if no lucky hit
    return base_damage, critical_hit, "normal" # Return damage, crit status, and 'normal' event
