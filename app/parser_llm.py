import os, json
from tenacity import retry, wait_exponential, stop_after_attempt
from dotenv import load_dotenv

# Always load .env explicitly
import os
from pathlib import Path

# Get the project root directory (one level up from app/)
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"

# Load .env from project root
load_dotenv(dotenv_path=env_path)

# --- Groq client (primary) ---
try:
    from groq import Groq
    groq_api_key = os.getenv("GROQ_API_KEY")
    print(f"[DEBUG] Groq API key found: {bool(groq_api_key)}")
    if groq_api_key:
        groq_client = Groq(api_key=groq_api_key)
        print("[DEBUG] Groq client initialized successfully")
    else:
        groq_client = None
        print("[DEBUG] No Groq API key found")
except ImportError:
    groq_client = None
    print("[DEBUG] Groq import failed")
except Exception as e:
    groq_client = None
    print(f"[DEBUG] Groq client initialization failed: {e}")

# --- OpenAI client (fallback) - lazy initialization ---
openai_client = None

def get_openai_client():
    """Get OpenAI client with lazy initialization"""
    global openai_client
    if openai_client is None:
        try:
            from openai import OpenAI
            openai_api_key = os.getenv("OPENAI_API_KEY")
            print(f"[DEBUG] OpenAI API key found: {bool(openai_api_key)}")
            if openai_api_key:
                openai_client = OpenAI(api_key=openai_api_key)
                print("[DEBUG] OpenAI client initialized successfully")
            else:
                print("[DEBUG] No OpenAI API key found")
        except (ImportError, Exception) as e:
            print(f"[DEBUG] OpenAI client initialization failed: {e}")
            openai_client = None
    return openai_client


PROMPT_TEMPLATE = """
You are a resume parser. 
Extract the following fields from the resume text and return ONLY JSON, no explanation:

{
  "full_name": "",
  "emails": [],
  "phones": [],
  "location": "",
  "linkedin_url": "",
  "current_role": "",
  "current_employer": "",
  "total_experience_years": "",
  "current_salary": "",
  "expected_salary": "",
  "notice_period": "",
  "education": [
    {"degree": "", "institution": "", "major": "", "graduation_year": ""}
  ],
  "experience": [
    {"job_title": "", "organization": "", "location": "", "reporting_to": "", 
     "start_date": "", "end_date": "", "roles_responsibilities": "", "achievements": ""}
  ],
  "skills": [],
  "languages": []
}

Resume text:
----------------
{resume_text}
"""


def _clean_json(raw: str) -> str:
    """Strip markdown fences and json prefix."""
    content = raw.strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:].strip()
    return content


@retry(wait=wait_exponential(min=1, max=10), stop=stop_after_attempt(3))
def _call_groq(prompt: str, model: str) -> dict:
    resp = groq_client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt[:4000]}],
        temperature=0,
    )
    content = _clean_json(resp.choices[0].message.content)
    parsed = json.loads(content)
    parsed["_model_used"] = f"Groq:{model}"
    return parsed


@retry(wait=wait_exponential(min=1, max=10), stop=stop_after_attempt(3))
def _call_openai(prompt: str) -> dict:
    client = get_openai_client()
    if not client:
        raise Exception("OpenAI client not available")
    
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt[:6000]}],
        temperature=0,
    )
    content = _clean_json(resp.choices[0].message.content)
    parsed = json.loads(content)
    parsed["_model_used"] = "OpenAI:gpt-4o-mini"
    return parsed


def parse_with_llm(resume_text: str) -> dict:
    """Try Groq instant, then Groq 70B, then OpenAI."""
    prompt = PROMPT_TEMPLATE.replace("{resume_text}", resume_text)

    # Check if we have any working clients
    groq_available = groq_client is not None
    openai_available = get_openai_client() is not None
    
    print(f"[DEBUG] Groq available: {groq_available}, OpenAI available: {openai_available}")
    
    if not groq_available and not openai_available:
        return {"error": "No LLM clients available - check API keys"}

    try:
        if groq_client:
            return _call_groq(prompt, "llama-3.1-8b-instant")
    except Exception as e:
        print(f"[WARN] Groq 8B failed: {e}")

    try:
        if groq_client:
            return _call_groq(prompt, "llama-3.1-70b-versatile")
    except Exception as e:
        print(f"[WARN] Groq 70B failed: {e}")

    try:
        if get_openai_client():
            return _call_openai(prompt)
    except Exception as e:
        print(f"[ERROR] OpenAI failed: {e}")

    return {"error": "Parsing failed with Groq and OpenAI"}
