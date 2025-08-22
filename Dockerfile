# --- STAGE 1: The Builder ---
# This stage installs dependencies, including a CPU-only version of PyTorch
FROM python:3.11-slim as builder

# Set the working directory
WORKDIR /app

# Install system dependencies needed for building
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch for CPU only to save space
# This is the most important optimization step
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Copy requirements and install the rest of the dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the sentence transformer model to cache it
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-mpnet-base-v2')" || echo "Model download failed, will download at runtime"

# --- STAGE 2: The Final Image ---
# This stage creates the small, final image for production
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install minimal runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the installed Python packages from the 'builder' stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy the cached model from builder stage
COPY --from=builder /root/.cache /root/.cache

# Copy your application code
COPY . .

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Expose the necessary ports
EXPOSE 8000
EXPOSE 8501

# Health check for the backend
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# The command to run the app will be in docker-compose.yml or Railway's start command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]