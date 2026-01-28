#!/usr/bin/env python3
"""
Scanner de réseau WiFi avec interface radar style sonar
Couleurs: noir et vert (style Matrix/militaire)
Version Windows compatible - Sans dépendances externes complexes
"""

import tkinter as tk
from tkinter import ttk, messagebox
import math
import threading
import time
import socket
import subprocess
import re
import platform
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed

class WifiRadarScanner:
    def __init__(self, root):
        self.root = root
        self.root.title("WiFi Radar Scanner v2.0")
        self.root.geometry("1200x800")
        self.root.configure(bg='#000000')
        
        # Couleurs du thème
        self.bg_color = '#000000'
        self.radar_color = '#00FF00'
        self.text_color = '#00FF00'
        self.device_color = '#00FF00'
        
        # Variables
        self.devices = []
        self.angle = 0
        self.scanning = False
        self.radar_lines = []
        self.scan_progress = 0
        
        # Détecter l'OS
        self.os_type = platform.system()
        
        # Configuration de l'interface
        self.setup_ui()
        
        # Démarrer l'animation du radar
        self.animate_radar()
        
    def setup_ui(self):
        # Frame principal
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Frame gauche pour la liste des appareils
        left_frame = tk.Frame(main_frame, bg=self.bg_color, width=350)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))
        left_frame.pack_propagate(False)
        
        # Titre de la liste
        title_label = tk.Label(
            left_frame, 
            text="APPAREILS DÉTECTÉS", 
            bg=self.bg_color, 
            fg=self.text_color,
            font=('Courier', 12, 'bold')
        )
        title_label.pack(pady=(0, 10))
        
        # Frame pour la liste avec scrollbar
        list_frame = tk.Frame(left_frame, bg=self.bg_color)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(list_frame, bg='#003300', troughcolor=self.bg_color)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Text widget pour la liste
        self.device_list = tk.Text(
            list_frame,
            bg='#001100',
            fg=self.text_color,
            font=('Courier', 9),
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            relief=tk.SOLID,
            borderwidth=2
        )
        self.device_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.device_list.yview)
        
        # Boutons de contrôle
        button_frame = tk.Frame(left_frame, bg=self.bg_color)
        button_frame.pack(pady=10)
        
        self.scan_button = tk.Button(
            button_frame,
            text="▶ DÉMARRER SCAN",
            bg='#003300',
            fg=self.text_color,
            font=('Courier', 10, 'bold'),
            command=self.toggle_scan,
            relief=tk.RAISED,
            borderwidth=2,
            padx=10,
            pady=5,
            cursor='hand2'
        )
        self.scan_button.pack()
        
        # Barre de progression
        self.progress_bar = ttk.Progressbar(
            left_frame,
            mode='determinate',
            length=300
        )
        self.progress_bar.pack(pady=5)
        
        # Status label
        self.status_label = tk.Label(
            left_frame,
            text="Status: En attente",
            bg=self.bg_color,
            fg=self.text_color,
            font=('Courier', 9)
        )
        self.status_label.pack(pady=5)
        
        # Compteur d'appareils
        self.device_count_label = tk.Label(
            left_frame,
            text="Appareils: 0",
            bg=self.bg_color,
            fg=self.text_color,
            font=('Courier', 10, 'bold')
        )
        self.device_count_label.pack(pady=5)
        
        # Frame droit pour le radar
        right_frame = tk.Frame(main_frame, bg=self.bg_color)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Canvas pour le radar
        self.canvas = tk.Canvas(
            right_frame,
            bg=self.bg_color,
            highlightthickness=2,
            highlightbackground=self.radar_color
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Dessiner le radar initial
        self.root.after(100, self.draw_radar_base)
        
    def draw_radar_base(self):
        """Dessine la base du radar (cercles concentriques)"""
        self.canvas.delete("all")
        
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        if width < 10 or height < 10:
            self.root.after(100, self.draw_radar_base)
            return
            
        center_x = width // 2
        center_y = height // 2
        max_radius = min(width, height) // 2 - 30
        
        # Dessiner les cercles concentriques
        for i in range(1, 5):
            radius = (max_radius // 4) * i
            self.canvas.create_oval(
                center_x - radius, center_y - radius,
                center_x + radius, center_y + radius,
                outline=self.radar_color,
                width=1
            )
        
        # Dessiner les lignes de grille (croix)
        self.canvas.create_line(
            center_x, center_y - max_radius,
            center_x, center_y + max_radius,
            fill=self.radar_color,
            width=1
        )
        self.canvas.create_line(
            center_x - max_radius, center_y,
            center_x + max_radius, center_y,
            fill=self.radar_color,
            width=1
        )
        
        # Lignes diagonales
        offset = int(max_radius * 0.707)
        self.canvas.create_line(
            center_x - offset, center_y - offset,
            center_x + offset, center_y + offset,
            fill=self.radar_color,
            width=1,
            dash=(2, 4)
        )
        self.canvas.create_line(
            center_x - offset, center_y + offset,
            center_x + offset, center_y - offset,
            fill=self.radar_color,
            width=1,
            dash=(2, 4)
        )
        
        # Dessiner le point central
        self.canvas.create_oval(
            center_x - 5, center_y - 5,
            center_x + 5, center_y + 5,
            fill=self.radar_color,
            outline=self.radar_color
        )
        
        # Label du radar
        self.canvas.create_text(
            center_x, 20,
            text="RADAR RÉSEAU WiFi",
            fill=self.text_color,
            font=('Courier', 14, 'bold')
        )
        
        # Labels des distances
        for i in range(1, 5):
            radius = (max_radius // 4) * i
            self.canvas.create_text(
                center_x + radius + 5, center_y + 5,
                text=f"{i*25}m",
                fill=self.radar_color,
                font=('Courier', 8)
            )
        
    def animate_radar(self):
        """Animation du balayage radar"""
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        if width < 10 or height < 10:
            self.root.after(50, self.animate_radar)
            return
            
        center_x = width // 2
        center_y = height // 2
        max_radius = min(width, height) // 2 - 30
        
        # Effacer les anciennes lignes de balayage
        for line in self.radar_lines:
            try:
                self.canvas.delete(line)
            except:
                pass
        self.radar_lines.clear()
        
        # Dessiner la ligne de balayage principale
        end_x = center_x + max_radius * math.cos(math.radians(self.angle))
        end_y = center_y + max_radius * math.sin(math.radians(self.angle))
        
        main_line = self.canvas.create_line(
            center_x, center_y, end_x, end_y,
            fill=self.radar_color,
            width=3
        )
        self.radar_lines.append(main_line)
        
        # Effet de traînée (lignes semi-transparentes)
        for i in range(1, 8):
            fade_angle = self.angle - i * 8
            fade_end_x = center_x + max_radius * math.cos(math.radians(fade_angle))
            fade_end_y = center_y + max_radius * math.sin(math.radians(fade_angle))
            
            # Calculer l'intensité de la couleur verte
            intensity = int(255 * (1 - i/8))
            fade_color = f'#{0:02x}{intensity:02x}{0:02x}'
            
            fade_line = self.canvas.create_line(
                center_x, center_y, fade_end_x, fade_end_y,
                fill=fade_color,
                width=max(1, 3 - i // 2)
            )
            self.radar_lines.append(fade_line)
        
        # Dessiner les appareils détectés
        self.draw_devices()
        
        # Incrémenter l'angle
        self.angle = (self.angle + 3) % 360
        
        # Continuer l'animation
        self.root.after(50, self.animate_radar)
        
    def draw_devices(self):
        """Dessine les appareils sur le radar"""
        # Supprimer les anciens marqueurs d'appareils
        self.canvas.delete('device')
        
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        if width < 10 or height < 10:
            return
            
        center_x = width // 2
        center_y = height // 2
        max_radius = min(width, height) // 2 - 30
        
        for i, device in enumerate(self.devices):
            # Positionner l'appareil de manière circulaire
            angle = (i * 360 / max(len(self.devices), 1)) % 360
            distance = max_radius * 0.65  # 65% du rayon max
            
            device_x = center_x + distance * math.cos(math.radians(angle))
            device_y = center_y + distance * math.sin(math.radians(angle))
            
            # Effet de pulsation (cercle externe)
            pulse_size = 12 + 3 * math.sin(time.time() * 2 + i)
            self.canvas.create_oval(
                device_x - pulse_size, device_y - pulse_size,
                device_x + pulse_size, device_y + pulse_size,
                outline=self.radar_color,
                width=1,
                tags='device'
            )
            
            # Dessiner le point de l'appareil
            self.canvas.create_oval(
                device_x - 6, device_y - 6,
                device_x + 6, device_y + 6,
                fill='#00FF00',
                outline='#FFFFFF',
                width=2,
                tags='device'
            )
            
            # Ligne de connexion au centre
            self.canvas.create_line(
                center_x, center_y,
                device_x, device_y,
                fill=self.radar_color,
                width=1,
                dash=(2, 4),
                tags='device'
            )
            
            # Icône selon le type d'appareil
            icon = self.get_device_icon(device)
            self.canvas.create_text(
                device_x, device_y - 22,
                text=icon,
                fill=self.text_color,
                font=('Arial', 16),
                tags='device'
            )
            
            # Nom court de l'appareil
            short_name = device.get('hostname', 'N/A')[:12]
            self.canvas.create_text(
                device_x, device_y + 20,
                text=short_name,
                fill=self.text_color,
                font=('Courier', 7),
                tags='device'
            )
    
    def get_device_icon(self, device):
        """Retourne une icône selon le type d'appareil"""
        hostname = device.get('hostname', '').lower()
        vendor = device.get('vendor', '').lower()
        
        # Détection basée sur le hostname et le vendor
        if 'iphone' in hostname or 'ipad' in hostname or 'apple' in vendor:
            return '📱'
        elif 'android' in hostname or 'samsung' in hostname or 'galaxy' in hostname:
            return '📱'
        elif 'router' in hostname or 'gateway' in hostname:
            return '📡'
        elif 'laptop' in hostname or 'pc-' in hostname or 'desktop' in hostname:
            return '💻'
        elif 'tv' in hostname or 'smart' in hostname:
            return '📺'
        elif 'printer' in hostname or 'print' in hostname:
            return '🖨️'
        elif 'raspberry' in hostname or 'pi' in hostname:
            return '🔧'
        elif 'camera' in hostname or 'cam' in hostname:
            return '📷'
        else:
            return '🖥️'
    
    def toggle_scan(self):
        """Démarre ou arrête le scan"""
        if not self.scanning:
            self.scanning = True
            self.scan_button.config(text="■ ARRÊTER SCAN", bg='#330000')
            self.status_label.config(text="Status: Scan en cours...")
            self.progress_bar['value'] = 0
            threading.Thread(target=self.scan_network, daemon=True).start()
        else:
            self.scanning = False
            self.scan_button.config(text="▶ DÉMARRER SCAN", bg='#003300')
            self.status_label.config(text="Status: Scan arrêté")
    
    def get_local_ip(self):
        """Obtient l'adresse IP locale"""
        try:
            # Méthode compatible Windows/Linux/Mac
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.1)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception as e:
            print(f"Erreur get_local_ip: {e}")
            return None
    
    def is_host_alive(self, ip):
        """Vérifie si un hôte est accessible"""
        try:
            # Utiliser ping selon l'OS
            if self.os_type == "Windows":
                command = ["ping", "-n", "1", "-w", "500", ip]
            else:
                command = ["ping", "-c", "1", "-W", "1", ip]
            
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=2
            )
            return result.returncode == 0
        except:
            return False
    
    def get_hostname(self, ip):
        """Obtient le nom d'hôte à partir de l'IP"""
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            return hostname
        except:
            return f"Device-{ip.split('.')[-1]}"
    
    def get_mac_address(self, ip):
        """Obtient l'adresse MAC (Windows/Linux)"""
        try:
            if self.os_type == "Windows":
                # Utiliser arp -a sur Windows
                result = subprocess.run(
                    ["arp", "-a", ip],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                output = result.stdout
                
                # Rechercher le format MAC Windows (xx-xx-xx-xx-xx-xx)
                mac_pattern = r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})'
                match = re.search(mac_pattern, output)
                if match:
                    return match.group(0).replace('-', ':')
            else:
                # Utiliser arp sur Linux/Mac
                result = subprocess.run(
                    ["arp", "-n", ip],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                output = result.stdout
                mac_pattern = r'([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}'
                match = re.search(mac_pattern, output)
                if match:
                    return match.group(0)
        except:
            pass
        return "N/A"
    
    def get_vendor_from_mac(self, mac):
        """Base de données simplifiée des fabricants"""
        if mac == "N/A":
            return "Inconnu"
        
        mac_upper = mac.upper().replace(':', '').replace('-', '')[:6]
        
        vendors = {
            '001A11': 'Google',
            '0050F2': 'Microsoft',
            'DCA632': 'Raspberry Pi',
            'B827EB': 'Raspberry Pi',
            'D83ADD': 'Raspberry Pi',
            '000A95': 'Apple',
            '00039': 'Apple',
            '001B63': 'Apple',
            '28CDC4': 'Apple',
            '001EC2': 'Apple',
            '001F3C': 'Samsung',
            '0015B9': 'TP-Link',
            '00059A': 'Cisco',
            'E84E06': 'TP-Link',
            '50C7BF': 'TP-Link',
            'A036BC': 'D-Link',
            '001D0F': 'Dell',
            '00237D': 'Huawei',
        }
        
        for prefix, vendor in vendors.items():
            if mac_upper.startswith(prefix):
                return vendor
        
        return "Inconnu"
    
    def scan_network(self):
        """Scanne le réseau pour trouver les appareils"""
        try:
            # Obtenir l'IP locale
            local_ip = self.get_local_ip()
            
            if not local_ip:
                self.update_status("Erreur: Impossible de détecter votre IP")
                self.scanning = False
                self.scan_button.config(text="▶ DÉMARRER SCAN", bg='#003300')
                return
            
            # Calculer le réseau
            ip_parts = local_ip.split('.')
            network_base = '.'.join(ip_parts[:3])
            
            self.update_status(f"Scan du réseau {network_base}.0/24...")
            self.devices.clear()
            
            # Scanner les 254 adresses possibles
            alive_hosts = []
            
            # Utiliser ThreadPoolExecutor pour scanner en parallèle
            with ThreadPoolExecutor(max_workers=50) as executor:
                futures = {}
                
                for i in range(1, 255):
                    if not self.scanning:
                        break
                    
                    ip = f"{network_base}.{i}"
                    future = executor.submit(self.is_host_alive, ip)
                    futures[future] = ip
                
                # Collecter les résultats
                completed = 0
                for future in as_completed(futures):
                    if not self.scanning:
                        break
                    
                    ip = futures[future]
                    try:
                        if future.result():
                            alive_hosts.append(ip)
                            self.update_status(f"Trouvé: {ip}")
                    except:
                        pass
                    
                    completed += 1
                    progress = (completed / 254) * 100
                    self.update_progress(progress)
            
            if not self.scanning:
                self.update_status("Scan annulé")
                return
            
            # Obtenir les détails de chaque hôte vivant
            self.update_status("Collecte des informations...")
            
            for ip in alive_hosts:
                if not self.scanning:
                    break
                
                hostname = self.get_hostname(ip)
                mac = self.get_mac_address(ip)
                vendor = self.get_vendor_from_mac(mac)
                
                device_info = {
                    'ip': ip,
                    'mac': mac,
                    'hostname': hostname,
                    'vendor': vendor
                }
                self.devices.append(device_info)
            
            # Mettre à jour l'affichage
            self.update_device_list()
            self.update_device_count()
            self.update_status(f"Scan terminé: {len(self.devices)} appareils trouvés")
            self.update_progress(100)
            
            # Rescanner après 30 secondes si toujours actif
            if self.scanning:
                time.sleep(30)
                if self.scanning:
                    self.scan_network()
            else:
                self.scan_button.config(text="▶ DÉMARRER SCAN", bg='#003300')
            
        except Exception as e:
            self.update_status(f"Erreur: {str(e)}")
            self.scanning = False
            self.scan_button.config(text="▶ DÉMARRER SCAN", bg='#003300')
    
    def update_device_list(self):
        """Met à jour la liste des appareils dans l'interface"""
        def update():
            self.device_list.config(state=tk.NORMAL)
            self.device_list.delete(1.0, tk.END)
            
            if not self.devices:
                self.device_list.insert(tk.END, "\n  Aucun appareil détecté.\n\n  Lancez un scan pour détecter\n  les appareils sur votre réseau.\n")
            else:
                for i, device in enumerate(self.devices, 1):
                    icon = self.get_device_icon(device)
                    device_text = f"\n{icon} APPAREIL #{i}\n"
                    device_text += f"{'═' * 35}\n"
                    device_text += f"IP:       {device['ip']}\n"
                    device_text += f"MAC:      {device['mac']}\n"
                    device_text += f"Nom:      {device['hostname']}\n"
                    device_text += f"Vendor:   {device['vendor']}\n"
                    device_text += f"{'═' * 35}\n"
                    
                    self.device_list.insert(tk.END, device_text)
            
            self.device_list.config(state=tk.DISABLED)
        
        self.root.after(0, update)
    
    def update_device_count(self):
        """Met à jour le compteur d'appareils"""
        def update():
            self.device_count_label.config(text=f"Appareils: {len(self.devices)}")
        self.root.after(0, update)
    
    def update_status(self, message):
        """Met à jour le label de status"""
        def update():
            self.status_label.config(text=f"Status: {message}")
        self.root.after(0, update)
    
    def update_progress(self, value):
        """Met à jour la barre de progression"""
        def update():
            self.progress_bar['value'] = value
        self.root.after(0, update)

def main():
    """Point d'entrée principal"""
    print("=" * 60)
    print("  WiFi Radar Scanner v2.0")
    print("  Interface radar style sonar")
    print("=" * 60)
    print()
    
    os_type = platform.system()
    print(f"Système détecté: {os_type}")
    
    if os_type == "Windows":
        print("✓ Version Windows - Compatible")
    elif os_type == "Linux":
        print("✓ Version Linux - Compatible")
    elif os_type == "Darwin":
        print("✓ Version macOS - Compatible")
    
    print()
    print("Lancement de l'interface...")
    print()
    
    root = tk.Tk()
    app = WifiRadarScanner(root)
    
    # Message de bienvenue
    app.device_list.config(state=tk.NORMAL)
    app.device_list.insert(tk.END, "\n  ╔═══════════════════════════════╗\n")
    app.device_list.insert(tk.END, "  ║  WiFi Radar Scanner v2.0  ║\n")
    app.device_list.insert(tk.END, "  ╚═══════════════════════════════╝\n\n")
    app.device_list.insert(tk.END, "  Cliquez sur 'DÉMARRER SCAN'\n")
    app.device_list.insert(tk.END, "  pour commencer la détection\n")
    app.device_list.insert(tk.END, "  des appareils sur votre réseau.\n\n")
    app.device_list.insert(tk.END, "  Le scan peut prendre 1-2 minutes.\n")
    app.device_list.config(state=tk.DISABLED)
    
    root.mainloop()

if __name__ == "__main__":
    main()