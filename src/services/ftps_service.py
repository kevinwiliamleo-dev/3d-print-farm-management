"""
Direct FTPS Upload Service for Bambu Lab Printers
Enables uploading files directly to printer SD card without HTTP server
Based on OctoPrint-BambuPrinter plugin implementation
"""
import ftplib
import ssl
import socket
import logging
import os
from typing import Optional, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


class ImplicitTLS(ftplib.FTP_TLS):
    """ftplib.FTP_TLS sub-class to support implicit SSL FTPS (like Bambu printers)"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sock = None

    @property
    def sock(self):
        """return socket"""
        return self._sock

    @sock.setter
    def sock(self, value):
        """wrap and set SSL socket"""
        if value is not None and not isinstance(value, ssl.SSLSocket):
            value = self.context.wrap_socket(value)
        self._sock = value

    def ntransfercmd(self, cmd, rest=None):
        conn, size = ftplib.FTP.ntransfercmd(self, cmd, rest)

        if self._prot_p:
            conn = self.context.wrap_socket(
                conn, server_hostname=self.host, session=self.sock.session
            )
        return conn, size


class SimpleFTPSClient:
    """Simple FTPS client using implicit SSL for Bambu Lab printers"""
    
    BAMBU_USERNAME = "bblp"
    BAMBU_FTPS_PORT = 990
    CHUNK_SIZE = 65536
    
    def __init__(self, host: str, access_code: str, port: int = 990, timeout: int = 30):
        """Initialize FTPS client"""
        self.host = host
        self.access_code = access_code
        self.port = port
        self.timeout = timeout
        self.ftp = None
        self.connected = False
    
    def connect(self) -> bool:
        """Connect to printer FTPS server with implicit SSL"""
        try:
            logger.info(f"📋 Connecting to FTPS: {self.host}:{self.port} (implicit SSL)")
            
            # Create implicit TLS FTP connection
            self.ftp = ImplicitTLS()
            self.ftp.set_debuglevel(0)
            
            # Connect with implicit SSL on port 990
            self.ftp.connect(host=self.host, port=self.port, timeout=self.timeout)
            logger.info(f"📋 Welcome: {self.ftp.welcome.strip()}")
            
            # Login
            self.ftp.login(user=self.BAMBU_USERNAME, passwd=self.access_code)
            logger.info(f"✅ FTPS authenticated as {self.BAMBU_USERNAME}")
            
            # Set up protection level for data connection
            self.ftp.prot_p()
            
            self.connected = True
            return True
                
        except Exception as e:
            logger.error(f"❌ Connection error: {e}")
            import traceback
            traceback.print_exc()
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from FTPS server"""
        try:
            if self.ftp:
                self.ftp.quit()
                self.connected = False
                logger.info("📋 FTPS disconnected")
        except Exception as e:
            logger.warning(f"Disconnect error: {e}")
            try:
                if self.ftp:
                    self.ftp.close()
            except:
                pass
    
    def delete_file(self, remote_filename: str) -> bool:
        """Delete file from printer"""
        try:
            if not self.connected:
                if not self.connect():
                    return False
            
            # Determine location
            location = "cache directory" if remote_filename.startswith("cache/") else "root directory"
            logger.info(f"🗑️ Deleting file from {location}: {remote_filename}")
            self.ftp.delete(remote_filename)
            logger.info(f"✅ Successfully deleted from SD card ({location}): {remote_filename}")
            return True
                
        except Exception as e:
            logger.error(f"❌ Delete error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def list_files(self, path: str = "") -> list:
        """List files on printer"""
        try:
            if not self.connected:
                if not self.connect():
                    return []
            
            logger.info(f"📋 Listing files in: {path or 'root'}")
            files = self.ftp.nlst(path) if path else self.ftp.nlst(".")
            logger.info(f"✅ Found {len(files)} files: {files}")
            return files
                
        except Exception as e:
            logger.error(f"❌ List error: {e}")
            return []
    
    def upload_file(
        self,
        local_path: str,
        remote_filename: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> bool:
        """
        Upload file to printer using EXACT OctoPrint-BambuPrinter implementation
        Uses transfercmd with context manager for proper SSL handling
        """
        try:
            if not self.connected:
                if not self.connect():
                    return False
            
            # Get file size
            file_size = os.path.getsize(local_path)
            logger.info(f"📤 Uploading {local_path} ({file_size} bytes) as {remote_filename}")
            
            # Dynamic block size based on file size
            block_size = max(file_size // 100, 8192)
            rest = None
            
            # EXACT OctoPrint-BambuPrinter implementation
            with open(local_path, "rb") as fp:
                # Set binary mode explicitly
                self.ftp.voidcmd("TYPE I")
                
                # Use transfercmd WITH context manager (THIS IS THE FIX!)
                with self.ftp.transfercmd(f"STOR {remote_filename}", rest) as conn:
                    bytes_sent = 0
                    
                    while True:
                        buf = fp.read(block_size)
                        if not buf:
                            break
                        
                        conn.sendall(buf)
                        bytes_sent += len(buf)
                        
                        if progress_callback:
                            progress_callback(bytes_sent, file_size)
                    
                    # Shutdown SSL layer properly
                    # This is critical for Bambu printers' FTPS implementation
                    if ftplib._SSLSocket is not None and isinstance(conn, ftplib._SSLSocket):
                        # Check FTP server type
                        if "vsFTPd" in self.ftp.welcome:
                            conn.unwrap()
                        else:
                            conn.shutdown(socket.SHUT_RDWR)
            
            logger.info(f"✅ Upload successful: {remote_filename} ({file_size} bytes sent)")
            return True
                
        except Exception as e:
            logger.error(f"❌ Upload error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def __enter__(self):
        """Context manager"""
        self.connect()
        return self
    
    def __exit__(self, *args):
        """Context manager"""
        self.disconnect()


class BambuFTPSClient:
    """FTPS client wrapper for Bambu Lab printers"""
    
    def __init__(self, host: str, access_code: str, port: int = 990, timeout: int = 30):
        """Initialize"""
        self.client = SimpleFTPSClient(host, access_code, port, timeout)
        self.host = host
        self.access_code = access_code
        self.port = port
        self.timeout = timeout
        self.connected = False
    
    def connect(self) -> bool:
        """Connect to printer"""
        return self.client.connect()
    
    def disconnect(self):
        """Disconnect from printer"""
        self.client.disconnect()
    
    def upload_file(
        self,
        local_path: str,
        remote_filename: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> bool:
        """Upload file"""
        return self.client.upload_file(local_path, remote_filename, progress_callback)
    
    def list_files(self, path: str = "") -> list:
        """List files on printer SD card with detailed info (includes cache directory)"""
        try:
            if not self.client.connected:
                if not self.client.connect():
                    return []
            
            file_objects = []
            
            # List root directory files
            try:
                root_files = self.client.ftp.nlst()
            except Exception as e:
                logger.error(f"Error listing root files: {e}")
                root_files = []
            
            logger.info(f"📋 Listed {len(root_files)} items in root")
            
            # Process root files
            for name in root_files:
                # Skip directories
                if name in ['logger', 'recorder', 'cache', 'model', 'image', 'ipcam', 'timelapse']:
                    continue
                
                # Only include 3mf and gcode files
                if not (name.lower().endswith('.3mf') or name.lower().endswith(('.gcode', '.g'))):
                    continue
                
                # Get file size
                try:
                    size = self.client.ftp.size(name)
                except:
                    size = 0
                
                file_objects.append(PrinterFileInfo(name=name, size=size or 0, path="root"))
            
            # List cache directory files
            try:
                cache_files = self.client.ftp.nlst("cache")
                logger.info(f"📂 Listed {len(cache_files)} items in cache")
                
                for name in cache_files:
                    # Skip if it's just "cache" itself
                    if name == "cache":
                        continue
                    
                    # Only include 3mf and gcode files
                    if not (name.lower().endswith('.3mf') or name.lower().endswith(('.gcode', '.g'))):
                        continue
                    
                    # Get file size
                    try:
                        size = self.client.ftp.size(f"cache/{name}")
                    except:
                        size = 0
                    
                    file_objects.append(PrinterFileInfo(name=name, size=size or 0, path="cache"))
            except Exception as e:
                logger.warning(f"Could not list cache directory: {e}")
            
            logger.info(f"✅ Found {len(file_objects)} printable files total")
            return file_objects
            
        except Exception as e:
            logger.error(f"❌ List files error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def delete_file(self, remote_filename: str) -> bool:
        """Delete file from printer"""
        return self.client.delete_file(remote_filename)
    
    def __enter__(self):
        """Context manager"""
        self.connect()
        return self
    
    def __exit__(self, *args):
        """Context manager"""
        self.disconnect()


class PrinterFileInfo:
    """File information from printer"""
    def __init__(self, name: str, size: int = 0, modified: str = "", path: str = "root"):
        self.name = name
        self.size = size
        self.modified = modified
        self.path = path  # "root" or "cache"
    
    def to_dict(self):
        return {
            "name": self.name,
            "size": self.size,
            "modified": self.modified,
            "path": self.path,
            "full_path": f"{self.path}/{self.name}" if self.path != "root" else self.name,
            "is_3mf": self.name.lower().endswith(".3mf"),
            "is_gcode": self.name.lower().endswith((".gcode", ".g")),
            "size_mb": round(self.size / (1024*1024), 2) if self.size else 0
        }


class BambuDirectUploadService:
    """High-level service for direct SD card uploads"""
    
    def __init__(self, printer_ip: str, access_code: str):
        """Initialize upload service"""
        self.printer_ip = printer_ip
        self.access_code = access_code
    
    def upload_to_sd(
        self,
        file_path: str,
        remote_name: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> bool:
        """
        Upload file directly to printer SD card
        
        Args:
            file_path: Local file path
            remote_name: Name for file on printer (defaults to basename)
            progress_callback: Optional progress callback
            
        Returns:
            True if successful
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return False
            
            remote_name = remote_name or Path(file_path).name
            
            with BambuFTPSClient(self.printer_ip, self.access_code) as client:
                return client.upload_file(file_path, remote_name, progress_callback)
                
        except Exception as e:
            logger.error(f"Direct upload error: {e}")
            import traceback
            traceback.print_exc()
            return False