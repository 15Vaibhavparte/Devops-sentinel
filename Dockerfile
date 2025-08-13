# Use an official lightweight Python image as a parent image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container
COPY . .

# Expose the ports the app runs on (FastAPI on 8000, Streamlit on 8501)
EXPOSE 8000
EXPOSE 8501

# The command to run the application will be specified in docker-compose.yml