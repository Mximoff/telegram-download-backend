from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from src.services.downloader import DownloaderService
from src.services.ytdlp import YtDlpService
from src.services.uploader import uploader
from src.utils.logger import logger
from src.utils.helpers import is_platform_url, delete_file, format_bytes
from src.config import config
import os
import asyncio

router = APIRouter()

class DownloadRequest(BaseModel):
    url: str
    chatId: int
    messageId: int
    userId: int
    fileName: str | None = None
    timestamp: int

# Progress tracking
upload_progress = {}

async def progress_callback(current, total, chat_id, message_id):
    """Progress callback for upload"""
    try:
        percent = (current / total) * 100
        
        # Update only every 5%
        key = f"{chat_id}_{message_id}"
        last_percent = upload_progress.get(key, 0)
        
        if percent - last_percent >= 5 or current == total:
            upload_progress[key] = percent
            
            await uploader.edit_message(
                chat_id,
                message_id,
                f"⏫ در حال آپلود...\n📊 {percent:.1f}%\n📦 {format_bytes(current)} / {format_bytes(total)}"
            )
    except Exception as e:
        logger.debug(f"Progress update failed: {e}")

@router.post("/download")
async def download_file(req: DownloadRequest):
    """Handle download request"""
    
    logger.info(f"Job received: {req.url} for user {req.userId}")
    
    filepath = None
    status_msg = None
    
    try:
        # Send status
        status_msg = await uploader.send_message(
            chat_id=req.chatId,
            text="🚀 سرور شروع به کار کرد...\n⏬ در حال دانلود...",
            reply_to=req.messageId
        )
        
        # Determine download method
        use_ytdlp = is_platform_url(req.url)
        
        if use_ytdlp:
            logger.info("Using yt-dlp")
            await uploader.edit_message(
                req.chatId,
                status_msg.id,
                "🎵 دانلود از پلتفرم...\n⏳ این کار ممکنه چند دقیقه طول بکشه..."
            )
            
            ytdlp = YtDlpService()
            filepath = await ytdlp.download(req.url, req.fileName)
        else:
            logger.info("Using direct download")
            downloader = DownloaderService()
            filepath = await downloader.download(req.url)
        
        # Get file size
        file_size = os.path.getsize(filepath)
        file_size_mb = file_size / 1024 / 1024
        
        logger.info(f"Download complete: {format_bytes(file_size)}")
        
        # Update status
        await uploader.edit_message(
            req.chatId,
            status_msg.id,
            f"✅ دانلود تمام شد!\n📦 حجم: {file_size_mb:.2f} MB\n⏫ شروع آپلود به تلگرام..."
        )
        
        # Determine filename
        final_filename = req.fileName if req.fileName else os.path.basename(filepath)
        
        # Upload to backup channel with progress
        backup_msg = await uploader.upload_document(
            chat_id=config.BACKUP_CHANNEL_ID,
            filepath=filepath,
            filename=final_filename,
            caption=f"🔗 {req.url}\n👤 User: {req.userId}\n📦 {format_bytes(file_size)}",
            progress_callback=lambda c, t: progress_callback(c, t, req.chatId, status_msg.id)
        )
        
        logger.info(f"Uploaded to backup channel")
        
        # Update status
        await uploader.edit_message(
            req.chatId,
            status_msg.id,
            f"✅ آپلود تمام شد!\n📤 در حال ارسال به شما..."
        )
        
        # Forward to user
        await uploader.forward_message(
            to_chat=req.chatId,
            from_chat=config.BACKUP_CHANNEL_ID,
            message_id=backup_msg.id,
            reply_to=req.messageId
        )
        
        # Final status
        await uploader.edit_message(
            req.chatId,
            status_msg.id,
            f"✅ تکمیل شد!\n📦 {file_size_mb:.2f} MB"
        )
        
        # Cleanup progress tracking
        key = f"{req.chatId}_{status_msg.id}"
        if key in upload_progress:
            del upload_progress[key]
        
        logger.info(f"Job completed successfully: {req.url}")
        
        return {
            "success": True,
            "fileSize": file_size,
            "fileId": backup_msg.document.id
        }
        
    except Exception as e:
        logger.error(f"Job failed: {str(e)}", exc_info=True)
        
        # Notify user
        if status_msg:
            try:
                error_msg = str(e)
                if len(error_msg) > 100:
                    error_msg = error_msg[:100] + "..."
                
                await uploader.edit_message(
                    req.chatId,
                    status_msg.id,
                    f"❌ خطا در دانلود:\n{error_msg}\n\n💡 نکات:\n• اگه لینک نیاز به لاگین داره، cookies.txt رو اضافه کن\n• برخی سایت‌ها ممکنه VPN نیاز داشته باشن"
                )
            except Exception as edit_error:
                logger.error(f"Failed to send error message: {edit_error}")
        
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Cleanup
        if filepath and os.path.exists(filepath):
            await delete_file(filepath)
            logger.debug(f"Cleaned up: {filepath}")