import pytest
import discord
import datetime
import random
from unittest.mock import patch, AsyncMock, MagicMock
from cogs.systems.squib_game import SquibGames, create_new_session, get_guild_avatar_url, play_minigame_logic, \
    generate_flavor_text, conclude_game_auto, run_game_loop


@pytest.fixture
def setup_squib_games_cog(mock_bot):
    """Create an instance of the SquibGames cog."""
    return SquibGames(mock_bot)


@pytest.fixture
def mock_game_session():
    """Create a mock game session."""
    return {
        "_id": "test_game_id",
        "guild_id": "123456789",
        "host_user_id": "987654321",
        "session_id": "session123",
        "current_round": 0,
        "current_game_state": "waiting_for_players",
        "participants": [
            {
                "user_id": "987654321",
                "username": "HostUser",
                "status": "alive"
            },
            {
                "user_id": "111222333",
                "username": "Player1",
                "status": "alive"
            },
            {
                "user_id": "444555666",
                "username": "Player2",
                "status": "alive"
            }
        ],
        "created_at": datetime.datetime.now(datetime.timezone.utc)
    }


@pytest.mark.asyncio
async def test_get_guild_avatar_url_success(mock_guild):
    """Test get_guild_avatar_url when the member is found and has a guild avatar."""
    user_id = 123456789

    # Mock guild.fetch_member to return a member with a guild avatar
    member = MagicMock()
    member.guild_avatar = MagicMock()
    member.guild_avatar.url = "https://example.com/guild_avatar.png"
    mock_guild.fetch_member.return_value = AsyncMock(return_value=member)

    # Call the function
    result = await get_guild_avatar_url(mock_guild, user_id)

    # Verify the result
    assert result == "https://example.com/guild_avatar.png"


@pytest.mark.asyncio
async def test_get_guild_avatar_url_default_avatar(mock_guild):
    """Test get_guild_avatar_url when the member is found but has no guild avatar."""
    user_id = 123456789

    # Mock guild.fetch_member to return a member without a guild avatar
    member = MagicMock()
    member.guild_avatar = None
    member.display_avatar = MagicMock()
    member.display_avatar.url = "https://example.com/display_avatar.png"
    mock_guild.fetch_member.return_value = AsyncMock(return_value=member)

    # Call the function
    result = await get_guild_avatar_url(mock_guild, user_id)

    # Verify the result
    assert result == "https://example.com/display_avatar.png"


@pytest.mark.asyncio
async def test_get_guild_avatar_url_member_not_found(mock_guild):
    """Test get_guild_avatar_url when the member is not found."""
    user_id = 123456789

    # Mock guild.fetch_member to return None
    mock_guild.fetch_member.return_value = AsyncMock(return_value=None)

    # Call the function
    result = await get_guild_avatar_url(mock_guild, user_id)

    # Verify the result
    assert result is None


@pytest.mark.asyncio
async def test_get_guild_avatar_url_exception(mock_guild):
    """Test get_guild_avatar_url when an exception occurs."""
    user_id = 123456789

    # Mock guild.fetch_member to raise an exception
    mock_guild.fetch_member.side_effect = Exception("Test error")

    # Call the function
    result = await get_guild_avatar_url(mock_guild, user_id)

    # Verify the result
    assert result is None


