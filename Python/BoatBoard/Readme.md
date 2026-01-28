# Network Surveillance System 🛡️

Tableau de bord de monitoring réseau avec interface cyber-futuriste pour serveur Debian 13.

## 📋 Fonctionnalités

### Monitoring Réseau
- 🌐 **Détection automatique des appareils** connectés au réseau
- 📡 **Radar central animé** avec positionnement des périphériques
- 🎯 **Classification des appareils** (PC, mobile, Raspberry Pi, VM, NAS)
- ⚡ **Test de vitesse** (download/upload/ping) via Speedtest

### Monitoring Système
- 💻 **Utilisation CPU** en temps réel
- 🧠 **Utilisation RAM** en temps réel
- 🔌 **Adresse IP** du serveur
- ⚙️ **Services actifs** (systemd)
- 📝 **Logs journalctl** en temps réel

### Interface
- 🎨 Design **cyber-futuriste** inspiré des systèmes militaires
- 🌊 Animations fluides et effets lumineux
- 📊 Mise à jour en **temps réel** via WebSocket
- 📱 Responsive et optimisé

## 🚀 Installation

### Prérequis
- Docker et Docker Compose installés
- Debian 13 (ou distribution Linux compatible)
- Accès root/sudo

### Installation rapide

1. **Cloner ou télécharger les fichiers** dans un dossier :
```bash
mkdir network-monitor
cd network-monitor
# Copier tous les fichiers (app.py, Dockerfile, docker-compose.yml, etc.)
```

2. **Construire l'image Docker** :
```bash
docker-compose build
```

3. **Lancer l'application** :
```bash
docker-compose up -d
```

4. **Accéder au dashboard** :
Ouvrez votre navigateur à l'adresse : `http://localhost:5000`

## 📦 Structure du projet

```
network-monitor/
├── app.py                 # Serveur Flask backend
├── templates/
│   └── dashboard.html     # Interface web
├── static/                # Fichiers statiques (vide pour l'instant)
├── requirements.txt       # Dépendances Python
├── Dockerfile            # Configuration Docker
├── docker-compose.yml    # Orchestration Docker
└── README.md            # Ce fichier
```

## 🔧 Configuration

### Ports
- Par défaut : `5000`
- Pour changer le port, modifier dans `docker-compose.yml` :
```yaml
ports:
  - "VOTRE_PORT:5000"
```

### Permissions réseau
L'application utilise `network_mode: host` et `privileged: true` pour :
- Scanner le réseau local (ARP)
- Accéder aux logs journalctl
- Lister les services systemd

### Fréquence des mises à jour
Dans `app.py`, fonction `update_network_data()` :
- **Système** (CPU/RAM) : toutes les 2 secondes
- **Scan réseau** : toutes les 10 secondes
- **Speedtest** : toutes les 5 minutes

## 🎮 Utilisation

### Commandes Docker

**Démarrer** :
```bash
docker-compose up -d
```

**Arrêter** :
```bash
docker-compose down
```

**Voir les logs** :
```bash
docker-compose logs -f
```

**Redémarrer** :
```bash
docker-compose restart
```

### Panneau de contrôle

L'interface est divisée en 4 zones :

1. **Panneau gauche** : Appareils connectés, statistiques réseau, services actifs
2. **Panneau central** : Radar animé avec visualisation des périphériques
3. **Panneau droit** : Vitesses réseau (speedtest), CPU, RAM
4. **Panneau bas** : Logs système journalctl en temps réel

## 🛠️ Dépendances

### Python
- Flask 3.0.0 - Framework web
- Flask-SocketIO 5.3.5 - WebSocket temps réel
- psutil 5.9.6 - Monitoring système
- speedtest-cli 2.1.3 - Tests de vitesse réseau

### Système
- net-tools - Commandes réseau (arp, ifconfig)
- iputils-ping - Utilitaire ping
- systemd - Gestion des services
- arp-scan - Scan réseau avancé

## 📊 Types d'appareils détectés

Le système identifie automatiquement :
- 💻 **computer** - Ordinateurs de bureau/portables
- 📱 **mobile** - Smartphones et tablettes
- 🔴 **raspberry** - Raspberry Pi
- 📦 **vm** - Machines virtuelles
- 💾 **nas** - Serveurs de stockage réseau

Basé sur les préfixes MAC (OUI - Organizationally Unique Identifier).

## ⚠️ Sécurité

### Recommandations
- 🔒 Utiliser un **reverse proxy** (nginx) pour la production
- 🔐 Ajouter une **authentification** pour l'accès distant
- 🛡️ Configurer un **pare-feu** pour limiter l'accès au port 5000
- 🔑 Ne pas exposer directement sur Internet

### Exemple nginx avec authentification :
```nginx
server {
    listen 443 ssl;
    server_name monitor.votredomaine.com;
    
    auth_basic "Network Monitor";
    auth_basic_user_file /etc/nginx/.htpasswd;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 🐛 Dépannage

### Le speedtest ne fonctionne pas
- Vérifier la connexion Internet
- Le premier test peut prendre 1-2 minutes
- Consulter les logs : `docker-compose logs -f`

### Pas d'appareils détectés
- Vérifier que le conteneur a les permissions nécessaires (`privileged: true`)
- Vérifier `network_mode: host` dans docker-compose.yml
- Tester manuellement : `docker exec network_monitor arp -a`

### Erreur journalctl
- Vérifier le montage du volume : `/var/log/journal:/var/log/journal:ro`
- Sur certains systèmes, journalctl peut nécessiter des permissions supplémentaires

## ✨ Version 2.0 - Améliorations

Cette version inclut de nombreuses améliorations par rapport à la version initiale :

### Backend
- ✅ Gestion d'erreurs robuste avec logging professionnel
- ✅ Configuration complète par variables d'environnement
- ✅ Cache intelligent pour speedtest (évite surcharge réseau)
- ✅ Support arp-scan + arp avec fallback automatique
- ✅ +50% de préfixes MAC reconnus
- ✅ Calcul du débit réseau temps réel (Mbps)
- ✅ Health endpoint pour monitoring externe

### Frontend
- ✅ Design cyber-futuriste avec animations fluides
- ✅ Effets visuels (scanline, grille animée, glow)
- ✅ Radar interactif avec couleurs par type d'appareil
- ✅ Interface optimisée et responsive

### DevOps
- ✅ Script de démarrage automatisé (`start.sh`)
- ✅ Script de tests (`test.sh`)
- ✅ Documentation complète (README, CHANGELOG)
- ✅ Configuration Docker optimisée

Voir [CHANGELOG.md](CHANGELOG.md) pour la liste complète.

## 📈 Améliorations futures possibles

- ✨ Historique des données avec graphiques
- 🔔 Alertes (email/webhook) sur seuils dépassés
- 🗺️ Carte réseau interactive
- 📊 Export des données (CSV/JSON)
- 🌍 Support multi-langue
- 📲 Notifications push
- 🔍 Scan de ports et vulnérabilités
- 📦 Intégration avec d'autres outils de monitoring

## 📝 Licence

Projet libre d'utilisation pour usage personnel et professionnel.

## 👨‍💻 Support

Pour toute question ou problème :
1. Vérifier les logs Docker
2. Consulter ce README
3. Vérifier les permissions système

---

**Créé avec ❤️ pour le monitoring réseau moderne**