import os
import aiohttp
import aiofiles
from src.utils.logger import logger
from src.utils.helpers import get_random_user_agent, get_random_proxy, get_temp_filepath, format_bytes
from src.config import config

class DownloaderService:
    async def download(self, url: str) -> str:
        """Download file from URL"""
        filepath = get_temp_filepath()
        user_agent = get_random_user_agent()
        proxy = get_random_proxy()
        
        headers = {
            'User-Agent': user_agent,
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        logger.info(f"Downloading: {url}")
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