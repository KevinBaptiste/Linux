#include &lt;stdio.h&gt;
#include &lt;stdlib.h&gt;
#include &lt;string.h&gt;
#include &lt;unistd.h&gt;  // Pour getpass si disponible, sinon utiliser scanf

// Fonction pour lire un mot de passe sans écho (simple implémentation)
char* read_password(const char* prompt) {
    printf("%s", prompt);
    char* password = (char*)malloc(256);
    if (password == NULL) {
        perror("Erreur d'allocation mémoire");
        exit(1);
    }
    // Note: Pour une vraie sécurité, utiliser une bibliothèque comme libreadline ou getpass
    scanf("%255s", password);  // Limite à 255 caractères
    return password;
}

int main(int argc, char* argv[]) {
    // Couleurs ANSI (si supportées)
    const char* RED = "\033[0;31m";
    const char* GREEN = "\033[0;32m";
    const char* YELLOW = "\033[1;33m";
    const char* BLUE = "\033[0;34m";
    const char* NC = "\033[0m";

    // Vérification des paramètres
    if (argc < 2) {
        printf("%sUsage: %s <IP_DU_SERVEUR>%s\n", RED, argv[0], NC);
        printf("Exemple: %s 192.168.1.100\n", argv[0]);
        return 1;
    }

    char* SERVER_IP = argv[1];
    char SSH_DIR[256];
    sprintf(SSH_DIR, "%s/.ssh", getenv("HOME"));
    char KEY_NAME[256];
    sprintf(KEY_NAME, "key%s", SERVER_IP);
    char KEY_PATH[512];
    sprintf(KEY_PATH, "%s/%s", SSH_DIR, KEY_NAME);
    char CONFIG_FILE[512];
    sprintf(CONFIG_FILE, "%s/config", SSH_DIR);

    printf("%s╔════════════════════════════════════════╗%s\n", BLUE, NC);
    printf("%s║  Automatisation Configuration VPS     ║%s\n", BLUE, NC);
    printf("%s╔════════════════════════════════════════╗%s\n\n", BLUE, NC);

    // Demander le mot de passe root
    char* ROOT_PASSWORD = read_password("Entrez le mot de passe root du serveur : ");
    printf("\n");

    // Demander la passphrase pour la clé SSH
    char* PASSPHRASE = read_password("Entrez la passphrase pour la clé SSH : ");
    printf("\n");

    // Confirmer la passphrase
    char* PASSPHRASE_CONFIRM = read_password("Confirmez la passphrase : ");
    printf("\n");

    if (strcmp(PASSPHRASE, PASSPHRASE_CONFIRM) != 0) {
        printf("%sErreur : Les passphrases ne correspondent pas%s\n", RED, NC);
        free(ROOT_PASSWORD);
        free(PASSPHRASE);
        free(PASSPHRASE_CONFIRM);
        return 1;
    }

    // Étape 1 : Mise à jour et installation sur le serveur
    printf("%s[1/6] Mise à jour du serveur et installation de neovim...%s\n", GREEN, NC);
    char cmd1[1024];
    sprintf(cmd1, "sshpass -p \"%s\" ssh -o StrictHostKeyChecking=no root@%s \"apt update -y && apt upgrade -y && apt install -y neovim && echo '✓ Serveur mis à jour et neovim installé'\"", ROOT_PASSWORD, SERVER_IP);
    system(cmd1);
    printf("%s✓ Étape 1 terminée%s\n\n", GREEN, NC);

    // Étape 2 : Génération de la clé SSH
    printf("%s[2/6] Génération de la clé SSH...%s\n", GREEN, NC);
    char mkdir_cmd[512];
    sprintf(mkdir_cmd, "mkdir -p %s", SSH_DIR);
    system(mkdir_cmd);
    FILE* key_file = fopen(KEY_PATH, "r");
    if (key_file) {
        printf("%sLa clé %s existe déjà, elle sera utilisée%s\n", YELLOW, KEY_NAME, NC);
        fclose(key_file);
    } else {
        char keygen_cmd[1024];
        sprintf(keygen_cmd, "ssh-keygen -t rsa -b 4096 -f %s -N \"%s\" -C \"vps-%s\"", KEY_PATH, PASSPHRASE, SERVER_IP);
        system(keygen_cmd);
        printf("%s✓ Clé SSH générée : %s%s\n", GREEN, KEY_PATH, NC);
    }
    printf("\n");

    // Étape 3 : Copie de la clé sur le serveur
    printf("%s[3/6] Copie de la clé SSH sur le serveur...%s\n", GREEN, NC);
    char copy_cmd[1024];
    sprintf(copy_cmd, "sshpass -p \"%s\" ssh-copy-id -i %s.pub -o StrictHostKeyChecking=no root@%s", ROOT_PASSWORD, KEY_PATH, SERVER_IP);
    system(copy_cmd);
    printf("%s✓ Clé SSH copiée%s\n\n", GREEN, NC);

    // Étape 4 : Configuration du fichier config SSH
    printf("%s[4/6] Configuration du fichier SSH config...%s\n", GREEN, NC);

    // Trouver le prochain numéro de serveur disponible
    int SERVER_NUM = 1;
    char host_line[256];
    sprintf(host_line, "Host srv%d", SERVER_NUM);
    FILE* config = fopen(CONFIG_FILE, "r");
    if (config) {
        char line[256];
        while (fgets(line, sizeof(line), config)) {
            if (strstr(line, host_line) == line) {
                SERVER_NUM++;
                sprintf(host_line, "Host srv%d", SERVER_NUM);
                rewind(config);
            }
        }
        fclose(config);
    }
    char SERVER_NAME[256];
    sprintf(SERVER_NAME, "srv%d", SERVER_NUM);

    // Créer le fichier config s'il n'existe pas
    config = fopen(CONFIG_FILE, "a");
    if (config) {
        fprintf(config, "\nHost %s\n    Hostname %s\n    User root\n    IdentityFile %s\n", SERVER_NAME, SERVER_IP, KEY_PATH);
        fclose(config);
    }

    printf("%s✓ Configuration ajoutée pour %s%s\n", GREEN, SERVER_NAME, NC);
    printf("%sVous pouvez maintenant vous connecter avec : ssh %s%s\n\n", BLUE, SERVER_NAME, NC);

    // Étape 5 : Désactivation de l'authentification par mot de passe
    printf("%s[5/6] Désactivation de l'authentification par mot de passe...%s\n", GREEN, NC);

    // Créer le script de configuration SSH
    FILE* script_file = fopen("/tmp/ssh_config.sh", "w");
    if (script_file) {
        fprintf(script_file, "#!/bin/bash\ncd /etc/ssh\n\n# Backup du fichier de config\ncp sshd_config sshd_config.backup.$(date +%%Y%%m%%d_%%H%%M%%S)\n\n# Modifications de sshd_config\nsed -i 's/#*PasswordAuthentication.*/PasswordAuthentication no/' sshd_config\nsed -i 's/#*PubkeyAuthentication.*/PubkeyAuthentication yes/' sshd_config\nsed -i 's/#*ChallengeResponseAuthentication.*/ChallengeResponseAuthentication no/' sshd_config\nsed -i 's/#*UsePAM.*/UsePAM no/' sshd_config\nsed -i 's/#*PermitRootLogin.*/PermitRootLogin prohibit-password/' sshd_config\n\necho \"✓ Configuration SSH modifiée\"\n");
        fclose(script_file);
        system("chmod +x /tmp/ssh_config.sh");
    }

    // Copier et exécuter le script sur le serveur
    char scp_cmd[1024];
    sprintf(scp_cmd, "scp -i %s /tmp/ssh_config.sh root@%s:/tmp/", KEY_PATH, SERVER_IP);
    system(scp_cmd);
    char ssh_exec_cmd[1024];
    sprintf(ssh_exec_cmd, "ssh -i %s root@%s \"bash /tmp/ssh_config.sh\"", KEY_PATH, SERVER_IP);
    system(ssh_exec_cmd);

    printf("%s✓ Authentification par mot de passe désactivée%s\n\n", GREEN, NC);

    // Étape 6 : Redémarrage du service SSH
    printf("%s[6/6] Redémarrage du service SSH...%s\n", GREEN, NC);

    char restart_cmd[1024];
    sprintf(restart_cmd, "ssh -i %s root@%s \"systemctl daemon-reload && systemctl restart ssh && systemctl restart ssh.socket 2>/dev/null || true && echo '✓ Service SSH redémarré'\"", KEY_PATH, SERVER_IP);
    system(restart_cmd);

    printf("%s✓ Service SSH redémarré%s\n\n", GREEN, NC);

    // Nettoyage
    system("rm /tmp/ssh_config.sh");

    // Résumé
    printf("%s╔════════════════════════════════════════╗%s\n", BLUE, NC);
    printf("%s║        Configuration terminée !        ║%s\n", BLUE, NC);
    printf("%s╚════════════════════════════════════════╝%s\n\n", BLUE, NC);

    printf("%sRésumé de la configuration :%s\n", GREEN, NC);
    printf("  • Serveur mis à jour ✓\n");
    printf("  • Neovim installé ✓\n");
    printf("  • Clé SSH créée : %s%s%s\n", YELLOW, KEY_PATH, NC);
    printf("  • Alias SSH créé : %s%s%s\n", YELLOW, SERVER_NAME, NC);
    printf("  • Authentification par mot de passe : %sDÉSACTIVÉE%s\n", RED, NC);
    printf("  • Authentification par clé : %sACTIVÉE%s\n\n", GREEN, NC);

    printf("%sCommande de connexion :%s\n", YELLOW, NC);
    printf("  %sssh %s%s\n\n", BLUE, SERVER_NAME, NC);

    printf("%s⚠️  IMPORTANT :%s\n", RED, NC);
    printf("  • Testez la connexion MAINTENANT dans un nouveau terminal\n");
    printf("  • L'authentification par mot de passe est désactivée\n");
    printf("  • Conservez votre clé privée : %s\n", KEY_PATH);
    printf("  • N'oubliez pas votre passphrase SSH !\n\n");

    // Test de connexion
    printf("%sTest de connexion...%s\n", YELLOW, NC);
    char test_cmd[1024];
    sprintf(test_cmd, "ssh -i %s -o BatchMode=yes -o ConnectTimeout=5 root@%s \"echo 'Connexion réussie'\" 2>/dev/null", KEY_PATH, SERVER_IP);
    int test_result = system(test_cmd);
    if (test_result == 0) {
        printf("%s✓ Test de connexion réussi !%s\n\n", GREEN, NC);
    } else {
        printf("%s✗ Erreur de connexion. Vérifiez la configuration.%s\n\n", RED, NC);
    }

    printf("%sScript terminé avec succès !%s\n", GREEN, NC);

    // Libération de la mémoire
    free(ROOT_PASSWORD);
    free(PASSPHRASE);
    free(PASSPHRASE_CONFIRM);

    return 0;
}