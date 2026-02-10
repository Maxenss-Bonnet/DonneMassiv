# Dockerfile pour le TP5 : Apache Spark pour le traitement massif des donnees
# Cette image fournit un environnement Jupyter avec Spark et les dependances necessaires

FROM python:3.10-slim-bookworm

LABEL maintainer="TDM Course"
LABEL description="Environnement Docker pour le TP5 - Apache Spark"

# Variables d'environnement
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV JUPYTER_ENABLE_LAB=yes

# Configuration Spark
ENV SPARK_HOME=/opt/spark
ENV PATH="${SPARK_HOME}/bin:${PATH}"
ENV PYSPARK_PYTHON=python3
ENV PYSPARK_DRIVER_PYTHON=python3
ENV PYTHONPATH="/opt/spark/python:/opt/spark/python/lib/py4j-0.10.9.7-src.zip"

# Repertoire de travail
WORKDIR /app

# Installation des dependances systeme (Java requis pour Spark)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    wget \
    git \
    openjdk-17-jdk-headless \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Installer Apache Spark
ARG SPARK_VERSION=3.5.3
ARG HADOOP_VERSION=3
RUN mkdir -p /opt && \
    curl -fSL "https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz" -o /tmp/spark.tgz && \
    tar -xzf /tmp/spark.tgz -C /opt && \
    mv "/opt/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}" "${SPARK_HOME}" && \
    rm /tmp/spark.tgz

# Definir JAVA_HOME
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

# Copier le fichier requirements
COPY requirements.txt .

# Installer les dependances Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Creer les dossiers pour les notebooks et les donnees
RUN mkdir -p /app/notebooks /app/data /app/output

# Exposer le port Jupyter et le port UI Spark
EXPOSE 8888
EXPOSE 4040

# Commande par defaut pour lancer Jupyter Lab
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token=''", "--NotebookApp.password=''"]
