import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
import glob
import shutil

def setup_logging():
    """Setup comprehensive logging configuration"""
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(log_dir / "app.log"),
            logging.StreamHandler()  # Also log to console
        ]
    )
    
    # Create specific loggers for different components
    loggers = {
        'upload': logging.getLogger('resume_parser.upload'),
        'parsing': logging.getLogger('resume_parser.parsing'),
        'database': logging.getLogger('resume_parser.database'),
        's3': logging.getLogger('resume_parser.s3'),
        'llm': logging.getLogger('resume_parser.llm'),
        'errors': logging.getLogger('resume_parser.errors'),
        'access': logging.getLogger('resume_parser.access'),
        'security': logging.getLogger('resume_parser.security')
    }
    
    # Set up file handlers for each component
    for name, logger in loggers.items():
        # Create component-specific log file
        handler = logging.FileHandler(log_dir / f"{name}.log")
        handler.setFormatter(logging.Formatter(log_format, date_format))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return loggers

def log_processing_event(logger, event_type, candidate_id=None, resume_id=None, details=None, success=True):
    """Log processing events with structured data"""
    status = "SUCCESS" if success else "ERROR"
    message = f"[{status}] {event_type}"
    
    if candidate_id:
        message += f" - Candidate ID: {candidate_id}"
    if resume_id:
        message += f" - Resume ID: {resume_id}"
    if details:
        message += f" - Details: {details}"
    
    if success:
        logger.info(message)
    else:
        logger.error(message)

def log_llm_usage(logger, model_name, tokens_used=None, cost=None, processing_time=None):
    """Log LLM usage for monitoring and cost tracking"""
    message = f"LLM Usage - Model: {model_name}"
    if tokens_used:
        message += f" - Tokens: {tokens_used}"
    if cost:
        message += f" - Cost: ${cost:.4f}"
    if processing_time:
        message += f" - Time: {processing_time:.2f}s"
    
    logger.info(message)

def log_parsing_quality(logger, confidence, model_used, parsing_errors=None):
    """Log parsing quality metrics"""
    quality = "HIGH" if confidence >= 80 else "MEDIUM" if confidence >= 60 else "LOW"
    message = f"Parsing Quality: {quality} (Confidence: {confidence}%, Model: {model_used})"
    
    if parsing_errors:
        message += f" - Errors: {parsing_errors}"
    
    logger.info(message)

def log_access_event(logger, ip_address, method, endpoint, status_code, response_time, user_agent=None):
    """Log HTTP access events for compliance and monitoring"""
    message = f"ACCESS - IP: {ip_address} | {method} {endpoint} | Status: {status_code} | Time: {response_time:.3f}s"
    if user_agent:
        message += f" | UA: {user_agent[:100]}"  # Truncate long user agents
    
    logger.info(message)

def log_security_event(logger, event_type, ip_address, details=None):
    """Log security-related events"""
    message = f"SECURITY - {event_type} - IP: {ip_address}"
    if details:
        message += f" - Details: {details}"
    
    logger.warning(message)

def cleanup_old_logs(retention_days=180):
    """
    Clean up log files older than specified retention period (default 6 months)
    
    Args:
        retention_days: Number of days to retain logs (default 180 = 6 months)
    """
    log_dir = Path("logs")
    if not log_dir.exists():
        return
    
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    deleted_files = []
    total_size_freed = 0
    
    # Get all log files
    log_files = list(log_dir.glob("*.log"))
    
    for log_file in log_files:
        try:
            # Get file modification time
            file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            
            if file_mtime < cutoff_date:
                # Get file size before deletion
                file_size = log_file.stat().st_size
                
                # Delete the file
                log_file.unlink()
                
                deleted_files.append(str(log_file))
                total_size_freed += file_size
                
        except Exception as e:
            # Log error but continue with other files
            print(f"Error deleting {log_file}: {e}")
    
    if deleted_files:
        print(f"Log cleanup completed: {len(deleted_files)} files deleted, {total_size_freed / 1024 / 1024:.2f} MB freed")
        return {
            "deleted_files": deleted_files,
            "files_count": len(deleted_files),
            "size_freed_mb": round(total_size_freed / 1024 / 1024, 2)
        }
    else:
        print("No old log files found for cleanup")
        return {"deleted_files": [], "files_count": 0, "size_freed_mb": 0}

def rotate_logs():
    """
    Rotate log files by moving current logs to timestamped archives
    This helps with log management and prevents single files from becoming too large
    """
    log_dir = Path("logs")
    if not log_dir.exists():
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    rotated_files = []
    
    # List of log files to rotate
    log_files = ["app.log", "access.log", "security.log", "upload.log", "parsing.log", "database.log", "s3.log", "llm.log", "errors.log"]
    
    for log_file in log_files:
        log_path = log_dir / log_file
        if log_path.exists() and log_path.stat().st_size > 0:
            # Create archive filename
            archive_name = f"{log_file}.{timestamp}"
            archive_path = log_dir / archive_name
            
            try:
                # Move current log to archive
                shutil.move(str(log_path), str(archive_path))
                rotated_files.append(archive_name)
                
                # Create new empty log file
                log_path.touch()
                
            except Exception as e:
                print(f"Error rotating {log_file}: {e}")
    
    if rotated_files:
        print(f"Log rotation completed: {len(rotated_files)} files rotated")
        return {"rotated_files": rotated_files}
    else:
        print("No log files found for rotation")
        return {"rotated_files": []}

def get_log_stats():
    """Get statistics about log files (size, count, oldest/newest)"""
    log_dir = Path("logs")
    if not log_dir.exists():
        return {"error": "Logs directory not found"}
    
    log_files = list(log_dir.glob("*.log"))
    total_size = 0
    file_stats = []
    
    for log_file in log_files:
        try:
            stat = log_file.stat()
            file_info = {
                "filename": log_file.name,
                "size_mb": round(stat.st_size / 1024 / 1024, 2),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "age_days": (datetime.now() - datetime.fromtimestamp(stat.st_mtime)).days
            }
            file_stats.append(file_info)
            total_size += stat.st_size
        except Exception as e:
            file_info = {
                "filename": log_file.name,
                "error": str(e)
            }
            file_stats.append(file_info)
    
    return {
        "total_files": len(log_files),
        "total_size_mb": round(total_size / 1024 / 1024, 2),
        "files": file_stats
    }
