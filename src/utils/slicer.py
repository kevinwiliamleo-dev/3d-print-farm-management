"""
Utility functions for OrcaSlicer integration and file handling
"""
import subprocess
import os
import logging
from pathlib import Path
from typing import Dict, Tuple

from src.config import (
    ORCA_SLICER_PATH,
    DEFAULT_PRINTER_PROFILE,
    SLICING_TIMEOUT_SECONDS,
    GCODE_DIR,
)

logger = logging.getLogger(__name__)


class OrcaSlicerManager:
    """Manages OrcaSlicer CLI operations for automated slicing"""

    def __init__(self, orca_path: str = ORCA_SLICER_PATH):
        self.orca_path = orca_path
        self.printer_profile = DEFAULT_PRINTER_PROFILE
        self.timeout = SLICING_TIMEOUT_SECONDS

    def check_orca_installed(self) -> bool:
        """
        Check if OrcaSlicer is installed and accessible
        Returns: True if OrcaSlicer is available, False otherwise
        """
        try:
            result = subprocess.run(
                [self.orca_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except FileNotFoundError:
            logger.error(f"OrcaSlicer not found at: {self.orca_path}")
            return False
        except Exception as e:
            logger.error(f"Error checking OrcaSlicer: {str(e)}")
            return False

    def slice_model(
        self,
        input_file: str,
        layer_height: float = 0.2,
        infill_density: int = 15,
        support_enabled: bool = False,
    ) -> Tuple[bool, Dict[str, any]]:
        """
        Slice a model file using OrcaSlicer CLI

        Args:
            input_file: Path to .3mf or .stl file
            layer_height: Layer height in mm (default 0.2)
            infill_density: Infill percentage 0-100 (default 15)
            support_enabled: Enable supports (default False)

        Returns:
            Tuple of (success: bool, result: dict)
            result includes: output_gcode, gcode_size_mb, error_message
        """
        try:
            # Validate input file exists
            if not os.path.exists(input_file):
                return False, {"error_message": f"Input file not found: {input_file}"}

            # Generate output filename
            input_name = Path(input_file).stem
            output_gcode = str(GCODE_DIR / f"{input_name}.gcode")

            # Build command
            cmd = [
                self.orca_path,
                "--slice",
                input_file,
                "--printer", self.printer_profile,
                "--layer-height", str(layer_height),
                "--infill-density", str(infill_density),
            ]

            if support_enabled:
                cmd.append("--support-enable")

            cmd.extend(["--output", output_gcode])

            logger.info(f"Starting slicing: {input_file}")
            logger.debug(f"Command: {' '.join(cmd)}")

            # Run slicing
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            if result.returncode != 0:
                error_msg = result.stderr or "Unknown error"
                logger.error(f"Slicing failed: {error_msg}")
                return False, {"error_message": error_msg}

            # Check if output file was created
            if not os.path.exists(output_gcode):
                return False, {"error_message": "Output G-code file not created"}

            # Get file size
            gcode_size_mb = os.path.getsize(output_gcode) / (1024 * 1024)

            logger.info(f"Slicing successful: {output_gcode} ({gcode_size_mb:.2f} MB)")

            return True, {
                "output_gcode": output_gcode,
                "gcode_size_mb": round(gcode_size_mb, 2),
                "message": f"Slicing complete: {gcode_size_mb:.2f}MB",
            }

        except subprocess.TimeoutExpired:
            error_msg = f"Slicing timeout (exceeded {self.timeout}s)"
            logger.error(error_msg)
            return False, {"error_message": error_msg}
        except Exception as e:
            error_msg = f"Slicing error: {str(e)}"
            logger.error(error_msg)
            return False, {"error_message": error_msg}

    def get_profiles(self) -> list:
        """
        Get list of available printer profiles
        Returns: List of profile names
        """
        try:
            result = subprocess.run(
                [self.orca_path, "--list-profiles"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                profiles = result.stdout.strip().split("\n")
                return profiles
            return []
        except Exception as e:
            logger.error(f"Error getting profiles: {str(e)}")
            return []


def validate_model_file(file_path: str) -> Tuple[bool, str]:
    """
    Validate that a file is a valid model file (.3mf or .stl)

    Args:
        file_path: Path to file

    Returns:
        Tuple of (is_valid: bool, message: str)
    """
    valid_extensions = [".3mf", ".stl"]
    file_ext = Path(file_path).suffix.lower()

    if file_ext not in valid_extensions:
        return False, f"Invalid file type: {file_ext}. Allowed: {', '.join(valid_extensions)}"

    if not os.path.exists(file_path):
        return False, f"File not found: {file_path}"

    # Check file size (max 500MB by default from config)
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    from src.config import MAX_UPLOAD_SIZE_MB

    if file_size_mb > MAX_UPLOAD_SIZE_MB:
        return False, f"File too large: {file_size_mb:.2f}MB (max {MAX_UPLOAD_SIZE_MB}MB)"

    return True, "File is valid"


def cleanup_temp_file(file_path: str) -> bool:
    """
    Delete a temporary file safely

    Args:
        file_path: Path to file to delete

    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Deleted temporary file: {file_path}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        return False
