import boto3
import os
import io
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import logging
from botocore.exceptions import ClientError, NoCredentialsError

class S3LogHandler(logging.Handler):
    """
    Custom logging handler that uploads logs to S3 in batches
    """
    
    def __init__(self, bucket_name: str, log_prefix: str = "logs", 
                 batch_size: int = 100, flush_interval: int = 300):
        super().__init__()
        self.bucket_name = bucket_name
        self.log_prefix = log_prefix
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        # Initialize S3 client
        try:
            self.s3_client = boto3.client('s3')
            self.s3_available = True
        except (NoCredentialsError, Exception) as e:
            print(f"S3 not available for logging: {e}")
            self.s3_available = False
        
        # Batch storage
        self.log_buffer = []
        self.buffer_lock = threading.Lock()
        
        # Start background flush thread
        self.flush_thread = threading.Thread(target=self._background_flush, daemon=True)
        self.flush_thread.start()
    
    def emit(self, record):
        """Add log record to batch buffer"""
        if not self.s3_available:
            return
        
        try:
            # Format the log record
            log_entry = self.format(record)
            
            with self.buffer_lock:
                self.log_buffer.append({
                    'timestamp': datetime.now().isoformat(),
                    'level': record.levelname,
                    'message': log_entry,
                    'logger': record.name
                })
                
                # Flush if batch size reached
                if len(self.log_buffer) >= self.batch_size:
                    self._flush_buffer()
        
        except Exception as e:
            print(f"Error in S3LogHandler.emit: {e}")
    
    def _flush_buffer(self):
        """Flush current buffer to S3"""
        if not self.s3_available or not self.log_buffer:
            return
        
        try:
            with self.buffer_lock:
                if not self.log_buffer:
                    return
                
                # Create batch log content
                batch_content = []
                for entry in self.log_buffer:
                    batch_content.append(f"{entry['timestamp']} - {entry['logger']} - {entry['level']} - {entry['message']}")
                
                # Generate S3 key with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                s3_key = f"{self.log_prefix}/batch_{timestamp}_{len(self.log_buffer)}.log"
                
                # Upload to S3
                log_content = '\n'.join(batch_content)
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=log_content.encode('utf-8'),
                    ContentType='text/plain'
                )
                
                # Clear buffer
                self.log_buffer.clear()
                
        except Exception as e:
            print(f"Error flushing logs to S3: {e}")
    
    def _background_flush(self):
        """Background thread to flush logs periodically"""
        while True:
            time.sleep(self.flush_interval)
            try:
                with self.buffer_lock:
                    if self.log_buffer:
                        self._flush_buffer()
            except Exception as e:
                print(f"Error in background flush: {e}")
    
    def close(self):
        """Flush remaining logs before closing"""
        if self.s3_available:
            self._flush_buffer()
        super().close()

class S3LogManager:
    """
    Manager for S3 log operations including rotation and cleanup
    """
    
    def __init__(self, bucket_name: str, log_prefix: str = "logs"):
        self.bucket_name = bucket_name
        self.log_prefix = log_prefix
        
        try:
            self.s3_client = boto3.client('s3')
            self.s3_available = True
        except (NoCredentialsError, Exception) as e:
            print(f"S3 not available: {e}")
            self.s3_available = False
    
    def upload_log_file(self, local_file_path: str, s3_key: Optional[str] = None) -> bool:
        """Upload a single log file to S3"""
        if not self.s3_available:
            return False
        
        try:
            if not os.path.exists(local_file_path):
                return False
            
            # Generate S3 key if not provided
            if not s3_key:
                filename = os.path.basename(local_file_path)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                s3_key = f"{self.log_prefix}/archives/{filename}.{timestamp}"
            
            # Upload file
            with open(local_file_path, 'rb') as f:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=f.read(),
                    ContentType='text/plain'
                )
            
            return True
            
        except Exception as e:
            print(f"Error uploading {local_file_path} to S3: {e}")
            return False
    
    def upload_log_directory(self, local_dir: str) -> dict:
        """Upload all log files in a directory to S3"""
        if not self.s3_available:
            return {"success": False, "error": "S3 not available"}
        
        results = {
            "uploaded": [],
            "failed": [],
            "total_size": 0
        }
        
        try:
            log_dir = Path(local_dir)
            if not log_dir.exists():
                return {"success": False, "error": "Directory not found"}
            
            # Find all log files
            log_files = list(log_dir.glob("*.log"))
            
            for log_file in log_files:
                if log_file.stat().st_size > 0:  # Only upload non-empty files
                    s3_key = f"{self.log_prefix}/archives/{log_file.name}"
                    
                    if self.upload_log_file(str(log_file), s3_key):
                        results["uploaded"].append(str(log_file))
                        results["total_size"] += log_file.stat().st_size
                    else:
                        results["failed"].append(str(log_file))
            
            return results
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_s3_logs(self, prefix: Optional[str] = None) -> List[dict]:
        """List log files in S3"""
        if not self.s3_available:
            return []
        
        try:
            prefix = prefix or f"{self.log_prefix}/"
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            logs = []
            for obj in response.get('Contents', []):
                logs.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'size_mb': round(obj['Size'] / 1024 / 1024, 2)
                })
            
            return logs
            
        except Exception as e:
            print(f"Error listing S3 logs: {e}")
            return []
    
    def cleanup_old_s3_logs(self, retention_days: int = 180) -> dict:
        """Delete old log files from S3"""
        if not self.s3_available:
            return {"success": False, "error": "S3 not available"}
        
        try:
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            # List all log files
            logs = self.list_s3_logs()
            deleted_files = []
            total_size_freed = 0
            
            for log_info in logs:
                if log_info['last_modified'].replace(tzinfo=None) < cutoff_date:
                    try:
                        self.s3_client.delete_object(
                            Bucket=self.bucket_name,
                            Key=log_info['key']
                        )
                        deleted_files.append(log_info['key'])
                        total_size_freed += log_info['size']
                    except Exception as e:
                        print(f"Error deleting {log_info['key']}: {e}")
            
            return {
                "success": True,
                "deleted_files": deleted_files,
                "files_count": len(deleted_files),
                "size_freed_mb": round(total_size_freed / 1024 / 1024, 2)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_s3_log_stats(self) -> dict:
        """Get statistics about S3 logs"""
        if not self.s3_available:
            return {"error": "S3 not available"}
        
        try:
            logs = self.list_s3_logs()
            
            total_size = sum(log['size'] for log in logs)
            total_files = len(logs)
            
            # Group by date
            by_date = {}
            for log in logs:
                date_str = log['last_modified'].strftime('%Y-%m-%d')
                if date_str not in by_date:
                    by_date[date_str] = {'count': 0, 'size': 0}
                by_date[date_str]['count'] += 1
                by_date[date_str]['size'] += log['size']
            
            return {
                "total_files": total_files,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "by_date": by_date,
                "bucket": self.bucket_name,
                "prefix": self.log_prefix
            }
            
        except Exception as e:
            return {"error": str(e)}
