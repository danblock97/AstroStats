import pytest
import discord
from discord.ext import commands
import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import json

# Mock bot instance
@pytest.fixture
def mock_bot():
    bot = MagicMock(spec=commands.Bot)
    bot.guilds = []
    bot.tree = AsyncMock()
    bot.tree.sync = AsyncMock()
    bot.change_presence = AsyncMock()
    bot.wait_until_ready = AsyncMock()
    bot.fetch_user = AsyncMock()
    bot.add_cog = AsyncMock()
    return bot

# Mock interaction instance
@pytest.fixture
def mock_interaction():
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.response = AsyncMock()
    interaction.response.is_done = MagicMock(return_value=False)
    interaction.followup = AsyncMock()
    interaction.guild = MagicMock(spec=discord.Guild)
    interaction.guild.id = 123456789
    interaction.guild_id = 123456789
    interaction.user = MagicMock(spec=discord.User)
    interaction.user.id = 987654321
    interaction.user.display_name = "TestUser"
    interaction.user.display_avatar = MagicMock()
    interaction.user.display_avatar.url = "https://example.com/avatar.png"
    interaction.user.mention = "<@987654321>"
    interaction.message = MagicMock()
    interaction.message.embeds = []
    interaction.message.edit = AsyncMock()
    return interaction

# Mock guild instance
@pytest.fixture
def mock_guild():
    guild = MagicMock(spec=discord.Guild)
    guild.id = 123456789
    guild.name = "Test Guild"
    guild.icon = MagicMock()
    guild.icon.url = "https://example.com/icon.png"
    guild.system_channel = MagicMock(spec=discord.TextChannel)
    guild.text_channels = [MagicMock(spec=discord.TextChannel)]
    guild.me = MagicMock()
    guild.fetch_member = AsyncMock()
    guild.leave = AsyncMock()
    return guild

# Mock commands.Context
@pytest.fixture
def mock_context(mock_bot, mock_guild):
    ctx = MagicMock(spec=commands.Context)
    ctx.bot = mock_bot
    ctx.guild = mock_guild
    ctx.channel = MagicMock(spec=discord.TextChannel)
    ctx.author = MagicMock(spec=discord.Member)
    ctx.author.id = 987654321
    ctx.author.display_name = "TestUser"
    ctx.send = AsyncMock()
    return ctx

# Mock Member instance
@pytest.fixture
def mock_member():
    member = MagicMock(spec=discord.Member)
    member.id = 987654321
    member.display_name = "TestUser"
    member.display_avatar = MagicMock()
    member.display_avatar.url = "https://example.com/avatar.png"
    member.guild_avatar = None
    member.mention = "<@987654321>"
    return member

# Mock API response fixtures
@pytest.fixture
def mock_apex_response():
    return {
        "data": {
            "metadata": {
                "activeLegendName": "Wraith"
            },
            "segments": [
                {
                    "metadata": {
                        "name": "Wraith",
                        "portraitImageUrl": "https://example.com/wraith.png",
                        "bgColor": "#9B8651"
                    },
                    "stats": {
                        "kills": {
                            "value": 1000,
                            "percentile": 80
                        },
                        "damage": {
                            "value": 300000,
                            "percentile": 75
                        },
                        "rankScore": {
                            "value": 7200,
                            "percentile": 60,
                            "metadata": {
                                "rankName": "Platinum"
                            }
                        },
                        "lifetimePeakRankScore": {
                            "value": 10000,
                            "metadata": {
                                "rankName": "Diamond"
                            }
                        },
                        "level": {
                            "value": 100,
                            "percentile": 75
                        },
                        "matchesPlayed": {
                            "value": 2000,
                            "percentile": 70
                        },
                        "arenaWinStreak": {
                            "value": 10,
                            "percentile": 90
                        }
                    }
                }
            ]
        }
    }

# Mock response for League of Legends
@pytest.fixture
def mock_lol_account_response():
    return {
        "puuid": "test-puuid-123",
        "gameName": "TestPlayer",
        "tagLine": "1234"
    }

@pytest.fixture
def mock_lol_summoner_response():
    return {
        "id": "test-summoner-id",
        "accountId": "test-account-id",
        "puuid": "test-puuid-123",
        "name": "TestPlayer",
        "profileIconId": 1234,
        "summonerLevel": 100
    }

@pytest.fixture
def mock_lol_league_response():
    return [
        {
            "queueType": "RANKED_SOLO_5x5",
            "tier": "GOLD",
            "rank": "II",
            "leaguePoints": 75,
            "wins": 120,
            "losses": 100
        },
        {
            "queueType": "RANKED_FLEX_SR",
            "tier": "SILVER",
            "rank": "I",
            "leaguePoints": 50,
            "wins": 80,
            "losses": 70
        }
    ]

# Mock MongoDB Collection
@pytest.fixture
def mock_mongo_collection():
    collection = MagicMock()
    collection.find_one.return_value = None
    collection.insert_one.return_value = MagicMock()
    collection.insert_one.return_value.inserted_id = "mocked_id"
    collection.update_one.return_value = MagicMock()
    collection.update_one.return_value.modified_count = 1
    collection.find.return_value = []
    collection.count_documents.return_value = 0
    return collection

# Async time-related fixture
@pytest.fixture
async def mock_sleep():
    with patch('asyncio.sleep', return_value=None) as mock:
        yield mock