# Image de base Python
FROM python:3.11-slim

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers de requirements
COPY requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le code de l'application
COPY app/ ./app/

# Exposer le port du dashboard
EXPOSE 8050

# Définir le répertoire de travail pour l'app
WORKDIR /app/app

# Lancer l'application Dash
CMD ["python", "main.py"]
