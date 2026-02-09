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
import math
import random

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
        self.avatar_size = (168, 168)   # Poster-style fighter portraits
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
        """Create a refreshed comic-style background with new colors."""
        background = Image.new('RGBA', self.default_size, (8, 20, 46, 255))
        draw = ImageDraw.Draw(background)
        width, height = self.default_size

        # Vertical deep-blue to cyan-violet gradient.
        for y in range(height):
            ratio = y / max(1, height - 1)
            r = int(8 + (38 - 8) * ratio)
            g = int(20 + (86 - 20) * ratio)
            b = int(46 + (124 - 46) * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

        # Add aurora-like wave strokes for texture.
        for i in range(12):
            y_base = int((i + 1) * height / 13)
            amp = 9 + i % 4
            color = (70 + i * 8, 120 + i * 6, 205 - i * 4, 74)
            points = []
            for x in range(0, width + 1, 14):
                y = y_base + int(math.sin((x / 34.0) + i) * amp)
                points.append((x, y))
            draw.line(points, fill=color, width=3)

        self.add_light_bursts(background)
        self.add_decorative_elements(draw, width, height)
        return background
    
    def add_decorative_elements(self, draw: ImageDraw.Draw, width: int, height: int):
        """Add confetti particles that match the command art style."""
        confetti_colors = [
            (255, 238, 0, 220), (52, 255, 118, 220), (255, 77, 123, 220),
            (0, 230, 255, 220), (255, 156, 30, 220), (188, 134, 255, 220),
        ]
        for _ in range(85):
            x = random.randint(0, width)
            y = random.randint(0, height)
            w = random.randint(3, 7)
            h = random.randint(2, 4)
            color = random.choice(confetti_colors)
            if random.random() < 0.4:
                draw.ellipse((x, y, x + w, y + h), fill=color)
                continue
            angle = math.radians(random.randint(-35, 35))
            cx, cy = x + (w / 2), y + (h / 2)
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            corners = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
            points = []
            for px, py in corners:
                rx = cx + (px * cos_a - py * sin_a)
                ry = cy + (px * sin_a + py * cos_a)
                points.append((rx, ry))
            draw.polygon(points, fill=color)
    
    def add_light_bursts(self, background: Image.Image):
        """Add soft light bursts for depth."""
        width, height = background.size
        overlay = Image.new("RGBA", background.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.ellipse((width * 0.02, height * 0.08, width * 0.46, height * 0.86), fill=(44, 255, 205, 34))
        draw.ellipse((width * 0.52, height * 0.0, width * 0.98, height * 0.68), fill=(139, 87, 255, 32))
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
                "Impact.ttf",
                "Arial Black.ttf",
                "Arial Bold.ttf",
                "DejaVuSans-Bold.ttf",
                "NotoSans-Bold.ttf",
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
        """Add large center VS text with drop-shadow."""
        draw = ImageDraw.Draw(background)
        width, height = background.size
        center_x, center_y = width // 2, int(height * 0.49)
        font = self.load_font(56, bold=True)
        label = "VS"
        try:
            bbox = draw.textbbox((0, 0), label, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except Exception:
            text_width = 30
            text_height = 18
        text_x = center_x - text_width // 2
        text_y = center_y - text_height // 2
        draw.text((text_x + 4, text_y + 4), label, font=font, fill=(58, 14, 26, 235))
        draw.text((text_x, text_y), label, font=font, fill=(248, 255, 255, 255))
        return background

    def draw_title(self, background: Image.Image):
        """Draw CATFIGHT title with heavy comic styling."""
        draw = ImageDraw.Draw(background)
        title = "CATFIGHT"
        font = self.load_font(74, bold=True)
        width, _ = background.size
        bbox = draw.textbbox((0, 0), title, font=font)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) // 2
        y = 10
        # Shadow, then accent, then face.
        draw.text((x + 6, y + 6), title, font=font, fill=(7, 15, 32, 245))
        draw.text((x + 2, y + 1), title, font=font, fill=(57, 255, 220, 255))
        draw.text((x, y), title, font=font, fill=(245, 253, 255, 255))

    def style_avatar(self, avatar: Image.Image, grayscale: bool = False) -> Image.Image:
        """Apply subtle color grading for each fighter side."""
        portrait = avatar.copy().convert("RGBA")
        if grayscale:
            gray = portrait.convert("L")
            portrait = Image.merge("RGBA", (gray, gray, gray, portrait.split()[-1]))
            tint = Image.new("RGBA", portrait.size, (95, 110, 135, 74))
        else:
            tint = Image.new("RGBA", portrait.size, (255, 178, 86, 54))
        portrait.alpha_composite(tint)
        return portrait

    def draw_panel(self, background: Image.Image, x: int, y: int, avatar: Image.Image, left_side: bool):
        """Draw one fighter card panel."""
        draw = ImageDraw.Draw(background)
        panel_w = self.avatar_size[0] + 10
        panel_h = self.avatar_size[1] + 40
        fill = (14, 55, 86, 200) if left_side else (90, 36, 88, 210)
        border = (48, 239, 210, 255) if left_side else (213, 124, 255, 255)
        bar = (0, 219, 186, 255) if left_side else (178, 68, 255, 255)
        draw.rectangle((x, y, x + panel_w, y + panel_h), fill=fill, outline=border, width=3)
        draw.rectangle((x, y + panel_h - 28, x + panel_w, y + panel_h), fill=bar)
        portrait = self.style_avatar(avatar, grayscale=not left_side)
        background.paste(portrait, (x + 5, y + 5), portrait)

    def draw_icon_badges(self, background: Image.Image):
        """Add trophy and RIP icon badges near the bottom."""
        draw = ImageDraw.Draw(background)
        trophy_font = self.load_font(54, bold=False)
        rip_font = self.load_font(56, bold=False)
        draw.text((95, 220), "🏆", font=trophy_font, fill=(255, 255, 255, 255))
        draw.text((332, 218), "🪦", font=rip_font, fill=(255, 255, 255, 255))
    
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
            
            # Compose poster style.
            left_x, panel_y = 22, 64
            right_x = self.default_size[0] - (self.avatar_size[0] + 10) - 22
            self.draw_panel(background, left_x, panel_y, avatar1, left_side=True)
            self.draw_panel(background, right_x, panel_y, avatar2, left_side=False)
            background = self.add_vs_badge(background)
            self.draw_icon_badges(background)

            # Add user names to panel bars.
            self.add_user_names(background, user1_name, user2_name, left_x, right_x, panel_y + self.avatar_size[1] + 15)
            # Keep title on top of all effects/elements.
            self.draw_title(background)
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
                      left_x: int, right_x: int, text_y: int):
        """Add names centered over each panel footer."""
        draw = ImageDraw.Draw(background)
        font = self.load_font(24, bold=True)

        user1_display = self.sanitize_name(user1_name)
        user2_display = self.sanitize_name(user2_name)
        
        panel_w = self.avatar_size[0] + 10
        max_width = panel_w - 14
        user1_display = self.fit_text(draw, user1_display, font, max_width)
        user2_display = self.fit_text(draw, user2_display, font, max_width)

        outline_color = (42, 8, 22, 230)
        text_color = (245, 255, 245, 255)

        # User 1 name (left)
        bbox1 = draw.textbbox((0, 0), user1_display, font=font)
        text1_width = bbox1[2] - bbox1[0]
        text1_x = left_x + (panel_w - text1_width) // 2
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx != 0 or dy != 0:
                    draw.text((text1_x + dx, text_y + dy), user1_display, font=font, fill=outline_color)
        draw.text((text1_x, text_y), user1_display, font=font, fill=text_color)

        # User 2 name (right)
        bbox2 = draw.textbbox((0, 0), user2_display, font=font)
        text2_width = bbox2[2] - bbox2[0]
        text2_x = right_x + (panel_w - text2_width) // 2
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx != 0 or dy != 0:
                    draw.text((text2_x + dx, text_y + dy), user2_display, font=font, fill=outline_color)
        draw.text((text2_x, text_y), user2_display, font=font, fill=text_color)

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
