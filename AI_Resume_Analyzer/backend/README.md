# Multi-PDF Resume RAG Chatbot Backend

A production-quality, modular FastAPI backend that leverages **LangChain**, **Pinecone**, and **Google Gemini** to build a Retrieval-Augmented Generation (RAG) system for resume parsing and questioning. 

Designed specifically as a backend for an Android application, this service uses REST APIs and maintains persistent user profile data in SQLite while allowing resume files and vector embeddings to be managed dynamically.

---

## Technical Stack
- **Framework:** FastAPI, Uvicorn
- **Language:** Python 3.12+
- **Database:** SQLite + SQLAlchemy (ORM)
- **RAG Engine:** LangChain (Latest v0.2+ APIs)
  - `GoogleGenAIEmbeddings` (`models/embedding-001`)
  - `ChatGoogleGenerativeAI` (`gemini-1.5-flash`)
  - `PineconeVectorStore`
  - `PyPDFLoader` & `RecursiveCharacterTextSplitter`
- **Vector DB:** Pinecone (Single index with user-specific namespaces)

---

## Setup & Running Instructions

### 1. Prerequisites
Ensure you have Python 3.12 or newer installed on your machine.

### 2. Create and Activate Virtual Environment
From the `backend/` directory, run:
```bash
# Windows PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configuration (.env)
Copy the `.env.example` to a new `.env` file:
```bash
cp .env.example .env
```
Open the `.env` file and populate it with your API keys:
```ini
GEMINI_API_KEY=your_gemini_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=resume-rag
DATABASE_URL=sqlite:///./users.db
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K=4
```

### 5. Running the Application
Run the backend using Uvicorn:
```bash
uvicorn main:app --reload --port 8000
```
The API documentation will be available at: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## API Documentation & cURL Examples

All responses follow the envelope format:
- **Success:** `{"success": true, "message": "...", "data": {...}}`
- **Error:** `{"success": false, "message": "..."}`

### 1. Start Session
Registers/Retrieves a user profile. It does NOT wipe user data or PDFs unless manually deleted.
- **Endpoint:** `POST /start-session`
- **Payload:**
```json
{
    "userId": "PRATIK123",
    "name": "Pratik",
    "email": "pratik@gmail.com"
}
```
- **cURL Command:**
```bash
curl -X POST http://localhost:8000/start-session \
  -H "Content-Type: application/json" \
  -d '{"userId": "PRATIK123", "name": "Pratik", "email": "pratik@gmail.com"}'
```

---

### 2. Upload PDF
Uploads a resume PDF. Chunks are generated, embedded, and stored in the user's Pinecone namespace.
- **Endpoint:** `POST /upload-pdf`
- **Content-Type:** `multipart/form-data`
- **cURL Command:**
```bash
curl -X POST http://localhost:8000/upload-pdf \
  -F "userId=PRATIK123" \
  -F "pdf=@/path/to/your/Resume.pdf"
```

---

### 3. List Uploaded PDFs
Retrieves all uploaded documents and their page count for a user.
- **Endpoint:** `GET /uploaded-pdfs?userId=PRATIK123`
- **cURL Command:**
```bash
curl -X GET "http://localhost:8000/uploaded-pdfs?userId=PRATIK123"
```

---

### 4. Ask Question
Queries the Gemini RAG chain inside the user's Pinecone namespace.
- **Endpoint:** `POST /ask`
- **Payload:**
```json
{
    "userId": "PRATIK123",
    "question": "What is Pratik's experience with Python?"
}
```
- **cURL Command:**
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"userId": "PRATIK123", "question": "What is Pratik's experience with Python?"}'
```

---

### 5. Delete Single PDF
Removes a specific PDF, its local file copy, and deletes its matching vectors from Pinecone.
- **Endpoint:** `DELETE /delete-pdf`
- **Payload:**
```json
{
    "userId": "PRATIK123",
    "filename": "Resume.pdf"
}
```
- **cURL Command:**
```bash
curl -X DELETE http://localhost:8000/delete-pdf \
  -H "Content-Type: application/json" \
  -d '{"userId": "PRATIK123", "filename": "Resume.pdf"}'
```

---

### 6. Delete All PDFs
Deletes all files and clears the entire user namespace from Pinecone.
- **Endpoint:** `DELETE /delete-all-pdfs`
- **Payload:**
```json
{
    "userId": "PRATIK123"
}
```
- **cURL Command:**
```bash
curl -X DELETE http://localhost:8000/delete-all-pdfs \
  -H "Content-Type: application/json" \
  -d '{"userId": "PRATIK123"}'
```

---

### 7. Health Check
- **Endpoint:** `GET /health`
- **cURL Command:**
```bash
curl -X GET http://localhost:8000/health
```

---

## Folder Structure & Code Quality (SOLID)
- **Modular Design:** The project isolates database access (`services/db_service.py`), local storage (`services/file_service.py`), settings loader (`core/config.py`), vector database operations (`rag/pinecone_service.py`), and response formatting into separate, testable services.
- **Single Responsibility (SRP):** API routing is clean and relies on dependency injection. DB connections and config values are decoupled.
- **Robust Exception Handling:** Customized FastAPI middleware wraps validation errors and runtime exceptions to return user-specified format standards, preventing raw traceback disclosures.
