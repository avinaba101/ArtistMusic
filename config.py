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
# GitHub       : https://github.com/elevenyts
#
# Unauthorized copying, modification, or redistribution
# of this source code without permission is prohibited.
# ==========================================================
from os import getenv
from typing import List, Dict, Optional
from dotenv import load_dotenv
import random

load_dotenv()


class Config:
    def __init__(self):
        # Telegram API
        self.API_ID: int = int(getenv("API_ID", "0"))
        self.API_HASH: str = getenv("API_HASH", "")
        self.BOT_TOKEN: str = getenv("BOT_TOKEN", "")
        self.LOGGER_ID: int = int(getenv("LOGGER_ID", "0"))
        self.OWNER_ID: int = int(getenv("OWNER_ID", "0"))

        # Database
        self.MONGO_URL: str = getenv("MONGO_DB_URI", "")

        # Limits
        self.DURATION_LIMIT: int = int(getenv("DURATION_LIMIT", "300")) * 60
        self.QUEUE_LIMIT: int = int(getenv("QUEUE_LIMIT", "30"))
        self.PLAYLIST_LIMIT: int = int(getenv("PLAYLIST_LIMIT", "20"))

        # Assistant Sessions
        self.SESSION1: str = getenv("STRING_SESSION", "")
        self.SESSION2: str = getenv("STRING_SESSION2", "")
        self.SESSION3: str = getenv("STRING_SESSION3", "")

        # Support Links
        self.SUPPORT_CHANNEL: str = getenv("SUPPORT_CHANNEL", "https://t.me/darkroom149")
        self.SUPPORT_CHAT: str = getenv("SUPPORT_CHAT", "https://t.me/DDOS_SELLER_07")

        # Excluded Chats
        self.EXCLUDED_CHATS: List[int] = self._parse_excluded_chats()

        # Feature Flags
        self.AUTO_END: bool = self._str_to_bool(getenv("AUTO_END", "False"))
        self.AUTO_LEAVE: bool = self._str_to_bool(getenv("AUTO_LEAVE", "False"))
        self.THUMB_GEN: bool = self._str_to_bool(getenv("THUMB_GEN", "True"))
        self.VIDEO_PLAY: bool = self._str_to_bool(getenv("VIDEO_PLAY", "True"))
        self.VIDEO_MAX_HEIGHT: int = self._parse_video_height()

        # ArtistBots API
        self.ARTISTBOTS_API_URL: str = getenv("ARTISTBOTS_API_URL", "")
        self.ARTISTBOTS_KEY: str = getenv("ARTISTBOTS_KEY", "")
        self.ENABLE_API: bool = self._str_to_bool(getenv("ENABLE_API", "True"))
        self.ENABLE_COOKIES_FALLBACK: bool = self._str_to_bool(getenv("ENABLE_COOKIES_FALLBACK", "True"))
        self.API_TIMEOUT: int = int(getenv("API_TIMEOUT", "60"))
        self.API_STREAM_TIMEOUT: int = int(getenv("API_STREAM_TIMEOUT", "300"))

        # YouTube Cookies
        self.COOKIES_URL: List[str] = self._parse_cookies()

        # Images
        self.DEFAULT_THUMB: str = getenv("DEFAULT_THUMB", "https://iili.io/CBya8b9.jpg")
        self.PING_IMG: str = getenv("PING_IMG", "https://iili.io/CBya8b9.jpg")
        self.START_IMG: str = getenv("START_IMG", "https://iili.io/CBya8b9.jpg")
        self.RADIO_IMG: str = getenv("RADIO_IMG", "https://iili.io/CBya8b9.jpg")

        # Moderation
        self.EXCLUDED_USERNAMES: List[str] = getenv("EXCLUDED_USERNAMES", "").split()

        # ==================== PROXY CONFIGURATION (3 Proxies) ====================
        self.ENABLE_PROXY: bool = self._str_to_bool(getenv("ENABLE_PROXY", "True"))
        
        # List of all proxies
        self.PROXY_LIST: List[Dict[str, str]] = self._initialize_proxies()
        
        # Proxy rotation mode: "random", "round_robin", "sequential"
        self.PROXY_ROTATION: str = getenv("PROXY_ROTATION", "random")
        
        # Current proxy index for rotation
        self._current_proxy_index: int = 0
        
        # Proxy timeout
        self.PROXY_TIMEOUT: int = int(getenv("PROXY_TIMEOUT", "30"))
        
        # Retry attempts
        self.PROXY_RETRY_ATTEMPTS: int = int(getenv("PROXY_RETRY_ATTEMPTS", "3"))
        
        # Working proxies cache
        self._working_proxies: List[Dict[str, str]] = []
        self._failed_proxies: List[Dict[str, str]] = []

    def _initialize_proxies(self) -> List[Dict[str, str]]:
        """Initialize all 3 proxies"""
        
        # First check if proxies are provided in environment variable
        proxy_env = getenv("PROXY_LIST", "")
        
        if proxy_env:
            proxies = []
            for proxy in proxy_env.split(","):
                proxy = proxy.strip()
                if ":" in proxy:
                    host, port = proxy.split(":")
                    proxies.append(self._create_proxy_dict(host, port))
            if proxies:
                return proxies
        
        # Default 3 proxies (existing + 2 new)
        default_proxies = [
            "47.252.47.39:1080",    # Proxy 1 - Original
            "92.118.112.25:1082",   # Proxy 2 - New
            "138.2.216.186:1080"    # Proxy 3 - New
        ]
        
        proxies = []
        for proxy_str in default_proxies:
            host, port = proxy_str.split(":")
            proxies.append(self._create_proxy_dict(host, port))
        
        return proxies
    
    def _create_proxy_dict(self, host: str, port: str) -> Dict[str, str]:
        """Create proxy dictionary with multiple protocol support"""
        return {
            "http": f"http://{host}:{port}",
            "https": f"http://{host}:{port}",
            "socks5": f"socks5://{host}:{port}",
            "socks4": f"socks4://{host}:{port}",
            "host": host,
            "port": port,
            "original": f"{host}:{port}"
        }
    
    def get_proxy(self) -> Optional[Dict[str, str]]:
        """Get a proxy based on rotation mode"""
        if not self.ENABLE_PROXY or not self.PROXY_LIST:
            return None
        
        # Use working proxies if available
        if self._working_proxies:
            proxy_list = self._working_proxies
        else:
            proxy_list = self.PROXY_LIST
        
        if not proxy_list:
            return None
        
        if self.PROXY_ROTATION == "random":
            return random.choice(proxy_list)
        elif self.PROXY_ROTATION == "round_robin":
            proxy = proxy_list[self._current_proxy_index]
            self._current_proxy_index = (self._current_proxy_index + 1) % len(proxy_list)
            return proxy
        else:  # sequential
            proxy = proxy_list[self._current_proxy_index]
            self._current_proxy_index = min(self._current_proxy_index + 1, len(proxy_list) - 1)
            if self._current_proxy_index >= len(proxy_list):
                self._current_proxy_index = 0
            return proxy
    
    def get_proxy_for_request(self, protocol: str = "http") -> Optional[str]:
        """Get proxy URL for specific protocol"""
        proxy = self.get_proxy()
        if proxy and protocol in proxy:
            return proxy[protocol]
        return None
    
    def get_proxy_dict(self) -> Optional[Dict[str, str]]:
        """Get proxy as dictionary for requests library"""
        proxy = self.get_proxy()
        if proxy:
            return {
                "http": proxy["http"],
                "https": proxy["https"]
            }
        return None
    
    def get_all_proxies(self) -> List[Dict[str, str]]:
        """Get all proxies"""
        return self.PROXY_LIST.copy()
    
    def get_proxy_count(self) -> int:
        """Get total number of proxies"""
        return len(self.PROXY_LIST)
    
    def get_working_proxies(self) -> List[Dict[str, str]]:
        """Get list of working proxies"""
        return self._working_proxies.copy()
    
    def mark_proxy_failed(self, proxy: Dict[str, str]) -> None:
        """Mark a proxy as failed"""
        if proxy not in self._failed_proxies and proxy in self.PROXY_LIST:
            self._failed_proxies.append(proxy)
            if proxy in self._working_proxies:
                self._working_proxies.remove(proxy)
    
    def mark_proxy_working(self, proxy: Dict[str, str]) -> None:
        """Mark a proxy as working"""
        if proxy not in self._working_proxies and proxy in self.PROXY_LIST:
            self._working_proxies.append(proxy)
            if proxy in self._failed_proxies:
                self._failed_proxies.remove(proxy)
    
    def is_proxy_enabled(self) -> bool:
        """Check if proxy is enabled"""
        return self.ENABLE_PROXY
    
    def get_proxy_info(self) -> Dict[str, any]:
        """Get all proxies information"""
        return {
            "enabled": self.ENABLE_PROXY,
            "total_proxies": self.get_proxy_count(),
            "working_proxies": len(self._working_proxies),
            "failed_proxies": len(self._failed_proxies),
            "rotation_mode": self.PROXY_ROTATION,
            "proxies": [p["original"] for p in self.PROXY_LIST]
        }

    # ==================== EXISTING METHODS ====================
    
    def _parse_video_height(self) -> int:
        default_height = 1080
        raw_value = getenv("VIDEO_MAX_HEIGHT", str(default_height))
        try:
            height = int(raw_value)
        except (TypeError, ValueError):
            return default_height
        if height <= 0:
            return 0
        return max(480, min(height, 2160))

    def _parse_excluded_chats(self) -> List[int]:
        excluded = getenv("EXCLUDED_CHATS", "")
        if not excluded:
            return []
        chat_ids = []
        for chat_id in excluded.split(","):
            chat_id = chat_id.strip()
            if chat_id.lstrip('-').isdigit():
                chat_ids.append(int(chat_id))
        return chat_ids

    def _parse_cookies(self) -> List[str]:
        cookie_str = getenv("COOKIE_URL", "")
        if not cookie_str:
            return []
        valid_sources = ["batbin.me", "pastebin.com", "paste.ee", "rentry.co"]
        return [url.strip() for url in cookie_str.split() if url.strip() and any(source in url for source in valid_sources)]

    @staticmethod
    def _str_to_bool(value: str) -> bool:
        return value.lower() in ("true", "1", "yes", "y", "on")

    def check(self) -> None:
        required_vars = {
            "API_ID": self.API_ID,
            "API_HASH": self.API_HASH,
            "BOT_TOKEN": self.BOT_TOKEN,
            "MONGO_DB_URI": self.MONGO_URL,
            "LOGGER_ID": self.LOGGER_ID,
            "OWNER_ID": self.OWNER_ID,
            "STRING_SESSION": self.SESSION1,
        }
        missing = [name for name, value in required_vars.items() if not value or (isinstance(value, int) and value == 0)]
        if missing:
            raise SystemExit(f"Missing required env vars: {', '.join(missing)}")
        
        if self.ENABLE_API and not self.ARTISTBOTS_KEY:
            print("Warning: ENABLE_API is True but ARTISTBOTS_KEY is not set")
        
        # Print proxy status
        if self.ENABLE_PROXY:
            print(f"✅ Proxy enabled: {self.get_proxy_count()} proxies loaded")
            print(f"📋 Proxies: {', '.join([p['original'] for p in self.PROXY_LIST])}")
            print(f"🔄 Rotation mode: {self.PROXY_ROTATION}")
        else:
            print("⚠️ Proxy is disabled")


config = Config()
