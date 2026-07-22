import os
import logging
from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from langchain_google_genai import GoogleGenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Pinecone Client
pc = Pinecone(api_key=settings.PINECONE_API_KEY)

def init_pinecone_index():
    """Ensure that the Pinecone index exists. Create it if not."""
    try:
        existing_indexes = [idx.name for idx in pc.list_indexes()]
        if settings.PINECONE_INDEX_NAME not in existing_indexes:
            logger.info(f"Creating Pinecone index: {settings.PINECONE_INDEX_NAME}")
            pc.create_index(
                name=settings.PINECONE_INDEX_NAME,
                dimension=768,  # dimension for models/embedding-001
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
        else:
            logger.info(f"Pinecone index {settings.PINECONE_INDEX_NAME} already exists.")
    except Exception as e:
        logger.error(f"Error initializing Pinecone index: {e}")
        raise e

def get_embeddings_model():
    return GoogleGenAIEmbeddings(
        model="models/embedding-001",
        google_api_key=settings.GEMINI_API_KEY
    )

def index_pdf_file(file_path: str, user_id: str) -> int:
    """
    Parses a PDF file, splits it into chunks, embeds, and uploads to Pinecone.
    Returns the number of pages processed.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # Load PDF
    loader = PyPDFLoader(file_path)
    docs = loader.load()
    num_pages = len(docs)

    filename = os.path.basename(file_path)

    # Preprocess document metadata
    for doc in docs:
        doc.metadata = {
            "userId": user_id,
            "filename": filename,
            "page": doc.metadata.get("page", 0) + 1  # Make pages 1-indexed
        }

    # Split documents
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP
    )
    chunks = text_splitter.split_documents(docs)

    # Embed and upload to Pinecone
    embeddings = get_embeddings_model()
    
    # Initialize connection to vector store
    PineconeVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings,
        index_name=settings.PINECONE_INDEX_NAME,
        namespace=user_id
    )

    logger.info(f"Successfully indexed {filename} for user {user_id}. {len(chunks)} chunks uploaded.")
    return num_pages

def delete_all_vectors_for_user(user_id: str):
    """Delete the entire namespace for a user in Pinecone."""
    try:
        index = pc.Index(settings.PINECONE_INDEX_NAME)
        index.delete(delete_all=True, namespace=user_id)
        logger.info(f"Successfully deleted all Pinecone vectors for namespace: {user_id}")
    except Exception as e:
        logger.warning(f"Failed to delete all vectors for user {user_id}: {e}")

def delete_vectors_by_filename(user_id: str, filename: str):
    """Delete all vectors for a specific file inside a user's namespace."""
    try:
        index = pc.Index(settings.PINECONE_INDEX_NAME)
        index.delete(filter={"filename": filename}, namespace=user_id)
        logger.info(f"Successfully deleted Pinecone vectors for file '{filename}' in namespace '{user_id}'")
    except Exception as e:
        logger.warning(f"Failed to delete vectors for {filename} under user {user_id}: {e}")

def get_vector_store(user_id: str) -> PineconeVectorStore:
    """Get vector store instance bounded to the user's namespace."""
    embeddings = get_embeddings_model()
    return PineconeVectorStore(
        index_name=settings.PINECONE_INDEX_NAME,
        embedding=embeddings,
        namespace=user_id
    )
