# Dockerfile for Practical 5: Apache Spark for Massive Data Processing
# This image provides a Jupyter environment with PySpark and all necessary dependencies

FROM python:3.10-slim-bookworm

LABEL maintainer="TDM Course"
LABEL description="Docker environment for Practical 5 - Apache Spark"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV JUPYTER_ENABLE_LAB=yes

# Spark configuration
ENV SPARK_HOME=/opt/spark
ENV PATH="${SPARK_HOME}/bin:${PATH}"
ENV PYSPARK_PYTHON=python3
ENV PYSPARK_DRIVER_PYTHON=python3

# Set working directory
WORKDIR /app

# Install system dependencies including Java (required for Spark)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    wget \
    git \
    openjdk-17-jdk-headless \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

# Download and install Apache Spark
ARG SPARK_VERSION=3.5.3
ARG HADOOP_VERSION=3
RUN mkdir -p /opt && \
    curl -fSL "https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz" -o /tmp/spark.tgz && \
    tar -xzf /tmp/spark.tgz -C /opt && \
    mv "/opt/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}" "${SPARK_HOME}" && \
    rm /tmp/spark.tgz

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create directories for notebooks and data
RUN mkdir -p /app/notebooks /app/data /app/output

# Expose Jupyter port and Spark UI port
EXPOSE 8888
EXPOSE 4040

# Set the default command to run Jupyter Lab
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token=''", "--NotebookApp.password=''"]
