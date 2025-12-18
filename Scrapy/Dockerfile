# Image de base Python
FROM python:3.11-slim

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers de requirements
COPY requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier le fichier de configuration Scrapy
COPY scrapy.cfg .

# Copier le code du crawler
COPY crawler/ ./crawler/

# Copier le script d'entrée
COPY entrypoint.sh /app/entrypoint.sh

# Convertir les fins de ligne Windows (CRLF) vers Unix (LF) et rendre exécutable
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Créer le dossier data pour les sorties
RUN mkdir -p /data

# Point d'entrée qui initialise et scrappe automatiquement
ENTRYPOINT ["/app/entrypoint.sh"]
