import os
import pickle
from functools import lru_cache
from typing import Any, Dict, List, Tuple

import faiss
import numpy as np
from dotenv import load_dotenv
from groq import Groq
from sentence_transformers import SentenceTransformer

# Load environment variables from the project .env file
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

VECTOR_DB_DIR = os.path.join(os.path.dirname(__file__), "vector_db")
DB_FILE_PATH = os.path.join(VECTOR_DB_DIR, "faiss_index.pkl")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "all-MiniLM-L6-v2")
LLM_MODEL = "llama-3.1-8b-instant"


@lru_cache(maxsize=1)
def get_embed_model() -> SentenceTransformer:
    return SentenceTransformer(EMBED_MODEL, device="cpu")


def is_db_initialized() -> bool:
    """Checks whether the vector database file exists."""
    return os.path.exists(DB_FILE_PATH)


def load_vector_db() -> Tuple[faiss.Index, List[str], List[Dict[str, Any]]]:
    """Loads the FAISS index, text chunks, and metadata from the local pickle file."""
    if not is_db_initialized():
        raise FileNotFoundError("Vector database not found. Please run ingest.py first.")

    with open(DB_FILE_PATH, "rb") as handle:
        db_data = pickle.load(handle)

    if "index_bytes" in db_data:
        index = faiss.deserialize_index(db_data["index_bytes"])
    elif "index" in db_data:
        index = db_data["index"]
    else:
        raise KeyError("The vector database is missing the FAISS index payload.")

    return index, db_data["chunks"], db_data["metadata"]


def query_rag(query_text: str, top_k: int = 4) -> Tuple[str, List[Dict[str, Any]]]:
    """Retrieve relevant resume chunks and use Groq to answer the query."""
    index, chunks, metadata = load_vector_db()

    model = get_embed_model()
    query_emb = model.encode([query_text], convert_to_numpy=True, normalize_embeddings=True)[0]
    query_emb = np.array([query_emb], dtype="float32")
    faiss.normalize_L2(query_emb)

    distances, indices = index.search(query_emb, top_k)

    retrieved_sources = []
    context_parts = []
    for rank, idx in enumerate(indices[0]):
        if idx < 0:
            continue

        chunk_text = chunks[idx]
        meta = metadata[idx]
        score = float(distances[0][rank])

        retrieved_sources.append(
            {
                "text": chunk_text,
                "source": meta["source"],
                "candidate": meta["candidate"],
                "score": score,
            }
        )
        context_parts.append(
            f"--- Candidate: {meta['candidate']} (Source: {meta['source']}) ---\n{chunk_text}"
        )

    context_str = "\n\n".join(context_parts)
    system_prompt = (
        "You are an expert HR recruitment assistant. Answer user questions about candidates "
        "based only on the provided resume details. If the context does not contain enough "
        "information, say so clearly and do not make up facts."
    )
    prompt = f"""{system_prompt}

Use the context below to answer the user query:

{context_str}

---
User Query: {query_text}

Answer using only the resumes above."""

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set.")

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=600,
    )
    answer = response.choices[0].message.content
    return answer, retrieved_sources


if __name__ == "__main__":
    if is_db_initialized():
        print("Testing RAG Query...")
        query = "Who has experience with PyTorch and Machine Learning?"
        print(f"Query: {query}\n")
        ans, sources = query_rag(query)
        print(f"Answer:\n{ans}\n")
        print("Sources:")
        for s in sources:
            print(f"- Candidate: {s['candidate']} ({s['source']}) [Score: {s['score']:.4f}]")
    else:
        print("Vector database is not initialized. Please run ingest.py first.")
