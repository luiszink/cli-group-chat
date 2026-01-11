#!/usr/bin/env python3
"""
Hilfsskript zum Ermitteln der lokalen IP-Adresse für Netzwerk-Chat
"""

import socket
import sys


def get_local_ip():
    """Ermittelt die lokale IP-Adresse im Netzwerk"""
    try:
        # Erstelle eine UDP-Verbindung (muss nicht wirklich senden)
        # Dies gibt uns die IP-Adresse, die für externe Verbindungen verwendet wird
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return None


def get_all_ips():
    """Ermittelt alle Netzwerk-Interfaces mit ihren IP-Adressen"""
    hostname = socket.gethostname()
    try:
        # Alle IP-Adressen für diesen Host
        ip_list = socket.gethostbyname_ex(hostname)[2]
        return [ip for ip in ip_list if not ip.startswith("127.")]
    except Exception:
        return []


def main():
    print("=" * 60)
    print("Netzwerk-IP-Informationen für Group Chat Server")
    print("=" * 60)
    print()
    
    # Hostname
    hostname = socket.gethostname()
    print(f"Hostname: {hostname}")
    print()
    
    # Bevorzugte IP (die für externe Verbindungen verwendet wird)
    primary_ip = get_local_ip()
    if primary_ip:
        print(f"Hauptnetzwerk-IP: {primary_ip}")
        print()
        print("Diese IP-Adresse sollten andere Clients verwenden!")
        print()
    
    # Alle verfügbaren IPs
    all_ips = get_all_ips()
    if all_ips:
        print("Alle verfügbaren Netzwerk-IPs:")
        for ip in all_ips:
            if ip == primary_ip:
                print(f"  * {ip} (empfohlen)")
            else:
                print(f"  - {ip}")
        print()
    
    # Anweisungen
    print("-" * 60)
    print("So starten Sie den Server für Netzwerk-Chat:")
    print("-" * 60)
    print()
    print("1. Auf diesem Rechner den Server starten:")
    print("   python server.py 5555")
    print()
    print("2. Auf anderen Rechnern im gleichen Netzwerk Clients starten:")
    if primary_ip:
        print(f"   python client.py <nickname> {primary_ip} 5555 6001")
        print()
        print("   Beispiel:")
        print(f"   python client.py Alice {primary_ip} 5555 6001")
        print(f"   python client.py Bob {primary_ip} 5555 6002")
    else:
        print("   python client.py <nickname> <SERVER_IP> 5555 6001")
    print()
    print("3. Jeder Client benötigt einen eigenen UDP-Port (6001, 6002, etc.)")
    print()
    
    # Firewall-Hinweis
    print("-" * 60)
    print("WICHTIG: Firewall-Einstellungen")
    print("-" * 60)
    print()
    print("Stellen Sie sicher, dass folgende Ports freigegeben sind:")
    print(f"  - TCP Port 5555 (Server)")
    print(f"  - UDP Ports 6001-6010 (Clients für P2P)")
    print()
    print("Windows Firewall:")
    print("  Beim ersten Start wird Windows nach Erlaubnis fragen.")
    print("  Wählen Sie 'Zugriff zulassen' für private Netzwerke.")
    print()


if __name__ == '__main__':
    main()
