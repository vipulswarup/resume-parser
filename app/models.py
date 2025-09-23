from sqlalchemy import (
    Column, Integer, String, Text, Date, TIMESTAMP, ForeignKey, Numeric, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from .db import Base

class Candidate(Base):
    __tablename__ = "candidates"
    id = Column(Integer, primary_key=True)
    full_name = Column(String(255), nullable=False)
    title = Column(String(255))
    first_name = Column(String(100))
    middle_name = Column(String(100))
    last_name = Column(String(100))
    gender = Column(String(50))
    age = Column(Integer)
    date_of_birth = Column(Date)
    marital_status = Column(String(50))
    family_details = Column(Text)
    current_location = Column(String(255))
    preferred_location = Column(String(255))
    linkedin_url = Column(Text)
    current_salary = Column(String(255))
    expected_salary = Column(String(255))
    notice_period = Column(String(100))
    total_experience_years = Column(Numeric(4,1))
    processing_date = Column(TIMESTAMP)
    status = Column(String(50), default="active")
    raw_json = Column(JSONB)

    emails = relationship("CandidateEmail", back_populates="candidate", cascade="all, delete-orphan")
    phones = relationship("CandidatePhone", back_populates="candidate", cascade="all, delete-orphan")
    experiences = relationship("CandidateExperience", back_populates="candidate", cascade="all, delete-orphan")
    educations = relationship("CandidateEducation", back_populates="candidate", cascade="all, delete-orphan")
    skills = relationship("CandidateSkill", back_populates="candidate", cascade="all, delete-orphan")
    languages = relationship("CandidateLanguage", back_populates="candidate", cascade="all, delete-orphan")
    resumes = relationship("Resume", back_populates="candidate", cascade="all, delete-orphan")

class CandidateEmail(Base):
    __tablename__ = "candidate_emails"
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"))
    email_address = Column(String(255))
    candidate = relationship("Candidate", back_populates="emails")

class CandidatePhone(Base):
    __tablename__ = "candidate_phones"
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"))
    phone_number = Column(String(50))
    candidate = relationship("Candidate", back_populates="phones")

class CandidateExperience(Base):
    __tablename__ = "candidate_experience"
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"))
    job_title = Column(String(255))
    organization = Column(String(255))
    location = Column(String(255))
    reporting_to = Column(String(255))
    start_date = Column(Date)
    end_date = Column(Date)
    roles_responsibilities = Column(Text)
    achievements = Column(Text)
    candidate = relationship("Candidate", back_populates="experiences")

class CandidateEducation(Base):
    __tablename__ = "candidate_education"
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"))
    degree = Column(String(255))
    institution = Column(String(255))
    major = Column(String(255))
    graduation_year = Column(Integer)
    certifications = Column(Text)
    candidate = relationship("Candidate", back_populates="educations")

class MasterSkill(Base):
    __tablename__ = "master_skills"
    id = Column(Integer, primary_key=True)
    skill_name = Column(String(255), unique=True, nullable=False)
    skill_type = Column(String(50))
    category = Column(String(100))
    candidate_links = relationship("CandidateSkill", back_populates="master_skill", cascade="all, delete-orphan")

class CandidateSkill(Base):
    __tablename__ = "candidate_skills"
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"))
    skill_id = Column(Integer, ForeignKey("master_skills.id", ondelete="CASCADE"))
    skill_level = Column(String(50))
    candidate = relationship("Candidate", back_populates="skills")
    master_skill = relationship("MasterSkill", back_populates="candidate_links")
    __table_args__ = (UniqueConstraint('candidate_id', 'skill_id', name='_candidate_skill_uc'),)

class CandidateLanguage(Base):
    __tablename__ = "candidate_languages"
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"))
    language = Column(String(100))
    proficiency = Column(String(50))
    candidate = relationship("Candidate", back_populates="languages")

class Position(Base):
    __tablename__ = "positions"
    id = Column(Integer, primary_key=True)
    title = Column(String(255), unique=True, nullable=False)
    description = Column(Text)
    candidate_links = relationship("CandidatePosition", back_populates="position", cascade="all, delete-orphan")

class CandidatePosition(Base):
    __tablename__ = "candidate_positions"
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"))
    position_id = Column(Integer, ForeignKey("positions.id", ondelete="CASCADE"))
    position = relationship("Position", back_populates="candidate_links")
    __table_args__ = (UniqueConstraint('candidate_id', 'position_id', name='_candidate_position_uc'),)

class Resume(Base):
    __tablename__ = "resumes"
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"))
    source_filename = Column(Text)
    file_url = Column(Text)
    parsed_confidence = Column(Numeric(5,2))
    uploaded_at = Column(TIMESTAMP)
    candidate = relationship("Candidate", back_populates="resumes")
    parsed_model = Column(String, nullable=True)


class ProcessingLog(Base):
    __tablename__ = "processing_logs"
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=True)
    action = Column(String(255))
    details = Column(Text)
    created_at = Column(TIMESTAMP)
