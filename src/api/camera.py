"""
Camera API endpoints for streaming camera from Bambu Lab printers
Uses fresh connection per request with caching for fast response
"""
from fastapi import APIRouter, Response, HTTPException
from fastapi.responses import StreamingResponse
import logging
import time
import threading
from typing import Generator, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/camera", tags=["camera"])

# Configuration
BAMBU_PRINTER_IP = "192.168.4.101"
BAMBU_ACCESS_CODE = "34782589"
BAMBU_SERIAL_NUMBER = "03900D5A2402051"
BAMBU_PRINTER_MODEL = "Bambu Lab A1"

# Cache for frames
_last_frame: Optional[bytes] = None
_last_frame_time: float = 0
_frame_lock = threading.Lock()
_fetching = False
_fetch_lock = threading.Lock()

# Thread pool for camera operations
_executor = ThreadPoolExecutor(max_workers=3)


def _fetch_frame_sync(retry_count: int = 2) -> Optional[bytes]:
    """Synchronously fetch frame with fresh connection and retry logic"""
    from bambulab import JPEGFrameStream
    import socket
    
    last_error = None
    for attempt in range(retry_count):
        try:
            stream = JPEGFrameStream(BAMBU_PRINTER_IP, BAMBU_ACCESS_CODE)
            
            # Increase socket timeout for slow connections during printing
            stream.connect()
            
            # Try to set timeout on underlying socket if available
            if hasattr(stream, '_socket') and stream._socket:
                stream._socket.settimeout(10.0)
            
            try:
                frame = stream.get_frame()
                if frame:
                    return frame
            finally:
                try:
                    stream.disconnect()
                except:
                    pass
                    
        except socket.timeout as e:
            last_error = e
            logger.debug(f"Camera timeout attempt {attempt + 1}/{retry_count}")
            time.sleep(0.5)  # Brief pause before retry
        except Exception as e:
            last_error = e
            if attempt < retry_count - 1:
                logger.debug(f"Camera error attempt {attempt + 1}/{retry_count}: {e}")
                time.sleep(0.3)
            else:
                break
    
    if last_error:
        logger.warning(f"Camera frame error after {retry_count} attempts: {last_error}")
    return None


def get_fresh_frame(timeout: float = 8.0) -> Optional[bytes]:
    """Get a frame - returns cached if available, fetches new in background
    
    Increased timeout to 8s for stability during printing when camera
    responses may be slower.
    """
    global _last_frame, _last_frame_time, _fetching
    
    # Return cached frame immediately if fresh (within 500ms for smooth streaming)
    # Increased from 150ms to reduce camera load during printing
    with _frame_lock:
        if _last_frame and (time.time() - _last_frame_time) < 0.5:
            return _last_frame
    
    # Check if already fetching
    with _fetch_lock:
        if _fetching:
            # Return cached frame while waiting
            with _frame_lock:
                if _last_frame:
                    return _last_frame
            return None
        _fetching = True
    
    try:
        # Fetch new frame with retry
        future = _executor.submit(_fetch_frame_sync)
        frame = future.result(timeout=timeout)
        
        if frame:
            with _frame_lock:
                _last_frame = frame
                _last_frame_time = time.time()
            return frame
        
        # Return cached if fetch failed
        with _frame_lock:
            if _last_frame:
                return _last_frame
                
    except FuturesTimeoutError:
        logger.debug("Camera fetch timeout - using cached frame if available")
        with _frame_lock:
            if _last_frame:
                return _last_frame
    except Exception as e:
        logger.warning(f"Camera error: {e}")
    finally:
        with _fetch_lock:
            _fetching = False
    
    return None


