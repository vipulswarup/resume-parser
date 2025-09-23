Great idea — here’s the updated **README.md** with a **“Debugging Common Errors”** section at the end.

---

````markdown
# Resume Parser Project

## 📌 Overview
This project is a **resume parsing and standardization tool**.  
It processes resumes in multiple formats, extracts structured data using LLMs (OpenAI or Groq), and stores the results in a **PostgreSQL database** with links to the original files in **AWS S3**.  

The system also provides a **web UI** (via FastAPI + Jinja2) for internal users to upload resumes and view parsed candidates.

---

## ✅ Current Progress

### 1. Core Architecture
- **Backend framework:** FastAPI (Python).
- **Database:** PostgreSQL (local).
- **ORM:** SQLAlchemy with `SessionLocal` and declarative models.
- **Storage:** AWS S3 for resumes, logs, and templates.
- **Parsing Engines:**
  - OpenAI (fallback, slower but stable).
  - Groq Llama 3.1–8B (primary, much faster).

### 2. Implemented Features
- **Environment configuration:** `.env` file with secrets (AWS, DB, LLM API keys).
- **Database schema:**
  - `resumes` table → metadata, S3 URL, parsing model, confidence.
  - `candidates` table → structured fields (name, emails, phones, education, experience, skills, languages).
  - JSONB storage for raw parsed data.
- **Resume ingestion:**
  - Upload API saves files to S3.
  - Extracts raw text (PDF, DOCX, TXT, OCR).
  - Parses into structured JSON via LLM.
  - Saves results into DB.
- **UI:**
  - `/ui/upload` → HTML form to upload resumes.
  - `/ui/candidates` → HTML table listing parsed candidates with filtering.
- **Logging & Monitoring:**
  - Comprehensive logging system with component-specific loggers.
  - Access logs with IP addresses and timestamps.
  - Security event logging.
  - Performance monitoring and statistics.
  - Automatic log cleanup and rotation.
  - **S3 log storage** with batch upload and centralized logging.
  - **Log rotation to S3** with automatic archival.
  - **S3 log cleanup** with configurable retention periods.

### 3. Working Test Cases
- ✅ File upload works via API and UI.  
- ✅ Text extraction confirmed on sample resumes.  
- ✅ Parsing works with Groq (fast) and OpenAI (fallback).  
- ✅ Parsed data saved in PostgreSQL and verified via `psql`.  
- ✅ `parsed_model` column tracks which model parsed each resume.  
- ✅ Candidates show up in `/ui/candidates` with filtering.
- ✅ Comprehensive logging system operational.
- ✅ Access logs capture all HTTP requests with IPs and timestamps.
- ✅ Security events are logged and monitored.
- ✅ Excel export functionality working.
- ✅ Template generation (DOCX/PDF) working.  

---

## ⏭️ Next Steps

### UI Enhancements
- Add **pagination** to candidates page for large datasets.
- Add **candidate detail view** page.
- Improve **mobile responsiveness**.
- Add **bulk operations** (bulk delete, bulk export).

### Data Handling
- Improve **skill normalization** by mapping extracted skills to a master skills table.
- Handle **multiple emails & phone numbers** per candidate.
- Support **multiple resumes per candidate**.
- Add **data validation** and quality checks.

### Deployment / Ops
- **Docker containerization** for easy deployment.
- **Production deployment** scripts and documentation.
- **Database migration** scripts.
- **Backup and recovery** procedures.

---

## ⚙️ Running the Project (Current State)

### 1. Setup environment
```bash
git clone <repo>
cd resume-parser
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
````

### 2. Create `.env` file

```env
# AWS credentials
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET=resume-parser-rishit

# Database
DATABASE_URL=postgresql://<username>@localhost:5432/resume_parser_db

