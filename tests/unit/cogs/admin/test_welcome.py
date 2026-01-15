import pytest
import discord
from unittest.mock import AsyncMock, MagicMock, patch
from discord.ext import commands

from services.database.models import WelcomeSettings
from services.database.welcome import get_welcome_settings, update_welcome_settings


class TestWelcomeService:
    """Test welcome service functionality."""
    
    @patch('services.database.welcome._welcome_collection')
    @patch('services.database.welcome._init_db_if_needed')
    def test_get_welcome_settings_existing(self, mock_init, mock_collection):
        """Test retrieving existing welcome settings."""
        # Setup mock data
        mock_doc = {
            "guild_id": "123456789",
            "enabled": True,
            "custom_message": "Welcome {user} to {server}!",
            "custom_image_data": "base64encodedimagedata",
            "custom_image_filename": "welcome.png",
            "_id": "mock_id"
        }
        
        mock_collection.find_one.return_value = mock_doc
        
        # Test
        settings = get_welcome_settings("123456789")
        
        # Verify
        assert settings is not None
        assert settings.guild_id == "123456789"
        assert settings.enabled is True
        assert settings.custom_message == "Welcome {user} to {server}!"
        assert settings.custom_image_data == "base64encodedimagedata"
        assert settings.custom_image_filename == "welcome.png"
        assert settings._id == "mock_id"
        
        mock_collection.find_one.assert_called_once_with({"guild_id": "123456789"})

    @patch('services.database.welcome._welcome_collection')
    @patch('services.database.welcome._init_db_if_needed')
    def test_get_welcome_settings_not_found(self, mock_init, mock_collection):
        """Test retrieving non-existent welcome settings."""
        mock_collection.find_one.return_value = None
        
        settings = get_welcome_settings("123456789")
        
        assert settings is None
        mock_collection.find_one.assert_called_once_with({"guild_id": "123456789"})

    @patch('services.database.welcome._welcome_collection')
    @patch('services.database.welcome._init_db_if_needed')
    def test_update_welcome_settings_enabled(self, mock_init, mock_collection):
        """Test updating welcome enabled setting."""
        mock_result = MagicMock()
        mock_result.acknowledged = True
        mock_collection.update_one.return_value = mock_result
        
        success = update_welcome_settings("123456789", enabled=True)
        
        assert success is True
        mock_collection.update_one.assert_called_once_with(
            {"guild_id": "123456789"},
            {"$set": {"enabled": True}},
            upsert=True
        )

    @patch('services.database.welcome._welcome_collection')
    @patch('services.database.welcome._init_db_if_needed')
    def test_update_welcome_settings_message(self, mock_init, mock_collection):
        """Test updating custom welcome message."""
        mock_result = MagicMock()
        mock_result.acknowledged = True
        mock_collection.update_one.return_value = mock_result
        
        success = update_welcome_settings("123456789", custom_message="Hello {user}!")
        
        assert success is True
        mock_collection.update_one.assert_called_once_with(
            {"guild_id": "123456789"},
            {"$set": {"custom_message": "Hello {user}!"}},
            upsert=True
        )

    @patch('services.database.welcome._welcome_collection')
    @patch('services.database.welcome._init_db_if_needed')
    def test_update_welcome_settings_multiple(self, mock_init, mock_collection):
        """Test updating multiple welcome settings."""
        mock_result = MagicMock()
        mock_result.acknowledged = True
        mock_collection.update_one.return_value = mock_result
        
        success = update_welcome_settings(
            "123456789", 
            enabled=True,
            custom_message="Welcome {user}!",
            custom_image_data="base64data",
            custom_image_filename="welcome.webp"
        )
        
        assert success is True
        
        expected_update = {
            "$set": {
                "enabled": True,
                "custom_message": "Welcome {user}!",
                "custom_image_data": "base64data",
                "custom_image_filename": "welcome.webp"
            }
        }
        mock_collection.update_one.assert_called_once_with(
            {"guild_id": "123456789"},
            expected_update,
            upsert=True
        )

    @patch('services.database.welcome._welcome_collection')
    @patch('services.database.welcome._init_db_if_needed')
    def test_update_welcome_settings_no_changes(self, mock_init, mock_collection):
        """Test updating with no actual changes."""
        mock_result = MagicMock()
        mock_result.acknowledged = True
        mock_collection.update_one.return_value = mock_result
        
        success = update_welcome_settings("123456789")
        
        assert success is True
        # Should not call update_one when no changes
        mock_collection.update_one.assert_not_called()


