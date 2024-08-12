import subprocess
import re
from flask import Blueprint, render_template, current_app
<<<<<<< HEAD
from flask import request, jsonify

from time import sleep
import requests
from playwright.sync_api import sync_playwright
import logging
=======
import subprocess
from flask import request, jsonify
>>>>>>> b1d33405dc68a124f8072cde417a396a49c9e7d0

router_bp = Blueprint('router', __name__, url_prefix='/router')

# Configurar logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def check_router_state(playwright):
    logging.info("Iniciando verificación del estado del router")
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    page.goto('http://192.168.0.1/login.html')
    
    logging.info(f"URL actual: {page.url}")
    
    if 'quickset.html' in page.url:
        logging.info("Detectada versión 1.0.3 - Redirigido a quickset.html")
        handle_quickset_page(page)
        return "index", None, context
    elif page.url == 'http://192.168.0.1/index.html':
        logging.info("Redirigido a index.html - Se requiere crear una nueva contraseña")
        return "index", None, context
    elif page.url != 'http://192.168.0.1/login.html':
        logging.warning(f"Redireccionado a una página inesperada: {page.url}")
        browser.close()
        return "unknown", None, None
    
    logging.info("Página de login detectada")
    return "login", handle_login_page(page), context

def handle_quickset_page(page):
    logging.info("Manejando página de configuración rápida")
    page.click('input[id="dhcp"]')
    page.click('input[id="save"]')
    page.wait_for_load_state('networkidle')
    
    if 'success' in page.url.lower():
        logging.info("Configuración rápida exitosa")
        return page.context.cookies()
    else:
        logging.error("Error en la configuración rápida")
        return None

def handle_login_page(page):

    logging.info("Manejando página de login")
    passwords = ['admin', 'agwist2017']
    for password in passwords:
        logging.info(f"Ingresando contraseña: {password}")
        page.fill('input[id="login-password"]', password)
        page.click('button[id="save"]')
        page.wait_for_load_state('networkidle')

        if 'quickset.html' in page.url:
            logging.info("Detectada versión 1.0.3 - Redirigido a quickset.html")
            handle_quickset_page(page)

        try:
            page.wait_for_selector('#loginout', timeout=5000)
            logging.info("Login exitoso")
            return page.context.cookies()
        except:
            logging.error("Error al iniciar sesión")

    return None

def create_new_password(page):
    logging.info("Creando nueva contraseña en la página index.html")
    new_password = 'agwist2017'
    sleep(5)
    if page.query_selector('input[id="goSet"]'):
        logging.info("goSet, Página de configuración de contraseña detectada")
        page.click('input[id="goSet"]')
        page.wait_for_load_state('networkidle')
        logging.info(f"Nueva URL después de establecer contraseña: {page.url}")
    logging.info("Estableciendo nueva contraseña")
    sleep(5)
    page.fill('input[id="newPwd"]', new_password)
    page.fill('input[id="cfmPwd"]', new_password)
    
    logging.debug(f"Valor de newPwd: {page.input_value('input#newPwd')}")
    logging.debug(f"Valor de cfmPwd: {page.input_value('input#cfmPwd')}")
    
    page.click('button[id="submit"]')
    page.wait_for_load_state('networkidle')
    
    logging.info(f"Nueva URL después de establecer contraseña: {page.url}")
    
    

def make_post_request(context, cookies, endpoint_url, post_data):
    logging.info(f"Realizando solicitud POST a {endpoint_url}")
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept-Language': 'en-US,en;q=0.9',
        'Origin': 'null',
        'Upgrade-Insecure-Requests': '1'
    }

    if cookies:
        cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
        logging.debug(f"Usando cookies: {cookie_dict}")
        response = requests.post(endpoint_url, data=post_data, cookies=cookie_dict, headers=headers)
    else:
        logging.debug("No se están usando cookies para esta solicitud")
        response = requests.post(endpoint_url, data=post_data, headers=headers)
    
    logging.info(f"Respuesta del servidor: {response.text}")
    
    return cookies


