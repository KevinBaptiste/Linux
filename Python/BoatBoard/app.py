#!/usr/bin/env python3
"""
Network Monitor Dashboard - Backend Server (Version Améliorée)
Tableau de bord de monitoring réseau avec interface cyber-futuriste
"""

from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
import psutil
import subprocess
import threading
import time
import re
import json
import os
import logging
from datetime import datetime, timedelta
import socket
from collections import deque
from typing import Dict, List, Optional

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration via variables d'environnement
class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'network_monitor_secret_key')
    UPDATE_INTERVAL = int(os.getenv('UPDATE_INTERVAL', '2'))
    SCAN_INTERVAL = int(os.getenv('SCAN_INTERVAL', '10'))
    SPEEDTEST_INTERVAL = int(os.getenv('SPEEDTEST_INTERVAL', '300'))
    MAX_LOGS = int(os.getenv('MAX_LOGS', '50'))
    ENABLE_SPEEDTEST = os.getenv('ENABLE_SPEEDTEST', 'true').lower() == 'true'
    PORT = int(os.getenv('PORT', '5000'))

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Variables globales
network_data = {
    'devices': [],
    'speedtest': {'download': 0, 'upload': 0, 'ping': 0, 'last_update': 'Jamais'},
    'cpu': 0,
    'ram': 0,
    'disk': 0,
    'network_io': {'sent': 0, 'recv': 0},
    'server_ip': '',
    'hostname': '',
    'running_services': [],
    'logs': []
}

_cache = {
    'last_speedtest': None,
    'speedtest_data': None,
    'devices_scan_running': False,
    'last_network_io': None
}

