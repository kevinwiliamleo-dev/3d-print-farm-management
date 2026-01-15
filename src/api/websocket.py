"""
WebSocket API for real-time printer status updates
Provides live status, print progress, and queue updates

IMPROVED: Uses singleton MQTT client instead of creating new connections
"""
import asyncio
import json
import logging
import time
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from src.database import get_db
from src.database.db import Printer, Queue, Job
# Note: check_mqtt_status is no longer used here - we use singleton client instead

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, printer_id: str = "all"):
        await websocket.accept()
        async with self._lock:
            if printer_id not in self.active_connections:
                self.active_connections[printer_id] = set()
            self.active_connections[printer_id].add(websocket)
        # Removed verbose logging
    
    async def disconnect(self, websocket: WebSocket, printer_id: str = "all"):
        async with self._lock:
            if printer_id in self.active_connections:
                self.active_connections[printer_id].discard(websocket)
                if not self.active_connections[printer_id]:
                    del self.active_connections[printer_id]
        # Removed verbose logging
    
    async def broadcast(self, message: dict, printer_id: str = "all"):
        """Send message to all connections for a printer"""
        async with self._lock:
            connections = set()
            if printer_id in self.active_connections:
                connections.update(self.active_connections[printer_id])
            if "all" in self.active_connections:
                connections.update(self.active_connections["all"])
        
        msg_type = message.get('type', 'unknown')
        if msg_type == 'upload_progress':
            percent = message.get('progress', {}).get('percent', 0)
            logger.info(f"📡 Broadcasting {msg_type} ({percent}%) to {len(connections)} connections")
        
        sent_count = 0
        for connection in connections:
            try:
                await connection.send_json(message)
                sent_count += 1
            except Exception as e:
                logger.warning(f"Failed to send WebSocket message: {e}")
        
        if msg_type == 'upload_progress' and sent_count > 0:
            logger.info(f"✅ Sent to {sent_count}/{len(connections)} connections")


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/status")
async def websocket_all_status(websocket: WebSocket):
    """
    WebSocket endpoint for all printer status updates
    
    Sends periodic updates with all printer statuses
    """
    await manager.connect(websocket, "all")
    # Removed verbose logging
    
    try:
        status_update_counter = 0
        while True:
            # Wait for messages or send periodic updates
            try:
                # Check for incoming messages (with short timeout to allow processing other coroutines)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=0.1  # Short timeout to allow processing upload progress broadcasts
                )
                
                # Handle incoming commands
                try:
                    command = json.loads(data)
                    action = command.get("action")
                    if action == "refresh":
                        # Force refresh status
                        try:
                            await send_all_status(websocket)
                        except Exception as e:
                            logger.error(f"Error sending status on refresh: {e}", exc_info=True)
                    elif action == "ping":
                        # Respond to ping with pong to keep connection alive
                        try:
                            await websocket.send_json({"type": "pong", "timestamp": int(time.time() * 1000)})
                        except Exception as e:
                            logger.debug(f"Error sending pong: {e}")
                except json.JSONDecodeError:
                    pass
                    
            except asyncio.TimeoutError:
                # Increment counter and send status every 50 iterations (~5 seconds)
                status_update_counter += 1
                if status_update_counter >= 50:
                    status_update_counter = 0
                    try:
                        await send_all_status(websocket)
                    except Exception as e:
                        logger.error(f"Error sending periodic status: {e}", exc_info=True)
                # Short yield to allow other coroutines to run
                await asyncio.sleep(0)
                
    except WebSocketDisconnect:
        await manager.disconnect(websocket, "all")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket, "all")


