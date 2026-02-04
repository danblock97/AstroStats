"""
Dynamic image generation for player stat comparisons.
Creates high-quality side-by-side comparison cards rendered at 2x then
down-scaled for crisp output on Discord.
"""
import logging
import math
from io import BytesIO
from typing import List, Optional, Tuple

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

# ---------------------------------------------------------------------------
# Internal render scale – we draw at 2x then down-sample for sharpness.
# ---------------------------------------------------------------------------
_SCALE = 2


def _s(v: int) -> int:
    """Scale a pixel value."""
    return v * _SCALE


class CompareImageGenerator:
    """Generates polished comparison card images for game stat comparisons."""

    # ── Final output dimensions (before 2x) ──────────────────────────────
    WIDTH = 800
    HEADER_H = 92
    NAME_ROW_H = 64
    ROW_H = 56
    FOOTER_H = 40
    CORNER_R = 18

    # ── Colour palette ────────────────────────────────────────────────────
    BG_TOP = (22, 24, 35)
    BG_BOT = (14, 15, 22)
    HEADER_BG = (28, 30, 42)
    NAME_BG = (24, 26, 36)
    ROW_EVEN = (26, 28, 38)
    ROW_ODD = (30, 32, 44)
    ACCENT_LEFT = (78, 172, 255)      # Soft blue
    ACCENT_RIGHT = (255, 100, 120)    # Soft red / coral
    TEXT_WHITE = (240, 242, 250)
    TEXT_DIM = (140, 145, 165)
    TEXT_LABEL = (160, 165, 185)
    WIN_CLR = (72, 220, 130)
    LOSE_CLR = (255, 80, 80)
    TIE_CLR = (170, 175, 190)
    DIVIDER = (48, 50, 65)
    FOOTER_BG = (16, 17, 24)

    # Win-bar colours (translucent overlays on winning side)
    WIN_BAR_L = (78, 172, 255, 22)
    WIN_BAR_R = (255, 100, 120, 22)

    def __init__(self):
        self.pil_available = PIL_AVAILABLE

    # ── Font helpers ──────────────────────────────────────────────────────
    def _font(self, size: int, bold: bool = False):
        """Return a TrueType font at *scaled* size, with graceful fallback."""
        real = _s(size)
        candidates = []
        if bold:
            candidates += [
                "DejaVuSans-Bold.ttf", "NotoSans-Bold.ttf",
                "Arial Bold.ttf", "arialbd.ttf",
            ]
        candidates += [
            "DejaVuSans.ttf", "NotoSans-Regular.ttf",
            "Arial Unicode.ttf", "arial.ttf",
        ]
        for name in candidates:
            try:
                return ImageFont.truetype(name, real)
            except Exception:
                continue
        return ImageFont.load_default()

    @staticmethod
    def _tw(draw, text, font) -> int:
        b = draw.textbbox((0, 0), text, font=font)
        return b[2] - b[0]

    @staticmethod
    def _th(draw, text, font) -> int:
        b = draw.textbbox((0, 0), text, font=font)
        return b[3] - b[1]

    def _trunc(self, draw, text: str, font, max_w: int) -> str:
        if self._tw(draw, text, font) <= max_w:
            return text
        t = text
        while t:
            c = t + "\u2026"  # ellipsis character
            if self._tw(draw, c, font) <= max_w:
                return c
            t = t[:-1]
        return "\u2026"

    # ── Gradient helper ───────────────────────────────────────────────────
    @staticmethod
    def _v_gradient(w: int, h: int, top: tuple, bot: tuple) -> Image.Image:
        """Create a vertical linear gradient RGBA image."""
        img = Image.new("RGBA", (w, h))
        draw = ImageDraw.Draw(img)
        for y in range(h):
            r = int(top[0] + (bot[0] - top[0]) * y / h)
            g = int(top[1] + (bot[1] - top[1]) * y / h)
            b = int(top[2] + (bot[2] - top[2]) * y / h)
            draw.line([(0, y), (w, y)], fill=(r, g, b, 255))
        return img

    # ── Rounded-rect mask ─────────────────────────────────────────────────
    @staticmethod
    def _round_mask(w: int, h: int, radius: int) -> Image.Image:
        """Return an L-mode mask with rounded corners."""
        mask = Image.new("L", (w, h), 0)
        d = ImageDraw.Draw(mask)
        d.rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
        return mask

    # ── Public API ────────────────────────────────────────────────────────
    def create_image(
        self,
        title: str,
        player1_name: str,
        player2_name: str,
        rows: List[Tuple[str, str, str]],
        accent_color: Tuple[int, int, int] = None,
        subtitle: str = "",
    ) -> Optional[BytesIO]:
        """
        Create a comparison card image.

        *rows*: list of ``(label, value1, value2)`` tuples.
        Prefix a value with ``>`` (win), ``<`` (lose), or ``=`` (tie) so the
        renderer can highlight it.  The prefix is stripped before display.
        """
        if not self.pil_available:
            logger.warning("PIL not available, cannot generate comparison image")
            return None
        try:
            return self._render(title, player1_name, player2_name,
                                rows, accent_color, subtitle)
        except Exception as e:
            logger.error(f"Failed to generate comparison image: {e}",
                         exc_info=True)
            return None

    # ── Indicator parsing ─────────────────────────────────────────────────
    @staticmethod
    def _parse(value: str) -> Tuple[str, str]:
        if value.startswith(">"):
            return value[1:], "win"
        if value.startswith("<"):
            return value[1:], "lose"
        if value.startswith("="):
            return value[1:], "tie"
        return value, ""

    # ── Core renderer ─────────────────────────────────────────────────────
    def _render(self, title, p1, p2, rows, accent, subtitle):
        W = _s(self.WIDTH)
        hdr_h = _s(self.HEADER_H)
        name_h = _s(self.NAME_ROW_H)
        row_h = _s(self.ROW_H)
        ftr_h = _s(self.FOOTER_H)
        n = len(rows)
        H = hdr_h + name_h + n * row_h + ftr_h
        corner = _s(self.CORNER_R)

        accent = accent or self.ACCENT_LEFT

        # Background gradient
        canvas = self._v_gradient(W, H, self.BG_TOP, self.BG_BOT)
        draw = ImageDraw.Draw(canvas)

        # Fonts (sizes are pre-2x, _font handles scaling)
        f_title = self._font(26, bold=True)
        f_sub   = self._font(15)
        f_name  = self._font(20, bold=True)
        f_vs    = self._font(14, bold=True)
        f_label = self._font(16)
        f_val   = self._font(18, bold=True)
        f_ind   = self._font(12, bold=True)
        f_foot  = self._font(12)

        mid = W // 2
        pad = _s(28)

        # ── Header ────────────────────────────────────────────────────────
        draw.rectangle((0, 0, W, hdr_h), fill=self.HEADER_BG + (255,))

        # Accent gradient bar (top 5px scaled)
        bar_h = _s(4)
        for x in range(W):
            ratio = x / W
            r = int(accent[0] * (1 - ratio) + self.ACCENT_RIGHT[0] * ratio)
            g = int(accent[1] * (1 - ratio) + self.ACCENT_RIGHT[1] * ratio)
            b = int(accent[2] * (1 - ratio) + self.ACCENT_RIGHT[2] * ratio)
            draw.line([(x, 0), (x, bar_h)], fill=(r, g, b, 255))

        # Title text (centred)
        t_text = self._trunc(draw, title, f_title, W - _s(60))
        t_w = self._tw(draw, t_text, f_title)
        draw.text(((W - t_w) // 2, _s(16)), t_text, font=f_title,
                  fill=self.TEXT_WHITE)

        # Subtitle
        if subtitle:
            s_text = self._trunc(draw, subtitle, f_sub, W - _s(60))
            s_w = self._tw(draw, s_text, f_sub)
            draw.text(((W - s_w) // 2, _s(52)), s_text, font=f_sub,
                      fill=self.TEXT_DIM)

        # ── Name row ──────────────────────────────────────────────────────
        ny = hdr_h
        draw.rectangle((0, ny, W, ny + name_h), fill=self.NAME_BG + (255,))

        # Thin separator line top
        draw.line([(pad, ny), (W - pad, ny)], fill=self.DIVIDER, width=1)

        left_cx = mid // 2
        right_cx = mid + mid // 2
        name_text_y = ny + (name_h - self._th(draw, "X", f_name)) // 2

        # Player 1
        p1d = self._trunc(draw, p1, f_name, mid - _s(70))
        p1w = self._tw(draw, p1d, f_name)
        p1x = left_cx - p1w // 2
        # Coloured accent bar behind name
        pill_pad_x, pill_pad_y = _s(12), _s(5)
        pill_r = _s(8)
        pill_rect_l = (p1x - pill_pad_x, name_text_y - pill_pad_y,
                       p1x + p1w + pill_pad_x, name_text_y + self._th(draw, p1d, f_name) + pill_pad_y)
        draw.rounded_rectangle(pill_rect_l, radius=pill_r,
                               fill=self.ACCENT_LEFT + (30,))
        draw.rounded_rectangle(pill_rect_l, radius=pill_r,
                               outline=self.ACCENT_LEFT + (80,), width=_s(1))
        draw.text((p1x, name_text_y), p1d, font=f_name,
                  fill=self.ACCENT_LEFT)

        # VS badge
        vs_w = self._tw(draw, "VS", f_vs)
        vs_r = _s(14)
        vs_cx, vs_cy = mid, ny + name_h // 2
        draw.ellipse((vs_cx - vs_r, vs_cy - vs_r, vs_cx + vs_r, vs_cy + vs_r),
                     fill=(40, 42, 55, 220), outline=self.DIVIDER + (180,), width=_s(1))
        draw.text((vs_cx - vs_w // 2, vs_cy - self._th(draw, "VS", f_vs) // 2),
                  "VS", font=f_vs, fill=self.TEXT_DIM)

        # Player 2
        p2d = self._trunc(draw, p2, f_name, mid - _s(70))
        p2w = self._tw(draw, p2d, f_name)
        p2x = right_cx - p2w // 2
        pill_rect_r = (p2x - pill_pad_x, name_text_y - pill_pad_y,
                       p2x + p2w + pill_pad_x, name_text_y + self._th(draw, p2d, f_name) + pill_pad_y)
        draw.rounded_rectangle(pill_rect_r, radius=pill_r,
                               fill=self.ACCENT_RIGHT + (30,))
        draw.rounded_rectangle(pill_rect_r, radius=pill_r,
                               outline=self.ACCENT_RIGHT + (80,), width=_s(1))
        draw.text((p2x, name_text_y), p2d, font=f_name,
                  fill=self.ACCENT_RIGHT)

        # Separator under names
        sep_y = ny + name_h - 1
        draw.line([(pad, sep_y), (W - pad, sep_y)], fill=self.DIVIDER, width=1)

        # ── Stat rows ─────────────────────────────────────────────────────
        rows_y0 = ny + name_h
        label_w = _s(180)
        val_w = (W - label_w) // 2

        for i, (label, raw1, raw2) in enumerate(rows):
            ry = rows_y0 + i * row_h
            bg = self.ROW_EVEN if i % 2 == 0 else self.ROW_ODD
            draw.rectangle((0, ry, W, ry + row_h), fill=bg + (255,))

            v1, ind1 = self._parse(raw1)
            v2, ind2 = self._parse(raw2)

            # Subtle highlight bar on winning side
            if ind1 == "win":
                draw.rectangle((label_w, ry, label_w + val_w, ry + row_h),
                               fill=self.WIN_BAR_L)
            if ind2 == "win":
                draw.rectangle((label_w + val_w, ry, W, ry + row_h),
                               fill=self.WIN_BAR_R)

            # Label (right-aligned in label column with padding)
            l_trunc = self._trunc(draw, label, f_label, label_w - _s(24))
            l_tw = self._tw(draw, l_trunc, f_label)
            l_x = label_w - l_tw - _s(16)
            l_ty = ry + (row_h - self._th(draw, l_trunc, f_label)) // 2
            draw.text((l_x, l_ty), l_trunc, font=f_label, fill=self.TEXT_LABEL)

            # Thin vertical divider between label and values
            draw.line([(label_w, ry + _s(8)), (label_w, ry + row_h - _s(8))],
                      fill=self.DIVIDER, width=1)

            # ── Value 1 ──────────────────────────────────────────────────
            self._draw_value(draw, v1, ind1, f_val, f_ind,
                             label_w, val_w, ry, row_h, side="left")

            # Centre column divider
            cx = label_w + val_w
            draw.line([(cx, ry + _s(8)), (cx, ry + row_h - _s(8))],
                      fill=self.DIVIDER, width=1)

            # ── Value 2 ──────────────────────────────────────────────────
            self._draw_value(draw, v2, ind2, f_val, f_ind,
                             label_w + val_w, val_w, ry, row_h, side="right")

        # ── Footer ────────────────────────────────────────────────────────
        fy = rows_y0 + n * row_h
        draw.rectangle((0, fy, W, H), fill=self.FOOTER_BG + (255,))
        draw.line([(pad, fy), (W - pad, fy)], fill=self.DIVIDER, width=1)
        ft = "AstroStats  \u2022  astrostats.info"
        ftw = self._tw(draw, ft, f_foot)
        draw.text(((W - ftw) // 2, fy + _s(10)), ft, font=f_foot,
                  fill=self.TEXT_DIM)

        # ── Round corners (mask) ──────────────────────────────────────────
        mask = self._round_mask(W, H, corner)
        bg_black = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        result = Image.composite(canvas, bg_black, mask)

        # ── Down-scale 2x → 1x with high-quality resampling ──────────────
        final = result.resize((self.WIDTH, H // _SCALE), Image.Resampling.LANCZOS)

        buf = BytesIO()
        final.save(buf, format="PNG", optimize=True)
        buf.seek(0)
        return buf

    # ── Draw a single value cell ──────────────────────────────────────────
    def _draw_value(self, draw, text, indicator, f_val, f_ind,
                    area_x, area_w, row_y, row_h, side):
        display = self._trunc(draw, text, f_val, area_w - _s(44))
        tw = self._tw(draw, display, f_val)
        ty = row_y + (row_h - self._th(draw, display, f_val)) // 2

        # Colour
        if indicator == "win":
            clr = self.WIN_CLR
        elif indicator == "lose":
            clr = self.LOSE_CLR
        elif indicator == "tie":
            clr = self.TIE_CLR
        else:
            clr = self.TEXT_WHITE

        # Centre text in cell
        tx = area_x + (area_w - tw) // 2
        draw.text((tx, ty), display, font=f_val, fill=clr)

        # Small triangle indicator
        if indicator in ("win", "lose"):
            tri_size = _s(5)
            tri_x = tx + tw + _s(6)
            tri_cy = row_y + row_h // 2
            if indicator == "win":
                # Up-pointing triangle
                draw.polygon([
                    (tri_x, tri_cy + tri_size),
                    (tri_x + tri_size, tri_cy - tri_size),
                    (tri_x + tri_size * 2, tri_cy + tri_size),
                ], fill=self.WIN_CLR)
            else:
                # Down-pointing triangle
                draw.polygon([
                    (tri_x, tri_cy - tri_size),
                    (tri_x + tri_size, tri_cy + tri_size),
                    (tri_x + tri_size * 2, tri_cy - tri_size),
                ], fill=self.LOSE_CLR)


# ── Helper used by cogs to mark values ────────────────────────────────────

def compare_values(v1, v2, v1_str: str, v2_str: str,
                   higher_is_better: bool = True) -> Tuple[str, str]:
    """
    Prefix value display strings with ``>``, ``<`` or ``=`` markers so the
    image renderer can colour-code them.
    """
    if v1 is None or v2 is None:
        return v1_str, v2_str
    try:
        n1, n2 = float(v1), float(v2)
    except (ValueError, TypeError):
        return v1_str, v2_str

    if n1 == n2:
        return f"={v1_str}", f"={v2_str}"
    if higher_is_better:
        return (f">{v1_str}", f"<{v2_str}") if n1 > n2 else (f"<{v1_str}", f">{v2_str}")
    else:
        return (f">{v1_str}", f"<{v2_str}") if n1 < n2 else (f"<{v1_str}", f">{v2_str}")


# Global instance
compare_image_generator = CompareImageGenerator()
