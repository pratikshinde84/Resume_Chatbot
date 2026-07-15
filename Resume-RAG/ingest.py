import os
import pickle
from functools import lru_cache

import numpy as np
import faiss
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from utils import extract_text_from_pdf, recursive_split_text

# Load environment variables
load_dotenv()

# Configuration
RESUMES_DIR = os.path.join(os.path.dirname(__file__), "resumes")
VECTOR_DB_DIR = os.path.join(os.path.dirname(__file__), "vector_db")
DB_FILE_PATH = os.path.join(VECTOR_DB_DIR, "faiss_index.pkl")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "all-MiniLM-L6-v2")
EMBED_BATCH_SIZE = int(os.environ.get("EMBED_BATCH_SIZE", "8"))
MAX_CHUNK_SIZE = int(os.environ.get("MAX_CHUNK_SIZE", "700"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "120"))


@lru_cache(maxsize=1)
def get_embed_model() -> SentenceTransformer:
    return SentenceTransformer(EMBED_MODEL, device="cpu")


def ingest_resumes():
    print("Starting resume ingestion...")
    
    # 1. Ensure directories exist
    if not os.path.exists(RESUMES_DIR):
        print(f"Resumes directory '{RESUMES_DIR}' does not exist. Creating it.")
        os.makedirs(RESUMES_DIR, exist_ok=True)
    os.makedirs(VECTOR_DB_DIR, exist_ok=True)
    
    # 2. Get list of PDFs
    pdf_files = [f for f in os.listdir(RESUMES_DIR) if f.endswith(".pdf")]
    if not pdf_files:
        print(f"No PDF resumes found in '{RESUMES_DIR}'. Please add PDF resumes first.")
        return
        
    print(f"Found {len(pdf_files)} PDF resume(s) for ingestion.")
    
    # 3. Extract and chunk text
    all_chunks = []
    all_metadata = []
    
    for filename in pdf_files:
        pdf_path = os.path.join(RESUMES_DIR, filename)
        candidate_name = os.path.splitext(filename)[0].capitalize()
        print(f"Processing: {filename} ({candidate_name})")
        
        try:
            text = extract_text_from_pdf(pdf_path)
            chunks = recursive_split_text(text, max_chunk_size=MAX_CHUNK_SIZE, overlap=CHUNK_OVERLAP)
            print(f"  - Extracted {len(text)} characters, split into {len(chunks)} chunks.")
            
            for idx, chunk in enumerate(chunks):
                all_chunks.append(chunk)
                all_metadata.append({
                    "source": filename,
                    "candidate": candidate_name,
                    "chunk_id": idx
                })
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            
    if not all_chunks:
        print("No text chunks generated. Ingestion aborted.")
        return

    # 4. Generate embeddings in small batches to keep memory usage low on Render
    print(f"Generating embeddings using {EMBED_MODEL} in batches of {EMBED_BATCH_SIZE}...")
    try:
        model = get_embed_model()
        index = None
        batch_start = 0

        while batch_start < len(all_chunks):
            batch_end = min(batch_start + EMBED_BATCH_SIZE, len(all_chunks))
            batch_chunks = all_chunks[batch_start:batch_end]
            batch_embeddings = model.encode(
                batch_chunks,
                batch_size=EMBED_BATCH_SIZE,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
            batch_embeddings = np.asarray(batch_embeddings, dtype="float32")
            if batch_embeddings.ndim == 1:
                batch_embeddings = batch_embeddings.reshape(1, -1)

            if index is None:
                index = faiss.IndexFlatIP(batch_embeddings.shape[1])

            embeddings_normalized = batch_embeddings / (
                np.linalg.norm(batch_embeddings, axis=1, keepdims=True) + 1e-9
            )
            faiss.normalize_L2(embeddings_normalized)
            index.add(embeddings_normalized.astype("float32"))
            batch_start = batch_end

        print(f"Generated {len(all_chunks)} embeddings successfully.")
    except Exception as e:
        print(f"Error during embedding generation: {e}")
        return

    print(f"FAISS index created with {index.ntotal} vectors.")
    
    # 6. Save to pickle
    os.makedirs(VECTOR_DB_DIR, exist_ok=True)
    with open(DB_FILE_PATH, "wb") as f:
        pickle.dump(
            {
                "index_bytes": faiss.serialize_index(index),
                "chunks": all_chunks,
                "metadata": all_metadata,
            },
            f,
        )
    
    print(f"Vector database saved to {DB_FILE_PATH}.")
    print("\n=== Resume Ingestion Complete ===")
    print(f"Total resumes: {len(pdf_files)}")
    print(f"Total chunks: {len(all_chunks)}")
    print(f"Embeddings generated: {index.ntotal}")

if __name__ == "__main__":
    ingest_resumes()
