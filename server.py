#!/usr/bin/env python3
"""
Group Chat Server
Verwaltet Client-Registrierungen und Broadcast-Nachrichten über TCP.
"""

import socket
import threading
import sys
from typing import Dict, Tuple
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ChatServer:
    def __init__(self, host: str = '0.0.0.0', port: int = 5555):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients: Dict[str, Tuple[socket.socket, str, int]] = {}  # {nickname: (socket, ip, udp_port)}
        self.clients_lock = threading.Lock()
        self.running = False
        
    def start(self):
        """Startet den Server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            logging.info(f"Server gestartet auf {self.host}:{self.port}")
            
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    logging.info(f"Neue Verbindung von {client_address}")
                    
                    # Client in eigenem Thread behandeln
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_address),
                        daemon=True
                    )
                    client_thread.start()
                    
                except Exception as e:
                    if self.running:
                        logging.error(f"Fehler beim Akzeptieren einer Verbindung: {e}")
                    
        except Exception as e:
            logging.error(f"Fehler beim Starten des Servers: {e}")
        finally:
            self.stop()
            
    def stop(self):
        """Stoppt den Server"""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        logging.info("Server gestoppt")
        
    def handle_client(self, client_socket: socket.socket, client_address: Tuple[str, int]):
        """Behandelt einen einzelnen Client"""
        nickname = None
        file_handle = None
        
        try:
            # Socket in File-Objekt für zeilenweises Lesen umwandeln
            file_handle = client_socket.makefile('r', encoding='utf-8')
            
            # Warte auf LOGIN
            line = file_handle.readline().strip()
            
            if not line:
                logging.warning(f"Client {client_address} hat Verbindung ohne Login geschlossen")
                return
                
            parts = line.split(' ', 2)
            
            if parts[0] != 'LOGIN' or len(parts) < 3:
                self.send_message(client_socket, "ERROR INVALID_FORMAT\n")
                logging.warning(f"Ungültiges Login-Format von {client_address}: {line}")
                return
                
            nickname = parts[1]
            try:
                udp_port = int(parts[2])
            except ValueError:
                self.send_message(client_socket, "ERROR INVALID_FORMAT\n")
                logging.warning(f"Ungültiger UDP-Port von {client_address}: {parts[2]}")
                return
            
            # Nickname-Validierung
            if not self.is_valid_nickname(nickname):
                self.send_message(client_socket, "ERROR INVALID_FORMAT\n")
                logging.warning(f"Ungültiger Nickname: {nickname}")
                return
                
            # Prüfe ob Nickname bereits vergeben
            with self.clients_lock:
                if nickname in self.clients:
                    self.send_message(client_socket, "ERROR NICK_IN_USE\n")
                    logging.warning(f"Nickname {nickname} bereits vergeben")
                    return
                    
                # Client registrieren
                client_ip = client_address[0]
                self.clients[nickname] = (client_socket, client_ip, udp_port)
                
            logging.info(f"Client {nickname} erfolgreich eingeloggt von {client_ip}:{udp_port}")
            
            # LOGIN_OK senden
            self.send_message(client_socket, "LOGIN_OK\n")
            
            # Komplette Nutzerliste senden
            self.send_userlist(client_socket, nickname)
            
            # USER_JOINED an alle anderen senden
            self.broadcast_user_joined(nickname, client_ip, udp_port)
            
            # Nachrichten-Loop
            while self.running:
                line = file_handle.readline()
                
                if not line:
                    # Verbindung geschlossen
                    break
                    
                line = line.strip()
                if not line:
                    continue
                    
                self.process_command(client_socket, nickname, line)
                
        except Exception as e:
            logging.error(f"Fehler bei Client {nickname or client_address}: {e}")
            
        finally:
            # Client abmelden
            if nickname:
                with self.clients_lock:
                    if nickname in self.clients:
                        del self.clients[nickname]
                        
                self.broadcast_user_left(nickname)
                logging.info(f"Client {nickname} abgemeldet")
                
            if file_handle:
                try:
                    file_handle.close()
                except:
                    pass
                    
            try:
                client_socket.close()
            except:
                pass
                
    def process_command(self, client_socket: socket.socket, nickname: str, line: str):
        """Verarbeitet Kommandos vom Client"""
        parts = line.split(' ', 1)
        command = parts[0]
        
        if command == 'BROADCAST':
            if len(parts) < 2:
                self.send_message(client_socket, "ERROR INVALID_FORMAT\n")
                return
                
            message = parts[1]
            
            # Prüfe Nachrichtenlänge
            if len(message) > 1000:
                self.send_message(client_socket, "ERROR MSG_TOO_LONG\n")
                return
                
            # Broadcast an alle Clients
            self.broadcast_message(nickname, message)
            logging.info(f"Broadcast von {nickname}: {message[:50]}...")
            
        elif command == 'LOGOUT':
            self.send_message(client_socket, "LOGOUT_OK\n")
            # Verbindung wird im finally-Block geschlossen
            
        else:
            self.send_message(client_socket, "ERROR UNKNOWN_CMD\n")
            logging.warning(f"Unbekanntes Kommando von {nickname}: {command}")
            
    def send_userlist(self, client_socket: socket.socket, exclude_nickname: str = None):
        """Sendet die komplette Nutzerliste an einen Client"""
        self.send_message(client_socket, "USERLIST_BEGIN\n")
        
        with self.clients_lock:
            for nick, (_, ip, udp_port) in self.clients.items():
                if nick != exclude_nickname:
                    self.send_message(client_socket, f"USER {nick} {ip} {udp_port}\n")
                    
        self.send_message(client_socket, "USERLIST_END\n")
        
    def broadcast_user_joined(self, nickname: str, ip: str, udp_port: int):
        """Informiert alle Clients über einen neuen Benutzer"""
        message = f"USER_JOINED {nickname} {ip} {udp_port}\n"
        
        with self.clients_lock:
            for nick, (sock, _, _) in self.clients.items():
                if nick != nickname:
                    self.send_message(sock, message)
                    
    def broadcast_user_left(self, nickname: str):
        """Informiert alle Clients über einen abgemeldeten Benutzer"""
        message = f"USER_LEFT {nickname}\n"
        
        with self.clients_lock:
            for nick, (sock, _, _) in self.clients.items():
                if nick != nickname:
                    self.send_message(sock, message)
                    
    def broadcast_message(self, from_nickname: str, text: str):
        """Sendet eine Broadcast-Nachricht an alle Clients"""
        message = f"BROADCAST_MSG {from_nickname} {text}\n"
        
        with self.clients_lock:
            for nick, (sock, _, _) in self.clients.items():
                self.send_message(sock, message)
                
    @staticmethod
    def send_message(client_socket: socket.socket, message: str):
        """Sendet eine Nachricht an einen Client"""
        try:
            client_socket.sendall(message.encode('utf-8'))
        except Exception as e:
            logging.error(f"Fehler beim Senden einer Nachricht: {e}")
            
    @staticmethod
    def is_valid_nickname(nickname: str) -> bool:
        """Validiert einen Nickname"""
        if not nickname or len(nickname) < 2 or len(nickname) > 20:
            return False
        # Nur alphanumerische Zeichen und Unterstrich
        return nickname.replace('_', '').isalnum()


def main():
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 5555
        
    server = ChatServer(port=port)
    
    try:
        server.start()
    except KeyboardInterrupt:
        logging.info("\nServer wird beendet...")
        server.stop()


if __name__ == '__main__':
    main()
