import os
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.common import ApiResponse
from app.schemas.user import (
    StartSessionRequest,
    UserResponse,
    UploadedPDFResponse,
    DeletePDFRequest,
    DeleteAllPDFsRequest,
    AskRequest,
    AskResponse
)
from app.services import db_service, file_service
from app.rag import pinecone_service, rag_chain

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/start-session", response_model=ApiResponse[UserResponse])
def start_session(payload: StartSessionRequest, db: Session = Depends(get_db)):
    """
    Initializes a session for the user. Creates a user in the SQLite database if 
    they do not exist. Returns the user details. 
    Per requirements, this does NOT wipe out vectors/files unless explicitly requested by the user,
    allowing persistence across sessions.
    """
    try:
        user = db_service.get_or_create_user(db, payload)
        # Convert SQLAlchemy model to Pydantic Response schema
        user_resp = UserResponse.model_validate(user)
        return ApiResponse(
            success=True,
            message="Session started successfully",
            data=user_resp
        )
    except Exception as e:
        logger.error(f"Error in /start-session: {e}")
        return ApiResponse(
            success=False,
            message=f"Could not start session: {str(e)}"
        )

@router.post("/upload-pdf", response_model=ApiResponse[UploadedPDFResponse])
async def upload_pdf(
    userId: str = Form(...),
    pdf: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Uploads a resume PDF, saves it locally, extracts, splits, embeds, and uploads chunks 
    to the Pinecone namespace matching the userId, then records file metadata in SQLite.
    """
    try:
        # 1. Validate user exists
        user = db_service.get_user_by_id(db, userId)
        if not user:
            return ApiResponse(
                success=False,
                message="User not found. Please call /start-session first."
            )

        # Validate file type
        if not pdf.filename.endswith(".pdf"):
            return ApiResponse(
                success=False,
                message="Invalid file type. Only PDF files are allowed."
            )

        # 2. Save file locally
        local_path = file_service.save_uploaded_file(pdf, userId)

        # 3. Parse, chunk, and embed to Pinecone
        try:
            num_pages = pinecone_service.index_pdf_file(local_path, userId)
        except Exception as rag_err:
            logger.error(f"Failed to parse and index PDF: {rag_err}")
            # Clean up the local file if indexing fails
            file_service.delete_user_file(userId, pdf.filename)
            return ApiResponse(
                success=False,
                message=f"Failed to process and index PDF: {str(rag_err)}"
            )

        # 4. Save metadata in SQLite
        db_pdf = db_service.add_uploaded_pdf_metadata(
            db=db,
            user_id=userId,
            filename=pdf.filename,
            pages=num_pages,
            filepath=local_path
        )

        return ApiResponse(
            success=True,
            message="PDF uploaded and indexed successfully",
            data=UploadedPDFResponse.model_validate(db_pdf)
        )
    except Exception as e:
        logger.error(f"Unhandled error in /upload-pdf: {e}")
        return ApiResponse(
            success=False,
            message=f"An error occurred during file upload: {str(e)}"
        )

@router.get("/uploaded-pdfs", response_model=ApiResponse[list[UploadedPDFResponse]])
def get_uploaded_pdfs(userId: str, db: Session = Depends(get_db)):
    """
    Retrieves the list of uploaded PDFs for the user with their page counts.
    """
    try:
        user = db_service.get_user_by_id(db, userId)
        if not user:
            return ApiResponse(
                success=False,
                message="User not found."
            )

        pdfs = db_service.get_uploaded_pdfs_for_user(db, userId)
        data = [UploadedPDFResponse.model_validate(pdf) for pdf in pdfs]
        return ApiResponse(
            success=True,
            message="Uploaded PDFs retrieved successfully",
            data=data
        )
    except Exception as e:
        logger.error(f"Error in /uploaded-pdfs: {e}")
        return ApiResponse(
            success=False,
            message=f"Failed to retrieve PDFs: {str(e)}"
        )

@router.delete("/delete-pdf", response_model=ApiResponse[dict])
def delete_pdf(payload: DeletePDFRequest, db: Session = Depends(get_db)):
    """
    Deletes a single PDF. Deletes the local file, all corresponding Pinecone vectors, 
    and removes the file metadata from SQLite.
    """
    try:
        user = db_service.get_user_by_id(db, payload.userId)
        if not user:
            return ApiResponse(
                success=False,
                message="User not found."
            )

        # Check if file exists in SQLite metadata
        pdfs = db_service.get_uploaded_pdfs_for_user(db, payload.userId)
        file_meta = next((pdf for pdf in pdfs if pdf.filename == payload.filename), None)
        if not file_meta:
            return ApiResponse(
                success=False,
                message=f"PDF '{payload.filename}' not found for user."
            )

        # 1. Delete local file
        file_service.delete_user_file(payload.userId, payload.filename)

        # 2. Delete vectors from Pinecone using filename filter
        pinecone_service.delete_vectors_by_filename(payload.userId, payload.filename)

        # 3. Remove metadata from SQLite
        db_service.remove_uploaded_pdf_metadata(db, payload.userId, payload.filename)

        return ApiResponse(
            success=True,
            message=f"PDF '{payload.filename}' deleted successfully",
            data={}
        )
    except Exception as e:
        logger.error(f"Error in /delete-pdf: {e}")
        return ApiResponse(
            success=False,
            message=f"Failed to delete PDF: {str(e)}"
        )

@router.delete("/delete-all-pdfs", response_model=ApiResponse[dict])
def delete_all_pdfs(payload: DeleteAllPDFsRequest, db: Session = Depends(get_db)):
    """
    Deletes all uploaded PDFs for the user. Removes all local files, deletes 
    the entire Pinecone namespace, and clears the file metadata from SQLite.
    """
    try:
        user = db_service.get_user_by_id(db, payload.userId)
        if not user:
            return ApiResponse(
                success=False,
                message="User not found."
            )

        # 1. Delete all local files
        file_service.delete_all_user_files(payload.userId)

        # 2. Delete all vectors in Pinecone namespace
        pinecone_service.delete_all_vectors_for_user(payload.userId)

        # 3. Clear SQLite metadata
        db_service.remove_all_pdfs_metadata_for_user(db, payload.userId)

        return ApiResponse(
            success=True,
            message="All PDFs and vectors deleted successfully",
            data={}
        )
    except Exception as e:
        logger.error(f"Error in /delete-all-pdfs: {e}")
        return ApiResponse(
            success=False,
            message=f"Failed to delete all PDFs: {str(e)}"
        )

@router.post("/ask", response_model=ApiResponse[AskResponse])
def ask_question(payload: AskRequest, db: Session = Depends(get_db)):
    """
    Queries the RAG chatbot using context matching the user's Pinecone namespace.
    """
    try:
        user = db_service.get_user_by_id(db, payload.userId)
        if not user:
            return ApiResponse(
                success=False,
                message="User not found. Please call /start-session first."
            )

        # Check if they have uploaded files
        pdfs = db_service.get_uploaded_pdfs_for_user(db, payload.userId)
        if not pdfs:
            return ApiResponse(
                success=False,
                message="No resumes uploaded yet. Please upload files to ask questions."
            )

        # Perform RAG query
        answer = rag_chain.query_rag_chain(payload.userId, payload.question)
        
        return ApiResponse(
            success=True,
            message="Question answered successfully",
            data=AskResponse(answer=answer)
        )
    except Exception as e:
        logger.error(f"Error in /ask: {e}")
        return ApiResponse(
            success=False,
            message=f"Failed to generate answer: {str(e)}"
        )

@router.get("/health")
def health_check():
    """Simple check for service health."""
    return {
        "success": True,
        "message": "Healthy",
        "data": {}
    }
