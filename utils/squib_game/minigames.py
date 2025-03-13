import random

MINIGAMES = [
    {
        "name": "Red Light, Green Light 🚦",
        "emoji": "\U0001F6A5",
        "description": "Players must stay still when 'Red Light' is called.",
        "elimination_probability": 0.5
    },
    {
        "name": "Glass Bridge 🌉",
        "emoji": "\U0001F309",
        "description": "Choose the correct glass panels to cross safely.",
        "elimination_probability": 0.3
    },
    {
        "name": "Random Mayhem ⚡",
        "emoji": "\U000026A1",
        "description": "Unpredictable chaos ensues, testing players' luck.",
        "elimination_probability": 0.2
    },
    {
        "name": "Simon Says 🎤",
        "emoji": "\U0001F3A4",
        "description": "Players must follow the leader's commands precisely.",
        "elimination_probability": 0.25
    },
    {
        "name": "Treasure Hunt 🗺️",
        "emoji": "\U0001F5FA",
        "description": "Players search for hidden treasures under time pressure.",
        "elimination_probability": 0.35
    },
    {
        "name": "Knife Throwing 🗡️",
        "emoji": "\U0001F5E1",
        "description": "Players attempt to throw knives at a target with precision.",
        "elimination_probability": 0.4
    },
    {
        "name": "Marbles Madness 🏀",
        "emoji": "\U0001F3C0",
        "description": "Compete in a fast-paced marbles game where the last marble standing wins.",
        "elimination_probability": 0.3
    },
    {
        "name": "Dollmaker 🪆",
        "emoji": "\U0001FA86",
        "description": "Create dolls based on specific criteria; the least creative ones are eliminated.",
        "elimination_probability": 0.25
    },
    {
        "name": "Heartbeat 💓",
        "emoji": "\U0001F493",
        "description": "Players must keep their heartbeats steady; sudden changes lead to elimination.",
        "elimination_probability": 0.35
    },
    {
        "name": "Tug of War 🤼",
        "emoji": "\U0001F93C",
        "description": "Teams compete in a tug of war; the losing team faces elimination.",
        "elimination_probability": 0.5
    },
    {
        "name": "Quiz Show 🧠",
        "emoji": "\U0001F4DA",
        "description": "Answer rapid-fire trivia questions correctly to stay in the game.",
        "elimination_probability": 0.3
    },
    {
        "name": "Paintball 🖌️",
        "emoji": "\U0001F58C",
        "description": "Engage in a virtual paintball match; the last player unhit wins.",
        "elimination_probability": 0.4
    },
    {
        "name": "Maze Runner 🌀",
        "emoji": "\U0001F300",
        "description": "Navigate through a complex maze; failing to find the exit leads to elimination.",
        "elimination_probability": 0.35
    },
    {
        "name": "Jigsaw Puzzle 🧩",
        "emoji": "\U0001F9E9",
        "description": "Complete a jigsaw puzzle within the time limit to avoid elimination.",
        "elimination_probability": 0.25
    },
    {
        "name": "Scavenger Hunt 🔍",
        "emoji": "\U0001F50D",
        "description": "Find hidden items based on clues; failure to locate them results in elimination.",
        "elimination_probability": 0.3
    }
]

