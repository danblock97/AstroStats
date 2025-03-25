import random


def calculate_damage(attacker: dict, defender: dict):
    """
    Calculates the damage dealt by the attacker to the defender.
    Includes random multipliers, critical hit chance, and a chance for a lucky hit.
    Returns the damage value, a boolean for critical hit, and an event type ("normal" or "luck").
    """
    attack_multiplier = random.randint(8, 15) / 10
    defense_multiplier = random.randint(8, 15) / 10
    base_damage = int(
        (attacker['strength'] * attack_multiplier)
        * (random.randint(5, 15) / 10)
        - (defender['defense'] * defense_multiplier)
        * (random.randint(3, 10) / 10)
    )
    base_damage = max(5, base_damage)  # ensure minimum damage

    crit_chance = 15 + (10 if attacker['level'] < defender['level'] else 0)
    critical_hit = random.randint(1, 100) <= crit_chance

    if critical_hit:
        crit_multiplier = random.randint(15, 30) / 10
        base_damage = int(base_damage * crit_multiplier)

    if random.randint(1, 10) == 1:
        luck_damage = random.randint(15, 50)
        base_damage += luck_damage
        return base_damage, critical_hit, "luck"

    return base_damage, critical_hit, "normal"