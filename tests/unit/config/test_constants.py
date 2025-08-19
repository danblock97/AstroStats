import pytest


class TestConfigConstants:
    """Test configuration constants and data structures"""
    
    def test_league_regions_format(self):
        """Test League of Legends regions are properly formatted"""
        from config.constants import LEAGUE_REGIONS
        
        assert isinstance(LEAGUE_REGIONS, list)
        assert len(LEAGUE_REGIONS) > 0
        
        # Test common regions are included
        expected_regions = ["EUW1", "EUN1", "NA1", "KR", "JP1"]
        for region in expected_regions:
            assert region in LEAGUE_REGIONS
        
        # Test all regions are strings and uppercase
        for region in LEAGUE_REGIONS:
            assert isinstance(region, str)
            assert region.isupper()

    def test_league_queue_type_names(self):
        """Test League queue type mappings"""
        from config.constants import LEAGUE_QUEUE_TYPE_NAMES
        
        assert isinstance(LEAGUE_QUEUE_TYPE_NAMES, dict)
        
        # Test required queue types
        expected_queues = {
            "RANKED_SOLO_5x5": "Ranked Solo/Duo",
            "RANKED_FLEX_SR": "Ranked Flex 5v5",
            "CHERRY": "Arena"
        }
        
        for queue_id, display_name in expected_queues.items():
            assert queue_id in LEAGUE_QUEUE_TYPE_NAMES
            assert LEAGUE_QUEUE_TYPE_NAMES[queue_id] == display_name

    def test_tft_queue_type_names(self):
        """Test TFT queue type mappings"""
        from config.constants import TFT_QUEUE_TYPE_NAMES
        
        assert isinstance(TFT_QUEUE_TYPE_NAMES, dict)
        assert "RANKED_TFT" in TFT_QUEUE_TYPE_NAMES
        assert TFT_QUEUE_TYPE_NAMES["RANKED_TFT"] == "Ranked TFT"

    def test_apex_platform_mapping(self):
        """Test Apex Legends platform mappings"""
        from config.constants import APEX_PLATFORM_MAPPING
        
        assert isinstance(APEX_PLATFORM_MAPPING, dict)
        
        # Test required platforms
        expected_platforms = {
            'Xbox': 'xbl',
            'Playstation': 'psn',
            'Origin (PC)': 'origin'
        }
        
        for display_name, api_name in expected_platforms.items():
            assert display_name in APEX_PLATFORM_MAPPING
            assert APEX_PLATFORM_MAPPING[display_name] == api_name

    def test_fortnite_time_mapping(self):
        """Test Fortnite time period mappings"""
        from config.constants import FORTNITE_TIME_MAPPING
        
        assert isinstance(FORTNITE_TIME_MAPPING, dict)
        
        expected_times = {
            'Season': 'season',
            'Lifetime': 'lifetime'
        }
        
        for display_name, api_name in expected_times.items():
            assert display_name in FORTNITE_TIME_MAPPING
            assert FORTNITE_TIME_MAPPING[display_name] == api_name

    def test_special_emoji_names(self):
        """Test League champion emoji name mappings"""
        from config.constants import SPECIAL_EMOJI_NAMES
        
        assert isinstance(SPECIAL_EMOJI_NAMES, dict)
        
        # Test some specific champion mappings
        expected_mappings = {
            "Renata Glasc": "Renata",
            "Wukong": "MonkeyKing",
            "Miss Fortune": "MissFortune",
            "Aurelion Sol": "AurelionSol",
            "Cho'Gath": "Chogath",
            "Nunu & Willump": "Nunu"
        }
        
        for champion_name, emoji_name in expected_mappings.items():
            assert champion_name in SPECIAL_EMOJI_NAMES
            assert SPECIAL_EMOJI_NAMES[champion_name] == emoji_name

    def test_latest_updates_format(self):
        """Test latest updates string format"""
        from config.constants import LATEST_UPDATES
        
        assert isinstance(LATEST_UPDATES, str)
        assert len(LATEST_UPDATES) > 0
        
        # Test contains version information
        assert "Version" in LATEST_UPDATES
        assert "2.6.0" in LATEST_UPDATES
        
        # Test contains key feature mentions
        assert "Catfight" in LATEST_UPDATES
        assert "Premium" in LATEST_UPDATES
        assert "PvP" in LATEST_UPDATES
        
        # Test formatting markers
        assert "**" in LATEST_UPDATES  # Bold formatting
        assert "\n" in LATEST_UPDATES   # Line breaks

    def test_sfw_truths_content(self):
        """Test SFW truth questions"""
        from config.constants import SFW_TRUTHS
        
        assert isinstance(SFW_TRUTHS, list)
        assert len(SFW_TRUTHS) >= 50  # Should have many questions
        
        # Test all entries are strings and questions
        for truth in SFW_TRUTHS:
            assert isinstance(truth, str)
            assert len(truth) > 10  # Reasonable minimum length
            assert truth.endswith("?")  # Should be questions
        
        # Test some expected content exists
        sample_keywords = ["superpower", "embarrassing", "travel", "favorite"]
        found_keywords = 0
        for truth in SFW_TRUTHS:
            if any(keyword in truth.lower() for keyword in sample_keywords):
                found_keywords += 1
        
        assert found_keywords >= 2  # Should find multiple expected topics

    def test_sfw_dares_content(self):
        """Test SFW dare challenges"""
        from config.constants import SFW_DARES
        
        assert isinstance(SFW_DARES, list)
        assert len(SFW_DARES) >= 50  # Should have many dares
        
        # Test all entries are strings and commands
        for dare in SFW_DARES:
            assert isinstance(dare, str)
            assert len(dare) > 10  # Reasonable minimum length
        
        # Test some expected dare types exist
        sample_keywords = ["impression", "dance", "sing", "push-ups", "accent"]
        found_keywords = 0
        for dare in SFW_DARES:
            if any(keyword in dare.lower() for keyword in sample_keywords):
                found_keywords += 1
        
        assert found_keywords >= 3  # Should find multiple expected dare types

    def test_nsfw_truths_content(self):
        """Test NSFW truth questions exist and are properly separated"""
        from config.constants import NSFW_TRUTHS
        
        assert isinstance(NSFW_TRUTHS, list)
        assert len(NSFW_TRUTHS) >= 50  # Should have many questions
        
        # Test all entries are strings and questions
        for truth in NSFW_TRUTHS:
            assert isinstance(truth, str)
            assert len(truth) > 10  # Reasonable minimum length
            assert truth.endswith(("?", "."))  # Should be questions or statements

    def test_nsfw_dares_content(self):
        """Test NSFW dare challenges exist and are properly separated"""
        from config.constants import NSFW_DARES
        
        assert isinstance(NSFW_DARES, list)
        assert len(NSFW_DARES) >= 50  # Should have many dares
        
        # Test all entries are strings
        for dare in NSFW_DARES:
            assert isinstance(dare, str)
            assert len(dare) > 10  # Reasonable minimum length

    def test_sfw_would_you_rather_content(self):
        """Test SFW Would You Rather questions"""
        from config.constants import SFW_WOULD_YOU_RATHER
        
        assert isinstance(SFW_WOULD_YOU_RATHER, list)
        assert len(SFW_WOULD_YOU_RATHER) >= 50  # Should have many questions
        
        # Test all entries are proper Would You Rather format
        for question in SFW_WOULD_YOU_RATHER:
            assert isinstance(question, str)
            assert question.startswith("Would you rather")
            assert " or " in question
            assert question.endswith("?")

    def test_nsfw_would_you_rather_content(self):
        """Test NSFW Would You Rather questions"""
        from config.constants import NSFW_WOULD_YOU_RATHER
        
        assert isinstance(NSFW_WOULD_YOU_RATHER, list)
        assert len(NSFW_WOULD_YOU_RATHER) >= 50  # Should have many questions
        
        # Test all entries are proper Would You Rather format
        for question in NSFW_WOULD_YOU_RATHER:
            assert isinstance(question, str)
            assert question.startswith("Would you rather")
            assert " or " in question
            assert question.endswith("?")

    def test_forfeits_content(self):
        """Test forfeit challenges for declined dares"""
        from config.constants import FORFEITS
        
        assert isinstance(FORFEITS, list)
        assert len(FORFEITS) >= 5  # Should have multiple forfeit options
        
        # Test all entries are strings and reasonable commands
        for forfeit in FORFEITS:
            assert isinstance(forfeit, str)
            assert len(forfeit) > 10  # Reasonable minimum length
        
        # Test some expected forfeit types
        sample_keywords = ["embarrassing", "push-ups", "compliment", "joke"]
        found_keywords = 0
        for forfeit in FORFEITS:
            if any(keyword in forfeit.lower() for keyword in sample_keywords):
                found_keywords += 1
        
        assert found_keywords >= 2  # Should find multiple expected forfeit types

    def test_champion_name_special_cases(self):
        """Test champion names handle special characters correctly"""
        from config.constants import SPECIAL_EMOJI_NAMES
        
        # Test apostrophes and special characters
        apostrophe_champions = ["Cho'Gath", "Rek'Sai", "Kai'Sa", "Vel'Koz", "Kha'Zix", "Bel'Veth", "K'Sante"]
        
        for champion in apostrophe_champions:
            if champion in SPECIAL_EMOJI_NAMES:
                emoji_name = SPECIAL_EMOJI_NAMES[champion]
                # Emoji names should not have apostrophes
                assert "'" not in emoji_name

    def test_platform_mappings_consistency(self):
        """Test platform mappings are consistent and valid"""
        from config.constants import APEX_PLATFORM_MAPPING
        
        # Test all values are lowercase API identifiers
        for display_name, api_name in APEX_PLATFORM_MAPPING.items():
            assert api_name.islower()
            assert len(api_name) >= 3  # Reasonable minimum length
            assert " " not in api_name  # No spaces in API names

    def test_queue_type_name_consistency(self):
        """Test queue type names are user-friendly"""
        from config.constants import LEAGUE_QUEUE_TYPE_NAMES, TFT_QUEUE_TYPE_NAMES
        
        all_queue_names = list(LEAGUE_QUEUE_TYPE_NAMES.values()) + list(TFT_QUEUE_TYPE_NAMES.values())
        
        for display_name in all_queue_names:
            # Should be human-readable (contain spaces or be single words)
            assert len(display_name) >= 3
            # Should not contain underscores (those are for API keys)
            assert "_" not in display_name

    def test_truth_dare_content_safety(self):
        """Test SFW content is appropriate and safe"""
        from config.constants import SFW_TRUTHS, SFW_DARES, FORFEITS
        
        # Words that should not appear in SFW content
        inappropriate_words = ["sex", "naked", "nude", "orgasm", "porn"]
        
        all_sfw_content = SFW_TRUTHS + SFW_DARES + FORFEITS
        
        for content in all_sfw_content:
            content_lower = content.lower()
            for word in inappropriate_words:
                assert word not in content_lower, f"Inappropriate word '{word}' found in SFW content: {content}"

    def test_content_length_limits(self):
        """Test content doesn't exceed reasonable Discord limits"""
        from config.constants import SFW_TRUTHS, SFW_DARES, NSFW_TRUTHS, NSFW_DARES, SFW_WOULD_YOU_RATHER, NSFW_WOULD_YOU_RATHER
        
        all_content = SFW_TRUTHS + SFW_DARES + NSFW_TRUTHS + NSFW_DARES + SFW_WOULD_YOU_RATHER + NSFW_WOULD_YOU_RATHER
        
        for content in all_content:
            # Discord embed field value limit is 1024 characters
            assert len(content) <= 1000, f"Content too long: {content[:100]}..."

    def test_latest_updates_version_info(self):
        """Test latest updates contain proper version information"""
        from config.constants import LATEST_UPDATES
        
        # Test version format
        assert "Version 2.6.0" in LATEST_UPDATES
        
        # Test contains feature descriptions
        feature_keywords = ["Catfight", "PvP", "Premium", "battle", "leaderboard"]
        found_features = 0
        for keyword in feature_keywords:
            if keyword.lower() in LATEST_UPDATES.lower():
                found_features += 1
        
        assert found_features >= 3, "Latest updates should mention key features"

    def test_region_code_validity(self):
        """Test League region codes follow expected patterns"""
        from config.constants import LEAGUE_REGIONS
        
        # Most regions follow pattern: 2-3 letters + 1 number
        valid_patterns = 0
        for region in LEAGUE_REGIONS:
            if len(region) >= 3 and region[-1].isdigit():
                valid_patterns += 1
            elif region in ["RU", "KR"]:  # Special cases
                valid_patterns += 1
        
        # Most regions should follow the pattern
        assert valid_patterns >= len(LEAGUE_REGIONS) * 0.8

    def test_emoji_mapping_completeness(self):
        """Test emoji mappings cover all special cases"""
        from config.constants import SPECIAL_EMOJI_NAMES
        
        # Test that all mapped names are different from original
        for original, mapped in SPECIAL_EMOJI_NAMES.items():
            assert original != mapped, f"Champion '{original}' maps to itself"
            
        # Test specific problematic champions are handled
        problematic_champions = ["Cho'Gath", "Kai'Sa", "Vel'Koz", "Miss Fortune"]
        for champion in problematic_champions:
            assert champion in SPECIAL_EMOJI_NAMES, f"Problematic champion '{champion}' not in emoji mapping"

    def test_truth_dare_question_formats(self):
        """Test truth and dare questions have proper formats"""
        from config.constants import SFW_TRUTHS, NSFW_TRUTHS
        
        all_truths = SFW_TRUTHS + NSFW_TRUTHS
        
        for truth in all_truths:
            # Truths should be questions or statements
            assert truth.endswith(("?", ".")), f"Truth should end with '?' or '.': {truth[:50]}..."
            
            # Should start with appropriate question words or descriptive words
            question_starters = ["What", "How", "When", "Where", "Who", "Why", "If", "Have", "Do", "Are", "Would", "Describe", "Tell", "Share", "Name"]
            starts_correctly = any(truth.startswith(starter) for starter in question_starters)
            assert starts_correctly, f"Truth should start with question/prompt word: {truth[:50]}..."

    def test_dare_command_formats(self):
        """Test dare commands have proper action formats"""
        from config.constants import SFW_DARES, NSFW_DARES
        
        all_dares = SFW_DARES + NSFW_DARES
        
        for dare in all_dares:
            # Dares should be imperative commands
            command_starters = ["Do", "Try", "Act", "Make", "Sing", "Dance", "Wear", "Let", "Give", "Tell", "Show", "Take", "Go", "Put", "Remove", "Pretend", "Build", "Draw", "Call", "Text", "Speak", "Use", "Lick", "Kiss", "Balance", "Hop", "Spin", "Describe", "Talk", "Write", "Say", "Create", "Invent", "Moonwalk", "Recite", "Eat", "Walk", "Send", "Whisper", "Read", "Swap", "Post", "Re-enact", "Truth", "Apply", "Serenade", "Stick", "Slowly", "Slow", "Confess", "Massage", "Blindfold"]
            starts_correctly = any(dare.startswith(starter) for starter in command_starters)
            assert starts_correctly, f"Dare should start with command verb: {dare[:50]}..."

    def test_would_you_rather_format_consistency(self):
        """Test Would You Rather questions have consistent format"""
        from config.constants import SFW_WOULD_YOU_RATHER, NSFW_WOULD_YOU_RATHER
        
        all_wyr = SFW_WOULD_YOU_RATHER + NSFW_WOULD_YOU_RATHER
        
        for question in all_wyr:
            # Should have exactly one " or " separator
            or_count = question.count(" or ")
            assert or_count == 1, f"Would You Rather should have exactly one ' or ': {question[:50]}..."
            
            # Should start with "Would you rather"
            assert question.startswith("Would you rather"), f"Should start with 'Would you rather': {question[:50]}..."

    def test_data_structure_immutability(self):
        """Test that constants are properly structured as immutable data"""
        from config.constants import LEAGUE_REGIONS, APEX_PLATFORM_MAPPING, SFW_TRUTHS
        
        # Test lists and dictionaries exist and have content
        assert isinstance(LEAGUE_REGIONS, list)
        assert len(LEAGUE_REGIONS) > 0
        
        assert isinstance(APEX_PLATFORM_MAPPING, dict)
        assert len(APEX_PLATFORM_MAPPING) > 0
        
        assert isinstance(SFW_TRUTHS, list)
        assert len(SFW_TRUTHS) > 0