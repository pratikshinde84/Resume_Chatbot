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


def list_resume_files() -> list[str]:
    if not RESUMES_DIR.exists():
        return []
    return sorted([f.name for f in RESUMES_DIR.iterdir() if f.is_file() and f.suffix.lower() == ".pdf"])


@app.get("/resumes")
@app.get("/resumes/")
def get_resumes():
    return {"resumes": list_resume_files()}


@app.post("/rebuild")
@app.post("/rebuild/")
@app.get("/rebuild")
@app.get("/rebuild/")
def rebuild_index():
    try:
        from ingest import ingest_resumes
        ingest_resumes()
        return {"status": "success", "message": "Resume vector database rebuilt."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


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
