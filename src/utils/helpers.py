import os
import random
import aiofiles
from pathlib import Path
from src.config import config
from datetime import datetime
def get_random_user_agent() -> str:
    return random.choice(config.USER_AGENTS)

def get_random_proxy() -> str | None:
    if not config.PROXY_LIST:
        return None
    return random.choice(config.PROXY_LIST)

def sanitize_filename(filename: str) -> str:
    """Remove invalid characters from filename"""
    invalid_chars = '<>:"/\\|?*\x00-\x1f'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename[:200]  # Limit length

def get_temp_filepath(prefix: str = 'download') -> str:
    """Generate unique temp file path"""
    timestamp = int(datetime.now().timestamp() * 1000)
    random_str = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
    return os.path.join(config.DOWNLOAD_DIR, f"{prefix}_{timestamp}_{random_str}")

async def ensure_dir(path: str):
    """Create directory if not exists"""
    Path(path).mkdir(parents=True, exist_ok=True)

async def delete_file(filepath: str):
    """Delete file safely"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception:
        pass

def format_bytes(size: int) -> str:
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"

def is_platform_url(url: str) -> bool:
    """Check if URL is from supported platform"""
    platforms = [
        'youtube.com', 'youtu.be', 'spotify.com', 'deezer.com',
        'soundcloud.com', 'pornhub.com', 'xvideos.com', 'xnxx.com'
    ]
    url_lower = url.lower()
    return any(platform in url_lower for platform in platforms)