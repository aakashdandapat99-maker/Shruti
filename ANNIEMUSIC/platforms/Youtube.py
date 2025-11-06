import asyncio
import contextlib
import json
import os
import re
import time
import random
import aiohttp
import sqlite3
from typing import Dict, List, Optional, Tuple, Union, Any
from urllib.parse import urlparse

import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from py_yt import VideosSearch

from ANNIEMUSIC.utils.cookie_handler import COOKIE_PATH
from ANNIEMUSIC.utils.database import is_on_off
from ANNIEMUSIC.utils.downloader import download_audio_concurrent, yt_dlp_download
from ANNIEMUSIC.utils.errors import capture_internal_err
from ANNIEMUSIC.utils.formatters import time_to_seconds
from ANNIEMUSIC.utils.tuning import (
    YTDLP_TIMEOUT,
    YOUTUBE_META_MAX,
    YOUTUBE_META_TTL,
)

_cache: Dict[str, Tuple[float, List[Dict]]] = {}
_cache_lock = asyncio.Lock()
_formats_cache: Dict[str, Tuple[float, List[Dict], str]] = {}
_formats_lock = asyncio.Lock()

# API URL System
YOUR_API_URL = None

# Rate limiting protection
_request_timestamps = []
_RATE_LIMIT_WINDOW = 60  # 60 seconds window
_MAX_REQUESTS_PER_WINDOW = 10  # Max 10 requests per minute

