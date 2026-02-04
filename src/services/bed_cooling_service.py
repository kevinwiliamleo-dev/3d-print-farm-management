"""
Bed Cooling Service
Automatically control external Kit fan when bed needs to cool down

When bed_temp > bed_target_temp (cooling down):
1. Turn ON Kit fan
2. Monitor temperature
3. Turn OFF fan when bed_temp <= bed_target_temp

Integrated with MQTT temperature monitoring
"""
import logging
import time
import asyncio
import aiohttp
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CoolingState:
    """Track cooling operation state"""
    is_cooling: bool = False
    start_time: Optional[float] = None
    start_temp: float = 0.0
    target_temp: float = 0.0
    kit_ip: Optional[str] = None
    last_temp_check: float = 0.0


class BedCoolingService:
    """
    Service to automatically control external fan for bed cooling
    
    Features:
    - Detect when bed needs cooling (current > target)
    - Auto turn ON external Kit fan
    - Monitor temp progress
    - Auto turn OFF fan when target reached
    - Prevent rapid on/off cycles with hysteresis
    """
    
    def __init__(self, printer_id: str):
        self.printer_id = printer_id
        self.cooling_state = CoolingState()
        
        # Cooling parameters
        self.temp_threshold = 2.0  # Only activate if diff > 2°C
        self.temp_tolerance = 1.0   # Turn off when within 1°C of target
        self.min_cooling_time = 30  # Minimum 30 seconds before checking
        self.check_interval = 5     # Check every 5 seconds
        
        # Kit configuration (will be set from settings)
        self.kit_ip: Optional[str] = None
        self.kit_enabled: bool = False
        
        logger.info(f"🌡️ Bed Cooling Service initialized for printer: {printer_id}")
    
    def configure_kit(self, kit_ip: str, enabled: bool = True):
        """
        Configure external Kit for cooling
        
        Args:
            kit_ip: IP address of ESP32 Kit (e.g. "192.168.1.100")
            enabled: Enable/disable auto cooling feature
        """
        self.kit_ip = kit_ip
        self.kit_enabled = enabled
        logger.info(f"🔧 Kit configured: IP={kit_ip}, Enabled={enabled}")
    
    async def _control_fan(self, state: str) -> bool:
        """
        Control Kit fan via HTTP
        
        Args:
            state: "on" or "off"
        
        Returns:
            True if successful, False otherwise
        """
        if not self.kit_ip:
            logger.warning("⚠️ Kit IP not configured, cannot control fan")
            return False
        
        try:
            url = f"http://{self.kit_ip}:5000/kit/fan?state={state}"
            timeout = aiohttp.ClientTimeout(total=10.0)  # Increased timeout
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ Fan {state.upper()}: {data}")
                        return True
                    else:
                        logger.error(f"❌ Fan control failed: HTTP {response.status}")
                        return False
        
        except asyncio.TimeoutError:
            logger.error(f"⏱️ Fan control timeout (Kit IP: {self.kit_ip})")
            return False
        except Exception as e:
            logger.error(f"❌ Fan control error: {e}")
            return False
    
    async def update_temperature(
        self, 
        bed_temp: float, 
        bed_target_temp: float,
        force_check: bool = False
    ):
        """
        Called by MQTT handler when temperature updates arrive
        
        Detects cooling scenarios and controls fan accordingly
        
        Args:
            bed_temp: Current bed temperature
            bed_target_temp: Target bed temperature
            force_check: Force immediate check (bypass timing)
        """
        # Skip if Kit not configured
        if not self.kit_enabled or not self.kit_ip:
            return
        
        # Skip if no valid target (target = 0 means no active heating/cooling)
        if bed_target_temp <= 0:
            # If currently cooling, stop it
            if self.cooling_state.is_cooling:
                logger.info("🛑 No target temp, stopping cooling")
                await self._stop_cooling()
            return
        
        current_time = time.time()
        temp_diff = bed_temp - bed_target_temp
        
        # =================================================================
        # SCENARIO 1: Bed needs cooling (current > target + threshold)
        # =================================================================
        if temp_diff > self.temp_threshold:
            if not self.cooling_state.is_cooling:
                # Start new cooling cycle
                logger.info(f"🌡️ Bed cooling needed: {bed_temp:.1f}°C → {bed_target_temp:.1f}°C (diff: {temp_diff:.1f}°C)")
                await self._start_cooling(bed_temp, bed_target_temp)
            else:
                # Already cooling, just update progress
                elapsed = current_time - self.cooling_state.start_time
                temp_drop = self.cooling_state.start_temp - bed_temp
                
                # Log progress every 30 seconds
                if current_time - self.cooling_state.last_temp_check >= 30:
                    logger.info(
                        f"❄️ Cooling in progress: {bed_temp:.1f}°C → {bed_target_temp:.1f}°C "
                        f"(elapsed: {int(elapsed)}s, dropped: {temp_drop:.1f}°C)"
                    )
                    self.cooling_state.last_temp_check = current_time
        
        # =================================================================
        # SCENARIO 2: Target temperature reached (within tolerance)
        # =================================================================
        elif self.cooling_state.is_cooling and temp_diff <= self.temp_tolerance:
            elapsed = current_time - self.cooling_state.start_time
            total_drop = self.cooling_state.start_temp - bed_temp
            
            # Only stop if minimum cooling time elapsed (prevent rapid cycling)
            if elapsed >= self.min_cooling_time or force_check:
                logger.info(
                    f"✅ Bed cooling complete! {self.cooling_state.start_temp:.1f}°C → {bed_temp:.1f}°C "
                    f"(time: {int(elapsed)}s, dropped: {total_drop:.1f}°C)"
                )
                await self._stop_cooling()
            else:
                logger.debug(f"⏳ Target reached but waiting minimum time ({int(elapsed)}/{self.min_cooling_time}s)")
    
    async def _start_cooling(self, bed_temp: float, bed_target_temp: float):
        """Start cooling cycle - turn ON fan"""
        self.cooling_state.is_cooling = True
        self.cooling_state.start_time = time.time()
        self.cooling_state.start_temp = bed_temp
        self.cooling_state.target_temp = bed_target_temp
        self.cooling_state.last_temp_check = time.time()
        
        logger.info(f"🌀 Starting bed cooling: {bed_temp:.1f}°C → {bed_target_temp:.1f}°C")
        
        # Turn ON Kit fan
        success = await self._control_fan("on")
        if success:
            logger.info("✅ Cooling fan turned ON")
        else:
            logger.error("❌ Failed to turn ON cooling fan")
    
    async def _stop_cooling(self):
        """Stop cooling cycle - turn OFF fan"""
        if not self.cooling_state.is_cooling:
            return
        
        logger.info("🛑 Stopping bed cooling")
        
        # Turn OFF Kit fan
        success = await self._control_fan("off")
        if success:
            logger.info("✅ Cooling fan turned OFF")
        else:
            logger.error("❌ Failed to turn OFF cooling fan")
        
        # Reset state
        self.cooling_state = CoolingState()
    
    def get_cooling_status(self) -> Dict[str, Any]:
        """
        Get current cooling status
        
        Returns dict with:
        - is_cooling: bool
        - elapsed_seconds: int
        - start_temp, target_temp: float
        - kit_ip, kit_enabled: config info
        """
        elapsed = 0
        if self.cooling_state.is_cooling and self.cooling_state.start_time:
            elapsed = int(time.time() - self.cooling_state.start_time)
        
        return {
            "is_cooling": self.cooling_state.is_cooling,
            "elapsed_seconds": elapsed,
            "start_temp": self.cooling_state.start_temp,
            "target_temp": self.cooling_state.target_temp,
            "kit_ip": self.kit_ip,
            "kit_enabled": self.kit_enabled,
        }
    
    async def force_stop(self):
        """Force stop cooling (manual override)"""
        if self.cooling_state.is_cooling:
            logger.warning("⚠️ Force stopping bed cooling")
            await self._stop_cooling()


# Global instance per printer
_cooling_services: Dict[str, BedCoolingService] = {}


def get_cooling_service(printer_id: str) -> BedCoolingService:
    """
    Get or create cooling service for printer
    
    Args:
        printer_id: Printer ID
    
    Returns:
        BedCoolingService instance
    """
    if printer_id not in _cooling_services:
        _cooling_services[printer_id] = BedCoolingService(printer_id)
    
    return _cooling_services[printer_id]
