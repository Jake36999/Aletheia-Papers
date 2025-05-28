# core/memory_system.py (or corememory_system.py)

import chromadb
from docx import Document # pip install python-docx
import os
from typing import List, Dict, Any, Optional
import datetime

# --- Import the REAL embedding function ---
from core.llm_interface import get_openai_embedding 
# ----------------------------------------

# --- ChromaDB Setup ---
CHROMA_DATA_PATH = "db_data/" # Path relative to the project root where ingest_all.py is
COLLECTION_NAME = "aletheia_memory"

try:
    # When scripts in core/ are run directly for testing, the path might need adjustment
    # However, for ingest_all.py in the root, this should be fine.
    if not os.path.exists(CHROMA_DATA_PATH) and not os.path.isabs(CHROMA_DATA_PATH):
         # Attempt to create path relative to project root if core script is run directly
        if __name__ == "__main__" and os.path.basename(os.getcwd()) == "core":
            persistent_path = os.path.join("..", CHROMA_DATA_PATH)
        else:
            persistent_path = CHROMA_DATA_PATH
    else:
        persistent_path = CHROMA_DATA_PATH

    client = chromadb.PersistentClient(path=persistent_path)
except Exception as e:
    print(f"Error initializing ChromaDB persistent client at '{persistent_path}': {e}")
    client = chromadb.Client() 
    print("Initialized in-memory ChromaDB client as a fallback.")

try:
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    print(f"ChromaDB collection '{COLLECTION_NAME}' loaded/created successfully.")
except Exception as e:
    print(f"Error getting or creating ChromaDB collection: {e}")
    collection = None 
    print("Failed to initialize ChromaDB collection.")

# --- Document Loaders ---
def load_text_file(file_path: str) -> Optional[str]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except Exception as e:
        print(f"Error loading text file {file_path}: {e}")
        return None

def load_docx_file(file_path: str) -> Optional[str]:
    try:
        doc = Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except Exception as e:
        print(f"Error loading DOCX file {file_path}: {e}")
        return None

# --- Text Chunking Strategy ---
def chunk_text(text: str, chunk_size: int = 1200, chunk_overlap: int = 150) -> List[str]:
    if not text: return []
    chunks = []
    start_index = 0
    text_len = len(text)
    while start_index < text_len:
        end_index = min(start_index + chunk_size, text_len)
        chunks.append(text[start_index:end_index])
        if end_index == text_len: break
        start_index += (chunk_size - chunk_overlap)
        if (chunk_size - chunk_overlap) <= 0: 
            print(f"Warning: Chunking parameters might lead to infinite loop (size: {chunk_size}, overlap: {chunk_overlap}). Breaking.")
            break 
    return chunks

# --- Ingestion into ChromaDB ---
def ingest_document(file_path: str, document_title: str, content_type: str):
    if not collection:
        print("Error: ChromaDB collection not initialized. Skipping ingestion.")
        return
    print(f"Starting ingestion for: {file_path} (Title: {document_title})")
    _, file_extension = os.path.splitext(file_path)
    file_name = os.path.basename(file_path)

    text_content = None 
    if file_extension.lower() == '.txt' or file_extension.lower() == '.yaml': 
        text_content = load_text_file(file_path)
    elif file_extension.lower() == '.docx':
        text_content = load_docx_file(file_path)
    else:
        print(f"Warning: Unsupported file type '{file_extension}' for {file_path}. Skipping.")
        return 

    if not text_content: 
        print(f"Warning: No text content loaded from {file_path}. Skipping.")
        return
        
    chunks = chunk_text(text_content)
    if not chunks:
        print(f"Warning: No chunks generated for {document_title}. Skipping.")
        return
        
    print(f"Generated {len(chunks)} chunks for {document_title}.")

    embeddings_to_add, documents_to_add, metadatas_to_add, ids_to_add = [], [], [], []

    for i, chunk in enumerate(chunks):
        chunk_sequence_id = i + 1
        
        embedding_vector = get_openai_embedding(chunk) 

        if embedding_vector is None:
            print(f"Warning: Could not generate embedding for chunk {chunk_sequence_id} of {document_title}. Skipping.")
            continue # This 'continue' is correctly in the loop

        metadata = {
            "source_file_name": file_name, "document_title": document_title,
            "content_type": content_type, "chunk_sequence_id": chunk_sequence_id,
            "original_text_preview": chunk[:200] + "..." 
        }
        embeddings_to_add.append(embedding_vector)
        documents_to_add.append(chunk) 
        metadatas_to_add.append(metadata)
        
        sane_title = "".join(c if c.isalnum() else "_" for c in document_title)
        ids_to_add.append(f"{sane_title}_chunk_{chunk_sequence_id}")

    if documents_to_add: 
        try:
            collection.add(
                embeddings=embeddings_to_add,
                documents=documents_to_add, 
                metadatas=metadatas_to_add,
                ids=ids_to_add
            )
            print(f"Successfully added {len(documents_to_add)} chunks from {document_title} to ChromaDB.")
        except Exception as e:
            print(f"Error adding chunks to ChromaDB for {document_title}: {e}")
    else:
        print(f"No valid chunks with embeddings to add for {document_title}.")

