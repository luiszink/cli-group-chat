# Group Chat System

Ein vollständiges Peer-to-Peer Group Chat System mit zentralem Server für Benutzerverwaltung und direkter P2P-Kommunikation zwischen Clients.

## Features

- **Zentrale Benutzerverwaltung**: Server verwaltet alle registrierten Benutzer
- **TCP-Server-Kommunikation**: Zuverlässige Übertragung für Registrierung und Updates
- **Broadcast-Nachrichten**: Nachrichten an alle Benutzer über den Server
- **Peer-to-Peer Direct Chat**: Direkte TCP-Verbindungen zwischen Clients
- **UDP-Signalisierung**: Port-Austausch für P2P-Verbindungsaufbau
- **Fehlerbehandlung**: Robuste Behandlung von Verbindungsabbrüchen, Timeouts und ungültigen Nachrichten

## Architektur

### Server
- Verwaltet Nutzerliste (Nickname, IP, UDP-Port)
- TCP-Socket für Client-Verbindungen
- Sendet Updates bei Join/Leave an alle Clients
- Verteilt Broadcast-Nachrichten

### Client
- Registrierung beim Server via TCP
- UDP-Socket für P2P-Signalisierung (empfängt Chat-Anfragen)
- TCP Listening-Socket für eingehende P2P-Verbindungen
- Mehrere gleichzeitige P2P-Chat-Verbindungen möglich

### P2P-Verbindungsaufbau
1. Client A möchte mit Client B chatten
2. A öffnet TCP Listening-Socket
3. A sendet UDP-Paket an B mit seinem TCP-Port
4. B empfängt UDP-Paket und baut TCP-Verbindung zu A auf
5. Chat-Nachrichten laufen über diese direkte TCP-Verbindung

## Installation

### Voraussetzungen
- Python 3.7 oder höher
- Keine externen Abhängigkeiten (nur Python Standard Library)

### Download
```bash
git clone <repository-url>
cd group-chat
```

## Verwendung

### 1. Server starten

```bash
python server.py [port]
```

**Beispiel:**
```bash
python server.py 5555
```

Standard-Port ist `5555` wenn nicht angegeben.

Der Server läuft und wartet auf Client-Verbindungen.

### 2. Clients starten

```bash
python client.py <nickname> <server_host> <server_port> [udp_port]
```

**Parameter:**
- `nickname`: Dein eindeutiger Benutzername (2-20 Zeichen, alphanumerisch + Unterstrich)
- `server_host`: IP/Hostname des Servers (z.B. `localhost` oder `192.168.1.100`)
- `server_port`: Port des Servers (z.B. `5555`)
- `udp_port`: (Optional) UDP-Port für P2P-Kommunikation (Standard: `6000`)

**Beispiele:**

Drei Clients auf demselben Rechner:
```bash
# Terminal 1 - Server
python server.py 5555

# Terminal 2 - Client Alice
python client.py Alice localhost 5555 6001

# Terminal 3 - Client Bob
python client.py Bob localhost 5555 6002

# Terminal 4 - Client Charlie
python client.py Charlie localhost 5555 6003
```

Clients im Netzwerk:
```bash
# Auf Server-Rechner (z.B. 192.168.1.10)
python server.py 5555

# Auf Client-Rechner 1
python client.py Alice 192.168.1.10 5555 6001

# Auf Client-Rechner 2
python client.py Bob 192.168.1.10 5555 6002
```

### 3. Client-Befehle

Nach erfolgreichem Login stehen folgende Befehle zur Verfügung:

#### `/broadcast <nachricht>`
Sendet eine Nachricht an alle verbundenen Benutzer über den Server.

```
> /broadcast Hallo zusammen!
```

#### `/users`
Zeigt alle aktuell online Benutzer an.

```
> /users
=== Online Benutzer (2) ===
  - Bob
  - Charlie [verbunden]
```

#### `/chat <user>`
Initiiert einen Direkt-Chat mit einem anderen Benutzer.

```
> /chat Bob
Chat-Anfrage an Bob gesendet
>>> Direkt-Chat mit Bob verbunden <<<
```

#### `/msg <user> <nachricht>`
Sendet eine Direkt-Nachricht an einen Benutzer (Chat-Verbindung muss bereits bestehen).

```
> /msg Bob Hi Bob, wie geht's?
```

#### `/quit`
Beendet den Client und meldet sich vom Server ab.

```
> /quit
```

## Beispiel-Session

### Server-Terminal
```
$ python server.py 5555
2025-12-10 10:00:00 - INFO - Server gestartet auf 0.0.0.0:5555
2025-12-10 10:00:15 - INFO - Neue Verbindung von ('127.0.0.1', 54321)
2025-12-10 10:00:15 - INFO - Client Alice erfolgreich eingeloggt von 127.0.0.1:6001
2025-12-10 10:00:30 - INFO - Neue Verbindung von ('127.0.0.1', 54322)
2025-12-10 10:00:30 - INFO - Client Bob erfolgreich eingeloggt von 127.0.0.1:6002
2025-12-10 10:01:00 - INFO - Broadcast von Alice: Hallo Bob!
```

