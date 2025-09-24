import threading
import time
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app import models
from app.text_extract import extract_text_from_file
from app.parser_llm import parse_with_llm
from app.save_to_db import save_parsed_candidate
from app.logging_config import log_processing_event
import logging

# Get logger for background tasks
background_logger = logging.getLogger('resume_parser.background')

def process_resume_background(resume_id: int, file_url: str, source_filename: str):
    """
    Background task to process resume: extract text, parse with LLM, save to DB
    """
    db = SessionLocal()
    try:
        background_logger.info(f"Starting background processing for resume ID: {resume_id}")
        
        # Update status to processing
        resume = db.query(models.Resume).filter_by(id=resume_id).first()
        if resume:
            resume.processing_status = "processing"
            db.commit()
        
        # Extract text from file
        background_logger.info(f"Extracting text from: {source_filename}")
        extracted_text = extract_text_from_file(file_url)
        
        if not extracted_text or len(extracted_text.strip()) < 50:
            background_logger.error(f"Text extraction failed or insufficient text for: {source_filename}")
            resume.processing_status = "failed"
            db.commit()
            return
        
        # Parse with LLM
        background_logger.info(f"Starting LLM parsing for: {source_filename}")
        parsed_data = parse_with_llm(extracted_text)
        
        if "error" in parsed_data:
            background_logger.error(f"LLM parsing failed for: {source_filename} - {parsed_data.get('error')}")
            resume.processing_status = "failed"
            db.commit()
            return
        
        # Save parsed data to database
        background_logger.info(f"Saving parsed data for: {source_filename}")
        candidate_id = save_parsed_candidate(parsed_data, resume_id, db)
        
        # Update resume with parsed data
        if resume:
            resume.candidate_id = candidate_id
            resume.parsed_confidence = parsed_data.get("confidence", 0)
            resume.parsed_model = parsed_data.get("_model_used", "unknown")
            resume.processing_status = "completed"
            db.commit()
        
        background_logger.info(f"Background processing completed for resume ID: {resume_id}")
        
        # Log successful processing
        log_processing_event(
            background_logger,
            "BACKGROUND_PROCESSING_COMPLETE",
            candidate_id=candidate_id,
            resume_id=resume_id,
            details=f"Processing completed successfully for {source_filename}",
            success=True
        )
        
    except Exception as e:
        background_logger.error(f"Background processing failed for resume ID {resume_id}: {str(e)}")
        
        # Update status to failed
        resume = db.query(models.Resume).filter_by(id=resume_id).first()
        if resume:
            resume.processing_status = "failed"
            db.commit()
        
        # Log failed processing
        log_processing_event(
            background_logger,
            "BACKGROUND_PROCESSING_FAILED",
            candidate_id=None,
            resume_id=resume_id,
            details=f"Background processing failed: {str(e)}",
            success=False
        )
        
    finally:
        db.close()

def start_background_processing(resume_id: int, file_url: str, source_filename: str):
    """
    Start background processing in a separate thread
    """
    thread = threading.Thread(
        target=process_resume_background,
        args=(resume_id, file_url, source_filename),
        daemon=True
    )
    thread.start()
    background_logger.info(f"Started background thread for resume ID: {resume_id}")
    return thread
