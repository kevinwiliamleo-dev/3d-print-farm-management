"""
Scheduled background cleanup service.
Reuses the existing helper functions from scripts/cleanup.py and runs them
periodically (default: every 24 hours) inside the FastAPI event-loop.
"""

import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta

from src.config import (
    UPLOAD_DIR,
    GCODE_DIR,
    QUEUE_FILES_DIR,
    OUTPUT_DIR,
    LOG_DIR,
    DATA_DIR,
)

logger = logging.getLogger(__name__)

# --------------- configuration (env-overridable via config.py) ---------------
import os

CLEANUP_INTERVAL_HOURS = int(os.getenv("CLEANUP_INTERVAL_HOURS", 24))
CLEANUP_GCODE_DAYS = int(os.getenv("CLEANUP_GCODE_DAYS", 30))
CLEANUP_LOG_DAYS = int(os.getenv("CLEANUP_LOG_DAYS", 7))
CLEANUP_UPLOAD_DAYS = int(os.getenv("CLEANUP_UPLOAD_DAYS", 14))
CLEANUP_OUTPUT_DAYS = int(os.getenv("CLEANUP_OUTPUT_DAYS", 14))

# --------------- low-level helpers (sync, run in executor) -------------------


def _remove_old_files(directory: Path, extensions: list[str], days: int) -> int:
    """Delete files matching *extensions* older than *days*. Returns count."""
    if not directory.exists():
        return 0
    cutoff = datetime.now() - timedelta(days=days)
    count = 0
    for ext in extensions:
        for fp in directory.glob(f"*{ext}"):
            if fp.is_file() and datetime.fromtimestamp(fp.stat().st_mtime) < cutoff:
                try:
                    fp.unlink()
                    logger.info("🗑️ Deleted old file: %s", fp.name)
                    count += 1
                except Exception as exc:
                    logger.warning("Failed to delete %s: %s", fp.name, exc)
    return count


def _remove_temp_files(directory: Path, pattern: str = "tmp*") -> int:
    if not directory.exists():
        return 0
    count = 0
    for fp in directory.glob(pattern):
        if fp.is_file():
            try:
                fp.unlink()
                logger.info("🗑️ Deleted temp file: %s", fp.name)
                count += 1
            except Exception as exc:
                logger.warning("Failed to delete %s: %s", fp.name, exc)
    return count


def run_cleanup() -> dict:
    """Execute all cleanup tasks (synchronous). Returns summary dict."""
    summary: dict[str, int] = {}

    summary["temp_files"] = _remove_temp_files(UPLOAD_DIR)

    summary["old_gcode"] = _remove_old_files(
        GCODE_DIR, [".gcode", ".g"], CLEANUP_GCODE_DAYS
    )

    summary["old_logs"] = _remove_old_files(
        LOG_DIR, [".log"], CLEANUP_LOG_DAYS
    )

    summary["old_uploads"] = _remove_old_files(
        UPLOAD_DIR, [".3mf", ".stl", ".gcode"], CLEANUP_UPLOAD_DAYS
    )

    summary["old_output"] = _remove_old_files(
        OUTPUT_DIR, [".3mf", ".gcode"], CLEANUP_OUTPUT_DAYS
    )

    total = sum(summary.values())
    if total:
        logger.info("🧹 Cleanup finished – removed %d files %s", total, summary)
    else:
        logger.debug("🧹 Cleanup finished – nothing to remove")
    return summary


# --------------- async background loop ---------------------------------------

_cleanup_task: asyncio.Task | None = None


async def _cleanup_loop() -> None:
    """Periodically run cleanup inside the running event-loop."""
    interval = CLEANUP_INTERVAL_HOURS * 3600
    logger.info(
        "🧹 Cleanup scheduler started (every %dh, gcode=%dd, logs=%dd, uploads=%dd)",
        CLEANUP_INTERVAL_HOURS,
        CLEANUP_GCODE_DAYS,
        CLEANUP_LOG_DAYS,
        CLEANUP_UPLOAD_DAYS,
    )
    # Run once at startup, then repeat at interval
    while True:
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, run_cleanup)
        except Exception as exc:
            logger.error("Cleanup error: %s", exc)
        await asyncio.sleep(interval)


def start_cleanup_scheduler() -> None:
    """Start the background cleanup task. Call from lifespan startup."""
    global _cleanup_task
    if _cleanup_task is None or _cleanup_task.done():
        _cleanup_task = asyncio.create_task(_cleanup_loop())
        logger.info("🧹 Cleanup background task created")


def stop_cleanup_scheduler() -> None:
    """Cancel the background cleanup task. Call from lifespan shutdown."""
    global _cleanup_task
    if _cleanup_task and not _cleanup_task.done():
        _cleanup_task.cancel()
        logger.info("🧹 Cleanup background task cancelled")
    _cleanup_task = None
