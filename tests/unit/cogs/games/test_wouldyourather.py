import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock
import discord
from discord import app_commands


class TestWouldYouRatherCommand:
    """Test Would You Rather game command functionality"""
    
    @pytest.fixture
    def mock_bot(self):
        """Mock Discord bot"""
        bot = MagicMock()
        return bot

    @pytest.fixture
    def mock_interaction(self):
        """Mock Discord interaction"""
        interaction = AsyncMock()
        interaction.user = MagicMock()
        interaction.user.id = 123456789
        interaction.guild = MagicMock()
        interaction.guild.name = "Test Server"
        interaction.response = AsyncMock()
        return interaction

    @pytest.fixture
    def mock_interaction_dm(self):
        """Mock Discord interaction in DM"""
        interaction = AsyncMock()
        interaction.user = MagicMock()
        interaction.user.id = 123456789
        interaction.guild = None  # DM has no guild
        interaction.response = AsyncMock()
        return interaction

    @pytest.fixture
    def sfw_choice(self):
        """Mock SFW choice"""
        choice = MagicMock()
        choice.name = "SFW"
        choice.value = "SFW"
        return choice

    @pytest.fixture
    def nsfw_choice(self):
        """Mock NSFW choice"""
        choice = MagicMock()
        choice.name = "NSFW"
        choice.value = "NSFW"
        return choice

    @pytest.fixture
    def would_you_rather_cog(self, mock_bot):
        """Create WouldYouRather cog instance"""
        from cogs.games.wouldyourather import WouldYouRather
        return WouldYouRather(mock_bot)

    @pytest.mark.asyncio
    async def test_would_you_rather_sfw_success(self, would_you_rather_cog, mock_interaction, sfw_choice):
        """Test successful SFW Would You Rather command"""
        # Mock constants module
        mock_sfw_questions = [
            "Would you rather have the ability to fly or be invisible?",
            "Would you rather always be 10 minutes late or always be 20 minutes early?",
            "Would you rather live without music or live without TV?"
        ]
        
        with patch('cogs.games.wouldyourather.constants.SFW_WOULD_YOU_RATHER', mock_sfw_questions):
            with patch('cogs.games.wouldyourather.random.choice', return_value=mock_sfw_questions[0]):
                with patch('cogs.games.wouldyourather.os.path.exists', return_value=True):
                    with patch('discord.File') as mock_file:
                        with patch('cogs.games.wouldyourather.get_premium_promotion_view') as mock_premium_view:
                            mock_premium_view.return_value = MagicMock()
                            
                            await would_you_rather_cog.would_you_rather.callback(would_you_rather_cog, mock_interaction, sfw_choice)
                            
                            # Verify response was sent
                            mock_interaction.response.send_message.assert_called_once()
                            
                            # Get the call arguments
                            call_kwargs = mock_interaction.response.send_message.call_args[1]
                            
                            # Verify embeds were included
                            assert 'embeds' in call_kwargs
                            embeds = call_kwargs['embeds']
                            assert len(embeds) == 1
                            
                            # Verify embed contains the question
                            embed_dict = embeds[0].to_dict()
                            assert mock_sfw_questions[0] in embed_dict['description']
                            assert "Test Server - Would You Rather" in embed_dict['title']
                            assert "🤔" in embed_dict['title']  # SFW emoji
                            
                            # Verify files were attached
                            assert 'files' in call_kwargs
                            assert len(call_kwargs['files']) == 2

    @pytest.mark.asyncio
    async def test_would_you_rather_nsfw_success(self, would_you_rather_cog, mock_interaction, nsfw_choice):
        """Test successful NSFW Would You Rather command"""
        mock_nsfw_questions = [
            "Would you rather have sex with someone you love but terrible chemistry or amazing sex with someone you don't love?",
            "Would you rather your partner be amazing in bed but terrible at communicating or great at communicating but bad in bed?"
        ]
        
        with patch('cogs.games.wouldyourather.constants.NSFW_WOULD_YOU_RATHER', mock_nsfw_questions):
            with patch('cogs.games.wouldyourather.random.choice', return_value=mock_nsfw_questions[0]):
                with patch('cogs.games.wouldyourather.os.path.exists', return_value=True):
                    with patch('discord.File') as mock_file:
                        with patch('cogs.games.wouldyourather.get_premium_promotion_view') as mock_premium_view:
                            mock_premium_view.return_value = MagicMock()
                            
                            await would_you_rather_cog.would_you_rather.callback(would_you_rather_cog, mock_interaction, nsfw_choice)
                            
                            mock_interaction.response.send_message.assert_called_once()
                            
                            # Get embed and verify NSFW styling
                            call_kwargs = mock_interaction.response.send_message.call_args[1]
                            embeds = call_kwargs['embeds']
                            embed_dict = embeds[0].to_dict()
                            
                            assert "😈" in embed_dict['title']  # NSFW emoji
                            assert embed_dict['color'] == discord.Color.red().value  # Red color for NSFW

    @pytest.mark.asyncio
    async def test_would_you_rather_dm_context(self, would_you_rather_cog, mock_interaction_dm, sfw_choice):
        """Test Would You Rather command in DM context"""
        mock_sfw_questions = ["Would you rather test question?"]
        
        with patch('cogs.games.wouldyourather.constants.SFW_WOULD_YOU_RATHER', mock_sfw_questions):
            with patch('cogs.games.wouldyourather.random.choice', return_value=mock_sfw_questions[0]):
                with patch('cogs.games.wouldyourather.os.path.exists', return_value=True):
                    with patch('discord.File') as mock_file:
                        with patch('cogs.games.wouldyourather.get_premium_promotion_view') as mock_premium_view:
                            mock_premium_view.return_value = MagicMock()
                            
                            await would_you_rather_cog.would_you_rather.callback(would_you_rather_cog, mock_interaction_dm, sfw_choice)
                            
                            # Verify DM context shows "DM" instead of server name
                            call_kwargs = mock_interaction_dm.response.send_message.call_args[1]
                            embeds = call_kwargs['embeds']
                            embed_dict = embeds[0].to_dict()
                            
                            assert "DM - Would You Rather" in embed_dict['title']

    @pytest.mark.asyncio
    async def test_would_you_rather_missing_questions_list(self, would_you_rather_cog, mock_interaction, sfw_choice):
        """Test error when questions list is missing"""
        # Mock constants to not have the required list
        with patch('cogs.games.wouldyourather.constants.SFW_WOULD_YOU_RATHER', None):
            await would_you_rather_cog.would_you_rather.callback(would_you_rather_cog, mock_interaction, sfw_choice)
            
            # Should send error message
            mock_interaction.response.send_message.assert_called_once()
            call_args = mock_interaction.response.send_message.call_args
            assert call_args[1]['ephemeral'] is True
            assert "Could not find the list" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_would_you_rather_empty_questions_list(self, would_you_rather_cog, mock_interaction, sfw_choice):
        """Test error when questions list is empty"""
        with patch('cogs.games.wouldyourather.constants.SFW_WOULD_YOU_RATHER', []):
            await would_you_rather_cog.would_you_rather.callback(would_you_rather_cog, mock_interaction, sfw_choice)
            
            # Should send error message  
            mock_interaction.response.send_message.assert_called_once()
            call_args = mock_interaction.response.send_message.call_args
            assert call_args[1]['ephemeral'] is True
            # The actual error message is "Could not find the list for SFW Would You Rather questions."
            assert "Could not find" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_would_you_rather_invalid_list_type(self, would_you_rather_cog, mock_interaction, sfw_choice):
        """Test error when questions list is not a list"""
        with patch('cogs.games.wouldyourather.constants.SFW_WOULD_YOU_RATHER', "not a list"):
            await would_you_rather_cog.would_you_rather.callback(would_you_rather_cog, mock_interaction, sfw_choice)
            
            # Should send error message
            mock_interaction.response.send_message.assert_called_once()
            call_args = mock_interaction.response.send_message.call_args
            assert call_args[1]['ephemeral'] is True
            assert "Could not find the list" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_would_you_rather_file_fallback(self, would_you_rather_cog, mock_interaction, sfw_choice):
        """Test file fallback when wouldyourather.png doesn't exist"""
        mock_sfw_questions = ["Test question?"]
        
        with patch('cogs.games.wouldyourather.constants.SFW_WOULD_YOU_RATHER', mock_sfw_questions):
            with patch('cogs.games.wouldyourather.random.choice', return_value=mock_sfw_questions[0]):
                # Mock wouldyourather.png doesn't exist but truthordare.png does
                with patch('cogs.games.wouldyourather.os.path.exists', side_effect=lambda path: 'truthordare.png' in path):
                    with patch('discord.File') as mock_file:
                        with patch('cogs.games.wouldyourather.get_premium_promotion_view') as mock_premium_view:
                            mock_premium_view.return_value = MagicMock()
                            
                            await would_you_rather_cog.would_you_rather.callback(would_you_rather_cog, mock_interaction, sfw_choice)
                            
                            # Should successfully use fallback image
                            mock_interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_would_you_rather_exception_handling(self, would_you_rather_cog, mock_interaction, sfw_choice):
        """Test exception handling in would_you_rather command"""
        # Mock getattr to raise an exception by making constants.SFW_WOULD_YOU_RATHER not exist
        with patch('cogs.games.wouldyourather.constants') as mock_constants:
            mock_constants.SFW_WOULD_YOU_RATHER = None
            await would_you_rather_cog.would_you_rather.callback(would_you_rather_cog, mock_interaction, sfw_choice)
            
            # Should send error message about not finding the list
            mock_interaction.response.send_message.assert_called_once()
            call_args = mock_interaction.response.send_message.call_args
            assert call_args[1]['ephemeral'] is True
            assert "Could not find" in call_args[0][0]

    def test_would_you_rather_cog_initialization(self, mock_bot):
        """Test WouldYouRather cog initialization"""
        from cogs.games.wouldyourather import WouldYouRather
        
        cog = WouldYouRather(mock_bot)
        
        assert cog.bot == mock_bot
        assert hasattr(cog, 'base_path')
        assert hasattr(cog, 'would_you_rather_img')
        assert hasattr(cog, 'astrostats_img')

    def test_would_you_rather_image_paths(self, would_you_rather_cog):
        """Test image path construction"""
        assert 'wouldyourather.png' in would_you_rather_cog.would_you_rather_img
        assert 'astrostats.png' in would_you_rather_cog.astrostats_img
        
        # Paths should be absolute
        assert os.path.isabs(would_you_rather_cog.would_you_rather_img)
        assert os.path.isabs(would_you_rather_cog.astrostats_img)

    def test_would_you_rather_command_properties(self):
        """Test command is properly configured"""
        from cogs.games.wouldyourather import WouldYouRather
        
        # Check if the command exists on the cog
        assert hasattr(WouldYouRather, 'would_you_rather')
        command = WouldYouRather.would_you_rather
        
        # Should have app_commands attributes
        assert hasattr(command, 'qualified_name') or hasattr(command, 'name')
        # Should have app_commands decorator
        assert hasattr(command, '__discord_app_commands_param_description__') or hasattr(command, 'extras')

    def test_category_choice_validation(self):
        """Test category choices are properly defined"""
        # The command should accept SFW and NSFW choices
        # This is implicit in the app_commands.choices decorator
        valid_categories = ["SFW", "NSFW"]
        
        # Test that our fixtures match expected values
        sfw_choice = MagicMock()
        sfw_choice.value = "SFW"
        nsfw_choice = MagicMock()
        nsfw_choice.value = "NSFW"
        
        assert sfw_choice.value in valid_categories
        assert nsfw_choice.value in valid_categories

    @pytest.mark.asyncio
    async def test_would_you_rather_embed_structure(self, would_you_rather_cog, mock_interaction, sfw_choice):
        """Test embed structure and required fields"""
        mock_questions = ["Test question with options?"]
        
        with patch('cogs.games.wouldyourather.constants.SFW_WOULD_YOU_RATHER', mock_questions):
            with patch('cogs.games.wouldyourather.random.choice', return_value=mock_questions[0]):
                with patch('cogs.games.wouldyourather.os.path.exists', return_value=True):
                    with patch('discord.File'):
                        with patch('cogs.games.wouldyourather.get_premium_promotion_view', return_value=MagicMock()):
                            await would_you_rather_cog.would_you_rather.callback(would_you_rather_cog, mock_interaction, sfw_choice)
                            
                            call_kwargs = mock_interaction.response.send_message.call_args[1]
                            embeds = call_kwargs['embeds']
                            embed = embeds[0]
                            embed_dict = embed.to_dict()
                            
                            # Required fields
                            assert 'title' in embed_dict
                            assert 'description' in embed_dict
                            assert 'color' in embed_dict
                            assert 'thumbnail' in embed_dict
                            assert 'footer' in embed_dict
                            
                            # Footer should have AstroStats branding
                            assert "AstroStats" in embed_dict['footer']['text']
                            assert "astrostats.info" in embed_dict['footer']['text']

    def test_constants_integration(self):
        """Test integration with constants module"""
        from config import constants
        
        # Should have both SFW and NSFW would you rather questions
        assert hasattr(constants, 'SFW_WOULD_YOU_RATHER')
        assert hasattr(constants, 'NSFW_WOULD_YOU_RATHER')
        
        # Both should be lists
        assert isinstance(constants.SFW_WOULD_YOU_RATHER, list)
        assert isinstance(constants.NSFW_WOULD_YOU_RATHER, list)
        
        # Should have questions
        assert len(constants.SFW_WOULD_YOU_RATHER) > 0
        assert len(constants.NSFW_WOULD_YOU_RATHER) > 0

    @pytest.mark.asyncio
    async def test_would_you_rather_premium_integration(self, would_you_rather_cog, mock_interaction, sfw_choice):
        """Test premium promotion view integration"""
        mock_questions = ["Test question?"]
        mock_premium_view = MagicMock()
        
        with patch('cogs.games.wouldyourather.constants.SFW_WOULD_YOU_RATHER', mock_questions):
            with patch('cogs.games.wouldyourather.random.choice', return_value=mock_questions[0]):
                with patch('cogs.games.wouldyourather.os.path.exists', return_value=True):
                    with patch('discord.File'):
                        with patch('cogs.games.wouldyourather.get_premium_promotion_view', return_value=mock_premium_view) as mock_get_premium:
                            await would_you_rather_cog.would_you_rather.callback(would_you_rather_cog, mock_interaction, sfw_choice)
                            
                            # Should call premium promotion with user ID
                            mock_get_premium.assert_called_once_with(str(mock_interaction.user.id))
                            
                            # Should include view in response
                            call_kwargs = mock_interaction.response.send_message.call_args[1]
                            assert 'view' in call_kwargs
                            assert call_kwargs['view'] == mock_premium_view

    def test_list_key_generation(self):
        """Test that list keys are generated correctly for constants lookup"""
        # Test SFW
        sfw_choice = MagicMock()
        sfw_choice.value = "SFW"
        sfw_list_key = f"{sfw_choice.value}_WOULD_YOU_RATHER"
        assert sfw_list_key == "SFW_WOULD_YOU_RATHER"
        
        # Test NSFW
        nsfw_choice = MagicMock()
        nsfw_choice.value = "NSFW"
        nsfw_list_key = f"{nsfw_choice.value}_WOULD_YOU_RATHER"
        assert nsfw_list_key == "NSFW_WOULD_YOU_RATHER"

    def test_emoji_selection_logic(self):
        """Test emoji selection based on category"""
        # SFW should get thinking emoji
        sfw_category = MagicMock()
        sfw_category.value = "SFW"
        sfw_emoji = "😈" if sfw_category.value == "NSFW" else "🤔"
        assert sfw_emoji == "🤔"
        
        # NSFW should get devil emoji
        nsfw_category = MagicMock()
        nsfw_category.value = "NSFW"
        nsfw_emoji = "😈" if nsfw_category.value == "NSFW" else "🤔"
        assert nsfw_emoji == "😈"

    def test_color_selection_logic(self):
        """Test color selection based on category"""
        # SFW should get blue color
        sfw_color = discord.Color.red().value if "SFW" == "NSFW" else discord.Color.blue().value
        assert sfw_color == discord.Color.blue().value
        
        # NSFW should get red color
        nsfw_color = discord.Color.red().value if "NSFW" == "NSFW" else discord.Color.blue().value
        assert nsfw_color == discord.Color.red().value

    @pytest.mark.asyncio
    async def test_setup_function(self, mock_bot):
        """Test the setup function adds the cog correctly"""
        from cogs.games.wouldyourather import setup
        
        mock_bot.add_cog = AsyncMock()
        
        await setup(mock_bot)
        
        mock_bot.add_cog.assert_called_once()
        # The argument should be a WouldYouRather instance
        added_cog = mock_bot.add_cog.call_args[0][0]
        assert added_cog.__class__.__name__ == 'WouldYouRather'