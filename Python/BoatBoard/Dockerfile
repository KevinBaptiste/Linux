FROM python:3.11-slim

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    net-tools \
    iputils-ping \
    systemd \
    arp-scan \
    && rm -rf /var/lib/apt/lists/*

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers requirements
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier l'application
COPY app.py .
COPY templates/ templates/
COPY static/ static/

# Exposer le port
EXPOSE 5000

# Variables d'environnement
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py

# Commande de démarrage
CMD ["python", "app.py"]