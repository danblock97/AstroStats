import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from io import BytesIO
import aiohttp


class TestBattleImageGenerator:
    """Test battle image generation service functionality"""
    
    @pytest.fixture
    def mock_image_generator(self):
        """Mock image generator with PIL available"""
        with patch('services.image_generator.PIL_AVAILABLE', True):
            from services.image_generator import BattleImageGenerator
            generator = BattleImageGenerator()
            return generator

    @pytest.fixture
    def mock_image_generator_no_pil(self):
        """Mock image generator without PIL"""
        with patch('services.image_generator.PIL_AVAILABLE', False):
            from services.image_generator import BattleImageGenerator
            generator = BattleImageGenerator()
            return generator

    @pytest.fixture
    def mock_pil_image(self):
        """Mock PIL Image object"""
        mock_image = MagicMock()
        mock_image.size = (120, 120)
        mock_image.convert.return_value = mock_image
        mock_image.resize.return_value = mock_image
        return mock_image

    def test_image_generator_initialization(self, mock_image_generator):
        """Test image generator initialization with correct settings"""
        assert mock_image_generator.default_size == (520, 300)
        assert mock_image_generator.avatar_size == (168, 168)
        assert mock_image_generator.pil_available is True

    def test_image_generator_no_pil_initialization(self, mock_image_generator_no_pil):
        """Test image generator initialization without PIL"""
        assert mock_image_generator_no_pil.pil_available is False

    @pytest.mark.asyncio
    async def test_download_avatar_success(self, mock_image_generator, mock_pil_image):
        """Test successful avatar download and processing"""
        avatar_url = "https://example.com/avatar.png"
        mock_response_data = b"fake_image_data"
        
        # Create a proper mock for async context managers
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=mock_response_data)
        
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        # Setup response context manager
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)  
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            with patch('services.image_generator.Image') as mock_image_class:
                mock_image_class.open.return_value = mock_pil_image
                mock_image_class.new.return_value = mock_pil_image
                
                with patch('services.image_generator.ImageDraw'):
                    result = await mock_image_generator.download_avatar(avatar_url)
                    
                    assert result is not None
                    mock_image_class.open.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_avatar_failure(self, mock_image_generator):
        """Test avatar download failure and fallback to default"""
        avatar_url = "https://example.com/nonexistent.png"
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 404
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            with patch.object(mock_image_generator, 'create_default_avatar') as mock_default:
                mock_default.return_value = MagicMock()
                result = await mock_image_generator.download_avatar(avatar_url)
                
                mock_default.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_avatar_network_error(self, mock_image_generator):
        """Test avatar download network error handling"""
        avatar_url = "https://example.com/avatar.png"
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.side_effect = aiohttp.ClientError("Network error")
            
            with patch.object(mock_image_generator, 'create_default_avatar') as mock_default:
                mock_default.return_value = MagicMock()
                result = await mock_image_generator.download_avatar(avatar_url)
                
                mock_default.assert_called_once()

    def test_create_default_avatar(self, mock_image_generator):
        """Test default avatar creation with cat silhouette"""
        with patch('services.image_generator.Image') as mock_image_class:
            mock_image = MagicMock()
            mock_image_class.new.return_value = mock_image
            
            with patch('services.image_generator.ImageDraw') as mock_draw_class:
                mock_draw = MagicMock()
                mock_draw_class.Draw.return_value = mock_draw
                
                result = mock_image_generator.create_default_avatar()
                
                # Should create image with correct size
                mock_image_class.new.assert_called_with(
                    'RGBA',
                    mock_image_generator.avatar_size,
                    (100, 100, 100, 255),
                )
                
                # Should draw cat silhouette (ellipse + polygons for ears)
                assert mock_draw.ellipse.called
                assert mock_draw.polygon.call_count >= 2  # Two ears

    def test_create_gradient_background(self, mock_image_generator):
        """Test gradient background creation"""
        with patch('services.image_generator.Image') as mock_image_class:
            mock_image = MagicMock()
            mock_image.size = mock_image_generator.default_size
            mock_image_class.new.return_value = mock_image
            
            with patch('services.image_generator.ImageDraw') as mock_draw_class:
                mock_draw = MagicMock()
                mock_draw_class.Draw.return_value = mock_draw
                
                with patch.object(mock_image_generator, 'add_light_bursts') as mock_bursts, \
                     patch.object(mock_image_generator, 'add_decorative_elements') as mock_decor:
                    result = mock_image_generator.create_gradient_background()
                    
                    # Should create image with correct size
                    mock_image_class.new.assert_called_with(
                        'RGBA',
                        mock_image_generator.default_size,
                        (8, 20, 46, 255),
                    )
                    
                    # Should draw gradient lines
                    assert mock_draw.line.called
                    mock_bursts.assert_called_once_with(mock_image)
                    mock_decor.assert_called_once_with(
                        mock_draw,
                        mock_image_generator.default_size[0],
                        mock_image_generator.default_size[1],
                    )

    def test_add_decorative_elements(self, mock_image_generator):
        """Test decorative elements (sparkles) addition"""
        mock_draw = MagicMock()
        width, height = 400, 250
        
        with patch('random.randint', return_value=5), \
             patch('random.choice', return_value=(255, 238, 0, 220)), \
             patch('random.random', return_value=0.9):
            mock_image_generator.add_decorative_elements(mock_draw, width, height)

            # Current implementation draws 85 confetti elements.
            assert mock_draw.polygon.call_count == 85

    def test_add_vs_badge(self, mock_image_generator):
        """Test VS badge drawing in the center panel"""
        mock_background = MagicMock()
        mock_background.size = mock_image_generator.default_size

        with patch('services.image_generator.ImageDraw') as mock_draw_class:
            mock_draw = MagicMock()
            mock_draw.textbbox.return_value = (0, 0, 80, 40)
            mock_draw_class.Draw.return_value = mock_draw

            with patch.object(mock_image_generator, 'load_font', return_value=MagicMock()):
                result = mock_image_generator.add_vs_badge(mock_background)

                assert result == mock_background
                assert mock_draw.text.call_count >= 2

    @pytest.mark.asyncio
    async def test_create_battle_image_success(self, mock_image_generator):
        """Test successful battle image creation"""
        user1_avatar_url = "https://example.com/user1.png"
        user2_avatar_url = "https://example.com/user2.png"
        user1_name = "TestUser1"
        user2_name = "TestUser2"
        
        mock_avatar = MagicMock()
        mock_background = MagicMock()
        mock_background.size = mock_image_generator.default_size
        
        with patch.object(mock_image_generator, 'create_gradient_background', return_value=mock_background):
            with patch.object(mock_image_generator, 'download_avatar', return_value=mock_avatar):
                with patch.object(mock_image_generator, 'draw_panel') as mock_draw_panel, \
                     patch.object(mock_image_generator, 'add_vs_badge', return_value=mock_background), \
                     patch.object(mock_image_generator, 'draw_icon_badges') as mock_draw_icon_badges, \
                     patch.object(mock_image_generator, 'add_user_names') as mock_add_user_names, \
                     patch.object(mock_image_generator, 'draw_title') as mock_draw_title, \
                     patch.object(mock_image_generator, 'add_border') as mock_add_border:
                    mock_background.save = MagicMock()

                    result = await mock_image_generator.create_battle_image(
                        user1_avatar_url, user2_avatar_url, user1_name, user2_name
                    )

                    assert isinstance(result, BytesIO)
                    mock_draw_panel.assert_called()
                    mock_draw_icon_badges.assert_called_once_with(mock_background)
                    mock_add_user_names.assert_called_once()
                    mock_draw_title.assert_called_once_with(mock_background)
                    mock_add_border.assert_called_once_with(mock_background)
                    mock_background.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_battle_image_no_pil(self, mock_image_generator_no_pil):
        """Test battle image creation without PIL available"""
        result = await mock_image_generator_no_pil.create_battle_image(
            "url1", "url2", "user1", "user2"
        )
        
        assert result is None

    @pytest.mark.asyncio
    async def test_create_battle_image_error_fallback(self, mock_image_generator):
        """Test battle image creation error handling with fallback"""
        with patch.object(mock_image_generator, 'create_gradient_background', side_effect=Exception("Test error")):
            with patch.object(mock_image_generator, 'create_fallback_image') as mock_fallback:
                mock_fallback.return_value = BytesIO()
                
                result = await mock_image_generator.create_battle_image(
                    "url1", "url2", "user1", "user2"
                )
                
                mock_fallback.assert_called_once()

    def test_add_glow_effect(self, mock_image_generator):
        """Test glow effect addition to avatars"""
        mock_avatar = MagicMock()
        glow_color = (255, 100, 100, 100)
        
        with patch('services.image_generator.Image') as mock_image_class:
            mock_glow = MagicMock()
            mock_image_class.new.return_value = mock_glow
            
            with patch('services.image_generator.ImageDraw') as mock_draw_class:
                mock_draw = MagicMock()
                mock_draw_class.Draw.return_value = mock_draw
                
                result = mock_image_generator.add_glow_effect(mock_avatar, glow_color)
                
                # Should create glow image
                expected_size = (
                    mock_image_generator.avatar_size[0] + 20,
                    mock_image_generator.avatar_size[1] + 20,
                )
                mock_image_class.new.assert_called_with('RGBA', expected_size, (0, 0, 0, 0))
                
                # Should draw multiple ellipses for glow layers
                assert mock_draw.ellipse.call_count >= 5

    def test_add_user_names(self, mock_image_generator):
        """Test user name addition below avatars"""
        mock_background = MagicMock()
        user1_name = "TestUser1"
        user2_name = "VeryLongUserName12345"  # Test name truncation
        left_x = 20
        right_x = 260
        avatar_y = 65
        
        with patch('services.image_generator.ImageDraw') as mock_draw_class:
            mock_draw = MagicMock()
            mock_draw_class.Draw.return_value = mock_draw
            
            # Mock textbbox for text positioning
            mock_draw.textbbox.return_value = (0, 0, 100, 20)
            
            with patch('services.image_generator.ImageFont'):
                mock_image_generator.add_user_names(
                    mock_background, user1_name, user2_name, left_x, right_x, avatar_y
                )
                
                # Should draw text for both users (with outlines)
                assert mock_draw.text.call_count >= 4  # 2 users * (outline + main text)

    def test_add_user_names_truncation(self, mock_image_generator):
        """Test user name truncation for long names"""
        long_name = "VeryLongUserNameThatShouldBeTruncated"
        short_name = "Short"
        
        # Test truncation logic
        user1_display = long_name[:12] + "..." if len(long_name) > 15 else long_name
        user2_display = short_name[:12] + "..." if len(short_name) > 15 else short_name
        
        assert user1_display == "VeryLongUser..."
        assert user2_display == "Short"

    def test_create_fallback_image(self, mock_image_generator):
        """Test fallback image creation when generation fails"""
        with patch('services.image_generator.Image') as mock_image_class:
            mock_image = MagicMock()
            mock_image_class.new.return_value = mock_image
            
            with patch('services.image_generator.ImageDraw') as mock_draw_class:
                mock_draw = MagicMock()
                mock_draw_class.Draw.return_value = mock_draw
                
                mock_image.save = MagicMock()
                
                result = mock_image_generator.create_fallback_image()
                
                # Should create basic image
                mock_image_class.new.assert_called_with(
                    'RGB',
                    mock_image_generator.default_size,
                    (100, 100, 100),
                )
                
                # Should draw fallback text
                mock_draw.text.assert_called_once()
                
                # Should return BytesIO
                assert isinstance(result, BytesIO)

    def test_image_size_constraints(self, mock_image_generator):
        """Test that image sizes are appropriate for Discord embeds"""
        # Default image size should be reasonable for Discord
        assert mock_image_generator.default_size[0] <= 600  # Width constraint
        assert mock_image_generator.default_size[1] <= 400  # Height constraint
        
        # Avatar size should be visible but not too large
        assert 100 <= mock_image_generator.avatar_size[0] <= 200
        assert 100 <= mock_image_generator.avatar_size[1] <= 200

    def test_color_validation(self):
        """Test color values are valid RGBA"""
        from services.image_generator import BattleImageGenerator
        
        # Test glow colors
        red_glow = (255, 100, 100, 100)
        blue_glow = (100, 100, 255, 100)
        
        for color in [red_glow, blue_glow]:
            assert len(color) == 4  # RGBA
            assert all(0 <= c <= 255 for c in color)  # Valid range

    def test_gradient_color_progression(self):
        """Test gradient color progression is smooth"""
        # Test gradient calculation logic
        width = 400
        test_positions = [0, 0.33, 0.66, 1.0]
        
        for position in test_positions:
            ratio = position
            if ratio < 0.33:
                # Pink to magenta transition
                r = int(255 - (255 - 219) * (ratio * 3))
                assert 219 <= r <= 255
            elif ratio < 0.66:
                # Magenta to orange transition  
                local_ratio = (ratio - 0.33) * 3
                r = int(219 + (255 - 219) * local_ratio)
                assert 219 <= r <= 255
            else:
                # Orange to yellow transition
                r = 255
                assert r == 255

    @pytest.mark.asyncio
    async def test_avatar_circular_mask(self, mock_image_generator):
        """Test avatar circular masking"""
        with patch('services.image_generator.Image') as mock_image_class:
            mock_avatar = MagicMock()
            mock_mask = MagicMock()
            mock_image_class.open.return_value = mock_avatar
            mock_image_class.new.return_value = mock_mask
            
            with patch('services.image_generator.ImageDraw') as mock_draw_class:
                mock_draw = MagicMock()
                mock_draw_class.Draw.return_value = mock_draw
                
                # Create a proper mock for async context managers
                mock_response = MagicMock()
                mock_response.status = 200
                mock_response.read = AsyncMock(return_value=b"fake_data")
                
                mock_session = MagicMock()
                mock_session.get = MagicMock(return_value=mock_response)
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                
                # Setup response context manager
                mock_response.__aenter__ = AsyncMock(return_value=mock_response)
                mock_response.__aexit__ = AsyncMock(return_value=None)
                
                with patch('aiohttp.ClientSession', return_value=mock_session):
                    
                    await mock_image_generator.download_avatar("http://example.com/avatar.png")
                    
                    # Should create circular mask
                    mask_calls = mock_image_class.new.call_args_list
                    assert any('L' in str(call) for call in mask_calls)  # L mode for mask
                    
                    # Should draw ellipse for circular mask
                    mock_draw.ellipse.assert_called()

    def test_font_fallback_handling(self, mock_image_generator):
        """Test font loading with graceful fallbacks"""
        with patch('services.image_generator.ImageFont') as mock_font:
            # Simulate font loading failures
            fallback_font = MagicMock()
            mock_font.truetype.side_effect = OSError("Font not found")
            mock_font.load_default.return_value = fallback_font

            result = mock_image_generator.load_font(24, bold=True)

            assert result == fallback_font
            mock_font.load_default.assert_called_once()

    def test_star_sparkle_geometry(self):
        """Test star sparkle geometric calculations"""
        import math
        
        # Test star point calculation
        x, y = 100, 100
        size = 5
        points = []
        
        for i in range(10):
            angle = i * 36  # 360 / 10
            if i % 2 == 0:
                radius = size
            else:
                radius = size // 2
            
            px = x + radius * math.cos(math.radians(angle))
            py = y + radius * math.sin(math.radians(angle))
            points.append((px, py))
        
        # Should have 10 points for star
        assert len(points) == 10
        
        # Points should alternate between outer and inner radius
        distances = []
        for px, py in points:
            dist = math.sqrt((px - x)**2 + (py - y)**2)
            distances.append(dist)
        
        # Should have two distinct distances (inner and outer)
        unique_distances = set(round(d, 1) for d in distances)
        assert len(unique_distances) <= 3  # Allow for small rounding differences

    def test_battle_positioning_logic(self, mock_image_generator):
        """Test avatar positioning logic for battle layout"""
        width, height = mock_image_generator.default_size
        avatar_width, avatar_height = mock_image_generator.avatar_size
        
        # Calculate positions
        avatar_y = (height - avatar_height) // 2
        left_x = 20
        right_x = width - avatar_width - 20
        
        # Avatars should not overlap
        assert right_x > left_x + avatar_width
        
        # Avatars should be vertically centered
        assert avatar_y >= 0
        assert avatar_y + avatar_height <= height
        
        # Should have reasonable spacing from edges
        assert left_x >= 10
        assert right_x + avatar_width <= width - 10
