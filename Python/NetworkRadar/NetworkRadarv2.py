"""
Application de scan réseau avec affichage radar
Scanne le réseau local, détecte les appareils et les affiche sur un radar animé
Version améliorée avec effets visuels et correction des bugs
"""

import pygame
import math
import subprocess
import platform
import ipaddress
import threading
import time
import re
from collections import deque
from datetime import datetime

# Configuration
WIDTH, HEIGHT = 1200, 800
FPS = 60
SCAN_INTERVAL = 5  # secondes entre chaque ping

# Couleurs - Thème bleu glacial
ICE_BLUE = (2, 2, 40)  # Fond bleu glacial foncé
CYAN_ICE = (170, 211, 233)  # Cyan glacial
LIGHT_ICE = (150, 230, 255)  # Bleu glacial clair
PALE_ICE = (200, 240, 255)  # Bleu très pâle
GREEN = (0, 255, 150)  # Vert plus vif
RED = (255, 50, 80)  # Rouge plus vif
YELLOW = (255, 255, 100)
WHITE = (255, 255, 255)
GLOW_CYAN = (50, 200, 255)  # Cyan brillant pour les effets

class NetworkDevice:
    """Représente un appareil sur le réseau"""
    def __init__(self, ip, hostname="Unknown"):
        self.ip = ip
        self.hostname = hostname
        self.is_online = True
        self.last_seen = datetime.now()
        self.response_time = 0
        self.angle = 0  # Position angulaire sur le radar
        self.distance = 0  # Distance du centre (simulée)
        
    def update_status(self, is_online, response_time=0):
        self.is_online = is_online
        if is_online:
            self.last_seen = datetime.now()
            self.response_time = response_time