@router.websocket("/ws/printer/{printer_id}")
async def websocket_printer_status(websocket: WebSocket, printer_id: str):
    """
    WebSocket endpoint for specific printer status
    
    Sends real-time updates for a single printer
    """
    await manager.connect(websocket, printer_id)
    
    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=3.0
                )
                
                command = json.loads(data)
                action = command.get("action")
                if action == "refresh":
                    await send_printer_status(websocket, printer_id)
                elif action == "ping":
                    # Respond to ping with pong to keep connection alive
                    try:
                        await websocket.send_json({"type": "pong", "timestamp": int(time.time() * 1000)})
                    except Exception as e:
                        logger.debug(f"Error sending pong: {e}")
                    
            except asyncio.TimeoutError:
                await send_printer_status(websocket, printer_id)
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        await manager.disconnect(websocket, printer_id)
    except Exception as e:
        logger.error(f"WebSocket error for {printer_id}: {e}")
        await manager.disconnect(websocket, printer_id)


async def send_all_status(websocket: WebSocket):
    """Send status for all printers - enhanced with full printer data from database"""
    from src.database import SessionLocal
    from src.services.bambu_service import get_bambu_client
    
    db = None
    try:
        db = SessionLocal()
        printers = db.query(Printer).all()
        
        if not printers:
            logger.warning("No printers found in database")
        
        # Get singleton MQTT client for live status
        bambu_client = get_bambu_client()
        
        status_list = []
        for printer in printers:
            try:
                # Get queue info
                queue_items = db.query(Queue).filter(
                    Queue.printer_id == printer.printer_id,
                    Queue.status.in_(["pending", "running"])
                ).count()
                
                running_job = db.query(Queue).filter(
                    Queue.printer_id == printer.printer_id,
                    Queue.status == "running"
                ).first()
                
                # Use live status from MQTT client if available
                if bambu_client and bambu_client.printer_id == printer.printer_id and bambu_client.mqtt_connected:
                    # Live data from MQTT client
                    status_list.append({
                        "printer_id": printer.printer_id,
                        "printer_name": printer.printer_name,
                        "status": bambu_client.printer_status,
                        "mqtt_connected": True,
                        "reconnecting": False,
                        "queue_count": queue_items,
                        "current_job": running_job.job_id if running_job else None,
                        # Additional live data
                        "print_progress": bambu_client.current_print_progress,
                        "nozzle_temp": bambu_client.nozzle_temp,
                        "nozzle_target_temp": bambu_client.nozzle_target_temp,
                        "bed_temp": bambu_client.bed_temp,
                        "bed_target_temp": bambu_client.bed_target_temp,
                        "chamber_temp": bambu_client.chamber_temp,
                    })
                elif bambu_client and bambu_client.printer_id == printer.printer_id and not bambu_client.mqtt_connected:
                    # MQTT client exists but not connected - likely reconnecting
                    is_reconnecting = bambu_client.connection_state.reconnect_attempts > 0 if bambu_client.connection_state else False
                    status_list.append({
                        "printer_id": printer.printer_id,
                        "printer_name": printer.printer_name,
                        "status": "offline",
                        "mqtt_connected": False,
                        "reconnecting": is_reconnecting,
                        "reconnect_attempts": bambu_client.connection_state.reconnect_attempts if bambu_client.connection_state else 0,
                        "queue_count": queue_items,
                        "current_job": running_job.job_id if running_job else None,
                        # Data from database
                        "print_progress": getattr(printer, 'print_progress', 0) or 0,
                        "nozzle_temp": getattr(printer, 'nozzle_temp', 0) or 0,
                        "nozzle_target_temp": getattr(printer, 'nozzle_target_temp', 0) or 0,
                        "bed_temp": getattr(printer, 'bed_temp', 0) or 0,
                        "bed_target_temp": getattr(printer, 'bed_target_temp', 0) or 0,
                        "chamber_temp": getattr(printer, 'chamber_temp', 0) or 0,
                    })
                else:
                    # Data from database (synced from MQTT)
                    status_list.append({
                        "printer_id": printer.printer_id,
                        "printer_name": printer.printer_name,
                        "status": printer.status or "offline",
                        "mqtt_connected": printer.mqtt_connected,
                        "reconnecting": False,
                        "queue_count": queue_items,
                        "current_job": running_job.job_id if running_job else None,
                        # Data from database
                        "print_progress": getattr(printer, 'print_progress', 0) or 0,
                        "remaining_time": getattr(printer, 'remaining_time', 0) or 0,  # seconds
                        "current_file": getattr(printer, 'current_file', None),
                        "nozzle_temp": getattr(printer, 'nozzle_temp', 0) or 0,
                        "nozzle_target_temp": getattr(printer, 'nozzle_target_temp', 0) or 0,
                        "bed_temp": getattr(printer, 'bed_temp', 0) or 0,
                        "bed_target_temp": getattr(printer, 'bed_target_temp', 0) or 0,
                        "chamber_temp": getattr(printer, 'chamber_temp', 0) or 0,
                    })
            except Exception as e:
                logger.error(f"Error processing printer {printer.printer_id}: {e}")
                continue
        
        # Send message
        message = {
            "type": "status_update",
            "printers": status_list,
            "timestamp": int(time.time() * 1000)
        }
        
        try:
            await websocket.send_json(message)
            logger.debug(f"Sent status update: {len(status_list)} printers")
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
        
    except Exception as e:
        logger.error(f"Error in send_all_status: {e}", exc_info=True)
    finally:
        if db:
            try:
                db.close()
            except:
                pass


