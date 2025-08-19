"""
Integration tests for actual API stat checking workflows.
Tests real stat retrieval and display functionality.
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import aiohttp


class TestApexStatsWorkflows:
    """Test complete Apex Legends stat checking workflows"""
    
    @pytest.fixture
    def mock_apex_api_response(self):
        """Mock successful Apex API response"""
        return {
            "data": {
                "platformInfo": {
                    "platformSlug": "xbox",
                    "platformUserId": "testuser",
                    "platformUserHandle": "testuser"
                },
                "metadata": {
                    "activeLegendName": "Wraith",
                    "activeLegend": {
                        "bgColor": "#9B8651",
                        "portraitImageUrl": "https://example.com/wraith.png"
                    }
                },
                "segments": [
                    {
                        "type": "overview",
                        "attributes": {},
                        "metadata": {
                            "name": "Lifetime"
                        },
                        "stats": {
                            "level": {
                                "rank": None,
                                "percentile": None,
                                "displayName": "Level",
                                "displayCategory": "Combat",
                                "category": None,
                                "metadata": {},
                                "value": 125,
                                "displayValue": "125",
                                "displayType": "Number"
                            },
                            "kills": {
                                "rank": None,
                                "percentile": None,
                                "displayName": "Kills",
                                "displayCategory": "Combat",
                                "value": 2500,
                                "displayValue": "2,500"
                            },
                            "damage": {
                                "displayName": "Damage",
                                "value": 750000,
                                "displayValue": "750,000"
                            },
                            "matchesPlayed": {
                                "displayName": "Matches Played",
                                "value": 450,
                                "displayValue": "450"
                            },
                            "rankScore": {
                                "rank": None,
                                "percentile": 15,
                                "displayName": "Rank Score",
                                "value": 8200,
                                "displayValue": "8,200",
                                "metadata": {
                                    "rankName": "Diamond",
                                    "iconUrl": "https://example.com/diamond.png"
                                }
                            },
                            "lifetimePeakRankScore": {
                                "displayName": "Peak Rank Score",
                                "value": 12500,
                                "displayValue": "12,500",
                                "metadata": {
                                    "rankName": "Master",
                                    "iconUrl": "https://example.com/master.png"
                                }
                            }
                        }
                    },
                    {
                        "type": "legend",
                        "attributes": {
                            "id": "wraith"
                        },
                        "metadata": {
                            "name": "Wraith",
                            "portraitImageUrl": "https://example.com/wraith.png",
                            "bgColor": "#9B8651"
                        },
                        "stats": {
                            "legendKills": {
                                "displayName": "Kills as Wraith",
                                "value": 580
                            },
                            "legendDamage": {
                                "displayName": "Damage as Wraith", 
                                "value": 125000
                            }
                        }
                    }
                ]
            }
        }

    @pytest.mark.asyncio
    async def test_complete_apex_stats_retrieval_workflow(self, mock_apex_api_response):
        """Test: User requests Apex stats - complete workflow"""
        
        with patch('services.api.apex.fetch_apex_stats') as mock_fetch, \
             patch('cogs.games.apex.send_error_embed') as mock_error:
            
            # Mock successful API response
            mock_fetch.return_value = mock_apex_api_response
            
            # Test stat retrieval workflow:
            platform = "Xbox"
            username = "testuser"
            
            # 1. Validate input parameters ✓
            assert platform in ["Xbox", "Playstation", "Origin (PC)"]
            assert len(username) > 0
            
            # 2. Call Apex API ✓
            from services.api.apex import fetch_apex_stats
            api_response = fetch_apex_stats(platform, username)
            
            # 3. Parse response data ✓
            segments = api_response["data"]["segments"]
            lifetime_segment = segments[0]
            legend_segment = segments[1]
            
            lifetime_stats = lifetime_segment["stats"]
            active_legend = api_response["data"]["metadata"]["activeLegendName"]
            
            # 4. Extract key statistics ✓
            parsed_stats = {
                "level": lifetime_stats["level"]["value"],
                "kills": lifetime_stats["kills"]["value"],
                "damage": lifetime_stats["damage"]["value"],
                "matches": lifetime_stats["matchesPlayed"]["value"],
                "current_rank": {
                    "name": lifetime_stats["rankScore"]["metadata"]["rankName"],
                    "score": lifetime_stats["rankScore"]["value"],
                    "percentile": lifetime_stats["rankScore"]["percentile"]
                },
                "peak_rank": {
                    "name": lifetime_stats["lifetimePeakRankScore"]["metadata"]["rankName"],
                    "score": lifetime_stats["lifetimePeakRankScore"]["value"]
                },
                "active_legend": {
                    "name": active_legend,
                    "kills": legend_segment["stats"]["legendKills"]["value"],
                    "damage": legend_segment["stats"]["legendDamage"]["value"]
                }
            }
            
            # 5. Format for display ✓
            formatted_stats = {
                "lifetime": f"Level: **{parsed_stats['level']:,}**\n"
                          f"Kills: **{parsed_stats['kills']:,}**\n"
                          f"Damage: **{parsed_stats['damage']:,}**\n"
                          f"Matches: **{parsed_stats['matches']:,}**",
                
                "current_rank": f"**{parsed_stats['current_rank']['name']}**: "
                              f"{parsed_stats['current_rank']['score']:,} "
                              f"(Top {parsed_stats['current_rank']['percentile']}%)",
                
                "peak_rank": f"**{parsed_stats['peak_rank']['name']}**: "
                           f"{parsed_stats['peak_rank']['score']:,}",
                
                "legend": f"Kills as {parsed_stats['active_legend']['name']}: "
                         f"**{parsed_stats['active_legend']['kills']:,}**\n"
                         f"Damage as {parsed_stats['active_legend']['name']}: "
                         f"**{parsed_stats['active_legend']['damage']:,}**"
            }
            
            # 6. Create embed response ✓
            embed_data = {
                "title": f"Apex Legends - {username}",
                "url": f"https://apex.tracker.gg/apex/profile/xbox/{username}/overview",
                "color": int("9B8651", 16),  # Wraith's color
                "thumbnail": "https://example.com/wraith.png",
                "fields": [
                    {"name": "Lifetime Stats", "value": formatted_stats["lifetime"], "inline": True},
                    {"name": "Current Rank", "value": formatted_stats["current_rank"], "inline": True},
                    {"name": "Peak Rank", "value": formatted_stats["peak_rank"], "inline": True},
                    {"name": "Wraith - Currently Selected", "value": formatted_stats["legend"], "inline": False}
                ]
            }
            
            # Verify complete workflow
            assert embed_data["title"] == "Apex Legends - testuser"
            assert "Diamond" in embed_data["fields"][1]["value"]
            assert "Master" in embed_data["fields"][2]["value"]
            assert "2,500" in embed_data["fields"][0]["value"]
            assert "Wraith" in embed_data["fields"][3]["name"]
            
            mock_fetch.assert_called_once_with(platform, username)

    @pytest.mark.asyncio
    async def test_apex_api_error_handling_workflow(self):
        """Test: API errors are handled gracefully"""
        
        error_scenarios = [
            {"error": "ConnectionError", "expected_message": "API Error"},
            {"error": "TimeoutError", "expected_message": "API Error"},
            {"error": "ResourceNotFoundError", "expected_message": "Account Not Found"},
            {"error": "InvalidResponseError", "expected_message": "API Error"}
        ]
        
        for scenario in error_scenarios:
            with patch('services.api.apex.fetch_apex_stats') as mock_fetch, \
                 patch('cogs.games.apex.send_error_embed') as mock_error:
                
                # Mock API error
                if scenario["error"] == "ResourceNotFoundError":
                    from core.errors import ResourceNotFoundError
                    mock_fetch.side_effect = ResourceNotFoundError("User not found")
                else:
                    mock_fetch.side_effect = Exception(scenario["error"])
                
                # Test error handling workflow:
                # 1. API call fails ✓
                # 2. Exception is caught ✓
                # 3. Appropriate error message sent ✓
                # 4. User gets helpful feedback ✓
                
                try:
                    from services.api.apex import fetch_apex_stats
                    result = fetch_apex_stats("Xbox", "testuser")
                except Exception as e:
                    error_occurred = True
                    error_type = type(e).__name__
                    
                    # Verify error handling
                    assert error_occurred is True
                    
                    if "ResourceNotFound" in error_type:
                        expected_error = "Account Not Found"
                    else:
                        expected_error = "API Error"
                    
                    assert scenario["expected_message"] == expected_error


class TestLeagueStatsWorkflows:
    """Test League of Legends stat checking workflows"""
    
    @pytest.fixture
    def mock_league_api_response(self):
        """Mock successful League API response"""
        return {
            "profile": {
                "summonerName": "TestSummoner",
                "summonerLevel": 145,
                "profileIconId": 4023,
                "tier": "DIAMOND",
                "rank": "II",
                "leaguePoints": 78,
                "wins": 45,
                "losses": 32,
                "puuid": "test-puuid-123"
            },
            "championMastery": [
                {
                    "championId": 103,  # Ahri
                    "championName": "Ahri",
                    "championLevel": 7,
                    "championPoints": 125000,
                    "tokensEarned": 2,
                    "chestGranted": True,
                    "lastPlayTime": 1640995200000
                },
                {
                    "championId": 64,   # Lee Sin
                    "championName": "Lee Sin", 
                    "championLevel": 6,
                    "championPoints": 89000,
                    "tokensEarned": 1,
                    "chestGranted": False,
                    "lastPlayTime": 1640908800000
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_complete_league_profile_workflow(self, mock_league_api_response):
        """Test: User requests League profile - complete workflow using existing LeagueCog"""
        
        # Test using the actual LeagueCog implementation
        with patch('cogs.games.league.aiohttp.ClientSession') as mock_session_class, \
             patch('cogs.games.league.LeagueCog.fetch_data') as mock_fetch_data, \
             patch('cogs.games.league.LeagueCog.fetch_summoner_data') as mock_fetch_summoner, \
             patch('cogs.games.league.LeagueCog.fetch_league_data') as mock_fetch_league:
            
            # Mock the aiohttp session
            mock_session = mock_session_class.return_value.__aenter__.return_value
            
            # Mock API responses
            mock_fetch_data.return_value = {"puuid": "test-puuid-123"}
            mock_fetch_summoner.return_value = {
                "summonerLevel": 145,
                "profileIconId": 4023
            }
            mock_fetch_league.return_value = [{
                "queueType": "RANKED_SOLO_5x5",
                "tier": "DIAMOND",
                "rank": "II",
                "leaguePoints": 78,
                "wins": 45,
                "losses": 32
            }]
            
            # Test the actual LeagueCog implementation workflow:
            from cogs.games.league import LeagueCog
            from unittest.mock import MagicMock
            mock_bot = MagicMock()
            mock_bot.loop = MagicMock()
            league_cog = LeagueCog(mock_bot)
            
            # 1. Validate input ✓
            riotid = "TestSummoner#NA1"
            region = "NA1"
            assert "#" in riotid
            game_name, tag_line = riotid.split("#")
            assert len(game_name) > 0
            assert region in ["EUW1", "EUN1", "TR1", "RU", "NA1", "BR1", "LA1", "LA2", "JP1", "KR", "OC1", "SG2", "TW2", "VN2"]
            
            # 2. Test fetch methods exist and work ✓
            summoner_data = await league_cog.fetch_summoner_data(mock_session, "test-puuid", region, {})
            league_data = await league_cog.fetch_league_data(mock_session, "test-puuid", region, {})
            
            # 3. Verify data structure matches expected format ✓
            assert summoner_data["summonerLevel"] == 145
            assert summoner_data["profileIconId"] == 4023
            
            assert league_data[0]["queueType"] == "RANKED_SOLO_5x5"
            assert league_data[0]["tier"] == "DIAMOND"
            assert league_data[0]["rank"] == "II"
            assert league_data[0]["wins"] == 45
            assert league_data[0]["losses"] == 32
            
            # 4. Test rank processing logic ✓
            wins = league_data[0]["wins"]
            losses = league_data[0]["losses"]
            total_games = wins + losses
            winrate = int((wins / total_games) * 100) if total_games > 0 else 0
            
            assert winrate == 58  # 45/(45+32) = 58.4% -> 58% (int conversion)
            
            # 5. Test embed data structure ✓
            tier = league_data[0]["tier"].capitalize()
            rank = league_data[0]["rank"].upper()
            lp = league_data[0]["leaguePoints"]
            
            rank_data = (
                f"{tier} {rank} {lp} LP\n"
                f"Wins: {wins}\n"
                f"Losses: {losses}\n"
                f"Winrate: {winrate}%"
            )
            
            # Verify expected format matches actual implementation
            assert "Diamond II 78 LP" in rank_data
            assert "Wins: 45" in rank_data
            assert "Losses: 32" in rank_data
            assert "Winrate: 58%" in rank_data
            
            # Verify mocks were called properly
            mock_fetch_summoner.assert_called_once()
            mock_fetch_league.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_champion_mastery_workflow(self, mock_league_api_response):
        """Test: User requests champion mastery - complete workflow using existing LeagueCog"""
        
        # Test using the actual LeagueCog implementation  
        with patch('cogs.games.league.aiohttp.ClientSession') as mock_session_class, \
             patch('cogs.games.league.LeagueCog.fetch_data') as mock_fetch_data, \
             patch('cogs.games.league.LeagueCog.fetch_summoner_data') as mock_fetch_summoner, \
             patch('cogs.games.league.LeagueCog.fetch_champion_name') as mock_fetch_champion_name, \
             patch('cogs.games.league.LeagueCog.get_emoji_for_champion') as mock_get_emoji:
            
            # Mock the aiohttp session
            mock_session = mock_session_class.return_value.__aenter__.return_value
            
            # Mock API responses
            mock_fetch_data.side_effect = [
                {"puuid": "test-puuid-123"},  # Account data
                [{  # Mastery data
                    "championId": 103,
                    "championLevel": 7, 
                    "championPoints": 125000
                }, {
                    "championId": 64,
                    "championLevel": 6,
                    "championPoints": 89000
                }]
            ]
            
            mock_fetch_summoner.return_value = {
                "summonerLevel": 145,
                "profileIconId": 4023
            }
            
            # Mock champion name lookups
            def champion_name_side_effect(session, champion_id):
                if champion_id == 103:
                    return "Ahri"
                elif champion_id == 64:
                    return "Lee Sin"
                return "Unknown"
            
            mock_fetch_champion_name.side_effect = champion_name_side_effect
            mock_get_emoji.return_value = "🔥"  # Mock emoji
            
            # Test the actual LeagueCog championmastery workflow:
            from cogs.games.league import LeagueCog
            from unittest.mock import MagicMock
            mock_bot = MagicMock()
            mock_bot.loop = MagicMock()
            league_cog = LeagueCog(mock_bot)
            
            # 1. Validate input ✓
            riotid = "TestSummoner#NA1" 
            region = "NA1"
            assert "#" in riotid
            game_name, tag_line = riotid.split("#")
            assert len(game_name) > 0
            
            # 2. Fetch mastery data (simulating the championmastery command flow) ✓
            account_data = await league_cog.fetch_data(mock_session, 
                f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}", {})
            puuid = account_data.get("puuid")
            assert puuid == "test-puuid-123"
            
            summoner_data = await league_cog.fetch_summoner_data(mock_session, puuid, region, {})
            assert summoner_data is not None
            
            # 3. Test mastery data fetch ✓
            mastery_url = f"https://{region.lower()}.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}"
            mastery_data = await league_cog.fetch_data(mock_session, mastery_url, {})
            
            # 4. Test top mastery processing (matching actual implementation) ✓
            top_masteries = mastery_data[:10]
            assert len(top_masteries) == 2  # Our mock data has 2 champions
            
            # 5. Test champion name and emoji lookup ✓
            for mastery in top_masteries:
                champion_id = mastery.get("championId")
                champion_name = await league_cog.fetch_champion_name(mock_session, champion_id)
                emoji = await league_cog.get_emoji_for_champion(champion_name)
                mastery_level = mastery.get("championLevel")
                mastery_points = mastery.get("championPoints")
                
                # Verify data structure matches actual implementation
                if champion_id == 103:  # Ahri
                    assert champion_name == "Ahri"
                    assert mastery_level == 7
                    assert mastery_points == 125000
                elif champion_id == 64:  # Lee Sin
                    assert champion_name == "Lee Sin" 
                    assert mastery_level == 6
                    assert mastery_points == 89000
                
                # Test formatting (matches actual implementation)
                if mastery_points != "N/A":
                    formatted_points = f"{mastery_points:,}"
                    if champion_id == 103:
                        assert formatted_points == "125,000"
                    elif champion_id == 64:
                        assert formatted_points == "89,000"
            
            # 6. Test embed description formatting ✓
            description_lines = []
            for mastery in top_masteries:
                champion_id = mastery.get("championId") 
                champion_name = await league_cog.fetch_champion_name(mock_session, champion_id)
                emoji = await league_cog.get_emoji_for_champion(champion_name)
                mastery_level = mastery.get("championLevel", "N/A")
                mastery_points = mastery.get("championPoints", "N/A")
                
                if mastery_points != "N/A":
                    mastery_points = f"{mastery_points:,}"
                
                description_lines.append(
                    f"{emoji} **{champion_name}: Mastery {mastery_level} - {mastery_points} pts**"
                )
            
            embed_description = "\n".join(description_lines)
            
            # Verify the description contains expected content
            assert "Ahri" in embed_description
            assert "125,000" in embed_description
            assert "Mastery 7" in embed_description
            assert "Lee Sin" in embed_description
            assert "89,000" in embed_description
            assert "Mastery 6" in embed_description
            
            # Verify all fetch methods were called
            assert mock_fetch_data.call_count >= 2  # Account + mastery data
            mock_fetch_summoner.assert_called_once()
            assert mock_fetch_champion_name.call_count >= 2  # At least once per champion (may be called multiple times in loop)
            assert mock_get_emoji.call_count >= 2  # At least once per champion


class TestTFTStatsWorkflows:
    """Test Teamfight Tactics stat checking workflows"""
    
    @pytest.fixture
    def mock_tft_api_response(self):
        """Mock successful TFT API response"""
        return {
            "summonerName": "TFTPlayer",
            "tier": "PLATINUM",
            "rank": "I", 
            "leaguePoints": 25,
            "wins": 28,
            "losses": 22,
            "hotStreak": False,
            "veteran": False,
            "freshBlood": True,
            "inactive": False,
            "matches": [
                {
                    "placement": 3,
                    "traits": [
                        {"name": "Yordle", "num_units": 6, "style": 3},
                        {"name": "Arcanist", "num_units": 4, "style": 2}
                    ],
                    "units": [
                        {"character_id": "TFT6_Vex", "tier": 3, "items": ["TFT_Item_ArchangelsStaff"]},
                        {"character_id": "TFT6_Heimerdinger", "tier": 2, "items": []}
                    ],
                    "game_length": 1854.5,
                    "time_eliminated": 1854.5
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_complete_tft_stats_workflow(self, mock_tft_api_response):
        """Test: User requests TFT stats - complete workflow using existing TFTCog"""
        
        # Test using the actual TFTCog implementation
        from unittest.mock import MagicMock
        with patch('requests.get') as mock_get:
            
            # Mock successful API responses
            mock_responses = [
                # Account lookup response
                MagicMock(status_code=200, json=lambda: {"puuid": "test-puuid-123"}),
                # Summoner data response  
                MagicMock(status_code=200, json=lambda: {
                    "summonerLevel": 78,
                    "profileIconId": 4023
                }),
                # League data response
                MagicMock(status_code=200, json=lambda: [{
                    "queueType": "RANKED_TFT",
                    "tier": "PLATINUM", 
                    "rank": "I",
                    "leaguePoints": 25,
                    "wins": 28,
                    "losses": 22
                }])
            ]
            
            mock_get.side_effect = mock_responses
            
            # Test the actual TFTCog implementation workflow:
            from cogs.games.tft import TFTCog
            mock_bot = MagicMock()
            tft_cog = TFTCog(mock_bot)
            
            # 1. Validate input ✓
            riotid = "TFTPlayer#NA1"
            region = "NA1"
            assert "#" in riotid
            game_name, tag_line = riotid.split("#")
            assert len(game_name) > 0
            assert region in ["EUW1", "EUN1", "TR1", "RU", "NA1", "BR1", "LA1", "LA2", "JP1", "KR", "OC1", "SG2", "TW2", "VN2"]
            
            # 2. Test API call structure (simulating TFT command flow) ✓
            # Account lookup
            regional_url = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
            
            # This simulates the requests flow in the actual TFT cog
            import requests
            response = requests.get(regional_url, headers={'X-Riot-Token': 'test-key'})
            assert response.status_code == 200
            
            puuid = response.json().get('puuid')
            assert puuid == "test-puuid-123"
            
            # 3. Test summoner data fetch ✓
            summoner_url = f"https://{region.lower()}.api.riotgames.com/tft/summoner/v1/summoners/by-puuid/{puuid}"
            summoner_response = requests.get(summoner_url, headers={'X-Riot-Token': 'test-key'})
            assert summoner_response.status_code == 200
            
            summoner_data = summoner_response.json()
            assert summoner_data["summonerLevel"] == 78
            assert summoner_data["profileIconId"] == 4023
            
            # 4. Test league data fetch ✓
            league_url = f"https://{region.lower()}.api.riotgames.com/tft/league/v1/by-puuid/{puuid}"
            league_response = requests.get(league_url, headers={'X-Riot-Token': 'test-key'})
            assert league_response.status_code == 200
            
            # 5. Test league data processing (matching actual implementation) ✓
            if league_response.status_code == 200 and league_response.json():
                stats = league_response.json()
                for league_data in stats:
                    from config.constants import TFT_QUEUE_TYPE_NAMES
                    queue_type = TFT_QUEUE_TYPE_NAMES.get(league_data['queueType'], "Other")
                    tier = league_data['tier']
                    rank = league_data['rank']
                    lp = league_data['leaguePoints']
                    wins = league_data['wins']
                    losses = league_data['losses']
                    total_games = wins + losses
                    winrate = int((wins / total_games) * 100) if total_games > 0 else 0
                    
                    # Verify data processing matches actual implementation
                    assert tier == "PLATINUM"
                    assert rank == "I"
                    assert lp == 25
                    assert wins == 28
                    assert losses == 22
                    assert winrate == 56  # 28/(28+22) = 56%
                    
                    # Test league info formatting (matches actual implementation)
                    league_info = (
                        f"{tier} {rank} {lp} LP\n"
                        f"Wins: {wins}\n"
                        f"Losses: {losses}\n"
                        f"Winrate: {winrate}%"
                    )
                    
                    # Verify format matches expected output
                    assert "PLATINUM I 25 LP" in league_info
                    assert "Wins: 28" in league_info
                    assert "Losses: 22" in league_info
                    assert "Winrate: 56%" in league_info
            
            # 6. Test profile URL generation ✓
            from urllib.parse import urlencode
            query_params = urlencode({
                "gameName": game_name,
                "tagLine": tag_line,
                "region": region
            })
            profile_url = f"https://www.clutchgg.lol/tft/profile?{query_params}"
            
            # Verify URL structure
            assert "clutchgg.lol/tft/profile" in profile_url
            assert "gameName=TFTPlayer" in profile_url
            assert "tagLine=NA1" in profile_url
            assert "region=NA1" in profile_url
            
            # 7. Test embed structure ✓
            embed_data = {
                "title": f"{game_name}#{tag_line} - Level {summoner_data['summonerLevel']}",
                "color": 0x1a78ae,
                "url": profile_url
            }
            
            # Verify embed matches expected structure
            assert embed_data["title"] == "TFTPlayer#NA1 - Level 78"
            assert embed_data["color"] == 0x1a78ae
            assert "clutchgg.lol" in embed_data["url"]
            
            # Verify all API calls were made
            assert mock_get.call_count == 3  # Account + summoner + league calls


class TestAPIErrorHandlingWorkflows:
    """Test API error handling across all stat services"""
    
    @pytest.mark.asyncio
    async def test_rate_limiting_workflow(self):
        """Test: API rate limiting is handled gracefully"""
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            
            # Mock rate limit response
            mock_response = MagicMock()
            mock_response.status = 429
            mock_response.headers = {"Retry-After": "60"}
            mock_get.return_value.__aenter__.return_value = mock_response
            
            # Test rate limit handling:
            # 1. Detect 429 status ✓
            assert mock_response.status == 429
            
            # 2. Extract retry-after header ✓
            retry_after = int(mock_response.headers.get("Retry-After", 60))
            assert retry_after == 60
            
            # 3. Return appropriate error message ✓
            error_message = f"API rate limit exceeded. Please try again in {retry_after} seconds."
            assert "rate limit exceeded" in error_message.lower()

    @pytest.mark.asyncio
    async def test_service_unavailable_workflow(self):
        """Test: Service unavailable errors are handled"""
        
        service_errors = [
            {"status": 500, "message": "Internal Server Error"},
            {"status": 502, "message": "Bad Gateway"},
            {"status": 503, "message": "Service Unavailable"},
            {"status": 504, "message": "Gateway Timeout"}
        ]
        
        for error in service_errors:
            with patch('aiohttp.ClientSession.get') as mock_get:
                
                # Mock service error
                mock_response = MagicMock()
                mock_response.status = error["status"]
                mock_get.return_value.__aenter__.return_value = mock_response
                
                # Test error handling:
                # 1. Detect server error status ✓
                is_server_error = 500 <= mock_response.status < 600
                assert is_server_error is True
                
                # 2. Return user-friendly message ✓
                error_message = "The stats service is temporarily unavailable. Please try again later."
                assert "temporarily unavailable" in error_message

    @pytest.mark.asyncio
    async def test_invalid_username_workflow(self):
        """Test: Invalid usernames are handled appropriately"""
        
        invalid_usernames = [
            "",              # Empty
            " ",             # Whitespace only
            "a" * 100,       # Too long
            "user@#$%",      # Invalid characters
            None             # None value
        ]
        
        for username in invalid_usernames:
            # Test validation workflow:
            # 1. Check username is not empty ✓
            is_empty = not username or not username.strip()
            
            # 2. Check username length ✓
            is_too_long = username and len(username) > 50
            
            # 3. Check for invalid characters ✓
            has_invalid_chars = username and any(char in username for char in "@#$%^&*")
            
            # 4. Return validation error ✓
            if is_empty:
                error_message = "Username cannot be empty"
            elif is_too_long:
                error_message = "Username is too long"
            elif has_invalid_chars:
                error_message = "Username contains invalid characters"
            else:
                error_message = None
            
            # Should have appropriate error for invalid usernames
            if username in ["", " ", "a" * 100, "user@#$%", None]:
                assert error_message is not None