def generate_flavor_text(minigame_desc: str, eliminated_this_round: list, alive_players: list) -> str:
    flavor_sentences = []
    max_display = 10
    if "Red Light" in minigame_desc:
        if eliminated_this_round:
            if len(eliminated_this_round) > max_display:
                displayed = eliminated_this_round[:max_display]
                remaining = len(eliminated_this_round) - max_display
                flavor_sentences.append(
                    f"As the lights flickered, **{', '.join(displayed)}** "
                    f"{'and ' + str(remaining) + ' others' if remaining > 0 else ''} were caught moving at the wrong moment..."
                )
            else:
                flavor_sentences.append(
                    f"As the lights flickered, **{', '.join(eliminated_this_round)}** were caught moving at the wrong moment..."
                )
        else:
            flavor_sentences.append("Everyone froze perfectly still—no one got caught this time!")
        if alive_players:
            flavor_sentences.append(
                f"The relentless spotlights scanned the field, but **{', '.join(alive_players)}** "
                "made it through unscathed."
            )
    elif "Glass Bridge" in minigame_desc:
        if eliminated_this_round:
            if len(eliminated_this_round) > max_display:
                displayed = eliminated_this_round[:max_display]
                remaining = len(eliminated_this_round) - max_display
                flavor_sentences.append(
                    f"**{', '.join(displayed)}** "
                    f"{'and ' + str(remaining) + ' others' if remaining > 0 else ''} chose the wrong panel and plummeted into the abyss..."
                )
            else:
                flavor_sentences.append(
                    f"**{', '.join(eliminated_this_round)}** chose the wrong panel and plummeted into the abyss..."
                )
        else:
            flavor_sentences.append(
                "Miraculously, nobody fell this round—every guess was spot on!"
            )
        if alive_players:
            flavor_sentences.append(
                f"Shards of glass littered the bridge, yet **{', '.join(alive_players)}** "
                "bravely reached the other side."
            )
    elif "Simon Says" in minigame_desc:
        if eliminated_this_round:
            if len(eliminated_this_round) > max_display:
                displayed = eliminated_this_round[:max_display]
                remaining = len(eliminated_this_round) - max_display
                flavor_sentences.append(
                    f"**{', '.join(displayed)}** "
                    f"{'and ' + str(remaining) + ' others' if remaining > 0 else ''} failed to follow the commands and were eliminated..."
                )
            else:
                flavor_sentences.append(
                    f"**{', '.join(eliminated_this_round)}** failed to follow the commands and were eliminated..."
                )
        else:
            flavor_sentences.append(
                "Everyone followed the commands flawlessly—no eliminations this round!"
            )
        if alive_players:
            flavor_sentences.append(
                f"**{', '.join(alive_players)}** showed impeccable discipline and stayed in the game."
            )
    elif "Treasure Hunt" in minigame_desc:
        if eliminated_this_round:
            if len(eliminated_this_round) > max_display:
                displayed = eliminated_this_round[:max_display]
                remaining = len(eliminated_this_round) - max_display
                flavor_sentences.append(
                    f"**{', '.join(displayed)}** "
                    f"{'and ' + str(remaining) + ' others' if remaining > 0 else ''} couldn't find the hidden treasures in time and were eliminated..."
                )
            else:
                flavor_sentences.append(
                    f"**{', '.join(eliminated_this_round)}** couldn't find the hidden treasures in time and were eliminated..."
                )
        else:
            flavor_sentences.append(
                "All players found the treasures swiftly—no eliminations this round!"
            )
        if alive_players:
            flavor_sentences.append(
                f"**{', '.join(alive_players)}** continue their quest with renewed vigor."
            )
    else:
        if eliminated_this_round:
            if len(eliminated_this_round) > max_display:
                displayed = eliminated_this_round[:max_display]
                remaining = len(eliminated_this_round) - max_display
                flavor_sentences.append(
                    f"The chaos claimed **{', '.join(displayed)}** "
                    f"{'and ' + str(remaining) + ' others' if remaining > 0 else ''} as they stumbled in the mayhem..."
                )
            else:
                flavor_sentences.append(
                    f"The chaos claimed **{', '.join(eliminated_this_round)}** as they stumbled in the mayhem..."
                )
        else:
            flavor_sentences.append("Somehow, no one fell victim to the chaos this round!")
        if alive_players:
            flavor_sentences.append(
                f"By skill or sheer luck, **{', '.join(alive_players)}** remain in the competition."
            )
    return "\n".join(flavor_sentences)

def play_minigame_logic(round_number: int, participants: list) -> tuple[list, dict]:
    updated = [dict(p) for p in participants]
    minigame = random.choice(MINIGAMES)
    minigame_desc = f"{minigame['name']} {minigame['emoji']}"
    elimination_candidates = [
        p for p in updated
        if p["status"] == "alive" and random.random() < minigame["elimination_probability"]
    ]
    random.shuffle(elimination_candidates)
    for p in elimination_candidates[:3]:
        p["status"] = "eliminated"
    return updated, minigame
