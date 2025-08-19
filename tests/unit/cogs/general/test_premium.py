import pytest
import discord
from unittest.mock import patch, AsyncMock
from cogs.general.premium import PremiumCog, PRICING


class TestPremiumCog:
    
    @pytest.fixture
    def premium_cog(self, mock_bot):
        return PremiumCog(mock_bot)

    @pytest.mark.asyncio
    async def test_premium_command_free_tier(self, premium_cog, mock_interaction, free_tier_user):
        with patch('cogs.general.premium.get_user_entitlements') as mock_get_ent:
            mock_get_ent.return_value = {"tier": "free"}
            
            await premium_cog.premium.callback(premium_cog, mock_interaction)
            
            mock_interaction.response.send_message.assert_called_once()
            call_kwargs = mock_interaction.response.send_message.call_args[1]
            
            assert call_kwargs['ephemeral'] is True
            embed = call_kwargs['embed']
            assert "AstroStats Premium" in embed.title
            assert "Free" in str(embed.fields)

    @pytest.mark.asyncio
    async def test_premium_command_supporter_tier(self, premium_cog, mock_interaction):
        with patch('cogs.general.premium.get_user_entitlements') as mock_get_ent:
            mock_get_ent.return_value = {"tier": "supporter"}
            
            await premium_cog.premium.callback(premium_cog, mock_interaction)
            
            mock_interaction.response.send_message.assert_called_once()
            call_kwargs = mock_interaction.response.send_message.call_args[1]
            
            embed = call_kwargs['embed']
            assert "Supporter" in str(embed.fields)

    @pytest.mark.asyncio
    async def test_premium_command_sponsor_tier(self, premium_cog, mock_interaction):
        with patch('cogs.general.premium.get_user_entitlements') as mock_get_ent:
            mock_get_ent.return_value = {"tier": "sponsor"}
            
            await premium_cog.premium.callback(premium_cog, mock_interaction)
            
            mock_interaction.response.send_message.assert_called_once()
            call_kwargs = mock_interaction.response.send_message.call_args[1]
            
            embed = call_kwargs['embed']
            assert "Sponsor" in str(embed.fields)

    @pytest.mark.asyncio
    async def test_premium_command_vip_tier(self, premium_cog, mock_interaction):
        with patch('cogs.general.premium.get_user_entitlements') as mock_get_ent:
            mock_get_ent.return_value = {"tier": "vip"}
            
            await premium_cog.premium.callback(premium_cog, mock_interaction)
            
            mock_interaction.response.send_message.assert_called_once()
            call_kwargs = mock_interaction.response.send_message.call_args[1]
            
            embed = call_kwargs['embed']
            assert "Vip" in str(embed.fields)

    def test_pricing_structure(self):
        assert "free" in PRICING
        assert "supporter" in PRICING
        assert "sponsor" in PRICING
        assert "vip" in PRICING
        
        # Verify free tier benefits
        free_benefits = PRICING["free"]["benefits"]
        assert "3 daily quests" in free_benefits
        assert "1 pet capacity" in free_benefits
        assert "Standard SquibGames cap" in free_benefits
        
        # Verify supporter tier benefits  
        supporter_benefits = PRICING["supporter"]["benefits"]
        assert "+2 daily quests (total 5)" in supporter_benefits
        assert "SquibGames cap 20" in supporter_benefits
        assert "Premium badge" in supporter_benefits
        assert "Premium-only commands" in supporter_benefits
        assert "1.2x XP & cash" in supporter_benefits
        
        # Verify sponsor tier benefits
        sponsor_benefits = PRICING["sponsor"]["benefits"]
        assert "+5 daily quests (total 8)" in sponsor_benefits
        assert "+1 extra pets (2 total)" in sponsor_benefits
        assert "SquibGames cap 50" in sponsor_benefits
        assert "1.5x XP & cash" in sponsor_benefits
        
        # Verify VIP tier benefits
        vip_benefits = PRICING["vip"]["benefits"]
        assert "+8 daily quests (total 11)" in vip_benefits
        assert "+3 extra pets (4 total)" in vip_benefits
        assert "SquibGames cap 75" in vip_benefits
        assert "1.75x XP & cash" in vip_benefits

    def test_pricing_values(self):
        assert PRICING["free"]["price"] == "£0"
        assert PRICING["supporter"]["price"] == "£3/mo"
        assert PRICING["sponsor"]["price"] == "£5/mo"
        assert PRICING["vip"]["price"] == "£10/mo"

    @pytest.mark.asyncio
    async def test_premium_embed_structure(self, premium_cog, mock_interaction):
        with patch('cogs.general.premium.get_user_entitlements') as mock_get_ent:
            mock_get_ent.return_value = {"tier": "free"}
            
            await premium_cog.premium.callback(premium_cog, mock_interaction)
            
            call_kwargs = mock_interaction.response.send_message.call_args[1]
            embed = call_kwargs['embed']
            
            assert embed.title == "🌟 AstroStats Premium"
            assert embed.color == discord.Color.gold()
            assert "astrostats.info" in embed.description
            assert "Built By Goldiez ❤️" in embed.footer.text
            
            # Check that all tiers are included in fields
            field_names = [field.name for field in embed.fields]
            assert "Your Tier" in field_names
            assert "Free — £0" in field_names
            assert "Supporter — £3/mo" in field_names
            assert "Sponsor — £5/mo" in field_names
            assert "Vip — £10/mo" in field_names
            assert "Get Premium" in field_names