# ingest.py

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from langchain_community.document_loaders import DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

# -- 1. LOAD ENVIRONMENT VARIABLES --
load_dotenv()
tidb_host = os.getenv("TIDB_HOST")
tidb_port = os.getenv("TIDB_PORT")
tidb_user = os.getenv("TIDB_USER")
tidb_password = os.getenv("TIDB_PASSWORD")

# Validate environment variables
if not all([tidb_host, tidb_port, tidb_user, tidb_password]):
    print("Error: Missing required environment variables!")
    print(f"TIDB_HOST: {tidb_host}")
    print(f"TIDB_PORT: {tidb_port}")
    print(f"TIDB_USER: {tidb_user}")
    print(f"TIDB_PASSWORD: {'***' if tidb_password else None}")
    exit(1)

# Convert port to integer
try:
    tidb_port = int(tidb_port)
except (ValueError, TypeError):
    print(f"Error: TIDB_PORT must be a valid integer, got: {tidb_port}")
    exit(1)

# Use the 'devops_sentinel' database
DB_NAME = "devops_sentinel"

# Check if we have a DATABASE_URL or need to construct one
database_url = os.getenv("DATABASE_URL")
if database_url:
    connection_string = database_url
    print(f"✅ Using DATABASE_URL from environment")
else:
    # Check SSL certificate
    ssl_ca_path = "./certs/isrgrootx1.pem"
    if os.path.exists(ssl_ca_path):
        connection_string = f"mysql+pymysql://{tidb_user}:{tidb_password}@{tidb_host}:{tidb_port}/{DB_NAME}?ssl_ca={ssl_ca_path}"
        print(f"✅ Using SSL certificate: {ssl_ca_path}")
    else:
        connection_string = f"mysql+pymysql://{tidb_user}:{tidb_password}@{tidb_host}:{tidb_port}/{DB_NAME}?ssl_disabled=false"
        print(f"✅ Using connection without SSL file")

engine = create_engine(connection_string)

# -- 2. INITIALIZE MODELS AND LOADERS --
print("Initializing models and loaders...")
# Use a model that produces 768-dimensional embeddings
model = SentenceTransformer('all-mpnet-base-v2')  # This produces 768 dimensions

# Loader for markdown files specifically (more reliable than generic loader)
from langchain_community.document_loaders import TextLoader
import glob
import os

# Load all markdown files manually for better control
def load_markdown_files(directory):
    docs = []
    md_files = glob.glob(os.path.join(directory, "*.md"))
    for file_path in md_files:
        try:
            loader = TextLoader(file_path, encoding='utf-8')
            file_docs = loader.load()
            for doc in file_docs:
                if len(doc.page_content.strip()) > 0:  # Only add non-empty documents
                    docs.append(doc)
                    print(f"Loaded: {file_path}")
                    print(f"  Document length: {len(doc.page_content)} characters")
                    print(f"  First 100 chars: {doc.page_content[:100]}...")
                else:
                    print(f"Skipped empty file: {file_path}")
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
    return docs

# Text splitter with smaller chunk size for testing
text_splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=20)

# -- 3. LOAD, SPLIT, EMBED, and INSERT --
print("Loading documents from './knowledge_docs/'...")
docs = load_markdown_files('./knowledge_docs/')
print(f"Total documents loaded: {len(docs)}")

chunks = text_splitter.split_documents(docs)
print(f"Loaded {len(docs)} document(s) and split them into {len(chunks)} chunks.")

# Debug: Show chunk info
for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
    print(f"Chunk {i+1}: {len(chunk.page_content)} chars - {chunk.page_content[:50]}...")

try:
    with engine.begin() as connection:  # Use begin() for automatic transaction handling
        print("Connected to TiDB. Starting ingestion...")
        for i, chunk in enumerate(chunks):
            # Create the vector embedding for the chunk's content
            embedding = model.encode(chunk.page_content).tolist()
            
            # Prepare the SQL statement with parameters to prevent SQL injection
            stmt = text("""
                INSERT INTO knowledgebase (source_file, content_chunk, embedding) 
                VALUES (:source, :content, :embedding)
            """)
            
            # Execute the statement
            connection.execute(stmt, {
                "source": chunk.metadata.get('source', 'Unknown'),
                "content": chunk.page_content,
                "embedding": str(embedding)
            })
            
            print(f"  -> Ingested chunk {i+1}/{len(chunks)}")
        
        # Commit happens automatically with begin() context manager
        print("\nIngestion complete! All chunks have been saved to the knowledgebase.")

except Exception as e:
    print(f"An error occurred during ingestion: {e}")