def test_play_minigame_logic():
    """Test the play_minigame_logic function."""
    # Setup
    round_number = 1
    participants = [
        {"user_id": "1", "username": "Player1", "status": "alive"},
        {"user_id": "2", "username": "Player2", "status": "alive"},
        {"user_id": "3", "username": "Player3", "status": "alive"},
        {"user_id": "4", "username": "Player4", "status": "eliminated"}
    ]

    # Mock random functions to ensure consistent results
    with patch('random.choice') as mock_choice, \
            patch('random.random') as mock_random, \
            patch('random.shuffle') as mock_shuffle:
        # Set up mock return values
        minigame = {
            "name": "Test Minigame",
            "emoji": "🎮",
            "description": "Test description",
            "elimination_probability": 0.5
        }
        mock_choice.return_value = minigame

        # Set random.random to return values that cause eliminations for some players
        mock_random.side_effect = [0.4, 0.6, 0.2]  # Player1 and Player3 are eliminated

        # Call the function
        updated_participants, returned_minigame = play_minigame_logic(round_number, participants)

        # Verify the results
        assert returned_minigame == minigame
        assert len(updated_participants) == 4

        # Check status of each participant
        alive_count = sum(1 for p in updated_participants if p["status"] == "alive")
        eliminated_count = sum(1 for p in updated_participants if p["status"] == "eliminated")

        # Verify that some players were eliminated
        assert eliminated_count > 1
        assert alive_count < 3  # Not all alive players stayed alive


def test_generate_flavor_text():
    """Test the generate_flavor_text function for different minigame types."""
    # Setup
    eliminated_players = ["Player1", "Player2"]
    alive_players = ["Player3", "Player4"]

    # Test Red Light, Green Light
    flavor_text = generate_flavor_text("Red Light, Green Light 🚦", eliminated_players, alive_players)
    assert "lights flickered" in flavor_text
    assert "Player1" in flavor_text
    assert "Player2" in flavor_text
    assert "Player3" in flavor_text
    assert "Player4" in flavor_text

    # Test Glass Bridge
    flavor_text = generate_flavor_text("Glass Bridge 🌉", eliminated_players, alive_players)
    assert "chose the wrong panel" in flavor_text
    assert "Player1" in flavor_text
    assert "Player2" in flavor_text
    assert "Player3" in flavor_text
    assert "Player4" in flavor_text

    # Test Simon Says
    flavor_text = generate_flavor_text("Simon Says 🎤", eliminated_players, alive_players)
    assert "failed to follow the commands" in flavor_text
    assert "Player1" in flavor_text
    assert "Player2" in flavor_text
    assert "Player3" in flavor_text
    assert "Player4" in flavor_text

    # Test Treasure Hunt
    flavor_text = generate_flavor_text("Treasure Hunt 🗺️", eliminated_players, alive_players)
    assert "find the hidden treasures" in flavor_text
    assert "Player1" in flavor_text
    assert "Player2" in flavor_text
    assert "Player3" in flavor_text
    assert "Player4" in flavor_text

    # Test another minigame (should use generic text)
    flavor_text = generate_flavor_text("Other Minigame", eliminated_players, alive_players)
    assert "chaos claimed" in flavor_text
    assert "Player1" in flavor_text
    assert "Player2" in flavor_text
    assert "Player3" in flavor_text
    assert "Player4" in flavor_text


def test_generate_flavor_text_no_eliminations():
    """Test the generate_flavor_text function when no players are eliminated."""
    # Setup
    eliminated_players = []
    alive_players = ["Player1", "Player2", "Player3"]

    # Test Red Light, Green Light with no eliminations
    flavor_text = generate_flavor_text("Red Light, Green Light 🚦", eliminated_players, alive_players)
    assert "Everyone froze perfectly still" in flavor_text
    assert "Player1" in flavor_text
    assert "Player2" in flavor_text
    assert "Player3" in flavor_text


def test_create_new_session():
    """Test the create_new_session function."""
    # Setup
    guild_id = "test_guild"
    user_id = "test_user"
    display_name = "Test User"

    # Mock squib_game_sessions.insert_one
    with patch('cogs.systems.squib_game.squib_game_sessions.insert_one') as mock_insert:
        mock_result = MagicMock()
        mock_result.inserted_id = "test_session_id"
        mock_insert.return_value = mock_result

        # Call the function
        session_id, session_doc = create_new_session(guild_id, user_id, display_name)

        # Verify the results
        assert guild_id in session_id
        assert user_id in session_id
        assert session_doc["guild_id"] == guild_id
        assert session_doc["host_user_id"] == user_id
        assert session_doc["session_id"] == session_id
        assert session_doc["current_round"] == 0
        assert session_doc["current_game_state"] == "waiting_for_players"
        assert len(session_doc["participants"]) == 1
        assert session_doc["participants"][0]["user_id"] == user_id
        assert session_doc["participants"][0]["username"] == display_name
        assert session_doc["participants"][0]["status"] == "alive"
        assert session_doc["_id"] == "test_session_id"


