import os
from pypdf import PdfReader

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extracts all text content from a PDF file using pypdf.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found at {pdf_path}")
        
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text

def recursive_split_text(text: str, max_chunk_size: int = 800, overlap: int = 150) -> list:
    """
    Splits text into chunks of maximum size `max_chunk_size` with `overlap`.
    Recursively attempts to split on paragraph (\n\n), newline (\n), sentence (. ), word ( ), and character.
    """
    separators = ["\n\n", "\n", ". ", " ", ""]
    
    def split(text_to_split, separators_list):
        if len(text_to_split) <= max_chunk_size:
            return [text_to_split]
        if not separators_list:
            # If no separators left, hard split by character size
            return [text_to_split[i:i+max_chunk_size] for i in range(0, len(text_to_split), max_chunk_size)]
        
        separator = separators_list[0]
        # Avoid splitting by empty string which returns list of chars
        if separator == "":
            splits = list(text_to_split)
        else:
            splits = text_to_split.split(separator)
        
        chunks = []
        current_chunk = ""
        
        for i, item in enumerate(splits):
            # For rebuilding: add separator back if it's not the last element
            item_with_sep = item + separator if (separator and i < len(splits) - 1) else item
            
            if len(item_with_sep) > max_chunk_size:
                # If a single item exceeds max chunk size, flush current and recursively split item
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                sub_chunks = split(item, separators_list[1:])
                chunks.extend(sub_chunks)
            elif len(current_chunk) + len(item_with_sep) <= max_chunk_size:
                current_chunk += item_with_sep
            else:
                # Flush the current chunk
                if current_chunk:
                    chunks.append(current_chunk.strip())
                # Handle overlap: take end of current chunk
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                current_chunk = overlap_text + item_with_sep
                
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks

    return split(text, separators)
