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
        
        # Check that all command categories are present
        commands_field = next(field for field in embed.fields if field.name == "Commands & Usage")
        assert "Apex Legends Lifetime Stats" in commands_field.value
        assert "LoL Player Stats" in commands_field.value
        assert "TFT Player Stats" in commands_field.value
        assert "Fortnite Player Stats" in commands_field.value
        assert "Horoscope" in commands_field.value
        assert "Pet Battles" in commands_field.value
        assert "Squib Games" in commands_field.value
        assert "Catfight PvP" in commands_field.value
        assert "Premium" in commands_field.value
        assert "Support" in commands_field.value
        
        # Check command examples
        assert "/apex <platform> <username>" in commands_field.value
        assert "/league profile" in commands_field.value
        assert "/tft <Summoner#0001>" in commands_field.value
        assert "/fortnite <time> <name>" in commands_field.value
        assert "/horoscope <sign>" in commands_field.value
        assert "/petbattles summon" in commands_field.value
        assert "/squibgames start" in commands_field.value
        assert "/catfight @user" in commands_field.value
        assert "/premium" in commands_field.value
        assert "/feedback" in commands_field.value
        assert "/bug" in commands_field.value

    def test_help_embed_fields(self, help_cog):
        embed = help_cog.build_help_embed()
        
        field_names = [field.name for field in embed.fields]
        assert "Commands & Usage" in field_names
        assert "Check Out My Other Apps" in field_names
        assert "Support" in field_names
        
        # Check specific field content
        apps_field = next(field for field in embed.fields if field.name == "Check Out My Other Apps")
        assert "ClutchGG.LOL" in apps_field.value
        assert "https://clutchgg.lol" in apps_field.value
        
        support_field = next(field for field in embed.fields if field.name == "Support")
        assert "astrostats.info" in support_field.value

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
        commands_field = next(field for field in embed.fields if field.name == "Commands & Usage")
        
        # Verify all pet battle commands are mentioned
        pet_commands = [
            "/petbattles summon",
            "/petbattles battle", 
            "/petbattles stats",
            "/petbattles quests",
            "/petbattles achievements",
            "/petbattles leaderboard",
            "/petbattles vote"
        ]
        
        for command in pet_commands:
            assert command in commands_field.value

    def test_guild_count_integration(self, mock_bot):
        # Test with different guild counts
        test_counts = [0, 1, 10, 100, 1000]
        
        for count in test_counts:
            mock_bot.guilds = [MagicMock() for _ in range(count)]
            cog = HelpCog(mock_bot)
            embed = cog.build_help_embed()
            assert f"Trusted by {count} servers" in embed.title