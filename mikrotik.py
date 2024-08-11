from flask import Blueprint, render_template, current_app, jsonify, request
import paramiko
import time
import json
import os
from datetime import datetime
import subprocess

mikrotik_bp = Blueprint('mikrotik', __name__, url_prefix='/mikrotik')

# Configuración del dispositivo MikroTik
HOSTNAME = '192.168.88.1'
USUARIOS_CONTRASENAS = [
    ('admin', ''),
    ('admin', 'agwist2017'),
    ('admin', '-Agwist1.'),
    ('admin', 'Agwist1.'),
    ('admin', 'admin')
]
SHORT_DURATION = 0.1  # Duración corta en segundos
NORMAL_DURATION = 5  # Duración normal en segundos

ssh_client = None
interfaz_wireless = None

nueva_contrasena = 'agwist2017' # Contraseña nueva para el usuario 'admin'
nuevo_usuario = 'invitado'
contrasena_invitado = 'invitado'
grupo_lectura = 'read'  # Asumimos que 'read' es el grupo con permisos de solo lectura


def exec_command(command):
    global ssh_client
    if ssh_client and ssh_client.get_transport() and ssh_client.get_transport().is_active():
        stdin, stdout, stderr = ssh_client.exec_command(command)
        output = stdout.read().decode()
        error = stderr.read().decode()
        return output, error
    else:
        return None, "No hay conexión activa"

def connect_to_mikrotik():
    global ssh_client, interfaz_wireless
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    for username, password in USUARIOS_CONTRASENAS:
        try:
            ssh_client.connect(HOSTNAME, username=username, password=password, allow_agent=False, look_for_keys=False)
            # Cambiar la contraseña si es vacía
            if password == '':
                print(f"Cambiando contraseña para el usuario {username}...")
                change_password_command = f'/user set {username} password={nueva_contrasena}'
                exec_command(change_password_command)
                print(f"Contraseña para el usuario {username} cambiada a {nueva_contrasena}")
                print("=======")
            interfaz_wireless = obtener_primera_interfaz_wireless()
            if interfaz_wireless:
                habilitar_interfaz_wireless()
            return True, None
        except paramiko.AuthenticationException:
            continue
        except Exception as e:
            return False, str(e)
    
    return False, "No se pudo autenticar con ninguna credencial"

def obtener_primera_interfaz_wireless():
    output, error = exec_command("/interface wireless print without-paging")
    if error:
        return None
    
    for line in output.split('\n'):
        if line.strip().split() and line.strip().split()[0].isdigit():
            parts = line.strip().split()
            interface_name = next((part.split('=')[1].strip('"') for part in parts if part.startswith('name=')), None)
            if interface_name:
                return interface_name
    
    return None

def habilitar_interfaz_wireless():
    global interfaz_wireless
    if interfaz_wireless:
        exec_command(f"/interface wireless enable {interfaz_wireless}")

def escanear_redes(duration=10):
    global interfaz_wireless
    if not interfaz_wireless:
        return [], "No se ha establecido la interfaz inalámbrica"
    print(f"Escanenado redes en la interfaz {interfaz_wireless} con duración {duration} segundos")
    scan_command = f"/interface wireless scan {interfaz_wireless} duration={duration} save-file=scan1"
    exec_command(scan_command)
    
    time.sleep(duration + 1)  # Esperar un poco más que la duración del escaneo
    
    results_command = ":put [/file get scan1 contents]"
    output, _ = exec_command(results_command)
    
    exec_command("/file remove scan1")
    
    return parse_scan_results(output.strip()), None

def parse_scan_results(scan_output):
    redes = []
    for line in scan_output.split('\n'):
        parts = line.strip().split(',')
        if len(parts) >= 4:
            redes.append({
                'mac': parts[0],
                'ssid': parts[1].strip("'"),
                'frequency': parts[2].split('/')[0],
                'signal': int(parts[3])
            })
    return redes

def leer_frecuencias_json(archivo):
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(script_dir, archivo)
        
        with open(json_path, 'r') as f:
            data = json.load(f)
        print(f"Frecuencias cargadas: {data}")  # Para depuración
        return data
    except FileNotFoundError:
        print(f"Error: No se pudo encontrar el archivo '{archivo}'.")
        return []
    except json.JSONDecodeError:
        print(f"Error: El archivo '{archivo}' no es un JSON válido.")
        return []

def eliminar_nat_content():
    print("Eliminando reglas de NAT con contenido útil...")
    while True:
        output, _ = exec_command("/ip firewall nat print")
        if '0  ' not in output:
            break
        exec_command("/ip firewall nat remove 0")
    print("Reglas de NAT con contenido útil eliminadas.")