async def send_printer_status(websocket: WebSocket, printer_id: str):
    """Send status for specific printer - uses singleton MQTT client with full data"""
    from src.database import SessionLocal
    from src.services.bambu_service import get_bambu_client
    
    try:
        db = SessionLocal()
        printer = db.query(Printer).filter(
            Printer.printer_id == printer_id
        ).first()
        
        if not printer:
            await websocket.send_json({
                "type": "error",
                "message": f"Printer not found: {printer_id}"
            })
            return
        
        # Get status from singleton MQTT client (no new connection!)
        bambu_client = get_bambu_client()
        
        if bambu_client and bambu_client.printer_id == printer_id and bambu_client.mqtt_connected:
            # Use live status from persistent connection
            printer_data = {
                "printer_id": printer.printer_id,
                "printer_name": printer.printer_name,
                "status": bambu_client.printer_status,
                "mqtt_connected": True,
                "printing": bambu_client.printer_status == "printing",
                "progress": bambu_client.current_print_progress,
                # Temperature data
                "nozzle_temp": bambu_client.nozzle_temp,
                "nozzle_target_temp": bambu_client.nozzle_target_temp,
                "bed_temp": bambu_client.bed_temp,
                "bed_target_temp": bambu_client.bed_target_temp,
                "chamber_temp": bambu_client.chamber_temp,
                # Remaining time from database (updated via MQTT)
                "remaining_time": getattr(printer, 'remaining_time', 0) or 0,
                "current_file": getattr(printer, 'current_file', '') or '',
            }
        else:
            # Use database status (synced from MQTT)
            printer_data = {
                "printer_id": printer.printer_id,
                "printer_name": printer.printer_name,
                "status": printer.status or "offline",
                "mqtt_connected": printer.mqtt_connected,
                "printing": printer.status == "printing",
                "progress": getattr(printer, 'print_progress', 0) or 0,
                # Temperature data from database
                "nozzle_temp": getattr(printer, 'nozzle_temp', 0) or 0,
                "nozzle_target_temp": getattr(printer, 'nozzle_target_temp', 0) or 0,
                "bed_temp": getattr(printer, 'bed_temp', 0) or 0,
                "bed_target_temp": getattr(printer, 'bed_target_temp', 0) or 0,
                "chamber_temp": getattr(printer, 'chamber_temp', 0) or 0,
                # Remaining time from database
                "remaining_time": getattr(printer, 'remaining_time', 0) or 0,
                "current_file": getattr(printer, 'current_file', '') or '',
            }
        
        # Get queue info
        queue_items = db.query(Queue).filter(
            Queue.printer_id == printer_id
        ).order_by(Queue.position_in_queue).all()
        
        queue_list = []
        for item in queue_items:
            job = db.query(Job).filter(Job.job_id == item.job_id).first()
            queue_list.append({
                "queue_id": item.queue_id,
                "job_id": item.job_id,
                "job_name": job.job_name if job else None,
                "position": item.position_in_queue,
                "current_loop": item.current_loop,
                "loop_count": job.loop_count if job else 1,
                "status": item.status,
            })
        
        await websocket.send_json({
            "type": "printer_status",
            "printer": printer_data,
            "queue": queue_list,
            "timestamp": asyncio.get_event_loop().time()
        })
        
    except Exception as e:
        logger.error(f"Error sending printer status: {e}")
    finally:
        db.close()


