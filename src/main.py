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
    
    # Initialize global Bambu MQTT client from database
    logger.info("Initializing Bambu Lab MQTT client...")
    from src.database.db import Printer
    db = next(get_db())
    first_printer = db.query(Printer).first()
    
    if first_printer and first_printer.printer_id:
        bambu_client = initialize_bambu_client(
            printer_id=first_printer.printer_id,
            printer_ip=first_printer.printer_ip,
            access_code=first_printer.access_code,
            use_lan_mode=True
        )
        logger.info(f"✅ MQTT initialized for: {first_printer.printer_name} ({first_printer.printer_id}) at {first_printer.printer_ip}")
    else:
        # Fallback to env vars if no printer in database
        bambu_client = initialize_bambu_client(
            printer_id=BAMBU_SERIAL,
            printer_ip=BAMBU_PRINTER_IP,
            access_code=BAMBU_ACCESS_CODE,
            use_lan_mode=True
        )
        logger.warning("⚠️ No printer in database, using environment variables (may not connect)")
    db.close()
    
    # Handler for when print is completed successfully
    def handle_print_complete():
        """Update queue status when print completes successfully (100%)"""
        logger.info("✅ Print completed - checking for loop...")
        try:
            db = next(get_db())
            # Find running or paused queue item
            active_queue = db.query(Queue).filter(
                Queue.status.in_(["running", "paused"])
            ).first()
            
            if active_queue:
                job = db.query(Job).filter(Job.job_id == active_queue.job_id).first()
                
                # Note: current_loop is already incremented when print started
                logger.info(f"📊 Loop {active_queue.current_loop}/{job.loop_count if job else 1} completed")
                
                # Check if should repeat
                if job and active_queue.current_loop < job.loop_count:
                    # Need to repeat - auto start next loop
                    logger.info(f"🔄 Starting loop {active_queue.current_loop + 1}/{job.loop_count}...")
                    active_queue.status = "pending"
                    db.commit()
                    
                    # Auto-start next loop in background thread
                    import threading
                    from src.services.queue_service import QueueService
                    
                    def auto_start_next_loop():
                        try:
                            logger.info(f"🚀 Auto-starting loop {active_queue.current_loop + 1}/{job.loop_count}")
                            queue_service = QueueService(db)
                            success = queue_service.start_queue_job(active_queue.queue_id)
                            if success:
                                logger.info(f"✅ Loop {active_queue.current_loop + 1} started successfully")
                            else:
                                logger.error(f"❌ Failed to auto-start loop {active_queue.current_loop + 1}")
                        except Exception as e:
                            logger.error(f"❌ Error auto-starting next loop: {e}")
                    
                    thread = threading.Thread(target=auto_start_next_loop, daemon=True)
                    thread.start()
                else:
                    # All loops finished
                    logger.info(f"✅ All loops finished ({active_queue.current_loop}/{job.loop_count if job else 1}) - marking as finished")
                    active_queue.status = "finished"
                    
                    # Update job status too
                    if job:
                        job.status = "finished"
                    
                    db.commit()
                
                logger.info(f"✅ Queue status updated")
            else:
                logger.info("No active queue item found to update")
            db.close()
        except Exception as e:
            logger.error(f"Error updating queue on print complete: {e}")
    
    # NOTE: Print completion callbacks MUST be set here at startup
    # PrintControlService callback needs to be active for auto-loop functionality
    
    # Setup PrintControlService with callbacks at startup
    if bambu_client:
        from src.services.print_control_service import PrintControlService
        from src.database import SessionLocal
        
        # Create a persistent PrintControlService instance
        startup_db = SessionLocal()
        print_control_service = PrintControlService(startup_db, bambu_client)
        logger.info("✅ PrintControlService callbacks registered")
        
        # Store reference to prevent garbage collection
        app.state.print_control_service = print_control_service
        app.state.startup_db = startup_db
    
    if bambu_client and bambu_client.mqtt_connected:
        logger.info(f"✅ Bambu MQTT client connected to {BAMBU_PRINTER_IP}")
    else:
        logger.warning("⚠️ Bambu MQTT client connection pending...")
    
    yield
    
    # Shutdown
    logger.info("Shutting down 3D Print Farm Management System")
    
    # Close startup database session
    if hasattr(app.state, 'startup_db'):
        app.state.startup_db.close()
        logger.info("Startup database session closed")
    
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
    allow_origins=["*"],  # Allow all origins for development
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
# Printer will access: http://controller-ip:5051/uploads/filename.3mf
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
from src.api.bed_cooling import router as bed_cooling_router  # Bed cooling control
from src.api.discovery import router as discovery_router  # Printer auto-discovery

# Include API routers
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
app.include_router(bed_cooling_router)
app.include_router(discovery_router, prefix="/api/discovery", tags=["discovery"])


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