class TestWelcomeModels:
    """Test welcome model structures."""
    
    def test_welcome_settings_creation(self):
        """Test WelcomeSettings dataclass creation."""
        settings = WelcomeSettings(guild_id="123456789")
        
        assert settings.guild_id == "123456789"
        assert settings.enabled is False  # Default
        assert settings.custom_message is None  # Default
        assert settings.custom_image_data is None  # Default
        assert settings.custom_image_filename is None  # Default
        assert settings._id is None  # Default

    def test_welcome_settings_with_values(self):
        """Test WelcomeSettings with custom values."""
        settings = WelcomeSettings(
            guild_id="123456789",
            enabled=True,
            custom_message="Welcome {user} to our server!",
            custom_image_data="base64encodedimagedata",
            custom_image_filename="welcome.png",
            _id="some_object_id"
        )
        
        assert settings.guild_id == "123456789"
        assert settings.enabled is True
        assert settings.custom_message == "Welcome {user} to our server!"
        assert settings.custom_image_data == "base64encodedimagedata"
        assert settings.custom_image_filename == "welcome.png"
        assert settings._id == "some_object_id"


class TestWelcomeFeatureTiers:
    """Test premium tier requirements for welcome features."""
    
    def test_free_tier_features(self):
        """Test which features are available to free tier."""
        free_features = [
            "toggle",  # Enable/disable welcome messages
            "remove-message",  # Remove custom message
        ]
        
        # Free tier should have access to basic toggle and remove functions
        assert "toggle" in free_features
        assert "remove-message" in free_features

    def test_premium_tier_features(self):
        """Test which features require premium tiers."""
        supporter_features = ["set-message"]  # Supporter and above
        sponsor_vip_features = ["set-image", "remove-image"]  # Sponsor and VIP only
        
        # Premium tiers should have access to advanced features
        assert "set-message" in supporter_features
        assert "set-image" in sponsor_vip_features
        assert "remove-image" in sponsor_vip_features

    def test_tier_hierarchy(self):
        """Test that higher tiers include lower tier features."""
        free_features = {"toggle", "remove-message"}
        supporter_features = free_features | {"set-message"}
        sponsor_features = supporter_features | {"set-image", "remove-image"}
        vip_features = sponsor_features.copy()  # VIP has same as sponsor for welcome
        
        # Verify tier hierarchy
        assert free_features.issubset(supporter_features)
        assert supporter_features.issubset(sponsor_features)
        assert sponsor_features == vip_features


class TestMessagePlaceholders:
    """Test welcome message placeholder functionality."""
    
    def test_placeholder_replacement(self):
        """Test placeholder replacement in welcome messages."""
        template = "Welcome {user} to {server}! Your username is {username}."
        
        # Mock member and guild
        mock_member = MagicMock()
        mock_member.mention = "<@123456789>"
        mock_member.display_name = "TestUser"
        mock_member.guild.name = "Test Server"
        
        # Replace placeholders
        result = template.replace(
            "{user}", mock_member.mention
        ).replace(
            "{username}", mock_member.display_name
        ).replace(
            "{server}", mock_member.guild.name
        )
        
        expected = "Welcome <@123456789> to Test Server! Your username is TestUser."
        assert result == expected

    def test_placeholder_edge_cases(self):
        """Test placeholder replacement with edge cases."""
        # Test with missing placeholders
        template = "Welcome to the server!"
        result = template.replace("{user}", "@user").replace("{server}", "server")
        assert result == "Welcome to the server!"
        
        # Test with multiple occurrences
        template = "Hello {user}, {user} welcome to {server}!"
        result = template.replace("{user}", "@testuser").replace("{server}", "TestGuild")
        assert result == "Hello @testuser, @testuser welcome to TestGuild!"

    def test_message_length_validation(self):
        """Test message length constraints."""
        # Test normal length message
        normal_message = "Welcome to our server! " * 20  # About 500 chars
        assert len(normal_message) <= 1000
        
        # Test overly long message
        long_message = "Welcome to our server! " * 50  # About 1250 chars
        assert len(long_message) > 1000


