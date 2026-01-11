#!/usr/bin/env python3
"""
GUI für Group Chat Client
Verwendet tkinter für die grafische Oberfläche.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from typing import Optional
import logging


class ChatGUI:
    def __init__(self, client):
        """
        Initialisiert die GUI für einen bestehenden ChatClient
        
        Args:
            client: Eine ChatClient-Instanz die bereits verbunden ist
        """
        self.client = client
        self.root = None
        self.running = False
        
        # GUI-Elemente
        self.chat_display = None
        self.broadcast_input = None
        self.users_listbox = None
        self.peer_chat_notebook = None
        self.peer_chat_tabs = {}  # {nickname: (frame, text_widget, input_widget)}
        
    def start(self):
        """Startet die GUI im aktuellen Thread"""
        self.running = True
        self.root = tk.Tk()
        self.root.title(f"Group Chat - {self.client.nickname}")
        self.root.geometry("900x600")
        
        # Hauptcontainer
        main_container = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Linke Seite: Benutzerliste
        self._create_users_panel(main_container)
        
        # Mittlere Seite: Broadcast-Chat
        self._create_broadcast_panel(main_container)
        
        # Rechte Seite: Peer-to-Peer Chats
        self._create_peer_panel(main_container)
        
        # Aktualisiere die Benutzerliste initial
        self.update_users_list()
        
        # Registriere UI-Callbacks beim Client
        self._register_callbacks()
        
        # Starte Aktualisierungs-Thread
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        
        # Beim Schließen
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # GUI-Loop starten
        self.root.mainloop()
        
    def _create_users_panel(self, parent):
        """Erstellt das Benutzerlisten-Panel"""
        users_frame = ttk.Frame(parent, width=200)
        parent.add(users_frame, weight=1)
        
        ttk.Label(users_frame, text="Online Benutzer", font=('Arial', 10, 'bold')).pack(pady=5)
        
        # Listbox mit Scrollbar
        list_frame = ttk.Frame(users_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.users_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        self.users_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.users_listbox.yview)
        
        # Doppelklick um Chat zu starten
        self.users_listbox.bind('<Double-Button-1>', self._on_user_double_click)
        
        # Button: Chat starten
        ttk.Button(users_frame, text="Chat starten", command=self._start_selected_chat).pack(pady=5)
        
    def _create_broadcast_panel(self, parent):
        """Erstellt das Broadcast-Chat-Panel"""
        broadcast_frame = ttk.Frame(parent)
        parent.add(broadcast_frame, weight=2)
        
        ttk.Label(broadcast_frame, text="Broadcast Chat", font=('Arial', 10, 'bold')).pack(pady=5)
        
        # Chat-Anzeige
        self.chat_display = scrolledtext.ScrolledText(
            broadcast_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            height=20
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Eingabebereich
        input_frame = ttk.Frame(broadcast_frame)
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.broadcast_input = ttk.Entry(input_frame)
        self.broadcast_input.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.broadcast_input.bind('<Return>', lambda e: self._send_broadcast())
        
        ttk.Button(input_frame, text="Senden", command=self._send_broadcast).pack(side=tk.RIGHT, padx=(5, 0))
        
    def _create_peer_panel(self, parent):
        """Erstellt das Peer-to-Peer-Chat-Panel"""
        peer_frame = ttk.Frame(parent)
        parent.add(peer_frame, weight=2)
        
        ttk.Label(peer_frame, text="Direkt-Chats", font=('Arial', 10, 'bold')).pack(pady=5)
        
        # Notebook für mehrere Peer-Chats
        self.peer_chat_notebook = ttk.Notebook(peer_frame)
        self.peer_chat_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Info-Label wenn keine Chats offen
        info_frame = ttk.Frame(self.peer_chat_notebook)
        self.peer_chat_notebook.add(info_frame, text="Info")
        
        info_label = ttk.Label(
            info_frame,
            text="Doppelklick auf einen Benutzer\nlinks, um einen Chat zu starten",
            justify=tk.CENTER
        )
        info_label.pack(expand=True)
    
    def _register_callbacks(self):
        """Registriert alle Event-Callbacks beim Client"""
        self.client.register_ui_callback('user_joined', self.show_user_joined)
        self.client.register_ui_callback('user_left', self.show_user_left)
        self.client.register_ui_callback('broadcast_message', self.show_broadcast_message)
        self.client.register_ui_callback('peer_chat_started', self.show_peer_chat_started)
        self.client.register_ui_callback('peer_chat_ended', self.show_peer_chat_ended)
        self.client.register_ui_callback('peer_message', self.show_peer_message)
        self.client.register_ui_callback('peer_message_sent', self.show_peer_message_sent)
        self.client.register_ui_callback('chat_request', self._on_chat_request)
        self.client.register_ui_callback('error', self._on_error)
    
    def _on_chat_request(self, from_nick: str):
        """Wird aufgerufen bei Chat-Anfrage"""
        self.add_broadcast_message(f">>> Chat-Anfrage von {from_nick} <<<")
    
    def _on_error(self, error_msg: str):
        """Wird aufgerufen bei Fehler"""
        self.add_broadcast_message(f"[SERVER ERROR] {error_msg}")
        
    def _on_user_double_click(self, event):
        """Wird aufgerufen bei Doppelklick auf Benutzer"""
        self._start_selected_chat()
        
    def _start_selected_chat(self):
        """Startet einen Chat mit dem ausgewählten Benutzer"""
        selection = self.users_listbox.curselection()
        if not selection:
            return
            
        username = self.users_listbox.get(selection[0])
        # Entferne "[verbunden]" falls vorhanden
        username = username.replace(" [verbunden]", "").strip()
        
        # Prüfe ob bereits verbunden
        with self.client.peer_lock:
            if username not in self.client.peer_connections:
                # Initiiere Chat in separatem Thread (blockiert GUI nicht)
                threading.Thread(
                    target=self.client.initiate_peer_chat,
                    args=(username,),
                    daemon=True
                ).start()
                self.add_broadcast_message(f">>> Chat-Anfrage an {username} gesendet <<<")
            else:
                # Zeige existierenden Tab
                if username in self.peer_chat_tabs:
                    # Wechsle zum Tab
                    frame, _, _ = self.peer_chat_tabs[username]
                    for i in range(self.peer_chat_notebook.index('end')):
                        if self.peer_chat_notebook.tab(i, 'text') == username:
                            self.peer_chat_notebook.select(i)
                            break
                            
    def create_peer_chat_tab(self, peer_nick: str):
        """Erstellt einen neuen Tab für einen Peer-Chat"""
        # Thread-safe: Führe im GUI-Thread aus
        if not self.root:
            return
            
        if threading.current_thread() != threading.main_thread():
            # Rufe im GUI-Thread auf
            self.root.after(0, lambda: self.create_peer_chat_tab(peer_nick))
            return
            
        if peer_nick in self.peer_chat_tabs:
            return
            
        # Neuer Tab
        tab_frame = ttk.Frame(self.peer_chat_notebook)
        self.peer_chat_notebook.add(tab_frame, text=peer_nick)
        
        # Chat-Anzeige
        chat_text = scrolledtext.ScrolledText(
            tab_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            height=15
        )
        chat_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Eingabebereich
        input_frame = ttk.Frame(tab_frame)
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        input_entry = ttk.Entry(input_frame)
        input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        def send_peer_msg():
            msg = input_entry.get().strip()
            if msg:
                # Sende in separatem Thread (blockiert GUI nicht)
                # Die Anzeige erfolgt über das peer_message_sent Event
                threading.Thread(
                    target=self.client.send_peer_message,
                    args=(peer_nick, msg),
                    daemon=True
                ).start()
                input_entry.delete(0, tk.END)
                
        input_entry.bind('<Return>', lambda e: send_peer_msg())
        
        send_btn = ttk.Button(input_frame, text="Senden", command=send_peer_msg)
        send_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Speichern
        self.peer_chat_tabs[peer_nick] = (tab_frame, chat_text, input_entry)
        
        # Wechsle zum neuen Tab
        self.peer_chat_notebook.select(tab_frame)
        
    def remove_peer_chat_tab(self, peer_nick: str):
        """Entfernt einen Peer-Chat-Tab"""
        # Thread-safe: Führe im GUI-Thread aus
        if not self.root:
            return
            
        if threading.current_thread() != threading.main_thread():
            self.root.after(0, lambda: self.remove_peer_chat_tab(peer_nick))
            return
            
        if peer_nick not in self.peer_chat_tabs:
            return
            
        frame, _, _ = self.peer_chat_tabs[peer_nick]
        
        # Finde Tab-Index
        for i in range(self.peer_chat_notebook.index('end')):
            if self.peer_chat_notebook.tab(i, 'text') == peer_nick:
                self.peer_chat_notebook.forget(i)
                break
                
        del self.peer_chat_tabs[peer_nick]
        
    def add_broadcast_message(self, message: str):
        """Fügt eine Nachricht zum Broadcast-Chat hinzu"""
        # Thread-safe: Führe im GUI-Thread aus
        if not self.root or not self.chat_display:
            return
            
        if threading.current_thread() != threading.main_thread():
            self.root.after(0, lambda: self.add_broadcast_message(message))
            return
            
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, message + '\n')
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
            
    def add_peer_message(self, peer_nick: str, from_nick: str, message: str):
        """Fügt eine Nachricht zu einem Peer-Chat hinzu"""
        # Thread-safe: Führe im GUI-Thread aus
        if not self.root:
            return
            
        if threading.current_thread() != threading.main_thread():
            self.root.after(0, lambda: self.add_peer_message(peer_nick, from_nick, message))
            return
            
        # Erstelle Tab falls nicht vorhanden
        if peer_nick not in self.peer_chat_tabs:
            self.create_peer_chat_tab(peer_nick)
            
        if peer_nick not in self.peer_chat_tabs:
            return
            
        _, chat_text, _ = self.peer_chat_tabs[peer_nick]
        
        chat_text.config(state=tk.NORMAL)
        chat_text.insert(tk.END, f"[{from_nick}] {message}\n")
        chat_text.see(tk.END)
        chat_text.config(state=tk.DISABLED)
        
    def update_users_list(self):
        """Aktualisiert die Benutzerliste"""
        # Thread-safe: Führe im GUI-Thread aus
        if not self.root or not self.users_listbox:
            return
            
        if threading.current_thread() != threading.main_thread():
            self.root.after(0, self.update_users_list)
            return
            
        # Aktuelle Auswahl speichern
        current_selection = self.users_listbox.curselection()
        selected_user = None
        if current_selection:
            selected_user = self.users_listbox.get(current_selection[0])
            
        # Liste leeren
        self.users_listbox.delete(0, tk.END)
        
        # Benutzer hinzufügen
        with self.client.users_lock:
            for nick in sorted(self.client.users.keys()):
                with self.client.peer_lock:
                    status = " [verbunden]" if nick in self.client.peer_connections else ""
                display_name = f"{nick}{status}"
                self.users_listbox.insert(tk.END, display_name)
                
                # Auswahl wiederherstellen
                if selected_user and display_name == selected_user:
                    self.users_listbox.selection_set(self.users_listbox.size() - 1)
                    
    def _send_broadcast(self):
        """Sendet eine Broadcast-Nachricht"""
        message = self.broadcast_input.get().strip()
        if message:
            # Sende in separatem Thread (blockiert GUI nicht)
            threading.Thread(
                target=self.client.send_broadcast,
                args=(message,),
                daemon=True
            ).start()
            self.broadcast_input.delete(0, tk.END)
            
    def _update_loop(self):
        """Aktualisiert die GUI regelmäßig"""
        import time
        while self.running:
            try:
                if self.root:
                    self.root.after(0, self.update_users_list)
                time.sleep(1)
            except Exception as e:
                logging.error(f"Fehler im GUI-Update-Loop: {e}")
                break
                
    def on_closing(self):
        """Wird aufgerufen beim Schließen des Fensters"""
        self.running = False
        if self.root:
            self.root.destroy()
            
    def show_user_joined(self, nickname: str, ip: str = None, udp_port: int = None):
        """Zeigt an, dass ein Benutzer beigetreten ist"""
        self.add_broadcast_message(f">>> {nickname} ist beigetreten <<<")
        self.update_users_list()
        
    def show_user_left(self, nickname: str):
        """Zeigt an, dass ein Benutzer gegangen ist"""
        self.add_broadcast_message(f">>> {nickname} hat den Chat verlassen <<<")
        self.update_users_list()
        
        # Entferne Chat-Tab falls vorhanden
        if nickname in self.peer_chat_tabs:
            self.remove_peer_chat_tab(nickname)
            
    def show_broadcast_message(self, from_nick: str, message: str):
        """Zeigt eine Broadcast-Nachricht an"""
        self.add_broadcast_message(f"[{from_nick}] {message}")
        
    def show_peer_chat_started(self, peer_nick: str):
        """Zeigt an, dass ein Peer-Chat gestartet wurde"""
        self.create_peer_chat_tab(peer_nick)
        self.add_broadcast_message(f">>> Direkt-Chat mit {peer_nick} gestartet <<<")
        self.update_users_list()
        
    def show_peer_chat_ended(self, peer_nick: str):
        """Zeigt an, dass ein Peer-Chat beendet wurde"""
        if peer_nick in self.peer_chat_tabs:
            self.add_peer_message(peer_nick, "System", f"{peer_nick} hat den Chat beendet")
        self.add_broadcast_message(f">>> {peer_nick} hat den Direkt-Chat beendet <<<")
        self.update_users_list()
        
    def show_peer_message(self, peer_nick: str, message: str):
        """Zeigt eine empfangene Peer-Nachricht an"""
        self.add_peer_message(peer_nick, peer_nick, message)
    
    def show_peer_message_sent(self, peer_nick: str, message: str):
        """Zeigt eine gesendete Peer-Nachricht an"""
        self.add_peer_message(peer_nick, self.client.nickname, message)
