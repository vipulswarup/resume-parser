import os
import io
import tempfile
from datetime import datetime
from docxtpl import DocxTemplate
from sqlalchemy.orm import Session
from app import models
from app.s3utils import upload_bytes
import boto3
try:
    from docx2pdf import convert
    PDF_CONVERSION_AVAILABLE = True
except ImportError:
    PDF_CONVERSION_AVAILABLE = False

class ResumeTemplateGenerator:
    """Generate standardized resume templates from candidate data"""
    
    def __init__(self, template_path: str = "test-data/SpearBravo Full Candiate Profile Template.docx"):
        self.template_path = template_path
        self.s3_client = boto3.client("s3")
        self.available_templates = {
            "standard": "test-data/Standardized_Resume_Template_Styled.docx",
            "v2": "test-data/Standardized_Resume_Template_v2_Styled.docx",
            "original": "test-data/SpearBravo Full Candiate Profile Template.docx"
        }
    
    def generate_resume_template(self, candidate_id: int, db: Session, output_format: str = "docx", template_type: str = "standard") -> dict:
        """
        Generate a standardized resume template for a candidate
        
        Args:
            candidate_id: ID of the candidate
            db: Database session
            output_format: 'docx' or 'pdf'
            template_type: 'standard' or 'v2'
            
        Returns:
            dict with file_url, filename, and success status
        """
        try:
            # Get candidate data
            candidate = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
            if not candidate:
                return {"success": False, "error": "Candidate not found"}
            
            # Get resume info
            resume = db.query(models.Resume).filter_by(candidate_id=candidate_id).first()
            
            # Prepare template data
            template_data = self._prepare_template_data(candidate, resume, db)
            
            # Select template
            template_path = self.available_templates.get(template_type, self.available_templates["standard"])
            
            # Load and populate template
            doc = DocxTemplate(template_path)
            doc.render(template_data)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = "".join(c for c in candidate.full_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_name = safe_name.replace(' ', '_')
            filename = f"{safe_name}_StandardizedResume_{timestamp}.{output_format}"
            
            # Save to memory
            output = io.BytesIO()
            doc.save(output)
            output.seek(0)
            docx_content = output.getvalue()
            
            # Convert to PDF if requested
            if output_format.lower() == "pdf":
                try:
                    pdf_content = self.generate_pdf(docx_content)
                    # Update filename to .pdf
                    filename = filename.replace('.docx', '.pdf')
                    file_content = pdf_content
                except Exception as e:
                    return {"success": False, "error": f"PDF conversion failed: {str(e)}"}
            else:
                file_content = docx_content
            
            # Upload to S3
            s3_url = upload_bytes(file_content, filename, prefix="generated_templates")
            
            return {
                "success": True,
                "file_url": s3_url,
                "filename": filename,
                "candidate_name": candidate.full_name
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _prepare_template_data(self, candidate, resume, db):
        """Prepare data dictionary for template population"""
        
        # Basic info
        data = {
            "full_name": candidate.full_name or "",
            "title": candidate.title or "",
            "current_location": candidate.current_location or "",
            "linkedin_url": candidate.linkedin_url or "",
            "total_experience_years": str(candidate.total_experience_years) if candidate.total_experience_years else "",
            "current_salary": candidate.current_salary or "",
            "expected_salary": candidate.expected_salary or "",
            "notice_period": candidate.notice_period or "",
        }
        
        # Contact information
        emails = [email.email_address for email in candidate.emails] if candidate.emails else []
        phones = [phone.phone_number for phone in candidate.phones] if candidate.phones else []
        
        data.update({
            "primary_email": emails[0] if emails else "",
            "all_emails": "; ".join(emails),
            "primary_phone": phones[0] if phones else "",
            "all_phones": "; ".join(phones),
        })
        
        # Education
        education_list = []
        for edu in candidate.educations:
            edu_text = f"{edu.degree or ''}"
            if edu.institution:
                edu_text += f" - {edu.institution}"
            if edu.graduation_year:
                edu_text += f" ({edu.graduation_year})"
            if edu.major:
                edu_text += f" - {edu.major}"
            education_list.append(edu_text)
        
        data["education_list"] = education_list
        data["education_summary"] = "; ".join(education_list)
        
        # Skills
        skills_list = []
        if candidate.raw_json and "skills" in candidate.raw_json:
            skills_list = candidate.raw_json["skills"]
        else:
            # Get from skills relationship
            for skill_rel in candidate.skills:
                if skill_rel.master_skill:
                    skills_list.append(skill_rel.master_skill.skill_name)
        
        data["skills_list"] = skills_list
        data["skills_summary"] = ", ".join(skills_list)
        
        # Languages
        languages = [lang.language for lang in candidate.languages]
        data["languages"] = languages
        data["languages_summary"] = ", ".join(languages)
        
        # Experience - get current/most recent
        current_experience = None
        if candidate.experiences:
            sorted_experiences = sorted(candidate.experiences, 
                                     key=lambda x: x.start_date or datetime.min, 
                                     reverse=True)
            if sorted_experiences:
                current_experience = sorted_experiences[0]
        
        data.update({
            "current_role": current_experience.job_title if current_experience else candidate.title or "",
            "current_employer": current_experience.organization if current_experience else "",
            "current_period": self._format_date_range(current_experience.start_date, current_experience.end_date) if current_experience else "",
            "current_responsibilities": current_experience.roles_responsibilities if current_experience else "",
            "current_achievements": current_experience.achievements if current_experience else "",
        })
        
        # All experiences for detailed view
        all_experiences = []
        for exp in candidate.experiences:
            exp_data = {
                "company": exp.organization or "",
                "designation": exp.job_title or "",
                "period": self._format_date_range(exp.start_date, exp.end_date),
                "responsibilities": exp.roles_responsibilities or "",
                "achievements": exp.achievements or "",
                "location": exp.location or "",
                "reporting_to": exp.reporting_to or "",
            }
            all_experiences.append(exp_data)
        
        data["all_experiences"] = all_experiences
        
        # Metadata
        data.update({
            "processing_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "parse_confidence": str(resume.parsed_confidence) if resume and resume.parsed_confidence else "N/A",
            "parse_model": resume.parsed_model if resume else "N/A",
            "original_filename": resume.source_filename if resume else "N/A",
        })
        
        return data
    
    def _format_date_range(self, start_date, end_date):
        """Format date range for display"""
        if not start_date:
            return ""
        
        start_str = start_date.strftime("%b %Y") if start_date else ""
        end_str = end_date.strftime("%b %Y") if end_date else "Present"
        
        if start_str and end_str:
            return f"{start_str} - {end_str}"
        elif start_str:
            return f"{start_str} - Present"
        else:
            return ""
    
    def generate_pdf(self, docx_content: bytes) -> bytes:
        """Convert DOCX to PDF using docx2pdf library"""
        if not PDF_CONVERSION_AVAILABLE:
            raise Exception("PDF conversion not available. docx2pdf library not installed.")
        
        try:
            # Create temporary files for conversion
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_docx:
                temp_docx.write(docx_content)
                temp_docx_path = temp_docx.name
            
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
                temp_pdf_path = temp_pdf.name
            
            # Convert DOCX to PDF
            convert(temp_docx_path, temp_pdf_path)
            
            # Read the PDF content
            with open(temp_pdf_path, 'rb') as pdf_file:
                pdf_content = pdf_file.read()
            
            # Clean up temporary files
            os.unlink(temp_docx_path)
            os.unlink(temp_pdf_path)
            
            return pdf_content
            
        except Exception as e:
            # Clean up temporary files in case of error
            try:
                if 'temp_docx_path' in locals():
                    os.unlink(temp_docx_path)
                if 'temp_pdf_path' in locals():
                    os.unlink(temp_pdf_path)
            except:
                pass
            raise Exception(f"PDF conversion failed: {str(e)}")


def generate_candidate_template(candidate_id: int, db: Session, output_format: str = "docx", template_type: str = "standard") -> dict:
    """Convenience function to generate template for a candidate"""
    generator = ResumeTemplateGenerator()
    return generator.generate_resume_template(candidate_id, db, output_format, template_type)
