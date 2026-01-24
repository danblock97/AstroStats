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
import unicodedata

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
        self.default_size = (520, 300)  # Larger for clearer UI layout
        self.avatar_size = (132, 132)   # Prominent avatars
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
        # Create layered gradient for depth
        background = Image.new('RGBA', self.default_size, (30, 30, 40, 255))
        draw = ImageDraw.Draw(background)
        
        width, height = self.default_size
        
        # Create horizontal gradient
        for x in range(width):
            # Calculate color transition
            ratio = x / width
            if ratio < 0.5:
                local_ratio = ratio * 2
                r = int(30 + (120 - 30) * local_ratio)
                g = int(40 + (70 - 40) * local_ratio)
                b = int(80 + (140 - 80) * local_ratio)
            else:
                local_ratio = (ratio - 0.5) * 2
                r = int(120 + (255 - 120) * local_ratio)
                g = int(70 + (140 - 70) * local_ratio)
                b = int(140 - (140 - 60) * local_ratio)
            
            draw.line([(x, 0), (x, height)], fill=(r, g, b, 255))
        
        # Add some decorative elements
        self.add_decorative_elements(draw, width, height)
        self.add_light_bursts(background)
        # Removed soft bars to avoid visible black strips at top/bottom
        
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
    
    def add_light_bursts(self, background: Image.Image):
        """Add soft light bursts for depth."""
        width, height = background.size
        overlay = Image.new("RGBA", background.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.ellipse((width * 0.05, height * 0.1, width * 0.45, height * 0.8), fill=(255, 255, 255, 30))
        draw.ellipse((width * 0.55, height * 0.0, width * 0.95, height * 0.7), fill=(255, 180, 120, 28))
        background.alpha_composite(overlay)

    def add_soft_bars(self, background: Image.Image):
        """Add subtle top/bottom bars to frame the scene."""
        draw = ImageDraw.Draw(background)
        width, height = background.size
        draw.rectangle((0, 0, width, 18), fill=(0, 0, 0, 28))
        draw.rectangle((0, height - 18, width, height), fill=(0, 0, 0, 28))

    def load_font(self, size: int, bold: bool = False) -> ImageFont.ImageFont:
        """Load a font with broader Unicode support when available."""
        candidates = []
        if bold:
            candidates.extend([
                "DejaVuSans-Bold.ttf",
                "NotoSans-Bold.ttf",
                "Arial Bold.ttf",
                "arialbd.ttf",
            ])
        candidates.extend([
            "DejaVuSans.ttf",
            "NotoSans-Regular.ttf",
            "Arial Unicode.ttf",
            "arial.ttf",
        ])
        for font_name in candidates:
            try:
                return ImageFont.truetype(font_name, size)
            except Exception:
                continue
        return ImageFont.load_default()

    def sanitize_name(self, name: str) -> str:
        """Normalize and clean names for image rendering."""
        cleaned = unicodedata.normalize("NFKC", name)
        cleaned = " ".join(cleaned.replace("\n", " ").replace("\r", " ").replace("\t", " ").split())
        return cleaned

    def fit_text(self, draw: ImageDraw.Draw, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
        """Trim text to fit within max width."""
        display = text
        try:
            bbox = draw.textbbox((0, 0), display, font=font)
            text_width = bbox[2] - bbox[0]
        except Exception:
            text_width = len(display) * 10
        if text_width <= max_width:
            return display
        trimmed = display
        while trimmed:
            candidate = f"{trimmed}..."
            try:
                bbox = draw.textbbox((0, 0), candidate, font=font)
                candidate_width = bbox[2] - bbox[0]
            except Exception:
                candidate_width = len(candidate) * 10
            if candidate_width <= max_width:
                return candidate
            trimmed = trimmed[:-1]
        return "..."

    def add_vs_badge(self, background: Image.Image) -> Image.Image:
        """Add a VS badge in the center."""
        draw = ImageDraw.Draw(background)
        width, height = background.size
        center_x, center_y = width // 2, height // 2
        badge_radius = 30
        badge_box = (
            center_x - badge_radius,
            center_y - badge_radius,
            center_x + badge_radius,
            center_y + badge_radius,
        )
        draw.ellipse(badge_box, fill=(15, 15, 20, 200), outline=(255, 255, 255, 200), width=2)
        font = self.load_font(26, bold=True)
        label = "VS"
        try:
            bbox = draw.textbbox((0, 0), label, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except Exception:
            text_width = 30
            text_height = 18
        text_x = center_x - text_width // 2
        text_y = center_y - text_height // 2 - 1
        draw.text((text_x, text_y), label, font=font, fill=(255, 255, 255, 255))
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
            
            # Add center badge
            background = self.add_vs_badge(background)
            
            # Add user names
            self.add_user_names(background, user1_name, user2_name, left_x, right_x, avatar_y)
            self.add_border(background)
            
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
        font = self.load_font(22, bold=True)

        user1_display = self.sanitize_name(user1_name)
        user2_display = self.sanitize_name(user2_name)
        
        # Calculate text positions
        nameplate_y = avatar_y + self.avatar_size[1] + 10
        text_y = nameplate_y - 4
        max_width = self.avatar_size[0] + 12
        user1_display = self.fit_text(draw, user1_display, font, max_width)
        user2_display = self.fit_text(draw, user2_display, font, max_width)

        outline_color = (0, 0, 0, 220)
        text_color = (255, 255, 255, 255)

        # User 1 name (left)
        bbox1 = draw.textbbox((0, 0), user1_display, font=font)
        text1_width = bbox1[2] - bbox1[0]
        text1_height = bbox1[3] - bbox1[1]
        text1_x = left_x + (self.avatar_size[0] - text1_width) // 2
        self.draw_nameplate(draw, text1_x, nameplate_y, text1_width, text1_height, (255, 120, 120, 200))
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx != 0 or dy != 0:
                    draw.text((text1_x + dx, text_y + dy), user1_display, font=font, fill=outline_color)
        draw.text((text1_x, text_y), user1_display, font=font, fill=text_color)

        # User 2 name (right)
        bbox2 = draw.textbbox((0, 0), user2_display, font=font)
        text2_width = bbox2[2] - bbox2[0]
        text2_height = bbox2[3] - bbox2[1]
        text2_x = right_x + (self.avatar_size[0] - text2_width) // 2
        self.draw_nameplate(draw, text2_x, nameplate_y, text2_width, text2_height, (120, 160, 255, 200))
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx != 0 or dy != 0:
                    draw.text((text2_x + dx, text_y + dy), user2_display, font=font, fill=outline_color)
        draw.text((text2_x, text_y), user2_display, font=font, fill=text_color)

    def draw_nameplate(self, draw: ImageDraw.Draw, text_x: int, text_y: int, text_w: int, text_h: int,
                       outline_color: Tuple[int, int, int, int]):
        """Draw a nameplate behind text."""
        pad_x = 10
        pad_y = 4
        rect = (
            text_x - pad_x,
            text_y - pad_y,
            text_x + text_w + pad_x,
            text_y + text_h + pad_y,
        )
        if hasattr(draw, "rounded_rectangle"):
            draw.rounded_rectangle(rect, radius=8, fill=(0, 0, 0, 140), outline=outline_color, width=2)
        else:
            draw.rectangle(rect, fill=(0, 0, 0, 140), outline=outline_color, width=2)

    def add_border(self, background: Image.Image):
        """Add a thin border to frame the image."""
        draw = ImageDraw.Draw(background)
        width, height = background.size
        draw.rectangle((0, 0, width - 1, height - 1), outline=(255, 255, 255, 120), width=2)
    
    def create_fallback_image(self) -> BytesIO:
        """Create a simple fallback image if generation fails."""
        img = Image.new('RGB', self.default_size, (100, 100, 100))
        draw = ImageDraw.Draw(img)
        draw.text((self.default_size[0] // 2 - 50, self.default_size[1] // 2 - 10), "Battle Image", fill=(255, 255, 255))
        
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        return img_bytes


# Global instance
battle_image_generator = BattleImageGenerator()