@pytest.mark.asyncio
async def test_start_command_success(setup_squib_games_cog, mock_interaction):
    """Test the start command when no session exists."""
    # Setup
    cog = setup_squib_games_cog
    guild_id = str(mock_interaction.guild_id)
    user_id = str(mock_interaction.user.id)

    # Mock database call to check for existing game
    with patch('cogs.systems.squib_game.squib_game_sessions.find_one', return_value=None), \
            patch('cogs.systems.squib_game.create_new_session') as mock_create_session, \
            patch('cogs.systems.squib_game.get_guild_avatar_url', return_value="https://example.com/avatar.png"), \
            patch('discord.Embed') as mock_embed:
        # Set up mock return values
        session_id = "test_session_id"
        session_doc = {
            "guild_id": guild_id,
            "host_user_id": user_id,
            "session_id": session_id,
            "current_round": 0,
            "current_game_state": "waiting_for_players",
            "participants": [{"user_id": user_id, "username": mock_interaction.user.display_name, "status": "alive"}]
        }
        mock_create_session.return_value = (session_id, session_doc)

        # Call the command
        await cog.start(mock_interaction)

        # Verify create_new_session was called
        mock_create_session.assert_called_once_with(guild_id, user_id, mock_interaction.user.display_name)

        # Verify embeds were created
        assert mock_embed.call_count >= 1

        # Verify response with embeds and view
        mock_interaction.response.send_message.assert_called_once()
        called_with_kwargs = mock_interaction.response.send_message.call_args[1]
        assert 'embeds' in called_with_kwargs
        assert 'view' in called_with_kwargs


@pytest.mark.asyncio
async def test_start_command_session_exists(setup_squib_games_cog, mock_interaction):
    """Test the start command when a session already exists."""
    # Setup
    cog = setup_squib_games_cog

    # Mock database call to return an existing game
    existing_game = {
        "guild_id": str(mock_interaction.guild_id),
        "host_user_id": "other_user_id",
        "current_game_state": "waiting_for_players"
    }

    with patch('cogs.systems.squib_game.squib_game_sessions.find_one', return_value=existing_game), \
            patch('discord.Embed') as mock_embed:
        # Call the command
        await cog.start(mock_interaction)

        # Verify error embed was created
        mock_embed.assert_called_once()
        mock_embed.return_value.title = "Session Already Exists ❌"

        # Verify response with ephemeral error message
        mock_interaction.response.send_message.assert_called_once()
        called_with_kwargs = mock_interaction.response.send_message.call_args[1]
        assert 'embed' in called_with_kwargs
        assert called_with_kwargs.get('ephemeral') is True


@pytest.mark.asyncio
async def test_run_command_no_game(setup_squib_games_cog, mock_interaction):
    """Test the run command when no game exists."""
    # Setup
    cog = setup_squib_games_cog

    # Mock database call to return no game
    with patch('cogs.systems.squib_game.squib_game_sessions.find_one', return_value=None), \
            patch('discord.Embed') as mock_embed:
        # Call the command
        await cog.run(mock_interaction)

        # Verify error embed was created
        mock_embed.assert_called_once()
        mock_embed.return_value.title = "No Active or Waiting Game 🛑"

        # Verify response with ephemeral error message
        mock_interaction.response.send_message.assert_called_once()
        called_with_kwargs = mock_interaction.response.send_message.call_args[1]
        assert 'embed' in called_with_kwargs
        assert called_with_kwargs.get('ephemeral') is True


