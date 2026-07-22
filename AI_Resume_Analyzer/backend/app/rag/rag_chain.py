import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from app.rag.pinecone_service import get_vector_store
from app.core.config import settings

logger = logging.getLogger(__name__)

def format_docs(docs) -> str:
    formatted = []
    for doc in docs:
        filename = doc.metadata.get("filename", "Unknown")
        page = doc.metadata.get("page", "Unknown")
        formatted.append(f"--- Document: {filename} (Page {page}) ---\n{doc.page_content}")
    return "\n\n".join(formatted)

def query_rag_chain(user_id: str, question: str) -> str:
    """
    Retrieves relevant resume chunks from Pinecone namespace (user_id) 
    and uses Gemini to synthesize a structured answer.
    """
    logger.info(f"Querying RAG chain for user {user_id} with question: '{question}'")
    
    # Get vector store and retriever for user
    vector_store = get_vector_store(user_id)
    retriever = vector_store.as_retriever(
        search_kwargs={"k": settings.TOP_K}
    )
    
    # Retrieve documents
    retrieved_docs = retriever.invoke(question)
    
    if not retrieved_docs:
        logger.info(f"No context found in Pinecone namespace {user_id}")
        return "No relevant resume data found. Please ensure you have uploaded documents for this session."

    logger.info(f"Retrieved {len(retrieved_docs)} chunks from Pinecone.")
    for i, doc in enumerate(retrieved_docs):
        filename = doc.metadata.get("filename", "Unknown")
        page = doc.metadata.get("page", "Unknown")
        logger.debug(f"Chunk {i+1}: {filename} (Page {page}) - Length: {len(doc.page_content)}")

    # Format the documents into context block
    formatted_context = format_docs(retrieved_docs)
    
    # Setup LLM & Prompt
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.1
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are a helpful, professional AI Resume Analyzer assistant.\n"
            "Answer the user's question based strictly on the provided resume context chunks.\n"
            "If the context does not contain the answer or is insufficient, state that the information "
            "is not found in the uploaded resumes.\n\n"
            "Context Chunks:\n"
            "{context}"
        )),
        ("human", "{question}")
    ])
    
    # Build LCEL chain
    chain = prompt | llm | StrOutputParser()
    
    # Execute chain
    try:
        answer = chain.invoke({
            "context": formatted_context,
            "question": question
        })
        return answer
    except Exception as e:
        logger.error(f"Error executing Gemini LLM chain: {e}")
        raise e