@router.get("/snapshot")
async def get_snapshot():
    """
    Get a single JPEG snapshot from the printer camera
    """
    try:
        frame = get_fresh_frame()
        
        if frame:
            return Response(
                content=frame,
                media_type="image/jpeg",
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
        else:
            raise HTTPException(status_code=503, detail="Camera temporarily unavailable")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Camera snapshot error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshot/{printer_id}")
async def get_printer_snapshot(printer_id: str):
    """
    Get a snapshot from a specific printer (for multi-printer support)
    Currently only supports the configured printer
    """
    return await get_snapshot()


def generate_mjpeg_frames() -> Generator[bytes, None, None]:
    """
    Generator that yields MJPEG frames for streaming
    Like FDM Monster: continuous stream at higher FPS for smooth video
    """
    # Target ~3-5 FPS during printing for stability
    # Reduced from 8 FPS to handle slower camera responses during printing
    target_fps = 4
    frame_interval = 1.0 / target_fps
    
    consecutive_failures = 0
    max_failures = 30  # Increased tolerance - camera may be slow during printing
    
    while True:
        start_time = time.time()
        try:
            # Use longer timeout for MJPEG streaming during printing
            frame = get_fresh_frame(timeout=5.0)
            if frame:
                consecutive_failures = 0  # Reset on success
                yield (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n'
                    b'Content-Length: ' + str(len(frame)).encode() + b'\r\n'
                    b'\r\n' + frame + b'\r\n'
                )
            else:
                consecutive_failures += 1
                if consecutive_failures % 10 == 0:  # Log less frequently
                    logger.warning(f"No frame available ({consecutive_failures}/{max_failures})")
                
                if consecutive_failures >= max_failures:
                    logger.error("Too many consecutive failures, stopping stream")
                    break
                
                # Wait a bit before retrying when no frame
                time.sleep(0.5)
            
            # Calculate sleep time to maintain target FPS
            elapsed = time.time() - start_time
            sleep_time = max(0, frame_interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
                
        except GeneratorExit:
            logger.info("MJPEG stream closed by client")
            break
        except Exception as e:
            logger.error(f"MJPEG stream error: {e}")
            consecutive_failures += 1
            if consecutive_failures >= max_failures:
                break
            time.sleep(1.0)  # Longer wait on errors


@router.get("/stream")
async def get_stream():
    """
    Get MJPEG video stream from the printer camera
    Can be used directly in <img> tag: <img src="/api/camera/stream" />
    """
    return StreamingResponse(
        generate_mjpeg_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "close",
            "Access-Control-Allow-Origin": "*"
        }
    )


@router.get("/stream.mjpg")
async def get_stream_mjpg():
    """
    Alternative MJPEG stream endpoint (compatible with some clients)
    """
    return await get_stream()


@router.get("/status")
async def get_camera_status():
    """
    Get camera connection status and printer information
    """
    global _last_frame, _last_frame_time
    
    with _frame_lock:
        has_recent_frame = _last_frame is not None and (time.time() - _last_frame_time) < 10
        age = round(time.time() - _last_frame_time, 1) if _last_frame else None
    
    return {
        "printer": {
            "model": BAMBU_PRINTER_MODEL,
            "serial_number": BAMBU_SERIAL_NUMBER,
            "ip": BAMBU_PRINTER_IP,
            "access_code": BAMBU_ACCESS_CODE
        },
        "camera": {
            "available": True,
            "has_recent_frame": has_recent_frame,
            "last_frame_age": age,
        },
        "endpoints": {
            "stream_url": "/api/camera/stream",
            "snapshot_url": "/api/camera/snapshot",
            "status_url": "/api/camera/status"
        }
    }


@router.post("/reconnect")
async def reconnect_camera():
    """
    Clear cache and get fresh frame
    """
    global _last_frame, _last_frame_time
    
    with _frame_lock:
        _last_frame = None
        _last_frame_time = 0
    
    # Try to get a fresh frame
    frame = get_fresh_frame()
    
    if frame:
        return {"message": "Camera connected", "status": "connected", "frame_size": len(frame)}
    else:
        raise HTTPException(status_code=503, detail="Camera unavailable")
