"""
Main FastAPI application
Entry point for 3D Print Farm Management System
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.config import (
    API_TITLE,
    API_VERSION,
    API_DESCRIPTION,
    DEBUG,
    LOG_LEVEL,
    CORS_ORIGINS,
    BAMBU_PRINTER_IP,
    BAMBU_ACCESS_CODE,
    BAMBU_SERIAL,
)
from src.database import init_db
from src.database.db import get_db, Queue, Job
from src.services.bambu_service import initialize_bambu_client, shutdown_bambu_client

# Configure logging - reduce noise from uvicorn access logs
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
# Reduce uvicorn access log noise
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler
    Startup and shutdown logic
    """
    import asyncio
    from src.api.websocket import set_main_loop
    
    # Startup
    logger.info("Starting 3D Print Farm Management System")
    
    # Set the main event loop for WebSocket broadcasting from sync code
    loop = asyncio.get_running_loop()
    set_main_loop(loop)
    logger.info(f"Event loop configured for WebSocket broadcasts")
    
    init_db()
    logger.info("Database initialized successfully")
    
    # Initialize global Bambu MQTT client for A1 printer
    logger.info("Initializing Bambu Lab MQTT client...")
    bambu_client = initialize_bambu_client(
        printer_id=BAMBU_SERIAL,
        printer_ip=BAMBU_PRINTER_IP,
        access_code=BAMBU_ACCESS_CODE,
        use_lan_mode=True
    )
    
    # Handler for when print is stopped from printer directly
    def handle_print_stopped():
        """Update queue status when print is stopped from printer"""
        logger.info("🛑 Print stopped from printer - updating queue status...")
        try:
            db = next(get_db())
            # Find running or paused queue item
            active_queue = db.query(Queue).filter(
                Queue.status.in_(["running", "paused"])
            ).first()
            
            if active_queue:
                logger.info(f"Updating queue_id={active_queue.queue_id} status to 'stopped'")
                active_queue.status = "stopped"
                
                # Update job status too
                job = db.query(Job).filter(Job.job_id == active_queue.job_id).first()
                if job:
                    job.status = "stopped"
                
                db.commit()
                logger.info(f"✅ Queue status updated to 'stopped'")
            else:
                logger.info("No active queue item found to update")
            db.close()
        except Exception as e:
            logger.error(f"Error updating queue on print stop: {e}")
    
    # Set callbacks
    if bambu_client:
        bambu_client.on_print_stopped = handle_print_stopped
    
    if bambu_client and bambu_client.mqtt_connected:
        logger.info(f"✅ Bambu MQTT client connected to {BAMBU_PRINTER_IP}")
    else:
        logger.warning("⚠️ Bambu MQTT client connection pending...")
    
    yield
    
    # Shutdown
    logger.info("Shutting down 3D Print Farm Management System")
    shutdown_bambu_client()
    logger.info("Bambu MQTT client disconnected")


# Create FastAPI application
app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=API_DESCRIPTION,
    debug=DEBUG,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Health Check Endpoints ====================

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - API health check"""
    return {
        "status": "ok",
        "application": API_TITLE,
        "version": API_VERSION,
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "3D Print Farm Management System",
    }


# ==================== Static File Serving ====================

from fastapi.staticfiles import StaticFiles
from src.config import UPLOAD_DIR

# Serve uploaded files for printer download
# Printer will access: http://controller-ip:5000/uploads/filename.3mf
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


# ==================== API Routes ====================

from src.api.jobs import router as jobs_router
from src.api.printers import router as printers_router
from src.api.queue import router as queue_router
from src.api.print_control import router as print_control_router
from src.api.history import router as history_router
from src.api.websocket import router as websocket_router
from src.api.camera import router as camera_router
from src.api.printer_files import router as printer_files_router
from src.api.filaments import router as filaments_router
from src.api.bucket_list import router as bucket_list_router
from src.api.templates_db import router as templates_router  # Changed to database version
from src.api.presets import router as presets_router

# Include routers
app.include_router(jobs_router)
app.include_router(printers_router)
app.include_router(queue_router)
app.include_router(print_control_router)
app.include_router(history_router)
app.include_router(websocket_router)
app.include_router(camera_router)
app.include_router(printer_files_router)
app.include_router(filaments_router)
app.include_router(bucket_list_router)
app.include_router(templates_router)
app.include_router(presets_router)


if __name__ == "__main__":
    import uvicorn
    
    from src.config import HOST, PORT, RELOAD
    
    logger.info(f"Starting server on {HOST}:{PORT}")
    uvicorn.run(
        "src.main:app",
        host=HOST,
        port=PORT,
        reload=RELOAD,
        log_level=LOG_LEVEL.lower(),
    )
