import os
from telethon import TelegramClient
from telethon.tl.types import DocumentAttributeFilename
from src.config import config
from src.utils.logger import logger
from src.utils.helpers import format_bytes

class UploaderService:
    def __init__(self):
        self.client = TelegramClient(
            session=os.path.join(config.SESSION_DIR, 'bot_session'),
            api_id=config.TELEGRAM_API_ID,
            api_hash=config.TELEGRAM_API_HASH
        )
        self._started = False
    
    async def start(self):
        """Start Telethon client"""
        if not self._started:
            await self.client.start(bot_token=config.BOT_TOKEN)
            self._started = True
            me = await self.client.get_me()
            logger.info(f"Telethon started as @{me.username}")
    
    async def stop(self):
        """Stop Telethon client"""
        if self._started:
            await self.client.disconnect()
            self._started = False
            logger.info("Telethon stopped")
    
    async def send_message(
        self, 
        chat_id: int, 
        text: str, 
        reply_to: int | None = None
    ):
        """Send text message"""
        await self.start()
        return await self.client.send_message(
            entity=chat_id,
            message=text,
            reply_to=reply_to
        )
    
    async def edit_message(
        self, 
        chat_id: int, 
        message_id: int, 
        text: str
    ):
        """Edit message text"""
        try:
            await self.start()
            return await self.client.edit_message(
                entity=chat_id,
                message=message_id,
                text=text
            )
        except Exception as e:
            logger.warning(f"Failed to edit message: {e}")
            return None
    
    async def upload_document(
        self,
        chat_id: int,
        filepath: str,
        caption: str | None = None,
        reply_to: int | None = None,
        filename: str | None = None,
        progress_callback=None
    ):
        """Upload document to Telegram"""
        await self.start()
        
        file_size = os.path.getsize(filepath)
        logger.info(f"Uploading: {filepath}")
        logger.info(f"Size: {format_bytes(file_size)}")
        
        # Check size limit (2GB for bots)
        if file_size > config.MAX_FILE_SIZE:
            raise Exception(f"File too large: {format_bytes(file_size)}")
        
        # Use custom filename if provided
        if not filename:
            filename = os.path.basename(filepath)
        
        # Create document attributes
        attributes = [DocumentAttributeFilename(file_name=filename)]
        
        # Upload with progress
        message = await self.client.send_file(
            entity=chat_id,
            file=filepath,
            caption=caption,
            reply_to=reply_to,
            attributes=attributes,
            force_document=True,
            progress_callback=progress_callback,
            silent=file_size > 50 * 1024 * 1024  # Silent for files > 50MB
        )
        
        logger.info(f"Upload completed: file_id={message.document.id}")
        return message
    
    async def forward_message(
        self,
        to_chat: int,
        from_chat: int,
        message_id: int,
        reply_to: int | None = None
    ):
        """Forward message without quote"""
        await self.start()
        
        # Get the message first
        message = await self.client.get_messages(from_chat, ids=message_id)
        
        # Send as copy (forward without quote)
        return await self.client.send_message(
            entity=to_chat,
            message=message.message if hasattr(message, 'message') else '',
            file=message.media if hasattr(message, 'media') else None,
            reply_to=reply_to
        )

# Global instance
uploader = UploaderService()