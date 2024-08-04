El archivo de configuración de `hostapd` parece tener los permisos correctos para ser leído por el servicio. Dado que el servicio `hostapd` no está funcionando correctamente cuando se inicia con `systemctl`, pero sí funciona cuando se ejecuta manualmente, es posible que haya un problema con la forma en que el servicio está configurado o con el entorno en el que se ejecuta.

Aquí hay algunos pasos adicionales que puedes seguir para solucionar el problema:

1. **Verifica el archivo de configuración del servicio**:
   Asegúrate de que el archivo de configuración del servicio `hostapd` esté correctamente configurado. Puedes revisar el archivo `/etc/default/hostapd` y asegurarte de que la línea `DAEMON_CONF` apunte al archivo correcto:

   ```shell
   DAEMON_CONF="/etc/hostapd/hostapd.conf"
   ```

2. **Revisa los logs del servicio**:
   Revisa los logs del servicio `hostapd` para obtener más detalles sobre el problema. Ejecuta el siguiente comando para ver los logs:

   ```shell
   sudo journalctl -u hostapd.service
   ```

3. **Edita el archivo de servicio de `hostapd`**:
   Si el archivo de configuración del servicio está correcto, intenta editar el archivo de servicio de `hostapd` para agregar más detalles de depuración. Puedes crear un archivo de servicio personalizado en `/etc/systemd/system/hostapd.service` con el siguiente contenido:

   ```ini
   [Unit]
   Description=Advanced IEEE 802.11 AP and IEEE 802.1X/WPA/WPA2/EAP/RADIUS Authenticator
   After=network.target

   [Service]
   ExecStart=/usr/sbin/hostapd -d /etc/hostapd/hostapd.conf
   Restart=on-failure

   [Install]
   WantedBy=multi-user.target
   ```

   Luego, recarga los archivos de servicio y reinicia `hostapd`:

   ```shell
   sudo systemctl daemon-reload
   sudo systemctl enable hostapd
   sudo systemctl restart hostapd
   ```

4. **Verifica el estado del servicio**:
   Verifica nuevamente el estado del servicio para asegurarte de que esté funcionando correctamente:

   ```shell
   sudo systemctl status hostapd
   ```

Siguiendo estos pasos, deberías poder identificar y solucionar el problema con el servicio `hostapd`.