def eliminar_dhcp_client():
    print("Eliminando clientes DHCP...")
    while True:
        output, _ = exec_command("/ip dhcp-client print")
        lines = output.strip().split('\n')
        client_ids = [line.split()[0] for line in lines if line.strip() and line.split()[0].isdigit()]
        if not client_ids:
            break
        for client_id in client_ids:
            exec_command(f"/ip dhcp-client remove numbers={client_id}")
    print("Clientes DHCP eliminados.")

def eliminar_default_route():
    print("Eliminando rutas por defecto existentes...")
    while True:
        output, _ = exec_command("/ip route print")
        lines = output.strip().split('\n')
        route_ids = [line.split()[0] for line in lines if '0.0.0.0/0' in line]
        if not route_ids:
            break
        for route_id in route_ids:
            exec_command(f"/ip route remove numbers={route_id}")
    print("Rutas por defecto eliminadas.")

def verificar_soporte_ac():
    command = ":local iface [/interface wireless find]; :if ([:len $iface] > 0) do={:set iface [:pick $iface 0]; :local name [/interface wireless get $iface name]; :local band [/interface wireless get $iface band]; :put (\"Interface: \" . $name . \" - Band: \" . $band . \" - Supports AC: \" . ($band = \"5ghz-n/ac\"))}"
    output, _ = exec_command(command)
    return "Supports AC: true" in output

def configurar_mikrotik(frecuencias):
    global interfaz_wireless
    if not frecuencias:
        print("No se cargaron frecuencias del archivo JSON. Abortando configuración inalámbrica.")
        return
    # Habilitar Romon
    exec_command("/tool romon set enabled=yes")
    print("Romon habilitado.")

    # Comando a ejecutar para remover reglas de firewall
    command = '/ip firewall filter remove [find chain=input action=drop connection-state!=invalid]'
    exec_command(command)

    # Crear un usuario "invitado" con permisos de solo lectura
    print(f"Creando usuario {nuevo_usuario} con permisos de solo lectura...")
    create_user_command = f'/user add name={nuevo_usuario} group={grupo_lectura} password={contrasena_invitado}'
    exec_command(create_user_command)
    print(f"Usuario {nuevo_usuario} creado con éxito con permisos de solo lectura y contraseña {contrasena_invitado}")
    print("=======")

    # Crear un script en Mikrotik para actualizar el identity con la velocidad de enlace de ether1 cada minuto
    print("Creando script de actualización del identity en MikroTik...")
    create_script_command = """/system script remove [find name="UpdateIdentity"];/system script add name=UpdateIdentity source=":local etherMonitorResult [/interface ethernet monitor ether1 once as-value];:local rateValue [:pick [:toarray (\$etherMonitorResult->\\\"rate\\\")] 0];:local currentIdentity [/system identity get name];:local simplifiedRate;:if (\$rateValue = \\\"10Mbps\\\") do={ :set simplifiedRate \\\"10\\\" };:if (\$rateValue = \\\"100Mbps\\\") do={ :set simplifiedRate \\\"100\\\" };:if (\$rateValue = \\\"1Gbps\\\") do={ :set simplifiedRate \\\"1000\\\" };:local cleanIdentity;:if ([:find \$currentIdentity \\\"/\\\"] >= 0) do={ :set cleanIdentity [:pick \$currentIdentity ([:find \$currentIdentity \\\"/\\\"] + 1) [:len \$currentIdentity]] } else={ :set cleanIdentity \$currentIdentity };:local newIdentity (\$simplifiedRate . \\\"/\\\" . \$cleanIdentity);/system identity set name=\$newIdentity;:log info (\\\"Nuevo identity configurado: \\\" . \$newIdentity);" """
    exec_command(create_script_command)
    print("Script de actualización del identity creado.")
    print("=======")

    # Crear la tarea programada para ejecutar el script cada minuto
    print("Creando tarea programada para ejecutar el script cada minuto...")
    create_scheduler_command = """/system scheduler remove [find name="RunUpdateIdentity"];/system scheduler add name=RunUpdateIdentity on-event=UpdateIdentity interval=1m"""
    exec_command(create_scheduler_command)
    print("Tarea programada creada.")
    print("=======")


    # Set Dns Server
    exec_command("/ip dns set servers=8.8.8.8,8.8.4.4")
    print("Servidor DNS habilitado.")

    # Eliminar reglas de NAT con contenido útil
    eliminar_nat_content()

    # Eliminar clientes DHCP
    eliminar_dhcp_client()

    # Agregar regla de NAT para permitir tráfico de la interfaz inalámbrica
    exec_command(f"/ip firewall nat add chain=srcnat out-interface={interfaz_wireless} action=masquerade")

    # Agregar regla de NAT para hacer dstnat hacia el router escuhando en el puerto 8080 en la ip 192.168.88.100
    exec_command("ip firewall nat add action=dst-nat chain=dstnat dst-port=8080 protocol=tcp to-addresses=192.168.88.100 to-ports=8080")

    # Agregar IP address a la interfaz inalámbrica
    exec_command("/ip address add address=192.168.111.222/24 interface={interfaz_wireless}")

    # Eliminar rutas por defecto
    eliminar_default_route()
    
    # Agregar default route
    exec_command("/ip route add gateway=192.168.111.1")

    soporta_ac = verificar_soporte_ac()
    banda = "5ghz-a/n-ac" if soporta_ac else "5ghz-a/n"
    print(f"El dispositivo {'soporta' if soporta_ac else 'no soporta'} AC. Usando banda: {banda}")

    # Extraer frecuencias numéricas y configurar "Scan List"
    frecuencias_numericas = ','.join(str(freq['frecuencia']) for freq in frecuencias)
    config_general = f"/interface wireless set {interfaz_wireless} mode=station-bridge band={banda} channel-width=20mhz radio-name=[/system identity get name] wireless-protocol=nv2 frequency-mode=superchannel country=etsi2 scan-list={frecuencias_numericas}"
    exec_command(config_general)
    print(f"Configuración general de la interfaz inalámbrica aplicada con scan-list: {frecuencias_numericas}")