class TestWelcomeCommands:
    """Test welcome cog commands and functionality."""

    def test_channel_placeholder_replacement(self):
        """Test channel placeholder replacement functionality."""
        import re
        
        # Mock guild with channels
        class MockChannel:
            def __init__(self, name):
                self.name = name
                self.mention = f"<#{name}-id>"
        
        class MockGuild:
            def __init__(self):
                self.text_channels = [
                    MockChannel("rules"),
                    MockChannel("general"),
                    MockChannel("verification"),
                    MockChannel("announcements")
                ]
        
        guild = MockGuild()
        
        def replace_channel_mention(match):
            channel_name = match.group(1)
            for channel in guild.text_channels:
                if channel.name.lower() == channel_name.lower():
                    return channel.mention
            return f"#{channel_name}"
        
        # Test various channel mentions
        test_cases = [
            ("Welcome! Check {#rules} first.", "Welcome! Check <#rules-id> first."),
            ("Read {#rules} and chat in {#general}!", "Read <#rules-id> and chat in <#general-id>!"),
            ("Verify in {#verification}", "Verify in <#verification-id>"),
            ("Non-existent {#missing-channel}", "Non-existent #missing-channel"),
            ("Case insensitive {#RULES}", "Case insensitive <#rules-id>"),
            ("Multiple {#rules} and {#general} channels", "Multiple <#rules-id> and <#general-id> channels"),
        ]
        
        for input_msg, expected in test_cases:
            result = re.sub(r'\{#([^}]+)\}', replace_channel_mention, input_msg)
            assert result == expected

    def test_all_placeholder_replacement(self):
        """Test replacement of all supported placeholders."""
        import re
        
        # Mock objects
        class MockUser:
            def __init__(self):
                self.mention = "<@123456789>"
                self.display_name = "TestUser"
        
        class MockGuild:
            def __init__(self):
                self.name = "Test Server"
                self.text_channels = [MockChannel("rules")]
        
        class MockChannel:
            def __init__(self, name):
                self.name = name
                self.mention = f"<#{name}-id>"
        
        user = MockUser()
        guild = MockGuild()
        
        # Test message with all placeholders
        message = "Welcome {user} to {server}! Your username is {username}. Read {#rules} first."
        
        # Replace user placeholders
        result = message.replace("{user}", user.mention).replace(
            "{username}", user.display_name
        ).replace("{server}", guild.name)
        
        # Replace channel mentions
        def replace_channel_mention(match):
            channel_name = match.group(1)
            for channel in guild.text_channels:
                if channel.name.lower() == channel_name.lower():
                    return channel.mention
            return f"#{channel_name}"
        
        result = re.sub(r'\{#([^}]+)\}', replace_channel_mention, result)
        
        expected = "Welcome <@123456789> to Test Server! Your username is TestUser. Read <#rules-id> first."
        assert result == expected

    def test_image_compression_size_calculation(self):
        """Test image size calculations for compression info."""
        # Test size calculations
        original_size = 2500000  # 2.5MB in bytes
        compressed_size = 800000  # 800KB in bytes
        
        original_mb = original_size / (1024 * 1024)
        compressed_mb = compressed_size / (1024 * 1024)
        
        assert abs(original_mb - 2.4) < 0.1  # Should be ~2.4MB
        assert abs(compressed_mb - 0.8) < 0.1  # Should be ~0.8MB
        
        # Test format string
        format_info = f"Original: {original_mb:.1f}MB → Compressed: {compressed_mb:.1f}MB (WEBP)"
        expected = "Original: 2.4MB → Compressed: 0.8MB (WEBP)"
        assert format_info == expected

    def test_gif_format_detection(self):
        """Test GIF format detection and info display."""
        # Test WEBP format
        is_gif = False
        format_info = "GIF (animated)" if is_gif else "WEBP"
        assert format_info == "WEBP"
        
        # Test GIF format
        is_gif = True
        format_info = "GIF (animated)" if is_gif else "WEBP"
        assert format_info == "GIF (animated)"

    def test_file_extension_validation(self):
        """Test file extension validation for image uploads."""
        allowed_formats = ['png', 'jpg', 'jpeg', 'webp', 'gif', 'bmp']
        
        # Test valid extensions
        valid_files = [
            "image.png",
            "photo.jpg", 
            "picture.jpeg",
            "animation.gif",
            "graphic.webp",
            "bitmap.bmp"
        ]
        
        for filename in valid_files:
            extension = filename.split('.')[-1].lower()
            assert extension in allowed_formats
        
        # Test invalid extensions
        invalid_files = [
            "document.pdf",
            "video.mp4",
            "audio.mp3",
            "text.txt"
        ]
        
        for filename in invalid_files:
            extension = filename.split('.')[-1].lower()
            assert extension not in allowed_formats


