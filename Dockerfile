# --- STAGE 1: The Builder ---
# This stage installs all dependencies in a single, optimized step.
FROM python:3.11-slim as builder

# Set the working directory
WORKDIR /app

# Copy requirements file first to leverage Docker layer caching.
COPY requirements.txt .

# Install all dependencies from requirements.txt in a single RUN command.
# This allows pip to resolve all versions correctly and creates a single layer.
# The CPU-only PyTorch index is used for all packages to ensure the correct versions are found.
# NOTE: Ensure 'torch', 'torchvision', and 'torchaudio' are listed in your requirements.txt
RUN pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu


# --- STAGE 2: The Final Image ---
# This stage creates the small, final production image.
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy only the installed Python packages from the 'builder' stage.
# This is much smaller than the entire builder image.
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy your application code into the final image.
COPY . .

# Create a non-root user for better security.
RUN useradd --create-home app
USER app

# Expose the necessary ports for your application.
EXPOSE 8000
EXPOSE 8501

# The command to run your app.
# Railway.app will likely override this with its own start command, but it's good practice.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]