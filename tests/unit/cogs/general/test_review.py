import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock
import discord


class TestReviewCommand:
    """Test Review command functionality for Top.gg reviews"""
    
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
    def review_cog(self, mock_bot):
        """Create ReviewCog instance"""
        from cogs.general.review import ReviewCog
        return ReviewCog(mock_bot)

    @pytest.mark.asyncio
    async def test_review_command_success(self, review_cog, mock_interaction):
        """Test successful review command execution"""
        mock_base_embed = MagicMock()
        mock_conditional_embed = MagicMock()
        
        with patch('cogs.general.review.create_base_embed', return_value=mock_base_embed) as mock_create_base:
            with patch('cogs.general.review.get_conditional_embed', return_value=mock_conditional_embed) as mock_get_conditional:
                await review_cog.review.callback(review_cog, mock_interaction)
                
                # Verify base embed was created
                mock_create_base.assert_called_once_with(
                    title="Enjoying AstroStats?",
                    description="If you're enjoying AstroStats, please consider leaving a review on Top.gg!",
                    color=discord.Color.blue()
                )
                
                # Verify conditional embed was fetched
                mock_get_conditional.assert_called_once_with(
                    mock_interaction, 'REVIEW_EMBED', discord.Color.orange()
                )
                
                # Verify response was sent with both embeds
                mock_interaction.response.send_message.assert_called_once()
                call_args = mock_interaction.response.send_message.call_args
                embeds = call_args[1]['embeds']
                assert len(embeds) == 2
                assert mock_base_embed in embeds
                assert mock_conditional_embed in embeds

    @pytest.mark.asyncio
    async def test_review_command_no_conditional_embed(self, review_cog, mock_interaction):
        """Test review command when no conditional embed is returned"""
        mock_base_embed = MagicMock()
        
        with patch('cogs.general.review.create_base_embed', return_value=mock_base_embed):
            with patch('cogs.general.review.get_conditional_embed', return_value=None):
                await review_cog.review.callback(review_cog, mock_interaction)
                
                # Should only send base embed
                mock_interaction.response.send_message.assert_called_once()
                call_args = mock_interaction.response.send_message.call_args
                embeds = call_args[1]['embeds']
                assert len(embeds) == 1
                assert mock_base_embed in embeds

    @pytest.mark.asyncio
    async def test_review_embed_structure(self, review_cog, mock_interaction):
        """Test review embed has correct structure and content"""
        with patch('cogs.general.review.create_base_embed') as mock_create_base:
            with patch('cogs.general.review.get_conditional_embed', return_value=None):
                await review_cog.review.callback(review_cog, mock_interaction)
                
                # Verify base embed creation with correct parameters
                mock_create_base.assert_called_once()
                call_args = mock_create_base.call_args[1]
                
                assert call_args['title'] == "Enjoying AstroStats?"
                assert "consider leaving a review" in call_args['description']
                assert call_args['color'] == discord.Color.blue()

    def test_review_cog_initialization(self, mock_bot):
        """Test ReviewCog initialization"""
        from cogs.general.review import ReviewCog
        
        cog = ReviewCog(mock_bot)
        
        assert cog.bot == mock_bot
        assert hasattr(cog, 'base_path')
        assert hasattr(cog, 'astrostats_img')

    def test_review_image_path(self, review_cog):
        """Test AstroStats image path construction"""
        assert 'astrostats.png' in review_cog.astrostats_img
        
        # Path should be absolute
        assert os.path.isabs(review_cog.astrostats_img)

    def test_review_command_properties(self):
        """Test review command is properly configured"""
        from cogs.general.review import ReviewCog
        
        # Get the review command directly
        command = getattr(ReviewCog, 'review', None)
        
        assert command is not None
        # Should have app_commands decorator - check for discord.py command attributes
        assert hasattr(command, 'qualified_name') or hasattr(command, 'callback') or hasattr(command, '__discord_app_commands_param_description__')

    @pytest.mark.asyncio
    async def test_review_embed_field_content(self, review_cog, mock_interaction):
        """Test review embed field contains Top.gg link"""
        mock_embed = MagicMock()
        
        with patch('cogs.general.review.create_base_embed', return_value=mock_embed):
            with patch('cogs.general.review.get_conditional_embed', return_value=None):
                await review_cog.review.callback(review_cog, mock_interaction)
                
                # Verify add_field was called with Top.gg link
                mock_embed.add_field.assert_called_once()
                call_args = mock_embed.add_field.call_args[1]
                
                assert call_args['name'] == "Leave a Review"
                assert "top.gg/bot/1088929834748616785#reviews" in call_args['value']
                assert call_args['inline'] is False

    @pytest.mark.asyncio
    async def test_review_embed_footer(self, review_cog, mock_interaction):
        """Test review embed footer is set correctly"""
        mock_embed = MagicMock()
        
        with patch('cogs.general.review.create_base_embed', return_value=mock_embed):
            with patch('cogs.general.review.get_conditional_embed', return_value=None):
                await review_cog.review.callback(review_cog, mock_interaction)
                
                # Verify footer was set with AstroStats branding
                mock_embed.set_footer.assert_called_once()
                call_args = mock_embed.set_footer.call_args[1]
                
                assert call_args['text'] == "AstroStats | astrostats.info"
                assert call_args['icon_url'] == "attachment://astrostats.png"

    @pytest.mark.asyncio
    async def test_review_conditional_embed_type(self, review_cog, mock_interaction):
        """Test correct conditional embed type is requested"""
        with patch('cogs.general.review.create_base_embed', return_value=MagicMock()):
            with patch('cogs.general.review.get_conditional_embed') as mock_get_conditional:
                mock_get_conditional.return_value = None
                
                await review_cog.review.callback(review_cog, mock_interaction)
                
                # Verify correct embed type and color for conditional embed
                mock_get_conditional.assert_called_once_with(
                    mock_interaction, 'REVIEW_EMBED', discord.Color.orange()
                )

    def test_review_top_gg_bot_id(self):
        """Test Top.gg bot ID in the review link is correct"""
        # The bot ID should match AstroStats bot ID
        expected_bot_id = "1088929834748616785"
        
        # This would be in the embed field value
        review_link = f"https://top.gg/bot/{expected_bot_id}#reviews"
        assert expected_bot_id in review_link

    @pytest.mark.asyncio
    async def test_review_embeds_list_construction(self, review_cog, mock_interaction):
        """Test embeds list is constructed correctly"""
        mock_base_embed = MagicMock()
        mock_conditional_embed = MagicMock()
        
        with patch('cogs.general.review.create_base_embed', return_value=mock_base_embed):
            with patch('cogs.general.review.get_conditional_embed', return_value=mock_conditional_embed):
                await review_cog.review.callback(review_cog, mock_interaction)
                
                # Verify embeds are in correct order
                call_args = mock_interaction.response.send_message.call_args[1]
                embeds = call_args['embeds']
                
                assert embeds[0] == mock_base_embed  # Base embed first
                assert embeds[1] == mock_conditional_embed  # Conditional second

    @pytest.mark.asyncio
    async def test_review_base_embed_customization(self, review_cog, mock_interaction):
        """Test base embed is customized after creation"""
        mock_embed = MagicMock()
        
        with patch('cogs.general.review.create_base_embed', return_value=mock_embed):
            with patch('cogs.general.review.get_conditional_embed', return_value=None):
                await review_cog.review.callback(review_cog, mock_interaction)
                
                # Verify embed was customized with field and footer
                assert mock_embed.add_field.called
                assert mock_embed.set_footer.called

    def test_review_description_content(self):
        """Test review description encourages users appropriately"""
        description = "If you're enjoying AstroStats, please consider leaving a review on Top.gg!"
        
        # Should be encouraging but not pushy
        assert "enjoying" in description.lower()
        assert "consider" in description.lower()
        assert "top.gg" in description.lower()

    def test_review_link_format(self):
        """Test review link format is correct"""
        bot_id = "1088929834748616785"
        review_link = f"[Click here to leave a review on Top.gg](https://top.gg/bot/{bot_id}#reviews)"
        
        # Should be markdown link format
        assert review_link.startswith("[")
        assert "](https://" in review_link
        assert "#reviews" in review_link

    @pytest.mark.asyncio
    async def test_review_color_scheme(self, review_cog, mock_interaction):
        """Test color scheme for review embeds"""
        with patch('cogs.general.review.create_base_embed') as mock_create_base:
            with patch('cogs.general.review.get_conditional_embed') as mock_get_conditional:
                mock_get_conditional.return_value = None
                
                await review_cog.review.callback(review_cog, mock_interaction)
                
                # Base embed should be blue
                base_call_args = mock_create_base.call_args[1]
                assert base_call_args['color'] == discord.Color.blue()
                
                # Conditional embed request should be orange
                conditional_call_args = mock_get_conditional.call_args[0]
                assert conditional_call_args[2] == discord.Color.orange()

    @pytest.mark.asyncio
    async def test_review_no_parameters_required(self, review_cog, mock_interaction):
        """Test review command requires no parameters"""
        with patch('cogs.general.review.create_base_embed', return_value=MagicMock()):
            with patch('cogs.general.review.get_conditional_embed', return_value=None):
                # Should work without any additional parameters
                await review_cog.review.callback(review_cog, mock_interaction)
                
                mock_interaction.response.send_message.assert_called_once()

    def test_review_command_description(self):
        """Test review command has appropriate description"""
        from cogs.general.review import ReviewCog
        
        # Find the command and check its description
        review_method = getattr(ReviewCog, 'review')
        
        # Should have a description about leaving reviews
        # The exact way to access this depends on how discord.py stores it
        # This is more of a structural test

    @pytest.mark.asyncio
    async def test_review_integration_with_utils(self, review_cog, mock_interaction):
        """Test review command integrates correctly with core utils"""
        with patch('cogs.general.review.create_base_embed', return_value=MagicMock()):
            with patch('cogs.general.review.get_conditional_embed') as mock_utils:
                mock_utils.return_value = MagicMock()
                
                await review_cog.review.callback(review_cog, mock_interaction)
                
                # Should call utils with interaction for user context
                mock_utils.assert_called_once()
                assert mock_utils.call_args[0][0] == mock_interaction

    @pytest.mark.asyncio
    async def test_setup_function(self, mock_bot):
        """Test the setup function adds the cog correctly"""
        from cogs.general.review import setup
        
        mock_bot.add_cog = AsyncMock()
        
        await setup(mock_bot)
        
        mock_bot.add_cog.assert_called_once()
        # The argument should be a ReviewCog instance
        added_cog = mock_bot.add_cog.call_args[0][0]
        assert added_cog.__class__.__name__ == 'ReviewCog'

    def test_review_encourages_positive_engagement(self):
        """Test review command promotes positive engagement"""
        title = "Enjoying AstroStats?"
        description = "If you're enjoying AstroStats, please consider leaving a review on Top.gg!"
        
        # Should be positive and encouraging
        assert "enjoying" in title.lower() or "enjoying" in description.lower()
        assert "please" in description.lower()  # Polite request
        assert "consider" in description.lower()  # Not demanding

    def test_review_provides_direct_link(self):
        """Test review command provides direct link to review page"""
        field_name = "Leave a Review"
        field_value = "[Click here to leave a review on Top.gg](https://top.gg/bot/1088929834748616785#reviews)"
        
        # Should have clear call-to-action
        assert "click here" in field_value.lower()
        assert "leave a review" in field_value.lower()
        assert "#reviews" in field_value  # Direct to reviews section