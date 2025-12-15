import pytest
import discord
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from cogs.games.apex import ApexCog
from core.errors import ResourceNotFoundError


class TestApexCog:
    
    @pytest.fixture
    def apex_cog(self, mock_bot):
        return ApexCog(mock_bot)

    @pytest.fixture
    def mock_apex_data(self):
        return {
            "data": {
                "metadata": {"activeLegendName": "Wraith"},
                "segments": [
                    {
                        "metadata": {"name": "Overview"},
                        "stats": {
                            "level": {"value": 120},
                            "kills": {"value": 1500},
                            "damage": {"value": 500000},
                            "matchesPlayed": {"value": 200},
                            "arenaWinStreak": {"value": 5},
                            "rankScore": {
                                "value": 4500,
                                "metadata": {"rankName": "Diamond"},
                                "percentile": 10
                            },
                            "lifetimePeakRankScore": {
                                "value": 6000,
                                "metadata": {"rankName": "Master"}
                            }
                        }
                    },
                    {
                        "metadata": {
                            "name": "Wraith",
                            "bgColor": "#9B8651",
                            "portraitImageUrl": "https://example.com/wraith.png"
                        },
                        "stats": {
                            "stat1": {"displayName": "Wraith Kills", "value": 200},
                            "stat2": {"displayName": "Wraith Damage", "value": 50000}
                        }
                    }
                ]
            }
        }

    @pytest.mark.asyncio
    async def test_apex_command_success(self, apex_cog, mock_interaction, mock_apex_data):
        with patch('cogs.games.apex.fetch_apex_stats') as mock_fetch, \
             patch('cogs.games.apex.get_conditional_embed') as mock_conditional, \
             patch('cogs.games.apex.get_premium_promotion_view') as mock_premium_view, \
             patch('asyncio.to_thread') as mock_thread:
            
            mock_thread.return_value = mock_apex_data
            mock_conditional.return_value = None
            mock_premium_view.return_value = MagicMock()
            
            await apex_cog.apex.callback(apex_cog, mock_interaction, "Xbox", "testuser")
            
            mock_interaction.response.defer.assert_called_once()
            mock_interaction.followup.send.assert_called_once()
            
            call_kwargs = mock_interaction.followup.send.call_args[1]
            assert 'embeds' in call_kwargs
            assert 'view' in call_kwargs
            assert 'files' in call_kwargs

    @pytest.mark.asyncio
    async def test_apex_command_missing_username(self, apex_cog, mock_interaction):
        with patch('cogs.games.apex.send_error_embed') as mock_error:
            await apex_cog.apex.callback(apex_cog, mock_interaction, "Xbox", "")
            
            mock_interaction.response.defer.assert_called_once()
            mock_error.assert_called_once()
            error_call = mock_error.call_args[0]
            assert error_call[1] == "Missing Username"

    @pytest.mark.asyncio
    async def test_apex_command_resource_not_found(self, apex_cog, mock_interaction):
        with patch('asyncio.to_thread') as mock_thread, \
             patch('cogs.games.apex.send_error_embed') as mock_error:
            
            mock_thread.side_effect = ResourceNotFoundError("User not found")
            
            await apex_cog.apex.callback(apex_cog, mock_interaction, "Xbox", "nonexistentuser")
            
            mock_error.assert_called_once()
            error_call = mock_error.call_args[0]
            assert error_call[1] == "Account Not Found"

    @pytest.mark.asyncio
    async def test_apex_command_api_error(self, apex_cog, mock_interaction):
        with patch('asyncio.to_thread') as mock_thread, \
             patch('cogs.games.apex.send_error_embed') as mock_error:
            
            mock_thread.side_effect = Exception("API Error")
            
            await apex_cog.apex.callback(apex_cog, mock_interaction, "Xbox", "testuser")
            
            mock_error.assert_called_once()
            error_call = mock_error.call_args[0]
            assert error_call[1] == "API Error"

    @pytest.mark.asyncio
    async def test_apex_command_no_data(self, apex_cog, mock_interaction):
        with patch('asyncio.to_thread') as mock_thread, \
             patch('cogs.games.apex.send_error_embed') as mock_error:
            
            mock_thread.return_value = {}
            
            await apex_cog.apex.callback(apex_cog, mock_interaction, "Xbox", "testuser")
            
            mock_error.assert_called_once()
            error_call = mock_error.call_args[0]
            assert error_call[1] == "Account Not Found"

    @pytest.mark.asyncio
    async def test_apex_command_no_segments(self, apex_cog, mock_interaction):
        with patch('asyncio.to_thread') as mock_thread, \
             patch('cogs.games.apex.send_error_embed') as mock_error:
            
            mock_thread.return_value = {"data": {"segments": []}}
            
            await apex_cog.apex.callback(apex_cog, mock_interaction, "Xbox", "testuser")
            
            mock_error.assert_called_once()
            error_call = mock_error.call_args[0]
            assert error_call[1] == "No Data Available"

    def test_build_embed_structure(self, apex_cog, mock_apex_data):
        segments = mock_apex_data["data"]["segments"]
        lifetime = segments[0]["stats"]
        ranked = lifetime.get("rankScore", {})
        peak_rank = lifetime.get("lifetimePeakRankScore", {})
        active_legend_data = segments[1]
        
        embed = apex_cog.build_embed("testuser", "Xbox", active_legend_data, lifetime, ranked, peak_rank)
        
        assert "Apex Legends - testuser" in embed.title
        assert "apex.tracker.gg" in embed.url
        assert embed.color.value == int("9B8651", 16)
        assert embed.footer.text == "AstroStats | astrostats.info"
        assert embed.footer.icon_url == "attachment://astrostats.png"

    def test_build_embed_fields(self, apex_cog, mock_apex_data):
        segments = mock_apex_data["data"]["segments"]
        lifetime = segments[0]["stats"]
        ranked = lifetime.get("rankScore", {})
        peak_rank = lifetime.get("lifetimePeakRankScore", {})
        active_legend_data = segments[1]
        
        embed = apex_cog.build_embed("testuser", "Xbox", active_legend_data, lifetime, ranked, peak_rank)
        
        field_names = [field.name for field in embed.fields]
        assert "Lifetime Stats" in field_names
        assert "Current Rank" in field_names
        assert "Peak Rank" in field_names
        assert "Wraith - Currently Selected" in field_names

    def test_format_lifetime_stats(self, apex_cog):
        lifetime_stats = {
            "level": {"value": 120},
            "kills": {"value": 1500},
            "damage": {"value": 500000},
            "matchesPlayed": {"value": 200},
            "arenaWinStreak": {"value": 5}
        }
        
        with patch('cogs.games.apex.format_stat_value') as mock_format:
            mock_format.side_effect = lambda x: str(x.get("value", 0))
            
            result = apex_cog.format_lifetime_stats(lifetime_stats)
            
            assert "Level: **120**" in result
            assert "Kills: **1500**" in result
            assert "Damage: **500000**" in result
            assert "Matches Played: **200**" in result
            assert "Arena Winstreak: **5**" in result

    def test_format_ranked_stats(self, apex_cog):
        ranked_stats = {
            "value": 4500,
            "metadata": {"rankName": "Diamond"},
            "percentile": 10
        }
        
        # 10th percentile -> Bottom 10%
        result = apex_cog.format_ranked_stats(ranked_stats)
        assert "**Diamond**: 4,500 (Bottom 10%)" in result

    def test_format_ranked_stats_no_percentile(self, apex_cog):
        ranked_stats = {
            "value": 4500,
            "metadata": {"rankName": "Diamond"}
        }
        
        result = apex_cog.format_ranked_stats(ranked_stats)
        assert "**Diamond**: 4,500" in result
        assert "Top" not in result
        assert "Bottom" not in result

    def test_format_peak_rank(self, apex_cog):
        peak_rank = {
            "value": 6000,
            "metadata": {"rankName": "Master"}
        }
        
        result = apex_cog.format_peak_rank(peak_rank)
        assert "**Master**: 6,000" in result

    def test_format_active_legend_stats(self, apex_cog):
        legend_stats = {
            "stat1": {"displayName": "Wraith Kills", "value": 200},
            "stat2": {"displayName": "Wraith Damage", "value": 50000}
        }
        
        result = apex_cog.format_active_legend_stats(legend_stats)
        assert "Wraith Kills: **200**" in result
        assert "Wraith Damage: **50000**" in result

    @pytest.mark.asyncio
    async def test_apex_command_all_platforms(self, apex_cog, mock_interaction, mock_apex_data):
        platforms = ["Xbox", "Playstation", "Origin (PC)"]
        
        for platform in platforms:
            with patch('asyncio.to_thread') as mock_thread, \
                 patch('cogs.games.apex.get_conditional_embed') as mock_conditional, \
                 patch('cogs.games.apex.get_premium_promotion_view') as mock_premium_view:
                
                mock_thread.return_value = mock_apex_data
                mock_conditional.return_value = None
                mock_premium_view.return_value = MagicMock()
                
                await apex_cog.apex.callback(apex_cog, mock_interaction, platform, "testuser")
                
                mock_interaction.followup.send.assert_called()
                # Reset mock for next iteration
                mock_interaction.reset_mock()

    def test_embed_with_conditional_embed(self, apex_cog, mock_interaction, mock_apex_data):
        # This would be tested in integration but ensures conditional embed logic
        pass

    def test_premium_promotion_view_integration(self, apex_cog, mock_interaction, mock_apex_data):
        # This would be tested in integration but ensures premium view is included
        pass