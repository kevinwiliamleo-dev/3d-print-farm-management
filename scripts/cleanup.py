"""
Cleanup utility for 3D Print Farm Management System
Removes temporary files and performs maintenance tasks
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import shutil
import argparse

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))


def cleanup_temp_files(uploads_dir: Path, pattern: str = "tmp*", dry_run: bool = False) -> int:
    """
    Remove temporary files from uploads directory
    
    Args:
        uploads_dir: Path to uploads directory
        pattern: Glob pattern for temp files
        dry_run: If True, only print what would be deleted
        
    Returns:
        Number of files removed
    """
    if not uploads_dir.exists():
        print(f"Directory not found: {uploads_dir}")
        return 0
    
    temp_files = list(uploads_dir.glob(pattern))
    count = 0
    
    for file_path in temp_files:
        if file_path.is_file():
            if dry_run:
                print(f"[DRY RUN] Would delete: {file_path.name}")
            else:
                try:
                    file_path.unlink()
                    print(f"Deleted: {file_path.name}")
                    count += 1
                except Exception as e:
                    print(f"Failed to delete {file_path.name}: {e}")
    
    return count


def cleanup_old_gcode(gcode_dir: Path, days: int = 30, dry_run: bool = False) -> int:
    """
    Remove G-code files older than specified days
    
    Args:
        gcode_dir: Path to gcode directory
        days: Files older than this will be deleted
        dry_run: If True, only print what would be deleted
        
    Returns:
        Number of files removed
    """
    if not gcode_dir.exists():
        print(f"Directory not found: {gcode_dir}")
        return 0
    
    cutoff_date = datetime.now() - timedelta(days=days)
    gcode_files = list(gcode_dir.glob("*.gcode")) + list(gcode_dir.glob("*.g"))
    count = 0
    
    for file_path in gcode_files:
        if file_path.is_file():
            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_mtime < cutoff_date:
                if dry_run:
                    print(f"[DRY RUN] Would delete (older than {days} days): {file_path.name}")
                else:
                    try:
                        file_path.unlink()
                        print(f"Deleted old G-code: {file_path.name}")
                        count += 1
                    except Exception as e:
                        print(f"Failed to delete {file_path.name}: {e}")
    
    return count


def cleanup_logs(logs_dir: Path, days: int = 7, dry_run: bool = False) -> int:
    """
    Remove log files older than specified days
    
    Args:
        logs_dir: Path to logs directory
        days: Files older than this will be deleted
        dry_run: If True, only print what would be deleted
        
    Returns:
        Number of files removed
    """
    if not logs_dir.exists():
        print(f"Directory not found: {logs_dir}")
        return 0
    
    cutoff_date = datetime.now() - timedelta(days=days)
    log_files = list(logs_dir.glob("*.log"))
    count = 0
    
    for file_path in log_files:
        if file_path.is_file():
            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_mtime < cutoff_date:
                if dry_run:
                    print(f"[DRY RUN] Would delete (older than {days} days): {file_path.name}")
                else:
                    try:
                        file_path.unlink()
                        print(f"Deleted old log: {file_path.name}")
                        count += 1
                    except Exception as e:
                        print(f"Failed to delete {file_path.name}: {e}")
    
    return count


def get_disk_usage(path: Path) -> dict:
    """Get disk usage information"""
    total, used, free = shutil.disk_usage(path)
    return {
        "total_gb": total / (1024**3),
        "used_gb": used / (1024**3),
        "free_gb": free / (1024**3),
        "percent_used": (used / total) * 100
    }


def main():
    parser = argparse.ArgumentParser(
        description="Cleanup utility for 3D Print Farm Management System"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    parser.add_argument(
        "--temp-only",
        action="store_true",
        help="Only clean temporary files in uploads"
    )
    parser.add_argument(
        "--gcode-days",
        type=int,
        default=30,
        help="Delete G-code files older than this many days (default: 30)"
    )
    parser.add_argument(
        "--log-days",
        type=int,
        default=7,
        help="Delete log files older than this many days (default: 7)"
    )
    
    args = parser.parse_args()
    
    # Define directories
    data_dir = BASE_DIR / "data"
    uploads_dir = data_dir / "uploads"
    gcode_dir = data_dir / "gcode"
    logs_dir = BASE_DIR / "logs"
    
    print("=" * 50)
    print("🧹 3D Print Farm Cleanup Utility")
    print("=" * 50)
    
    if args.dry_run:
        print("⚠️  DRY RUN MODE - No files will be deleted\n")
    
    # Show disk usage
    disk_info = get_disk_usage(BASE_DIR)
    print(f"💾 Disk Usage: {disk_info['used_gb']:.1f} GB / {disk_info['total_gb']:.1f} GB ({disk_info['percent_used']:.1f}%)")
    print(f"   Free space: {disk_info['free_gb']:.1f} GB\n")
    
    total_cleaned = 0
    
    # Clean temporary files
    print("📁 Cleaning temporary files in uploads...")
    temp_count = cleanup_temp_files(uploads_dir, "tmp*", args.dry_run)
    total_cleaned += temp_count
    print(f"   {'Would remove' if args.dry_run else 'Removed'}: {temp_count} temp files\n")
    
    if not args.temp_only:
        # Clean old G-code files
        print(f"📁 Cleaning G-code files older than {args.gcode_days} days...")
        gcode_count = cleanup_old_gcode(gcode_dir, args.gcode_days, args.dry_run)
        total_cleaned += gcode_count
        print(f"   {'Would remove' if args.dry_run else 'Removed'}: {gcode_count} G-code files\n")
        
        # Clean old log files
        print(f"📁 Cleaning log files older than {args.log_days} days...")
        log_count = cleanup_logs(logs_dir, args.log_days, args.dry_run)
        total_cleaned += log_count
        print(f"   {'Would remove' if args.dry_run else 'Removed'}: {log_count} log files\n")
    
    print("=" * 50)
    print(f"✅ Total files {'would be cleaned' if args.dry_run else 'cleaned'}: {total_cleaned}")
    print("=" * 50)


if __name__ == "__main__":
    main()
