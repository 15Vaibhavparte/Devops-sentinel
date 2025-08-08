# query_agent.py

import os
import numpy as np
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sentence_transformers import SentenceTransformer

# -- 1. LOAD ENVIRONMENT AND MODELS --
load_dotenv()
tidb_host = os.getenv("TIDB_HOST")
tidb_port = os.getenv("TIDB_PORT")
tidb_user = os.getenv("TIDB_USER")
tidb_password = os.getenv("TIDB_PASSWORD")

# Validate environment variables
if not all([tidb_host, tidb_port, tidb_user, tidb_password]):
    print("Error: Missing required environment variables!")
    exit(1)

# Convert port to integer
try:
    tidb_port = int(tidb_port)
except (ValueError, TypeError):
    print(f"Error: TIDB_PORT must be a valid integer, got: {tidb_port}")
    exit(1)

DB_NAME = "devops_sentinel"
ssl_ca_path = os.path.abspath("isrgrootx1.pem")
connection_string = f"mysql+pymysql://{tidb_user}:{tidb_password}@{tidb_host}:{tidb_port}/{DB_NAME}?ssl_ca={ssl_ca_path}"
engine = create_engine(connection_string)

print("Loading embedding model...")
# Use the same model as ingest.py for consistency
model = SentenceTransformer('all-mpnet-base-v2')  # This produces 768 dimensions

# -- 2. DEFINE THE USER'S QUESTION --
user_question = "What should I do about database connection timeouts?"

print(f"\nUser Question: {user_question}")

# -- 3. CREATE EMBEDDING FOR THE QUESTION --
print("Creating embedding for the question...")
query_embedding = model.encode(user_question).tolist()

# -- 4. PERFORM VECTOR SEARCH IN TIDB --
print("Searching for relevant documents in TiDB...")
try:
    with engine.connect() as connection:
        # Convert query embedding to vector format for TiDB
        query_vector = f"[{','.join(map(str, query_embedding))}]"
        
        # This SQL query calculates the cosine distance between the user's question embedding
        # and all the chunk embeddings stored in the table.
        # Note: Lower distance = higher similarity, so we use ASC order
        stmt = text("""
            SELECT 
                content_chunk, 
                source_file,
                VEC_COSINE_DISTANCE(embedding, :query_vector) as distance
            FROM knowledgebase
            ORDER BY distance ASC
            LIMIT 3;
        """)
        
        result = connection.execute(stmt, {"query_vector": query_vector})
        
        print("\n--- Top Search Results ---")
        rows = result.fetchall()
        if not rows:
            print("No relevant documents found.")
        else:
            for i, row in enumerate(rows):
                # Convert distance to similarity for display (1 - distance)
                similarity = 1 - row[2]
                print(f"Result {i+1} (Similarity: {similarity:.4f}, Distance: {row[2]:.4f}):")
                print(f"Source: {row[1]}")
                print(f"Content: {row[0]}\n")

except Exception as e:
    print(f"An error occurred during search: {e}")