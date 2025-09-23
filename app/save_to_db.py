from sqlalchemy.orm import Session
from datetime import datetime
from app import models
from app.logging_config import log_processing_event
import logging

def save_parsed_candidate(parsed: dict, resume_id: int, db: Session):
    """
    Save parsed resume JSON into Postgres.
    Creates/updates Candidate and child tables.
    Links Candidate to Resume.
    """

    # --- 1. Candidate record ---
    candidate = models.Candidate(
        full_name=parsed.get("full_name"),
        current_location=parsed.get("location"),  # ✅ mapped correctly
        linkedin_url=parsed.get("linkedin_url"),
        current_salary=parsed.get("current_salary"),
        expected_salary=parsed.get("expected_salary"),
        notice_period=parsed.get("notice_period"),
        total_experience_years=float(parsed.get("total_experience_years") or 0),
        processing_date=datetime.utcnow(),
        raw_json=parsed
    )

    db.add(candidate)
    db.flush()  # get candidate.id

    # --- 2. Emails ---
    for email in parsed.get("emails", []):
        db.add(models.CandidateEmail(candidate_id=candidate.id, email_address=email))

    # --- 3. Phones ---
    for phone in parsed.get("phones", []):
        db.add(models.CandidatePhone(candidate_id=candidate.id, phone_number=phone))

    # --- 4. Education ---
    for edu in parsed.get("education", []):
        db.add(models.CandidateEducation(
            candidate_id=candidate.id,
            degree=edu.get("degree"),
            institution=edu.get("institution"),
            major=edu.get("major"),
            graduation_year=int(edu.get("graduation_year") or 0) if edu.get("graduation_year") else None,
            certifications=edu.get("certifications")
        ))

    # --- 5. Experience ---
    for exp in parsed.get("experience", []):
        db.add(models.CandidateExperience(
            candidate_id=candidate.id,
            job_title=exp.get("job_title"),
            organization=exp.get("organization"),
            location=exp.get("location"),
            reporting_to=exp.get("reporting_to"),
            start_date=None,  # TODO: parse string → date
            end_date=None,
            roles_responsibilities=exp.get("roles_responsibilities"),
            achievements=exp.get("achievements")
        ))

    # --- 6. Skills (raw, without master list matching for now) ---
    for skill in parsed.get("skills", []):
        # Just create MasterSkill if not exists
        skill_obj = db.query(models.MasterSkill).filter_by(skill_name=skill).first()
        if not skill_obj:
            skill_obj = models.MasterSkill(skill_name=skill)
            db.add(skill_obj)
            db.flush()
        db.add(models.CandidateSkill(candidate_id=candidate.id, skill_id=skill_obj.id))

    # --- 7. Languages ---
    for lang in parsed.get("languages", []):
        db.add(models.CandidateLanguage(candidate_id=candidate.id, language=lang, proficiency=None))

    # --- 8. Link Resume to Candidate ---
    resume = db.query(models.Resume).filter_by(id=resume_id).first()
    if resume:
        resume.candidate_id = candidate.id
        resume.parsed_confidence = 90  # placeholder, refine later
        resume.parsed_model = parsed.get("_model_used")



    db.commit()
    db.refresh(candidate)

    # Log successful candidate creation
    database_logger = logging.getLogger('resume_parser.database')
    log_processing_event(
        database_logger,
        "CANDIDATE_SAVED",
        candidate_id=candidate.id,
        resume_id=resume_id,
        details=f"Saved {len(parsed.get('skills', []))} skills, {len(parsed.get('experience', []))} experiences",
        success=True
    )

    return candidate.id
