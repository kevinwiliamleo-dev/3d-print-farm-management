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
        # HYSTERESIS DESIGN: start_threshold must be > stop_tolerance
        # This prevents rapid on/off cycling when bed temp fluctuates
        self.start_threshold = 3.0     # START fan when bed > target + 3°C
        self.stop_tolerance = 2.0      # STOP fan when bed <= target + 2°C
        self.min_fan_action_interval = 60  # Min 60s between fan state changes (prevent rapid cycling)
        self.check_interval = 5        # Check every 5 seconds
        self.ambient_threshold = 33.0  # Activate fan when target=0 but bed > this (°C)
        self._last_fan_action_time: float = 0  # Track last time fan was toggled
        
        # Kit configuration (will be set from settings)
        self.kit_ip: Optional[str] = None
        self.kit_enabled: bool = False
        
        # Keep-alive task: sends fan=ON every 10s while cooling, independent of MQTT
        self._keepalive_task: Optional[asyncio.Task] = None
        self.keepalive_interval = 10  # seconds between keep-alive sends
        
        logger.info(f"🌡️ Bed Cooling Service initialized for printer: {printer_id}")
    
    def configure_kit(self, kit_ip: str, enabled: bool = True, ambient_threshold: float = None):
        """
        Configure external Kit for cooling
        
        Args:
            kit_ip: IP address of ESP32 Kit (e.g. "192.168.1.100")
            enabled: Enable/disable auto cooling feature
            ambient_threshold: Activate fan when bed heater is OFF but bed > this temp (°C).
                               If not provided, keeps the current value (default 33°C from __init__).
        """
        self.kit_ip = kit_ip
        self.kit_enabled = enabled
        if ambient_threshold is not None:
            self.ambient_threshold = ambient_threshold
        # else: keep __init__ default (33.0°C) — do NOT override with function default
        logger.info(f"🔧 Kit configured: IP={kit_ip}, Enabled={enabled}, AmbientThreshold={self.ambient_threshold}°C")
    
    async def _verify_fan_state(self) -> bool:
        """
        Query ESP32 to get actual fan state.
        Returns True if fan is ON, False if OFF or unreachable.
        On error, returns True to avoid spurious re-sends.
        """
        if not self.kit_ip:
            return True  # Can't verify, assume OK
        try:
            url = f"http://{self.kit_ip}:5000/kit/fan?state=status"
            timeout = aiohttp.ClientTimeout(total=5.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("status") == "ON"
        except Exception as e:
            logger.debug(f"⚠️ Could not verify fan state: {e} — assuming ON to avoid spam")
        return True  # Can't determine → optimistic (don't re-send on every network blip)

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
        
        # Skip if no valid target (target = 0 means bed heater OFF after print)
        # Special case: still activate fan if bed is hot (ambient cooling mode)
        if bed_target_temp <= 0:
            if bed_temp >= self.ambient_threshold:
                # Bed heater OFF but bed still hot → cool to ambient threshold
                if not self.cooling_state.is_cooling:
                    time_since_last = time.time() - self._last_fan_action_time
                    if time_since_last >= self.min_fan_action_interval:
                        logger.info(
                            f"🌡️ Bed heater OFF but bed hot ({bed_temp:.1f}°C >= {self.ambient_threshold:.1f}°C) — "
                            f"activating fan for ambient cooling"
                        )
                        await self._start_cooling(bed_temp, self.ambient_threshold)
                    else:
                        logger.debug(f"⏳ Ambient cooling: waiting {int(self.min_fan_action_interval - time_since_last)}s before restart")
                    return  # BUG FIX: don't fall through to scenario checks after just starting/waiting
                # Already cooling in ambient mode — set target for scenario 2 stop check
                bed_target_temp = self.ambient_threshold
            else:
                # Bed already cool, stop if still running
                if self.cooling_state.is_cooling:
                    logger.info(f"🛑 Bed target=0 and bed cool ({bed_temp:.1f}°C ≤ {self.ambient_threshold:.1f}°C), stopping fan")
                    await self._stop_cooling()
                return
        
        current_time = time.time()
        temp_diff = bed_temp - bed_target_temp
        time_since_last_action = current_time - self._last_fan_action_time
        
        # =================================================================
        # SCENARIO 1: Bed needs cooling → START fan
        # Only start if diff > start_threshold AND fan not already on
        # AND minimum interval since last action (prevent rapid cycling)
        # =================================================================
        if temp_diff >= self.start_threshold:
            if not self.cooling_state.is_cooling:
                if time_since_last_action >= self.min_fan_action_interval:
                    logger.info(
                        f"🌡️ Bed cooling needed: {bed_temp:.1f}°C → {bed_target_temp:.1f}°C "
                        f"(diff: {temp_diff:.1f}°C > threshold {self.start_threshold}°C)"
                    )
                    await self._start_cooling(bed_temp, bed_target_temp)
                else:
                    logger.debug(
                        f"⏳ Waiting before restart: {int(time_since_last_action)}/{self.min_fan_action_interval}s"
                    )
            else:
                # Already cooling, log progress AND verify fan state every 30 seconds
                elapsed = current_time - self.cooling_state.start_time
                temp_drop = self.cooling_state.start_temp - bed_temp
                if current_time - self.cooling_state.last_temp_check >= 30:
                    logger.info(
                        f"❄️ Cooling in progress: {bed_temp:.1f}°C → {bed_target_temp:.1f}°C "
                        f"(elapsed: {int(elapsed)}s, dropped: {temp_drop:.1f}°C)"
                    )
                    self.cooling_state.last_temp_check = current_time
                    # Keep-alive is handled by _keepalive_loop() background task (every 10s)
        
        # =================================================================
        # SCENARIO 2: Target reached → STOP fan
        # Only stop when bed is truly within stop_tolerance of target
        # AND fan has been running at least min_fan_action_interval seconds
        # =================================================================
        elif self.cooling_state.is_cooling and temp_diff <= self.stop_tolerance:
            elapsed = current_time - self.cooling_state.start_time
            total_drop = self.cooling_state.start_temp - bed_temp
            # Ensure fan ran for at least min_fan_action_interval before stopping
            if elapsed >= self.min_fan_action_interval:
                logger.info(
                    f"✅ Bed cooling complete! {self.cooling_state.start_temp:.1f}°C → {bed_temp:.1f}°C "
                    f"(diff: {temp_diff:.1f}°C ≤ stop_tolerance {self.stop_tolerance}°C, "
                    f"time: {int(elapsed)}s, dropped: {total_drop:.1f}°C)"
                )
                await self._stop_cooling()
            else:
                logger.debug(f"⏳ Target reached but fan min runtime not met ({int(elapsed)}/{self.min_fan_action_interval}s)")
        
        # =================================================================
        # In-between zone (stop_tolerance < diff <= start_threshold):
        # Fan already ON → keep running (let it cool further)
        # Fan already OFF → don't start yet (hysteresis gap)
        # =================================================================
    
    async def _keepalive_loop(self):
        """Background task: send fan=ON every keepalive_interval seconds while cooling.
        Prevents ESP32 watchdog auto-off and handles brief reboots/network blips.
        """
        try:
            while self.cooling_state.is_cooling:
                await asyncio.sleep(self.keepalive_interval)
                if not self.cooling_state.is_cooling:
                    break  # Stopped while sleeping
                logger.debug(f"🔄 Fan keep-alive ping ({self.keepalive_interval}s interval)")
                success = await self._control_fan("on")
                if not success:
                    logger.warning("⚠️ Keep-alive fan=ON failed (will retry next interval)")
        except asyncio.CancelledError:
            logger.debug("🛑 Fan keep-alive task cancelled")
        except Exception as e:
            logger.error(f"❌ Keep-alive loop error: {e}")

    async def _start_cooling(self, bed_temp: float, bed_target_temp: float):
        """Start cooling cycle - turn ON fan"""
        self.cooling_state.is_cooling = True
        self.cooling_state.start_time = time.time()
        self.cooling_state.start_temp = bed_temp
        self.cooling_state.target_temp = bed_target_temp
        self.cooling_state.last_temp_check = time.time()
        
        logger.info(f"🌀 Starting bed cooling: {bed_temp:.1f}°C → {bed_target_temp:.1f}°C")
        self._last_fan_action_time = time.time()
        
        # Turn ON Kit fan
        success = await self._control_fan("on")
        if success:
            logger.info("✅ Cooling fan turned ON")
        else:
            logger.error("❌ Failed to turn ON cooling fan")
        
        # Start background keep-alive task
        if self._keepalive_task and not self._keepalive_task.done():
            self._keepalive_task.cancel()
        self._keepalive_task = asyncio.create_task(self._keepalive_loop())
        logger.debug(f"✅ Fan keep-alive task started (interval: {self.keepalive_interval}s)")
    
    async def _stop_cooling(self):
        """Stop cooling cycle - turn OFF fan"""
        if not self.cooling_state.is_cooling:
            return
        
        logger.info("🛑 Stopping bed cooling")
        self._last_fan_action_time = time.time()
        
        # Cancel keep-alive task first
        if self._keepalive_task and not self._keepalive_task.done():
            self._keepalive_task.cancel()
            self._keepalive_task = None
        
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
