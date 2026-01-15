"""
Printer Network Discovery Service
Auto-discovers Bambu Lab A1 printers on local network using mDNS/SSDP
Follows naming conventions from README.md

OPTIMIZED: Uses parallel scanning and proper mDNS for fast discovery
Now includes MQTT status check for real-time printer status
"""
import logging
import socket
import ssl
import json
from typing import List, Dict, Any, Optional
import threading
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


def check_mqtt_status(ip_address: str, access_code: str, printer_id: str = None, timeout: float = 5.0) -> Dict[str, Any]:
    """
    Quick MQTT connection to check printer status
    
    Args:
        ip_address: Printer IP address
        access_code: Access code for LAN mode
        printer_id: Printer serial number (optional, uses default if not provided)
        timeout: Connection timeout
        
    Returns:
        Dict with status info: {"online": bool, "status": str, "printing": bool, "progress": int}
    """
    try:
        import paho.mqtt.client as mqtt
        
        result = {
            "online": False,
            "status": "offline",
            "printing": False,
            "progress": 0,
            "mqtt_connected": False
        }
        
        if not access_code:
            logger.warning("No access code provided for MQTT status check")
            return result
        
        # Use printer_id or generate one
        device_id = printer_id or os.getenv("BAMBU_PRINTER_ID", "")
        if not device_id:
            # Try to get from IP
            device_id = f"BAMBU_{ip_address.replace('.', '_')}"
        
        status_received = threading.Event()
        
        def on_connect(client, userdata, flags, reason_code, properties=None):
            rc = reason_code if isinstance(reason_code, int) else reason_code.value if hasattr(reason_code, 'value') else 0
            if rc == 0:
                result["mqtt_connected"] = True
                result["online"] = True
                result["status"] = "idle"  # Connected = at least idle
                
                # Subscribe to status topic
                topic = f"device/{device_id}/report"
                client.subscribe(topic)
                
                # Request status push
                cmd_topic = f"device/{device_id}/request"
                push_cmd = {"pushing": {"sequence_id": "0", "command": "pushall"}}
                client.publish(cmd_topic, json.dumps(push_cmd))
        
        def on_message(client, userdata, msg):
            try:
                payload = json.loads(msg.payload.decode())
                
                # Check print section for status
                if "print" in payload:
                    print_data = payload["print"]
                    gcode_state = print_data.get("gcode_state", "")
                    mc_print_stage = print_data.get("mc_print_stage", "")
                    
                    if gcode_state in ["RUNNING", "PRINTING"] or mc_print_stage == "printing":
                        result["status"] = "printing"
                        result["printing"] = True
                        result["progress"] = print_data.get("mc_percent", 0)
                    elif gcode_state == "PAUSE":
                        result["status"] = "paused"
                        result["printing"] = True
                        result["progress"] = print_data.get("mc_percent", 0)
                    elif gcode_state in ["IDLE", "FINISH", "FAILED"]:
                        result["status"] = "idle"
                        result["printing"] = False
                    
                    status_received.set()
                    
            except Exception as e:
                logger.debug(f"Error parsing MQTT message: {e}")
        
        # Create MQTT client
        try:
            client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        except TypeError:
            client = mqtt.Client()
        
        client.username_pw_set("bblp", access_code)
        client.tls_set(cert_reqs=ssl.CERT_NONE)
        client.tls_insecure_set(True)
        
        client.on_connect = on_connect
        client.on_message = on_message
        
        # Connect with short timeout
        client.connect(ip_address, 8883, keepalive=30)
        client.loop_start()
        
        # Wait for status (with timeout)
        status_received.wait(timeout=timeout)
        
        # Cleanup
        client.loop_stop()
        client.disconnect()
        
        if result["mqtt_connected"]:
            logger.info(f"Printer at {ip_address}: status={result['status']}, printing={result['printing']}")
        
        return result
        
    except Exception as e:
        logger.debug(f"MQTT status check failed for {ip_address}: {e}")
        return {
            "online": False,
            "status": "offline", 
            "printing": False,
            "progress": 0,
            "mqtt_connected": False
        }