# --- Retrieval from ChromaDB ---
def retrieve_relevant_chunks(query_text: str, filters: Optional[Dict[str, Any]] = None, n_results: int = 5) -> List[Dict[str, Any]]:
    if not collection or not query_text: return []

    query_embedding = get_openai_embedding(query_text)
    if query_embedding is None: return []

    try:
        results = collection.query(query_embeddings=[query_embedding], n_results=n_results, where=filters, include=['metadatas', 'documents', 'distances'])
    except Exception as e:
        print(f"Error querying ChromaDB: {e}")
        return []

    formatted_results = []
    if results and results.get('ids') and results['ids'] and len(results['ids'][0]) > 0: 
        for i in range(len(results['ids'][0])):
            distance = results['distances'][0][i] if results['distances'] and results['distances'][0] else None
            formatted_results.append({
                "id": results['ids'][0][i],
                "text_chunk": results['documents'][0][i] if results['documents'] and results['documents'][0] else "N/A",
                "metadata": results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {},
                "similarity_score": (1 - distance) if distance is not None else None
            })
        # print(f"Retrieved {len(formatted_results)} relevant chunks.") # Less verbose for ingest_all
    else:
        # print("No relevant chunks found or results format unexpected.") # Less verbose for ingest_all
        pass
    return formatted_results
# --- Function to Ingest Raw Interaction Text ---
def ingest_interaction_text(user_input: str, ai_response: str):
    """
    Formats a user/AI interaction, gets its embedding, and stores it.
    """
    if not collection:
        print("[corememory] Error: ChromaDB collection not initialized. Skipping interaction ingestion.")
        return

    # 1. Format the interaction text
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    interaction_text = f"Interaction at {timestamp}:\nUser: {user_input}\nAletheia: {ai_response}"

    # 2. Define Title and Content Type
    doc_title = f"Interaction_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    content_type = "LiveInteraction"

    print(f"[corememory] Ingesting: {doc_title}...")

    # 3. Get Embedding (We embed the whole small interaction as one chunk)
    embedding_vector = get_openai_embedding(interaction_text)

    if embedding_vector is None:
        print(f"[corememory] Warning: Could not generate embedding for {doc_title}. Skipping.")
        return

    # 4. Prepare Metadata and ID
    metadata = {
        "source_file_name": "LiveSession",
        "document_title": doc_title,
        "content_type": content_type,
        "chunk_sequence_id": 1, # Only one chunk per interaction
        "timestamp": timestamp
    }
    unique_id = f"{doc_title}_chunk_1"

    # 5. Add to ChromaDB
    try:
        collection.add(
            embeddings=[embedding_vector],
            documents=[interaction_text],
            metadatas=[metadata],
            ids=[unique_id]
        )
        print(f"[corememory] Successfully added {doc_title} to ChromaDB.")
    except Exception as e:
        print(f"[corememory] Error adding interaction {doc_title} to ChromaDB: {e}")
# --- Main execution / Example Usage (for testing this file directly) ---
if __name__ == "__main__":
    print("Memory System Direct Test (corememory_system.py)")

    # Determine DATA_DIR relative to this script's location if run directly
    # Assumes this script is in 'core' and 'data' is a sibling to 'core'
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root_dir = os.path.dirname(current_script_dir) # Up one level to Aletheia/
    DATA_DIR_FOR_TEST = os.path.join(project_root_dir, "data")
    
    if not os.path.exists(DATA_DIR_FOR_TEST):
        print(f"Error: Data directory '{DATA_DIR_FOR_TEST}' for testing not found.")
    else:
        test_file_path = os.path.join(DATA_DIR_FOR_TEST, "Aletheiapersonalnotes.txt") 
        
        if os.path.exists(test_file_path):
            if collection:
                print(f"\n--- Test Ingestion from corememory_system.py: {test_file_path} ---")
                ingest_document(
                    file_path=test_file_path,
                    document_title="Aletheia's Personal Notes - Direct Test", 
                    content_type="AletheiaAnalysis_SelfGenerated_Test"
                )
                
                print("\n--- Testing Retrieval from corememory_system.py ---")
                query1 = "What are Aletheia's thoughts on its own identity?" 
                retrieved_chunks1 = retrieve_relevant_chunks(query1, n_results=2)
                if retrieved_chunks1:
                    for i, chunk_info in enumerate(retrieved_chunks1):
                        print(f"\nRetrieved Chunk {i+1}:")
                        print(f"  ID: {chunk_info.get('id')}")
                        print(f"  Similarity: {chunk_info.get('similarity_score'):.4f}" if chunk_info.get('similarity_score') is not None else "N/A")
                        print(f"  Text: {chunk_info.get('text_chunk')[:150]}...")
                        print(f"  Metadata: {chunk_info.get('metadata')}")
                else:
                    print("No chunks retrieved for the test query or retrieval failed.")
            else:
                print("Skipping ingestion as ChromaDB collection was not initialized.")
        else:
            print(f"Error: Test file not found at {test_file_path}. Please place it in the '{DATA_DIR_FOR_TEST}' folder.")

    print("\nMemory System Direct Test Finished.")