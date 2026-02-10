# Dockerfile pour le TP4 : Calcul parallele et distribue
# Cette image fournit un environnement Jupyter avec toutes les dependances necessaires

FROM python:3.10-slim

LABEL maintainer="TDM Course"
LABEL description="Environnement Docker pour le TP4 - Calcul parallele et distribue"

# Variables d'environnement
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV JUPYTER_ENABLE_LAB=yes

# Repertoire de travail
WORKDIR /app

# Installation des dependances systeme
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copier le fichier requirements
COPY requirements.txt .

# Installer les dependances Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Creer les dossiers pour les notebooks et les donnees
RUN mkdir -p /app/notebooks /app/data

# Exposer le port Jupyter
EXPOSE 8888

# Commande par defaut pour lancer Jupyter Lab
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token=''", "--NotebookApp.password=''"]
