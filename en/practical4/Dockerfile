# Dockerfile for Practical 4: Parallel and Distributed Computing
# This image provides a Jupyter environment with all necessary dependencies

FROM python:3.10-slim

LABEL maintainer="TDM Course"
LABEL description="Docker environment for Practical 4 - Parallel and Distributed Computing"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV JUPYTER_ENABLE_LAB=yes

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create directories for notebooks and data
RUN mkdir -p /app/notebooks /app/data

# Expose Jupyter port
EXPOSE 8888

# Set the default command to run Jupyter Lab
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token=''", "--NotebookApp.password=''"]
