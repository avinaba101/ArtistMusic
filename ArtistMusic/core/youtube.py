# ==========================================================
# Copyright (c) 2026 ArtistBots
# All Rights Reserved.
#
# Project      : ArtistBots API Telegram Music Bot
# Powered By   : Artist
# Type         : API Based Telegram Music Bot
#
# Bot          : @ArtistApibot
# Channel      : https://t.me/artistbots
# GitHub       : https://github.com/elevenyts/ArtistMusic
#
# Unauthorized copying, modification, or redistribution
# of this source code without permission is prohibited.
# ==========================================================

import os
import re
import glob
import time
import yt_dlp
import random
import asyncio
import aiohttp
from dataclasses import replace
from pathlib import Path
from typing import Optional, Union

from pyrogram import enums, types
from py_yt import Playlist, VideosSearch
from ArtistMusic import config, logger
from ArtistMusic.helpers import Track, utils


class YouTube:
    def __init__(self):
        """Initialize YouTube handler with configuration and caching."""
        self.base = "https://www.youtube.com/watch?v="
        self.cookies = []
        self.checked = False
        self.warned = False

        # Regular expression to match YouTube URLs
        self.regex = re.compile(
            r"(https?://)?(www\.|m\.|music\.)?"
            r"(youtube\.com/(watch\?v=|shorts/|live/|embed/|playlist\?list=)|youtu\.be/)"
            r"([A-Za-z0-9_-]{11}|PL[A-Za-z0-9_-]+)([&?][^\s]*)?"
        )

        # Cache search results (10 minute TTL)
        self.search_cache = {}
        self._download_semaphore = asyncio.Semaphore(5)
        self._max_video_height = 480  # 💡 FIX: Video quality 480p par lock kar di

        # Log configuration
        logger.info("=" * 50)
        logger.info("📹 YouTube Handler Initialized (FIXED 480p SMOOTH STREAM)")
        logger.info("=" * 50)

    def _locate_download_file(self, video_id: str, video: bool = False) -> Optional[str]:
        """Locate any completed download file for a video id."""
        pattern = f"downloads/{video_id}*"
        candidates = sorted([
            path for path in glob.glob(pattern)
            if not path.endswith((".part", ".ytdl", ".info.json", ".temp"))
        ])

        video_exts = {".mp4", ".mkv", ".webm", ".mov"}
        audio_exts = {".m4a", ".webm", ".opus", ".mp3", ".ogg", ".wav", ".flac"}

        if video:
            for path in candidates:
                if os.path.isdir(path):
                    continue
                if Path(path).suffix.lower() in video_exts:
                    return path
        else:
            for path in candidates:
                if os.path.isdir(path):
                    continue
                if Path(path).suffix.lower() in audio_exts:
                    return path

        for path in candidates:
            if os.path.isdir(path):
                continue
            return path
        return None

    def get_cookies(self):
        """Get random cookie file from cookies directory."""
        if not self.checked:
            cookies_dir = "ArtistMusic/cookies"
            if os.path.exists(cookies_dir):
                for file in os.listdir(cookies_dir):
                    if file.endswith(".txt"):
                        self.cookies.append(file)
            self.checked = True
        
        if not self.cookies:
            if not self.warned:
                self.warned = True
                logger.warning("🍪 Cookies are missing; downloads might fail.")
            return None
        
        cookie_file = f"ArtistMusic/cookies/{random.choice(self.cookies)}"
        logger.debug(f"Using cookie file: {cookie_file}")
        return cookie_file

    async def save_cookies(self, urls: list[str]) -> None:
        """Save cookies from URLs to files."""
        logger.info("🍪 Saving cookies from urls...")
        saved_count = 0
        
        cookies_dir = Path("ArtistMusic/cookies")
        cookies_dir.mkdir(parents=True, exist_ok=True)
        
        for url in urls:
            try:
                path = cookies_dir / f"cookie{random.randint(10000, 99999)}.txt"
                
                if "pastebin.com" in url:
                    link = url.replace("pastebin.com", "pastebin.com/raw")
                elif "batbin.me" in url:
                    link = url.replace("batbin.me", "batbin.me/raw")
                else:
                    link = url
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(link, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                        if resp.status != 200:
                            continue
                        
                        content = await resp.read()
                        if not content or len(content) < 50:
                            continue
                        
                        with open(path, "wb") as fw:
                            fw.write(content)
                        
                        if path.exists() and path.stat().st_size > 0:
                            saved_count += 1
                            cookie_filename = path.name
                            if cookie_filename not in self.cookies:
                                self.cookies.append(cookie_filename)
                            
            except Exception:
                pass
        
        self.checked = True
        
        if saved_count > 0:
            logger.info(f"✅ Cookies saved successfully! ({saved_count} file(s))")
        else:
            logger.error("❌ No cookies saved! Check COOKIE_URL in .env.")

    async def download_via_cookies(self, video_id: str, video: bool = False) -> Optional[str]:
        """
        Download audio/video using yt-dlp with cookies (Fallback Method).
        
        Args:
            video_id: YouTube video ID
            video: True for video download, False for audio download
        
        Returns:
            Path to downloaded file or None if failed
        """
        url = self.base + video_id
        filename_pattern = f"downloads/{video_id}"
        
        existing_files = [
            f for f in glob.glob(f"{filename_pattern}.*")
            if not f.endswith('.part')
        ]
        
        if video:
            video_candidates = [
                f for f in existing_files
                if Path(f).suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}
            ]
            if video_candidates:
                logger.debug(f"Found existing video file: {video_candidates[0]}")
                return video_candidates[0]
        else:
            audio_candidates = [
                f for f in existing_files
                if Path(f).suffix.lower() in {".m4a", ".webm", ".opus", ".mp3", ".ogg", ".wav", ".flac"}
            ]
            if audio_candidates:
                logger.debug(f"Found existing audio file: {audio_candidates[0]}")
                return audio_candidates[0]

            container_fallbacks = [
                f for f in existing_files
                if Path(f).suffix.lower() in {".mp4", ".mkv", ".mov"}
            ]
            if container_fallbacks:
                logger.debug(f"Found existing container file: {container_fallbacks[0]}")
                return container_fallbacks[0]
        
        downloads_dir = Path("downloads")
        if not downloads_dir.exists():
            try:
                downloads_dir.mkdir(parents=True, exist_ok=True)
                logger.info("📁 Created downloads directory")
            except Exception as e:
                logger.error(f"❌ Cannot create downloads directory: {e}")
                return None

        async with self._download_semaphore:
            cookie = self.get_cookies()
            base_opts = {
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "quiet": True,
                "noplaylist": True,
                "geo_bypass": True,
                "no_warnings": True,
                "overwrites": False,
                "nocheckcertificate": True,
                "continuedl": True,
                "noprogress": True,
                "concurrent_fragment_downloads": 4,
                "http_chunk_size": 524288,
                "socket_timeout": 30,
                "retries": 2,
                "fragment_retries": 2,
                "extractor_retries": 5,
                "sleep_interval_requests": 1,
                "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
            }

            if video:
                # 💡 FIX: Video quality ko 480p par limit kar diya (Size aadha ho jayega, smooth chalegi)
                format_chain = (
                    "bestvideo[ext=mp4][height<=480]+bestaudio[ext=m4a]/"
                    "bestvideo[height<=480]+bestaudio/"
                    "bestvideo+bestaudio/best"
                )
                ydl_opts = {
                    **base_opts,
                    "format": format_chain,
                    "merge_output_format": "mp4",
                    "postprocessors": [
                        {
                            "key": "FFmpegVideoConvertor",
                            "preferedformat": "mp4",
                        }
                    ],
                }
            else:
                # 💡 Audio ke liye best quality waisa hi rakha hai
                ydl_opts = {
                    **base_opts,
                    "format": "bestaudio[ext=m4a]/bestaudio[acodec=opus]/bestaudio/best",
                    "postprocessors": [],
                }

            ydl_opts_cookie = {
                **ydl_opts,
                "cookiefile": cookie,
            }

            def _download(ydl_runtime_opts):
                ydl_instance = None
                try:
                    ydl_instance = yt_dlp.YoutubeDL(ydl_runtime_opts)
                    info = ydl_instance.extract_info(url, download=True)
                    if not info:
                        logger.error(f"❌ Failed to extract info for {video_id}")
                        return None
                    
                    time.sleep(0.5)
                    located = self._locate_download_file(video_id, video=video)
                    if located:
                        logger.info(f"✅ Download completed: {located}")
                        return located
                    
                    logger.error(f"❌ Download completed but file not found for: {video_id}")
                    return None
                except Exception as ex:
                    logger.warning(f"⚠️ Download error for {video_id}: {ex}")
                    recovered = self._locate_download_file(video_id, video=video)
                    if recovered:
                        logger.info(f"✅ Recovered existing file: {recovered}")
                        return recovered
                    return None
                finally:
                    if ydl_instance:
                        try:
                            ydl_instance.close()
                        except Exception:
                            pass

            logger.info(f"🍪 Downloading {video_id} (Quality: 480p SMOOTH)...")
            result = await asyncio.to_thread(_download, ydl_opts_cookie)
            
            if result:
                logger.info(f"✅ SUCCESS: Downloaded: {result}")
            else:
                logger.warning(f"⚠️ FAILED: Could not download {video_id}")
            
            return result

    def valid(self, url: str) -> bool:
        """Check if URL is a valid YouTube URL."""
        return bool(re.match(self.regex, url))

    def url(self, message_1: types.Message) -> Union[str, None]:
        """Extract YouTube URL from message."""
        messages = [message_1]
        link = None
        
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)

        for message in messages:
            text = message.text or message.caption or ""

            if message.entities:
                for entity in message.entities:
                    if entity.type == enums.MessageEntityType.URL:
                        link = text[entity.offset: entity.offset + entity.length]
                        break

            if message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == enums.MessageEntityType.TEXT_LINK:
                        link = entity.url
                    elif entity.type == enums.MessageEntityType.URL:
                        link = message.caption[entity.offset: entity.offset + entity.length]
                        break

        # Agar pahle se direct link hai toh
        if not link:
            for message in messages:
                text = message.text or message.caption or ""
                # Check for direct YouTube link in text
                if "youtube.com" in text or "youtu.be" in text:
                    words = text.split()
                    for word in words:
                        if "youtube.com" in word or "youtu.be" in word:
                            link = word
                            break
                    if link:
                        break

        return link
