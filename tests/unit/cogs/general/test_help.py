import pytest
import discord
from unittest.mock import patch, AsyncMock, MagicMock
from cogs.general.help import HelpCog


class TestHelpCog:
    
    @pytest.fixture
    def help_cog(self, mock_bot):
        mock_bot.guilds = [MagicMock() for _ in range(5)]  # 5 guilds
        return HelpCog(mock_bot)

    def test_build_help_embed(self, help_cog):
        embed = help_cog.build_help_embed()
        
        assert "AstroStats Help & Support - Trusted by 5 servers" in embed.title
        assert embed.color.value == 0xdd4f7a
        
        # Combine all field values for easier checking
        all_field_content = " ".join([field.value for field in embed.fields])
        
        # Check that all command categories are present
        assert "Apex Legends" in all_field_content
        assert "League of Legends" in all_field_content
        assert "TFT" in all_field_content
        assert "Fortnite" in all_field_content
        assert "Horoscope" in all_field_content
        assert "Pet Battles" in all_field_content
        assert "Squib Games" in all_field_content
        assert "Catfight PvP" in all_field_content
        assert "Welcome System" in all_field_content
        assert "Premium" in all_field_content
        
        # Check command examples
        assert "/apex <platform> <username>" in all_field_content
        assert "/league profile <region> <riotid>" in all_field_content
        assert "/tft <region> <riotid>" in all_field_content
        assert "/fortnite <time> <name>" in all_field_content
        assert "/horoscope <sign>" in all_field_content
        assert "/petbattles summon" in all_field_content
        assert "/squibgames start" in all_field_content
        assert "/catfight @user" in all_field_content
        assert "/welcome toggle" in all_field_content
        assert "/welcome set-message" in all_field_content
        assert "/welcome set-image" in all_field_content
        assert "/premium" in all_field_content
        assert "/issues" in all_field_content
        assert "/support" in all_field_content
        assert "/review" in all_field_content
        assert "/truthordare" in all_field_content
        assert "/wouldyourather" in all_field_content
        assert "/bingo start" in all_field_content
        assert "/astronauts" in all_field_content
        assert "/apod" in all_field_content
        assert "/iss" in all_field_content
        assert "/launch" in all_field_content

    def test_help_embed_fields(self, help_cog):
        embed = help_cog.build_help_embed()
        
        field_names = [field.name for field in embed.fields]
        assert "🎮 Gaming Stats Commands" in field_names
        assert "🎲 Fun & Games" in field_names
        assert "🌌 Space & NASA" in field_names
        assert "⚙️ Server & Premium" in field_names
        assert "💬 Support & Feedback" in field_names
        assert "Check Out My Other Apps" in field_names
        assert "🆘 Need Help?" in field_names
        
        # Check specific field content
        apps_field = next(field for field in embed.fields if field.name == "Check Out My Other Apps")
        assert "ClutchGG.LOL" in apps_field.value
        assert "https://clutchgg.lol" in apps_field.value
        
        support_field = next(field for field in embed.fields if field.name == "🆘 Need Help?")
        assert "astrostats.info" in support_field.value
        assert "/support" in support_field.value
        assert "support center" in support_field.value

    def test_help_embed_footer(self, help_cog):
        embed = help_cog.build_help_embed()
        
        assert embed.footer.text == "AstroStats | astrostats.info"
        assert embed.footer.icon_url == "attachment://astrostats.png"

    @pytest.mark.asyncio
    async def test_help_command_basic(self, help_cog, mock_interaction):
        with patch('cogs.general.help.get_conditional_embed') as mock_conditional, \
             patch('cogs.general.help.get_premium_promotion_view') as mock_premium_view:
            
            mock_conditional.return_value = None
            mock_premium_view.return_value = MagicMock()
            
            await help_cog.help_command.callback(help_cog, mock_interaction)
            
            mock_interaction.response.send_message.assert_called_once()
            call_kwargs = mock_interaction.response.send_message.call_args[1]
            
            assert 'embeds' in call_kwargs
            assert 'view' in call_kwargs
            assert len(call_kwargs['embeds']) == 1
            
            # Verify the embed content
            embed = call_kwargs['embeds'][0]
            assert "AstroStats Help & Support" in embed.title

    @pytest.mark.asyncio
    async def test_help_command_with_conditional_embed(self, help_cog, mock_interaction):
        with patch('cogs.general.help.get_conditional_embed') as mock_conditional, \
             patch('cogs.general.help.get_premium_promotion_view') as mock_premium_view:
            
            conditional_embed = MagicMock()
            mock_conditional.return_value = conditional_embed
            mock_premium_view.return_value = MagicMock()
            
            await help_cog.help_command.callback(help_cog, mock_interaction)
            
            call_kwargs = mock_interaction.response.send_message.call_args[1]
            assert len(call_kwargs['embeds']) == 2
            assert call_kwargs['embeds'][1] == conditional_embed

    @pytest.mark.asyncio 
    async def test_help_command_premium_view(self, help_cog, mock_interaction):
        with patch('cogs.general.help.get_conditional_embed') as mock_conditional, \
             patch('cogs.general.help.get_premium_promotion_view') as mock_premium_view:
            
            mock_conditional.return_value = None
            premium_view = MagicMock()
            mock_premium_view.return_value = premium_view
            
            await help_cog.help_command.callback(help_cog, mock_interaction)
            
            mock_premium_view.assert_called_once_with(str(mock_interaction.user.id))
            call_kwargs = mock_interaction.response.send_message.call_args[1]
            assert call_kwargs['view'] == premium_view

    def test_help_cog_init(self, mock_bot):
        cog = HelpCog(mock_bot)
        assert cog.bot == mock_bot
        assert cog.base_path is not None
        assert cog.astrostats_img.endswith('astrostats.png')

    def test_pet_battles_commands_coverage(self, help_cog):
        embed = help_cog.build_help_embed()
        all_field_content = " ".join([field.value for field in embed.fields])
        
        # Verify all pet battle commands are mentioned (basic + advanced)
        pet_commands = [
            "/petbattles summon",
            "/petbattles pets",
            "/petbattles setactive",
            "/petbattles release",
            "/petbattles battle", 
            "/petbattles stats",
            "/petbattles quests",
            "/petbattles achievements",
            "/petbattles leaderboard",
            "/petbattles globalrank",
            "/petbattles vote",
            "/petbattles shop",
            "/petbattles buy",
            "/petbattles train",
            "/petbattles rename",
            "/petbattles profile",
            "/petbattles daily",
            "/petbattles hunt"
        ]
        
        for command in pet_commands:
            assert command in all_field_content

    def test_guild_count_integration(self, mock_bot):
        # Test with different guild counts
        test_counts = [0, 1, 10, 100, 1000]
        
        for count in test_counts:
            mock_bot.guilds = [MagicMock() for _ in range(count)]
            cog = HelpCog(mock_bot)
            embed = cog.build_help_embed()
            assert f"Trusted by {count} servers" in embed.title

    def test_welcome_commands_coverage(self, help_cog):
        embed = help_cog.build_help_embed()
        server_field = next(field for field in embed.fields if field.name == "⚙️ Server & Premium")
        
        # Verify all welcome commands are mentioned
        welcome_commands = [
            "/welcome toggle",
            "/welcome set-message", 
            "/welcome set-image",
            "/welcome remove-message",
            "/welcome remove-image",
            "/welcome test"
        ]
        
        for command in welcome_commands:
            assert command in server_field.value

    def test_space_nasa_commands_coverage(self, help_cog):
        """Test that all Space & NASA commands are included"""
        embed = help_cog.build_help_embed()
        space_field = next(field for field in embed.fields if field.name == "🌌 Space & NASA")
        
        space_commands = [
            "/apod",
            "/iss",
            "/astronauts",
            "/launch"
        ]
        
        for command in space_commands:
            assert command in space_field.value

    def test_bingo_commands_coverage(self, help_cog):
        """Test that all Bingo commands are included"""
        embed = help_cog.build_help_embed()
        all_field_content = " ".join([field.value for field in embed.fields])
        
        bingo_commands = [
            "/bingo start",
            "/bingo run",
            "/bingo status",
            "/bingo cancel",
            "/bingo stats",
            "/bingo leaderboard"
        ]
        
        for command in bingo_commands:
            assert command in all_field_content

    def test_squib_games_commands_coverage(self, help_cog):
        """Test that all Squib Games commands are included"""
        embed = help_cog.build_help_embed()
        all_field_content = " ".join([field.value for field in embed.fields])
        
        squib_commands = [
            "/squibgames start",
            "/squibgames run",
            "/squibgames status",
            "/squibgames cancel"
        ]
        
        for command in squib_commands:
            assert command in all_field_content

    def test_premium_tagging_in_help(self, help_cog):
        embed = help_cog.build_help_embed()
        server_field = next(field for field in embed.fields if field.name == "⚙️ Server & Premium")
        
        # Check that premium features are properly tagged
        assert "🔒 **Premium**" in server_field.value
        assert "🔒 **Sponsor/VIP**" in server_field.value
        
        # Check admin-only notation
        assert "(Admin Only)" in server_field.value