# LLM Keys
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk-...
```

### 3. Initialize DB

```bash
python create_tables.py
```

### 4. Run the server

```bash
uvicorn app.main:app --reload
```

* Upload UI → [http://127.0.0.1:8000/ui/upload](http://127.0.0.1:8000/ui/upload)
* Candidates list → [http://127.0.0.1:8000/ui/candidates](http://127.0.0.1:8000/ui/candidates)

### 5. Verify DB contents

```bash
psql -U <username> -d resume_parser_db -c "SELECT id, candidate_id, parsed_confidence, parsed_model FROM resumes ORDER BY id DESC LIMIT 5;"
```

---

## 📂 Project Structure

```
resume-parser/
│── app/
│   ├── main.py              # FastAPI app (API + UI routes)
│   ├── db.py                # DB engine, session, get_db()
│   ├── models.py            # SQLAlchemy models
│   ├── text_extract.py      # Resume text extraction (PDF, DOCX, OCR)
│   ├── parser_llm.py        # LLM integration (Groq + OpenAI)
│   ├── save_to_db.py        # Store parsed data into DB
│   ├── s3utils.py           # S3 upload/download helpers
│   └── templates/           # Jinja2 HTML templates
│       ├── base.html
│       ├── upload.html
│       └── candidates.html
│── requirements.txt
│── create_tables.py
│── .env
```

---

## 📝 Notes

* Current parsing accuracy is good but **Groq sometimes fails on bad prompts** (returns `BadRequestError`).
* Confidence is hardcoded (`90.0`) for now — need a better scoring system.
* No Docker yet (local run only).

---

## 📚 API Documentation

### Core Endpoints

#### **Resume Upload & Processing**
- `POST /upload` - Upload resume file (API)
- `POST /ui/upload` - Upload resume file (UI form)
- `GET /ui/upload` - Upload form page

#### **Candidate Management**
- `GET /ui/candidates` - List candidates with filtering
- `GET /download/{resume_id}` - Download original resume file

#### **Data Export**
- `GET /export/excel` - Export candidates to Excel
  - Query params: `date_from`, `date_to`, `skills`
- `GET /generate-template/{candidate_id}` - Generate standardized resume
  - Query params: `format` (docx/pdf), `template` (standard/v2)

#### **Monitoring & Health**
- `GET /health` - Basic health check
- `GET /stats` - System statistics
- `GET /logs/recent` - Recent application logs
- `GET /logs/access` - Access logs with IP addresses
- `GET /logs/security` - Security event logs
- `GET /logs/stats` - Log file statistics

#### **Log Management**
- `POST /logs/cleanup` - Clean up old logs (retention_days param)
- `POST /logs/rotate` - Rotate current logs to archives
- `GET /logs/s3` - Get S3 log statistics and recent logs
- `POST /logs/s3/cleanup` - Clean up old S3 logs
- `POST /logs/s3/upload` - Upload current logs to S3

### Filtering Parameters (Candidates Page)
- `search` - Search by candidate name
- `date_from` - Filter from processing date
- `date_to` - Filter to processing date  
- `skills` - Comma-separated skills filter
- `experience_min` - Minimum years of experience
- `experience_max` - Maximum years of experience

### Response Formats

#### **System Statistics** (`/stats`)
```json
{
  "total_candidates": 150,
  "total_resumes": 150,
  "recent_uploads_24h": 5,
  "parsing_success_rate": 94.2,
  "model_usage": {
    "groq-llama-3.1-8b": 120,
    "openai-gpt-4": 30
  },
  "timestamp": "2024-01-15T10:30:45"
}
```

#### **Access Logs** (`/logs/access`)
```json
{
  "access_logs": [
    "ACCESS - IP: 192.168.1.100 | GET /ui/candidates | Status: 200 | Time: 0.045s | UA: Mozilla/5.0...",
    "ACCESS - IP: 192.168.1.100 | POST /ui/upload | Status: 200 | Time: 2.456s | UA: Mozilla/5.0..."
  ],
  "count": 2
}
```

---

## 🚀 Roadmap

1. ✅ ~~Fix UI blank page issue~~ - **COMPLETED**
2. ✅ ~~Add Excel export with filters~~ - **COMPLETED**  
3. ✅ ~~Add standardized resume DOCX/PDF generation~~ - **COMPLETED**
4. ✅ ~~Add logging + Cert-In compliance features~~ - **COMPLETED**
5. **Improve skill mapping and master data tables**
6. **Docker containerization for deployment**
7. **Production deployment documentation**

---

## 🐞 Debugging Common Errors

### 1. `RuntimeError: S3_BUCKET env var not set`

* Ensure `.env` file exists with `S3_BUCKET=...`.
* Run with:

  ```bash
  source .venv/bin/activate
  uvicorn app.main:app --reload
  ```

### 2. `OperationalError: role "username" does not exist`

* Your `.env` has a placeholder DB URL.
* Fix it to use your real Postgres user:

  ```env
  DATABASE_URL=postgresql://vipulswarup@localhost:5432/resume_parser_db
  ```

### 3. Blank `/ui/upload` page

* Ensure `app/templates/upload.html` exists and extends `base.html`.
* Check template path in `main.py`:

  ```python
  templates = Jinja2Templates(directory="app/templates")
  ```

### 4. `ImportError: cannot import name 'get_db'`

* Add `get_db()` to `app/db.py`:

  ```python
  def get_db():
      db = SessionLocal()
      try:
          yield db
      finally:
          db.close()
  ```

### 5. `groq.GroqError: The api_key client option must be set`

* Ensure `.env` has:

  ```env
  GROQ_API_KEY=gsk-...
  ```
* Call `load_dotenv()` before using Groq client.

### 6. `Invalid JSON` from LLM

* Happens when the model responds with text outside strict JSON.
* Current code falls back to OpenAI if Groq fails.