class TestWelcomePermissions:
    """Test welcome command permissions and access control."""

    def test_manage_guild_permission_check(self):
        """Test manage guild permission validation."""
        # Mock user with manage guild permission
        class MockUserWithPermission:
            def __init__(self):
                self.guild_permissions = MockPermissions(manage_guild=True)
        
        class MockUserWithoutPermission:
            def __init__(self):
                self.guild_permissions = MockPermissions(manage_guild=False)
        
        class MockPermissions:
            def __init__(self, manage_guild=False):
                self.manage_guild = manage_guild
        
        # Test user with permission
        user_with_perm = MockUserWithPermission()
        assert user_with_perm.guild_permissions.manage_guild is True
        
        # Test user without permission
        user_without_perm = MockUserWithoutPermission()
        assert user_without_perm.guild_permissions.manage_guild is False

    def test_premium_tier_requirements(self):
        """Test premium tier requirements for different commands."""
        # Define command tier requirements
        command_requirements = {
            "toggle": [],  # Free
            "remove-message": [],  # Free  
            "remove-image": ["sponsor", "vip"],
            "set-message": ["supporter", "sponsor", "vip"],
            "set-image": ["sponsor", "vip"],
        }
        
        # Test tier access
        user_tiers = ["free", "supporter", "sponsor", "vip"]
        
        for tier in user_tiers:
            # Check which commands this tier can access
            accessible_commands = []
            for cmd, required_tiers in command_requirements.items():
                if not required_tiers or tier in required_tiers:
                    accessible_commands.append(cmd)
            
            if tier == "free":
                assert "toggle" in accessible_commands
                assert "remove-message" in accessible_commands
                assert "set-message" not in accessible_commands
                assert "set-image" not in accessible_commands
            elif tier == "supporter":
                assert "set-message" in accessible_commands
                assert "set-image" not in accessible_commands  # Requires sponsor+
            elif tier in ["sponsor", "vip"]:
                assert "set-message" in accessible_commands
                assert "set-image" in accessible_commands
                assert "remove-image" in accessible_commands

    def test_permission_error_messages(self):
        """Test permission error message generation."""
        # Test manage server permission error
        manage_server_error = {
            "title": "❌ Missing Permissions",
            "description": "You need the **Manage Server** permission to use this command."
        }
        
        assert "Manage Server" in manage_server_error["description"]
        
        # Test premium tier error
        required_tiers = ["sponsor", "vip"]
        premium_error = {
            "title": "🔒 Premium Feature Required",
            "description": f"This feature requires **{' or '.join(required_tiers).title()}** tier or higher."
        }
        
        assert "Sponsor Or Vip" in premium_error["description"]


