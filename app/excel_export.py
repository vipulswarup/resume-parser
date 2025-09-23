import pandas as pd
from sqlalchemy.orm import Session
from app import models
from datetime import datetime
import io

def export_candidates_to_excel(db: Session, filters: dict = None) -> bytes:
    """
    Export candidates data to Excel format with structured schema.
    
    Args:
        db: Database session
        filters: Optional filters for candidates (date_range, skills, etc.)
    
    Returns:
        Excel file as bytes
    """
    # Build query with optional filters
    query = db.query(models.Candidate)
    
    if filters:
        if filters.get('date_from'):
            query = query.filter(models.Candidate.processing_date >= filters['date_from'])
        if filters.get('date_to'):
            query = query.filter(models.Candidate.processing_date <= filters['date_to'])
        if filters.get('skills'):
            # Filter by skills (simplified - would need proper skill matching)
            pass
    
    candidates = query.all()
    
    # Prepare data for Excel
    excel_data = []
    
    for candidate in candidates:
        # Get resume info
        resume = db.query(models.Resume).filter_by(candidate_id=candidate.id).first()
        
        # Extract skills from raw_json or skills relationship
        skills_list = []
        if candidate.raw_json and "skills" in candidate.raw_json:
            skills_list = candidate.raw_json["skills"]
        else:
            # Get skills from relationship
            for skill_rel in candidate.skills:
                if skill_rel.master_skill:
                    skills_list.append(skill_rel.master_skill.skill_name)
        
        # Extract emails and phones
        emails = [email.email_address for email in candidate.emails] if candidate.emails else []
        phones = [phone.phone_number for phone in candidate.phones] if candidate.phones else []
        
        # Get current experience
        current_exp = None
        if candidate.experiences:
            # Find most recent experience
            sorted_experiences = sorted(candidate.experiences, 
                                     key=lambda x: x.start_date or datetime.min, 
                                     reverse=True)
            if sorted_experiences:
                current_exp = sorted_experiences[0]
        
        # Get education
        education_list = []
        for edu in candidate.educations:
            education_list.append(f"{edu.degree} - {edu.institution} ({edu.graduation_year})")
        
        # Get languages
        languages = [lang.language for lang in candidate.languages]
        
        row = {
            'Candidate ID': candidate.id,
            'Full Name': candidate.full_name,
            'First Name': candidate.first_name,
            'Last Name': candidate.last_name,
            'Title': candidate.title,
            'Current Role': current_exp.job_title if current_exp else candidate.title,
            'Current Employer': current_exp.organization if current_exp else candidate.raw_json.get('current_employer', '') if candidate.raw_json else '',
            'Total Experience (Years)': float(candidate.total_experience_years) if candidate.total_experience_years else '',
            'Current Location': candidate.current_location,
            'Preferred Location': candidate.preferred_location,
            'Primary Email': emails[0] if emails else '',
            'All Emails': '; '.join(emails),
            'Primary Phone': phones[0] if phones else '',
            'All Phones': '; '.join(phones),
            'LinkedIn URL': candidate.linkedin_url,
            'Current Salary': candidate.current_salary,
            'Expected Salary': candidate.expected_salary,
            'Notice Period': candidate.notice_period,
            'Skills': '; '.join(skills_list),
            'Languages': '; '.join(languages),
            'Education': '; '.join(education_list),
            'Resume Filename': resume.source_filename if resume else '',
            'Parse Confidence': float(resume.parsed_confidence) if resume and resume.parsed_confidence else '',
            'Parse Model': resume.parsed_model if resume else '',
            'Processing Date': candidate.processing_date.strftime('%Y-%m-%d %H:%M:%S') if candidate.processing_date else '',
            'Status': candidate.status,
            'Raw JSON Available': 'Yes' if candidate.raw_json else 'No'
        }
        
        excel_data.append(row)
    
    # Create DataFrame
    df = pd.DataFrame(excel_data)
    
    # Create Excel file in memory
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Main candidates sheet
        df.to_excel(writer, sheet_name='Candidates', index=False)
        
        # Skills summary sheet
        if skills_list:
            skills_df = pd.DataFrame({'Skills': skills_list})
            skills_df.to_excel(writer, sheet_name='Skills Summary', index=False)
        
        # Processing metadata sheet
        metadata = {
            'Export Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Total Candidates': len(candidates),
            'Filters Applied': str(filters) if filters else 'None',
            'Export Schema Version': '1.0'
        }
        metadata_df = pd.DataFrame(list(metadata.items()), columns=['Field', 'Value'])
        metadata_df.to_excel(writer, sheet_name='Export Metadata', index=False)
    
    output.seek(0)
    return output.getvalue()


def get_export_filename(filters: dict = None) -> str:
    """Generate filename for Excel export"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    if filters and filters.get('date_from'):
        return f"candidates_export_{timestamp}.xlsx"
    return f"candidates_export_{timestamp}.xlsx"