def get_server_info() -> Dict[str, str]:
    """Récupère les informations du serveur"""
    info = {'ip': 'Indisponible', 'hostname': 'Indisponible'}
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        s.connect(("8.8.8.8", 80))
        info['ip'] = s.getsockname()[0]
        s.close()
    except:
        try:
            result = subprocess.run(['hostname', '-I'], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                ips = result.stdout.strip().split()
                if ips:
                    info['ip'] = ips[0]
        except:
            pass
    
    try:
        info['hostname'] = socket.gethostname()
    except:
        pass
    
    return info

def detect_device_type(mac: str, vendor: str = '') -> str:
    """Détecte le type d'appareil"""
    mac_upper = mac.upper()
    vendor_lower = vendor.lower()
    
    if vendor_lower:
        if any(x in vendor_lower for x in ['apple', 'iphone', 'samsung', 'huawei', 'xiaomi']):
            return 'mobile'
        elif 'raspberry' in vendor_lower:
            return 'raspberry'
        elif any(x in vendor_lower for x in ['synology', 'qnap', 'netgear']):
            return 'nas'
        elif any(x in vendor_lower for x in ['vmware', 'virtualbox']):
            return 'vm'
    
    mac_prefixes = {
        'vm': ['00:50:56', '00:0C:29', '00:05:69', '08:00:27', '52:54:00'],
        'raspberry': ['B8:27:EB', 'DC:A6:32', 'E4:5F:01', 'D8:3A:DD', '28:CD:C1'],
        'mobile': ['AC:DE:48', '00:11:32', '5C:CF:7F', '54:E4:BD', '00:1F:5B'],
        'nas': ['00:11:32', '00:08:9B', '00:1B:63'],
    }
    
    for device_type, prefixes in mac_prefixes.items():
        if any(mac_upper.startswith(p) for p in prefixes):
            return device_type
    
    return 'computer'

def get_hostname_safe(ip: str) -> str:
    """Récupère le hostname"""
    try:
        return socket.gethostbyaddr(ip)[0]
    except:
        return ip

def get_network_devices() -> List[Dict]:
    """Scanne le réseau"""
    if _cache['devices_scan_running']:
        return network_data.get('devices', [])
    
    _cache['devices_scan_running'] = True
    devices = []
    
    try:
        try:
            result = subprocess.run(['arp-scan', '--localnet', '--retry=3'], 
                                  capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    match = re.search(r'([0-9.]+)\s+([0-9a-f:]+)\s+(.*)', line, re.IGNORECASE)
                    if match:
                        ip, mac, vendor = match.groups()
                        devices.append({
                            'ip': ip,
                            'mac': mac.lower(),
                            'vendor': vendor.strip(),
                            'type': detect_device_type(mac, vendor),
                            'hostname': get_hostname_safe(ip)
                        })
                if devices:
                    logger.info(f"arp-scan: {len(devices)} appareils")
                    _cache['devices_scan_running'] = False
                    return devices
        except:
            pass
        
        result = subprocess.run(['arp', '-a'], capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                match = re.search(r'\(([0-9.]+)\)\s+at\s+([0-9a-f:]+)', line, re.IGNORECASE)
                if match:
                    ip, mac = match.groups()
                    mac = mac.lower()
                    if mac != '(incomplete)' and not any(d['mac'] == mac for d in devices):
                        devices.append({
                            'ip': ip,
                            'mac': mac,
                            'vendor': '',
                            'type': detect_device_type(mac),
                            'hostname': get_hostname_safe(ip)
                        })
            logger.info(f"arp: {len(devices)} appareils")
    
    except Exception as e:
        logger.error(f"Erreur scan: {e}")
    finally:
        _cache['devices_scan_running'] = False
    
    return devices

def run_speedtest() -> Dict:
    """Speedtest avec cache"""
    now = datetime.now()
    if _cache['last_speedtest'] and _cache['speedtest_data']:
        if (now - _cache['last_speedtest']).total_seconds() < Config.SPEEDTEST_INTERVAL:
            return _cache['speedtest_data']
    
    if not Config.ENABLE_SPEEDTEST:
        return {'download': 0, 'upload': 0, 'ping': 0}
    
    try:
        logger.info("Speedtest...")
        result = subprocess.run(['speedtest-cli', '--simple'], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            data = {}
            for line in result.stdout.strip().split('\n'):
                if 'Ping:' in line:
                    data['ping'] = float(re.search(r'[\d.]+', line).group())
                elif 'Download:' in line:
                    data['download'] = float(re.search(r'[\d.]+', line).group())
                elif 'Upload:' in line:
                    data['upload'] = float(re.search(r'[\d.]+', line).group())
            
            result_data = {
                'download': round(data.get('download', 0), 2),
                'upload': round(data.get('upload', 0), 2),
                'ping': round(data.get('ping', 0), 2)
            }
            
            _cache['last_speedtest'] = now
            _cache['speedtest_data'] = result_data
            logger.info(f"Speedtest: ↓{result_data['download']} ↑{result_data['upload']} Mbps")
            return result_data
    except Exception as e:
        logger.error(f"Erreur speedtest: {e}")
    
    return {'download': 0, 'upload': 0, 'ping': 0}

def get_system_resources() -> Dict:
    """Ressources système"""
    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        net_io = psutil.net_io_counters()
        
        network_speed = {'sent': 0, 'recv': 0}
        if _cache['last_network_io']:
            sent_diff = net_io.bytes_sent - _cache['last_network_io'].bytes_sent
            recv_diff = net_io.bytes_recv - _cache['last_network_io'].bytes_recv
            network_speed['sent'] = round((sent_diff * 8) / 2_000_000, 2)
            network_speed['recv'] = round((recv_diff * 8) / 2_000_000, 2)
        
        _cache['last_network_io'] = net_io
        
        return {'cpu': cpu, 'ram': ram, 'disk': disk, 'network_io': network_speed}
    except Exception as e:
        logger.error(f"Erreur ressources: {e}")
        return {'cpu': 0, 'ram': 0, 'disk': 0, 'network_io': {'sent': 0, 'recv': 0}}

def get_running_services() -> List[str]:
    """Services actifs"""
    services = []
    try:
        result = subprocess.run(['systemctl', 'list-units', '--type=service', '--state=running', 
                               '--no-pager', '--no-legend'],
                              capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            for line in result.stdout.split('\n')[:20]:
                match = re.search(r'^\s*(\S+\.service)', line)
                if match:
                    services.append(match.group(1).replace('.service', ''))
    except Exception as e:
        logger.error(f"Erreur services: {e}")
    
    return services

def get_journalctl_logs(lines: int = 50) -> List[str]:
    """Logs journalctl"""
    logs = []
    try:
        result = subprocess.run(['journalctl', '-n', str(lines), '--no-pager', '-o', 'short-iso'],
                              capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            logs = [line for line in result.stdout.split('\n') if line.strip()]
    except Exception as e:
        logger.error(f"Erreur logs: {e}")
    
    return logs[-Config.MAX_LOGS:]

def update_network_data():
    """Thread de mise à jour"""
    global network_data
    update_counter = 0
    
    server_info = get_server_info()
    network_data['server_ip'] = server_info['ip']
    network_data['hostname'] = server_info['hostname']
    
    while True:
        try:
            resources = get_system_resources()
            network_data.update(resources)
            network_data['logs'] = get_journalctl_logs()
            
            if update_counter % 5 == 0:
                network_data['devices'] = get_network_devices()
                network_data['running_services'] = get_running_services()
            
            if update_counter % 150 == 0:
                speedtest_result = run_speedtest()
                speedtest_result['last_update'] = datetime.now().strftime('%H:%M:%S')
                network_data['speedtest'] = speedtest_result
            
            socketio.emit('update', network_data)
            
            update_counter = (update_counter + 1) % 1000
            time.sleep(Config.UPDATE_INTERVAL)
            
        except Exception as e:
            logger.error(f"Erreur update: {e}")
            time.sleep(5)

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/data')
def get_data():
    return jsonify(network_data)

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

@socketio.on('connect')
def handle_connect():
    logger.info('Client connecté')
    socketio.emit('update', network_data)

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client déconnecté')

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("Network Monitor Dashboard")
    logger.info("=" * 60)
    
    server_info = get_server_info()
    network_data['server_ip'] = server_info['ip']
    network_data['hostname'] = server_info['hostname']
    network_data['devices'] = get_network_devices()
    network_data['running_services'] = get_running_services()
    
    if Config.ENABLE_SPEEDTEST:
        logger.info("Speedtest initial...")
        speedtest_result = run_speedtest()
        speedtest_result['last_update'] = datetime.now().strftime('%H:%M:%S')
        network_data['speedtest'] = speedtest_result
    
    update_thread = threading.Thread(target=update_network_data, daemon=True)
    update_thread.start()
    
    logger.info(f"Serveur: http://0.0.0.0:{Config.PORT}")
    logger.info(f"IP: {server_info['ip']}")
    logger.info("=" * 60)
    
    socketio.run(app, host='0.0.0.0', port=Config.PORT, debug=False, allow_unsafe_werkzeug=True)