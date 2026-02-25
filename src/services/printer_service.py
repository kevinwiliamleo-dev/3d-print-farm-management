"""
Printer Service - Manage printer status and control
Follows naming conventions from README.md
"""
from datetime import datetime
from sqlalchemy.orm import Session
from src.database.db import Printer
from src.models.schemas import PrinterCreate, PrinterResponse
import logging

logger = logging.getLogger(__name__)


class PrinterService:
    """Service for managing printers"""

    def __init__(self, db: Session):
        self.db = db

    def create_printer(self, printer_id: str, printer_name: str, serial_number: str = None) -> dict:
        """
        Register new printer
        
        Args:
            printer_id: Unique printer identifier (database FK)
            printer_name: Display name for printer
            serial_number: Actual Bambu serial for MQTT topics (e.g. '03900D5A2402051')
            
        Returns:
            Printer details
        """
        # Check if printer already exists
        existing = self.db.query(Printer).filter(Printer.printer_id == printer_id).first()
        if existing:
            logger.warning(f"Printer already exists: printer_id={printer_id}")
            return None
        
        # Create printer_id entry
        printer_record = Printer(
            printer_id=printer_id,
            printer_name=printer_name,
            serial_number=serial_number,
            status="offline",
            mqtt_connected=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db.add(printer_record)
        self.db.commit()
        self.db.refresh(printer_record)
        
        logger.info(f"Created printer: printer_id={printer_id}, serial={serial_number}, printer_name={printer_name}")
        
        return {
            "printer_id": printer_record.printer_id,
            "printer_name": printer_record.printer_name,
            "serial_number": printer_record.serial_number,
            "status": printer_record.status,
            "mqtt_connected": printer_record.mqtt_connected,
            "auto_continue": printer_record.auto_continue
        }

    def get_printer_by_id(self, printer_id: str) -> dict:
        """Get printer details by printer_id"""
        printer = self.db.query(Printer).filter(Printer.printer_id == printer_id).first()
        if not printer:
            return None
        
        return {
            "printer_id": printer.printer_id or "",
            "printer_name": printer.printer_name or "Unknown Printer",
            "status": printer.status or "offline",
            "mqtt_connected": printer.mqtt_connected or False,
            "auto_continue": printer.auto_continue or False,
            "nozzle_temp": printer.nozzle_temp or 0.0,
            "nozzle_target_temp": printer.nozzle_target_temp or 0.0,
            "bed_temp": printer.bed_temp or 0.0,
            "bed_target_temp": printer.bed_target_temp or 0.0,
            "print_progress": printer.print_progress or 0,
            "remaining_time": printer.remaining_time or 0,
            "current_file": printer.current_file or "",
            "print_error": printer.print_error or "",
            "model": printer.model or "",
            "printer_ip": printer.printer_ip or "",
            "created_at": printer.created_at,
            "updated_at": printer.updated_at
        }


    def get_all_printers(self) -> list:
        """Get all registered printers"""
        printers = self.db.query(Printer).all()
        return [
            {
                "printer_id": p.printer_id or "",
                "printer_name": p.printer_name or "Unknown Printer",
                "status": p.status or "offline",
                "mqtt_connected": p.mqtt_connected or False,
                "auto_continue": p.auto_continue or False,
                "nozzle_temp": p.nozzle_temp or 0.0,
                "nozzle_target_temp": p.nozzle_target_temp or 0.0,
                "bed_temp": p.bed_temp or 0.0,
                "bed_target_temp": p.bed_target_temp or 0.0,
                "print_progress": p.print_progress or 0,
                "remaining_time": p.remaining_time or 0,
                "current_file": p.current_file or "",
                "print_error": p.print_error or "",
                "model": p.model or "",
                "printer_ip": p.printer_ip or ""
            }
            for p in printers
        ]

    def update_printer_status(self, printer_id: str, printer_status: str) -> bool:
        """
        Update printer_status for given printer_id
        
        Status values: idle, printing, offline
        """
        printer = self.db.query(Printer).filter(Printer.printer_id == printer_id).first()
        if not printer:
            return False
        
        printer.status = printer_status
        printer.updated_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Updated printer_status: printer_id={printer_id}, status={printer_status}")
        return True

    def update_mqtt_connection(self, printer_id: str, mqtt_connected: bool) -> bool:
        """Update mqtt_connected status for printer"""
        printer = self.db.query(Printer).filter(Printer.printer_id == printer_id).first()
        if not printer:
            return False
        
        printer.mqtt_connected = mqtt_connected
        printer.updated_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Updated mqtt_connected: printer_id={printer_id}, mqtt_connected={mqtt_connected}")
        return True

    def is_printer_online(self, printer_id: str) -> bool:
        """Check if printer is online (mqtt_connected and not offline)"""
        printer = self.db.query(Printer).filter(Printer.printer_id == printer_id).first()
        if not printer:
            return False
        
        return printer.mqtt_connected and printer.status != "offline"

    def is_printer_idle(self, printer_id: str) -> bool:
        """Check if printer is idle and ready for printing"""
        printer = self.db.query(Printer).filter(Printer.printer_id == printer_id).first()
        if not printer:
            return False
        
        return printer.status == "idle" and printer.mqtt_connected

    def set_printer_idle(self, printer_id: str) -> bool:
        """Set printer to idle status"""
        return self.update_printer_status(printer_id, "idle")

    def set_printer_printing(self, printer_id: str) -> bool:
        """Set printer to printing status"""
        return self.update_printer_status(printer_id, "printing")

    def set_printer_offline(self, printer_id: str) -> bool:
        """Set printer to offline status"""
        return self.update_printer_status(printer_id, "offline")

    def delete_printer(self, printer_id: str) -> bool:
        """Delete printer registration"""
        printer = self.db.query(Printer).filter(Printer.printer_id == printer_id).first()
        if not printer:
            return False
        
        self.db.delete(printer)
        self.db.commit()
        
        logger.info(f"Deleted printer: printer_id={printer_id}")
        return True
