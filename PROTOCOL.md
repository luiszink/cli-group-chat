"""
Protokoll-Spezifikation für Group Chat System
=============================================

1. CLIENT-SERVER-PROTOKOLL (TCP)
=================================

1.1 Login
---------
Client -> Server:
    LOGIN <nickname> <udp_port>\n

Server -> Client (Erfolg):
    LOGIN_OK\n
    USERLIST_BEGIN\n
    USER <nickname1> <ip1> <udp_port1>\n
    USER <nickname2> <ip2> <udp_port2>\n
    ...
    USERLIST_END\n

Server -> Client (Fehler):
    ERROR NICK_IN_USE\n          # Nickname bereits vergeben
    ERROR INVALID_FORMAT\n       # Ungültiges Nachrichtenformat
    ERROR NOT_LOGGED_IN\n        # Aktion vor erfolgreichem Login

Nickname-Regeln:
- 2-20 Zeichen
- Nur alphanumerische Zeichen und Unterstrich
- Eindeutig


1.2 User-Updates
----------------
Server -> Alle Clients (bei neuem User):
    USER_JOINED <nickname> <ip> <udp_port>\n

Server -> Alle Clients (bei User-Abmeldung):
    USER_LEFT <nickname>\n


1.3 Broadcast-Nachrichten
--------------------------
Client -> Server:
    BROADCAST <text>\n

Server -> Alle Clients:
    BROADCAST_MSG <from_nickname> <text>\n

Fehler:
    ERROR MSG_TOO_LONG\n         # Nachricht > 1000 Zeichen


1.4 Logout
----------
Client -> Server:
    LOGOUT\n

Server -> Client:
    LOGOUT_OK\n

Dann: Verbindung schließen, USER_LEFT an alle anderen senden


1.5 Fehlerbehandlung
--------------------
- Unbekanntes Kommando -> ERROR UNKNOWN_CMD\n
- Nachricht vor Login -> ERROR NOT_LOGGED_IN\n
- Falsches Format -> ERROR INVALID_FORMAT\n
- Verbindungsabbruch -> automatische Abmeldung


2. PEER-TO-PEER-PROTOKOLL
==========================

2.1 UDP-Phase (Chat-Anfrage)
-----------------------------
Initiator (A) öffnet TCP-Listening-Socket auf Port X

A -> B (UDP):
    CHAT_REQUEST <from_nickname> <tcp_port>\n

B empfängt und verbindet zu A via TCP

Optional - B -> A (UDP):
    CHAT_ACCEPT <to_nickname> <from_nickname>\n
oder
    CHAT_REJECT <reason>\n

Retry-Strategie:
- Timeout: 5 Sekunden
- Max. 3 Versuche
- Bei mehrfachen Anfragen: Duplikate ignorieren


2.2 TCP-Phase (Direkt-Chat)
----------------------------
Nach TCP-Verbindungsaufbau B -> A:

B -> A:
    CHAT_HELLO <nickname_B>\n

A -> B:
    CHAT_HELLO <nickname_A>\n

Chat-Nachrichten:
A <-> B:
    MSG <text>\n

Verbindungsende:
A oder B:
    BYE\n

Gegenüber antwortet:
    BYE\n
oder schließt Verbindung

Fehler:
    ERROR UNKNOWN_CMD\n          # Unbekanntes Kommando
    ERROR PROTOCOL_VIOLATION\n   # Protokollverletzung (z.B. MSG vor CHAT_HELLO)


3. NACHRICHTENFORMAT
====================

3.1 Abgrenzung
--------------
- Jede Nachricht endet mit \n (Newline)
- UTF-8 Encoding
- Maximale Länge: 1024 Bytes pro Zeile

3.2 Parsing
-----------
- Space ' ' als Trennzeichen zwischen Command und Parametern
- Erster Space trennt Command von Argumenten
- Bei Text-Feldern: alles nach erstem Space ist der Text

Beispiele:
    "BROADCAST Hello World" -> Command: BROADCAST, Text: "Hello World"
    "MSG Test 123" -> Command: MSG, Text: "Test 123"


4. FEHLERBEHANDLUNG & TIMEOUTS
===============================

4.1 TCP-Verbindungen
--------------------
- Verbindungsabbruch: Socket schließen, Cleanup durchführen
- Timeout beim Lesen: keine (blockierend)
- Ungültige Nachricht: ERROR senden, Verbindung optional schließen

4.2 UDP-Kommunikation
---------------------
- Paketverlust: Retry mit Timeout (5s, max. 3 Versuche)
- Duplikate: Ignorieren wenn bereits behandelt
- Ungültige Pakete: Loggen und ignorieren

4.3 Unerwartete Situationen
---------------------------
- Client sendet Command vor Login: ERROR NOT_LOGGED_IN\n
- Unbekanntes Command: ERROR UNKNOWN_CMD\n
- Nachricht zu lang: ERROR MSG_TOO_LONG\n
- Peer nicht erreichbar: Nach Timeouts aufgeben
- Server nicht erreichbar: Reconnect oder Beenden


5. ZUSTANDSDIAGRAMME
====================

5.1 Client-Status
-----------------
DISCONNECTED -> (TCP connect) -> CONNECTING
CONNECTING -> (LOGIN sent) -> AUTHENTICATING
AUTHENTICATING -> (LOGIN_OK) -> CONNECTED
AUTHENTICATING -> (ERROR) -> DISCONNECTED
CONNECTED -> (LOGOUT) -> DISCONNECTED

5.2 Peer-Verbindung
-------------------
IDLE -> (CHAT_REQUEST sent) -> REQUESTING
REQUESTING -> (TCP accept) -> HANDSHAKING
HANDSHAKING -> (CHAT_HELLO exchanged) -> CHATTING
CHATTING -> (BYE) -> CLOSED

Alternative (Empfänger):
IDLE -> (CHAT_REQUEST received) -> ACCEPTING
ACCEPTING -> (TCP connect to peer) -> HANDSHAKING
HANDSHAKING -> (CHAT_HELLO exchanged) -> CHATTING
CHATTING -> (BYE) -> CLOSED


6. SICHERHEITSASPEKTE
======================

6.1 Validierung
---------------
- Nickname: Länge und Zeichen prüfen
- Ports: 1-65535 Bereich
- Nachrichten: Länge begrenzen
- IP-Adressen: Format validieren

6.2 Ressourcen
--------------
- Max. Verbindungen pro Client: z.B. 10
- Max. Nachrichtengröße: 1000 Zeichen
- Socket-Timeouts setzen
- Ressourcen freigeben (finally-Blöcke)

6.3 DoS-Schutz
--------------
- Rate-Limiting für Nachrichten
- Verbindungslimits
- Timeout für inaktive Verbindungen


7. ERWEITERUNGEN (OPTIONAL)
============================

7.1 Zusätzliche Features
------------------------
- PING/PONG Keep-Alive
- Verschlüsselte Verbindungen (TLS)
- Dateiübertragung
- Gruppenchats
- Nachrichtenhistorie
- User-Status (online, away, busy)

7.2 Verbesserungen
------------------
- JSON-basiertes Protokoll für komplexere Daten
- Kompression für große Nachrichten
- Ende-zu-Ende-Verschlüsselung
- Authentifizierung mit Passwort/Token
"""
