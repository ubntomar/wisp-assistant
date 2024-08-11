import requests
from playwright.sync_api import sync_playwright

def login_router():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Cambia a True para modo headless
        page = browser.new_page()
        page.goto('http://192.168.0.1/login.html')

        # Completar el formulario de login
        page.fill('input[id="login-password"]', 'agwist2017')

        # Imprimir el valor del campo para confirmar que se ha llenado correctamente
        print("Contraseña ingresada:", page.input_value('input[id="login-password"]'))

        # Enviar el formulario
        page.click('button[id="save"]')

        # Esperar a que la página se cargue completamente y manejar redirecciones
        page.wait_for_load_state('networkidle')

        # Imprimir el título de la página para verificar si el login tuvo éxito
        print("Título de la página después del login:", page.title())

        # Comprobar si el login fue exitoso buscando el elemento #loginout
        try:
            page.wait_for_selector('#loginout', timeout=5000)  # Espera hasta 5 segundos por el selector
            print("Login exitoso")
            cookies = page.context.cookies()
            print("Cookies recibidas:", cookies)
        except:
            print("Error al iniciar sesión")
            cookies = None

        # Cerrar el navegador
        browser.close()

    return cookies

def make_post_request(cookies, endpoint_url, post_data):
    if not cookies:
        print("No se recibieron cookies. No se puede realizar la solicitud POST.")
        return

    # Convertir cookies a formato dict para requests
    cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}

    # Encabezados de la solicitud
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept-Language': 'en-US,en;q=0.9',
        'Origin': 'null',
        'Upgrade-Insecure-Requests': '1',
        'Authorization': 'Basic Auth'  # Ajustar si se necesita autenticación básica
    }

    # Hacer la solicitud POST con las cookies
    response = requests.post(endpoint_url, data=post_data, cookies=cookie_dict, headers=headers)
    
    # Imprimir la respuesta
    print("Respuesta del servidor:", response.text)

# Capturar las cookies después del login
cookies = login_router()

# Datos para cambiar el SSID y la contraseña de la red WiFi
post_data_wifi = {
    'module1': 'wifiBasicCfg',
    'wifiSSID': 'PHP',
    'wifiPwd': 'agwist2017'
}
# Hacer una solicitud POST para cambiar el SSID y la contraseña de la red WiFi
make_post_request(cookies, 'http://192.168.0.1/goform/setWizard', post_data_wifi)

# Datos para configurar la WAN
post_data_wan = {
    'module2': 'wanBasicCfg',
    'wanIP': '192.168.88.100',
    'wanMask': '255.255.255.0',
    'wanGateway': '192.168.88.1',
    'wanDns1': '8.8.8.8',
    'wanDns2': '8.8.4.4',
    'wanType': 'static'
}
# Hacer una solicitud POST para configurar la WAN
make_post_request(cookies, 'http://192.168.0.1/goform/setWizard', post_data_wan)

# Datos para configurar la herramienta remota
post_data_remote = {
    'module4': 'remoteWeb',
    'remoteWebEn  ': 'false',
    'remoteWebType': 'any',
    'remoteWebIP': '',
    'remoteWebPort': '8000'
}
# Hacer una solicitud POST para configurar la herramienta remota
make_post_request(cookies, 'http://192.168.0.1/goform/setSysTools', post_data_remote)
