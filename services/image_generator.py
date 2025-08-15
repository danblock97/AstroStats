"""
Dynamic image generation service for catfight battles.
Creates battle images with user avatars and backgrounds.
"""
import asyncio
import aiohttp
import logging
from io import BytesIO
from typing import Optional, Tuple
import requests

# Try to import PIL, fallback if not available
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
    ImageDraw = None
    ImageFont = None
    ImageFilter = None

logger = logging.getLogger(__name__)

class BattleImageGenerator:
    """Generates dynamic battle images with user avatars."""
    
    def __init__(self):
        self.default_size = (400, 250)  # Smaller to match embed width
        self.avatar_size = (120, 120)   # Bigger avatars for better visibility
        self.pil_available = PIL_AVAILABLE
        
    async def download_avatar(self, avatar_url: str) -> Optional[Image.Image]:
        """Download and process user avatar."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(avatar_url) as response:
                    if response.status == 200:
                        avatar_data = await response.read()
                        avatar = Image.open(BytesIO(avatar_data))
                        avatar = avatar.convert('RGBA')
                        avatar = avatar.resize(self.avatar_size, Image.Resampling.LANCZOS)
                        
                        # Create circular mask
                        mask = Image.new('L', self.avatar_size, 0)
                        draw = ImageDraw.Draw(mask)
                        draw.ellipse((0, 0) + self.avatar_size, fill=255)
                        
                        # Apply mask to make avatar circular
                        avatar.putalpha(mask)
                        return avatar
        except Exception as e:
            logger.error(f"Failed to download avatar from {avatar_url}: {e}")
            
        return self.create_default_avatar()
    
    def create_default_avatar(self) -> Image.Image:
        """Create a default avatar when download fails."""
        avatar = Image.new('RGBA', self.avatar_size, (100, 100, 100, 255))
        draw = ImageDraw.Draw(avatar)
        
        # Draw a simple cat silhouette
        center_x, center_y = self.avatar_size[0] // 2, self.avatar_size[1] // 2
        draw.ellipse(
            (center_x - 30, center_y - 20, center_x + 30, center_y + 40),
            fill=(50, 50, 50, 255)
        )
        
        # Cat ears
        draw.polygon(
            [(center_x - 20, center_y - 20), (center_x - 35, center_y - 45), (center_x - 10, center_y - 35)],
            fill=(50, 50, 50, 255)
        )
        draw.polygon(
            [(center_x + 10, center_y - 35), (center_x + 35, center_y - 45), (center_x + 20, center_y - 20)],
            fill=(50, 50, 50, 255)
        )
        
        return avatar
    
    def create_gradient_background(self) -> Image.Image:
        """Create a vibrant gradient background."""
        # Create gradient from pink to orange to yellow
        background = Image.new('RGBA', self.default_size, (255, 255, 255, 255))
        draw = ImageDraw.Draw(background)
        
        width, height = self.default_size
        
        # Create horizontal gradient
        for x in range(width):
            # Calculate color transition
            ratio = x / width
            if ratio < 0.33:
                # Pink to magenta
                r = int(255 - (255 - 219) * (ratio * 3))
                g = int(64 + (20 - 64) * (ratio * 3))
                b = int(129 + (147 - 129) * (ratio * 3))
            elif ratio < 0.66:
                # Magenta to orange
                local_ratio = (ratio - 0.33) * 3
                r = int(219 + (255 - 219) * local_ratio)
                g = int(20 + (140 - 20) * local_ratio)
                b = int(147 - 147 * local_ratio)
            else:
                # Orange to yellow
                local_ratio = (ratio - 0.66) * 3
                r = 255
                g = int(140 + (215 - 140) * local_ratio)
                b = int(0 + (80 * local_ratio))
            
            draw.line([(x, 0), (x, height)], fill=(r, g, b, 255))
        
        # Add some decorative elements
        self.add_decorative_elements(draw, width, height)
        
        return background
    
    def add_decorative_elements(self, draw: ImageDraw.Draw, width: int, height: int):
        """Add decorative elements to the background."""
        import random
        
        # Add some sparkle effects
        for _ in range(15):
            x = random.randint(0, width)
            y = random.randint(0, height)
            size = random.randint(3, 8)
            
            # Create star shape
            points = []
            for i in range(10):
                angle = i * 36  # 360 / 10
                if i % 2 == 0:
                    radius = size
                else:
                    radius = size // 2
                
                import math
                px = x + radius * math.cos(math.radians(angle))
                py = y + radius * math.sin(math.radians(angle))
                points.append((px, py))
            
            draw.polygon(points, fill=(255, 255, 255, 180))
    
    def add_sword_emoji(self, background: Image.Image) -> Image.Image:
        """Add crossed swords emoji in the center."""
        draw = ImageDraw.Draw(background)
        width, height = background.size
        center_x, center_y = width // 2, height // 2
        
        try:
            # Try to load a larger font for the emoji
            emoji_size = 60
            font = ImageFont.truetype("NotoColorEmoji.ttf", emoji_size)
        except:
            try:
                font = ImageFont.truetype("arial.ttf", 48)
            except:
                font = ImageFont.load_default()
        
        # Use actual crossed swords emoji
        swords_emoji = "⚔️"
        
        # Get text size for centering
        try:
            bbox = draw.textbbox((0, 0), swords_emoji, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except:
            # Fallback for older PIL versions
            text_width = 50
            text_height = 50
        
        emoji_x = center_x - text_width // 2
        emoji_y = center_y - text_height // 2
        
        # Draw outline for better visibility
        outline_color = (0, 0, 0, 200)
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                if dx != 0 or dy != 0:
                    draw.text((emoji_x + dx, emoji_y + dy), swords_emoji, font=font, fill=outline_color)
        
        # Draw main emoji
        draw.text((emoji_x, emoji_y), swords_emoji, font=font, fill=(255, 255, 255, 255))
        
        return background
    
    async def create_battle_image(self, user1_avatar_url: str, user2_avatar_url: str, 
                                 user1_name: str, user2_name: str) -> Optional[BytesIO]:
        """Create the complete battle image."""
        if not self.pil_available:
            logger.warning("PIL not available, skipping image generation")
            return None
            
        try:
            # Create background
            background = self.create_gradient_background()
            
            # Download avatars
            avatar1_task = self.download_avatar(user1_avatar_url)
            avatar2_task = self.download_avatar(user2_avatar_url)
            
            avatar1, avatar2 = await asyncio.gather(avatar1_task, avatar2_task)
            
            if not avatar1:
                avatar1 = self.create_default_avatar()
            if not avatar2:
                avatar2 = self.create_default_avatar()
            
            # Position avatars (adjust for smaller image)
            width, height = background.size
            avatar_y = (height - self.avatar_size[1]) // 2
            
            # Left avatar position (closer to edges for smaller image)
            left_x = 20
            # Right avatar position  
            right_x = width - self.avatar_size[0] - 20
            
            # Add glow effect to avatars
            avatar1_glow = self.add_glow_effect(avatar1, (255, 100, 100, 100))
            avatar2_glow = self.add_glow_effect(avatar2, (100, 100, 255, 100))
            
            # Paste avatars with glow
            background.paste(avatar1_glow, (left_x - 10, avatar_y - 10), avatar1_glow)
            background.paste(avatar1, (left_x, avatar_y), avatar1)
            
            background.paste(avatar2_glow, (right_x - 10, avatar_y - 10), avatar2_glow)
            background.paste(avatar2, (right_x, avatar_y), avatar2)
            
            # Add crossed swords
            background = self.add_sword_emoji(background)
            
            # Add user names
            self.add_user_names(background, user1_name, user2_name, left_x, right_x, avatar_y)
            
            # Convert to BytesIO
            img_bytes = BytesIO()
            background.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            return img_bytes
            
        except Exception as e:
            logger.error(f"Failed to create battle image: {e}")
            return self.create_fallback_image()
    
    def add_glow_effect(self, avatar: Image.Image, glow_color: Tuple[int, int, int, int]) -> Image.Image:
        """Add a glow effect around the avatar."""
        glow_size = (self.avatar_size[0] + 20, self.avatar_size[1] + 20)
        glow = Image.new('RGBA', glow_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(glow)
        
        # Draw multiple circles for glow effect
        center_x, center_y = glow_size[0] // 2, glow_size[1] // 2
        for i in range(5):
            alpha = max(10, glow_color[3] - i * 20)
            radius = self.avatar_size[0] // 2 + i * 2
            
            draw.ellipse(
                (center_x - radius, center_y - radius, center_x + radius, center_y + radius),
                fill=(*glow_color[:3], alpha)
            )
        
        return glow
    
    def add_user_names(self, background: Image.Image, user1_name: str, user2_name: str,
                      left_x: int, right_x: int, avatar_y: int):
        """Add user names below avatars."""
        draw = ImageDraw.Draw(background)
        
        try:
            # Try to load a better font
            font_size = 24
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        # Truncate names if too long
        user1_display = user1_name[:12] + "..." if len(user1_name) > 15 else user1_name
        user2_display = user2_name[:12] + "..." if len(user2_name) > 15 else user2_name
        
        # Calculate text positions
        name_y = avatar_y + self.avatar_size[1] + 10
        
        # Draw names with outline for better visibility
        outline_color = (0, 0, 0, 255)
        text_color = (255, 255, 255, 255)
        
        # User 1 name (left)
        bbox1 = draw.textbbox((0, 0), user1_display, font=font)
        text1_width = bbox1[2] - bbox1[0]
        text1_x = left_x + (self.avatar_size[0] - text1_width) // 2
        
        # Draw outline
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx != 0 or dy != 0:
                    draw.text((text1_x + dx, name_y + dy), user1_display, font=font, fill=outline_color)
        
        # Draw main text
        draw.text((text1_x, name_y), user1_display, font=font, fill=text_color)
        
        # User 2 name (right)
        bbox2 = draw.textbbox((0, 0), user2_display, font=font)
        text2_width = bbox2[2] - bbox2[0]
        text2_x = right_x + (self.avatar_size[0] - text2_width) // 2
        
        # Draw outline
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx != 0 or dy != 0:
                    draw.text((text2_x + dx, name_y + dy), user2_display, font=font, fill=outline_color)
        
        # Draw main text
        draw.text((text2_x, name_y), user2_display, font=font, fill=text_color)
    
    def create_fallback_image(self) -> BytesIO:
        """Create a simple fallback image if generation fails."""
        img = Image.new('RGB', (400, 200), (100, 100, 100))
        draw = ImageDraw.Draw(img)
        draw.text((150, 90), "Battle Image", fill=(255, 255, 255))
        
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        return img_bytes


# Global instance
battle_image_generator = BattleImageGenerator()