# Database setup for downloaded songs
def init_downloaded_songs_db():
    """Initialize database for downloaded songs"""
    try:
        conn = sqlite3.connect('downloaded_songs.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloaded_songs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT UNIQUE,
                title TEXT,
                file_path TEXT,
                file_size INTEGER,
                duration INTEGER,
                download_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                play_count INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()
        print("✅ Downloaded songs database initialized")
    except Exception as e:
        print(f"❌ Database initialization error: {e}")

# Initialize database on startup
init_downloaded_songs_db()

class DownloadedSongsManager:
    def __init__(self):
        self.db_path = 'downloaded_songs.db'
    
    async def save_downloaded_song(self, video_id: str, title: str, file_path: str, duration: int = 0) -> bool:
        """Save downloaded song info to database"""
        try:
            if not os.path.exists(file_path):
                return False
            
            file_size = os.path.getsize(file_path)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO downloaded_songs 
                (video_id, title, file_path, file_size, duration, play_count)
                VALUES (?, ?, ?, ?, ?, COALESCE((SELECT play_count FROM downloaded_songs WHERE video_id = ?), 0))
            ''', (video_id, title, file_path, file_size, duration, video_id))
            
            conn.commit()
            conn.close()
            
            print(f"💾 [DB] Song saved: {video_id} - {title}")
            return True
            
        except Exception as e:
            print(f"❌ [DB] Error saving song: {e}")
            return False
    
    async def get_downloaded_song(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get downloaded song info from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT video_id, title, file_path, file_size, duration, play_count 
                FROM downloaded_songs 
                WHERE video_id = ?
            ''', (video_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                # Check if file still exists and has size
                file_path = result[2]
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    
                    # Update play count
                    await self._increment_play_count(video_id)
                    
                    return {
                        'video_id': result[0],
                        'title': result[1],
                        'file_path': file_path,
                        'file_size': result[3],
                        'duration': result[4],
                        'play_count': result[5] + 1
                    }
                else:
                    # File doesn't exist, remove from database
                    await self._remove_song(video_id)
                    return None
                    
            return None
            
        except Exception as e:
            print(f"❌ [DB] Error getting song: {e}")
            return None
    
    async def _increment_play_count(self, video_id: str):
        """Increment play count for song"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE downloaded_songs 
                SET play_count = play_count + 1 
                WHERE video_id = ?
            ''', (video_id,))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"❌ [DB] Error updating play count: {e}")
    
    async def _remove_song(self, video_id: str):
        """Remove song from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM downloaded_songs WHERE video_id = ?', (video_id,))
            conn.commit()
            conn.close()
            print(f"🗑️ [DB] Removed song: {video_id}")
        except Exception as e:
            print(f"❌ [DB] Error removing song: {e}")

# Global instance
song_manager = DownloadedSongsManager()

async def load_api_url():
    global YOUR_API_URL
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://pastebin.com/raw/rLsBhAQa") as response:
                if response.status == 200:
                    content = await response.text()
                    YOUR_API_URL = content.strip()
                    print(f"✅ API URL loaded successfully: {YOUR_API_URL}")
                else:
                    print(f"❌ Failed to fetch API URL. HTTP Status: {response.status}")
    except Exception as e:
        print(f"❌ Error loading API URL: {e}")

# Initialize API URL on startup
try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(load_api_url())
    else:
        loop.run_until_complete(load_api_url())
except RuntimeError:
    pass

def _cookiefile_path() -> Optional[str]:
    path = str(COOKIE_PATH)
    try:
        if path and os.path.exists(path) and os.path.getsize(path) > 0:
            return path
    except Exception:
        pass
    return None

def _cookies_args() -> List[str]:
    p = _cookiefile_path()
    return ["--cookies", p] if p else []

async def _exec_proc(*args: str) -> Tuple[bytes, bytes]:
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        return await asyncio.wait_for(proc.communicate(), timeout=YTDLP_TIMEOUT)
    except asyncio.TimeoutError:
        with contextlib.suppress(Exception):
            proc.kill()
        return b"", b"timeout"

# Rate limiting check
def _check_rate_limit():
    global _request_timestamps
    now = time.time()
    
    # Remove timestamps older than our window
    _request_timestamps = [ts for ts in _request_timestamps if now - ts < _RATE_LIMIT_WINDOW]
    
    # Check if we've exceeded the limit
    if len(_request_timestamps) >= _MAX_REQUESTS_PER_WINDOW:
        sleep_time = _RATE_LIMIT_WINDOW - (now - _request_timestamps[0])
        print(f"⚠️ [RATE LIMIT] Too many requests, sleeping for {sleep_time:.1f}s")
        time.sleep(sleep_time)
        _request_timestamps = []  # Reset after sleep
    
    # Add current timestamp
    _request_timestamps.append(now)

# Improved Telegram Download Function with Request Error Fix
async def get_telegram_file(telegram_link: str, video_id: str, file_type: str) -> str:
    """
    Improved TG link download with request error handling
    """
    try:
        extension = ".webm" if file_type == "audio" else ".mkv"
        file_path = os.path.join("downloads", f"{video_id}{extension}")
        
        # Agar already exist kare to seedha return
        if os.path.exists(file_path):
            print(f"✅ [LOCAL] File exists: {video_id}")
            return file_path
        
        # Parse Telegram link: https://t.me/channelname/messageid
        parsed = urlparse(telegram_link)
        parts = parsed.path.strip("/").split("/")
        
        if len(parts) < 2:
            print(f"❌ Invalid Telegram link format: {telegram_link}")
            return None
            
        channel_name = parts[0]
        message_id = int(parts[1])
        
        print(f"📥 [TELEGRAM] Downloading from @{channel_name}/{message_id}")
        
        # Pyrogram se message fetch karke download with enhanced error handling
        from ANNIEMUSIC import app
        
        # Enhanced retry mechanism for request errors
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Get message with timeout
                msg = await asyncio.wait_for(
                    app.get_messages(channel_name, message_id), 
                    timeout=10.0
                )
                
                if not msg or not msg.document and not msg.video and not msg.audio:
                    print(f"❌ [TELEGRAM] No media found in message: {video_id}")
                    return None
                
                os.makedirs("downloads", exist_ok=True)
                
                # Download with progress and timeout
                download_task = asyncio.create_task(
                    msg.download(file_name=file_path)
                )
                
                try:
                    await asyncio.wait_for(download_task, timeout=30.0)
                except asyncio.TimeoutError:
                    download_task.cancel()
                    print(f"❌ [TELEGRAM] Download timeout: {video_id}")
                    continue
                
                # Verify file download
                timeout = 0
                while not os.path.exists(file_path) and timeout < 30:
                    await asyncio.sleep(0.5)
                    timeout += 0.5
                
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                    print(f"✅ [TELEGRAM] Downloaded: {video_id} ({file_size:.2f} MB)")
                    return file_path
                else:
                    print(f"❌ [TELEGRAM] File not created or empty: {video_id}")
                    
            except asyncio.TimeoutError:
                print(f"❌ [TELEGRAM] Timeout attempt {attempt + 1}: {video_id}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                continue
                    
            except Exception as e:
                error_msg = str(e)
                if "request error" in error_msg.lower() or "timeout" in error_msg.lower():
                    print(f"⚠️ [TELEGRAM] Request error attempt {attempt + 1}: {video_id}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)  # Wait before retry
                        continue
                else:
                    print(f"❌ [TELEGRAM] Error for {video_id}: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1)
                        continue
                
                print(f"❌ [TELEGRAM] Failed after {max_retries} attempts: {video_id}")
                return None
        
        return None
        
    except Exception as e:
        print(f"❌ [TELEGRAM] Critical error for {video_id}: {e}")
        return None

# Enhanced API-based download function - ONLY FOR AUDIO
async def download_via_api(link: str, download_type: str = "audio") -> Optional[str]:
    """Download using external API - ONLY FOR AUDIO, VIDEO KE LIYE DIRECT yt-dlp"""
    
    # VIDEO KE LIYE API BYPASS - Direct yt-dlp use karo
    if download_type == "video":
        print(f"🚀 [VIDEO] Bypassing API, using direct yt-dlp for faster download")
        return None
    
    global YOUR_API_URL
    
    if not YOUR_API_URL:
        await load_api_url()
        if not YOUR_API_URL:
            print("❌ API URL not available")
            return None
    
    video_id = link.split('v=')[-1].split('&')[0] if 'v=' in link else link
    
    if not video_id or len(video_id) < 3:
        return None

    DOWNLOAD_DIR = "downloads"
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    extension = ".webm" if download_type == "audio" else ".mkv"
    file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}{extension}")

    # Local check - return immediately if exists
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        print(f"✅ [LOCAL] File exists: {video_id}")
        return file_path

    try:
        async with aiohttp.ClientSession() as session:
            params = {"url": video_id, "type": download_type}
            
            # API request with timeout
            try:
                async with session.get(
                    f"{YOUR_API_URL}/download",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        print(f"❌ [API] API error: {response.status}")
                        return None
                        
                    data = await response.json()

                    # Format 1: Telegram Link
                    if data.get("link") and "t.me" in str(data.get("link")):
                        telegram_link = data["link"]
                        print(f"🔗 [TELEGRAM] Link received: {telegram_link}")
                        
                        # Telegram se download karo
                        downloaded_file = await get_telegram_file(telegram_link, video_id, download_type)
                        if downloaded_file:
                            return downloaded_file
                        else:
                            print(f"⚠️ [TELEGRAM] Download failed, falling back to yt-dlp")
                            return None
                    
                    # Format 2: Stream URL
                    elif data.get("status") == "success" and data.get("stream_url"):
                        stream_url = data["stream_url"]
                        print(f"📥 [API] Stream URL obtained: {video_id}")
                        
                        # Download from stream URL with enhanced timeout
                        try:
                            async with session.get(
                                stream_url,
                                timeout=aiohttp.ClientTimeout(total=60)  # 1 minute for audio
                            ) as file_response:
                                if file_response.status != 200:
                                    print(f"❌ [API] Stream download failed: {file_response.status}")
                                    return None
                                
                                print(f"⏳ [API] Downloading audio: {video_id}")
                                
                                with open(file_path, "wb") as f:
                                    async for chunk in file_response.content.iter_chunked(16384):  # 16KB chunks for audio
                                        f.write(chunk)
                                
                                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                                    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                                    print(f"🎉 [API] Downloaded audio: {video_id} ({file_size_mb:.2f} MB)")
                                    return file_path
                                else:
                                    print(f"❌ [API] Stream file creation failed: {video_id}")
                                    return None
                        except asyncio.TimeoutError:
                            print(f"❌ [API] Stream download timeout: {video_id}")
                            return None
                    else:
                        print(f"⚠️ [API] Invalid response, falling back to yt-dlp: {data}")
                        return None
                        
            except asyncio.TimeoutError:
                print(f"❌ [API] Request timeout: {video_id}")
                return None
            except aiohttp.ClientError as e:
                print(f"❌ [API] Network error: {video_id} - {e}")
                return None

    except Exception as e:
        print(f"❌ [API] Unexpected error: {video_id} - {e}")
        return None

@capture_internal_err
async def cached_youtube_search(query: str) -> List[Dict]:
    key = f"q:{query}"
    now = time.time()
    async with _cache_lock:
        if key in _cache:
            ts, val = _cache[key]
            if now - ts < YOUTUBE_META_TTL:
                return val
            _cache.pop(key, None)
        if len(_cache) > YOUTUBE_META_MAX:
            _cache.clear()
    try:
        data = await VideosSearch(query, limit=1).next()
        result = data.get("result", [])
    except Exception:
        result = []
    if result:
        async with _cache_lock:
            _cache[key] = (now, result)
    return result


class YouTubeAPI:
    def __init__(self) -> None:
        self.base_url = "https://www.youtube.com/watch?v="
        self.playlist_url = "https://youtube.com/playlist?list="
        self._url_pattern = re.compile(r"(?:youtube\.com|youtu\.be)")

    def _prepare_link(
        self, link: str, videoid: Union[str, bool, None] = None
    ) -> str:
        if isinstance(videoid, str) and videoid.strip():
            link = self.base_url + videoid.strip()
        if "youtu.be" in link:
            link = self.base_url + link.split("/")[-1].split("?")[0]
        elif "youtube.com/shorts/" in link or "youtube.com/live/" in link:
            link = self.base_url + link.split("/")[-1].split("?")[0]
        return link.split("&")[0]

    # URL extraction method
    @capture_internal_err
    async def url(self, message: Message) -> Optional[str]:
        """
        Extract YouTube URL from message
        """
        msgs = [message] + (
            [message.reply_to_message] if message.reply_to_message else []
        )
        for msg in msgs:
            text = msg.text or msg.caption or ""
            entities = msg.entities or msg.caption_entities or []
            for ent in entities:
                if ent.type == MessageEntityType.URL:
                    url = text[ent.offset : ent.offset + ent.length]
                    if self._url_pattern.search(url):
                        return url
                if ent.type == MessageEntityType.TEXT_LINK:
                    url = ent.url
                    if self._url_pattern.search(url):
                        return url
        return None

    @capture_internal_err
    async def exists(
        self, link: str, videoid: Union[str, bool, None] = None
    ) -> bool:
        return bool(self._url_pattern.search(self._prepare_link(link, videoid)))

    @capture_internal_err
    async def _fetch_video_info(
        self, query: str, use_cache: bool = True
    ) -> Optional[Dict]:
        q = self._prepare_link(query)
        if use_cache and not q.startswith("http"):
            res = await cached_youtube_search(q)
            return res[0] if res else None
        data = await VideosSearch(q, limit=1).next()
        result = data.get("result", [])
        return result[0] if result else None

    @capture_internal_err
    async def is_live(self, link: str) -> bool:
        # Rate limiting check
        _check_rate_limit()
        
        prepared = self._prepare_link(link)
        stdout, _ = await _exec_proc(
            "yt-dlp", *(_cookies_args()), "--dump-json", prepared
        )
        if not stdout:
            return False
        try:
            info = json.loads(stdout.decode())
            return bool(info.get("is_live"))
        except json.JSONDecodeError:
            return False

    @capture_internal_err
    async def details(
        self, link: str, videoid: Union[str, bool, None] = None
    ) -> Tuple[str, Optional[str], int, str, str]:
        info = await self._fetch_video_info(self._prepare_link(link, videoid))
        if not info:
            raise ValueError("Video not found")
        dt = info.get("duration")
        ds = int(time_to_seconds(dt)) if dt else 0
        thumb = (
            info.get("thumbnail")
            or info.get("thumbnails", [{}])[0].get("url", "")
        ).split("?")[0]
        return info.get("title", ""), dt, ds, thumb, info.get("id", "")

    @capture_internal_err
    async def title(
        self, link: str, videoid: Union[str, bool, None] = None
    ) -> str:
        info = await self._fetch_video_info(self._prepare_link(link, videoid))
        return info.get("title", "") if info else ""

    @capture_internal_err
    async def duration(
        self, link: str, videoid: Union[str, bool, None] = None
    ) -> Optional[str]:
        info = await self._fetch_video_info(self._prepare_link(link, videoid))
        return info.get("duration") if info else None

    @capture_internal_err
    async def thumbnail(
        self, link: str, videoid: Union[str, bool, None] = None
    ) -> str:
        info = await self._fetch_video_info(self._prepare_link(link, videoid))
        if info:
            thumb = info.get("thumbnail") or info.get("thumbnails", [{}])[0].get("url", "")
            return thumb.split("?")[0] if thumb else ""
        return ""

    @capture_internal_err
    async def video(self, link: str, videoid: Union[str, bool, None] = None) -> Tuple[int, str]:
        link = self._prepare_link(link, videoid)
        
        # Rate limiting check - IMPORTANT!
        _check_rate_limit()
        
        print(f"🚀 [VIDEO] Using direct yt-dlp with cookies: {link}")
        
        # Enhanced yt-dlp command with better error handling
        ytdlp_args = [
            "yt-dlp",
            *(_cookies_args()),
            "--no-warnings",  # Reduce warning noise
            "--geo-bypass",   # Bypass geographic restrictions
            "--force-ipv4",   # Force IPv4
            "-g",
            "-f",
            "best[height<=?720][width<=?1280]/best",  # Fallback to any best format
            link,
        ]
        
        stdout, stderr = await _exec_proc(*ytdlp_args)
        
        if stdout:
            stream_url = stdout.decode().split("\n")[0]
            if stream_url and stream_url.startswith('http'):
                print(f"✅ [VIDEO] Stream URL fetched: {stream_url[:100]}...")
                return (1, stream_url)
            else:
                print(f"❌ [VIDEO] Invalid stream URL received")
                return (0, "Invalid stream URL")
        else:
            error_msg = stderr.decode() if stderr else "Unknown error"
            
            # Handle specific errors
            if "429" in error_msg or "Too Many Requests" in error_msg:
                print(f"🚫 [RATE LIMITED] YouTube blocking requests, waiting 30 seconds...")
                await asyncio.sleep(30)  # Wait 30 seconds if rate limited
                return (0, "Rate limited, please try again later")
            elif "403" in error_msg:
                print(f"🔒 [FORBIDDEN] YouTube blocking access, trying alternative method...")
                # Try alternative format
                return await self._try_alternative_format(link)
            else:
                print(f"❌ [VIDEO] yt-dlp failed: {error_msg[:200]}...")
                return (0, error_msg)

    async def _try_alternative_format(self, link: str) -> Tuple[int, str]:
        """Try alternative formats when main format fails"""
        print(f"🔄 [VIDEO] Trying alternative format for: {link}")
        
        # Try different format combinations
        format_options = [
            "best[height<=480]",
            "best[ext=mp4]", 
            "best",
            "worst"  # Last resort
        ]
        
        for fmt in format_options:
            print(f"🔄 [VIDEO] Trying format: {fmt}")
            stdout, stderr = await _exec_proc(
                "yt-dlp",
                *(_cookies_args()),
                "--no-warnings",
                "-g",
                "-f",
                fmt,
                link,
            )
            
            if stdout:
                stream_url = stdout.decode().split("\n")[0]
                if stream_url and stream_url.startswith('http'):
                    print(f"✅ [VIDEO] Alternative format success: {fmt}")
                    return (1, stream_url)
            
            await asyncio.sleep(1)  # Small delay between attempts
        
        return (0, "All format attempts failed")

    @capture_internal_err
    async def playlist(
        self, link: str, limit: int, user_id, videoid: Union[str, bool, None] = None
    ) -> List[str]:
        if videoid:
            link = self.playlist_url + str(videoid)
        link = link.split("&")[0]
        
        # Rate limiting check
        _check_rate_limit()
        
        stdout, _ = await _exec_proc(
            "yt-dlp",
            *(_cookies_args()),
            "-i",
            "--get-id",
            "--flat-playlist",
            "--playlist-end",
            str(limit),
            "--skip-download",
            link,
        )
        items = stdout.decode().strip().split("\n") if stdout else []
        return [i for i in items if i]

    @capture_internal_err
    async def track(
        self, link: str, videoid: Union[str, bool, None] = None
    ) -> Tuple[Dict, str]:
        try:
            info = await self._fetch_video_info(self._prepare_link(link, videoid))
            if not info:
                raise ValueError("Track not found via API")
        except Exception:
            # Rate limiting check
            _check_rate_limit()
            
            prepared = self._prepare_link(link, videoid)
            stdout, _ = await _exec_proc(
                "yt-dlp", *(_cookies_args()), "--dump-json", prepared
            )
            if not stdout:
                raise ValueError("Track not found (yt-dlp fallback)")
            info = json.loads(stdout.decode())
        thumb = (
            info.get("thumbnail")
            or info.get("thumbnails", [{}])[0].get("url", "")
        ).split("?")[0]
        details = {
            "title": info.get("title", ""),
            "link": info.get("webpage_url", self._prepare_link(link, videoid)),
            "vidid": info.get("id", ""),
            "duration_min": info.get("duration")
            if isinstance(info.get("duration"), str)
            else None,
            "thumb": thumb,
        }
        return details, info.get("id", "")

    @capture_internal_err
    async def formats(
        self, link: str, videoid: Union[str, bool, None] = None
    ) -> Tuple[List[Dict], str]:
        link = self._prepare_link(link, videoid)
        key = f"f:{link}"
        now = time.time()
        async with _formats_lock:
            cached = _formats_cache.get(key)
            if cached and now - cached[0] < YOUTUBE_META_TTL:
                return cached[1], cached[2]

        # Rate limiting check
        _check_rate_limit()
        
        opts = {"quiet": True}
        cf = _cookiefile_path()
        if cf:
            opts["cookiefile"] = cf
        out: List[Dict] = []
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(link, download=False)
                for fmt in info.get("formats", []):
                    # Skip dash formats
                    if "dash" in str(fmt.get("format", "")).lower():
                        continue
                    # Check for required keys
                    if not any(k in fmt for k in ("filesize", "filesize_approx")):
                        continue
                    if not all(k in fmt for k in ("format", "format_id", "ext", "format_note")):
                        continue
                    size = fmt.get("filesize") or fmt.get("filesize_approx")
                    if not size:
                        continue
                    out.append(
                        {
                            "format": fmt["format"],
                            "filesize": size,
                            "format_id": fmt["format_id"],
                            "ext": fmt["ext"],
                            "format_note": fmt["format_note"],
                            "yturl": link,
                        }
                    )
        except Exception:
            pass

        async with _formats_lock:
            if len(_formats_cache) > YOUTUBE_META_MAX:
                _formats_cache.clear()
            _formats_cache[key] = (now, out, link)

        return out, link

    @capture_internal_err
    async def slider(
        self, link: str, query_type: int, videoid: Union[str, bool, None] = None
    ) -> Tuple[str, Optional[str], str, str]:
        data = await VideosSearch(self._prepare_link(link, videoid), limit=10).next()
        results = data.get("result", [])
        if not results or query_type >= len(results):
            raise IndexError(
                f"Query type index {query_type} out of range (found {len(results)} results)"
            )
        r = results[query_type]
        return (
            r.get("title", ""),
            r.get("duration"),
            r.get("thumbnails", [{}])[0].get("url", "").split("?")[0],
            r.get("id", ""),
        )

    @capture_internal_err
    async def download(
        self,
        link: str,
        mystic,
        *,
        video: Union[bool, str, None] = None,
        videoid: Union[str, bool, None] = None,
        songaudio: Union[bool, str, None] = None,
        songvideo: Union[bool, str, None] = None,
        format_id: Union[bool, str, None] = None,
        title: Union[bool, str, None] = None,
    ) -> Union[Tuple[str, Optional[bool]], Tuple[None, None]]:
        link = self._prepare_link(link, videoid)
        
        # Pehle check karo agar song already downloaded hai
        if songaudio and videoid:
            existing_song = await song_manager.get_downloaded_song(videoid)
            if existing_song:
                print(f"🎵 [DB] Using cached song: {existing_song['title']} (Play count: {existing_song['play_count']})")
                return existing_song['file_path'], True

        # VIDEO KE LIYE DIRECT yt-dlp WITH COOKIES
        if songvideo or video:
            print(f"🚀 [VIDEO] Using direct yt-dlp with cookies for fast download: {link}")
            
            # Live stream check
            if await self.is_live(link):
                status, stream_url = await self.video(link)
                if status == 1:
                    return stream_url, None
                raise ValueError("Unable to fetch live stream link")
            
            # Download video with cookies
            if await is_on_off(1):
                p = await yt_dlp_download(link, type="video")
                return (p, True) if p else (None, None)
            
            # Fallback to stream URL with cookies
            status, stream_url = await self.video(link)
            if status == 1:
                return stream_url, None
            return None, None

        # AUDIO KE LIYE API USE KARO
        else:
            # Try API-based download first for audio
            try:
                print(f"🎵 [AUDIO] Starting API download for: {link}")
                api_result = await download_via_api(link, "audio")
                if api_result:
                    # Download successful, save to database
                    if videoid and title:
                        await song_manager.save_downloaded_song(
                            video_id=videoid,
                            title=title,
                            file_path=api_result,
                            duration=0  # Aap duration bhi add kar sakte hain
                        )
                    return api_result, True
            except Exception as e:
                print(f"⚠️ API download failed, falling back to yt-dlp: {e}")

            # Fallback to yt-dlp for audio WITH COOKIES
            print(f"🔄 [AUDIO FALLBACK] Using yt-dlp with cookies for: {link}")
            p = await download_audio_concurrent(link)
            
            # Save to database if download successful
            if p and videoid and title:
                await song_manager.save_downloaded_song(
                    video_id=videoid,
                    title=title,
                    file_path=p,
                    duration=0
                )
                
            return (p, True) if p else (None, None)

# Additional utility functions
async def get_song_stats(video_id: str) -> Optional[Dict[str, Any]]:
    """Get song statistics from database"""
    return await song_manager.get_downloaded_song(video_id)

async def get_all_downloaded_songs() -> List[Dict[str, Any]]:
    """Get all downloaded songs"""
    try:
        conn = sqlite3.connect('downloaded_songs.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT video_id, title, file_path, file_size, duration, play_count, download_time 
            FROM downloaded_songs 
            ORDER BY play_count DESC
        ''')
        results = cursor.fetchall()
        conn.close()
        
        songs = []
        for result in results:
            songs.append({
                'video_id': result[0],
                'title': result[1],
                'file_path': result[2],
                'file_size': result[3],
                'duration': result[4],
                'play_count': result[5],
                'download_time': result[6]
            })
        return songs
    except Exception as e:
        print(f"❌ [DB] Error getting all songs: {e}")
        return []

async def cleanup_missing_songs():
    """Cleanup database entries for songs that no longer exist"""
    try:
        conn = sqlite3.connect('downloaded_songs.db')
        cursor = conn.cursor()
        cursor.execute('SELECT video_id, file_path FROM downloaded_songs')
        results = cursor.fetchall()
        
        removed_count = 0
        for video_id, file_path in results:
            if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                cursor.execute('DELETE FROM downloaded_songs WHERE video_id = ?', (video_id,))
                removed_count += 1
                print(f"🗑️ [CLEANUP] Removed missing song: {video_id}")
        
        conn.commit()
        conn.close()
        print(f"✅ [CLEANUP] Cleaned up {removed_count} missing songs")
        return removed_count
    except Exception as e:
        print(f"❌ [DB] Error cleaning up songs: {e}")
        return 0