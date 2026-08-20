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
import asyncio
import aiohttp

from PIL import Image, ImageDraw, ImageFont

from ArtistMusic import config
from ArtistMusic.helpers import Track


class Thumbnail:

    async def save_thumb(self, output_path: str, url: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                with open(output_path, "wb") as f:
                    f.write(await resp.read())
        return output_path

    async def generate(self, song: Track, size=(1280, 720)) -> str:
        try:
            temp   = f"cache/temp_{song.id}.jpg"
            output = f"cache/{song.id}_pill.png"
            
            if os.path.exists(output):
                return output
            
            await self.save_thumb(temp, song.thumbnail)
            
            with Image.open(temp).convert("RGBA") as img:
                img = img.resize(size, Image.Resampling.LANCZOS)
                draw = ImageDraw.Draw(img)
                
                try:
                    # ✅ BADA FONT (Screenshot jaisa clean dikhne ke liye)
                    font_size = 30  
                    try:
                        font = ImageFont.truetype("ArtistMusic/helpers/Raleway-Bold.ttf", font_size)
                    except:
                        font = ImageFont.load_default()
                    
                    full_text = "✦ PremiumXmusic ✦"
                    
                    # Colors ka map
                    color_map = {
                        'P': "#F05C91",   # Melon Mambo (Pink)
                        'X': "#B24080",   # Regal Rose (Dark Pink)
                        'c': "#D95A56",   # Calypso Coral (Orange-Pink)
                    }
                    
                    # Text ki width aur height calculate karo
                    bbox = draw.textbbox((0, 0), full_text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    
                    # Pill shape ke liye padding (Thoda sa gap)
                    pad_x, pad_y = 18, 10
                    
                    # Top-Left corner coordinate
                    x0, y0 = 16, 16
                    x1 = x0 + text_width + (pad_x * 2)
                    y1 = y0 + text_height + (pad_y * 2)
                    
                    # ✅ 1. Dark semi-transparent rounded Pill background
                    draw.rounded_rectangle(
                        (x0, y0, x1, y1),
                        radius=25,  # Roundness
                        fill=(20, 20, 20, 200)  # Dark grey with transparency
                    )
                    
                    # ✅ 2. Thin white elegant border
                    draw.rounded_rectangle(
                        (x0, y0, x1, y1),
                        radius=25,
                        outline=(255, 255, 255, 80),
                        width=1
                    )
                    
                    # ✅ 3. Text draw karo (Multicolor with logic)
                    current_x = x0 + pad_x
                    text_y = y0 + pad_y
                    
                    for char in full_text:
                        if char in color_map:
                            fill_color = color_map[char]
                        else:
                            fill_color = "#FFFFFF" # White
                        
                        draw.text((current_x, text_y), char, fill=fill_color, font=font)
                        
                        char_bbox = draw.textbbox((0, 0), char, font=font)
                        char_width = char_bbox[2] - char_bbox[0]
                        current_x += char_width + 2
                        
                except Exception as e:
                    print(f"Badge error: {e}")
                
                img.save(output, format="PNG", optimize=True)
            
            if os.path.exists(temp):
                os.remove(temp)
                
            return output

        except Exception as e:
            print(f"Thumbnail error: {e}")
            return config.DEFAULT_THUMB
