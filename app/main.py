from fastapi import FastAPI, UploadFile, File, Depends, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import boto3
import io
from datetime import datetime, date

from app.db import get_db
from app import models
from app.s3utils import upload_bytes
from app.excel_export import export_candidates_to_excel, get_export_filename
from app.template_generator import generate_candidate_template

# For text extraction + parsing
from app.text_extract import extract_text
from app.parser_llm import parse_with_llm
from app.save_to_db import save_parsed_candidate

# Initialize FastAPI
app = FastAPI()

# Setup templates folder
templates = Jinja2Templates(directory="app/templates")


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
    # Save to S3
    contents = await file.read()
    s3_url = upload_bytes(contents, file.filename, prefix="resumes")

    # Save temp file locally for text extraction
    local_path = f"/tmp/{file.filename}"
    with open(local_path, "wb") as f:
        f.write(contents)

    # Extract + parse
    text = extract_text(local_path)
    parsed = parse_with_llm(text)

    # Save resume
    resume = models.Resume(source_filename=file.filename, file_url=s3_url, parsed_confidence=90)
    db.add(resume)
    db.commit()
    db.refresh(resume)

    # Save candidate
    candidate_id = save_parsed_candidate(parsed, resume.id, db)

    return templates.TemplateResponse(
        "upload.html",
        {"request": request, "message": f"Uploaded and saved candidate {candidate_id}"}
    )


@app.get("/ui/candidates", response_class=HTMLResponse)
def ui_list_candidates(request: Request, db: Session = Depends(get_db)):
    candidates = db.query(models.Candidate).all()
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