def obtener_clave_nv2_desde_json (ssid):
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(script_dir, 'wireless_config.json')
        
        with open(json_path, 'r') as f:
            data = json.load(f)
        for red in data:
            if red['ssid'] == ssid:
                return red['claveNv2']
    except FileNotFoundError:
        print(f"Error: No se pudo encontrar el archivo 'wireless_config.json'.")
        return []
    except json.JSONDecodeError:
        print(f"Error: El archivo 'wireless_config.json' no es un JSON válido.")
        return []
    


def ping(host):
    try:
        output = subprocess.check_output(['ping', '-c', '1', '-W', '1', host], universal_newlines=True)
        for line in output.split('\n'):
            if 'time=' in line:
                print(f"host:{host}  Respuesta de ping: {line}  return: {float(line.split('time=')[1].split()[0])}")
                return float(line.split('time=')[1].split()[0])
    except subprocess.CalledProcessError:
        return print(f"host:{host}  Respuesta de ping: 0")
@mikrotik_bp.route('/')
def mikrotik_page():
    network_connected = current_app.config.get('NETWORK_CONNECTED', False)
    return render_template('mikrotik.html', network_connected=network_connected)

@mikrotik_bp.route('/connect', methods=['POST'])
def connect():
    success, error = connect_to_mikrotik()
    if success:
        frecuencias = leer_frecuencias_json('wireless_config.json')
        if frecuencias:
            configurar_mikrotik(frecuencias)
        else:
            return jsonify({'status': 'error', 'message': 'No se pudo configurar la interfaz inalámbrica debido a problemas con el archivo de frecuencias.'})
        return jsonify({
            'status': 'success', 
            'message': 'Conexión establecida con éxito. Interfaz inalámbrica habilitada.',
            'interface': interfaz_wireless
        })
    else:
        return jsonify({'status': 'error', 'message': f'Error de conexión: {error}'})

@mikrotik_bp.route('/scan_networks', methods=['POST'])
def scan_networks():
    start_time = datetime.now()
    print(f"Iniciando escaneo a las {start_time.strftime('%H:%M:%S.%f')[:-3]}")
    
    data = request.json
    connected = data.get('connected', False)
    duration = SHORT_DURATION if connected else NORMAL_DURATION
    
    print(f"Duración del escaneo: {duration} segundos")
    redes, error = escanear_redes(duration)
    
    end_time = datetime.now()
    print(f"Escaneo completado a las {end_time.strftime('%H:%M:%S.%f')[:-3]}")
    print(f"Redes encontradas: {len(redes)}")
    
    if error:
        return jsonify({'status': 'error', 'message': error})
    return jsonify({'status': 'success', 'redes': redes})

@mikrotik_bp.route('/get_connection_info', methods=['POST'])
def get_connection_info():
    global interfaz_wireless
    try:
        command = f"/interface wireless registration-table print"
        output, error = exec_command(command)
        if error:
            return jsonify({'status': 'error', 'message': f'Error al obtener información: {error}'})
        
        lines = output.strip().split('\n')
        if len(lines) > 1:  # Asumiendo que la primera línea es el encabezado
            # Eliminar espacios múltiples y dividir la línea
            parts = ' '.join(lines[1].split()).split()
            
            # Inicializar un diccionario con valores por defecto
            info = {
                'index': 'N/A',
                'interface': 'N/A',
                'radio_name': 'N/A',
                'mac_address': 'N/A',
                'ap': 'N/A',
                'signal_strength': 'N/A',
                'tx_rate': 'N/A',
                'uptime': 'N/A'
            }
            
            # Asignar valores solo si existen
            if len(parts) > 0: info['index'] = parts[0]
            if len(parts) > 1: info['interface'] = parts[1]
            if len(parts) > 5: 
                info['radio_name'] = ' '.join(parts[2:-4])
                info['mac_address'] = parts[-4]
                info['ap'] = parts[-3]
                info['signal_strength'] = parts[-2]
                if len(parts[-1].split()) == 2:
                    info['tx_rate'], info['uptime'] = parts[-1].split()
                else:
                    info['tx_rate'] = parts[-1]
            
            return jsonify({'status': 'success', 'info': info})
        info = {
            'index': 'N/A',
            'interface': 'N/A',
            'radio_name': 'N/A',
            'mac_address': 'N/A',
            'ap': 'N/A',
            'signal_strength': 'N/A',
            'tx_rate': 'N/A',
            'uptime': 'N/A'
        }    
        return jsonify({'status': 'error', 'message': 'No se encontró información de conexión', 'info': info})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error: {str(e)}'})

