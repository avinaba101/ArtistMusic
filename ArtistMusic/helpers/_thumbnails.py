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
        """Download the thumbnail image from the given URL."""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                with open(output_path, "wb") as f:
                    f.write(await resp.read())
        return output_path

    async def generate(self, song: Track, size=(1280, 720)) -> str:
        """
        Downloads the original YouTube thumbnail and adds a custom 
        multi-colored 'PremiumXmusic' badge in the top-left corner.
        """
        try:
            temp   = f"cache/temp_{song.id}.jpg"
            output = f"cache/{song.id}_badge.png"
            
            # If already cached, return it
            if os.path.exists(output):
                return output
            
            # Download the raw thumbnail
            await self.save_thumb(temp, song.thumbnail)
            
            # Open the image and prepare to add badge
            with Image.open(temp).convert("RGBA") as img:
                # Resize to standard size
                img = img.resize(size, Image.Resampling.LANCZOS)
                
                # ✅ BADGE DRAWING CODE START
                draw = ImageDraw.Draw(img)
                
                try:
                    font_size = 24
                    try:
                        font = ImageFont.truetype("ArtistMusic/helpers/Raleway-Bold.ttf", font_size)
                    except:
                        font = ImageFont.load_default()
                    
                    # ⭐ FULL NAME
                    full_text = "✦ PremiumXmusic ✦"
                    
                    # Colors Mapping (Hex codes)
                    # Melon Mambo (Pinkish) - For 'P'
                    # Regal Rose (Dark Pink) - For 'X'
                    # Calypso Coral (Orange-Pink) - For last 'c'
                    color_map = {
                        'P': "#F05C91",   # Melon Mambo
                        'X': "#B24080",   # Regal Rose
                        'c': "#D95A56",   # Calypso Coral
                    }
                    
                    # Calculate overall bounding box
                    bbox = draw.textbbox((0, 0), full_text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    
                    # Padding and positioning
                    pad_x, pad_y = 18, 8
                    x0, y0 = 16, 16
                    x1 = x0 + text_width + (pad_x * 2)
                    y1 = y0 + text_height + (pad_y * 2)
                    
                    # 1. Draw semi-transparent black pill background
                    draw.rounded_rectangle(
                        (x0, y0, x1, y1),
                        radius=18,
                        fill=(0, 0, 0, 180)  # Dark glass look
                    )
                    
                    # 2. Draw thin white border for premium look
                    draw.rounded_rectangle(
                        (x0, y0, x1, y1),
                        radius=18,
                        outline=(255, 255, 255, 60),
                        width=1
                    )
                    
                    # 3. Draw each letter with its specific color
                    current_x = x0 + pad_x
                    text_y = y0 + pad_y
                    
                    for char in full_text:
                        # Pick color if specific letter, else white
                        if char in color_map:
                            fill_color = color_map[char]
                        else:
                            fill_color = "#FFFFFF" # White for other letters/stars
                        
                        draw.text((current_x, text_y), char, fill=fill_color, font=font)
                        
                        # Update X position for next letter
                        char_bbox = draw.textbbox((0, 0), char, font=font)
                        char_width = char_bbox[2] - char_bbox[0]
                        current_x += char_width + 1 # Small spacing between letters
                        
                except Exception as e:
                    print(f"Error drawing badge: {e}")
                # ✅ BADGE DRAWING CODE END
                
                # Save the final image
                img.save(output, format="PNG", optimize=True)
            
            # Clean up temp file
            if os.path.exists(temp):
                os.remove(temp)
                
            return output

        except Exception as e:
            print(f"Error generating thumbnail: {e}")
            return config.DEFAULT_THUMB
