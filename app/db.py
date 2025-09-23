import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Load .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "Set DATABASE_URL environment variable, e.g. postgresql://user:pass@localhost:5432/resume_parser_db"
    )

# SQLAlchemy engine and session factory
engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()


# Dependency for FastAPI routes
def get_db():
    """Provide a SQLAlchemy session to FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
