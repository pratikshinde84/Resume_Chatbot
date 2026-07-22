from typing import Generator
from app.database.connection import SessionLocal

def get_db() -> Generator:
    """Dependency injector for database session."""
    db = SessionLocal()
    try:
        yield db 
    finally:
        db.close()
