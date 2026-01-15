"""
Bambu Lab MQTT Integration Service
Handles real-time communication with Bambu Lab A1 via MQTT
Supports both Cloud mode and LAN mode
Follows naming conventions from README.md

Enhanced with:
- Proper sequence_id tracking (like FDM Monster)
- Connection state management (SOCKET_STATE, API_STATE)
- Auto-reconnection logic
- subtask_name for print tracking
"""
import json
import logging
import time
import threading
import ssl
from typing import Callable, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass
import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


# ============================================================================
# Database Sync Helper (sync MQTT status to database)
# ============================================================================

def _sync_mqtt_status_to_db(printer_id: str, mqtt_connected: bool, status: str = None):
    """
    Sync MQTT connection status to database.
    Called when connection state changes.
    This ensures frontend always shows correct connection status.
    """
    try:
        from src.database import SessionLocal
        from src.database.db import Printer
        
        db = SessionLocal()
        try:
            printer = db.query(Printer).filter(Printer.printer_id == printer_id).first()
            if printer:
                printer.mqtt_connected = mqtt_connected
                if status:
                    printer.status = status
                elif not mqtt_connected:
                    printer.status = "offline"
                db.commit()
                logger.info(f"📊 Synced to DB: printer={printer_id}, mqtt_connected={mqtt_connected}, status={printer.status}")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Failed to sync MQTT status to DB: {e}")


def _sync_printer_status_to_db(
    printer_id: str,
    status: str = None,
    progress: int = None,
    nozzle_temp: float = None,
    nozzle_target: float = None,
    bed_temp: float = None,
    bed_target: float = None,
    chamber_temp: float = None,
    remaining_time: int = None,
):
    """
    Sync full printer status to database.
    Called when printer sends status updates via MQTT.
    This ensures all printer data is available to frontend.
    """
    try:
        from src.database import SessionLocal
        from src.database.db import Printer
        
        db = SessionLocal()
        try:
            printer = db.query(Printer).filter(Printer.printer_id == printer_id).first()
            if printer:
                # Update status if provided
                if status is not None:
                    printer.status = status
                
                # Update progress if provided
                if progress is not None:
                    printer.print_progress = progress
                
                # Update temperatures if provided (store as JSON or separate fields)
                # For now, we'll update what columns exist
                if hasattr(printer, 'nozzle_temp') and nozzle_temp is not None:
                    printer.nozzle_temp = nozzle_temp
                if hasattr(printer, 'nozzle_target_temp') and nozzle_target is not None:
                    printer.nozzle_target_temp = nozzle_target
                if hasattr(printer, 'bed_temp') and bed_temp is not None:
                    printer.bed_temp = bed_temp
                if hasattr(printer, 'bed_target_temp') and bed_target is not None:
                    printer.bed_target_temp = bed_target
                if hasattr(printer, 'chamber_temp') and chamber_temp is not None:
                    printer.chamber_temp = chamber_temp
                if hasattr(printer, 'remaining_time') and remaining_time is not None:
                    printer.remaining_time = remaining_time
                
                db.commit()
                logger.debug(f"📊 Synced printer status: {printer_id}, status={status}, progress={progress}%")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Failed to sync printer status to DB: {e}")


# ============================================================================
# Connection State Management (like FDM Monster)
# ============================================================================

class SocketState(Enum):
    """Socket connection states"""
    UNOPENED = "unopened"
    OPENING = "opening"
    OPENED = "opened"
    AUTHENTICATED = "authenticated"
    CLOSED = "closed"
    ERROR = "error"
    ABORTED = "aborted"


class ApiState(Enum):
    """API/printer response states"""
    UNSET = "unset"
    RESPONDING = "responding"
    NO_RESPONSE = "no_response"
    ERROR = "error"


@dataclass
class ConnectionState:
    """Tracks the current connection state"""
    socket_state: SocketState = SocketState.UNOPENED
    api_state: ApiState = ApiState.UNSET
    last_message_timestamp: Optional[float] = None
    reconnect_attempts: int = 0
    max_reconnect_attempts: int = 5
    reconnect_delay: float = 5.0  # seconds


class SequenceIdGenerator:
    """
    Generate unique sequence IDs for MQTT commands
    Like FDM Monster, uses timestamp-based IDs
    """
    _counter: int = 0
    _lock = threading.Lock()
    
    @classmethod
    def generate(cls) -> str:
        """Generate a unique sequence ID based on timestamp + counter"""
        with cls._lock:
            cls._counter += 1
            # Format: timestamp_counter for uniqueness
            return f"{int(time.time() * 1000)}_{cls._counter}"
    
    @classmethod
    def reset(cls):
        """Reset counter (useful for testing)"""
        with cls._lock:
            cls._counter = 0


