from fastapi import FastAPI, UploadFile, File, Depends, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import boto3
import io
import time
from datetime import datetime, date

from app.db import get_db
from app import models
from app.s3utils import upload_bytes
from app.excel_export import export_candidates_to_excel, get_export_filename
from app.template_generator import generate_candidate_template
from app.logging_config import setup_logging, log_processing_event, log_llm_usage, log_parsing_quality, log_access_event, log_security_event, cleanup_old_logs, rotate_logs, get_log_stats
from app.s3_log_handler import S3LogManager

# For text extraction + parsing
from app.text_extract import extract_text
from app.parser_llm import parse_with_llm
from app.save_to_db import save_parsed_candidate

# Initialize FastAPI
app = FastAPI()

# Setup templates folder
templates = Jinja2Templates(directory="app/templates")

# Setup logging with S3 support
import os
s3_bucket = os.getenv('S3_LOG_BUCKET', os.getenv('S3_BUCKET'))
s3_log_prefix = os.getenv('S3_LOG_PREFIX', 'logs')
enable_s3_logging = os.getenv('ENABLE_S3_LOGGING', 'true').lower() == 'true'

loggers = setup_logging(
    s3_bucket=s3_bucket,
    s3_log_prefix=s3_log_prefix,
    enable_s3_logging=enable_s3_logging
)

# Middleware for access logging
@app.middleware("http")
async def access_logging_middleware(request: Request, call_next):
    """Middleware to log all HTTP requests with IP, timestamp, and response details"""
    start_time = time.time()
    
    # Get client IP (handles proxies)
    client_ip = request.client.host
    if "x-forwarded-for" in request.headers:
        client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
    elif "x-real-ip" in request.headers:
        client_ip = request.headers["x-real-ip"]
    
    # Get user agent
    user_agent = request.headers.get("user-agent", "")
    
    # Process request
    response = await call_next(request)
    
    # Calculate response time
    response_time = time.time() - start_time
    
    # Log access event
    log_access_event(
        loggers['access'],
        client_ip,
        request.method,
        str(request.url.path),
        response.status_code,
        response_time,
        user_agent
    )
    
    # Log security events for suspicious activity
    if response.status_code >= 400:
        if response.status_code >= 500:
            log_security_event(
                loggers['security'],
                "SERVER_ERROR",
                client_ip,
                f"Status: {response.status_code}, Path: {request.url.path}"
            )
        elif response.status_code == 404:
            log_security_event(
                loggers['security'],
                "NOT_FOUND_ACCESS",
                client_ip,
                f"Path: {request.url.path}"
            )
        elif response.status_code == 403:
            log_security_event(
                loggers['security'],
                "FORBIDDEN_ACCESS",
                client_ip,
                f"Path: {request.url.path}"
            )
    
    return response


# -------------------
# API ROUTES
# -------------------

@app.post("/upload")
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    s3_url = upload_bytes(contents, file.filename, prefix="resumes")

    # Save resume record
    resume = models.Resume(source_filename=file.filename, file_url=s3_url, parsed_confidence=0)
    db.add(resume)
    db.commit()
    db.refresh(resume)

    return {"resume_id": resume.id, "s3_url": s3_url}


