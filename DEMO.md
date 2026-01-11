# Demo-Skript für Präsentation

## 🎬 Automatische Demo (Docker)

**Zeigt: Vollständige Netzwerk-Kommunikation mit Server + 2 Clients automatisch**

```bash
docker-compose -f docker/docker-compose.yml up --build
```

Warten bis Demo durchgelaufen ist (~30 Sekunden), dann beenden:

```bash
# Ctrl+C drücken, dann:
docker-compose -f docker/docker-compose.yml down
```

---

## 💻 Manuelle Demo (Python)

### 1. Server starten

**Zeigt: Server wartet auf Clients und zeigt Netzwerk-IP**

```bash
python src/server.py 5555
```

### 2. Client 1 starten (neues Terminal)

**Zeigt: Client-Registrierung und Login**

```bash
python src/client.py Alice localhost 5555 6001
```

### 3. Client 2 starten (neues Terminal)

**Zeigt: Zweiter Client verbindet sich, beide sehen sich**

```bash
python src/client.py Bob localhost 5555 6002
```

### 4. Broadcast-Nachricht (in Alice Terminal)

**Zeigt: Server verteilt Nachricht an alle Clients**

```bash
/broadcast Hallo von Alice an alle!
```

### 5. Online-Benutzer anzeigen (in Bob Terminal)

**Zeigt: Bob sieht Alice in der Benutzerliste**

```bash
/users
```

### 6. P2P-Chat starten (in Bob Terminal)

**Zeigt: UDP-Signalisierung und TCP-Verbindungsaufbau zwischen Clients**

```bash
/chat Alice
```

### 7. Direkt-Nachricht senden (in Bob Terminal)

**Zeigt: Nachricht geht direkt über TCP, nicht über Server**

```bash
/msg Alice Hey Alice, das ist eine direkte P2P-Nachricht!
```

### 8. Antwort senden (in Alice Terminal)

**Zeigt: Bidirektionale P2P-Kommunikation**

```bash
/msg Bob Hi Bob! Direkter Chat funktioniert!
```

### 9. GUI starten (optional, in neuem Terminal)

**Zeigt: Grafische Benutzeroberfläche mit Tabs**

```bash
python src/client.py Charlie localhost 5555 6003
```

Dann im Chat:
```bash
/gui
```

### 10. Beenden

**In jedem Client-Terminal:**
```bash
/quit
```

**Im Server-Terminal:**
```bash
# Ctrl+C drücken
```

---

## 🌐 Netzwerk-Demo (Verschiedene Rechner)

### 1. IP-Adresse ermitteln (Server-Rechner)

**Zeigt: Lokale Netzwerk-IP für andere Clients**

```bash
python scripts/get_ip.py
```

### 2. Server starten (Server-Rechner)

```bash
python src/server.py 5555
```

### 3. Client von anderem Rechner (Laptop 1)

**Zeigt: Client aus Netzwerk verbindet sich (IP anpassen!)**

```bash
python src/client.py Alice 192.168.178.63 5555 6001
```

### 4. Zweiter Client von anderem Rechner (Laptop 2)

```bash
python src/client.py Bob 192.168.178.63 5555 6002
```

**Dann wie oben chatten!**

---

## 📋 Empfohlene Demo-Reihenfolge für Abgabe

1. **Docker-Demo zeigen** (vollautomatisch, 30 Sek)
2. **Projektstruktur erklären** (Ordner zeigen)
3. **Manuelle Demo** (Broadcast + P2P zeigen)
4. **Protokoll kurz zeigen** (`docs/PROTOCOL.md` öffnen)
5. **Fertig!** ✅

---

## 🎯 Was wird demonstriert?

- ✅ **TCP Server-Client**: Registrierung, Benutzerverwaltung
- ✅ **Broadcast**: Server verteilt Nachrichten an alle
- ✅ **UDP Signalisierung**: Port-Austausch für P2P
- ✅ **TCP Peer-to-Peer**: Direkte Verbindung zwischen Clients
- ✅ **Multithreading**: Server handhabt mehrere Clients parallel
- ✅ **Netzwerk-fähig**: Funktioniert über LAN/WLAN
- ✅ **Protokoll**: Textbasiert, zeilenorientiert
- ✅ **Docker**: Deployment und automatische Demo
