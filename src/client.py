#!/usr/bin/env python3
"""
Group Chat Client
Registriert sich beim Server und kann direkt mit anderen Peers chatten.
"""

import socket
import threading
import sys
import time
import logging
from typing import Dict, Tuple, Optional

# Client: Logging auf ERROR setzen (nur kritische Fehler anzeigen)
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class ChatClient:
    def __init__(self, nickname: str, server_host: str, server_port: int, udp_port: int):
        self.nickname = nickname
        self.server_host = server_host
        self.server_port = server_port
        self.udp_port = udp_port
        
        # Server-Verbindung
        self.server_socket: Optional[socket.socket] = None
        self.server_file = None
        
        # UDP für Peer-Kommunikation
        self.udp_socket: Optional[socket.socket] = None
        
        # Nutzerliste: {nickname: (ip, udp_port)}
        self.users: Dict[str, Tuple[str, int]] = {}
        self.users_lock = threading.Lock()
        
        # Peer-to-Peer TCP Verbindungen: {nickname: socket}
        self.peer_connections: Dict[str, socket.socket] = {}
        self.peer_lock = threading.Lock()
        
        # TCP Listening Socket für eingehende Peer-Verbindungen
        self.tcp_listening_port: Optional[int] = None
        self.tcp_listening_socket: Optional[socket.socket] = None
        
        self.running = False
        
        # GUI (optional)
        self.gui = None
        self.gui_enabled = False
        
        # Event-Callbacks für UI-Updates (sowohl CLI als auch GUI)
        self.ui_callbacks = {
            'user_joined': [],
            'user_left': [],
            'broadcast_message': [],
            'peer_chat_started': [],
            'peer_chat_ended': [],
            'peer_message': [],
            'peer_message_sent': [],
            'chat_request': [],
            'error': []
        }
        
    def start(self) -> bool:
        """Startet den Client und verbindet zum Server"""
        try:
            # UDP Socket für Peer-Kommunikation öffnen
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.bind(('0.0.0.0', self.udp_port))
            logging.info(f"UDP Socket gebunden auf Port {self.udp_port}")
            
            # TCP Listening Socket für eingehende Peer-Verbindungen
            self.tcp_listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_listening_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_listening_socket.bind(('0.0.0.0', 0))  # OS wählt freien Port
            self.tcp_listening_port = self.tcp_listening_socket.getsockname()[1]
            self.tcp_listening_socket.listen(5)
            logging.info(f"TCP Listening Socket auf Port {self.tcp_listening_port}")
            
            # Mit Server verbinden
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.connect((self.server_host, self.server_port))
            self.server_file = self.server_socket.makefile('r', encoding='utf-8')
            
            # Login senden
            login_msg = f"LOGIN {self.nickname} {self.udp_port}\n"
            self.server_socket.sendall(login_msg.encode('utf-8'))
            
            # Login-Antwort empfangen
            response = self.server_file.readline().strip()
            
            if response == "LOGIN_OK":
                logging.info("Erfolgreich beim Server angemeldet")
                
                # Nutzerliste empfangen
                self.receive_userlist()
                
                self.running = True
                
                # Threads starten
                threading.Thread(target=self.receive_from_server, daemon=True).start()
                threading.Thread(target=self.receive_udp, daemon=True).start()
                threading.Thread(target=self.accept_peer_connections, daemon=True).start()
                
                return True
                
            elif response.startswith("ERROR"):
                error_type = response.split(' ', 1)[1] if ' ' in response else "UNKNOWN"
                logging.error(f"Login fehlgeschlagen: {error_type}")
                return False
            else:
                logging.error(f"Unerwartete Antwort vom Server: {response}")
                return False
                
        except Exception as e:
            logging.error(f"Fehler beim Starten des Clients: {e}")
            return False
            
    def stop(self):
        """Stoppt den Client"""
        self.running = False
        
        # Vom Server abmelden
        if self.server_socket:
            try:
                self.server_socket.sendall(b"LOGOUT\n")
                time.sleep(0.1)
            except:
                pass
                
        # Alle Sockets schließen
        if self.server_file:
            try:
                self.server_file.close()
            except:
                pass
                
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
                
        if self.udp_socket:
            try:
                self.udp_socket.close()
            except:
                pass
                
        if self.tcp_listening_socket:
            try:
                self.tcp_listening_socket.close()
            except:
                pass
                
        # Peer-Verbindungen schließen
        with self.peer_lock:
            for sock in self.peer_connections.values():
                try:
                    sock.sendall(b"BYE\n")
                    sock.close()
                except:
                    pass
            self.peer_connections.clear()
            
        logging.info("Client gestoppt")
    
    def register_ui_callback(self, event_type: str, callback):
        """Registriert einen Callback für UI-Events"""
        if event_type in self.ui_callbacks:
            self.ui_callbacks[event_type].append(callback)
            
    def trigger_ui_event(self, event_type: str, *args, **kwargs):
        """Triggert ein UI-Event für alle registrierten Callbacks"""
        if event_type in self.ui_callbacks:
            callback_count = len(self.ui_callbacks[event_type])
            logging.debug(f"Trigger Event '{event_type}' mit {callback_count} Callbacks, Args: {args}")
            for callback in self.ui_callbacks[event_type]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    logging.error(f"Fehler in UI-Callback für {event_type}: {e}")
        
    def receive_userlist(self):
        """Empfängt die initiale Nutzerliste vom Server"""
        line = self.server_file.readline().strip()
        
        if line != "USERLIST_BEGIN":
            logging.error(f"Erwartete USERLIST_BEGIN, erhielt: {line}")
            return
            
        with self.users_lock:
            while True:
                line = self.server_file.readline().strip()
                
                if line == "USERLIST_END":
                    break
                    
                if line.startswith("USER "):
                    parts = line.split(' ', 3)
                    if len(parts) >= 4:
                        nick = parts[1]
                        ip = parts[2]
                        udp_port = int(parts[3])
                        self.users[nick] = (ip, udp_port)
                        
        print(f"\n=== Aktuelle Benutzer ({len(self.users)}) ===")
        with self.users_lock:
            for nick in self.users.keys():
                print(f"  - {nick}")
        print()
        
    def receive_from_server(self):
        """Empfängt Nachrichten vom Server"""
        try:
            while self.running:
                line = self.server_file.readline()
                
                if not line:
                    break
                    
                line = line.strip()
                if not line:
                    continue
                    
                self.process_server_message(line)
                
        except Exception as e:
            if self.running:
                logging.error(f"Fehler beim Empfangen vom Server: {e}")
                
    def process_server_message(self, line: str):
        """Verarbeitet eine Nachricht vom Server"""
        parts = line.split(' ')
        command = parts[0]
        
        if command == "USER_JOINED" and len(parts) >= 4:
            nick = parts[1]
            ip = parts[2]
            udp_port = int(parts[3])
            
            with self.users_lock:
                self.users[nick] = (ip, udp_port)
            
            # Trigger Event für alle UIs
            self.trigger_ui_event('user_joined', nick, ip, udp_port)
            
        elif command == "USER_LEFT" and len(parts) >= 2:
            nick = parts[1]
            
            with self.users_lock:
                if nick in self.users:
                    del self.users[nick]
            
            # Trigger Event für alle UIs
            self.trigger_ui_event('user_left', nick)
            
        elif command == "BROADCAST_MSG" and len(parts) >= 3:
            from_nick = parts[1]
            # Alles nach dem zweiten Leerzeichen ist die Nachricht
            message = ' '.join(parts[2:]) if len(parts) > 2 else ""
            
            # Trigger Event für alle UIs
            self.trigger_ui_event('broadcast_message', from_nick, message)
            
        elif command == "LOGOUT_OK":
            logging.info("Logout bestätigt")
            
        elif command.startswith("ERROR"):
            error_msg = ' '.join(parts[1:]) if len(parts) > 1 else "UNKNOWN"
            
            # Trigger Event für alle UIs
            self.trigger_ui_event('error', error_msg)
            
        else:
            logging.warning(f"Unbekannte Server-Nachricht: {line}")
            
    def receive_udp(self):
        """Empfängt UDP-Nachrichten von anderen Peers"""
        try:
            while self.running:
                try:
                    data, addr = self.udp_socket.recvfrom(1024)
                    message = data.decode('utf-8').strip()
                    
                    self.process_udp_message(message, addr)
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        logging.error(f"Fehler beim UDP-Empfang: {e}")
                        
        except Exception as e:
            if self.running:
                logging.error(f"UDP-Empfangsthread beendet: {e}")
                
    def process_udp_message(self, message: str, addr: Tuple[str, int]):
        """Verarbeitet eine UDP-Nachricht"""
        parts = message.split(' ', 2)
        command = parts[0]
        
        if command == "CHAT_REQUEST" and len(parts) >= 3:
            from_nick = parts[1]
            tcp_port = int(parts[2])
            peer_ip = addr[0]
            
            # Trigger Event für alle UIs
            self.trigger_ui_event('chat_request', from_nick)
            
            # Automatisch akzeptieren und Verbindung aufbauen
            threading.Thread(
                target=self.connect_to_peer,
                args=(from_nick, peer_ip, tcp_port),
                daemon=True
            ).start()
            
        elif command == "CHAT_ACCEPT" and len(parts) >= 3:
            from_nick = parts[2]
            logging.info(f"Chat-Anfrage von {from_nick} akzeptiert")
            
        elif command == "CHAT_REJECT" and len(parts) >= 2:
            reason = parts[1] if len(parts) > 1 else "Keine Angabe"
            print(f"\n>>> Chat-Anfrage abgelehnt: {reason} <<<")
            print("> ", end='', flush=True)
            
    def accept_peer_connections(self):
        """Akzeptiert eingehende Peer-TCP-Verbindungen"""
        try:
            while self.running:
                try:
                    peer_socket, peer_addr = self.tcp_listening_socket.accept()
                    logging.info(f"Eingehende Peer-Verbindung von {peer_addr}")
                    
                    threading.Thread(
                        target=self.handle_peer_connection,
                        args=(peer_socket,),
                        daemon=True
                    ).start()
                    
                except Exception as e:
                    if self.running:
                        logging.error(f"Fehler beim Akzeptieren einer Peer-Verbindung: {e}")
                        
        except Exception as e:
            if self.running:
                logging.error(f"Peer-Accept-Thread beendet: {e}")
                
    def handle_peer_connection(self, peer_socket: socket.socket):
        """Behandelt eine Peer-to-Peer Chat-Verbindung"""
        peer_nick = None
        file_handle = None
        
        try:
            file_handle = peer_socket.makefile('r', encoding='utf-8')
            
            # CHAT_HELLO erwarten
            line = file_handle.readline().strip()
            
            if line.startswith("CHAT_HELLO "):
                peer_nick = line.split(' ', 1)[1]
                
                # Antworten
                peer_socket.sendall(f"CHAT_HELLO {self.nickname}\n".encode('utf-8'))
                
                # Prüfe ob bereits eine Verbindung existiert (Race Condition)
                already_connected = False
                with self.peer_lock:
                    if peer_nick in self.peer_connections:
                        logging.warning(f"Verbindung zu {peer_nick} existiert bereits, schließe neue")
                        already_connected = True
                    else:
                        self.peer_connections[peer_nick] = peer_socket
                        logging.info(f"Peer-Verbindung zu {peer_nick} gespeichert (handle_peer_connection), Socket {peer_socket.fileno()}")
                
                if already_connected:
                    # Schließe diese Verbindung, behalte die bestehende
                    return
                
                # Trigger Event für alle UIs
                self.trigger_ui_event('peer_chat_started', peer_nick)
                
                logging.info(f"Starte Chat-Loop (handle) für {peer_nick}, Socket {peer_socket.fileno()}")
                    
                # Chat-Loop
                while self.running:
                    line = file_handle.readline()
                    
                    if not line:
                        break
                        
                    line = line.strip()
                    if not line:
                        continue
                        
                    if line == "BYE":
                        print(f"\n>>> {peer_nick} hat den Direkt-Chat beendet <<<")
                        print("> ", end='', flush=True)
                        break
                        
                    if line.startswith("MSG "):
                        msg = line[4:]
                        print(f"\n[{peer_nick}] {msg}")
                        print("> ", end='', flush=True)
                        
            else:
                logging.warning(f"Erwartete CHAT_HELLO, erhielt: {line}")
                peer_socket.sendall(b"ERROR PROTOCOL_VIOLATION\n")
                
        except Exception as e:
            logging.error(f"Fehler in Peer-Verbindung mit {peer_nick}: {e}")
            
        finally:
            if peer_nick:
                with self.peer_lock:
                    if peer_nick in self.peer_connections:
                        del self.peer_connections[peer_nick]
                        
            if file_handle:
                try:
                    file_handle.close()
                except:
                    pass
                    
            try:
                peer_socket.close()
            except:
                pass
                
    def connect_to_peer(self, peer_nick: str, peer_ip: str, peer_tcp_port: int):
        """Verbindet zu einem Peer für Direkt-Chat"""
        try:
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.connect((peer_ip, peer_tcp_port))
            
            # CHAT_HELLO senden
            peer_socket.sendall(f"CHAT_HELLO {self.nickname}\n".encode('utf-8'))
            
            # Antwort empfangen
            file_handle = peer_socket.makefile('r', encoding='utf-8')
            response = file_handle.readline().strip()
            
            if response.startswith("CHAT_HELLO"):
                # Prüfe ob bereits eine Verbindung existiert (Race Condition)
                already_connected = False
                with self.peer_lock:
                    if peer_nick in self.peer_connections:
                        logging.warning(f"Verbindung zu {peer_nick} existiert bereits, schließe neue")
                        already_connected = True
                    else:
                        self.peer_connections[peer_nick] = peer_socket
                        logging.info(f"Peer-Verbindung zu {peer_nick} gespeichert (connect_to_peer), Socket {peer_socket.fileno()}")
                
                if already_connected:
                    # Schließe diese Verbindung, behalte die bestehende
                    return
                
                # Trigger Event für alle UIs
                self.trigger_ui_event('peer_chat_started', peer_nick)
                
                logging.info(f"Starte Chat-Loop (connect) für {peer_nick}, Socket {peer_socket.fileno()}")
                    
                # Chat-Loop
                while self.running:
                    line = file_handle.readline()
                    
                    if not line:
                        break
                        
                    line = line.strip()
                    if not line:
                        continue
                        
                    if line == "BYE":
                        # Trigger Event für alle UIs
                        self.trigger_ui_event('peer_chat_ended', peer_nick)
                        break
                        
                    if line.startswith("MSG "):
                        msg = line[4:]
                        logging.info(f"Peer-Nachricht empfangen von {peer_nick}: {msg}")
                        # Trigger Event für alle UIs
                        self.trigger_ui_event('peer_message', peer_nick, msg)
                        
            else:
                logging.error(f"Unerwartete Antwort von {peer_nick}: {response}")
                
        except Exception as e:
            logging.error(f"Fehler beim Verbinden zu {peer_nick}: {e}")
            
        finally:
            with self.peer_lock:
                if peer_nick in self.peer_connections:
                    del self.peer_connections[peer_nick]
                    
    def send_broadcast(self, message: str):
        """Sendet eine Broadcast-Nachricht über den Server"""
        try:
            self.server_socket.sendall(f"BROADCAST {message}\n".encode('utf-8'))
        except Exception as e:
            logging.error(f"Fehler beim Senden der Broadcast-Nachricht: {e}")
            
    def initiate_peer_chat(self, peer_nick: str):
        """Initiiert einen Direkt-Chat mit einem Peer"""
        with self.users_lock:
            if peer_nick not in self.users:
                print(f"Benutzer {peer_nick} nicht gefunden")
                return
                
            peer_ip, peer_udp_port = self.users[peer_nick]
            
        # Prüfe ob bereits verbunden
        with self.peer_lock:
            if peer_nick in self.peer_connections:
                print(f"Bereits mit {peer_nick} verbunden")
                return
                
        # CHAT_REQUEST per UDP senden
        try:
            message = f"CHAT_REQUEST {self.nickname} {self.tcp_listening_port}\n"
            self.udp_socket.sendto(message.encode('utf-8'), (peer_ip, peer_udp_port))
            print(f"Chat-Anfrage an {peer_nick} gesendet")
        except Exception as e:
            logging.error(f"Fehler beim Senden der Chat-Anfrage: {e}")
            
    def send_peer_message(self, peer_nick: str, message: str):
        """Sendet eine Direkt-Nachricht an einen Peer"""
        with self.peer_lock:
            if peer_nick not in self.peer_connections:
                logging.error(f"Keine aktive Verbindung zu {peer_nick}")
                print(f"Keine aktive Verbindung zu {peer_nick}")
                return
                
            sock = self.peer_connections[peer_nick]
            logging.info(f"Verwende Socket {sock.fileno()} für {peer_nick}")
            
        try:
            sock.sendall(f"MSG {message}\n".encode('utf-8'))
            logging.info(f"Peer-Nachricht gesendet an {peer_nick}: {message}")
            # Trigger Event für eigene Nachricht (damit sie im UI angezeigt wird)
            self.trigger_ui_event('peer_message_sent', peer_nick, message)
        except Exception as e:
            logging.error(f"Fehler beim Senden der Peer-Nachricht: {e}")
            with self.peer_lock:
                if peer_nick in self.peer_connections:
                    del self.peer_connections[peer_nick]
                    
    def list_users(self):
        """Zeigt alle verfügbaren Benutzer an"""
        with self.users_lock:
            if not self.users:
                print("Keine anderen Benutzer online")
            else:
                print(f"\n=== Online Benutzer ({len(self.users)}) ===")
                for nick in sorted(self.users.keys()):
                    with self.peer_lock:
                        status = " [verbunden]" if nick in self.peer_connections else ""
                    print(f"  - {nick}{status}")
                    
    def launch_gui(self):
        """Startet die GUI"""
        try:
            from gui import ChatGUI
            
            self.gui_enabled = True
            self.gui = ChatGUI(self)
            print("\nStarte GUI...")
            self.gui.start()
            
        except ImportError:
            print("Fehler: gui.py nicht gefunden oder tkinter nicht installiert")
            self.gui_enabled = False
        except Exception as e:
            print(f"Fehler beim Starten der GUI: {e}")
            self.gui_enabled = False
    
    def _register_cli_callbacks(self):
        """Registriert CLI-Callbacks für Events"""
        self.register_ui_callback('user_joined', lambda nick, ip, port: self._cli_print(f"\n>>> {nick} ist beigetreten <<<"))
        self.register_ui_callback('user_left', lambda nick: self._cli_print(f"\n>>> {nick} hat den Chat verlassen <<<"))
        self.register_ui_callback('broadcast_message', lambda from_nick, msg: self._cli_print(f"\n[BROADCAST von {from_nick}] {msg}"))
        self.register_ui_callback('peer_chat_started', lambda nick: self._cli_print(f"\n>>> Direkt-Chat mit {nick} gestartet <<<"))
        self.register_ui_callback('peer_chat_ended', lambda nick: self._cli_print(f"\n>>> {nick} hat den Direkt-Chat beendet <<<"))
        self.register_ui_callback('peer_message', lambda nick, msg: self._cli_print(f"\n[{nick}] {msg}"))
        self.register_ui_callback('peer_message_sent', lambda nick, msg: self._cli_print(f"\n[{self.nickname}] {msg}"))
        self.register_ui_callback('chat_request', lambda nick: self._cli_print(f"\n>>> Chat-Anfrage von {nick} <<<"))
        self.register_ui_callback('error', lambda msg: self._cli_print(f"\n[SERVER ERROR] {msg}"))
    
    def _cli_print(self, message: str):
        """Gibt eine Nachricht in der CLI aus"""
        # Immer ausgeben - CLI und GUI können parallel laufen
        # (Auch wenn GUI aktiv ist, kann man in der Konsole die Ausgaben sehen)
        print(message)
        if not self.gui_enabled:
            print("> ", end='', flush=True)
    
    def run_cli(self):
        """Führt die Command-Line-Interface aus"""
        # Registriere CLI-Callbacks
        self._register_cli_callbacks()
        
        print("\n=== Group Chat ===")
        print("Befehle:")
        print("  /broadcast (/b) <nachricht>  - Broadcast an alle")
        print("  /msg (/m) <user> <nachricht> - Direkt-Nachricht")
        print("  /chat (/c) <user>            - Direkt-Chat initiieren")
        print("  /users (/u)                  - Benutzer auflisten")
        print("  /gui                         - GUI starten")
        print("  /quit (/q)                   - Beenden")
        print()
        
        while self.running:
            try:
                print("> ", end='', flush=True)
                line = input()
                
                if not line:
                    continue
                    
                # Broadcast: /broadcast oder /b
                if line.startswith('/broadcast ') or line.startswith('/b '):
                    # Finde Position nach dem Befehl
                    space_pos = line.index(' ')
                    msg = line[space_pos + 1:]
                    self.send_broadcast(msg)
                    
                # Message: /msg oder /m
                elif line.startswith('/msg ') or line.startswith('/m '):
                    parts = line.split(' ', 2)
                    if len(parts) < 3:
                        print("Verwendung: /msg (/m) <user> <nachricht>")
                        continue
                    peer_nick = parts[1]
                    msg = parts[2]
                    self.send_peer_message(peer_nick, msg)
                    
                # Chat: /chat oder /c
                elif line.startswith('/chat ') or line.startswith('/c '):
                    space_pos = line.index(' ')
                    peer_nick = line[space_pos + 1:].strip()
                    self.initiate_peer_chat(peer_nick)
                    
                # Users: /users oder /u
                elif line == '/users' or line == '/u':
                    self.list_users()
                    
                # GUI starten
                elif line == '/gui':
                    self.launch_gui()
                    # GUI läuft im selben Thread, danach beenden
                    break
                    
                # Quit: /quit oder /q
                elif line == '/quit' or line == '/q':
                    self.stop()
                    break
                    
                else:
                    print("Unbekannter Befehl. Verwende /b, /m, /c, /u, /gui oder /q")
                    
            except EOFError:
                break
            except KeyboardInterrupt:
                print()
                self.stop()
                break
            except Exception as e:
                logging.error(f"Fehler in CLI: {e}")