@app.get("/download/{resume_id}")
async def download_resume(resume_id: int, db: Session = Depends(get_db)):
    """Download a resume file from S3"""
    resume = db.query(models.Resume).filter(models.Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # Extract bucket and key from S3 URL
    s3_url = resume.file_url
    if not s3_url.startswith("s3://"):
        raise HTTPException(status_code=400, detail="Invalid S3 URL")
    
    # Parse S3 URL: s3://bucket/key
    url_parts = s3_url[5:].split("/", 1)
    bucket = url_parts[0]
    key = url_parts[1]
    
    # Download from S3
    s3 = boto3.client("s3")
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        file_content = response["Body"].read()
        
        # Determine content type
        content_type = "application/octet-stream"
        if resume.source_filename:
            if resume.source_filename.lower().endswith('.pdf'):
                content_type = "application/pdf"
            elif resume.source_filename.lower().endswith('.docx'):
                content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            elif resume.source_filename.lower().endswith('.doc'):
                content_type = "application/msword"
        
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=content_type,
            headers={"Content-Disposition": f"inline; filename={resume.source_filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading file: {str(e)}")


@app.get("/export/excel")
async def export_excel(
    db: Session = Depends(get_db),
    date_from: date = Query(None, description="Filter candidates from this date"),
    date_to: date = Query(None, description="Filter candidates to this date"),
    skills: str = Query(None, description="Filter by skills (comma-separated)")
):
    """Export candidates data to Excel format"""
    filters = {}
    if date_from:
        filters['date_from'] = date_from
    if date_to:
        filters['date_to'] = date_to
    if skills:
        filters['skills'] = [s.strip() for s in skills.split(',')]
    
    try:
        excel_data = export_candidates_to_excel(db, filters)
        filename = get_export_filename(filters)
        
        return Response(
            content=excel_data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating Excel export: {str(e)}")


@app.get("/generate-template/{candidate_id}")
async def generate_template(
    candidate_id: int,
    format: str = Query("docx", description="Output format: docx or pdf"),
    template: str = Query("standard", description="Template type: standard or v2"),
    db: Session = Depends(get_db)
):
    """Generate standardized resume template for a candidate"""
    try:
        result = generate_candidate_template(candidate_id, db, format, template)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Get the generated file from S3
        s3_url = result["file_url"]
        if not s3_url.startswith("s3://"):
            raise HTTPException(status_code=400, detail="Invalid S3 URL")
        
        # Parse S3 URL
        url_parts = s3_url[5:].split("/", 1)
        bucket = url_parts[0]
        key = url_parts[1]
        
        # Download from S3
        s3 = boto3.client("s3")
        response = s3.get_object(Bucket=bucket, Key=key)
        file_content = response["Body"].read()
        
        # Determine content type
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if format.lower() == "pdf":
            content_type = "application/pdf"
        
        return Response(
            content=file_content,
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={result['filename']}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating template: {str(e)}")


# -------------------
# UI ROUTES
# -------------------

@app.get("/ui/upload", response_class=HTMLResponse)
async def ui_upload_form(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})


@app.post("/ui/upload", response_class=HTMLResponse)
async def ui_upload_resume(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    start_time = time.time()
    upload_logger = loggers['upload']
    parsing_logger = loggers['parsing']
    error_logger = loggers['errors']
    
    try:
        # Log upload start
        upload_logger.info(f"Starting upload: {file.filename} ({file.content_type})")
        
        # Save to S3
        contents = await file.read()
        s3_url = upload_bytes(contents, file.filename, prefix="resumes")
        upload_logger.info(f"S3 upload successful: {s3_url}")

        # Save temp file locally for text extraction
        local_path = f"/tmp/{file.filename}"
        with open(local_path, "wb") as f:
            f.write(contents)

        # Extract text
        parsing_logger.info(f"Starting text extraction for: {file.filename}")
        text = extract_text(local_path)
        parsing_logger.info(f"Text extraction completed. Length: {len(text)} characters")

        # Parse with LLM
        parsing_logger.info("Starting LLM parsing")
        parse_start = time.time()
        parsed = parse_with_llm(text)
        parse_time = time.time() - parse_start
        
        # Log parsing results
        model_used = parsed.get('model_used', 'unknown')
        confidence = parsed.get('confidence', 90.0)
        log_llm_usage(parsing_logger, model_used, processing_time=parse_time)
        log_parsing_quality(parsing_logger, confidence, model_used)

        # Save resume
        resume = models.Resume(
            source_filename=file.filename, 
            file_url=s3_url, 
            parsed_confidence=confidence,
            parsed_model=model_used,
            uploaded_at=datetime.now()
        )
        db.add(resume)
        db.commit()
        db.refresh(resume)
        
        upload_logger.info(f"Resume saved to database: ID {resume.id}")

        # Save candidate
        candidate_id = save_parsed_candidate(parsed, resume.id, db)
        
        # Log processing event
        total_time = time.time() - start_time
        log_processing_event(
            upload_logger, 
            "RESUME_PROCESSING_COMPLETE", 
            candidate_id=candidate_id, 
            resume_id=resume.id,
            details=f"Processing time: {total_time:.2f}s, Confidence: {confidence}%",
            success=True
        )

        # Clean up temp file
        import os
        try:
            os.remove(local_path)
        except:
            pass

        return templates.TemplateResponse(
            "upload.html",
            {"request": request, "message": f"Successfully uploaded and parsed candidate {candidate_id} (Confidence: {confidence}%)"}
        )
        
    except Exception as e:
        error_logger.error(f"Upload failed for {file.filename}: {str(e)}")
        log_processing_event(
            error_logger,
            "RESUME_PROCESSING_FAILED",
            details=f"Error: {str(e)}",
            success=False
        )
        
        return templates.TemplateResponse(
            "upload.html",
            {"request": request, "error": f"Upload failed: {str(e)}"}
        )


@app.get("/ui/candidates", response_class=HTMLResponse)
def ui_list_candidates(
    request: Request, 
    db: Session = Depends(get_db),
    search: str = Query(None, description="Search by name"),
    date_from: date = Query(None, description="Filter from this date"),
    date_to: date = Query(None, description="Filter to this date"),
    skills: str = Query(None, description="Filter by skills (comma-separated)"),
    experience_min: float = Query(None, description="Minimum experience years"),
    experience_max: float = Query(None, description="Maximum experience years")
):
    # Build query with filters
    query = db.query(models.Candidate)
    
    # Apply filters
    if search:
        query = query.filter(models.Candidate.full_name.ilike(f"%{search}%"))
    
    if date_from:
        query = query.filter(models.Candidate.processing_date >= date_from)
    
    if date_to:
        query = query.filter(models.Candidate.processing_date <= date_to)
    
    if experience_min is not None:
        query = query.filter(models.Candidate.total_experience_years >= experience_min)
    
    if experience_max is not None:
        query = query.filter(models.Candidate.total_experience_years <= experience_max)
    
    if skills:
        skill_list = [s.strip().lower() for s in skills.split(',')]
        # Filter by skills in raw_json or skills relationship
        from sqlalchemy import or_, and_
        skill_conditions = []
        
        # Check raw_json skills
        for skill in skill_list:
            skill_conditions.append(
                models.Candidate.raw_json.op('->>')('skills').op('ilike')(f'%{skill}%')
            )
        
        # Check skills relationship
        for skill in skill_list:
            skill_conditions.append(
                models.Candidate.skills.any(
                    models.CandidateSkill.master_skill.has(
                        models.MasterSkill.skill_name.ilike(f'%{skill}%')
                    )
                )
            )
        
        if skill_conditions:
            query = query.filter(or_(*skill_conditions))
    
    candidates = query.all()
    
    enriched = []
    for c in candidates:
        skills = []
        if c.raw_json and "skills" in c.raw_json:
            skills = c.raw_json["skills"]
        resume = db.query(models.Resume).filter_by(candidate_id=c.id).first()
        enriched.append({
            "id": c.id,
            "full_name": c.full_name,
            "total_experience_years": c.total_experience_years,
            "skills": skills,
            "parsed_model": resume.parsed_model if resume else None,
            "resume_url": f"/download/{resume.id}" if resume else "#"
        })
    
    return templates.TemplateResponse("candidates.html", {"request": request, "candidates": enriched})


# -------------------
# MONITORING & HEALTH ENDPOINTS
# -------------------

@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get basic system statistics"""
    try:
        # Basic counts
        total_candidates = db.query(models.Candidate).count()
        total_resumes = db.query(models.Resume).count()
        
        # Get recent uploads (last 24 hours) - handle case where uploaded_at might be None
        from datetime import timedelta
        try:
            recent_uploads = db.query(models.Resume).filter(
                models.Resume.uploaded_at >= datetime.now() - timedelta(days=1)
            ).count()
        except Exception:
            # Fallback if uploaded_at column has issues
            recent_uploads = 0
        
        # Get parsing success rate
        try:
            successful_parses = db.query(models.Resume).filter(
                models.Resume.parsed_confidence >= 60
            ).count()
            success_rate = (successful_parses / total_resumes * 100) if total_resumes > 0 else 0
        except Exception:
            success_rate = 0
        
        # Get model usage stats
        try:
            model_stats = db.query(
                models.Resume.parsed_model, 
                db.func.count(models.Resume.id).label('count')
            ).group_by(models.Resume.parsed_model).all()
            model_usage = {model: count for model, count in model_stats if model is not None}
        except Exception:
            model_usage = {}
        
        return {
            "total_candidates": total_candidates,
            "total_resumes": total_resumes,
            "recent_uploads_24h": recent_uploads,
            "parsing_success_rate": round(success_rate, 2),
            "model_usage": model_usage,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        loggers['errors'].error(f"Stats endpoint error: {str(e)}")
        return {"error": f"Unable to fetch statistics: {str(e)}"}

@app.get("/logs/recent")
async def get_recent_logs(limit: int = Query(50, description="Number of recent log entries")):
    """Get recent log entries for monitoring"""
    try:
        log_file = "logs/app.log"
        if not os.path.exists(log_file):
            return {"logs": [], "message": "No logs available"}
        
        with open(log_file, 'r') as f:
            lines = f.readlines()
            recent_lines = lines[-limit:] if len(lines) > limit else lines
        
        return {
            "logs": [line.strip() for line in recent_lines],
            "count": len(recent_lines)
        }
    except Exception as e:
        return {"error": f"Unable to read logs: {str(e)}"}

@app.get("/logs/access")
async def get_access_logs(limit: int = Query(100, description="Number of recent access log entries")):
    """Get recent access log entries"""
    try:
        log_file = "logs/access.log"
        if not os.path.exists(log_file):
            return {"logs": [], "message": "No access logs available"}
        
        with open(log_file, 'r') as f:
            lines = f.readlines()
            recent_lines = lines[-limit:] if len(lines) > limit else lines
        
        return {
            "access_logs": [line.strip() for line in recent_lines],
            "count": len(recent_lines)
        }
    except Exception as e:
        return {"error": f"Unable to read access logs: {str(e)}"}

@app.get("/logs/security")
async def get_security_logs(limit: int = Query(50, description="Number of recent security log entries")):
    """Get recent security log entries"""
    try:
        log_file = "logs/security.log"
        if not os.path.exists(log_file):
            return {"logs": [], "message": "No security logs available"}
        
        with open(log_file, 'r') as f:
            lines = f.readlines()
            recent_lines = lines[-limit:] if len(lines) > limit else lines
        
        return {
            "security_logs": [line.strip() for line in recent_lines],
            "count": len(recent_lines)
        }
    except Exception as e:
        return {"error": f"Unable to read security logs: {str(e)}"}

@app.post("/logs/cleanup")
async def cleanup_logs(retention_days: int = Query(180, description="Number of days to retain logs (default 180 = 6 months)")):
    """Clean up old log files"""
    try:
        result = cleanup_old_logs(retention_days)
        return {
            "message": f"Log cleanup completed",
            "deleted_files": result["deleted_files"],
            "files_count": result["files_count"],
            "size_freed_mb": result["size_freed_mb"]
        }
    except Exception as e:
        return {"error": f"Log cleanup failed: {str(e)}"}

@app.post("/logs/rotate")
async def rotate_log_files(upload_to_s3: bool = Query(True, description="Upload rotated logs to S3")):
    """Rotate current log files to archives"""
    try:
        result = rotate_logs(
            s3_bucket=s3_bucket,
            s3_log_prefix=s3_log_prefix,
            upload_to_s3=upload_to_s3
        )
        return {
            "message": "Log rotation completed",
            "rotated_files": result["rotated_files"],
            "s3_uploaded": result["s3_uploaded"]
        }
    except Exception as e:
        return {"error": f"Log rotation failed: {str(e)}"}

@app.get("/logs/stats")
async def get_log_statistics():
    """Get log file statistics"""
    try:
        return get_log_stats()
    except Exception as e:
        return {"error": f"Unable to get log stats: {str(e)}"}

@app.get("/logs/s3")
async def get_s3_logs(limit: int = Query(50, description="Number of S3 log entries to retrieve")):
    """Get S3 log statistics and recent logs"""
    try:
        if not s3_bucket:
            return {"error": "S3 logging not configured"}
        
        s3_manager = S3LogManager(s3_bucket, s3_log_prefix)
        stats = s3_manager.get_s3_log_stats()
        logs = s3_manager.list_s3_logs()
        
        # Get recent logs
        recent_logs = sorted(logs, key=lambda x: x['last_modified'], reverse=True)[:limit]
        
        return {
            "stats": stats,
            "recent_logs": recent_logs,
            "bucket": s3_bucket,
            "prefix": s3_log_prefix
        }
    except Exception as e:
        return {"error": f"Unable to get S3 log stats: {str(e)}"}

@app.post("/logs/s3/cleanup")
async def cleanup_s3_logs(retention_days: int = Query(180, description="Number of days to retain S3 logs")):
    """Clean up old S3 log files"""
    try:
        if not s3_bucket:
            return {"error": "S3 logging not configured"}
        
        s3_manager = S3LogManager(s3_bucket, s3_log_prefix)
        result = s3_manager.cleanup_old_s3_logs(retention_days)
        
        return {
            "message": f"S3 log cleanup completed",
            "deleted_files": result.get("deleted_files", []),
            "files_count": result.get("files_count", 0),
            "size_freed_mb": result.get("size_freed_mb", 0)
        }
    except Exception as e:
        return {"error": f"S3 log cleanup failed: {str(e)}"}

@app.post("/logs/s3/upload")
async def upload_logs_to_s3():
    """Upload current log files to S3"""
    try:
        if not s3_bucket:
            return {"error": "S3 logging not configured"}
        
        s3_manager = S3LogManager(s3_bucket, s3_log_prefix)
        result = s3_manager.upload_log_directory("logs")
        
        return {
            "message": "Log upload to S3 completed",
            "uploaded_files": result.get("uploaded", []),
            "failed_files": result.get("failed", []),
            "total_size_mb": round(result.get("total_size", 0) / 1024 / 1024, 2)
        }
    except Exception as e:
        return {"error": f"Log upload to S3 failed: {str(e)}"}


# Add import for os at the top
import os

