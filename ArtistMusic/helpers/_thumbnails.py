# ==========================================================
# Copyright (c) 2026 FushiguroXmusic
# All Rights Reserved.
#
# Project      : FushiguroXmusic API Telegram Music Bot
# Powered By   : FushiguroX
# Type         : API Based Telegram Music Bot
#
# Bot          : @FushiguroXmusicBot
# Channel      : https://t.me/fushiguroxmusic
# GitHub       : https://github.com/yourusername/FushiguroXmusic
#
# Unauthorized copying, modification, or redistribution
# of this source code without permission is prohibited.
# ==========================================================
import os
import re
import asyncio
import aiohttp
import base64

from PIL import (
    Image,
    ImageDraw,
    ImageEnhance,
    ImageFilter,
    ImageFont
)

from ArtistMusic import config
from ArtistMusic.helpers import Track


# └─ Canvas dimensions ──────────────────────────────────────────────────────────
W, H = 1280, 720

# Panel ─ centered, slight left-of-center for asymmetric layout
PANEL_W, PANEL_H = 1040, 622
PANEL_X = (W - PANEL_W) // 2
PANEL_Y = 49

# Thumbnail ─ inside panel, upper region
THUMB_W, THUMB_H = 940, 418
THUMB_X = PANEL_X + (PANEL_W - THUMB_W) // 2
THUMB_Y = PANEL_Y + 28

# Text rows
TITLE_X  = THUMB_X + 4
TITLE_Y  = THUMB_Y + THUMB_H + 22
META_Y   = TITLE_Y + 56

# Progress bar
BAR_X         = THUMB_X + 4
BAR_Y         = META_Y + 58
BAR_RED_LEN   = 340
BAR_TOTAL_LEN = 930
BAR_H         = 7    # half-height (bar drawn ±BAR_H from BAR_Y)

# Play icons strip
ICONS_W, ICONS_H = 420, 45
ICONS_X = PANEL_X + (PANEL_W - ICONS_W) // 2
ICONS_Y = BAR_Y + 68

MAX_TITLE_WIDTH = 830

# ── Palette ─────────────────────────────────────────────────────────────────────
# Primary accent: electric violet-cyan
ACCENT_A   = (140,  80, 255)   # deep violet
ACCENT_B   = (  0, 220, 255)   # cyan
ACCENT_C   = (200, 100, 255)   # light violet
WHITE      = (255, 255, 255)
DIM_WHITE  = (210, 210, 230)
MID_GREY   = (160, 160, 185)
DARK_GREY  = ( 45,  45,  60)

# Supersampling factor used for crisp, anti-aliased text rendering.
SS = 3


def trim_to_width(text: str, font, max_w: int) -> str:
    ellipsis = "…"
    if font.getlength(text) <= max_w:
        return text
    for i in range(len(text) - 1, 0, -1):
        if font.getlength(text[:i] + ellipsis) <= max_w:
            return text[:i] + ellipsis
    return ellipsis


def draw_glow_rect(draw, box, radius, color, spread=10, max_alpha=70):
    """Layered outer glow around a rounded rect."""
    x0, y0, x1, y1 = box
    for i in range(spread, 0, -1):
        alpha = int(max_alpha * (i / spread) ** 1.4)
        draw.rounded_rectangle(
            (x0 - i, y0 - i, x1 + i, y1 + i),
            radius=radius + i,
            outline=(*color[:3], alpha),
            width=1
        )


def gradient_line(draw, x0, y0, x1, y1, thickness,
                  color_a, color_b, steps=80):
    """Horizontal gradient bar drawn as thin vertical slices."""
    length = x1 - x0
    for i in range(steps):
        t  = i / (steps - 1)
        x  = int(x0 + length * i / steps)
        xn = int(x0 + length * (i + 1) / steps)
        r  = int(color_a[0] + (color_b[0] - color_a[0]) * t)
        g  = int(color_a[1] + (color_b[1] - color_a[1]) * t)
        b  = int(color_a[2] + (color_b[2] - color_a[2]) * t)
        draw.rectangle((x, y0, xn, y0 + thickness), fill=(r, g, b, 255))