async def broadcast_printer_update(printer_id: str, status: dict):
    """
    Broadcast printer status update to all connected clients
    Called by MQTT service when printer status changes
    """
    await manager.broadcast({
        "type": "printer_update",
        "printer_id": printer_id,
        "status": status,
    }, printer_id)


async def broadcast_upload_progress(printer_id: str, progress: dict):
    """
    Broadcast file upload progress to all connected clients
    Called when uploading file to printer SD card
    
    Args:
        printer_id: Target printer
        progress: Dict with keys: percent, bytes_sent, total_bytes, filename, status
    """
    message = {
        "type": "upload_progress",
        "printer_id": printer_id,
        "progress": progress,
    }
    
    # Broadcast to printer-specific connections
    await manager.broadcast(message, printer_id)
    
    # Also broadcast to "all" connections
    await manager.broadcast(message, "all")


# Global variable to store the main event loop
_main_loop = None

# Queue for progress updates (thread-safe)
import queue
_progress_queue: queue.Queue = queue.Queue()

def set_main_loop(loop):
    """Set the main event loop for use by sync functions"""
    global _main_loop
    _main_loop = loop
    logger.info(f"Main event loop set: {loop}")
    
    # Start background task to process progress queue
    asyncio.run_coroutine_threadsafe(_process_progress_queue(), loop)
    logger.info("Progress queue processor started")


async def _process_progress_queue():
    """Background task that continuously processes the progress queue"""
    global _progress_queue
    
    logger.info("🚀 Progress queue processor is running...")
    
    while True:
        try:
            # Check queue with small timeout
            try:
                item = _progress_queue.get_nowait()
                printer_id = item['printer_id']
                progress = item['progress']
                
                logger.info(f"📤 Processing queued progress: {progress.get('percent', 0)}%")
                
                # Actually broadcast the message
                await broadcast_upload_progress(printer_id, progress)
                logger.info(f"✅ Broadcast completed: {progress.get('percent', 0)}%")
                
            except queue.Empty:
                pass
            
            # Small sleep to prevent busy loop
            await asyncio.sleep(0.01)  # Reduced from 0.05 to 0.01 for faster processing
            
        except Exception as e:
            logger.error(f"Error in progress queue processor: {e}")
            await asyncio.sleep(0.1)


def broadcast_upload_progress_sync(printer_id: str, progress: dict):
    """
    Synchronous wrapper to broadcast upload progress
    Puts progress update in queue for async processing
    """
    global _progress_queue
    
    logger.info(f"🔄 broadcast_upload_progress_sync called: {progress.get('percent', 0)}% (status={progress.get('status', 'unknown')})")
    
    try:
        # Put in queue for background processing
        _progress_queue.put({
            'printer_id': printer_id,
            'progress': progress
        })
        logger.debug(f"📥 Progress queued: {progress.get('percent', 0)}%")
    except Exception as e:
        logger.error(f"Error in broadcast_upload_progress_sync: {e}")
