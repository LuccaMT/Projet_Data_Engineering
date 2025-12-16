# Image de base Python
FROM python:3.11-slim

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers de requirements
COPY requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code du crawler
COPY crawler/ ./crawler/

# Créer le dossier data pour les sorties
RUN mkdir -p /data

# Point d'entrée par défaut
CMD ["python", "-m", "crawler.fetch_finished", "--help"]
