from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime
from src.config import config
from src.routes.download import router as download_router
from src.services.uploader import uploader
from src.utils.logger import logger
from src.utils.helpers import ensure_dir

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("=" * 50)
    logger.info("Starting Telegram Downloader Backend")
    logger.info("=" * 50)
    
    # Ensure directories exist
    await ensure_dir(config.DOWNLOAD_DIR)
    await ensure_dir(config.SESSION_DIR)
    logger.info(f"Download dir: {config.DOWNLOAD_DIR}")
    logger.info(f"Session dir: {config.SESSION_DIR}")
    
    # Start Telethon
    await uploader.start()
    
    logger.info(f"Server ready on port {config.PORT}")
    logger.info("=" * 50)
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await uploader.stop()
    logger.info("Bye!")

app = FastAPI(
    title="Telegram Downloader Backend",
    description="Backend for downloading and uploading files to Telegram",
    version="1.0.0",
    lifespan=lifespan
)

# Auth dependency
async def verify_token(authorization: str = Header(None)):
    """Verify authorization token"""
    if not authorization:
        raise HTTPException(
            status_code=401, 
            detail="Missing Authorization header"
        )
    
    token = authorization.replace("Bearer ", "")
    if token != config.BACKEND_SECRET:
        raise HTTPException(
            status_code=403, 
            detail="Invalid token"
        )

# Health endpoints (no auth)
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "timestamp": int(datetime.now().timestamp()),
        "version": "1.0.0"
    }

@app.get("/ping")
async def ping():
    """Ping endpoint"""
    return {"pong": int(datetime.now().timestamp())}

# Root
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Telegram Downloader Backend",
        "version": "1.0.0",
        "status": "running"
    }

# API info
@app.get("/api")
async def api_info():
    """API information"""
    return {
        "name": "Telegram Downloader API",
        "version": "1.0.0",
        "endpoints": {
            "download": "/api/download (POST)",
            "health": "/health (GET)",
            "ping": "/ping (GET)"
        }
    }

# Include API routes with auth
app.include_router(
    download_router,
    prefix="/api",
    dependencies=[Depends(verify_token)],
    tags=["download"]
)

# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc)
        }
    )

# 404 handler
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors"""
    return JSONResponse(
        status_code=404,
        content={"error": "Not found"}
    )

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=config.PORT,
        workers=1,
        log_level="info",
        access_log=True
    )