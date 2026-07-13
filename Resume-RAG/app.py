import streamlit as st
import os
import sys
from dotenv import load_dotenv

# Ensure the app can find local modules
app_dir = os.path.dirname(os.path.abspath(__file__))
if app_dir not in sys.path:
    sys.path.append(app_dir)

# Load env variables from .env
load_dotenv(os.path.join(app_dir, ".env"))

from ingest import ingest_resumes, DB_FILE_PATH, RESUMES_DIR
from rag import query_rag, is_db_initialized

# ----------------- PAGE STYLING & CONFIG -----------------
st.set_page_config(
    page_title="AI Resume RAG Explorer",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for premium design
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    /* Global styles */
    .stApp {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Gradient Title */
    .title-text {
        background: linear-gradient(135deg, #4F46E5 0%, #10B981 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.8rem;
        margin-bottom: 0.5rem;
    }
    
    .subtitle-text {
        color: var(--text-color);
        opacity: 0.8;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }

    /* Premium Metric/Status Cards */
    .status-card {
        background-color: var(--background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 1.2rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 1rem;
    }

    /* Resume Source Cards styling */
    .source-card {
        background-color: var(--secondary-background-color);
        border-left: 5px solid #4F46E5;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
    }
    
    .source-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.05);
        border-left-color: #10B981;
    }

    .source-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-weight: 600;
        font-size: 0.95rem;
        color: #4F46E5;
        margin-bottom: 0.5rem;
    }

    .source-badge {
        background-color: rgba(79, 70, 229, 0.1);
        color: #4F46E5;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.8rem;
    }
    
    .source-text {
        font-size: 0.9rem;
        line-height: 1.5;
        white-space: pre-wrap;
        color: var(--text-color);
    }
    
    /* Footer styling */
    .footer {
        text-align: center;
        margin-top: 3rem;
        padding-top: 1.5rem;
        border-top: 1px solid rgba(128, 128, 128, 0.2);
        font-size: 0.85rem;
        opacity: 0.7;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SESSION STATE & INITIALIZATION -----------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# API Key handling
api_key = os.environ.get("GROQ_API_KEY", "")
api_key_configured = bool(api_key)

# ----------------- SIDEBAR -----------------
st.sidebar.markdown("## ⚙️ Configuration & Control")

# API Key input if not set in environment
if not api_key_configured:
    api_key_input = st.sidebar.text_input(
        "Enter Groq API Key",
        type="password",
        help="Get your free API key from https://console.groq.com/keys. It will be set for this session.",
    )
    if api_key_input:
        os.environ["GROQ_API_KEY"] = api_key_input
        api_key_configured = True
        st.sidebar.success("API Key applied!")
        st.rerun()

# Database Status Indicator
db_status = is_db_initialized()

st.sidebar.markdown("### 📊 System Status")
status_html = ""
if api_key_configured:
    status_html += "🟢 **Groq API Key:** Configured<br>"
else:
    status_html += "🔴 **Groq API Key:** Missing<br>"

if db_status:
    status_html += "🟢 **Vector Database:** Ready"
else:
    status_html += "🔴 **Vector Database:** Not Found"

st.sidebar.markdown(
    f"<div class='status-card'>{status_html}</div>",
    unsafe_allow_html=True
)

# List Resumes
st.sidebar.markdown("### 📂 Ingested Resumes")
if os.path.exists(RESUMES_DIR):
    pdf_files = [f for f in os.listdir(RESUMES_DIR) if f.endswith(".pdf")]
    if pdf_files:
        for pdf in pdf_files:
            st.sidebar.markdown(f"- 📄 `{pdf}`")
    else:
        st.sidebar.info("No resumes found. Put PDF files in `resumes/` folder.")
else:
    st.sidebar.warning("`resumes/` folder not found.")

# Trigger Ingestion
st.sidebar.markdown("### 🛠️ Actions")
if st.sidebar.button("🔄 Rebuild Vector DB", use_container_width=True):
    with st.sidebar.spinner("Processing resumes & generating embeddings (local)..."):
        try:
            ingest_resumes()
            st.sidebar.success("Database rebuild successful!")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Ingestion failed: {e}")

# Clear Chat History
if st.sidebar.button("🗑️ Clear Chat History", use_container_width=True):
    st.session_state.chat_history = []
    st.rerun()

# ----------------- MAIN LAYOUT -----------------
st.markdown("<div class='title-text'>AI Resume RAG Explorer</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='subtitle-text'>A Retrieval-Augmented Generation chatbot that searches candidate profiles and answers questions using Groq.</div>",
    unsafe_allow_html=True
)

# 1. Check Setup Warnings in main panel
if not api_key_configured:
    st.warning("⚠️ **Groq API Key required**: Please set the `GROQ_API_KEY` environment variable or enter it in the sidebar to proceed.")
if not db_status:
    st.info("💡 **Vector Database not found**: Click the **Rebuild Vector DB** button in the sidebar to index the default candidate resumes.")

# 2. Main Interface split: Chat on the left, Retrieved Sources on the right (if a query was made)
col1, col2 = st.columns([3, 2], gap="large")

with col1:
    st.markdown("### 💬 Chat with Resumes")
    
    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat Input
    if user_query := st.chat_input("Ask about candidates (e.g. 'Who is expert in NLP?', 'What is Pratik's summary?')"):
        if not api_key_configured:
            st.error("Please configure your Groq API Key in the sidebar first.")
        elif not db_status:
            st.error("Please build the Vector Database first by clicking 'Rebuild Vector DB' in the sidebar.")
        else:
            # Display user message
            with st.chat_message("user"):
                st.markdown(user_query)
            
            st.session_state.chat_history.append({"role": "user", "content": user_query})
            
            # Query the RAG system
            with st.chat_message("assistant"):
                with st.spinner("Searching database & thinking..."):
                    try:
                        answer, sources = query_rag(user_query)
                        st.markdown(answer)
                        st.session_state.chat_history.append({"role": "assistant", "content": answer, "sources": sources})
                    except Exception as e:
                        error_msg = f"An error occurred: {e}"
                        st.error(error_msg)
                        st.session_state.chat_history.append({"role": "assistant", "content": error_msg, "sources": []})
            st.rerun()

with col2:
    st.markdown("### 🔍 Retrieved Evidence")
    
    # Get sources from the last assistant response in history
    last_assistant_msg = next(
        (msg for msg in reversed(st.session_state.chat_history) if msg["role"] == "assistant"), 
        None
    )
    
    if last_assistant_msg and "sources" in last_assistant_msg and last_assistant_msg["sources"]:
        st.caption("Here are the top matches retrieved from the vector database for your last question:")
        for idx, source in enumerate(last_assistant_msg["sources"]):
            # Display beautifully styled source cards
            score_percent = f"Similarity: {source['score']:.2%}" if source['score'] <= 1.0 else f"Distance Score: {source['score']:.4f}"
            st.markdown(f"""
            <div class="source-card">
                <div class="source-header">
                    <span>📄 {source['candidate']} ({source['source']})</span>
                    <span class="source-badge">{score_percent}</span>
                </div>
                <div class="source-text">"{source['text']}"</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Retrieved text chunks from candidate resumes will appear here when you send a message.")
