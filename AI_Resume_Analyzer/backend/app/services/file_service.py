import os
import shutil
from pathlib import Path
from fastapi import UploadFile
from app.core.config import settings

def get_user_upload_dir(user_id: str) -> Path:
    upload_dir = Path(settings.UPLOAD_DIR) / user_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir

def save_uploaded_file(file: UploadFile, user_id: str) -> str:
    user_dir = get_user_upload_dir(user_id)
    file_path = user_dir / file.filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return str(file_path.absolute())

def delete_user_file(user_id: str, filename: str) -> bool:
    user_dir = Path(settings.UPLOAD_DIR) / user_id
    file_path = user_dir / filename
    
    if file_path.exists():
        os.remove(file_path)
        
        # If the directory is now empty, delete it
        if not os.listdir(user_dir):
            shutil.rmtree(user_dir)
        return True
    return False

def delete_all_user_files(user_id: str) -> bool:
    user_dir = Path(settings.UPLOAD_DIR) / user_id
    if user_dir.exists() and user_dir.is_dir():
        shutil.rmtree(user_dir)
        return True
    return False

def check_file_exists(user_id: str, filename: str) -> bool:
    user_dir = Path(settings.UPLOAD_DIR) / user_id
    file_path = user_dir / filename
    return file_path.exists()
