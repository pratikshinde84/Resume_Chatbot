from fastapi import FastAPI, File, UploadFile, HTTPException
from pathlib import Path
import os
import re

app = FastAPI(title="Resume Upload API")

BASE_DIR = Path(__file__).resolve().parent
RESUMES_DIR = BASE_DIR / "resumes"
RESUMES_DIR.mkdir(exist_ok=True)


def sanitize_filename(filename: str) -> str:
    safe_name = os.path.basename(filename)
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", safe_name)
    if not safe_name.lower().endswith(".pdf"):
        safe_name += ".pdf"
    return safe_name


@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    filename = sanitize_filename(file.filename)
    save_path = RESUMES_DIR / filename

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    with save_path.open("wb") as f:
        f.write(contents)

    return {
        "message": "Resume uploaded successfully.",
        "filename": filename,
        "stored_path": str(save_path.relative_to(BASE_DIR)),
    }


@app.get("/")
def read_root():
    return {"message": "Resume Upload API is running. POST a PDF to /upload-resume."}
