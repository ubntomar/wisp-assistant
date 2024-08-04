#!/bin/bash
sudo apt update
sudo apt install netfilter-persistent
sudo apt-get install iptables-persistent
sudo apt install 
sudo apt-get remove --purge network-manager
sudo systemctl stop wpa_supplicant
sudo systemctl disable wpa_supplicant
sudo apt-get remove --purge wpasupplicant
sudo apt update
sudo systemctl stop systemd-resolved
sudo systemctl disable systemd-resolved
sudo systemctl mask systemd-resolved
sudo systemctl enable hostapd
sudo systemctl start hostapd
systemctl status hostapd
#hostapd está levantando el ap cuando ejecuto sudo hostapd -d /etc/hostapd.conf
sudo vim /etc/systemd/system/hostapd.service
# [Unit]
# Description=Advanced IEEE 802.11 AP and IEEE 802.1X/WPA/WPA2/EAP/RADIUS Authenticator
# After=network.target

# [Service]
# ExecStart=/usr/sbin/hostapd -d /etc/hostapd/hostapd.conf
# Restart=on-failure

# [Install]
# WantedBy=multi-user.target
sudo systemctl daemon-reload
sudo systemctl enable hostapd
sudo systemctl restart hostapd