class PrinterDiscoveryService:
    """Discovers Bambu Lab printers on local network"""

    # Bambu Lab specific ports
    # 990 = FTP over TLS (file transfer)
    # 6000 = Bambu Lab streaming/control
    # 8883 = MQTT over TLS (main control)
    BAMBU_PORTS = [8883, 6000, 990]
    BAMBU_SSDP_PORT = 2021
    BAMBU_HTTP_PORT = 80
    
    def __init__(self):
        """Initialize discovery service"""
        self.discovered_printers: Dict[str, Dict[str, Any]] = {}
        self.discovery_thread: Optional[threading.Thread] = None
        self.is_discovering = False
        self._scan_timeout = 0.1  # 100ms timeout per port (fast)
        
        # Try to get known printer IP from config
        self._known_printer_ip = os.getenv("BAMBU_PRINTER_IP", "")
        self._known_printer_id = os.getenv("BAMBU_PRINTER_ID", "")

    def scan_network(self, timeout: float = 8.0) -> List[Dict[str, Any]]:
        """
        Scan local network for Bambu Lab printers (FAST version)
        
        Args:
            timeout: Maximum time for entire scan in seconds
            
        Returns:
            List of discovered printers with printer_id, printer_name, ip_address
        """
        logger.info("Starting fast network discovery...")
        start_time = time.time()
        discovered = []
        
        # Method 0: Check known printer IP from config first (fastest)
        if self._known_printer_ip:
            logger.info(f"[0/4] Checking configured printer at {self._known_printer_ip}...")
            config_result = self._check_known_printer()
            if config_result:
                discovered.append(config_result)
                logger.info(f"Found configured printer at {self._known_printer_ip}")
        
        # Method 1: Try mDNS hostnames (fast)
        logger.info("[1/4] Checking mDNS hostnames...")
        mdns_results = self._check_mdns_hostnames()
        for r in mdns_results:
            if r["ip_address"] not in [d.get("ip_address") for d in discovered]:
                discovered.append(r)
        
        # Method 2: Try SSDP discovery (Bambu Lab specific)
        logger.info("[2/4] Trying SSDP discovery...")
        ssdp_results = self._ssdp_discover(timeout=2.0)
        for r in ssdp_results:
            if r["ip_address"] not in [d.get("ip_address") for d in discovered]:
                discovered.append(r)
        
        # Method 3: Fast parallel port scan on all local subnets
        remaining_time = timeout - (time.time() - start_time)
        if remaining_time > 1.0:
            logger.info("[3/4] Running parallel network scan...")
            scan_results = self._fast_parallel_scan(max_time=remaining_time)
            for r in scan_results:
                if r["ip_address"] not in [d.get("ip_address") for d in discovered]:
                    discovered.append(r)
        
        elapsed = time.time() - start_time
        logger.info(f"Discovery completed in {elapsed:.1f}s, found {len(discovered)} printer(s)")
        
        # Save to discovered printers
        for p in discovered:
            self.discovered_printers[p["printer_id"]] = p
        
        return discovered

    def _check_known_printer(self) -> Optional[Dict[str, Any]]:
        """Check if the configured printer IP is reachable"""
        if not self._known_printer_ip:
            return None
            
        for port in self.BAMBU_PORTS:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1.0)
                result = sock.connect_ex((self._known_printer_ip, port))
                sock.close()
                
                if result == 0:
                    printer_id = self._known_printer_id or f"BAMBU_{self._known_printer_ip.replace('.', '_')}"
                    return {
                        "printer_id": printer_id,
                        "printer_name": f"Bambu Lab A1 ({self._known_printer_ip})",
                        "ip_address": self._known_printer_ip,
                        "port": port,
                        "mqtt_port": 8883,
                        "ftp_port": 990,
                        "discovery_method": "config"
                    }
            except:
                pass
        return None

    def _check_mdns_hostnames(self) -> List[Dict[str, Any]]:
        """Check common Bambu Lab mDNS hostnames (very fast)"""
        discovered = []
        
        # Common hostnames for Bambu Lab printers
        hostnames = [
            "bambu-lab.local",
            "a1.local", 
            "a1-combo.local",
            "bambulab.local",
            "BambuLab.local",
        ]
        
        for hostname in hostnames:
            try:
                socket.setdefaulttimeout(0.5)
                ip = socket.gethostbyname(hostname)
                logger.info(f"Found via mDNS: {hostname} -> {ip}")
                discovered.append({
                    "printer_id": hostname.replace(".local", "").replace("-", "_").upper(),
                    "printer_name": f"Bambu Lab ({hostname})",
                    "ip_address": ip,
                    "hostname": hostname,
                    "discovery_method": "mDNS"
                })
            except (socket.gaierror, socket.timeout):
                pass
        
        return discovered

    def _ssdp_discover(self, timeout: float = 2.0) -> List[Dict[str, Any]]:
        """
        Use SSDP to discover Bambu Lab printers
        Bambu Lab printers respond to SSDP M-SEARCH on local network
        """
        discovered = []
        
        try:
            # SSDP M-SEARCH message
            ssdp_request = (
                'M-SEARCH * HTTP/1.1\r\n'
                'HOST: 239.255.255.250:1900\r\n'
                'MAN: "ssdp:discover"\r\n'
                'MX: 2\r\n'
                'ST: ssdp:all\r\n'
                '\r\n'
            )
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.settimeout(timeout)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            # Send to SSDP multicast address
            sock.sendto(ssdp_request.encode(), ('239.255.255.250', 1900))
            
            end_time = time.time() + timeout
            while time.time() < end_time:
                try:
                    data, addr = sock.recvfrom(1024)
                    response = data.decode('utf-8', errors='ignore')
                    
                    # Check if this looks like a Bambu Lab printer
                    if 'bambu' in response.lower() or 'BambuLab' in response:
                        logger.info(f"Found Bambu Lab via SSDP at {addr[0]}")
                        discovered.append({
                            "printer_id": f"SSDP_{addr[0].replace('.', '_')}",
                            "printer_name": f"Bambu Lab at {addr[0]}",
                            "ip_address": addr[0],
                            "discovery_method": "SSDP"
                        })
                except socket.timeout:
                    break
                    
            sock.close()
            
        except Exception as e:
            logger.debug(f"SSDP discovery error: {e}")
        
        return discovered

    def _fast_parallel_scan(self, max_time: float = 5.0) -> List[Dict[str, Any]]:
        """
        Fast parallel port scan using ThreadPoolExecutor
        Scans multiple subnets and Bambu-specific ports
        """
        discovered = []
        
        try:
            # Get all local network interfaces
            subnets_to_scan = set()
            
            # Get local IP and its subnet
            try:
                local_ip = socket.gethostbyname(socket.gethostname())
                subnets_to_scan.add(".".join(local_ip.split(".")[:3]))
            except:
                pass
            
            # Add known printer subnet if configured
            if self._known_printer_ip:
                known_subnet = ".".join(self._known_printer_ip.split(".")[:3])
                subnets_to_scan.add(known_subnet)
            
            # Common home network subnets
            subnets_to_scan.add("192.168.1")
            subnets_to_scan.add("192.168.0")
            subnets_to_scan.add("192.168.4")  # Your printer's subnet
            subnets_to_scan.add("10.0.0")
            
            logger.info(f"Scanning subnets: {list(subnets_to_scan)}")
            
            # Bambu Lab specific ports: MQTT(8883), Control(6000), FTP(990)
            bambu_ports = self.BAMBU_PORTS
            
            # IP ranges to scan (common DHCP ranges)
            ip_ranges = list(range(2, 50)) + list(range(100, 255))
            
            def check_ip(ip: str) -> Optional[Dict]:
                """Check single IP for Bambu Lab printer"""
                for port in bambu_ports:
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(self._scan_timeout)
                        result = sock.connect_ex((ip, port))
                        sock.close()
                        
                        if result == 0:
                            return {
                                "printer_id": f"BAMBU_{ip.replace('.', '_')}",
                                "printer_name": f"Bambu Lab at {ip}",
                                "ip_address": ip,
                                "port": port,
                                "mqtt_port": 8883,
                                "ftp_port": 990,
                                "discovery_method": "port_scan"
                            }
                    except:
                        pass
                return None
            
            # Build list of all IPs to scan
            all_ips = []
            for subnet in subnets_to_scan:
                for i in ip_ranges:
                    all_ips.append(f"{subnet}.{i}")
            
            logger.info(f"Scanning {len(all_ips)} IP addresses...")
            
            # Parallel scan with max 100 workers for speed
            with ThreadPoolExecutor(max_workers=100) as executor:
                futures = {executor.submit(check_ip, ip): ip for ip in all_ips}
                
                start = time.time()
                for future in as_completed(futures, timeout=max_time):
                    if time.time() - start > max_time:
                        break
                    try:
                        result = future.result(timeout=0.1)
                        if result:
                            discovered.append(result)
                            logger.info(f"Found device at {result['ip_address']}")
                    except:
                        pass
                        
        except Exception as e:
            logger.warning(f"Parallel scan error: {e}")
        
        return discovered

    def discover_by_ip(self, ip_address: str, check_status: bool = True) -> Optional[Dict[str, Any]]:
        """
        Try to discover printer at specific IP address
        Also checks real-time status via MQTT if access_code is configured
        
        Args:
            ip_address: IP to check
            check_status: Whether to also check MQTT status
            
        Returns:
            Printer info if found, None otherwise
        """
        logger.info(f"Checking for printer at {ip_address}...")
        
        # Bambu Lab specific ports: 8883 (MQTT), 6000 (control), 990 (FTP)
        bambu_ports = self.BAMBU_PORTS
        
        for port in bambu_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2.0)
                result = sock.connect_ex((ip_address, port))
                sock.close()
                
                if result == 0:
                    # Get config values
                    access_code = os.getenv("BAMBU_ACCESS_CODE", "")
                    printer_id = os.getenv("BAMBU_PRINTER_ID", "")
                    
                    printer = {
                        "printer_id": printer_id or f"BAMBU_{ip_address.replace('.', '_')}",
                        "printer_name": f"Bambu Lab at {ip_address}",
                        "ip_address": ip_address,
                        "port": port,
                        "mqtt_port": 8883,
                        "ftp_port": 990,
                        "discovery_method": "manual",
                        "status": "offline",  # Default
                        "mqtt_connected": False
                    }
                    
                    # Check real-time status via MQTT if access_code is available
                    if check_status and access_code:
                        logger.info(f"Checking MQTT status for {ip_address}...")
                        mqtt_status = check_mqtt_status(ip_address, access_code, printer_id, timeout=5.0)
                        
                        printer["status"] = mqtt_status.get("status", "offline")
                        printer["mqtt_connected"] = mqtt_status.get("mqtt_connected", False)
                        printer["printing"] = mqtt_status.get("printing", False)
                        printer["progress"] = mqtt_status.get("progress", 0)
                        
                        if mqtt_status.get("online"):
                            logger.info(f"Printer is ONLINE: status={printer['status']}")
                    
                    self.discovered_printers[printer["printer_id"]] = printer
                    logger.info(f"Found Bambu Lab printer at {ip_address}:{port} - status: {printer['status']}")
                    return printer
            except Exception as e:
                logger.debug(f"Error checking {ip_address}:{port} - {e}")
        
        logger.warning(f"No printer found at {ip_address}")
        return None

    def discover_async(self, callback=None):
        """Start async discovery in background thread"""
        def _discover():
            try:
                self.is_discovering = True
                printers = self.scan_network()
                self.discovered_printers = {p["printer_id"]: p for p in printers}
                
                if callback:
                    callback(printers)
                    
            except Exception as e:
                logger.error(f"Async discovery error: {str(e)}")
            finally:
                self.is_discovering = False
        
        self.discovery_thread = threading.Thread(target=_discover, daemon=True)
        self.discovery_thread.start()
        return {"status": "discovery_started", "is_discovering": True}

    def get_discovered_printers(self) -> List[Dict[str, Any]]:
        """Get list of previously discovered printers"""
        return list(self.discovered_printers.values())

    def get_discovery_status(self) -> Dict[str, Any]:
        """Get current discovery status"""
        return {
            "is_discovering": self.is_discovering,
            "printers_found": len(self.discovered_printers),
            "printers": list(self.discovered_printers.values())
        }

    def clear_discovered(self):
        """Clear discovered printers list"""
        self.discovered_printers = {}


# Global discovery service instance
discovery_service = PrinterDiscoveryService()