def configure_tenda(wifi_name, wifi_password):
    logging.info("Iniciando el proceso de configuración del router")
    with sync_playwright() as playwright:
        state, cookies, context = check_router_state(playwright)

        if state == "unknown":
            logging.error("Estado del router desconocido. Abortando.")
            return

        try:
            if state == "index":
                logging.info("Se detectó la página index.html. Creando nueva contraseña.")
                page = context.pages[0]
                create_new_password(page)
                cookies = handle_login_page(page)

            # Configurar WiFi
            logging.info("Configurando WiFi")
            post_data_wifi = {
                'module1': 'wifiBasicCfg',
                'wifiSSID': wifi_name,
                'wifiPwd': wifi_password
            }
            cookies = make_post_request(context, cookies, 'http://192.168.0.1/goform/setWizard', post_data_wifi)

            # Configurar WAN
            logging.info("Configurando WAN")
            post_data_wan = {
                'module2': 'wanBasicCfg',
                'wanIP': '192.168.88.100',
                'wanMask': '255.255.255.0',
                'wanGateway': '192.168.88.1',
                'wanDns1': '8.8.8.8',
                'wanDns2': '8.8.4.4',
                'wanType': 'static'
            }
            cookies = make_post_request(context, cookies, 'http://192.168.0.1/goform/setWizard', post_data_wan)

            # Configurar herramienta remota
            logging.info("Configurando herramienta remota")
            post_data_remote = {
                'module4': 'remoteWeb',
                'remoteWebEn': 'true',
                'remoteWebType': 'any',
                'remoteWebIP': '',
                'remoteWebPort': '8080'
            }
            cookies = make_post_request(context, cookies, 'http://192.168.0.1/goform/setSysTools', post_data_remote)

            # Configurar Dhcp-Server
            logging.info("Configurando DNS en servidor DHCP")
            post_data_dhcp = {
                'module3': 'lanCfg',
                'lanIP': '192.168.0.1',
                'lanMask': '255.255.255.0',
                'dhcpEn': 'true',
                'lanDhcpStartIP': '192.168.0.100',
                'lanDhcpEndIP': '192.168.0.200',
                'lanDns1': '8.8.8.8',
                'lanDns2': '8.8.4.4'
            }
            cookies = make_post_request(context, cookies, 'http://192.168.0.1/goform/setSysTools', post_data_dhcp) 
            
            logging.info("Configurando Ping a Wan")
            post_data_ping_wan = {
                'module6': 'ping',
                'pingEn': 'true'
            }
            cookies = make_post_request(context, cookies, 'http://192.168.0.1/goform/setNAT', post_data_ping_wan) 


            logging.info("Proceso de configuración completado")
            return {'success': True, 'message': 'Configuración exitosa de router Tenda'}
        

        except Exception as e:
            logging.error(f"Error al configurar el router: {e}")
            return {'success': False, 'message': f"Error al configurar el router"}
        
        finally:
            if context:
                logging.info("Cerrando el contexto del navegador")
                try:
                    context.close()
                except Exception as e:
                    logging.error(f"Error al cerrar el contexto del navegador: {e}")
                    return {'success': False, 'message': f"Error al cerrar el contexto del navegador"}








@router_bp.route('/<brand>')
def router_page(brand):
    network_connected = current_app.config['NETWORK_CONNECTED']
    return render_template('router.html', brand=brand, network_connected=network_connected)



@router_bp.route('/tenda/update_wifi', methods=['POST'])
def update_tenda_wifi():
    data = request.json
    wifi_name = data.get('wifi_name')
    wifi_password = data.get('wifi_password')

<<<<<<< HEAD
    try:
        response=configure_tenda(wifi_name, wifi_password)
        success = response['success']
        message = response['message']
        return jsonify({
            'success': success,
            'message': message
        })
    
    except Exception as e:
        success = False
        message = f"Ocurrió un error inesperado: {str(e)}"
        return jsonify({
            'success': success,
            'message': message
        })


@router_bp.route('/ping/<ip_address>')
def ping_router(ip_address):
    try:
        output = subprocess.check_output(['ping', '-c', '1', '-W', '1', ip_address], universal_newlines=True)
        match = re.search(r'time=(\d+\.?\d*)', output)
        if match:
            ping_time = float(match.group(1))
            return jsonify({'success': True, 'ping_time': round(ping_time, 2)})
        else:
            return jsonify({'success': False, 'error': 'No se pudo obtener el tiempo de ping'})
    except subprocess.CalledProcessError:
        return jsonify({'success': False, 'error': 'No se pudo hacer ping al router'})
=======
    # Aquí iría la lógica para actualizar la configuración del router Tenda
    # Por ahora, simularemos una respuesta exitosa
    
    try:
        # Simulación de la actualización del router
        # En un escenario real, aquí llamarías a una función o script que se comunique con el router
        # subprocess.run(['./update_tenda_wifi.sh', wifi_name, wifi_password], check=True)
        
        # Simulamos éxito
        success = True
        message = f"Configuración de WiFi actualizada success. Nuevo SSID: {wifi_name}"
    except subprocess.CalledProcessError as e:
        success = False
        message = f"Error al actualizar la configuración de WiFi: {str(e)}"
    except Exception as e:
        success = False
        message = f"Ocurrió un error inesperado: {str(e)}"

    return jsonify({
        'success': success,
        'message': message
    })
>>>>>>> b1d33405dc68a124f8072cde417a396a49c9e7d0
