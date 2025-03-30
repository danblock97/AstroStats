# League related constants
LEAGUE_REGIONS = [
    "EUW1", "EUN1", "TR1", "RU", "NA1", "BR1", "LA1", "LA2",
    "JP1", "KR", "OC1", "SG2", "TW2", "VN2"
]

LEAGUE_QUEUE_TYPE_NAMES = {
    "RANKED_SOLO_5x5": "Ranked Solo/Duo",
    "RANKED_FLEX_SR": "Ranked Flex 5v5",
    "CHERRY": "Arena"
}

TFT_QUEUE_TYPE_NAMES = {
    "RANKED_TFT": "Ranked TFT",
}

# Platform mappings for Apex Legends
APEX_PLATFORM_MAPPING = {
    'Xbox': 'xbl',
    'Playstation': 'psn',
    'Origin (PC)': 'origin',
}

# Time mapping for Fortnite
FORTNITE_TIME_MAPPING = {
    'Season': 'season',
    'Lifetime': 'lifetime',
}

# Special emoji name mappings for League of Legends
SPECIAL_EMOJI_NAMES = {
    "Renata Glasc": "Renata",
    "Wukong": "MonkeyKing",
    "Miss Fortune": "MissFortune",
    "Xin Zhao": "XinZhao",
    "Aurelion Sol": "AurelionSol",
    "Bel'Veth": "Belveth",
    "Cho'Gath": "Chogath",
    "Nunu & Willump": "Nunu",
    "Lee Sin": "LeeSin",
    "K'Sante": "KSante",
    "Kog'Maw": "KogMaw",
    "Twisted Fate": "TwistedFate",
    "Dr. Mundo": "DrMundo",
    "Rek'Sai": "RekSai",
    "Kai'Sa": "KaiSa",
    "Vel'Koz": "Velkoz",
    "Kha'Zix": "Khazix",
    "Master Yi": "MasterYi",
}

# Latest bot updates
LATEST_UPDATES = (
    "**Version 2.1.0 (Pet Battles Overhaul & Maintenance)**:\n\n"
    "**🐾 Pet Battles Major Update**\n"
    "- **Economy System:** Introduced Pet Balance (🪙)! Pets now start with 0 balance.\n"
    "- **Cash Rewards:** Daily Quests and Achievements now grant cash rewards alongside XP.\n"
    "- **Daily Bonus:** Earn bonus XP and cash for completing all daily quests.\n"
    "- **Item Shop:** Added `/petbattles shop` and `/petbattles buy` commands. Purchase temporary stat-boosting items (potions, etc.) using your pet's balance.\n"
    "- **UI Enhancements:** Improved the visual presentation of all Pet Battles command embeds for better readability.\n\n"
    "**🧹 Maintenance**\n"
    "- **Database Migration:** Implemented necessary database updates for the new features. To ensure a smooth transition, pet data inactive for over 3 months prior to this update has been removed. All recently active pets have been successfully migrated.\n\n"
)