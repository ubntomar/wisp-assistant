#!/bin/bash

# Limpiar todas las reglas existentes
iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X

# Establecer políticas predeterminadas
iptables -P INPUT ACCEPT
iptables -P FORWARD ACCEPT
iptables -P OUTPUT ACCEPT

# Permitir tráfico en el puerto 5000 para la aplicación Flask
iptables -A INPUT -p tcp --dport 5000 -j ACCEPT

# Permitir tráfico relacionado y establecido de eth0 a wlan0
iptables -A FORWARD -i eth0 -o wlan0 -m state --state RELATED,ESTABLISHED -j ACCEPT

# Permitir todo el tráfico de wlan0 a eth0
iptables -A FORWARD -i wlan0 -o eth0 -j ACCEPT

# Habilitar NAT para que los clientes WiFi puedan acceder a Internet
iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE

# Guardar las reglas para que persistan después de reiniciar
netfilter-persistent save

# Habilitar el reenvío de IP
echo 1 > /proc/sys/net/ipv4/ip_forward

# Para hacer permanente el reenvío de IP, descomentar la siguiente línea:
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf

#sudo sh -c 'iptables-save > /etc/iptables/rules.v4'

#sudo systemctl restart netfilter-persistent

sudo iptables -L
sudo iptables -t nat -L -nv