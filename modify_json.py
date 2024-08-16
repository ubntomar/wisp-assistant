import json

# Leer el archivo JSON
with open('wireless_config.json', 'r') as file:
    data = json.load(file)

# Añadir el campo 'ip' a cada objeto en el array
for item in data:
    item['ip'] = ""

# Escribir el JSON modificado de vuelta al archivo
with open('wireless_config.json', 'w') as file:
    json.dump(data, file, indent=2)

print("El archivo JSON ha sido modificado exitosamente.")
