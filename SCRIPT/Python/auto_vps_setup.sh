#!/bin/bash

# Script d'automatisation complète de configuration VPS
# Usage: ./auto_vps_setup.sh <IP_DU_SERVEUR>

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Vérification des paramètres
if [ $# -lt 1 ]; then
    echo -e "${RED}Usage: $0 <IP_DU_SERVEUR>${NC}"
    echo "Exemple: $0 192.168.1.100"
    exit 1
fi

SERVER_IP=$1
SSH_DIR="$HOME/.ssh"
KEY_NAME="key${SERVER_IP}"
KEY_PATH="$SSH_DIR/$KEY_NAME"
CONFIG_FILE="$SSH_DIR/config"

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Automatisation Configuration VPS     ║${NC}"
echo -e "${BLUE}╔════════════════════════════════════════╗${NC}\n"

# Demander le mot de passe root
echo -e "${YELLOW}Entrez le mot de passe root du serveur :${NC}"
read -s ROOT_PASSWORD
echo

# Demander la passphrase pour la clé SSH
echo -e "${YELLOW}Entrez la passphrase pour la clé SSH :${NC}"
read -s PASSPHRASE
echo

# Confirmer la passphrase
echo -e "${YELLOW}Confirmez la passphrase :${NC}"
read -s PASSPHRASE_CONFIRM
echo

if [ "$PASSPHRASE" != "$PASSPHRASE_CONFIRM" ]; then
    echo -e "${RED}Erreur : Les passphrases ne correspondent pas${NC}"
    exit 1
fi

# Étape 1 : Mise à jour et installation sur le serveur
echo -e "${GREEN}[1/6] Mise à jour du serveur et installation de neovim...${NC}"
sshpass -p "$ROOT_PASSWORD" ssh -o StrictHostKeyChecking=no root@$SERVER_IP << 'ENDSSH'
apt update -y
apt upgrade -y
apt install -y neovim
echo "✓ Serveur mis à jour et neovim installé"
ENDSSH

echo -e "${GREEN}✓ Étape 1 terminée${NC}\n"

# Étape 2 : Génération de la clé SSH
echo -e "${GREEN}[2/6] Génération de la clé SSH...${NC}"
mkdir -p "$SSH_DIR"
if [ -f "$KEY_PATH" ]; then
    echo -e "${YELLOW}La clé $KEY_NAME existe déjà, elle sera utilisée${NC}"
else
    ssh-keygen -t rsa -b 4096 -f "$KEY_PATH" -N "$PASSPHRASE" -C "vps-$SERVER_IP"
    echo -e "${GREEN}✓ Clé SSH générée : $KEY_PATH${NC}"
fi
echo

# Étape 3 : Copie de la clé sur le serveur
echo -e "${GREEN}[3/6] Copie de la clé SSH sur le serveur...${NC}"
sshpass -p "$ROOT_PASSWORD" ssh-copy-id -i "$KEY_PATH.pub" -o StrictHostKeyChecking=no root@$SERVER_IP
echo -e "${GREEN}✓ Clé SSH copiée${NC}\n"

# Étape 4 : Configuration du fichier config SSH
echo -e "${GREEN}[4/6] Configuration du fichier SSH config...${NC}"

# Trouver le prochain numéro de serveur disponible
SERVER_NUM=1
while grep -q "^Host srv$SERVER_NUM" "$CONFIG_FILE" 2>/dev/null; do
    ((SERVER_NUM++))
done
SERVER_NAME="srv$SERVER_NUM"

# Créer le fichier config s'il n'existe pas
touch "$CONFIG_FILE"

# Ajouter la configuration
cat >> "$CONFIG_FILE" << EOF

Host $SERVER_NAME
    Hostname $SERVER_IP
    User root
    IdentityFile $KEY_PATH
EOF

echo -e "${GREEN}✓ Configuration ajoutée pour $SERVER_NAME${NC}"
echo -e "${BLUE}Vous pouvez maintenant vous connecter avec : ssh $SERVER_NAME${NC}\n"

# Étape 5 : Désactivation de l'authentification par mot de passe
echo -e "${GREEN}[5/6] Désactivation de l'authentification par mot de passe...${NC}"

# Créer le script de configuration SSH à exécuter sur le serveur
cat > /tmp/ssh_config.sh << 'SERVERSCRIPT'
#!/bin/bash
cd /etc/ssh

# Backup du fichier de config
cp sshd_config sshd_config.backup.$(date +%Y%m%d_%H%M%S)

# Modifications de sshd_config
sed -i 's/#*PasswordAuthentication.*/PasswordAuthentication no/' sshd_config
sed -i 's/#*PubkeyAuthentication.*/PubkeyAuthentication yes/' sshd_config
sed -i 's/#*ChallengeResponseAuthentication.*/ChallengeResponseAuthentication no/' sshd_config
sed -i 's/#*UsePAM.*/UsePAM no/' sshd_config
sed -i 's/#*PermitRootLogin.*/PermitRootLogin prohibit-password/' sshd_config

echo "✓ Configuration SSH modifiée"
SERVERSCRIPT

chmod +x /tmp/ssh_config.sh

# Copier et exécuter le script sur le serveur
scp -i "$KEY_PATH" /tmp/ssh_config.sh root@$SERVER_IP:/tmp/
ssh -i "$KEY_PATH" root@$SERVER_IP "bash /tmp/ssh_config.sh"

echo -e "${GREEN}✓ Authentification par mot de passe désactivée${NC}\n"

# Étape 6 : Redémarrage du service SSH
echo -e "${GREEN}[6/6] Redémarrage du service SSH...${NC}"

ssh -i "$KEY_PATH" root@$SERVER_IP << 'ENDSSH'
systemctl daemon-reload
systemctl restart ssh
systemctl restart ssh.socket 2>/dev/null || true
echo "✓ Service SSH redémarré"
ENDSSH

echo -e "${GREEN}✓ Service SSH redémarré${NC}\n"

# Nettoyage
rm /tmp/ssh_config.sh

# Résumé
echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        Configuration terminée !        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}\n"

echo -e "${GREEN}Résumé de la configuration :${NC}"
echo -e "  • Serveur mis à jour ✓"
echo -e "  • Neovim installé ✓"
echo -e "  • Clé SSH créée : ${YELLOW}$KEY_PATH${NC}"
echo -e "  • Alias SSH créé : ${YELLOW}$SERVER_NAME${NC}"
echo -e "  • Authentification par mot de passe : ${RED}DÉSACTIVÉE${NC}"
echo -e "  • Authentification par clé : ${GREEN}ACTIVÉE${NC}\n"

echo -e "${YELLOW}Commande de connexion :${NC}"
echo -e "  ${BLUE}ssh $SERVER_NAME${NC}\n"

echo -e "${RED}⚠️  IMPORTANT :${NC}"
echo -e "  • Testez la connexion MAINTENANT dans un nouveau terminal"
echo -e "  • L'authentification par mot de passe est désactivée"
echo -e "  • Conservez votre clé privée : $KEY_PATH"
echo -e "  • N'oubliez pas votre passphrase SSH !\n"

# Test de connexion
echo -e "${YELLOW}Test de connexion...${NC}"
if ssh -i "$KEY_PATH" -o BatchMode=yes -o ConnectTimeout=5 root@$SERVER_IP "echo 'Connexion réussie'" 2>/dev/null; then
    echo -e "${GREEN}✓ Test de connexion réussi !${NC}\n"
else
    echo -e "${RED}✗ Erreur de connexion. Vérifiez la configuration.${NC}\n"
fi

echo -e "${GREEN}Script terminé avec succès !${NC}"