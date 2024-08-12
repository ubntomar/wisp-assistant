from flask import Blueprint, render_template, current_app
import subprocess
from flask import request, jsonify

router_bp = Blueprint('router', __name__, url_prefix='/router')

@router_bp.route('/<brand>')
def router_page(brand):
    network_connected = current_app.config['NETWORK_CONNECTED']
    return render_template('router.html', brand=brand, network_connected=network_connected)



@router_bp.route('/tenda/update_wifi', methods=['POST'])
def update_tenda_wifi():
    data = request.json
    wifi_name = data.get('wifi_name')
    wifi_password = data.get('wifi_password')

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