class BambuLabMQTTClient:
    """
    MQTT client for Bambu Lab printer communication
    
    Enhanced with:
    - Connection state management (SOCKET_STATE, API_STATE)
    - Auto-reconnection with exponential backoff
    - Sequence ID tracking for all commands
    - subtask_name for print job tracking
    """

    # MQTT Topic templates for Bambu Lab A1
    TOPIC_STATUS = "device/{printer_id}/report"  # Status updates from printer
    TOPIC_COMMAND = "device/{printer_id}/request"  # Commands to printer
    TOPIC_PUSH = "device/{printer_id}/push"  # Push notifications
    
    # Default reconnection settings
    DEFAULT_MAX_RECONNECT_ATTEMPTS = 10
    DEFAULT_RECONNECT_DELAY = 5.0
    DEFAULT_RECONNECT_DELAY_MAX = 60.0

    def __init__(
        self,
        printer_id: str,
        printer_ip: str = None,
        access_code: str = None,
        mqtt_broker: str = "mqtt.bambulab.com",
        mqtt_port: int = 8883,
        bambu_username: str = None,
        bambu_password: str = None,
        use_lan_mode: bool = True,
        auto_reconnect: bool = True,
        max_reconnect_attempts: int = None,
    ):
        """
        Initialize MQTT connection to Bambu Lab
        
        LAN Mode (recommended):
            printer_ip: Printer's IP address (e.g., 192.168.4.101)
            access_code: Access code from printer settings
            printer_id: Printer serial number
            
        Cloud Mode:
            mqtt_broker: mqtt.bambulab.com
            bambu_username: Bambu Lab account email
            bambu_password: Bambu Lab password
            printer_id: Printer serial number
            
        Reconnection:
            auto_reconnect: Enable automatic reconnection (default True)
            max_reconnect_attempts: Max reconnection attempts (default 10)
        """
        self.printer_id = printer_id
        self.printer_ip = printer_ip
        self.access_code = access_code
        self.use_lan_mode = use_lan_mode and printer_ip
        
        # Reconnection settings
        self.auto_reconnect = auto_reconnect
        self.max_reconnect_attempts = max_reconnect_attempts or self.DEFAULT_MAX_RECONNECT_ATTEMPTS
        self._reconnect_thread: Optional[threading.Thread] = None
        self._stop_reconnect = threading.Event()
        
        # Connection state management (like FDM Monster)
        self.connection_state = ConnectionState(
            max_reconnect_attempts=self.max_reconnect_attempts
        )
        
        # Choose broker based on mode
        if self.use_lan_mode:
            self.mqtt_broker = printer_ip
            self.mqtt_port = 8883
            logger.info(f"Using LAN mode: connecting directly to {printer_ip}")
        else:
            self.mqtt_broker = mqtt_broker
            self.mqtt_port = mqtt_port
            logger.info(f"Using Cloud mode: connecting to {mqtt_broker}")
        
        # Generate unique Client ID to prevent "flapping" (connect-disconnect loop)
        # IMPORTANT: Each MQTT client MUST have a unique ID
        # If two clients have the same ID, broker will kick one out repeatedly
        import random
        unique_suffix = f"{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
        client_id = f"PrintFarm_{printer_id[-6:]}_{unique_suffix}"
        logger.info(f"🔑 MQTT Client ID: {client_id}")
        
        # MQTT client instance - use VERSION2 for newer paho-mqtt
        try:
            self.client = mqtt.Client(
                client_id=client_id,
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2
            )
        except TypeError:
            # Fallback for older paho-mqtt
            self.client = mqtt.Client(client_id=client_id)
        
        # Set credentials based on mode
        if self.use_lan_mode:
            # LAN mode uses "bblp" as username and access_code as password
            self.client.username_pw_set("bblp", access_code or "")
        else:
            # Cloud mode uses Bambu Lab account credentials
            self.client.username_pw_set(bambu_username, bambu_password)
        
        # TLS settings - disable certificate verification for LAN mode
        if self.use_lan_mode:
            self.client.tls_set(cert_reqs=ssl.CERT_NONE)
            self.client.tls_insecure_set(True)
        else:
            self.client.tls_set()
        
        # Connection state (legacy - kept for backward compatibility)
        self.mqtt_connected = False
        self.printer_status = "offline"
        self.current_print_progress = 0
        self.last_status = {}
        
        # Current print tracking
        self.current_subtask_name: Optional[str] = None
        self.current_task_id: Optional[str] = None
        
        # Layer tracking
        self.current_layer: int = 0
        self.total_layers: int = 0
        
        # Time tracking
        self.remaining_time: int = 0  # mc_remaining_time in seconds
        
        # Temperature data
        self.nozzle_temp = 0.0
        self.nozzle_target_temp = 0.0
        self.bed_temp = 0.0
        self.bed_target_temp = 0.0
        self.chamber_temp = 0.0
        
        # AMS (Automatic Material System) data
        # For A1 with AMS Lite: 4 slots (0-3)
        # tray_now: current active tray (255=none, 254=external spool)
        # Each tray has: id, tray_type, tray_color, remain, nozzle_temp_min/max
        self.ams_data = {
            "ams": [],  # List of AMS units (usually 1 for A1)
            "tray_now": 255,  # Currently selected tray
            "tray_tar": 255,  # Target tray
            "tray_pre": 255,  # Previous tray
            "ams_exist_bits": "0",  # Bitmask of which AMS slots exist
            "tray_exist_bits": "0",  # Bitmask of which trays have filament
            "version": 0,
        }
        self.external_spool = {}  # External spool (vt_tray) data
        
        # AMS Loading/Unloading state tracking (for real-time UI updates)
        # Based on FDM Monster mqtt-message.types.ts fields:
        # - hw_switch_state: Hardware switch state (0=idle, 1=loading, 2=unloading)
        # - mc_print_sub_stage: Sub-stage for detailed progress
        # - ams_status: AMS overall status
        self.ams_loading_state = {
            "active": False,           # Is load/unload in progress
            "is_unload": False,        # True if unloading, False if loading
            "target_slot": 255,        # Target slot for loading
            "current_step": 0,         # Current step (0-5 for load, 0-3 for unload)
            "step_name": "",           # Step description
            "nozzle_temp": 0.0,        # Current nozzle temp
            "target_temp": 220.0,      # Target nozzle temp
            "completed": False,        # Is operation complete
            "hw_switch_state": 0,      # Raw hw_switch_state from printer
            "mc_print_sub_stage": 0,   # Raw mc_print_sub_stage from printer
            "ams_status": 0,           # Raw ams_status from printer
        }
        
        # Heartbeat settings (like FDM Monster's keepalive)
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._stop_heartbeat = threading.Event()
        self.HEARTBEAT_INTERVAL = 30.0  # Request status every 30 seconds
        
        # Callbacks
        self.on_status_update: Optional[Callable] = None
        self.on_print_complete: Optional[Callable] = None
        self.on_print_stopped: Optional[Callable] = None  # Called when print is stopped/failed from printer
        self.on_error: Optional[Callable] = None
        self.on_connection_state_change: Optional[Callable] = None
        
        # Set MQTT callbacks
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        logger.info(f"Initialized BambuLabMQTTClient: printer_id={printer_id}, mode={'LAN' if self.use_lan_mode else 'Cloud'}, auto_reconnect={auto_reconnect}")

    def _update_socket_state(self, state: SocketState):
        """Update socket state and emit event"""
        old_state = self.connection_state.socket_state
        self.connection_state.socket_state = state
        
        if old_state != state:
            logger.info(f"🔌 Socket state changed: {old_state.value} → {state.value}")
            if self.on_connection_state_change:
                self.on_connection_state_change({
                    "type": "socket_state",
                    "old_state": old_state.value,
                    "new_state": state.value,
                })
    
    def _update_api_state(self, state: ApiState):
        """Update API state and emit event"""
        old_state = self.connection_state.api_state
        self.connection_state.api_state = state
        
        if old_state != state:
            logger.info(f"📡 API state changed: {old_state.value} → {state.value}")
            if self.on_connection_state_change:
                self.on_connection_state_change({
                    "type": "api_state",
                    "old_state": old_state.value,
                    "new_state": state.value,
                })
    
    def _generate_sequence_id(self) -> str:
        """Generate a unique sequence ID for MQTT commands"""
        return SequenceIdGenerator.generate()

    def connect(self) -> bool:
        """
        Connect to Bambu Lab MQTT broker
        
        Returns: True if connection successful
        """
        try:
            self._update_socket_state(SocketState.OPENING)
            self._stop_reconnect.clear()
            
            logger.info(f"Connecting to mqtt_broker={self.mqtt_broker}:{self.mqtt_port}")
            self.client.connect(self.mqtt_broker, self.mqtt_port, keepalive=60)
            self.client.loop_start()
            
            # Wait for connection to establish (max 10 seconds for LAN)
            timeout = 10 if self.use_lan_mode else 5
            start_time = time.time()
            while not self.mqtt_connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if self.mqtt_connected:
                self._update_socket_state(SocketState.AUTHENTICATED)
                self._update_api_state(ApiState.RESPONDING)
                self.connection_state.reconnect_attempts = 0  # Reset on success
                logger.info(f"Successfully connected to Bambu Lab MQTT ({'LAN' if self.use_lan_mode else 'Cloud'} mode)")
                return True
            else:
                self._update_socket_state(SocketState.ERROR)
                logger.error("Failed to connect to Bambu Lab MQTT (timeout)")
                return False
                
        except Exception as e:
            self._update_socket_state(SocketState.ERROR)
            logger.error(f"Error connecting to mqtt_broker: {str(e)}")
            if self.on_error:
                self.on_error(f"MQTT Connection Error: {str(e)}")
            return False

    def disconnect(self) -> bool:
        """Disconnect from MQTT broker"""
        try:
            # Stop any reconnection attempts
            self._stop_reconnect.set()
            if self._reconnect_thread and self._reconnect_thread.is_alive():
                self._reconnect_thread.join(timeout=2)
            
            self.client.loop_stop()
            self.client.disconnect()
            self.mqtt_connected = False
            self._update_socket_state(SocketState.CLOSED)
            logger.info("Disconnected from Bambu Lab MQTT")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting: {str(e)}")
            return False

    def _start_reconnect_thread(self):
        """Start background thread for reconnection attempts"""
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            return  # Already reconnecting
        
        self._reconnect_thread = threading.Thread(target=self._reconnect_loop, daemon=True)
        self._reconnect_thread.start()
    
    def _reconnect_loop(self):
        """Background reconnection loop with exponential backoff"""
        while not self._stop_reconnect.is_set():
            if self.connection_state.reconnect_attempts >= self.max_reconnect_attempts:
                logger.error(f"❌ Max reconnection attempts ({self.max_reconnect_attempts}) reached. Giving up.")
                self._update_socket_state(SocketState.ABORTED)
                return
            
            self.connection_state.reconnect_attempts += 1
            
            # Exponential backoff: 5s, 10s, 20s, 40s... max 60s
            delay = min(
                self.DEFAULT_RECONNECT_DELAY * (2 ** (self.connection_state.reconnect_attempts - 1)),
                self.DEFAULT_RECONNECT_DELAY_MAX
            )
            
            logger.info(f"🔄 Reconnection attempt {self.connection_state.reconnect_attempts}/{self.max_reconnect_attempts} in {delay:.1f}s...")
            
            # Wait with ability to be interrupted
            if self._stop_reconnect.wait(delay):
                return  # Stop signal received
            
            # Try to reconnect
            try:
                self._update_socket_state(SocketState.OPENING)
                self.client.reconnect()
                
                # Wait for connection
                start_time = time.time()
                while not self.mqtt_connected and (time.time() - start_time) < 10:
                    if self._stop_reconnect.is_set():
                        return
                    time.sleep(0.1)
                
                if self.mqtt_connected:
                    logger.info(f"✅ Reconnected successfully after {self.connection_state.reconnect_attempts} attempts")
                    self.connection_state.reconnect_attempts = 0
                    return
                    
            except Exception as e:
                logger.warning(f"Reconnection attempt failed: {e}")
                self._update_socket_state(SocketState.ERROR)

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        """Callback when MQTT client connects"""
        # Handle both old (rc as int) and new (reason_code object) paho-mqtt API
        rc = reason_code if isinstance(reason_code, int) else reason_code.value if hasattr(reason_code, 'value') else 0
        
        if rc == 0:
            self.mqtt_connected = True
            self._update_socket_state(SocketState.AUTHENTICATED)
            self._update_api_state(ApiState.RESPONDING)
            logger.info(f"MQTT connected successfully (mode={'LAN' if self.use_lan_mode else 'Cloud'})")
            
            # Sync to database
            _sync_mqtt_status_to_db(self.printer_id, True)
            
            # Subscribe to printer status topic
            status_topic = self.TOPIC_STATUS.format(printer_id=self.printer_id)
            self.client.subscribe(status_topic, qos=0)
            logger.info(f"Subscribed to topic: {status_topic}")
            
            # Request initial status push
            self._request_status_push()
            
            # Start heartbeat thread for keepalive
            self._start_heartbeat_thread()
        else:
            logger.error(f"MQTT connection failed with rc={rc}")
            self.mqtt_connected = False
            self._update_socket_state(SocketState.ERROR)
            _sync_mqtt_status_to_db(self.printer_id, False)

    def _request_status_push(self):
        """Request printer to send status update"""
        try:
            command_topic = self.TOPIC_COMMAND.format(printer_id=self.printer_id)
            push_request = {
                "pushing": {
                    "sequence_id": self._generate_sequence_id(),
                    "command": "pushall"
                }
            }
            self.client.publish(command_topic, json.dumps(push_request))
            logger.debug("Requested status push from printer")
        except Exception as e:
            logger.warning(f"Failed to request status push: {e}")

    def _start_heartbeat_thread(self):
        """
        Start heartbeat thread to keep connection alive.
        Like FDM Monster, periodically requests status to:
        1. Keep MQTT connection alive
        2. Detect stale connections (no response = reconnect)
        3. Update printer status in database
        """
        # Stop existing heartbeat if any
        self._stop_heartbeat.set()
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=1)
        
        self._stop_heartbeat.clear()
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
        logger.info(f"💓 Heartbeat thread started (interval: {self.HEARTBEAT_INTERVAL}s)")
    
    def _heartbeat_loop(self):
        """
        Heartbeat loop - requests status periodically.
        If no response received within timeout, connection is considered stale.
        """
        stale_timeout = 60.0  # Consider connection stale if no message for 60s
        
        while not self._stop_heartbeat.is_set():
            # Wait for heartbeat interval
            if self._stop_heartbeat.wait(self.HEARTBEAT_INTERVAL):
                return  # Stop signal received
            
            if not self.mqtt_connected:
                continue
            
            # Check if connection is stale (no messages received recently)
            if self.connection_state.last_message_timestamp:
                time_since_last = time.time() - self.connection_state.last_message_timestamp
                if time_since_last > stale_timeout:
                    logger.warning(f"⚠️ Connection stale: no messages for {time_since_last:.0f}s, triggering reconnect")
                    self._update_api_state(ApiState.NO_RESPONSE)
                    # Force disconnect to trigger reconnection
                    try:
                        self.client.disconnect()
                    except:
                        pass
                    continue
            
            # Request status push as heartbeat
            try:
                self._request_status_push()
                logger.debug(f"💓 Heartbeat: requested status push")
            except Exception as e:
                logger.warning(f"Heartbeat failed: {e}")

    def _on_message(self, client, userdata, msg):
        """Callback when MQTT message received"""
        try:
            # Update last message timestamp for connection health tracking
            self.connection_state.last_message_timestamp = time.time()
            self._update_api_state(ApiState.RESPONDING)
            
            payload = json.loads(msg.payload.decode())
            self._process_printer_status(payload)
        except json.JSONDecodeError:
            logger.warning(f"Failed to decode MQTT message: {msg.payload[:100]}")
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")

    def _on_disconnect(self, client, userdata, *args):
        """Callback when MQTT client disconnects"""
        self.mqtt_connected = False
        self._update_socket_state(SocketState.CLOSED)
        self._update_api_state(ApiState.NO_RESPONSE)
        logger.warning(f"MQTT disconnected")
        
        # Sync to database
        _sync_mqtt_status_to_db(self.printer_id, False)
        
        # Stop heartbeat
        self._stop_heartbeat.set()
        
        # Start auto-reconnection if enabled
        if self.auto_reconnect and not self._stop_reconnect.is_set():
            logger.info("🔄 Auto-reconnection enabled, starting reconnection thread...")
            self._start_reconnect_thread()

    def _process_printer_status(self, status_payload: Dict[str, Any]):
        """
        Process printer status update from MQTT
        
        Updates:
        - printer_status (idle, printing, offline)
        - current_print_progress (0-100%)
        - Temperature data (nozzle, bed, chamber)
        - Print completion detection
        - Syncs all data to database for frontend access
        """
        try:
            mc_remaining_time = 0
            status_changed = False
            
            # Check if this is a "print" message (contains temperature and status)
            print_data = status_payload.get("print", {})
            if print_data:
                # Extract temperature data from nested "print" object
                # Bambu printers send: nozzle_temper, nozzle_target_temper, bed_temper, bed_target_temper, chamber_temper
                # IMPORTANT: Only update if field exists - printer sends nozzle and bed in separate messages!
                if "nozzle_temper" in print_data:
                    self.nozzle_temp = float(print_data.get("nozzle_temper") or 0)
                if "nozzle_target_temper" in print_data:
                    self.nozzle_target_temp = float(print_data.get("nozzle_target_temper") or 0)
                if "bed_temper" in print_data:
                    self.bed_temp = float(print_data.get("bed_temper") or 0)
                if "bed_target_temper" in print_data:
                    self.bed_target_temp = float(print_data.get("bed_target_temper") or 0)
                if "chamber_temper" in print_data:
                    self.chamber_temp = float(print_data.get("chamber_temper") or 0)
                
                # ============================================================
                # AMS (Automatic Material System) data parsing
                # Based on pybambu and FDM Monster implementations
                # ============================================================
                ams_data = print_data.get("ams", {})
                if ams_data:
                    self._process_ams_data(ams_data)
                
                # External spool (vt_tray) - used when not using AMS
                vt_tray = print_data.get("vt_tray", {})
                if vt_tray:
                    self.external_spool = self._parse_tray_data(vt_tray)
                
                # ============================================================
                # AMS Loading/Unloading state tracking (for real-time UI)
                # Based on FDM Monster mqtt-message.types.ts
                # Key fields: hw_switch_state, mc_print_sub_stage, ams_status
                # ============================================================
                
                self._update_ams_loading_state(print_data)
                
                # Extract print status from nested object
                gcode_state = print_data.get("gcode_state", "")
                mc_remaining_time = print_data.get("mc_remaining_time", 0)
                mc_percent = print_data.get("mc_percent", 0)
                
                # Extract layer information
                # Bambu Lab sends: layer_num (current), total_layer_num (total)
                if "layer_num" in print_data:
                    self.current_layer = int(print_data.get("layer_num", 0))
                if "total_layer_num" in print_data:
                    self.total_layers = int(print_data.get("total_layer_num", 0))
                
                # Store remaining time (mc_remaining_time is in MINUTES from printer)
                if mc_remaining_time:
                    self.remaining_time = int(mc_remaining_time) * 60  # Convert to seconds
                
                # Extract current file name (gcode_file or subtask_name)
                if "gcode_file" in print_data:
                    self.current_subtask_name = print_data.get("gcode_file", "")
                elif "subtask_name" in print_data:
                    self.current_subtask_name = print_data.get("subtask_name", "")
                
                # Determine printer_status based on gcode_state
                old_status = self.printer_status
                if gcode_state in ["RUNNING", "PREPARE"]:
                    self.printer_status = "printing"
                    self.current_print_progress = mc_percent
                    status_changed = (old_status != "printing")
                elif gcode_state in ["IDLE", "FINISH", "FAILED"]:
                    self.printer_status = "idle"
                    if gcode_state != "FINISH":
                        self.current_print_progress = 0
                    status_changed = (old_status != "idle")
                elif gcode_state == "PAUSE":
                    self.printer_status = "paused"
                    status_changed = (old_status != "paused")
                else:
                    # Keep previous status if unknown
                    pass
            else:
                # Legacy format - direct fields
                print_status = status_payload.get("print_status", "")
                mc_remaining_time = status_payload.get("mc_remaining_time", 0)
                
                old_status = self.printer_status
                if print_status == "PRINTING":
                    self.printer_status = "printing"
                    self.current_print_progress = status_payload.get("print_progress", 0)
                elif print_status in ["IDLE", "RUNNING"]:
                    self.printer_status = "idle"
                    self.current_print_progress = 0
                elif print_status == "FAILED":
                    self.printer_status = "idle"
                else:
                    self.printer_status = "idle"
                status_changed = (old_status != self.printer_status)
            
            # Store last status for debugging
            self.last_status = status_payload
            
            # Sync all status to database (for frontend access)
            _sync_printer_status_to_db(
                printer_id=self.printer_id,
                status=self.printer_status,
                progress=self.current_print_progress,
                nozzle_temp=self.nozzle_temp,
                nozzle_target=self.nozzle_target_temp,
                bed_temp=self.bed_temp,
                bed_target=self.bed_target_temp,
                chamber_temp=self.chamber_temp,
                remaining_time=mc_remaining_time,
            )
            
            # Callback for status updates
            if self.on_status_update:
                self.on_status_update({
                    "printer_status": self.printer_status,
                    "current_print_progress": self.current_print_progress,
                    "nozzle_temp": self.nozzle_temp,
                    "nozzle_target_temp": self.nozzle_target_temp,
                    "bed_temp": self.bed_temp,
                    "bed_target_temp": self.bed_target_temp,
                    "chamber_temp": self.chamber_temp,
                    "mc_remaining_time": mc_remaining_time,
                })
            
            # Detect print completion
            if self.printer_status == "idle" and self.current_print_progress == 100:
                logger.info("Print job completed!")
                if self.on_print_complete:
                    self.on_print_complete()
            
            # Detect print stopped/failed from printer (status changed to idle but not completed)
            if status_changed and self.printer_status == "idle" and old_status in ["printing", "paused"] and self.current_print_progress < 100:
                logger.info(f"Print job stopped/failed from printer! Progress was {self.current_print_progress}%")
                if self.on_print_stopped:
                    self.on_print_stopped()
                    
        except Exception as e:
            logger.error(f"Error processing printer_status: {str(e)}")

    def _process_ams_data(self, ams_data: Dict[str, Any]):
        """
        Process AMS (Automatic Material System) data from MQTT message.
        
        Based on pybambu AMSList.print_update() implementation.
        
        AMS json payload format:
        {
            "ams": [
                {
                    "id": "0",
                    "humidity": "4",
                    "temp": "0.0",
                    "tray": [
                        {
                            "id": "0",
                            "remain": 80,
                            "tray_info_idx": "GFL99",
                            "tray_type": "PLA",
                            "tray_sub_brands": "",
                            "tray_color": "FFFF00FF",  # RRGGBBAA
                            "nozzle_temp_max": "240",
                            "nozzle_temp_min": "190",
                            ...
                        },
                        ...
                    ]
                }
            ],
            "ams_exist_bits": "1",
            "tray_exist_bits": "f",
            "tray_now": "255",
            "tray_tar": "255",
            "version": 3
        }
        """
        try:
            # Update AMS metadata
            self.ams_data["tray_now"] = int(ams_data.get("tray_now", 255))
            self.ams_data["tray_tar"] = int(ams_data.get("tray_tar", 255))
            self.ams_data["tray_pre"] = int(ams_data.get("tray_pre", 255))
            self.ams_data["ams_exist_bits"] = ams_data.get("ams_exist_bits", "0")
            self.ams_data["tray_exist_bits"] = ams_data.get("tray_exist_bits", "0")
            self.ams_data["version"] = ams_data.get("version", 0)
            
            # Process AMS units and their trays
            ams_list = ams_data.get("ams", [])
            parsed_ams_list = []
            
            for ams_unit in ams_list:
                ams_id = int(ams_unit.get("id", 0))
                ams_info = {
                    "id": ams_id,
                    "humidity": int(ams_unit.get("humidity", 0)),
                    "temp": float(ams_unit.get("temp", 0.0)),
                    "trays": []
                }
                
                # Process each tray (slot) in this AMS unit
                tray_list = ams_unit.get("tray", [])
                for tray in tray_list:
                    tray_info = self._parse_tray_data(tray)
                    ams_info["trays"].append(tray_info)
                
                parsed_ams_list.append(ams_info)
            
            self.ams_data["ams"] = parsed_ams_list
            
            # Log AMS status for debugging
            if parsed_ams_list:
                filled_trays = sum(
                    1 for ams in parsed_ams_list 
                    for tray in ams.get("trays", []) 
                    if not tray.get("empty", True)
                )
                logger.debug(f"🎨 AMS update: {len(parsed_ams_list)} unit(s), {filled_trays} filled tray(s), tray_now={self.ams_data['tray_now']}")
                
        except Exception as e:
            logger.warning(f"Error processing AMS data: {e}")

    def _parse_tray_data(self, tray_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse individual tray (filament slot) data.
        
        Based on pybambu AMSTray.print_update() implementation.
        
        Returns dict with tray info:
        {
            "id": 0,
            "empty": False,
            "type": "PLA",
            "color": "FFFF00FF",  # RRGGBBAA
            "name": "Bambu PLA Basic",
            "remain": 80,
            "nozzle_temp_min": 190,
            "nozzle_temp_max": 240,
            "tag_uid": "...",
            "k": 0.02
        }
        """
        tray_id = int(tray_data.get("id", 0))
        
        # If only "id" field exists, tray is empty
        if len(tray_data) <= 1:
            return {
                "id": tray_id,
                "empty": True,
                "type": "Empty",
                "color": "00000000",
                "name": "Empty",
                "remain": 0,
                "nozzle_temp_min": 0,
                "nozzle_temp_max": 0,
            }
        
        # Parse filament info
        tray_type = tray_data.get("tray_type", "Unknown")
        tray_color = tray_data.get("tray_color", "00000000")
        tray_info_idx = tray_data.get("tray_info_idx", "")
        
        # Get human-readable name from filament index
        filament_name = self._get_filament_name(tray_info_idx) or tray_type
        
        return {
            "id": tray_id,
            "empty": False,
            "type": tray_type,
            "color": tray_color,
            "name": filament_name,
            "sub_brands": tray_data.get("tray_sub_brands", ""),
            "remain": tray_data.get("remain", 0),
            "nozzle_temp_min": int(tray_data.get("nozzle_temp_min", 0)),
            "nozzle_temp_max": int(tray_data.get("nozzle_temp_max", 0)),
            "tag_uid": tray_data.get("tag_uid", ""),
            "k": tray_data.get("k", 0),
        }

    def _get_filament_name(self, idx: str) -> str:
        """
        Convert Bambu filament index to human-readable name.
        Based on pybambu const.py FILAMENT_NAMES.
        """
        FILAMENT_NAMES = {
            "GFA00": "Bambu PLA Basic",
            "GFA01": "Bambu PLA Matte",
            "GFA02": "Bambu PLA Metal",
            "GFA03": "Bambu PLA Impact",
            "GFA05": "Bambu PLA Silk",
            "GFA07": "Bambu PLA Marble",
            "GFA08": "Bambu PLA Sparkle",
            "GFA09": "Bambu PLA Tough",
            "GFA11": "Bambu PLA Aero",
            "GFA50": "Bambu PLA-CF",
            "GFB00": "Bambu ABS",
            "GFB01": "Bambu ASA",
            "GFC00": "Bambu PC",
            "GFG00": "Bambu PETG Basic",
            "GFG50": "Bambu PETG-CF",
            "GFN03": "Bambu PA-CF",
            "GFN04": "Bambu PAHT-CF",
            "GFN05": "Bambu PA6-CF",
            "GFS00": "Bambu Support W",
            "GFS01": "Bambu Support G",
            "GFS02": "Bambu Support For PLA",
            "GFS03": "Bambu Support For PA/PET",
            "GFT01": "Bambu PET-CF",
            "GFU01": "Bambu TPU 95A",
            "GFU00": "Bambu TPU 95A HF",
            "GFL99": "Generic PLA",
            "GFB99": "Generic ABS",
            "GFB98": "Generic ASA",
            "GFG99": "Generic PETG",
            "GFN98": "Generic PA-CF",
            "GFN99": "Generic PA",
        }
        return FILAMENT_NAMES.get(idx, idx if idx else "Unknown")

    def _update_ams_loading_state(self, print_data: Dict[str, Any]):
        """
        Update AMS loading/unloading state from MQTT print data.
        
        Based on real MQTT data captured from Bambu Lab A1 Combo:
        
        ams_status values observed during loading:
        - 768: IDLE (no operation)
        - 258: Heating/Preparing
        - 264: Check filament location
        - 259: Cut filament
        - 260: Pull back current filament
        - 261: Push new filament into extruder
        - 262: Feeding filament
        - 263: Purging old filament
        
        Detection logic:
        - Loading active: ams_status != 768 AND tray_tar != 255 AND tray_tar != tray_now
        - Complete: ams_status == 768 AND tray_now == tray_tar
        """
        try:
            # Extract relevant fields
            ams_status = print_data.get("ams_status")
            mc_print_sub_stage = print_data.get("mc_print_sub_stage", 0)
            
            # Get AMS tray info
            ams_data = print_data.get("ams", {})
            if ams_data:
                if "tray_now" in ams_data:
                    try:
                        self.ams_data["tray_now"] = int(ams_data["tray_now"])
                    except (ValueError, TypeError):
                        pass
                if "tray_tar" in ams_data:
                    try:
                        self.ams_data["tray_tar"] = int(ams_data["tray_tar"])
                    except (ValueError, TypeError):
                        pass
            
            tray_now = self.ams_data.get("tray_now", 255)
            tray_tar = self.ams_data.get("tray_tar", 255)
            
            # Get current nozzle temperature
            nozzle_temp = self.nozzle_temp
            target_temp = self.nozzle_target_temp or 220.0
            
            # Store raw values for API access
            if ams_status is not None:
                self.ams_loading_state["ams_status"] = ams_status
            self.ams_loading_state["mc_print_sub_stage"] = mc_print_sub_stage
            self.ams_loading_state["nozzle_temp"] = nozzle_temp
            self.ams_loading_state["target_temp"] = target_temp
            self.ams_loading_state["tray_now"] = tray_now
            self.ams_loading_state["tray_tar"] = tray_tar
            
            # Get current ams_status (use stored if not in this message)
            current_ams_status = ams_status if ams_status is not None else self.ams_loading_state.get("ams_status", 768)
            
            # Map ams_status to step info
            # Based on real captured data from printer
            AMS_STATUS_MAP = {
                768: {"step": -1, "name": "Idle", "loading": False},
                258: {"step": 0, "name": "Heat the Nozzle", "loading": True},
                264: {"step": 1, "name": "Check filament location", "loading": True},
                259: {"step": 2, "name": "Cut filament", "loading": True},
                260: {"step": 3, "name": "Pull back current filament", "loading": True},
                261: {"step": 4, "name": "Push new filament into the extruder", "loading": True},
                262: {"step": 4, "name": "Push new filament into the extruder", "loading": True},
                263: {"step": 5, "name": "Purge old filament", "loading": True},
            }
            
            status_info = AMS_STATUS_MAP.get(current_ams_status, {"step": 0, "name": "Loading...", "loading": current_ams_status != 768})
            
            # Determine if loading is active
            is_loading = status_info["loading"] and tray_tar != 255
            is_unloading = status_info["loading"] and tray_tar == 255 and tray_now != 255
            
            # Override: if ams_status is 768 and tray matches, we're complete
            is_complete = False
            if current_ams_status == 768:
                if tray_now == tray_tar and tray_tar != 255:
                    is_complete = True
                is_loading = False
                is_unloading = False
            
            # Get step info
            current_step = status_info["step"]
            step_name = status_info["name"]
            
            # If still heating, override step to 0
            if is_loading and nozzle_temp < (target_temp - 10) and current_ams_status == 258:
                current_step = 0
                step_name = "Heat the Nozzle"
            
            # Update state
            self.ams_loading_state["active"] = is_loading or is_unloading
            self.ams_loading_state["is_unload"] = is_unloading
            self.ams_loading_state["current_step"] = max(0, current_step)
            self.ams_loading_state["step_name"] = step_name
            self.ams_loading_state["completed"] = is_complete
            self.ams_loading_state["target_slot"] = tray_tar
            
            # Only log when there's an actual operation in progress (not idle state)
            # Removed verbose logging to reduce console spam
            
        except Exception as e:
            print(f"❌ AMS Error: {e}")

    def get_ams_status(self) -> Dict[str, Any]:
        """
        Get current AMS status including all trays and their filament info.
        
        Returns:
            {
                "tray_now": 0,  # Currently active tray (255=none, 254=external)
                "tray_tar": 0,  # Target tray
                "trays": [
                    {
                        "slot": 0,  # Slot number (0-3 for AMS Lite)
                        "empty": False,
                        "type": "PLA",
                        "color": "FFFF00FF",
                        "name": "Bambu PLA Basic",
                        "remain": 80
                    },
                    ...
                ],
                "external_spool": {...}  # External spool if present
            }
        """
        trays = []
        
        # Flatten all trays from all AMS units
        for ams_unit in self.ams_data.get("ams", []):
            for tray in ams_unit.get("trays", []):
                slot_num = len(trays)  # Calculate slot number
                trays.append({
                    "slot": slot_num,
                    "ams_id": ams_unit.get("id", 0),
                    "tray_id": tray.get("id", 0),
                    **tray
                })
        
        return {
            "tray_now": self.ams_data.get("tray_now", 255),
            "tray_tar": self.ams_data.get("tray_tar", 255),
            "ams_exist_bits": self.ams_data.get("ams_exist_bits", "0"),
            "tray_exist_bits": self.ams_data.get("tray_exist_bits", "0"),
            "trays": trays,
            "external_spool": self.external_spool if self.external_spool else None,
        }

    def get_ams_loading_state(self) -> Dict[str, Any]:
        """
        Get current AMS loading/unloading progress state.
        
        Used by frontend to show real-time progress during load/unload operations.
        
        Returns:
            {
                "active": True/False,         # Is operation in progress
                "is_unload": True/False,      # True if unloading, False if loading
                "target_slot": 0-3 or 255,    # Target slot for loading
                "current_step": 0-5,          # Current step index
                "step_name": "Heat the Nozzle", # Human-readable step
                "nozzle_temp": 150.0,         # Current nozzle temp
                "target_temp": 220.0,         # Target nozzle temp
                "completed": True/False,      # Is operation complete
                "total_steps": 6,             # Total steps (6 for load, 4 for unload)
                "tray_now": 255,              # Current loaded tray
                "tray_tar": 0                 # Target tray
            }
        """
        is_unload = self.ams_loading_state.get("is_unload", False)
        
        return {
            "active": self.ams_loading_state.get("active", False),
            "is_unload": is_unload,
            "target_slot": self.ams_loading_state.get("target_slot", 255),
            "current_step": self.ams_loading_state.get("current_step", 0),
            "step_name": self.ams_loading_state.get("step_name", ""),
            "nozzle_temp": self.ams_loading_state.get("nozzle_temp", 0.0),
            "target_temp": self.ams_loading_state.get("target_temp", 220.0),
            "completed": self.ams_loading_state.get("completed", False),
            "total_steps": 4 if is_unload else 6,
            "tray_now": self.ams_data.get("tray_now", 255),
            "tray_tar": self.ams_data.get("tray_tar", 255),
            # Include raw values for debugging
            "hw_switch_state": self.ams_loading_state.get("hw_switch_state", 0),
            "mc_print_sub_stage": self.ams_loading_state.get("mc_print_sub_stage", 0),
            "ams_status": self.ams_loading_state.get("ams_status", 0),
        }

    # ==================== AMS FILAMENT CONTROL ====================
    
    def send_gcode_line(self, gcode: str) -> bool:
        """
        Send a single G-code command to the printer via MQTT.
        
        Args:
            gcode: The G-code command string (e.g., "M701 S0")
            
        Returns:
            True if command was sent successfully
        """
        try:
            command = {
                "print": {
                    "sequence_id": self._generate_sequence_id(),
                    "command": "gcode_line",
                    "param": gcode + "\n"
                }
            }
            command_topic = self.TOPIC_COMMAND.format(printer_id=self.printer_id)
            
            result = self.client.publish(command_topic, json.dumps(command), qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Sent G-code: {gcode}")
                return True
            else:
                logger.error(f"Failed to send G-code: rc={result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending G-code: {str(e)}")
            return False

    def ams_load_filament(self, slot: int, cool_down: bool = True) -> bool:
        """
        Load filament from a specific AMS slot.
        
        For Bambu Lab printers, this uses the ams_change_filament command
        or the T[slot] G-code for tool change.
        
        Args:
            slot: The slot number to load from (0-3 for AMS Lite, 254 for external)
            cool_down: If True, will schedule temperature reset after load completes
            
        Returns:
            True if command was sent successfully
        """
        try:
            logger.info(f"🔄 Loading filament from slot {slot}")
            
            # Method 1: Use ams_change_filament command (recommended for AMS)
            # This is similar to what Bambu Studio uses
            command = {
                "print": {
                    "sequence_id": self._generate_sequence_id(),
                    "command": "ams_change_filament",
                    "target": slot,
                    "curr_temp": 220,  # Default PLA temp, could be made configurable
                    "tar_temp": 220
                }
            }
            command_topic = self.TOPIC_COMMAND.format(printer_id=self.printer_id)
            
            result = self.client.publish(command_topic, json.dumps(command), qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"✅ Sent AMS load command for slot {slot}")
                
                # Schedule cool down after load completes
                if cool_down:
                    self._schedule_cooldown_after_ams_operation()
                
                return True
            else:
                logger.error(f"Failed to send AMS load command: rc={result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Error loading filament: {str(e)}")
            return False

    def ams_unload_filament(self, cool_down: bool = True) -> bool:
        """
        Unload the currently loaded filament.
        
        Args:
            cool_down: If True, will schedule temperature reset after unload completes
            
        Returns:
            True if command was sent successfully
        """
        try:
            logger.info("🔄 Unloading filament")
            
            # Use ams_change_filament with target 255 (none) to unload
            # Or use the unload command
            command = {
                "print": {
                    "sequence_id": self._generate_sequence_id(),
                    "command": "ams_change_filament",
                    "target": 255,  # 255 = unload
                    "curr_temp": 220,
                    "tar_temp": 220
                }
            }
            command_topic = self.TOPIC_COMMAND.format(printer_id=self.printer_id)
            
            result = self.client.publish(command_topic, json.dumps(command), qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info("✅ Sent AMS unload command")
                
                # Schedule cool down after unload completes
                if cool_down:
                    self._schedule_cooldown_after_ams_operation()
                
                return True
            else:
                logger.error(f"Failed to send AMS unload command: rc={result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Error unloading filament: {str(e)}")
            return False
    
    def _schedule_cooldown_after_ams_operation(self):
        """
        Schedule a background task to monitor AMS operation and cool down nozzle when complete.
        Uses a separate thread to avoid blocking.
        """
        import threading
        
        def monitor_and_cooldown():
            import time
            
            # Wait for AMS operation to start (give it a moment)
            time.sleep(3)
            
            # Monitor AMS status - wait until loading is complete
            max_wait = 120  # Max 2 minutes
            check_interval = 2  # Check every 2 seconds
            elapsed = 0
            
            logger.info("🌡️ Monitoring AMS operation for cooldown...")
            
            while elapsed < max_wait:
                # Check if AMS loading is still active
                loading_state = self.ams_loading_state.get("active", False)
                ams_status = self.ams_loading_state.get("ams_status", 768)
                
                # 768 = idle, operation complete
                if not loading_state and ams_status == 768:
                    logger.info("✅ AMS operation complete, cooling down nozzle...")
                    time.sleep(1)  # Small delay before sending cooldown
                    self.set_nozzle_temperature(0)
                    logger.info("🌡️ Nozzle temperature set to 0°C")
                    return
                
                time.sleep(check_interval)
                elapsed += check_interval
            
            # Timeout - still send cooldown command
            logger.warning("⚠️ AMS operation timeout, sending cooldown anyway")
            self.set_nozzle_temperature(0)
        
        # Start monitoring in background thread
        thread = threading.Thread(target=monitor_and_cooldown, daemon=True)
        thread.start()
        logger.info("🔄 Started cooldown monitor thread")
    
    def set_nozzle_temperature(self, temp: int) -> bool:
        """
        Set the nozzle temperature.
        
        Args:
            temp: Target temperature in Celsius (0 to turn off heater)
            
        Returns:
            True if command was sent successfully
        """
        try:
            gcode = f"M104 S{temp}"
            logger.info(f"🌡️ Setting nozzle temperature to {temp}°C")
            return self.send_gcode_line(gcode)
        except Exception as e:
            logger.error(f"Error setting nozzle temperature: {str(e)}")
            return False

    def ams_filament_setting(self, slot: int, tray_color: str = "", tray_type: str = "PLA") -> bool:
        """
        Update filament settings for a specific AMS slot.
        
        Args:
            slot: The slot number (0-3)
            tray_color: Filament color in RRGGBBAA hex format
            tray_type: Filament type (e.g., "PLA", "PETG", "ABS")
            
        Returns:
            True if command was sent successfully
        """
        try:
            logger.info(f"⚙️ Setting filament config for slot {slot}: {tray_type} ({tray_color})")
            
            # Calculate AMS ID and tray ID from slot number
            ams_id = slot // 4  # 0 for slots 0-3, 1 for slots 4-7, etc.
            tray_id = slot % 4
            
            command = {
                "print": {
                    "sequence_id": self._generate_sequence_id(),
                    "command": "ams_filament_setting",
                    "ams_id": ams_id,
                    "tray_id": tray_id,
                    "tray_color": tray_color,
                    "tray_type": tray_type,
                    "setting_id": ""  # Empty for custom settings
                }
            }
            command_topic = self.TOPIC_COMMAND.format(printer_id=self.printer_id)
            
            result = self.client.publish(command_topic, json.dumps(command), qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"✅ Updated filament settings for slot {slot}")
                return True
            else:
                logger.error(f"Failed to update filament settings: rc={result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Error setting filament: {str(e)}")
            return False

    # ==================== END AMS FILAMENT CONTROL ====================

    def send_gcode_to_printer(self, gcode_path: str) -> bool:
        """
        Send G-code file to printer
        
        Args:
            gcode_path: Path to .gcode file
            
        Returns: True if sent successfully
        """
        try:
            # Read G-code file
            with open(gcode_path, 'r') as f:
                gcode_content = f.read()
            
            # Prepare command payload for Bambu Lab A1
            command = {
                "print": {
                    "command": "project_file",
                    "param": gcode_path,
                }
            }
            
            # Send via MQTT
            command_topic = self.TOPIC_COMMAND.format(printer_id=self.printer_id)
            result = self.client.publish(
                command_topic,
                json.dumps(command),
                qos=1
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Sent gcode to printer: {gcode_path}")
                return True
            else:
                logger.error(f"Failed to publish command: rc={result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending gcode_to_printer: {str(e)}")
            return False

    def start_print(self) -> bool:
        """Send start print command to printer"""
        try:
            command = {
                "print": {
                    "command": "start",
                    "sequence_id": self._generate_sequence_id()
                }
            }
            command_topic = self.TOPIC_COMMAND.format(printer_id=self.printer_id)
            
            result = self.client.publish(command_topic, json.dumps(command), qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info("Sent start print command")
                return True
            else:
                logger.error(f"Failed to start print: rc={result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Error starting print: {str(e)}")
            return False

    def pause_print(self) -> bool:
        """Send pause print command to printer"""
        try:
            print(f"⏸️ [PRINT] Sending PAUSE command to printer {self.printer_id}")
            command = {
                "print": {
                    "command": "pause",
                    "sequence_id": self._generate_sequence_id()
                }
            }
            command_topic = self.TOPIC_COMMAND.format(printer_id=self.printer_id)
            
            result = self.client.publish(command_topic, json.dumps(command), qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"✅ [PRINT] Pause command sent successfully")
                logger.info("Sent pause print command")
                return True
            else:
                print(f"🔴 [PRINT] Failed to send pause command: rc={result.rc}")
                logger.error(f"Failed to pause print: rc={result.rc}")
                return False
                
        except Exception as e:
            print(f"🔴 [PRINT] Error pausing print: {str(e)}")
            logger.error(f"Error pausing print: {str(e)}")
            return False

    def resume_print(self) -> bool:
        """Send resume print command to printer"""
        try:
            print(f"▶️ [PRINT] Sending RESUME command to printer {self.printer_id}")
            command = {
                "print": {
                    "command": "resume",
                    "sequence_id": self._generate_sequence_id()
                }
            }
            command_topic = self.TOPIC_COMMAND.format(printer_id=self.printer_id)
            
            result = self.client.publish(command_topic, json.dumps(command), qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"✅ [PRINT] Resume command sent successfully")
                logger.info("Sent resume print command")
                return True
            else:
                print(f"🔴 [PRINT] Failed to send resume command: rc={result.rc}")
                logger.error(f"Failed to resume print: rc={result.rc}")
                return False
                
        except Exception as e:
            print(f"🔴 [PRINT] Error resuming print: {str(e)}")
            logger.error(f"Error resuming print: {str(e)}")
            return False

    def stop_print(self, run_end_sequence: bool = True) -> bool:
        """
        Send stop print command to printer.
        
        Args:
            run_end_sequence: If True, will run end print sequence (turn off heaters, move to safe position)
        """
        try:
            print(f"⏹️ [PRINT] Sending STOP command to printer {self.printer_id}")
            command = {
                "print": {
                    "command": "stop",
                    "sequence_id": self._generate_sequence_id()
                }
            }
            command_topic = self.TOPIC_COMMAND.format(printer_id=self.printer_id)
            
            result = self.client.publish(command_topic, json.dumps(command), qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"✅ [PRINT] Stop command sent successfully")
                logger.info("Sent stop print command")
                
                # Run end sequence after stop
                if run_end_sequence:
                    self._run_stop_end_sequence()
                
                return True
            else:
                print(f"🔴 [PRINT] Failed to send stop command: rc={result.rc}")
                logger.error(f"Failed to stop print: rc={result.rc}")
                return False
                
        except Exception as e:
            print(f"🔴 [PRINT] Error stopping print: {str(e)}")
            logger.error(f"Error stopping print: {str(e)}")
            return False
    
    def _run_stop_end_sequence(self):
        """
        Run end sequence after stopping print:
        1. Turn off heaters (from end_print_start template)
        2. Move to safe position (from move_to_safe template)
        Uses a background thread to allow printer time to process stop command first.
        Templates are loaded from database for consistency.
        """
        import threading
        import time
        
        def execute_end_sequence():
            # Wait for printer to process stop command
            time.sleep(3)
            
            logger.info("🔄 Running end sequence after stop...")
            
            # Try to load templates from database
            end_gcode = None
            safe_gcode = None
            
            try:
                from src.api.templates_db import get_template_by_key
                
                # Get end_print_start template
                end_template = get_template_by_key('end_print_start')
                if end_template and end_template.get('gcode'):
                    end_gcode = end_template['gcode']
                    logger.info("📄 Using end_print_start template from database")
                
                # Get move_to_safe template
                safe_template = get_template_by_key('move_to_safe')
                if safe_template and safe_template.get('gcode'):
                    safe_gcode = safe_template['gcode']
                    logger.info("📄 Using move_to_safe template from database")
                    
            except Exception as e:
                logger.warning(f"Failed to load templates from database: {e}")
            
            # Fallback to hardcoded if templates not found
            if not end_gcode:
                end_gcode = """;===== start end print sequence =====
M106 P1 S255
M400 ; wait for buffer to clear
G92 E0 ; zero the extruder
G1 E-0.5 F300 ; retract filament
M104 S0 ; turn off hotend
M140 S0 ; turn off heatbed
M106 S0 ; turn off part cooling fan
M106 P2 S0 ; turn off aux fan
M106 P3 S0 ; turn off chamber fan
;===== end start end print sequence ====="""
                logger.info("📄 Using fallback end_print_start gcode")
            
            if not safe_gcode:
                safe_gcode = """;===== start move to safe position =====
G91 ; relative positioning
G1 Z5 F1200 ; raise Z by 5mm
G90 ; absolute positioning
G1 X0 Y250 F12000 ; move to back corner
;===== end move to safe position ====="""
                logger.info("📄 Using fallback move_to_safe gcode")
            
            # Send end print gcode
            for line in end_gcode.split('\n'):
                line = line.strip()
                if line and not line.startswith(';'):
                    self.send_gcode_line(line)
                    time.sleep(0.1)
            
            # Wait a moment before moving
            time.sleep(1)
            
            # Move to safe position
            for line in safe_gcode.split('\n'):
                line = line.strip()
                if line and not line.startswith(';'):
                    self.send_gcode_line(line)
                    time.sleep(0.1)
            
            logger.info("✅ End sequence completed - heaters off, moved to safe position")
        
        # Start in background thread
        thread = threading.Thread(target=execute_end_sequence, daemon=True)
        thread.start()
        logger.info("🔄 Started end sequence thread")

    def start_print_from_sd(self, filename: str, use_ams: bool = True, plate_number: int = 1, 
                            ams_mapping = None, ams_slot: int = 0, flow_cali: bool = True, vibration_cali: bool = True,
                            bed_leveling: bool = True, layer_inspect: bool = False, timelapse: bool = False) -> bool:
        """
        Start printing a 3MF file that's already on the printer's SD card
        
        Based on FDM Monster and OctoPrint-BambuPrinter implementations:
        
        URL Format (CRITICAL - different per device type):
        - A1/P1 series: file:///{path}  (e.g., file:///model.3mf or file:///cache/model.3mf)
        - X1/X1C series: file:///mnt/sdcard/{path}
        
        Args:
            filename: Full path of the 3MF file on SD card (e.g., "cache/model.3mf" or just "model.3mf")
            use_ams: Whether to use AMS (Automatic Material System)
            plate_number: Which plate to print (default 1)
            ams_mapping: AMS slot mapping as LIST of integers. Examples:
                - [0] = use AMS slot 0 (first slot)
                - [1] = use AMS slot 1 (second slot)
                - [0,1,2,3] = multi-color mapping
                - None or [] = use ams_slot parameter
            ams_slot: Simple AMS slot number (0-3) when ams_mapping not provided
            flow_cali: Whether to run flow/extrusion calibration before printing (default True)
            vibration_cali: Whether to run vibration/resonance calibration (default True)
            bed_leveling: Whether to run bed leveling before print (default True)
            layer_inspect: Whether to enable layer inspection/first layer check (default False)
            timelapse: Whether to record timelapse video (default False)
            
        Returns: True if print command sent successfully
        """
        try:
            # Extract just the filename for subtask_name (UI display)
            import os
            subtask_name = os.path.basename(filename)
            
            # FDM Monster format (WORKING):
            # url: file:///sdcard/{filename}
            # Reference: fdm-monster/src/services/bambu/bambu-mqtt.adapter.ts line 291-305
            
            # Remove any leading slashes from filename to avoid double slashes
            clean_filename = filename.lstrip('/').lstrip('\\')
            file_url = f"file:///sdcard/{clean_filename}"
            
            # Generate sequence_id like FDM Monster does
            sequence_id = str(int(time.time() * 1000))
            
            # Convert ams_mapping to proper format (must be array of integers)
            # CRITICAL: ams_mapping MUST be a list/array, not a string!
            if ams_mapping is None or ams_mapping == "" or ams_mapping == []:
                # Use ams_slot to create mapping
                if use_ams:
                    ams_mapping_list = [ams_slot]  # e.g., [0] for slot 0, [1] for slot 1
                else:
                    ams_mapping_list = []  # Empty array for external spool
            elif isinstance(ams_mapping, str):
                # Convert string like "[0,1,2]" to list [0,1,2]
                try:
                    import ast
                    ams_mapping_list = ast.literal_eval(ams_mapping)
                    if not isinstance(ams_mapping_list, list):
                        ams_mapping_list = [ams_slot] if use_ams else []
                except:
                    ams_mapping_list = [ams_slot] if use_ams else []
            elif isinstance(ams_mapping, list):
                ams_mapping_list = ams_mapping
            else:
                ams_mapping_list = [ams_slot] if use_ams else []
            
            logger.info(f"🚀 Starting print from SD card: {filename}")
            logger.info(f"   File URL: {file_url}")
            logger.info(f"   Subtask name: {subtask_name}")
            logger.info(f"   Use AMS: {use_ams}")
            logger.info(f"   AMS Slot: {ams_slot}")
            logger.info(f"   AMS Mapping (list): {ams_mapping_list}")
            logger.info(f"   Plate: {plate_number}")
            logger.info(f"   Calibration: flow={flow_cali}, vibration={vibration_cali}, bed_level={bed_leveling}")
            logger.info(f"   Sequence ID: {sequence_id}")
            
            # Store current print info for tracking
            self.current_subtask_name = subtask_name
            self.current_task_id = "0"
            
            # Build project_file command following FDM Monster bambu-mqtt.adapter.ts
            # Key format from FDM Monster:
            # - param: filename (for gcode path within 3mf)
            # - url: file:///sdcard/{filename}
            # - subtask_name: filename for UI display
            # - sequence_id: timestamp string
            # CRITICAL: ams_mapping must be a LIST of integers, not a string!
            project_command = {
                "print": {
                    "sequence_id": sequence_id,
                    "command": "project_file",
                    "param": f"Metadata/plate_{plate_number}.gcode",
                    "md5": "",
                    "profile_id": "0",
                    "project_id": "0",
                    "subtask_id": "0",
                    "task_id": "0",
                    "subtask_name": subtask_name,
                    "url": file_url,
                    "bed_type": "auto",
                    "timelapse": timelapse,
                    "bed_leveling": bed_leveling,
                    "flow_cali": flow_cali,
                    "vibration_cali": vibration_cali,
                    "layer_inspect": layer_inspect,
                    "use_ams": use_ams,
                    "ams_mapping": ams_mapping_list  # MUST be list like [0] or [0,1,2,3]
                }
            }
            
            command_topic = self.TOPIC_COMMAND.format(printer_id=self.printer_id)
            
            logger.info(f"📤 Sending project_file command: {json.dumps(project_command, indent=2)}")
            logger.info(f"🔍 CALIBRATION PARAMS: flow_cali={flow_cali}, vibration_cali={vibration_cali}, bed_leveling={bed_leveling}")
            
            result = self.client.publish(
                command_topic, 
                json.dumps(project_command), 
                qos=1
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"✅ Print command sent successfully for: {filename}")
                return True
            else:
                logger.error(f"❌ Failed to send print command: rc={result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error starting print from SD: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def trigger_auto_eject(self) -> bool:
        """
        Trigger auto-eject mechanism for Bambu Lab A1
        
        The A1 uses G-code M620.2 for bed leveling kick or 
        the print completion triggers automatic plate eject
        
        For print farm automation, we use the gcode_line command
        to send the plate back for easy part removal
        """
        try:
            # Use gcode_line to send eject G-code
            # M991 = Custom gcode for plate eject on A1
            # Alternative: Send G28 to home axes then move bed forward
            command = {
                "print": {
                    "command": "gcode_line",
                    "sequence_id": self._generate_sequence_id(),
                    "param": "G28 X Y\nG1 Y 230 F6000\nM400"  # Home XY, move bed forward
                }
            }
            command_topic = self.TOPIC_COMMAND.format(printer_id=self.printer_id)
            
            result = self.client.publish(command_topic, json.dumps(command), qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info("Sent auto-eject command (bed forward)")
                return True
            else:
                logger.error(f"Failed to trigger auto-eject: rc={result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Error triggering auto-eject: {str(e)}")
            return False

    def send_gcode_line(self, gcode: str) -> bool:
        """
        Send a single line or multiple lines of G-code to printer
        
        Args:
            gcode: G-code command(s) to send
            
        Returns: True if sent successfully
        """
        try:
            command = {
                "print": {
                    "command": "gcode_line",
                    "sequence_id": self._generate_sequence_id(),
                    "param": gcode
                }
            }
            command_topic = self.TOPIC_COMMAND.format(printer_id=self.printer_id)
            
            result = self.client.publish(command_topic, json.dumps(command), qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Sent gcode_line: {gcode[:50]}...")
                return True
            else:
                logger.error(f"Failed to send gcode_line: rc={result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending gcode_line: {str(e)}")
            return False

    def _upload_file_ftp(self, file_path: str, filename: str) -> bool:
        """
        Upload file to printer via Implicit FTPS (port 990)
        
        Bambu Lab uses implicit FTPS which requires SSL from the start.
        Based on: https://github.com/darkorb/bambu-ftp-and-print
        
        Returns: True if upload successful
        """
        import ftplib
        import ssl
        
        try:
            logger.info(f"FTP: Connecting to {self.printer_ip}:990 (implicit FTPS)...")
            
            # Create SSL context for implicit FTPS
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            # FTP_TLS with implicit mode
            ftp = ftplib.FTP_TLS(
                host=self.printer_ip,
                timeout=30,
                context=context
            )
            ftp.auth()  # For implicit FTPS, this is needed
            
            logger.info("FTP: Connected via implicit FTPS")
            
            # Login
            ftp.login('bblp', self.access_code)
            logger.info("FTP: Logged in")
            
            # Set passive mode
            ftp.set_pasv(True)
            
            # Set to binary mode
            ftp.sendcmd('TYPE I')
            
            # Upload file
            logger.info(f"FTP: Uploading {filename}...")
            with open(file_path, 'rb') as f:
                ftp.storbinary(f'STOR {filename}', f)
            
            logger.info(f"FTP: Upload successful: {filename}")
            ftp.quit()
            return True
            
        except Exception as e:
            logger.error(f"FTP error: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            return False

    def send_print_file(self, file_path: str, local_server_url: str = "http://localhost:5000", skip_http: bool = False) -> bool:
        """
        Send print command to Bambu Lab printer (LAN mode)
        
        Workflow (emulating Bambu Studio cloud approach):
        1. File hosted on local HTTP server  
        2. Send MQTT project_file command with HTTP URL
        3. Printer downloads file from HTTP server
        4. Send MQTT start command
        
        Args:
            file_path: Path to local 3mf file
            local_server_url: Base URL of local HTTP server hosting files
            skip_http: If True, assume file is already on printer
            
        Returns: True if print command sent successfully
        """
        import os
        
        try:
            filename = os.path.basename(file_path)
            
            logger.info(f"Starting print process for: {filename}")
            logger.info(f"Using HTTP URL: {local_server_url}/uploads/{filename}")
            
            if skip_http:
                logger.info("Skipping HTTP download (file assumed on printer)")
            
            # Step 1: Send MQTT project_file command with HTTP URL
            logger.info("Step 1: Sending project_file command via MQTT...")
            
            # Generate unique IDs for tracking
            sequence_id = self._generate_sequence_id()
            task_id = str(int(time.time() * 1000))
            
            # Store for tracking
            self.current_subtask_name = filename
            self.current_task_id = task_id
            
            project_command = {
                "print": {
                    "sequence_id": sequence_id,
                    "command": "project_file",
                    "param": "Metadata/plate_1.gcode",
                    "subtask_id": task_id,
                    "task_id": task_id,
                    "subtask_name": filename,  # For tracking
                    "url": f"{local_server_url}/uploads/{filename}",
                    "timelapse": False,
                    "bed_leveling": False,
                    "flow_cali": False,
                    "vibration_cali": False,
                    "layer_inspect": True,
                    "use_ams": True
                }
            }
            
            command_topic = self.TOPIC_COMMAND.format(printer_id=self.printer_id)
            result = self.client.publish(command_topic, json.dumps(project_command), qos=1)
            
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.error(f"Failed to send project_file command: rc={result.rc}")
                return False
            
            logger.info("Project file command sent, waiting 3 seconds for download...")
            import time
            time.sleep(3)
            
            # Step 2: Send start command
            logger.info("Step 2: Sending start command...")
            
            start_command = {
                "print": {
                    "command": "start",
                    "sequence_id": self._generate_sequence_id()
                }
            }
            
            result = self.client.publish(command_topic, json.dumps(start_command), qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Print sequence complete for: {filename}")
                return True
            else:
                logger.error(f"Failed to send start command: rc={result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Error in send_print_file: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
                
        except Exception as e:
            logger.error(f"Error sending print command: {str(e)}")
            return False

    def get_printer_status(self) -> Dict[str, Any]:
        """Get current printer status including temperature data and connection state"""
        return {
            "printer_id": self.printer_id,
            "printer_status": self.printer_status,
            "mqtt_connected": self.mqtt_connected,
            "current_print_progress": self.current_print_progress,
            "mc_remaining_time": self.remaining_time,
            "nozzle_temp": self.nozzle_temp,
            "nozzle_target_temp": self.nozzle_target_temp,
            "bed_temp": self.bed_temp,
            "bed_target_temp": self.bed_target_temp,
            "chamber_temp": self.chamber_temp,
            # Layer tracking
            "current_layer": self.current_layer,
            "total_layers": self.total_layers,
            # Connection state management
            "socket_state": self.connection_state.socket_state.value,
            "api_state": self.connection_state.api_state.value,
            "last_message_timestamp": self.connection_state.last_message_timestamp,
            "reconnect_attempts": self.connection_state.reconnect_attempts,
            # Current print tracking
            "current_subtask_name": self.current_subtask_name,
            "current_task_id": self.current_task_id,
        }

    def is_printer_online(self) -> bool:
        """Check if printer is online and MQTT connected"""
        return self.mqtt_connected and self.printer_status != "offline"

    def is_printer_idle(self) -> bool:
        """Check if printer is idle (not currently printing)"""
        return self.mqtt_connected and self.printer_status == "idle"

    def get_print_progress(self) -> int:
        """Get current print progress percentage (0-100)"""
        return self.current_print_progress


# ============================================================================
# Global Singleton for MQTT Client
# ============================================================================

_global_bambu_client: Optional[BambuLabMQTTClient] = None
_client_lock = threading.Lock()


def initialize_bambu_client(
    printer_id: str,
    printer_ip: str,
    access_code: str,
    use_lan_mode: bool = True
) -> BambuLabMQTTClient:
    """
    Initialize the global Bambu MQTT client singleton.
    Should be called once at application startup.
    
    Args:
        printer_id: Printer serial number
        printer_ip: Printer IP address
        access_code: Printer access code
        use_lan_mode: Whether to use LAN mode (default True for A1)
    
    Returns:
        The initialized BambuLabMQTTClient instance
    """
    global _global_bambu_client
    
    with _client_lock:
        if _global_bambu_client is not None:
            logger.warning("Bambu client already initialized, returning existing instance")
            return _global_bambu_client
        
        logger.info(f"Initializing global Bambu MQTT client: printer_id={printer_id}, ip={printer_ip}")
        
        _global_bambu_client = BambuLabMQTTClient(
            printer_id=printer_id,
            printer_ip=printer_ip,
            access_code=access_code,
            use_lan_mode=use_lan_mode
        )
        
        # Connect (loop_start is called inside connect())
        if _global_bambu_client.connect():
            logger.info("✅ Global Bambu MQTT client connected and started")
        else:
            logger.error("❌ Failed to connect global Bambu MQTT client")
        
        return _global_bambu_client


def get_bambu_client() -> Optional[BambuLabMQTTClient]:
    """
    Get the global Bambu MQTT client singleton.
    Returns None if not initialized.
    
    Returns:
        The BambuLabMQTTClient instance or None
    """
    global _global_bambu_client
    
    if _global_bambu_client is None:
        logger.warning("Bambu client not initialized. Call initialize_bambu_client() first.")
        return None
    
    return _global_bambu_client


def shutdown_bambu_client():
    """Shutdown the global Bambu MQTT client."""
    global _global_bambu_client
    
    with _client_lock:
        if _global_bambu_client is not None:
            logger.info("Shutting down global Bambu MQTT client...")
            _global_bambu_client.disconnect()
            _global_bambu_client = None
            logger.info("✅ Global Bambu MQTT client shut down")