### Client Alice
```
$ python client.py Alice localhost 5555 6001
2025-12-10 10:00:15 - INFO - UDP Socket gebunden auf Port 6001
2025-12-10 10:00:15 - INFO - TCP Listening Socket auf Port 54123
2025-12-10 10:00:15 - INFO - Erfolgreich beim Server angemeldet

=== Aktuelle Benutzer (0) ===

=== Group Chat ===
Befehle:
  /broadcast <nachricht>  - Broadcast an alle
  /msg <user> <nachricht> - Direkt-Nachricht
  /chat <user>            - Direkt-Chat initiieren
  /users                  - Benutzer auflisten
  /quit                   - Beenden

> 
>>> Bob ist beigetreten <<<
> /broadcast Hallo Bob!
> 
[BROADCAST von Alice] Hallo Bob!
> /chat Bob
Chat-Anfrage an Bob gesendet
>>> Direkt-Chat mit Bob verbunden <<<
> /msg Bob Wie geht's?
> 
[Bob] Gut, danke! Und dir?
> /quit
```

### Client Bob
```
$ python client.py Bob localhost 5555 6002
2025-12-10 10:00:30 - INFO - Erfolgreich beim Server angemeldet

=== Aktuelle Benutzer (1) ===
  - Alice

> 
[BROADCAST von Alice] Hallo Bob!
> 
>>> Chat-Anfrage von Alice <<<
>>> Direkt-Chat mit Alice gestartet <<<
> 
[Alice] Wie geht's?
> /msg Alice Gut, danke! Und dir?
```

## Protokoll-Spezifikation

Das System verwendet ein textbasiertes, zeilenorientiertes Protokoll. Siehe [PROTOCOL.md](PROTOCOL.md) für die vollständige Spezifikation.

### Wichtigste Protokoll-Nachrichten

#### Client → Server (TCP)
- `LOGIN <nickname> <udp_port>\n`
- `BROADCAST <text>\n`
- `LOGOUT\n`

#### Server → Client (TCP)
- `LOGIN_OK\n`
- `USERLIST_BEGIN\n ... USERLIST_END\n`
- `USER_JOINED <nickname> <ip> <udp_port>\n`
- `USER_LEFT <nickname>\n`
- `BROADCAST_MSG <from_nickname> <text>\n`
- `ERROR <type>\n`

#### Peer → Peer (UDP)
- `CHAT_REQUEST <from_nickname> <tcp_port>\n`
- `CHAT_ACCEPT <to_nickname> <from_nickname>\n`
- `CHAT_REJECT <reason>\n`

#### Peer → Peer (TCP)
- `CHAT_HELLO <nickname>\n`
- `MSG <text>\n`
- `BYE\n`

## Fehlerbehandlung

### TCP-Verbindungen
- **Nachrichtenabgrenzung**: Jede Nachricht endet mit `\n`
- **Verbindungsabbruch**: Automatische Cleanup und Benachrichtigung anderer Clients
- **Ungültige Nachrichten**: Server sendet `ERROR` und kann Verbindung schließen

### UDP-Kommunikation
- **Paketverlust**: Retry-Mechanismus mit Timeout (5s, max. 3 Versuche)
- **Duplikate**: Werden erkannt und ignoriert
- **Ungültige Pakete**: Werden geloggt und ignoriert

### Fehlertypen
- `ERROR NICK_IN_USE` - Nickname bereits vergeben
- `ERROR INVALID_FORMAT` - Ungültiges Nachrichtenformat
- `ERROR NOT_LOGGED_IN` - Aktion vor erfolgreichem Login
- `ERROR MSG_TOO_LONG` - Nachricht zu lang (> 1000 Zeichen)
- `ERROR UNKNOWN_CMD` - Unbekanntes Kommando
- `ERROR PROTOCOL_VIOLATION` - Protokollverletzung

## Einschränkungen & Bekannte Probleme

1. **Nickname-Kollisionen**: Nicknames sind case-sensitive und müssen eindeutig sein
2. **Firewall/NAT**: P2P-Verbindungen können durch Firewalls blockiert werden
3. **Keine Verschlüsselung**: Alle Kommunikation erfolgt im Klartext
4. **Keine Authentifizierung**: Jeder kann sich mit beliebigem Nickname anmelden
5. **Maximale Nachrichtenlänge**: 1000 Zeichen für Broadcast, keine Begrenzung für P2P
6. **Kein Reconnect**: Bei Verbindungsabbruch muss Client neu gestartet werden

## Erweiterungsmöglichkeiten

- [ ] TLS/SSL für verschlüsselte Verbindungen
- [ ] Authentifizierung mit Passwörtern
- [ ] Persistente Nachrichtenhistorie
- [ ] Dateiübertragung
- [ ] Gruppenchats (mehrere Teilnehmer)
- [ ] User-Status (online, away, busy)
- [ ] STUN/TURN für NAT-Traversal
- [ ] GUI-Client
- [ ] Ende-zu-Ende-Verschlüsselung für P2P-Chats

## Troubleshooting

### "Nickname bereits vergeben"
Ein anderer Client verwendet bereits diesen Nickname. Wähle einen anderen.

### "Keine Verbindung zum Server"
- Prüfe ob Server läuft
- Prüfe Server-IP und Port
- Prüfe Firewall-Einstellungen

### "Chat-Anfrage fehlgeschlagen"
- Prüfe ob beide Clients hinter NAT/Firewall sind
- Verwende lokale IPs im gleichen Netzwerk für Tests
- Prüfe UDP-Ports in Firewall

### "Port bereits in Verwendung"
- Wähle einen anderen UDP-Port beim Client-Start
- Prüfe ob bereits eine Instanz läuft

## Lizenz

Dieses Projekt ist für akademische Zwecke erstellt.

## Autoren

Erstellt für das Modul "Rechnernetze" im Semester 6 AIN.
