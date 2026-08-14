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

from PIL import Image

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
        Simply downloads and resizes the original YouTube thumbnail.
        No branding, no text, no fancy UI overlays. Just the raw image.
        """
        try:
            temp   = f"cache/temp_{song.id}.jpg"
            output = f"cache/{song.id}_simple.png"
            
            # If already cached, return it
            if os.path.exists(output):
                return output
            
            # Download the raw thumbnail
            await self.save_thumb(temp, song.thumbnail)
            
            # Open, resize, and save without ANY extra edits
            with Image.open(temp) as img:
                img = img.resize(size, Image.Resampling.LANCZOS)
                img.save(output, format="PNG", optimize=True)
            
            # Clean up temp file
            if os.path.exists(temp):
                os.remove(temp)
                
            return output

        except Exception as e:
            print(f"Error generating simple thumbnail: {e}")
            # If anything fails, return the default fallback thumbnail
            return config.DEFAULT_THUMB
