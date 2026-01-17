import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
TOKEN = os.getenv('TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID', 0))
OWNER_GUILD_ID = int(os.getenv('OWNER_GUILD_ID', 0))
BLACKLISTED_GUILDS = set(map(int, os.getenv('BLACKLISTED_GUILDS', '').split(','))) if os.getenv('BLACKLISTED_GUILDS') else set()
DISCORD_APP_ID = os.getenv('DISCORD_APP_ID')

# API keys
TRN_API_KEY = os.getenv('TRN_API_KEY')
LOL_API = os.getenv('LOL_API')
TFT_API = os.getenv('TFT_API')
FORTNITE_API_KEY = os.getenv('FORTNITE_API_KEY')
TOPGG_TOKEN = os.getenv('TOPGG_TOKEN')

# MongoDB configuration
MONGODB_URI = os.getenv('MONGODB_URI')

# Discord webhook for error logging
ERROR_WEBHOOK_URL = os.getenv('ERROR_WEBHOOK_URL')