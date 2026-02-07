import os
import asyncio
import subprocess
import json
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
import aiohttp
import aiofiles
from src.utils.logger import logger
from src.utils.helpers import get_random_user_agent, get_random_proxy, get_temp_filepath, format_bytes
from src.config import config


class DownloaderService:
    """
    دانلودر هوشمند با پشتیبانی از:
    - دانلود مستقیم فایل‌ها
    - دانلود از سایت‌های ویدیویی با yt-dlp (YouTube, Pornhub, Twitter, ...)
    - تشخیص خودکار بهترین روش دانلود
    """
    
    # سایت‌هایی که نیاز به yt-dlp دارن
    VIDEO_SITES = [
        'youtube.com', 'youtu.be',
        'pornhub.com', 'pornhub.org', 'pornhub.net',
        'xvideos.com',
        'xnxx.com',
        'twitter.com', 'x.com',
        'instagram.com',
        'tiktok.com',
        'reddit.com',
        'vimeo.com',
        'dailymotion.com',
        'facebook.com', 'fb.watch',
        'twitch.tv',
        'streamable.com',
    ]
    
    # پسوندهایی که لینک مستقیم فایل هستن
    DIRECT_EXTENSIONS = [
        '.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv',  # Video
        '.mp3', '.m4a', '.wav', '.flac', '.ogg', '.aac',          # Audio
        '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp',         # Image
        '.pdf', '.zip', '.rar', '.7z', '.tar', '.gz',             # Document
    ]
    
    def __init__(self, cookies_file: Optional[str] = None):
        """
        Args:
            cookies_file: مسیر فایل cookies (اختیاری). مثال: "./cookies/default.txt"
        """
        self.cookies_file = Path(cookies_file) if cookies_file else None
        
        # چک کردن وجود cookies
        if self.cookies_file and self.cookies_file.exists():
            logger.info(f"Using cookies: {self.cookies_file}")
        
        # چک کردن yt-dlp
        self._check_ytdlp()
        
        logger.info("DownloaderService initialized")
    
    def _check_ytdlp(self):
        """چک کردن نصب بودن yt-dlp"""
        try:
            result = subprocess.run(
                ['yt-dlp', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            version = result.stdout.strip()
            logger.info(f"yt-dlp version: {version}")
        except FileNotFoundError:
            logger.warning(
                "yt-dlp not installed! For video sites, install it:\n"
                "pip install yt-dlp --break-system-packages"
            )
        except Exception as e:
            logger.warning(f"yt-dlp check failed: {e}")
    
    def _is_video_site(self, url: str) -> bool:
        """چک کردن اینکه URL از سایت ویدیویی هست یا نه"""
        try:
            domain = urlparse(url).netloc.lower()
            domain = domain.replace('www.', '')
            return any(site in domain for site in self.VIDEO_SITES)
        except:
            return False
    
    def _is_direct_link(self, url: str) -> bool:
        """چک کردن اینکه URL لینک مستقیم فایل هست یا نه"""
        try:
            path = urlparse(url).path.lower()
            return any(path.endswith(ext) for ext in self.DIRECT_EXTENSIONS)
        except:
            return False
    
    async def download(self, url: str) -> str:
        """
        دانلود هوشمند - تشخیص خودکار بهترین روش
        
        Args:
            url: آدرس فایل یا ویدیو
            
        Returns:
            filepath: مسیر فایل دانلود شده
        """
        
        # تشخیص نوع لینک
        if self._is_video_site(url):
            logger.info(f"Detected video site: {url}")
            return await self._download_with_ytdlp(url)
        
        elif self._is_direct_link(url):
            logger.info(f"Detected direct link: {url}")
            return await self._download_direct(url)
        
        else:
            # تلاش با yt-dlp (شاید ساپورت کنه)
            logger.info(f"Trying yt-dlp for: {url}")
            try:
                return await self._download_with_ytdlp(url)
            except Exception as e:
                logger.warning(f"yt-dlp failed: {e}, trying direct download")
                return await self._download_direct(url)
    
    async def _download_direct(self, url: str) -> str:
        """دانلود مستقیم فایل"""
        filepath = get_temp_filepath()
        user_agent = get_random_user_agent()
        proxy = get_random_proxy()
        
        headers = {
            'User-Agent': user_agent,
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        logger.info(f"Direct downloading: {url}")
        logger.info(f"User-Agent: {user_agent}")
        if proxy:
            logger.info(f"Using proxy: {proxy}")
        
        timeout = aiohttp.ClientTimeout(total=3600)  # 1 hour
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers, proxy=proxy) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")
                
                # Check file size
                content_length = response.headers.get('content-length')
                if content_length:
                    file_size = int(content_length)
                    if file_size > config.MAX_FILE_SIZE:
                        raise Exception(f"File too large: {format_bytes(file_size)}")
                    logger.info(f"File size: {format_bytes(file_size)}")
                
                # Download
                async with aiofiles.open(filepath, 'wb') as f:
                    downloaded = 0
                    async for chunk in response.content.iter_chunked(1024 * 1024):  # 1MB chunks
                        await f.write(chunk)
                        downloaded += len(chunk)
                
                actual_size = os.path.getsize(filepath)
                logger.info(f"Downloaded: {format_bytes(actual_size)}")
                
                return filepath
    
    async def _download_with_ytdlp(self, url: str) -> str:
        """
        دانلود با yt-dlp
        
        این متد مشکل لینک‌های Pornhub و مشابه رو حل می‌کنه
        خود ویدیو رو دانلود می‌کنه نه فایل PHP
        """
        
        # تعیین مسیر خروجی
        output_dir = Path("/tmp/downloads")
        output_dir.mkdir(exist_ok=True)
        
        output_template = str(output_dir / "%(id)s.%(ext)s")
        
        # ساخت دستور yt-dlp
        cmd = [
            'yt-dlp',
            '--no-warnings',
            '--no-check-certificate',
            '-o', output_template,
            '-f', 'best[ext=mp4]/best',  # اولویت به MP4
        ]
        
        # افزودن cookies (اگه موجود باشه)
        if self.cookies_file and self.cookies_file.exists():
            cmd.extend(['--cookies', str(self.cookies_file)])
        
        # افزودن User-Agent
        cmd.extend([
            '--user-agent',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ])
        
        # افزودن URL
        cmd.append(url)
        
        logger.info(f"Running yt-dlp: {url}")
        
        # اجرا
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error = stderr.decode()
            logger.error(f"yt-dlp failed: {error}")
            raise Exception(f"yt-dlp failed: {error[:200]}")
        
        # پیدا کردن فایل دانلود شده
        downloaded_files = list(output_dir.glob("*"))
        if not downloaded_files:
            raise Exception("No file downloaded!")
        
        # گرفتن جدیدترین فایل
        filepath = max(downloaded_files, key=os.path.getctime)
        
        file_size = os.path.getsize(filepath)
        logger.info(f"Downloaded with yt-dlp: {filepath} ({format_bytes(file_size)})")
        
        return str(filepath)
    
    async def get_video_info(self, url: str) -> Optional[dict]:
        """
        دریافت اطلاعات ویدیو (بدون دانلود)
        
        فقط برای سایت‌های ویدیویی کار می‌کنه
        """
        if not self._is_video_site(url):
            return None
        
        try:
            cmd = ['yt-dlp', '--dump-json', '--no-warnings']
            
            # افزودن cookies
            if self.cookies_file and self.cookies_file.exists():
                cmd.extend(['--cookies', str(self.cookies_file)])
            
            cmd.append(url)
            
            logger.info(f"Getting video info: {url}")
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                error = stderr.decode()
                logger.error(f"Failed to get info: {error}")
                return None
            
            info = json.loads(stdout.decode())
            
            logger.info(f"Title: {info.get('title', 'Unknown')}")
            logger.info(f"Duration: {info.get('duration', 0)}s")
            
            return info
        
        except Exception as e:
            logger.error(f"Error getting info: {e}")
            return None
