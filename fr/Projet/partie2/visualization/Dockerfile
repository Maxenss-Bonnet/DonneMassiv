FROM python:3.10-slim

WORKDIR /app

# Copier et installer les dépendances (pas besoin de Java/PySpark ici)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le script
COPY visualization.py .

# Commande par défaut
CMD ["python", "visualization.py"]
