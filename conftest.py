import pytest
import asyncio
import discord
from unittest.mock import AsyncMock, MagicMock, patch
from discord.ext import commands
import os
import sys

os.environ.setdefault("ASTROSTATS_USE_MOCK_DB", "1")

sys.path.insert(0, os.path.abspath('.'))

@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_bot():
    bot = MagicMock(spec=commands.Bot)
    bot.user = MagicMock()
    bot.user.id = 123456789
    bot.guilds = []
    return bot

@pytest.fixture
def mock_interaction():
    interaction = MagicMock(spec=discord.Interaction)
    interaction.user = MagicMock()
    interaction.user.id = 987654321
    interaction.guild = MagicMock()
    interaction.guild.id = 111222333
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    return interaction

@pytest.fixture
def mock_user():
    user = MagicMock(spec=discord.User)
    user.id = 987654321
    user.name = "testuser"
    return user

@pytest.fixture
def mock_guild():
    guild = MagicMock(spec=discord.Guild)
    guild.id = 111222333
    guild.name = "Test Guild"
    return guild

@pytest.fixture(autouse=True)
def mock_env_vars():
    with patch.dict(os.environ, {
        'TOKEN': 'test_token',
        'MONGODB_URI': 'mongodb://localhost:27017/test',
        'MONGODB_USERS_DB': 'test_users'
    }):
        yield

@pytest.fixture
def free_tier_user():
    return {
        "discordId": "987654321",
        "premium": False,
        "tier": "free"
    }

@pytest.fixture
def supporter_tier_user():
    return {
        "discordId": "987654321",
        "premium": True,
        "status": "active",
        "role": "supporter",
        "currentPeriodEnd": 9999999999
    }

@pytest.fixture
def sponsor_tier_user():
    return {
        "discordId": "987654321",
        "premium": True,
        "status": "active",
        "role": "sponsor",
        "currentPeriodEnd": 9999999999
    }

@pytest.fixture
def vip_tier_user():
    return {
        "discordId": "987654321",
        "premium": True,
        "status": "active",
        "role": "vip",
        "currentPeriodEnd": 9999999999
    }
