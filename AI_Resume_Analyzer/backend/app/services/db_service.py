from sqlalchemy.orm import Session
from app.models.user import User, UploadedPDF
from app.schemas.user import StartSessionRequest

def get_user_by_id(db: Session, user_id: str) -> User | None:
    return db.query(User).filter(User.userId == user_id).first()

def create_user(db: Session, user_data: StartSessionRequest) -> User:
    db_user = User(
        userId=user_data.userId,
        name=user_data.name,
        email=user_data.email
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_or_create_user(db: Session, user_data: StartSessionRequest) -> User:
    db_user = get_user_by_id(db, user_data.userId)
    if not db_user:
        db_user = create_user(db, user_data)
    return db_user

def get_uploaded_pdfs_for_user(db: Session, user_id: str) -> list[UploadedPDF]:
    return db.query(UploadedPDF).filter(UploadedPDF.userId == user_id).all()

def add_uploaded_pdf_metadata(
    db: Session, user_id: str, filename: str, pages: int, filepath: str
) -> UploadedPDF:
    # Check if duplicate filename exists for this user, if so update it
    existing_pdf = db.query(UploadedPDF).filter(
        UploadedPDF.userId == user_id,
        UploadedPDF.filename == filename
    ).first()
    
    if existing_pdf:
        existing_pdf.pages = pages
        existing_pdf.filepath = filepath
        db.commit()
        db.refresh(existing_pdf)
        return existing_pdf
        
    db_pdf = UploadedPDF(
        userId=user_id,
        filename=filename,
        pages=pages,
        filepath=filepath
    )
    db.add(db_pdf)
    db.commit()
    db.refresh(db_pdf)
    return db_pdf

def remove_uploaded_pdf_metadata(db: Session, user_id: str, filename: str) -> bool:
    pdf = db.query(UploadedPDF).filter(
        UploadedPDF.userId == user_id,
        UploadedPDF.filename == filename
    ).first()
    if pdf:
        db.delete(pdf)
        db.commit()
        return True
    return False

def remove_all_pdfs_metadata_for_user(db: Session, user_id: str) -> int:
    deleted_count = db.query(UploadedPDF).filter(UploadedPDF.userId == user_id).delete()
    db.commit()
    return deleted_count
