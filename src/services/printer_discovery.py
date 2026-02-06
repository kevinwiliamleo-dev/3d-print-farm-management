"""
Printer Discovery Service - Auto-detect Bambu Lab printers on network
Similar to OrcaSlicer's network discovery feature
"""
import socket
import json
import logging
from typing import List, Dict, Optional
import asyncio

logger = logging.getLogger(__name__)

class BambuPrinterDiscovery:
    """
    Discover Bambu Lab printers on local network using UDP broadcast
    Based on OrcaSlicer's discovery implementation
    """
    
    DISCOVERY_PORT = 2021  # Bambu Lab discovery port
    BROADCAST_ADDR = '255.255.255.255'
    TIMEOUT = 5  # seconds
    
    def __init__(self):
        self.discovered_printers = []
    
    def discover_printers(self, timeout: int = 5) -> List[Dict]:
        """
        Scan network for Bambu Lab printers via UDP broadcast
        
        Returns:
            List of discovered printers with IP, name, model, serial
        """
        logger.info("🔍 Starting printer discovery scan...")
        self.discovered_printers = []
        
        try:
            # Create UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(timeout)
            
            # Broadcast discovery packet
            discovery_msg = json.dumps({
                "cmd": "discover",
                "from": "3d-print-farm"
            }).encode('utf-8')
            
            sock.sendto(discovery_msg, (self.BROADCAST_ADDR, self.DISCOVERY_PORT))
            logger.info(f"📡 Discovery broadcast sent to {self.BROADCAST_ADDR}:{self.DISCOVERY_PORT}")
            
            # Collect responses
            start_time = asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0
            while True:
                try:
                    data, addr = sock.recvfrom(4096)
                    printer_info = self._parse_printer_response(data, addr)
                    if printer_info:
                        self.discovered_printers.append(printer_info)
                        logger.info(f"✅ Found printer: {printer_info['name']} at {printer_info['ip']}")
                except socket.timeout:
                    logger.info("⏱️ Discovery scan timeout reached")
                    break
                except Exception as e:
                    logger.error(f"❌ Error receiving response: {e}")
                    break
            
            sock.close()
            logger.info(f"🎯 Discovery complete: Found {len(self.discovered_printers)} printer(s)")
            return self.discovered_printers
            
        except Exception as e:
            logger.error(f"❌ Discovery failed: {e}")
            return []
    
    def _parse_printer_response(self, data: bytes, addr: tuple) -> Optional[Dict]:
        """Parse printer UDP response"""
        try:
            response = json.loads(data.decode('utf-8'))
            
            # Extract printer info from response
            printer_info = {
                'ip': addr[0],
                'name': response.get('dev_name', 'Unknown Printer'),
                'model': response.get('dev_model_name', 'Unknown Model'),
                'serial': response.get('dev_id', ''),
                'access_code': '',  # User must provide this
                'status': 'discovered',
                'connection_type': response.get('connection', 'lan')
            }
            
            return printer_info
            
        except json.JSONDecodeError:
            logger.warning(f"⚠️ Invalid JSON from {addr[0]}")
            return None
        except Exception as e:
            logger.error(f"❌ Error parsing response from {addr[0]}: {e}")
            return None
    
    async def discover_printers_async(self, timeout: int = 5) -> List[Dict]:
        """Async version of discover_printers"""
        return await asyncio.to_thread(self.discover_printers, timeout)
    
    def get_last_discovered(self) -> List[Dict]:
        """Get results from last discovery scan"""
        return self.discovered_printers


# Fallback: IP range scanner if UDP discovery fails
class IPRangeScanner:
    """Scan IP range for Bambu Lab printers"""
    
    @staticmethod
    async def scan_subnet(subnet: str = "192.168.1", timeout: float = 1.0) -> List[Dict]:
        """
        Scan IP range for printers
        
        Args:
            subnet: First 3 octets of IP (e.g., "192.168.1")
            timeout: Socket timeout per IP
        
        Returns:
            List of found printers
        """
        logger.info(f"🔍 Scanning subnet {subnet}.0/24...")
        found_printers = []
        
        tasks = [
            IPRangeScanner._check_ip(f"{subnet}.{i}", timeout)
            for i in range(1, 255)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, dict) and result:
                found_printers.append(result)
                logger.info(f"✅ Found printer at {result['ip']}")
        
        logger.info(f"🎯 Subnet scan complete: Found {len(found_printers)} printer(s)")
        return found_printers
    
    @staticmethod
    async def _check_ip(ip: str, timeout: float) -> Optional[Dict]:
        """Check if Bambu printer exists at IP"""
        try:
            # Try to connect to MQTT port
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, 8883),
                timeout=timeout
            )
            writer.close()
            await writer.wait_closed()
            
            # If connection successful, likely a Bambu printer
            return {
                'ip': ip,
                'name': f'Bambu Printer ({ip})',
                'model': 'Unknown (Detected)',
                'serial': '',
                'access_code': '',
                'status': 'detected',
                'connection_type': 'lan'
            }
        except:
            return None