def render_text_layer(text, font_path, font_size, ss=SS):
    """
    Renders `text` on its own tightly-cropped RGBA layer at `ss×`
    resolution, then downsampled with LANCZOS for clean anti-aliasing.
    """
    if font_path:
        big_font = ImageFont.truetype(font_path, font_size * ss)
    else:
        big_font = ImageFont.load_default()
        ss = 1

    bbox = big_font.getbbox(text)
    pad  = 6 * ss
    tw   = (bbox[2] - bbox[0]) + pad * 2
    th   = (bbox[3] - bbox[1]) + pad * 2

    big = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    ImageDraw.Draw(big).text(
        (pad - bbox[0], pad - bbox[1]), text, font=big_font, fill=(255, 255, 255, 255)
    )

    target_size = (max(1, tw // ss), max(1, th // ss))
    layer = big.resize(target_size, Image.LANCZOS) if ss > 1 else big
    offset = (pad // ss, pad // ss)
    return layer, offset


def tint_layer(layer, color):
    """Recolors a white-on-transparent text layer to a flat `color`."""
    r, g, b, a = layer.split()
    solid = Image.new("RGBA", layer.size, (*color, 0))
    solid.putalpha(a)
    return solid


def gradient_tint_layer(layer, color_a, color_b):
    """Recolors a white-on-transparent text layer with a horizontal gradient."""
    w, h = layer.size
    grad = Image.new("RGBA", (w, h))
    gd = ImageDraw.Draw(grad)
    for x in range(w):
        t = x / max(w - 1, 1)
        r = int(color_a[0] + (color_b[0] - color_a[0]) * t)
        g = int(color_a[1] + (color_b[1] - color_a[1]) * t)
        b = int(color_a[2] + (color_b[2] - color_a[2]) * t)
        gd.line([(x, 0), (x, h)], fill=(r, g, b))
    grad = grad.convert("RGBA")
    grad.putalpha(layer.split()[3])
    return grad


def glow_from_layer(layer, color, blur=8, alpha=160):
    """Builds a soft radial-looking glow behind a text layer."""
    r, g, b, a = layer.split()
    tinted = Image.new("RGBA", layer.size, (*color, 0))
    tinted.putalpha(a)
    tinted = tinted.filter(ImageFilter.GaussianBlur(blur))
    r2, g2, b2, a2 = tinted.split()
    a2 = a2.point(lambda v: min(255, int(v * (alpha / 255))))
    tinted.putalpha(a2)
    return tinted


def paste_text(base_img, layer, x, y):
    """Alpha-composites a text layer onto `base_img` at (x, y)."""
    canvas = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
    canvas.paste(layer, (int(x), int(y)), layer)
    return Image.alpha_composite(base_img, canvas)


def _shadow(layer, alpha=140):
    r, g, b, a = layer.split()
    shadow = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    a2 = a.point(lambda v: int(v * (alpha / 255)))
    shadow.putalpha(a2)
    return shadow


class Thumbnail:

    def __init__(self):
        self.font_paths = {}
        try:
            self.title_font     = ImageFont.truetype(
                "ArtistMusic/helpers/Raleway-Bold.ttf", 46)
            self.regular_font   = ImageFont.truetype(
                "ArtistMusic/helpers/Inter-Light.ttf", 24)
            self.signature_font = ImageFont.truetype(
                "ArtistMusic/helpers/Raleway-Bold.ttf", 22)
            self.small_font     = ImageFont.truetype(
                "ArtistMusic/helpers/Inter-Light.ttf", 20)
            self.badge_font     = ImageFont.truetype(
                "ArtistMusic/helpers/Raleway-Bold.ttf", 19)
            self.title_font_path = "ArtistMusic/helpers/Raleway-Bold.ttf"
            self.badge_font_path = "ArtistMusic/helpers/Raleway-Bold.ttf"
        except OSError:
            fb = ImageFont.load_default()
            self.title_font = self.regular_font = self.signature_font = \
                self.small_font = self.badge_font = fb
            self.title_font_path = None
            self.badge_font_path = None

    async def save_thumb(self, output_path: str, url: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                with open(output_path, "wb") as f:
                    f.write(await resp.read())
        return output_path

    async def generate(self, song: Track, size=(1280, 720)) -> str:
        try:
            temp   = f"cache/temp_{song.id}.jpg"
            output = f"cache/{song.id}_ultra.png"
            if os.path.exists(output):
                return output
            await self.save_thumb(temp, song.thumbnail)
            return await asyncio.get_event_loop().run_in_executor(
                None, self._generate_sync, temp, output, song, size)
        except Exception:
            return config.DEFAULT_THUMB

    def _generate_sync(self, temp, output, song, size=(1280, 720)):
        try:
            cW, cH = size

            # ── 1. Background ──────────────────────────────────────────────────
            with Image.open(temp) as tmp:
                base = tmp.resize(size).convert("RGBA")

            bg = base.filter(ImageFilter.GaussianBlur(38))
            bg = ImageEnhance.Brightness(bg).enhance(0.18)
            bg = ImageEnhance.Contrast(bg).enhance(1.6)

            tint = Image.new("RGBA", size, (20, 5, 50, 120))
            bg   = Image.alpha_composite(bg, tint)

            vignette = Image.new("RGBA", size, (0, 0, 0, 0))
            vd = ImageDraw.Draw(vignette)
            for i in range(70, 0, -1):
                alpha  = int(180 * (1 - i / 70) ** 1.3)
                spread = i * 7
                vd.ellipse(
                    (cW // 2 - spread, cH // 2 - spread * 9 // 16,
                     cW // 2 + spread, cH // 2 + spread * 9 // 16),
                    fill=(0, 0, 0, alpha)
                )
            bg = Image.alpha_composite(bg, vignette)

            dark = Image.new("RGBA", size, (0, 0, 0, 80))
            bg   = Image.alpha_composite(bg, dark)

            draw = ImageDraw.Draw(bg, "RGBA")

            # ── 2. Glass panel ────────────────────────────────────────────────
            panel = Image.new("RGBA", (PANEL_W, PANEL_H), (0, 0, 0, 0))
            pd    = ImageDraw.Draw(panel, "RGBA")

            for gi in range(12, 0, -1):
                t   = gi / 12
                gr  = int(ACCENT_A[0] + (ACCENT_B[0] - ACCENT_A[0]) * (1 - t))
                gg  = int(ACCENT_A[1] + (ACCENT_B[1] - ACCENT_A[1]) * (1 - t))
                gb  = int(ACCENT_A[2] + (ACCENT_B[2] - ACCENT_A[2]) * (1 - t))
                ga  = int(45 * (gi / 12) ** 1.2)
                pd.rounded_rectangle(
                    (-gi, -gi, PANEL_W - 1 + gi, PANEL_H - 1 + gi),
                    radius=44 + gi,
                    outline=(gr, gg, gb, ga)
                )
            
            pd.rounded_rectangle(
                (0, 0, PANEL_W, PANEL_H),
                radius=44,
                fill=(10, 5, 30, 180)
            )
            
            pd.rounded_rectangle(
                (2, 2, PANEL_W - 2, PANEL_H // 3),
                radius=42,
                fill=(255, 255, 255, 12)
            )

            pd.rounded_rectangle(
                (0, 0, PANEL_W, PANEL_H),
                radius=44,
                outline=(*ACCENT_A, 80),
                width=1
            )

            bg.paste(panel, (PANEL_X, PANEL_Y), panel)

            # ── 3. Thumbnail ──────────────────────────────────────────────────
            with Image.open(temp) as thumb_img:
                thumb = thumb_img.resize((THUMB_W, THUMB_H)).convert("RGBA")
            
            shadow = Image.new("RGBA", (THUMB_W + 20, THUMB_H + 20), (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow)
            shadow_draw.rounded_rectangle(
                (10, 10, THUMB_W + 10, THUMB_H + 10),
                radius=12,
                fill=(0, 0, 0, 60)
            )
            shadow = shadow.filter(ImageFilter.GaussianBlur(8))
            bg.paste(shadow, (THUMB_X - 10, THUMB_Y - 10), shadow)
            
            mask = Image.new("L", (THUMB_W, THUMB_H), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rounded_rectangle((0, 0, THUMB_W, THUMB_H), radius=12, fill=255)
            
            thumb_rgba = thumb.copy()
            thumb_rgba.putalpha(mask)
            bg.paste(thumb_rgba, (THUMB_X, THUMB_Y), thumb_rgba)

            # ── 4. Text ────────────────────────────────────────────────────────
            title = trim_to_width(song.title, self.title_font, MAX_TITLE_WIDTH)
            title_layer, _ = render_text_layer(title, self.title_font_path, self.title_font.size)
            gradient_title = gradient_tint_layer(title_layer, WHITE, DIM_WHITE)
            bg = paste_text(bg, gradient_title, TITLE_X, TITLE_Y)

            meta_text = f"{song.artist} • {song.album}"
            meta = trim_to_width(meta_text, self.regular_font, MAX_TITLE_WIDTH - 100)
            meta_layer, _ = render_text_layer(meta, self.regular_font_path, self.regular_font.size)
            tinted_meta = tint_layer(meta_layer, MID_GREY)
            bg = paste_text(bg, tinted_meta, TITLE_X, META_Y)

            # ── 5. Progress Bar ───────────────────────────────────────────────
            draw.rounded_rectangle(
                (BAR_X, BAR_Y - BAR_H, BAR_X + BAR_TOTAL_LEN, BAR_Y + BAR_H),
                radius=BAR_H,
                fill=(*DARK_GREY, 180)
            )
            
            progress_len = int(BAR_TOTAL_LEN * (song.duration_ms / 1000 / 300))
            progress_len = min(progress_len, BAR_TOTAL_LEN)
            
            gradient_line(
                draw, BAR_X, BAR_Y - BAR_H, 
                BAR_X + progress_len, BAR_Y - BAR_H,
                BAR_H * 2, ACCENT_A, ACCENT_B
            )
            
            glow = Image.new("RGBA", (BAR_TOTAL_LEN, BAR_H * 4), (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow)
            glow_draw.rounded_rectangle(
                (0, BAR_H, progress_len, BAR_H * 3),
                radius=BAR_H,
                fill=(*ACCENT_A, 40)
            )
            glow = glow.filter(ImageFilter.GaussianBlur(6))
            bg.paste(glow, (BAR_X, BAR_Y - BAR_H * 2), glow)

            # ── 6. Playback Icons ─────────────────────────────────────────────
            icons_y = ICONS_Y
            icon_spacing = 60
            icon_x = ICONS_X
            
            play_points = [
                (icon_x + 10, icons_y + 5),
                (icon_x + 10, icons_y + ICONS_H - 5),
                (icon_x + ICONS_H - 10, icons_y + ICONS_H // 2)
            ]
            draw.polygon(play_points, fill=(*WHITE, 200))
            
            heart_x = icon_x + ICONS_H + icon_spacing
            heart_center = (heart_x + ICONS_H // 2, icons_y + ICONS_H // 2)
            heart_size = 14
            
            draw.ellipse(
                (heart_center[0] - heart_size, heart_center[1] - heart_size // 2,
                 heart_center[0], heart_center[1] + heart_size // 2),
                fill=(*WHITE, 180)
            )
            draw.ellipse(
                (heart_center[0], heart_center[1] - heart_size // 2,
                 heart_center[0] + heart_size, heart_center[1] + heart_size // 2),
                fill=(*WHITE, 180)
            )
            draw.polygon([
                (heart_center[0] - heart_size // 2, heart_center[1]),
                (heart_center[0], heart_center[1] + heart_size),
                (heart_center[0] + heart_size // 2, heart_center[1])
            ], fill=(*WHITE, 180))

            # ── 7. Save and cleanup ──────────────────────────────────────────
            bg.save(output, format="PNG", optimize=True)
            
            if os.path.exists(temp):
                os.remove(temp)

            return output

        except Exception as e:
            print(f"Error generating thumbnail: {e}")
            if os.path.exists(temp):
                try:
                    os.remove(temp)
                except:
                    pass
            return config.DEFAULT_THUMB
