import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Server
    PORT = int(os.getenv('PORT', 8080))
    BACKEND_SECRET = os.getenv('BACKEND_SECRET')
    
    # Telegram
    TELEGRAM_API_ID = int(os.getenv('TELEGRAM_API_ID'))
    TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    BACKUP_CHANNEL_ID = int(os.getenv('BACKUP_CHANNEL_ID'))
    
    # Limits
    MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 2147483648))  # 2GB
    
    # Paths
    DOWNLOAD_DIR = '/tmp/downloads'
    SESSION_DIR = '/app/sessions'
    COOKIE_FILE = os.getenv('COOKIE_FILE', '/app/cookies.txt')
    
    # Proxy
    PROXY_LIST = [p.strip() for p in os.getenv('PROXY_LIST', '').split(',') if p.strip()]
    
    # User agents
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    ]

config = Config()

# Validate
if not all([config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH, config.BOT_TOKEN, config.BACKEND_SECRET]):
    raise ValueError("Missing required environment variables!")