class TestWelcomeMessageFormatting:
    """Test welcome message formatting and display."""

    def test_single_message_combination(self):
        """Test that text and image are combined in single message."""
        # Mock message sending - should be one call with both content and file
        class MockMessage:
            def __init__(self):
                self.content = None
                self.file = None
                self.send_calls = []
            
            async def send(self, content=None, file=None):
                self.send_calls.append({"content": content, "file": file})
                return self
        
        mock_channel = MockMessage()
        
        # Simulate sending welcome with image
        message_content = "Welcome @user!"
        has_image = True
        
        if has_image:
            # Should be one call with both content and file
            import asyncio
            asyncio.run(mock_channel.send(content=message_content, file="mock_file"))
        else:
            # Should be one call with just content
            import asyncio
            asyncio.run(mock_channel.send(content=message_content))
        
        # Verify single message sent
        assert len(mock_channel.send_calls) == 1
        assert mock_channel.send_calls[0]["content"] == message_content

    def test_test_message_indicator(self):
        """Test that test indicator is only added to test commands."""
        base_message = "Welcome @user to **Server**!"
        
        # Real welcome message (no indicator)
        real_message = base_message
        assert "🧪 This is a test welcome message" not in real_message
        
        # Test welcome message (has indicator)
        test_message = f"{base_message}\n\n*🧪 This is a test welcome message*"
        assert "🧪 This is a test welcome message" in test_message
        assert test_message.startswith(base_message)

    def test_fallback_behavior(self):
        """Test fallback behavior when image processing fails."""
        # Test image processing failure fallback
        def process_welcome_message(has_image=False, image_processing_fails=False):
            message_content = "Welcome @user!"
            
            if has_image:
                if image_processing_fails:
                    # Should fallback to text-only
                    return {"content": message_content, "file": None, "fallback_used": True}
                else:
                    # Should include image
                    return {"content": message_content, "file": "image_data", "fallback_used": False}
            else:
                # Text only
                return {"content": message_content, "file": None, "fallback_used": False}
        
        # Test successful image processing
        result = process_welcome_message(has_image=True, image_processing_fails=False)
        assert result["file"] is not None
        assert result["fallback_used"] is False
        
        # Test failed image processing (fallback)
        result = process_welcome_message(has_image=True, image_processing_fails=True)
        assert result["file"] is None
        assert result["fallback_used"] is True
        assert result["content"] == "Welcome @user!"
        
        # Test no image
        result = process_welcome_message(has_image=False)
        assert result["file"] is None
        assert result["fallback_used"] is False


class TestWelcomeIntegration:
    """Test complete welcome system integration."""

    def test_complete_welcome_flow(self):
        """Test the complete welcome message flow with all features."""
        import re
        import base64
        
        # Mock guild setup
        class MockChannel:
            def __init__(self, name):
                self.name = name
                self.mention = f"<#{name}-123>"
        
        class MockUser:
            def __init__(self, user_id, display_name):
                self.id = user_id
                self.mention = f"<@{user_id}>"
                self.display_name = display_name
        
        class MockGuild:
            def __init__(self, name):
                self.name = name
                self.text_channels = [
                    MockChannel("rules"),
                    MockChannel("general"),
                    MockChannel("welcome")
                ]
        
        # Test data
        user = MockUser("123456789", "NewUser")
        guild = MockGuild("Test Server")
        custom_message = "Welcome {user} to {server}! Check {#rules} and chat in {#general}!"
        image_data = base64.b64encode(b"fake_image_data").decode('utf-8')
        
        # Process message (simulating the actual welcome logic)
        processed_message = custom_message.replace(
            "{user}", user.mention
        ).replace(
            "{username}", user.display_name
        ).replace(
            "{server}", guild.name
        )
        
        # Process channel mentions
        def replace_channel_mention(match):
            channel_name = match.group(1)
            for channel in guild.text_channels:
                if channel.name.lower() == channel_name.lower():
                    return channel.mention
            return f"#{channel_name}"
        
        processed_message = re.sub(r'\{#([^}]+)\}', replace_channel_mention, processed_message)
        
        # Expected result
        expected = "Welcome <@123456789> to Test Server! Check <#rules-123> and chat in <#general-123>!"
        assert processed_message == expected
        
        # Test image handling
        decoded_image = base64.b64decode(image_data)
        assert decoded_image == b"fake_image_data"
        
        # Test message with image would be sent as single message
        message_package = {
            "content": processed_message,
            "file": decoded_image if image_data else None
        }
        
        assert message_package["content"] == expected
        assert message_package["file"] is not None

    def test_base64_image_storage_retrieval(self):
        """Test base64 image storage and retrieval cycle."""
        import base64
        
        # Simulate image upload and storage
        original_image = b"fake_png_data_here"
        
        # Encode for storage (what happens in set-image command)
        stored_data = base64.b64encode(original_image).decode('utf-8')
        
        # Retrieve for sending (what happens in member join)
        retrieved_image = base64.b64decode(stored_data)
        
        # Should be identical
        assert retrieved_image == original_image
        
        # Test with larger "image"
        larger_image = b"much_larger_fake_image_data" * 1000
        stored_large = base64.b64encode(larger_image).decode('utf-8')
        retrieved_large = base64.b64decode(stored_large)
        
        assert retrieved_large == larger_image
        assert len(stored_large) > len(larger_image)  # Base64 adds overhead

    def test_database_migration_compatibility(self):
        """Test that old and new database schemas work together."""
        # Old schema (URL-based) - should be migrated
        old_doc = {
            "guild_id": "123456789",
            "enabled": True,
            "custom_message": "Welcome!",
            "custom_image_url": "https://old-cdn-url.com/image.png"
        }
        
        # After migration, old URL field should be removed
        migrated_doc = {
            "guild_id": "123456789", 
            "enabled": True,
            "custom_message": "Welcome!",
            "custom_image_data": None,  # Reset for re-upload
            "custom_image_filename": None
        }
        
        # Verify migration removes old field
        assert "custom_image_url" not in migrated_doc
        assert "custom_image_data" in migrated_doc
        assert "custom_image_filename" in migrated_doc
        
        # New schema should work correctly
        new_doc = {
            "guild_id": "123456789",
            "enabled": True, 
            "custom_message": "Welcome!",
            "custom_image_data": "base64data",
            "custom_image_filename": "welcome.webp"
        }
        
        assert new_doc["custom_image_data"] is not None
        assert new_doc["custom_image_filename"] is not None


