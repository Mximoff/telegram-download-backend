import os
import asyncio
from typing import Optional
from yt_dlp import YoutubeDL
from src.utils.logger import logger
from src.utils.helpers import get_temp_filepath, get_random_user_agent, get_random_proxy, sanitize_filename
from src.config import config

class YtDlpService:
    
    PLATFORM_CONFIGS = {
        'youtube': {
            'format': 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'merge_output_format': 'mp4',
        },
        'spotify': {
            'format': 'bestaudio/best',
            'extract_audio': True,
            'audio_format': 'mp3',
            'audio_quality': '320K',
        },
        'deezer': {
            'format': 'bestaudio/best',
            'extract_audio': True,
            'audio_format': 'mp3',
            'audio_quality': '320K',
        },
        'soundcloud': {
            'format': 'bestaudio/best',
            'extract_audio': True,
            'audio_format': 'mp3',
            'audio_quality': '320K',
        },
        'pornhub': {
            'format': 'best[height<=1080]',
            'age_limit': 18,
        },
        'xvideos': {
            'format': 'best',
            'age_limit': 18,
        },
        'xnxx': {
            'format': 'best',
            'age_limit': 18,
        }
    }
    
    def _detect_platform(self, url: str) -> Optional[str]:
        """Detect platform from URL"""
        url_lower = url.lower()
        
        if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            return 'youtube'
        elif 'spotify.com' in url_lower:
            return 'spotify'
        elif 'deezer.com' in url_lower:
            return 'deezer'
        elif 'soundcloud.com' in url_lower:
            return 'soundcloud'
        elif 'pornhub.com' in url_lower:
            return 'pornhub'
        elif 'xvideos.com' in url_lower:
            return 'xvideos'
        elif 'xnxx.com' in url_lower:
            return 'xnxx'
        
        return None
    
    def _get_ydl_opts(self, platform: Optional[str], output_path: str) -> dict:
        """Build yt-dlp options"""
        
        # Base options
        opts = {
            'outtmpl': output_path + '.%(ext)s',
            'quiet': False,
            'no_warnings': False,
            'restrictfilenames': True,
            'user_agent': get_random_user_agent(),
            'retries': 5,
            'fragment_retries': 5,
            'socket_timeout': 30,
        }
        
        # Add cookies if available
        if os.path.exists(config.COOKIE_FILE):
            opts['cookiefile'] = config.COOKIE_FILE
            logger.info(f"Using cookies from: {config.COOKIE_FILE}")
        
        # Add proxy if available
        proxy = get_random_proxy()
        if proxy:
            opts['proxy'] = proxy
            logger.info(f"Using proxy: {proxy}")
        
        # Platform-specific config
        if platform and platform in self.PLATFORM_CONFIGS:
            platform_opts = self.PLATFORM_CONFIGS[platform].copy()
            
            # Handle audio extraction
            if platform_opts.get('extract_audio'):
                opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': platform_opts.get('audio_format', 'mp3'),
                    'preferredquality': platform_opts.get('audio_quality', '320'),
                }]
                del platform_opts['extract_audio']
                if 'audio_format' in platform_opts:
                    del platform_opts['audio_format']
                if 'audio_quality' in platform_opts:
                    del platform_opts['audio_quality']
            
            opts.update(platform_opts)
            logger.info(f"Applied {platform} config")
        
        return opts
    
    async def download(self, url: str, custom_filename: Optional[str] = None) -> str:
        """Download media using yt-dlp"""
        
        platform = self._detect_platform(url)
        output_path = get_temp_filepath(f"ytdlp_{platform or 'unknown'}")
        
        logger.info(f"yt-dlp download started")
        logger.info(f"URL: {url}")
        logger.info(f"Platform: {platform or 'unknown'}")
        logger.info(f"Output: {output_path}")
        
        ydl_opts = self._get_ydl_opts(platform, output_path)
        
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        
        def _download():
            with YoutubeDL(ydl_opts) as ydl:
                try:
                    # Extract info and download
                    info = ydl.extract_info(url, download=True)
                    
                    # Get the actual filename
                    filename = ydl.prepare_filename(info)
                    
                    # Check if file exists
                    if not os.path.exists(filename):
                        raise FileNotFoundError(f"Downloaded file not found: {filename}")
                    
                    return filename
                    
                except Exception as e:
                    logger.error(f"yt-dlp error: {e}")
                    raise
        
        try:
            filepath = await loop.run_in_executor(None, _download)
            
            file_size = os.path.getsize(filepath)
            logger.info(f"yt-dlp success: {filepath} ({file_size} bytes)")
            
            return filepath
            
        except Exception as e:
            logger.error(f"yt-dlp failed: {e}", exc_info=True)
            raise Exception(f"Failed to download from {platform or 'platform'}: {str(e)}")