@mikrotik_bp.route('/connect_wireless', methods=['POST'])
def connect_wireless():
    global interfaz_wireless
    data = request.json
    red_seleccionada = data.get('red_seleccionada')
    clave=obtener_clave_nv2_desde_json(red_seleccionada['ssid'])
    if clave:
        nv2Security = "nv2-security=enabled"
        nv2PreSharedKey = f"nv2-preshared-key=\"{clave}\""
    else:
        nv2Security = "nv2-security=disabled"
        nv2PreSharedKey = "nv2-preshared-key=\"\""
    if not red_seleccionada:
        return jsonify({'status': 'error', 'message': 'No se seleccionó ninguna red'})

    try:
        config_command = f"/interface wireless set {interfaz_wireless} ssid=\"{red_seleccionada['ssid']}\" frequency={red_seleccionada['frequency']} {nv2PreSharedKey}  {nv2Security} "
        print (f"-------------------------------------------------------------------config_command: {config_command}")
        exec_command(config_command)
        return jsonify({'status': 'success', 'message': 'Conexión establecida con éxito'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error al conectar: {str(e)}'})


@mikrotik_bp.route('/disconnect_wireless', methods=['POST'])
def disconnect_wireless():
    global interfaz_wireless
    try:
        # Simplemente reseteamos el SSID de la interfaz
        reset_command = f"/interface wireless set {interfaz_wireless} ssid=\"\""
        exec_command(reset_command)
        return jsonify({'status': 'success', 'message': 'Desconectado de la red inalámbrica'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error al desconectar: {str(e)}'})

@mikrotik_bp.route('/apply_network_config', methods=['POST'])
def apply_network_config():
    data = request.json
    interface = data.get('interface')
    ip = data.get('ip')
    netmask = data.get('netmask')
    gateway = data.get('gateway')

    try:
        #Eliminar las direcciones ip existentes para la interfaz wireless
        exec_command(f"/ip address remove [find interface={interface}]")
        # Comando para configurar la IP y la máscara de red
        ip_command = f"/ip address add address={ip}/{netmask} interface={interface}"
        exec_command(ip_command)
        # Eliminar rutas por defecto existentes
        eliminar_default_route()
        # Comando para configurar el gateway
        gateway_command = f"/ip route add gateway={gateway}"
        exec_command(gateway_command)

        return jsonify({'status': 'success', 'message': 'Configuración aplicada con éxito'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@mikrotik_bp.route('/get_network_info', methods=['GET'])
def get_network_info():
    try:
        interface = obtener_primera_interfaz_wireless()
        ip_info, _ = exec_command(f':local ip [/ip address get [find interface="{interface}"] address ]; :put "$ip"')
        gateway_info, _ = exec_command(':local route [/ip route get [find dst-address="0.0.0.0/0"] gateway ]; :put "$route"')
        # Parsear la información del gateway  
        gateway = gateway_info.strip()
        
        
        # Parsear la información de IP y máscara
        ip = None
        netmask = None
        if ip_info:
            ip_address = ip_info.strip()
            ip, netmask = ip_address.split('/')
        print(f"ip: {ip}  netmask: {netmask}   gateway: {gateway}")

        return jsonify({
            'status': 'success',
            'interface': interface,
            'ip': ip,
            'netmask': "255.255.255.0",
            'gateway': gateway
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@mikrotik_bp.route('/get_ping_times', methods=['GET'])
def get_ping_times():
    try:
        # Obtener el gateway de los parámetros de la URL
        gateway = request.args.get('gateway')  
        gateway_ping = ping(gateway)
        google_ping = ping("www.google.com")
        return jsonify({
            'status': 'success',
            'gateway': gateway,
            'gateway_ping':gateway_ping ,
            'google_ping':google_ping 
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
@mikrotik_bp.route('/update_status')


def update_status():
    network_connected = current_app.config.get('NETWORK_CONNECTED', False)
    return jsonify({
        'network_connected': network_connected
    })