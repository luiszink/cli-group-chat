#!/usr/bin/env python3
"""
Demo Client für Docker-Präsentation
Sendet automatisch Demo-Nachrichten, um Netzwerk-Kommunikation zu demonstrieren.
"""

import sys
import os
import time
import threading

# Füge src/ zum Python-Path hinzu, damit wir client importieren können
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from client import ChatClient


class DemoClient(ChatClient):
    """Erweitert ChatClient um automatische Demo-Funktionalität"""
    
    def __init__(self, nickname: str, server_host: str, server_port: int, udp_port: int):
        super().__init__(nickname, server_host, server_port, udp_port)
        self.demo_running = False
        
    def start_demo(self):
        """Startet automatische Demo-Nachrichten"""
        self.demo_running = True
        demo_thread = threading.Thread(target=self._demo_loop, daemon=True)
        demo_thread.start()
        
    def _demo_loop(self):
        """Demo-Loop sendet automatisch Nachrichten"""
        # Warte kurz nach dem Login
        time.sleep(3)
        
        demo_messages = [
            f"Hallo! Ich bin {self.nickname} 👋",
            f"{self.nickname}: Die Netzwerk-Kommunikation funktioniert!",
            f"{self.nickname}: Dieser Chat läuft in Docker-Containern 🐳",
        ]
        
        # Sende Broadcast-Nachrichten
        for i, msg in enumerate(demo_messages):
            if not self.demo_running or not self.running:
                break
                
            time.sleep(5)  # 5 Sekunden Pause zwischen Nachrichten
            
            if self.server_socket:
                try:
                    cmd = f"BROADCAST {msg}\n"
                    self.server_socket.sendall(cmd.encode('utf-8'))
                    print(f"[GESENDET] {msg}")
                except Exception as e:
                    print(f"[FEHLER] Konnte Nachricht nicht senden: {e}")
        
        # Nach den Broadcasts: Versuche P2P-Chat zu starten
        time.sleep(5)
        self._demo_peer_chat()
        
    def _demo_peer_chat(self):
        """Demonstriert Peer-to-Peer Chat"""
        with self.users_lock:
            # Finde einen anderen Benutzer
            other_users = [u for u in self.users.keys() if u != self.nickname]
            
        if other_users and self.demo_running:
            target_user = other_users[0]
            print(f"\n[DEMO] Starte P2P-Chat mit {target_user}...")
            
            # Initiere Chat
            success = self.initiate_peer_chat(target_user)
            
            if success:
                time.sleep(2)
                # Sende P2P-Nachricht
                p2p_msg = f"Hallo {target_user}! Dies ist eine direkte P2P-Nachricht von {self.nickname}! 🚀"
                self.send_peer_message(target_user, p2p_msg)
                print(f"[P2P GESENDET] {p2p_msg}")
    
    def run_demo(self):
        """Startet den Client im Demo-Modus"""
        # Empfangs-Threads starten
        server_thread = threading.Thread(target=self.receive_from_server, daemon=True)
        server_thread.start()
        
        udp_thread = threading.Thread(target=self.receive_udp, daemon=True)
        udp_thread.start()
        
        tcp_thread = threading.Thread(target=self.accept_peer_connections, daemon=True)
        tcp_thread.start()
        
        # Demo-Modus starten
        self.start_demo()
        
        # Status-Ausgabe
        print("=" * 70)
        print(f"Demo-Client '{self.nickname}' gestartet")
        print("=" * 70)
        print(f"Verbunden mit Server: {self.server_host}:{self.server_port}")
        print(f"UDP-Port: {self.udp_port}")
        print(f"TCP Listening-Port: {self.tcp_listening_port}")
        print()
        print("Dieser Client sendet automatisch Demo-Nachrichten...")
        print("Drücke Ctrl+C zum Beenden")
        print("=" * 70)
        print()
        
        # Halte den Client am Laufen
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n{self.nickname} wird beendet...")
            self.stop()


def main():
    if len(sys.argv) < 4:
        print("Verwendung: python demo_client.py <nickname> <server_host> <server_port> [udp_port]")
        sys.exit(1)
    
    nickname = sys.argv[1]
    server_host = sys.argv[2]
    server_port = int(sys.argv[3])
    udp_port = int(sys.argv[4]) if len(sys.argv) > 4 else 6000
    
    # Warte kurz, damit der Server Zeit hat zu starten
    print(f"Warte 2 Sekunden, bis Server bereit ist...")
    time.sleep(2)
    
    client = DemoClient(nickname, server_host, server_port, udp_port)
    
    if client.start():
        print(f"✓ {nickname} erfolgreich mit Server verbunden!")
        client.run_demo()
    else:
        print(f"✗ {nickname} konnte keine Verbindung zum Server herstellen")
        sys.exit(1)


if __name__ == '__main__':
    main()
