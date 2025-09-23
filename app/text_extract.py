import os
import mimetypes
import pdfplumber
import docx
import pytesseract
from PIL import Image
import magic  # python-magic

def extract_text(filepath: str) -> str:
    """Extract text from PDF, DOCX, TXT, or image file"""
    mime = magic.Magic(mime=True).from_file(filepath)

    if mime == "application/pdf":
        return extract_pdf(filepath)
    elif mime in ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"):
        return extract_docx(filepath)
    elif mime.startswith("text/"):
        return extract_txt(filepath)
    elif mime.startswith("image/"):
        return extract_image(filepath)
    else:
        raise ValueError(f"Unsupported file type: {mime}")

def extract_pdf(filepath: str) -> str:
    text = []
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            text.append(page.extract_text() or "")
    return "\n".join(text)

def extract_docx(filepath: str) -> str:
    doc = docx.Document(filepath)
    return "\n".join([p.text for p in doc.paragraphs])

def extract_txt(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def extract_image(filepath: str) -> str:
    img = Image.open(filepath)
    return pytesseract.image_to_string(img)
