from flask import Flask, render_template, jsonify
import subprocess
import socket
import netifaces
import threading
import time
from router import router_bp
from mikrotik import mikrotik_bp

app = Flask(__name__)
app.config['NETWORK_CONNECTED'] = True

# Diccionarios globales para almacenar el estado de IPs e interfaces
ip_states = {}
interface_states = {}

def get_link_speed(iface):
    try:
        output = subprocess.check_output(['ethtool', iface], stderr=subprocess.DEVNULL).decode()
        for line in output.split('\n'):
            if 'Speed:' in line:
                return line.split(':')[1].strip()
        return ""
    except subprocess.CalledProcessError:
        return ""

def get_interface_info():
    interfaces = {}
    iface_list = [iface for iface in netifaces.interfaces() if not iface.startswith('w') and iface != 'lo']
    
    for iface in iface_list:
        try:
            output = subprocess.check_output(['ip', 'addr', 'show', 'dev', iface]).decode()
            is_up = 'state UP' in output
            link_speed = get_link_speed(iface) if is_up else ""
            is_damaged = link_speed == '10Mb/s'
            interfaces[iface] = {'ips': [], 'link_speed': link_speed, 'is_up': is_up, 'is_damaged': is_damaged}
            
            for line in output.split('\n'):
                if 'inet ' in line:
                    parts = line.split()
                    ip = parts[1].split('/')[0]
                    is_dhcp = 'dynamic' in ' '.join(parts[2:])
                    netmask = parts[1].split('/')[1]
                    gateway = get_gateway(ip)
                    is_active, response_time = ping_gateway(gateway)
                    
                    if is_active:
                        interfaces[iface]['ips'].append({
                            'ip': ip,
                            'netmask': netmask,
                            'is_dhcp': is_dhcp,
                            'gateway': gateway,
                            'is_active': is_active,
                            'response_time': response_time
                        })
                        
                        ip_states[ip] = {
                            'active': is_active,
                            'response_time': response_time,
                            'interface': iface,
                            'is_dhcp': is_dhcp
                        }
            
            interface_states[iface] = {'active': is_up, 'link_speed': link_speed, 'is_damaged': is_damaged}
        except subprocess.CalledProcessError:
            # La interfaz puede no estar disponible
            interface_states[iface] = {'active': False, 'link_speed': "", 'is_damaged': False}
    
    return interfaces

def get_gateway(ip):
    parts = ip.split('.')
    parts[-1] = '1'
    return '.'.join(parts)

def ping_gateway(gateway):
    try:
        output = subprocess.check_output(['ping', '-c', '1', '-W', '1', gateway], stderr=subprocess.STDOUT, universal_newlines=True)
        for line in output.split('\n'):
            if 'time=' in line:
                time_ms = float(line.split('time=')[1].split()[0])
                return True, time_ms
        return False, None
    except subprocess.CalledProcessError:
        return False, None

def ping_specific_ip(ip):
    try:
        output = subprocess.check_output(['ping', '-c', '1', '-W', '1', ip], stderr=subprocess.STDOUT, universal_newlines=True)
        for line in output.split('\n'):
            if 'time=' in line:
                time_ms = float(line.split('time=')[1].split()[0])
                return True, time_ms
        return False, None
    except subprocess.CalledProcessError:
        return False, None

def update_network_info():
    while True:
        iface_list = [iface for iface in netifaces.interfaces() if not iface.startswith('w') and iface != 'lo']
        network_connected = True
        
        for iface in iface_list:
            try:
                output = subprocess.check_output(['ip', 'addr', 'show', 'dev', iface]).decode()
                is_up = 'state UP' in output
                link_speed = get_link_speed(iface) if is_up else ""
                is_damaged = link_speed == '10Mb/s'
                
                interface_states[iface] = {
                    'active': is_up,
                    'link_speed': link_speed,
                    'is_damaged': is_damaged
                }
                
                if not is_up or link_speed == "":
                    network_connected = False
                    break  # Si alguna interfaz está inactiva o sin velocidad de enlace, se considera que la red está desconectada
                
                if is_up:
                    for line in output.split('\n'):
                        if 'inet ' in line:
                            parts = line.split()
                            ip = parts[1].split('/')[0]
                            is_dhcp = 'dynamic' in ' '.join(parts[2:])
                            gateway = get_gateway(ip)
                            is_active, response_time = ping_gateway(gateway)
                            
                            if is_active:
                                ip_states[ip] = {
                                    'active': is_active,
                                    'response_time': response_time,
                                    'interface': iface,
                                    'is_dhcp': is_dhcp
                                }
                            elif ip in ip_states:
                                del ip_states[ip]
                else:
                    # Eliminar IPs asociadas a interfaces inactivas
                    for ip in list(ip_states.keys()):
                        if ip_states[ip]['interface'] == iface:
                            del ip_states[ip]
                            
            except subprocess.CalledProcessError:
                interface_states[iface] = {'active': False, 'link_speed': "", 'is_damaged': False}
                network_connected = False
        
        app.config['NETWORK_CONNECTED'] = network_connected
        time.sleep(5)

# Iniciar el hilo de actualización
update_thread = threading.Thread(target=update_network_info, daemon=True)
update_thread.start()

app.register_blueprint(router_bp, url_prefix='/router')
app.register_blueprint(mikrotik_bp, url_prefix='/mikrotik')

@app.route('/')
def index():
    hostname = socket.gethostname()
    interfaces = get_interface_info()
    any_link_damaged = any(state['is_damaged'] for state in interface_states.values())
    return render_template('index.html', hostname=hostname, interfaces=interfaces, network_connected=app.config['NETWORK_CONNECTED'], any_link_damaged=any_link_damaged)

@app.route('/update_status')
def update_status():
    any_link_damaged = any(state['is_damaged'] for state in interface_states.values())
    ubiquiti_ping_time = None
    # Aquí, verifica si puedes hacer ping a 192.168.1.20 y actualiza ubiquiti_ping_time
    try:
        result = subprocess.run(['ping', '-c', '1', '-W', '1', '192.168.1.20'], capture_output=True, text=True)
        if result.returncode == 0:
            # Extrae el tiempo de ping de la salida
            time_ms = float(result.stdout.split('time=')[1].split()[0])
            ubiquiti_ping_time = time_ms
    except Exception as e:
        print(f"Error al hacer ping a Ubiquiti: {e}")

    return jsonify({
        'ip_states': ip_states,
        'interface_states': interface_states,
        'network_connected': app.config['NETWORK_CONNECTED'],
        'any_link_damaged': any_link_damaged,
        'ubiquiti_ping_time': ubiquiti_ping_time
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
