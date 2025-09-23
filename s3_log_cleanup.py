#!/usr/bin/env python3
"""
Standalone script for S3 log management
Can be run as a cron job for automatic S3 log cleanup and management
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.s3_log_handler import S3LogManager
import argparse
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description="S3 Log management utility")
    parser.add_argument("--bucket", required=True, help="S3 bucket name for logs")
    parser.add_argument("--prefix", default="logs", help="S3 prefix for logs (default: logs)")
    parser.add_argument("--stats", action="store_true", help="Show S3 log statistics")
    parser.add_argument("--cleanup", action="store_true", help="Clean up old S3 logs")
    parser.add_argument("--upload", action="store_true", help="Upload local logs to S3")
    parser.add_argument("--retention-days", type=int, default=180, help="Days to retain S3 logs (default: 180)")
    parser.add_argument("--list", action="store_true", help="List S3 log files")
    parser.add_argument("--limit", type=int, default=50, help="Limit number of files to show (default: 50)")
    
    args = parser.parse_args()
    
    # Initialize S3 manager
    try:
        s3_manager = S3LogManager(args.bucket, args.prefix)
    except Exception as e:
        print(f"Error initializing S3 manager: {e}")
        return
    
    if args.stats:
        print("=== S3 Log Statistics ===")
        stats = s3_manager.get_s3_log_stats()
        if "error" in stats:
            print(f"Error: {stats['error']}")
        else:
            print(f"Bucket: {args.bucket}")
            print(f"Prefix: {args.prefix}")
            print(f"Total files: {stats['total_files']}")
            print(f"Total size: {stats['total_size_mb']} MB")
            print("\nFiles by date:")
            for date, info in stats.get('by_date', {}).items():
                print(f"  {date}: {info['count']} files, {round(info['size']/1024/1024, 2)} MB")
    
    if args.list:
        print(f"\n=== S3 Log Files (limit: {args.limit}) ===")
        logs = s3_manager.list_s3_logs()
        recent_logs = sorted(logs, key=lambda x: x['last_modified'], reverse=True)[:args.limit]
        
        if not recent_logs:
            print("No log files found")
        else:
            for log in recent_logs:
                print(f"  {log['key']} - {log['size_mb']} MB - {log['last_modified']}")
    
    if args.cleanup:
        print(f"\n=== S3 Log Cleanup (retention: {args.retention_days} days) ===")
        result = s3_manager.cleanup_old_s3_logs(args.retention_days)
        
        if result.get("success"):
            print(f"Cleanup completed: {result['files_count']} files deleted, {result['size_freed_mb']} MB freed")
            if result.get("deleted_files"):
                print("Deleted files:")
                for file in result["deleted_files"][:10]:  # Show first 10
                    print(f"  {file}")
                if len(result["deleted_files"]) > 10:
                    print(f"  ... and {len(result['deleted_files']) - 10} more")
        else:
            print(f"Cleanup failed: {result.get('error', 'Unknown error')}")
    
    if args.upload:
        print(f"\n=== Upload Local Logs to S3 ===")
        result = s3_manager.upload_log_directory("logs")
        
        if "error" in result:
            print(f"Upload failed: {result['error']}")
        else:
            print(f"Upload completed:")
            print(f"  Uploaded: {len(result.get('uploaded', []))} files")
            print(f"  Failed: {len(result.get('failed', []))} files")
            print(f"  Total size: {round(result.get('total_size', 0) / 1024 / 1024, 2)} MB")
            
            if result.get('uploaded'):
                print("Uploaded files:")
                for file in result["uploaded"]:
                    print(f"  {file}")
            
            if result.get('failed'):
                print("Failed files:")
                for file in result["failed"]:
                    print(f"  {file}")
    
    if not any([args.stats, args.cleanup, args.upload, args.list]):
        print("No action specified. Use --help for options.")
        print("\nExamples:")
        print(f"  python s3_log_cleanup.py --bucket {args.bucket} --stats")
        print(f"  python s3_log_cleanup.py --bucket {args.bucket} --cleanup --retention-days 90")
        print(f"  python s3_log_cleanup.py --bucket {args.bucket} --upload")
        print(f"  python s3_log_cleanup.py --bucket {args.bucket} --list --limit 20")

if __name__ == "__main__":
    main()
