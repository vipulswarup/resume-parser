#!/usr/bin/env python3
"""
Standalone script for log cleanup and rotation
Can be run as a cron job for automatic log management
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.logging_config import cleanup_old_logs, rotate_logs, get_log_stats
import argparse
from datetime import datetime, timedelta

def main():
    parser = argparse.ArgumentParser(description="Log management utility")
    parser.add_argument("--cleanup", action="store_true", help="Clean up old logs")
    parser.add_argument("--rotate", action="store_true", help="Rotate current logs")
    parser.add_argument("--stats", action="store_true", help="Show log statistics")
    parser.add_argument("--retention-days", type=int, default=180, help="Days to retain logs (default: 180)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without actually deleting")
    
    args = parser.parse_args()
    
    if args.stats:
        print("=== Log Statistics ===")
        stats = get_log_stats()
        if "error" in stats:
            print(f"Error: {stats['error']}")
        else:
            print(f"Total files: {stats['total_files']}")
            print(f"Total size: {stats['total_size_mb']} MB")
            print("\nFile details:")
            for file_info in stats['files']:
                if 'error' in file_info:
                    print(f"  {file_info['filename']}: ERROR - {file_info['error']}")
                else:
                    print(f"  {file_info['filename']}: {file_info['size_mb']} MB, {file_info['age_days']} days old")
    
    if args.cleanup:
        print(f"\n=== Log Cleanup (retention: {args.retention_days} days) ===")
        if args.dry_run:
            print("DRY RUN - No files will be deleted")
            # For dry run, we'd need to modify cleanup_old_logs to support this
            # For now, just show what would be cleaned
            stats = get_log_stats()
            cutoff_date = datetime.now() - timedelta(days=args.retention_days)
            old_files = [f for f in stats['files'] if f.get('age_days', 0) > args.retention_days]
            if old_files:
                print(f"Files that would be deleted: {len(old_files)}")
                for file_info in old_files:
                    print(f"  {file_info['filename']} ({file_info['age_days']} days old)")
            else:
                print("No old files found for cleanup")
        else:
            result = cleanup_old_logs(args.retention_days)
            print(f"Cleanup completed: {result['files_count']} files deleted, {result['size_freed_mb']} MB freed")
    
    if args.rotate:
        print("\n=== Log Rotation ===")
        result = rotate_logs()
        if result['rotated_files']:
            print(f"Rotation completed: {len(result['rotated_files'])} files rotated")
            for file in result['rotated_files']:
                print(f"  {file}")
        else:
            print("No files rotated")
    
    if not any([args.cleanup, args.rotate, args.stats]):
        print("No action specified. Use --help for options.")
        print("\nExamples:")
        print("  python log_cleanup.py --stats")
        print("  python log_cleanup.py --cleanup --retention-days 90")
        print("  python log_cleanup.py --rotate")
        print("  python log_cleanup.py --cleanup --dry-run")

if __name__ == "__main__":
    main()
