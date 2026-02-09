FROM python:3.11-slim

# Éviter les questions interactives et mettre à jour les paquets
ENV DEBIAN_FRONTEND=noninteractive

# Installer les dépendances système nécessaires pour psycopg2
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# Créer un dossier pour l’app
WORKDIR /app

# Installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code de l’app
COPY app.py .

# Exposer le port Flask
EXPOSE 5000

# Lancer le serveur Flask
CMD ["python", "app.py"]