@pytest.mark.asyncio
async def test_run_command_not_enough_players(setup_squib_games_cog, mock_interaction):
    """Test the run command when there aren't enough players."""
    # Setup
    cog = setup_squib_games_cog
    game = {
        "_id": "test_game_id",
        "guild_id": str(mock_interaction.guild_id),
        "host_user_id": str(mock_interaction.user.id),
        "session_id": "test_session_id",
        "current_game_state": "waiting_for_players",
        "participants": [
            {"user_id": str(mock_interaction.user.id), "username": mock_interaction.user.display_name,
             "status": "alive"}
        ]
    }

    # Mock database call to return a game with only one player
    with patch('cogs.systems.squib_game.squib_game_sessions.find_one', return_value=game), \
            patch('discord.Embed') as mock_embed:
        # Call the command
        await cog.run(mock_interaction)

        # Verify error embed was created
        mock_embed.assert_called_once()
        mock_embed.return_value.title = "Not Enough Players 🙋‍♂️"

        # Verify response with ephemeral error message
        mock_interaction.response.send_message.assert_called_once()
        called_with_kwargs = mock_interaction.response.send_message.call_args[1]
        assert 'embed' in called_with_kwargs
        assert called_with_kwargs.get('ephemeral') is True


@pytest.mark.asyncio
async def test_status_command_no_game(setup_squib_games_cog, mock_interaction):
    """Test the status command when no game exists."""
    # Setup
    cog = setup_squib_games_cog

    # Mock database call to return no game
    with patch('cogs.systems.squib_game.squib_game_sessions.find_one', return_value=None), \
            patch('discord.Embed') as mock_embed:
        # Call the command
        await cog.status(mock_interaction)

        # Verify error embed was created
        mock_embed.assert_called_once()
        mock_embed.return_value.title = "No Active Session 🚫"

        # Verify response with ephemeral error message
        mock_interaction.response.send_message.assert_called_once()
        called_with_kwargs = mock_interaction.response.send_message.call_args[1]
        assert 'embed' in called_with_kwargs
        assert called_with_kwargs.get('ephemeral') is True


@pytest.mark.asyncio
async def test_status_command_success(setup_squib_games_cog, mock_interaction, mock_game_session):
    """Test the status command when a game exists."""
    # Setup
    cog = setup_squib_games_cog

    # Mock database call to return a game
    with patch('cogs.systems.squib_game.squib_game_sessions.find_one', return_value=mock_game_session), \
            patch('cogs.systems.squib_game.get_guild_avatar_url', return_value="https://example.com/avatar.png"):

        # Call the command
        await cog.status(mock_interaction)

        # Verify response with game status
        mock_interaction.response.send_message.assert_called_once()
        called_with_kwargs = mock_interaction.response.send_message.call_args[1]
        assert 'embed' in called_with_kwargs

        # Check the embed's content
        embed = called_with_kwargs['embed']
        assert "Current Squib Game Status" in embed.title
        assert mock_game_session["current_game_state"] in embed.description
        assert str(mock_game_session["current_round"]) in embed.description
        assert f"<@{mock_game_session['host_user_id']}>" in embed.description

        # Check the alive players field
        alive_field = None
        for field in embed.fields:
            if "Alive Players" in field.name:
                alive_field = field
                break

        assert alive_field is not None
        for participant in mock_game_session["participants"]:
            if participant["status"] == "alive":
                assert participant["username"] in alive_field.value


@pytest.mark.asyncio
async def test_setup(mock_bot):
    """Test the setup function."""
    # Call the setup function
    from cogs.systems.squib_game import setup
    await setup(mock_bot)

    # Verify the cog was added to the bot
    mock_bot.add_cog.assert_called_once()

    # Check that the cog is an instance of SquibGames
    cog = mock_bot.add_cog.call_args.args[0]
    assert isinstance(cog, SquibGames)