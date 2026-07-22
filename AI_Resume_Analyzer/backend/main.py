import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.database.connection import engine
from app.database.base import Base
from app.rag.pinecone_service import init_pinecone_index
from app.api.endpoints import router as api_router

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("backend_main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    logger.info("Creating SQLite tables...")
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise e

    # Pinecone Index initialization
    logger.info("Checking/Creating Pinecone Index...")
    try:
        init_pinecone_index()
    except Exception as e:
        logger.error(f"Pinecone initialization failed: {e}. Index might need to be created manually or API Keys are invalid.")
    
    yield
    # Shutdown actions (none)

app = FastAPI(
    title="Resume RAG Chatbot Backend",
    description="Production-quality FastAPI backend for Multi-PDF Resume RAG chatbot built with LangChain, Pinecone, and Gemini",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global Custom Exception Handlers to match User requirements ---

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Formats validation errors into the custom API envelope."""
    errors = exc.errors()
    messages = []
    for err in errors:
        loc = " -> ".join(str(l) for l in err["loc"] if l != "body")
        messages.append(f"{loc}: {err['msg']}")
    
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "; ".join(messages),
            "data": None
        }
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Formats HTTP exceptions into the custom API envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "data": None
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Fallback handler for generic internal server errors."""
    logger.error(f"Internal server error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal Server Error. Please check backend logs.",
            "data": None
        }
    )

# Include API Router
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    # Enable running the app directly via 'python main.py'
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
