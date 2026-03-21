"""
Utility functions for model file validation and cleanup
"""
import os
import logging
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)


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