class NetworkScanner:
    """Gestion du scan réseau et des pings"""
    def __init__(self):
        self.devices = {}
        self.network = self.get_local_network()
        self.scanning = False
        self.scan_thread = None
        self.ping_thread = None
        
    def get_local_network(self):
        """Détecte le réseau local en analysant ipconfig sur Windows"""
        try:
            if platform.system() == "Windows":
                result = subprocess.run(['ipconfig'], capture_output=True, text=True, encoding='cp850')
                
                # Recherche de l'adaptateur WiFi ou Ethernet actif
                lines = result.stdout.split('\n')
                ip_address = None
                subnet_mask = None
                
                for line in lines:
                    line = line.strip()
                    
                    # Recherche l'adresse IPv4
                    if "Adresse IPv4" in line or "IPv4 Address" in line:
                        # Extrait l'IP avec regex
                        ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
                        if ip_match:
                            potential_ip = ip_match.group(1)
                            # Ignore les adresses loopback et auto-config
                            if not potential_ip.startswith('127.') and not potential_ip.startswith('169.254.'):
                                ip_address = potential_ip
                    
                    # Recherche le masque de sous-réseau
                    if "Masque de sous-r" in line or "Subnet Mask" in line:
                        mask_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
                        if mask_match:
                            subnet_mask = mask_match.group(1)
                    
                    # Si on a trouvé IP et masque, on calcule le réseau
                    if ip_address and subnet_mask:
                        network = self.calculate_network(ip_address, subnet_mask)
                        print(f"✓ Réseau détecté: {network}")
                        return network
                
                # Si aucune IP trouvée, utilise la valeur par défaut
                print("⚠ Aucun réseau actif détecté, utilisation du réseau par défaut")
                return "192.168.1.0/24"
            
            else:  # Linux/Mac
                result = subprocess.run(['ip', 'route'], capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if 'default' in line:
                        parts = line.split()
                        if len(parts) > 2:
                            gateway = parts[2]
                            base = '.'.join(gateway.split('.')[:3])
                            network = f"{base}.0/24"
                            print(f"✓ Réseau détecté: {network}")
                            return network
        except Exception as e:
            print(f"❌ Erreur lors de la détection du réseau: {e}")
        
        return "192.168.1.0/24"  # Par défaut
    
    def calculate_network(self, ip, mask):
        """Calcule l'adresse réseau à partir de l'IP et du masque"""
        try:
            # Convertit l'IP et le masque en entiers
            ip_parts = [int(x) for x in ip.split('.')]
            mask_parts = [int(x) for x in mask.split('.')]
            
            # Calcule l'adresse réseau avec un ET logique
            network_parts = [ip_parts[i] & mask_parts[i] for i in range(4)]
            network_address = '.'.join(map(str, network_parts))
            
            # Détermine le CIDR à partir du masque
            cidr = sum([bin(x).count('1') for x in mask_parts])
            
            return f"{network_address}/{cidr}"
        except:
            # En cas d'erreur, utilise /24 par défaut
            base = '.'.join(ip.split('.')[:3])
            return f"{base}.0/24"
    
    def ping_device(self, ip):
        """Ping un appareil et retourne (success, response_time)"""
        param = "-n" if platform.system() == "Windows" else "-c"
        timeout_param = "-w" if platform.system() == "Windows" else "-W"
        
        try:
            start = time.time()
            result = subprocess.run(
                ['ping', param, '1', timeout_param, '1000', str(ip)],
                capture_output=True,
                text=True,
                timeout=2
            )
            response_time = (time.time() - start) * 1000  # en ms
            return result.returncode == 0, response_time
        except:
            return False, 0
    
    def scan_network(self):
        """Scanne le réseau pour trouver les appareils"""
        print(f"\n🔍 Scan du réseau {self.network}...")
        print("=" * 50)
        network = ipaddress.ip_network(self.network, strict=False)
        
        angle_step = 360 / min(254, network.num_addresses)
        current_angle = 0
        
        scanned = 0
        total = min(254, network.num_addresses - 2)
        
        for ip in network.hosts():
            if not self.scanning:
                break
                
            ip_str = str(ip)
            is_online, response_time = self.ping_device(ip_str)
            
            scanned += 1
            if scanned % 10 == 0:  # Affiche progression tous les 10 IPs
                print(f"Progression: {scanned}/{total} IPs scannées...")
            
            if is_online:
                if ip_str not in self.devices:
                    # Nouvel appareil détecté
                    device = NetworkDevice(ip_str)
                    device.angle = current_angle
                    device.distance = 50 + (hash(ip_str) % 200)  # Distance simulée
                    self.devices[ip_str] = device
                    print(f"✓ Appareil trouvé: {ip_str} ({response_time:.0f}ms)")
                else:
                    self.devices[ip_str].update_status(True, response_time)
            
            current_angle += angle_step
        
        print("=" * 50)
        print(f"✅ Scan terminé. {len(self.devices)} appareil(s) trouvé(s).\n")
    
    def continuous_ping(self):
        """Ping continu des appareils détectés"""
        while self.scanning:
            for ip, device in list(self.devices.items()):
                if not self.scanning:
                    break
                is_online, response_time = self.ping_device(ip)
                device.update_status(is_online, response_time)
            
            time.sleep(SCAN_INTERVAL)
    
    def start_scanning(self):
        """Démarre le scan et le monitoring"""
        if not self.scanning:
            self.scanning = True
            self.scan_thread = threading.Thread(target=self.scan_network, daemon=True)
            self.scan_thread.start()
            
            # Attend que le scan initial soit terminé
            self.scan_thread.join()
            
            # Lance le ping continu
            if len(self.devices) > 0:
                self.ping_thread = threading.Thread(target=self.continuous_ping, daemon=True)
                self.ping_thread.start()
    
    def stop_scanning(self):
        """Arrête le scan"""
        self.scanning = False

class RadarDisplay:
    """Affichage graphique du radar"""
    def __init__(self, width, height):
        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Network Radar Scanner - Ice Blue Edition")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 20)
        self.font_small = pygame.font.Font(None, 16)
        self.font_large = pygame.font.Font(None, 32)
        self.font_title = pygame.font.Font(None, 48)
        
        self.center_x = width // 2
        self.center_y = height // 2
        self.radar_radius = min(width, height) // 3
        
        self.sweep_angle = 0
        self.sweep_speed = 2
        
        # Historique des positions pour l'effet de traînée
        self.sweep_trail = deque(maxlen=30)
    
    def draw_radar_grid(self):
        """Dessine la grille du radar avec style glacial"""
        # Cercles concentriques
        for i in range(1, 5):
            radius = self.radar_radius * i // 4
            # Effet de brillance sur les cercles
            pygame.draw.circle(self.screen, LIGHT_ICE, 
                             (self.center_x, self.center_y), radius, 2)
            pygame.draw.circle(self.screen, PALE_ICE, 
                             (self.center_x, self.center_y), radius, 1)
        
        # Cercle extérieur plus épais
        pygame.draw.circle(self.screen, CYAN_ICE, 
                         (self.center_x, self.center_y), self.radar_radius, 3)
        
        # Cercle extérieur plus épais
        pygame.draw.circle(self.screen, CYAN_ICE, 
                         (self.center_x, self.center_y), self.radar_radius, 5)
        
        # Lignes radiales (tous les 15 degrés)
        for angle in range(0, 360, 15):
            rad = math.radians(angle)
            end_x = self.center_x + math.cos(rad) * self.radar_radius
            end_y = self.center_y + math.sin(rad) * self.radar_radius
            
            # Lignes principales plus épaisses tous les 45°
            if angle % 45 == 0:
                pygame.draw.line(self.screen, LIGHT_ICE,
                               (self.center_x, self.center_y),
                               (end_x, end_y), 2)
            else:
                pygame.draw.line(self.screen, LIGHT_ICE,
                               (self.center_x, self.center_y),
                               (end_x, end_y), 1)
        
        # Labels des angles avec meilleur style
        angles = [0, 45, 90, 135, 180, 225, 270, 315]
        for angle in angles:
            rad = math.radians(angle)
            label_dist = self.radar_radius + 30
            x = self.center_x + math.cos(rad) * label_dist
            y = self.center_y + math.sin(rad) * label_dist
            text = self.font.render(f"{angle}°", True, CYAN_ICE)
            rect = text.get_rect(center=(x, y))
            self.screen.blit(text, rect)
        
        # Point central brillant
        pygame.draw.circle(self.screen, GLOW_CYAN, (self.center_x, self.center_y), 8)
        pygame.draw.circle(self.screen, WHITE, (self.center_x, self.center_y), 4)

    def draw_sweep(self):
        """Dessine le balayage du radar avec effet de traînée amélioré"""
        # Ajoute la position actuelle à la traînée
        self.sweep_trail.append(self.sweep_angle)
        
        # Dessine la traînée avec transparence décroissante et dégradé
        for i, angle in enumerate(self.sweep_trail):
            alpha = int(255 * (i / len(self.sweep_trail)))
            rad = math.radians(angle)
            end_x = self.center_x + math.cos(rad) * self.radar_radius
            end_y = self.center_y + math.sin(rad) * self.radar_radius
            
            # Dégradé de couleur dans la traînée
            green_component = int(alpha * 0.8)
            color = (green_component, alpha, alpha)
            
            # Épaisseur variable
            thickness = max(1, int(3 * (i / len(self.sweep_trail))))
            pygame.draw.line(self.screen, color,
                           (self.center_x, self.center_y),
                           (end_x, end_y), thickness)
        
        # Ligne principale du balayage plus visible
        rad = math.radians(self.sweep_angle)
        end_x = self.center_x + math.cos(rad) * self.radar_radius
        end_y = self.center_y + math.sin(rad) * self.radar_radius
        
        # Ligne avec effet de brillance
        pygame.draw.line(self.screen, GLOW_CYAN,
                        (self.center_x, self.center_y),
                        (end_x, end_y), 4)
        pygame.draw.line(self.screen, WHITE,
                        (self.center_x, self.center_y),
                        (end_x, end_y), 2)
        
        # Met à jour l'angle
        self.sweep_angle = (self.sweep_angle + self.sweep_speed) % 360

    def draw_device(self, device):
        """Dessine un appareil sur le radar avec effet de clignotement au passage du balayage"""
        # Calcul de la position
        rad = math.radians(device.angle)
        scale = device.distance / 300  # Normalisation
        distance = self.radar_radius * scale
        
        x = int(self.center_x + math.cos(rad) * distance)
        y = int(self.center_y + math.sin(rad) * distance)
        
        # Couleur selon le statut
        color = GREEN if device.is_online else RED
        
        # Calcul de la différence d'angle entre le balayage et l'appareil
        angle_diff = abs(self.sweep_angle - device.angle)
        if angle_diff > 180:
            angle_diff = 360 - angle_diff
        
        # Effet de clignotement quand le balayage passe (dans une zone de 40°)
        is_being_swept = angle_diff < 40
        
        if is_being_swept:
            # Calcul de l'intensité du clignotement (plus proche = plus lumineux)
            intensity = 1 - (angle_diff / 40)
            
            # Taille du point qui grandit au passage
            base_size = 6
            sweep_size = int(base_size + intensity * 10)
            
            # Couleur plus brillante au passage
            if device.is_online:
                bright_color = (
                    int(100 + intensity * 155),
                    int(255),
                    int(150 + intensity * 105)
                )
            else:
                bright_color = (
                    int(255),
                    int(100 + intensity * 155),
                    int(100 + intensity * 155)
                )
            
            # Point principal avec taille variable et halo
            pygame.draw.circle(self.screen, bright_color, (x, y), sweep_size + 4, 2)
            pygame.draw.circle(self.screen, bright_color, (x, y), sweep_size)
            pygame.draw.circle(self.screen, WHITE, (x, y), sweep_size + 6, 1)
            
            # Cercles d'onde concentriques au moment du passage
            for wave_offset in range(1, 4):
                wave_radius = int(sweep_size + intensity * 15 * wave_offset)
                wave_alpha = max(0, int(255 * intensity / wave_offset))
                if wave_alpha > 30:
                    wave_color = (bright_color[0] // wave_offset, 
                                bright_color[1] // wave_offset, 
                                bright_color[2] // wave_offset)
                    pygame.draw.circle(self.screen, wave_color, (x, y), wave_radius, 2)
            
        else:
            # Point normal quand le balayage n'est pas dessus
            pygame.draw.circle(self.screen, color, (x, y), 7)
            pygame.draw.circle(self.screen, WHITE, (x, y), 9, 2)
            
            # Effet de pulsation lente pour les appareils en ligne
            if device.is_online:
                pulse_size = 13 + int(5 * math.sin(time.time() * 2))
                pygame.draw.circle(self.screen, color, (x, y), pulse_size, 1)
    
    def draw_info_panel(self, scanner):
        """Dessine le panneau d'informations avec style amélioré"""
        panel_x = 30
        panel_y = 30
        
        # Fond semi-transparent pour le panneau
        panel_width = 350
        panel_height = 350
        panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel_surface.fill((10, 25, 50, 180))
        self.screen.blit(panel_surface, (panel_x - 15, panel_y - 15))
        
        # Bordure du panneau
        pygame.draw.rect(self.screen, CYAN_ICE, 
                        (panel_x - 15, panel_y - 15, panel_width, panel_height), 2)
        
        # Titre stylisé
        title = self.font_large.render("NETWORK RADAR", True, GLOW_CYAN)
        self.screen.blit(title, (panel_x, panel_y))
        
        # Sous-titre
        subtitle = self.font_small.render("Ice Blue Edition", True, PALE_ICE)
        self.screen.blit(subtitle, (panel_x, panel_y + 35))
        
        # Informations générales
        y_offset = panel_y + 70
        info_lines = [
            ("Réseau:", scanner.network),
            ("Appareils:", str(len(scanner.devices))),
            ("En ligne:", str(sum(1 for d in scanner.devices.values() if d.is_online))),
            ("Hors ligne:", str(sum(1 for d in scanner.devices.values() if not d.is_online))),
        ]
        
        for label, value in info_lines:
            text_label = self.font.render(label, True, LIGHT_ICE)
            text_value = self.font.render(value, True, WHITE)
            self.screen.blit(text_label, (panel_x, y_offset))
            self.screen.blit(text_value, (panel_x + 120, y_offset))
            y_offset += 28
        
        # Séparateur
        pygame.draw.line(self.screen, CYAN_ICE, 
                        (panel_x, y_offset + 5), 
                        (panel_x + 320, y_offset + 5), 2)
        
        # Liste des appareils
        y_offset += 20
        list_title = self.font.render("APPAREILS DÉTECTÉS:", True, CYAN_ICE)
        self.screen.blit(list_title, (panel_x, y_offset))
        y_offset += 30
        
        if len(scanner.devices) == 0:
            no_device = self.font_small.render("Aucun appareil détecté", True, LIGHT_ICE)
            self.screen.blit(no_device, (panel_x, y_offset))
        else:
            for ip, device in list(scanner.devices.items())[:10]:  # Limite à 10
                status = "●" if device.is_online else "○"
                color = GREEN if device.is_online else RED
                ping = f"{device.response_time:.0f}ms" if device.is_online else "N/A"
                
                # IP tronquée si trop longue
                display_ip = ip if len(ip) <= 15 else ip[:12] + "..."
                
                text = self.font_small.render(f"{status} {display_ip}", True, color)
                self.screen.blit(text, (panel_x, y_offset))
                
                ping_text = self.font_small.render(ping, True, LIGHT_ICE)
                self.screen.blit(ping_text, (panel_x + 200, y_offset))
                
                y_offset += 22
    
    def draw_legend(self):
        """Dessine la légende avec style amélioré"""
        legend_x = WIDTH - 230
        legend_y = HEIGHT - 120
        
        # Fond semi-transparent
        legend_surface = pygame.Surface((210, 100), pygame.SRCALPHA)
        legend_surface.fill((10, 25, 50, 180))
        self.screen.blit(legend_surface, (legend_x - 15, legend_y - 15))
        
        # Bordure
        pygame.draw.rect(self.screen, CYAN_ICE, 
                        (legend_x - 15, legend_y - 15, 210, 100), 2)
        
        # Titre
        title = self.font.render("LÉGENDE", True, CYAN_ICE)
        self.screen.blit(title, (legend_x, legend_y - 5))
        
        # Icônes et labels
        pygame.draw.circle(self.screen, GREEN, (legend_x + 10, legend_y + 30), 7)
        pygame.draw.circle(self.screen, WHITE, (legend_x + 10, legend_y + 30), 9, 1)
        text = self.font_small.render("En ligne", True, WHITE)
        self.screen.blit(text, (legend_x + 30, legend_y + 22))
        
        pygame.draw.circle(self.screen, RED, (legend_x + 10, legend_y + 55), 7)
        pygame.draw.circle(self.screen, WHITE, (legend_x + 10, legend_y + 55), 9, 1)
        text = self.font_small.render("Hors ligne", True, WHITE)
        self.screen.blit(text, (legend_x + 30, legend_y + 47))
    
    def run(self, scanner):
        """Boucle principale d'affichage"""
        running = True
        
        # Lance le scan dans un thread
        scan_thread = threading.Thread(target=scanner.start_scanning, daemon=True)
        scan_thread.start()
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_r:
                        # Relance un scan
                        print("\n🔄 Relance du scan...")
                        scanner.devices.clear()
                        scan_thread = threading.Thread(target=scanner.start_scanning, daemon=True)
                        scan_thread.start()
            
            # Affichage avec fond bleu glacial
            self.screen.fill(ICE_BLUE)
            
            self.draw_radar_grid()
            self.draw_sweep()
            
            # Dessine les appareils
            for device in scanner.devices.values():
                self.draw_device(device)
            
            self.draw_info_panel(scanner)
            self.draw_legend()
            
            # Instructions en bas
            instructions = self.font.render("R: Nouveau scan | ESC: Quitter", True, PALE_ICE)
            self.screen.blit(instructions, (WIDTH // 2 - 140, HEIGHT - 35))
            
            pygame.display.flip()
            self.clock.tick(FPS)
        
        scanner.stop_scanning()
        pygame.quit()

def main():
    """Fonction principale"""
    print("=" * 60)
    print("🔷 NETWORK RADAR SCANNER - ICE BLUE EDITION 🔷")
    print("=" * 60)
    print("Démarrage de l'application...")
    print("")
    
    scanner = NetworkScanner()
    radar = RadarDisplay(WIDTH, HEIGHT)
    
    try:
        radar.run(scanner)
    except KeyboardInterrupt:
        print("\n⚠ Interruption utilisateur...")
        scanner.stop_scanning()
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        scanner.stop_scanning()
    finally:
        print("✅ Application arrêtée.")

if __name__ == "__main__":
    main()