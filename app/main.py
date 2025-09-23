from fastapi import FastAPI, UploadFile, File, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db import get_db
from app import models
from app.s3utils import upload_bytes

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
    resume = models.Resume(filename=file.filename, s3_url=s3_url, parsed_confidence=0)
    db.add(resume)
    db.commit()
    db.refresh(resume)

    return {"resume_id": resume.id, "s3_url": s3_url}


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
    resume = models.Resume(filename=file.filename, s3_url=s3_url, parsed_confidence=90)
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
            "resume_url": resume.s3_url if resume else "#"
        })
    return templates.TemplateResponse("candidates.html", {"request": request, "candidates": enriched})