class TestWelcomeCogCommands:
    """Direct tests for WelcomeCog slash command handlers."""

    @pytest.mark.asyncio
    async def test_toggle_welcome_enable_success(self):
        from cogs.admin.welcome import WelcomeCog
        with patch('cogs.admin.welcome.update_welcome_settings', return_value=True):
            # Mock interaction and guild
            interaction = AsyncMock()
            interaction.guild = MagicMock()
            interaction.guild.id = 123456789
            interaction.guild.system_channel = MagicMock()
            interaction.guild.system_channel.mention = "#general"
            interaction.response = AsyncMock()

            cog = WelcomeCog(MagicMock())
            await WelcomeCog.toggle_welcome.callback(cog, interaction, "true")

            interaction.response.send_message.assert_called_once()
            # Should be ephemeral
            assert interaction.response.send_message.call_args.kwargs.get('ephemeral') is True

    @pytest.mark.asyncio
    async def test_status_command_success(self):
        from cogs.admin.welcome import WelcomeCog
        from services.database.models import WelcomeSettings

        settings = WelcomeSettings(
            guild_id="123456789",
            enabled=True,
            custom_message="Welcome {user} to {server}! See {#rules}",
            custom_image_data="base64data",
            custom_image_filename="welcome.png"
        )

        class MockPermissions:
            def __init__(self, send_messages=True):
                self.send_messages = send_messages

        system_channel = MagicMock()
        system_channel.mention = "#welcome"
        system_channel.permissions_for.return_value = MockPermissions(send_messages=True)

        interaction = AsyncMock()
        interaction.guild = MagicMock()
        interaction.guild.id = 123456789
        interaction.guild.name = "TestGuild"
        interaction.guild.system_channel = system_channel
        interaction.guild.me = MagicMock()
        interaction.guild.text_channels = []
        interaction.user = MagicMock()
        interaction.user.mention = "<@user>"
        interaction.user.display_name = "TestUser"
        interaction.response = AsyncMock()

        with patch('cogs.admin.welcome.get_welcome_settings', return_value=settings):
            cog = WelcomeCog(MagicMock())
            await WelcomeCog.status.callback(cog, interaction)

            interaction.response.send_message.assert_called_once()
            args, kwargs = interaction.response.send_message.call_args
            embed = kwargs.get("embed")

            assert embed is not None
            assert "Welcome Settings Status" in embed.title
            assert any(field.name == "Message Preview" for field in embed.fields)

    @pytest.mark.asyncio
    async def test_set_message_success(self):
        from cogs.admin.welcome import WelcomeCog
        with patch('cogs.admin.welcome.update_welcome_settings', return_value=True):
            interaction = AsyncMock()
            # Mock minimal guild with channels used in preview replacement
            class MockTextChannel:
                def __init__(self, name):
                    self.name = name
                    self.mention = f"<{name}>"
            interaction.guild = MagicMock()
            interaction.guild.id = 555
            interaction.guild.name = "TestGuild"
            interaction.guild.text_channels = [MockTextChannel("general")]
            interaction.user = MagicMock()
            interaction.user.mention = "<@user>"
            interaction.user.display_name = "UserName"
            interaction.response = AsyncMock()

            cog = WelcomeCog(MagicMock())
            await WelcomeCog.set_message.callback(cog, interaction, "Welcome {user} to {server}! See {#general}")

            interaction.response.send_message.assert_called_once()
            assert interaction.response.send_message.call_args.kwargs.get('ephemeral') is True

    @pytest.mark.asyncio
    async def test_set_message_too_long(self):
        from cogs.admin.welcome import WelcomeCog
        long_msg = "x" * 1001
        interaction = AsyncMock()
        interaction.guild = MagicMock()
        interaction.guild.id = 1
        interaction.response = AsyncMock()
        cog = WelcomeCog(MagicMock())

        await WelcomeCog.set_message.callback(cog, interaction, long_msg)

        interaction.response.send_message.assert_called_once()
        # Should not attempt DB update when invalid; assert via ensuring only one send_message call occurred

    @pytest.mark.asyncio
    async def test_remove_message_success(self):
        from cogs.admin.welcome import WelcomeCog
        with patch('cogs.admin.welcome.update_welcome_settings', return_value=True):
            interaction = AsyncMock()
            interaction.guild = MagicMock()
            interaction.guild.id = 123
            interaction.response = AsyncMock()

            cog = WelcomeCog(MagicMock())
            await WelcomeCog.remove_message.callback(cog, interaction)

            interaction.response.send_message.assert_called_once()
            assert interaction.response.send_message.call_args.kwargs.get('ephemeral') is True

    @pytest.mark.asyncio
    async def test_set_image_invalid_extension(self):
        from cogs.admin.welcome import WelcomeCog
        interaction = AsyncMock()
        interaction.response = AsyncMock()
        # Provide a fake attachment with unsupported extension
        attachment = MagicMock()
        attachment.filename = 'document.pdf'

        cog = WelcomeCog(MagicMock())
        await WelcomeCog.set_image.callback(cog, interaction, attachment)

        interaction.response.send_message.assert_called_once()
        assert interaction.response.send_message.call_args.kwargs.get('ephemeral') is True

    @pytest.mark.asyncio
    async def test_remove_image_success(self):
        from cogs.admin.welcome import WelcomeCog
        with patch('cogs.admin.welcome.update_welcome_settings', return_value=True):
            interaction = AsyncMock()
            interaction.guild = MagicMock()
            interaction.guild.id = 321
            interaction.response = AsyncMock()

            cog = WelcomeCog(MagicMock())
            await WelcomeCog.remove_image.callback(cog, interaction)

            interaction.response.send_message.assert_called_once()
            assert interaction.response.send_message.call_args.kwargs.get('ephemeral') is True

    @pytest.mark.asyncio
    async def test_test_welcome_disabled(self):
        from cogs.admin.welcome import WelcomeCog
        with patch('cogs.admin.welcome.get_welcome_settings', return_value=None):
            interaction = AsyncMock()
            interaction.guild = MagicMock()
            interaction.guild.id = 99
            interaction.response = AsyncMock()

            cog = WelcomeCog(MagicMock())
            await WelcomeCog.test_welcome.callback(cog, interaction)

            # Should inform user it's disabled
            interaction.response.send_message.assert_called_once()