def main():
    if len(sys.argv) < 4:
        print("=" * 70)
        print("Group Chat Client - Verwendung")
        print("=" * 70)
        print()
        print("Verwendung: python client.py <nickname> <server_host> <server_port> [udp_port]")
        print()
        print("Parameter:")
        print("  nickname      - Dein eindeutiger Benutzername (2-20 Zeichen)")
        print("  server_host   - IP-Adresse oder Hostname des Servers")
        print("  server_port   - TCP-Port des Servers (Standard: 5555)")
        print("  udp_port      - Dein UDP-Port für P2P-Chat (optional, Standard: 6000)")
        print()
        print("Beispiele:")
        print()
        print("  Lokaler Test (auf demselben Rechner):")
        print("    python client.py Alice localhost 5555 6001")
        print()
        print("  Netzwerk-Chat (verschiedene Rechner im gleichen WLAN):")
        print("    python client.py Alice 192.168.1.10 5555 6001")
        print()
        print("Hinweise:")
        print("  - Für Netzwerk-Chat die Server-IP mit 'python get_ip.py' ermitteln")
        print("  - Jeder Client braucht einen eigenen UDP-Port (6001, 6002, etc.)")
        print("  - Alle Geräte müssen im gleichen Netzwerk sein")
        print("=" * 70)
        sys.exit(1)
        
    nickname = sys.argv[1]
    server_host = sys.argv[2]
    server_port = int(sys.argv[3])
    udp_port = int(sys.argv[4]) if len(sys.argv) > 4 else 6000
    
    client = ChatClient(nickname, server_host, server_port, udp_port)
    
    if client.start():
        client.run_cli()
    else:
        print("Konnte keine Verbindung zum Server herstellen")
        sys.exit(1)


if __name__ == '__main__':
    main()
